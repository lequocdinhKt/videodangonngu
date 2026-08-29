"""Regression tests for audit pipeline fixes."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import app.config.settings as settings_mod
import app.integrations.supabase.database as db_mod
import app.services.storage.local as storage_mod
from app.models.db import (
    JobStatus,
    LanguageStatus,
    ProcessingStage,
    VideoStatus,
)
from app.services.audio.alignment import apply_alignment, compute_alignment
from app.services.audio.ffmpeg_service import FFmpegService
from app.services.audio.workspace import cleanup_workspace, compute_timeline_duration_ms, workspace_root
from app.workers.pipeline_worker import _merge_quality_flags, run_pipeline
from tests.e2e_fixtures import ffmpeg_available
from tests.mock_repository import InMemoryRepository


def _setup_pipeline_test(tmp: str, monkeypatch) -> InMemoryRepository:
    os.environ["STORAGE_DIR"] = tmp
    os.environ["SKIP_SUPABASE_VALIDATION"] = "true"
    os.environ["STORAGE_PROVIDER"] = "local"
    settings_mod._settings = None
    storage_mod.reset_storage()
    repo = InMemoryRepository()
    monkeypatch.setattr(db_mod, "_repo", repo)
    return repo


def test_compute_timeline_duration_uses_video_when_longer():
    assert compute_timeline_duration_ms(120_000, 80_000) == 120_000


def test_compute_timeline_duration_uses_srt_when_longer():
    assert compute_timeline_duration_ms(80_000, 95_000) == 95_000


def test_compute_timeline_duration_without_video():
    assert compute_timeline_duration_ms(None, 50_000) == 50_000


def test_alignment_needs_retranslate_does_not_modify_audio(tmp_path):
    ffmpeg = MagicMock(spec=FFmpegService)
    ffmpeg.get_duration_ms.return_value = 5500
    input_path = tmp_path / "raw.mp3"
    input_path.write_bytes(b"fake")
    output_path = tmp_path / "final.mp3"

    result = apply_alignment(ffmpeg, input_path, output_path, 3000)

    assert result.status == "needs_retranslate"
    ffmpeg.change_tempo.assert_not_called()
    ffmpeg.add_silence.assert_not_called()
    ffmpeg.export_mp3.assert_not_called()


def test_alignment_persistent_needs_retranslate_status():
    result = compute_alignment(5500, 3000, max_speed=1.10, retry_threshold=1.30)
    assert result.status == "needs_retranslate"


def test_merge_quality_flags_preserves_other_languages():
    existing = [
        "alignment_warning:ru-RU:seg1",
        "alignment_failed:ru-RU:seg2",
        "validation_failed:en-US",
    ]
    new_flags = ["alignment_warning:en-US:seg1"]
    merged = _merge_quality_flags(existing, new_flags, ["en-US"])
    assert "alignment_warning:ru-RU:seg1" in merged
    assert "alignment_failed:ru-RU:seg2" in merged
    assert "validation_failed:en-US" not in merged
    assert "alignment_warning:en-US:seg1" in merged


def test_workspace_cleanup_removes_temp_files(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        _setup_pipeline_test(tmp, monkeypatch)
        vid = uuid.uuid4()
        root = workspace_root(vid)
        (root / "segments" / "en-US").mkdir(parents=True)
        (root / "segments" / "en-US" / "00001_final.mp3").write_bytes(b"x")
        (root / "timeline_work").mkdir()
        (root / "timeline_work" / "gap_0.mp3").write_bytes(b"x")
        (root / "voice_en-US.mp3").write_bytes(b"x")
        (root / "mixed_en-US.mp3").write_bytes(b"x")
        (root / "vi_mixed.mp3").write_bytes(b"x")
        (root / "extracted_audio.mp3").write_bytes(b"x")

        cleanup_workspace(vid)

        assert not (root / "segments").exists()
        assert not (root / "timeline_work").exists()
        assert not (root / "voice_en-US.mp3").exists()
        assert not (root / "mixed_en-US.mp3").exists()
        assert not (root / "vi_mixed.mp3").exists()
        assert not (root / "extracted_audio.mp3").exists()


@pytest.mark.skipif(not ffmpeg_available(), reason="needs ffmpeg")
def test_mix_voice_music_does_not_exceed_duration(tmp_path):
    ffmpeg = FFmpegService()
    duration_ms = 5000

    voice = tmp_path / "voice.mp3"
    music = tmp_path / "music.mp3"
    output = tmp_path / "mixed.mp3"

    ffmpeg.generate_silence(voice, duration_ms)
    ffmpeg.generate_silence(music, duration_ms * 3)

    ffmpeg.mix_voice_and_music(voice, music, output, music_volume_db=-18.0, duration_ms=duration_ms)

    mixed_ms = ffmpeg.get_duration_ms(output)
    assert mixed_ms <= duration_ms + 200


@pytest.mark.asyncio
async def test_persistent_alignment_failure_flags_requires_review(monkeypatch):
    tmp = tempfile.mkdtemp()
    try:
        repo = _setup_pipeline_test(tmp, monkeypatch)
        from app.services.storage.local import get_storage
        from app.workers import pipeline_worker as pw

        storage = get_storage()
        vid = uuid.uuid4()
        user = await repo.create_user("t@t.com", "h")
        await repo.create_video(
            "Alignment Test", "Hoi An tour", user.id,
            video_id=vid, duration_ms=10_000, srt_key=f"video/{vid}/source.srt",
        )
        vi_lang = await repo.create_video_language(vid, "vi-VN", LanguageStatus.COMPLETED)
        await repo.create_video_language(vid, "en-US", LanguageStatus.PENDING)
        await repo.create_segments([{
            "video_language_id": str(vi_lang.id), "sequence": 1, "start_ms": 0, "end_ms": 3000,
            "source_text": "Xin chào", "translated_text": "Xin chào",
        }])

        await storage.save_file(f"video/{vid}/source.srt", "1\n00:00:00,000 --> 00:00:03,000\nXin chao\n".encode("utf-8"))

        class FailingAlignmentTTS:
            provider_name = "stub"

            async def synthesize(self, text, language, voice, output_path):
                FFmpegService().generate_silence(Path(output_path), 6000)
                return Path(output_path)

        class StubTranslator:
            provider_name = "stub"

            async def translate_batch(self, segments, context):
                from app.services.translation.base import SegmentOutput
                return [
                    SegmentOutput(
                        sequence=s.sequence, start_ms=s.start_ms, end_ms=s.end_ms,
                        source_text=s.source_text,
                        translated_text="This is a very long translation that will not fit",
                    )
                    for s in segments
                ]

        with patch.object(pw, "get_translation_provider", lambda: StubTranslator()), \
             patch.object(pw, "get_tts_engine", lambda: FailingAlignmentTTS()):
            await run_pipeline(str(vid), language_codes=["en-US"])

        video = await repo.get_video(vid)
        assert video.status == VideoStatus.REQUIRES_REVIEW

        finalize_job = await repo.get_finalize_job(vid)
        flags = json.loads(finalize_job.error_message).get("quality_flags", [])
        assert any("alignment_failed:en-US:seg1" in f for f in flags)

        en_lang = await repo.get_video_language(vid, "en-US")
        segs = await repo.list_segments(en_lang.id)
        assert segs[0].alignment_meta is not None
        assert segs[0].alignment_meta["status"] == "alignment_failed"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.asyncio
async def test_per_language_regeneration_isolation(monkeypatch):
    tmp = tempfile.mkdtemp()
    try:
        repo = _setup_pipeline_test(tmp, monkeypatch)
        from app.services.storage.local import get_storage
        from app.workers import pipeline_worker as pw
        from tests.stub_translation import StubTranslationProvider

        storage = get_storage()
        vid = uuid.uuid4()
        user = await repo.create_user("t@t.com", "h")
        await repo.create_video(
            "Regen Test", "", user.id, status=VideoStatus.READY_FOR_REVIEW,
            video_id=vid, duration_ms=8000, srt_key=f"video/{vid}/source.srt",
        )
        vi_lang = await repo.create_video_language(
            vid, "vi-VN", LanguageStatus.COMPLETED,
        )
        await repo.update_video_language(vi_lang.id, subtitle_key=f"video/{vid}/subtitle/vi.vtt")
        ru_lang = await repo.create_video_language(
            vid, "ru-RU", LanguageStatus.COMPLETED,
        )
        await repo.update_video_language(ru_lang.id, subtitle_key=f"video/{vid}/subtitle/ru.vtt")

        await repo.create_segments([
            {"video_language_id": str(vi_lang.id), "sequence": 1, "start_ms": 1000, "end_ms": 4000,
             "source_text": "Xin chào", "translated_text": "Xin chào"},
            {"video_language_id": str(vi_lang.id), "sequence": 2, "start_ms": 4500, "end_ms": 8000,
             "source_text": "Tạm biệt", "translated_text": "Tạm biệt"},
            {"video_language_id": str(ru_lang.id), "sequence": 1, "start_ms": 1000, "end_ms": 4000,
             "source_text": "Xin chào", "translated_text": "ORIGINAL_RU_SEG1"},
            {"video_language_id": str(ru_lang.id), "sequence": 2, "start_ms": 4500, "end_ms": 8000,
             "source_text": "Tạm biệt", "translated_text": "ORIGINAL_RU_SEG2"},
        ])
        run_id = uuid.uuid4()
        await repo.upsert_job(
            vid, run_id, ProcessingStage.FINALIZE.value, None,
            JobStatus.COMPLETED, 100, json.dumps({"quality_flags": ["alignment_warning:ru-RU:seg1"]}),
        )

        vi_vtt_key = f"video/{vid}/subtitle/vi.vtt"
        ru_vtt_key = f"video/{vid}/subtitle/ru.vtt"
        await storage.save_file(vi_vtt_key, b"WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nXin chao\n")
        await storage.save_file(ru_vtt_key, b"WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nORIGINAL_RU\n")

        vi_hash_before = (await storage.get_path(vi_vtt_key)).read_bytes()

        class FastTTS:
            provider_name = "stub"

            async def synthesize(self, text, language, voice, output_path):
                FFmpegService().generate_silence(Path(output_path), 2500)
                return Path(output_path)

        with patch.object(pw, "get_translation_provider", lambda: StubTranslationProvider()), \
             patch.object(pw, "get_tts_engine", lambda: FastTTS()):
            await run_pipeline(str(vid), language_codes=["ru-RU"])

        vi_segs = await repo.list_segments(vi_lang.id)
        assert vi_segs[0].translated_text == "Xin chào"
        assert vi_segs[1].translated_text == "Tạm biệt"

        ru_segs = await repo.list_segments(ru_lang.id)
        assert ru_segs[0].translated_text != "ORIGINAL_RU_SEG1"

        vi_hash_after = (await storage.get_path(vi_vtt_key)).read_bytes()
        assert vi_hash_after == vi_hash_before
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.asyncio
async def test_quality_flags_preserved_when_regenerating_other_language(monkeypatch):
    tmp = tempfile.mkdtemp()
    try:
        repo = _setup_pipeline_test(tmp, monkeypatch)
        from app.workers import pipeline_worker as pw
        from tests.stub_translation import StubTranslationProvider

        vid = uuid.uuid4()
        user = await repo.create_user("t@t.com", "h")
        await repo.create_video(
            "Flag Test", "", user.id, status=VideoStatus.READY_FOR_REVIEW,
            video_id=vid, duration_ms=8000, srt_key=f"video/{vid}/source.srt",
        )
        vi_lang = await repo.create_video_language(vid, "vi-VN", LanguageStatus.COMPLETED)
        await repo.create_video_language(vid, "en-US", LanguageStatus.COMPLETED)
        await repo.create_video_language(vid, "ru-RU", LanguageStatus.COMPLETED)
        await repo.create_segments([
            {"video_language_id": str(vi_lang.id), "sequence": 1, "start_ms": 1000, "end_ms": 4000,
             "source_text": "Xin chào", "translated_text": "Xin chào"},
            {"video_language_id": str(vi_lang.id), "sequence": 2, "start_ms": 4500, "end_ms": 8000,
             "source_text": "Tạm biệt", "translated_text": "Tạm biệt"},
        ])
        run_id = uuid.uuid4()
        await repo.upsert_job(
            vid, run_id, ProcessingStage.FINALIZE.value, None,
            JobStatus.COMPLETED, 100, json.dumps({"quality_flags": ["alignment_warning:ru-RU:seg1"]}),
        )

        class FastTTS:
            provider_name = "stub"

            async def synthesize(self, text, language, voice, output_path):
                FFmpegService().generate_silence(Path(output_path), 2500)
                return Path(output_path)

        with patch.object(pw, "get_translation_provider", lambda: StubTranslationProvider()), \
             patch.object(pw, "get_tts_engine", lambda: FastTTS()):
            await run_pipeline(str(vid), language_codes=["en-US"])

        finalize_job = await repo.get_finalize_job(vid)
        flags = json.loads(finalize_job.error_message).get("quality_flags", [])
        assert "alignment_warning:ru-RU:seg1" in flags
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.asyncio
async def test_long_video_timeline_duration_in_output(monkeypatch):
    if not ffmpeg_available():
        pytest.skip("needs ffmpeg")

    tmp = tempfile.mkdtemp()
    try:
        repo = _setup_pipeline_test(tmp, monkeypatch)
        from app.services.storage.local import get_storage
        from app.workers import pipeline_worker as pw
        from tests.stub_translation import StubTranslationProvider

        storage = get_storage()
        ffmpeg = FFmpegService()
        vid = uuid.uuid4()
        video_duration_ms = 60_000
        srt_end_ms = 8_000
        user = await repo.create_user("t@t.com", "h")
        await repo.create_video(
            "Long Video", "", user.id, status=VideoStatus.DRAFT,
            video_id=vid, duration_ms=video_duration_ms, srt_key=f"video/{vid}/source.srt",
        )
        vi_lang = await repo.create_video_language(vid, "vi-VN", LanguageStatus.COMPLETED)
        await repo.create_video_language(vid, "en-US", LanguageStatus.PENDING)
        await repo.create_segments([
            {"video_language_id": str(vi_lang.id), "sequence": 1, "start_ms": 1000, "end_ms": 4000,
             "source_text": "Xin chào", "translated_text": "Xin chào"},
            {"video_language_id": str(vi_lang.id), "sequence": 2, "start_ms": 4500, "end_ms": srt_end_ms,
             "source_text": "Tạm biệt", "translated_text": "Tạm biệt"},
        ])

        class ShortTTS:
            provider_name = "stub"

            async def synthesize(self, text, language, voice, output_path):
                ffmpeg.generate_silence(Path(output_path), 2000)
                return Path(output_path)

        with patch.object(pw, "get_translation_provider", lambda: StubTranslationProvider()), \
             patch.object(pw, "get_tts_engine", lambda: ShortTTS()):
            await run_pipeline(str(vid), language_codes=["en-US"])

        audio_path = await storage.get_path(f"video/{vid}/audio/en.mp3")
        assert audio_path.exists()
        audio_ms = ffmpeg.get_duration_ms(audio_path)
        assert audio_ms >= video_duration_ms - 500
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
