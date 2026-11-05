"""
E2E pipeline runner — executes in an isolated environment with temp storage.

Usage: python -m tests.run_e2e_pipeline
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

_E2E_TMP = tempfile.mkdtemp(prefix="e2e_pipeline_")
os.environ["STORAGE_DIR"] = str(Path(_E2E_TMP) / "storage")
os.environ["SKIP_SUPABASE_VALIDATION"] = "true"
os.environ["STORAGE_PROVIDER"] = "local"

import app.config.settings as settings_mod  # noqa: E402
import app.integrations.supabase.database as db_mod  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.core.auth import ensure_admin_user  # noqa: E402
from app.models.db import (  # noqa: E402
    JobStatus,
    LanguageStatus,
    ProcessingStage,
    VideoStatus,
)
from app.services.audio.ffmpeg_service import FFmpegService  # noqa: E402
from app.services.storage.local import get_storage, reset_storage  # noqa: E402
from app.services.subtitle.parser import parse_srt  # noqa: E402
from app.workers.pipeline_worker import run_pipeline  # noqa: E402
from tests.e2e_fixtures import SAMPLE_SRT, generate_fixtures  # noqa: E402
from tests.mock_repository import InMemoryRepository  # noqa: E402

settings_mod._settings = None
reset_storage()
_repo = InMemoryRepository()
db_mod._repo = _repo

SUPPORTED_LANGS = ["vi-VN", "en-US", "ru-RU", "zh-CN"]
TARGET_STAGES = [
    ProcessingStage.PARSE.value,
    ProcessingStage.SUBTITLE_EXPORT.value,
    ProcessingStage.FINALIZE.value,
]
PER_LANG_STAGES = [
    ProcessingStage.TRANSLATE.value,
    ProcessingStage.VALIDATE.value,
    ProcessingStage.TTS.value,
    ProcessingStage.ALIGN.value,
    ProcessingStage.MIX.value,
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


async def _create_video_record(fixtures, storage, ffmpeg) -> tuple[uuid.UUID, str]:
    settings = get_settings()
    user = await _repo.create_user(settings.admin_email, "hash")

    video = await _repo.create_video(
        "E2E Pipeline Test",
        "Automated end-to-end pipeline verification",
        user.id,
    )
    video_id = video.id

    video_key = f"video/{video_id}/original.mp4"
    srt_key = f"video/{video_id}/source.srt"
    voice_key = f"video/{video_id}/voice_vi.mp3"
    music_key = f"video/{video_id}/music.mp3"

    await storage.save_file(video_key, fixtures.video)
    await storage.save_file(srt_key, fixtures.srt)
    await storage.save_file(voice_key, fixtures.voice)
    await storage.save_file(music_key, fixtures.music)

    updates = {
        "original_video_key": video_key,
        "srt_key": srt_key,
        "voice_key": voice_key,
        "music_key": music_key,
    }

    video_path = await storage.get_path(video_key)
    if ffmpeg.is_available():
        try:
            updates["duration_ms"] = ffmpeg.get_duration_ms(video_path)
        except Exception:
            pass

    await _repo.update_video(video_id, **updates)

    for lang_code in settings.supported_languages:
        await _repo.create_video_language(video_id, lang_code)

    return video_id, _sha256(video_path)


async def _poll_video_status(video_id: uuid.UUID, timeout_sec: int = 600):
    terminal = {VideoStatus.READY_FOR_REVIEW, VideoStatus.REQUIRES_REVIEW, VideoStatus.FAILED}
    for _ in range(timeout_sec):
        video = await _repo.get_video(video_id)
        if video and video.status in terminal:
            return video
        await asyncio.sleep(1)
    raise TimeoutError(f"Pipeline did not finish within {timeout_sec}s")


async def _get_segments(video_id: uuid.UUID, lang_code: str):
    lang = await _repo.get_video_language(video_id, lang_code)
    if not lang:
        return []
    return await _repo.list_segments(lang.id)


async def _print_full_report(video_id, fixtures, original_sha, video) -> list[str]:
    settings = get_settings()
    errors: list[str] = []
    warnings: list[str] = []

    print("\n=== E2E Pipeline Report ===")
    print("\nINPUT FILES")
    for label, path in [("video", fixtures.video), ("srt", fixtures.srt), ("voice", fixtures.voice), ("music", fixtures.music)]:
        sha = _sha256(path) if path.exists() else "missing"
        print(f"  {label}: {path} ({_file_size(path)} bytes, sha256={sha[:16]}...)")

    print("\nTRANSLATION RESULTS")
    for lang_code in SUPPORTED_LANGS:
        segments = await _get_segments(video_id, lang_code)
        print(f"  {lang_code}:")
        for seg in segments:
            text = (seg.translated_text or seg.source_text or "")[:80]
            print(f"    [seg{seg.sequence}] \"{text}\"")

    print("\nGENERATED FILES")
    storage_root = Path(settings.storage_dir) / "video" / str(video_id)
    for subdir in ("subtitle", "audio"):
        dir_path = storage_root / subdir
        if dir_path.exists():
            for f in sorted(dir_path.iterdir()):
                print(f"  {subdir}/{f.name} ({_file_size(f)} bytes)")

    print("\nPROCESSING JOBS")
    jobs = await _repo.list_jobs(video_id)
    for job in jobs:
        lang = f"/{job.language_code}" if job.language_code else ""
        print(f"  {job.stage}{lang}: {job.status.value}")

    print(f"\nFINAL STATUS: {video.status.value}")

    original_path = storage_root / "original.mp4"
    if original_path.exists():
        after_sha = _sha256(original_path)
        intact = after_sha == original_sha
        print(f"ORIGINAL MP4 INTEGRITY: {'unchanged' if intact else 'MODIFIED'}")
        if not intact:
            errors.append("Original MP4 was modified")
    else:
        errors.append("Original MP4 missing from storage")

    return errors


async def _assert_success(video_id, original_sha, video) -> list[str]:
    settings = get_settings()
    ffmpeg = FFmpegService()
    errors: list[str] = []

    if video.status == VideoStatus.FAILED:
        errors.append("Pipeline failed (status=failed)")
    elif video.status not in (VideoStatus.READY_FOR_REVIEW, VideoStatus.REQUIRES_REVIEW):
        errors.append(f"Unexpected status: {video.status.value}")

    langs = await _repo.list_video_languages(video_id)
    if len(langs) != 4:
        errors.append(f"Expected 4 languages, got {len(langs)}")
    for lang in langs:
        if lang.status != LanguageStatus.COMPLETED:
            errors.append(f"Language {lang.language_code} status={lang.status.value}")

    storage_root = Path(settings.storage_dir) / "video" / str(video_id)
    for short in ["vi", "en", "ru", "zh"]:
        vtt = storage_root / "subtitle" / f"{short}.vtt"
        if not vtt.exists():
            errors.append(f"Missing subtitle: {vtt}")
        audio = storage_root / "audio" / f"{short}.mp3"
        if not audio.exists():
            errors.append(f"Missing audio: {audio}")
        else:
            try:
                if ffmpeg.get_duration_ms(audio) <= 0:
                    errors.append(f"Audio has zero duration: {audio}")
            except Exception as exc:
                errors.append(f"Cannot read audio duration {audio}: {exc}")

    jobs = {(j.stage, j.language_code): j.status for j in await _repo.list_jobs(video_id)}
    for stage in TARGET_STAGES:
        if jobs.get((stage, None)) != JobStatus.COMPLETED:
            errors.append(f"Job {stage} not completed")

    for lang_code in settings.target_languages:
        for stage in PER_LANG_STAGES:
            if jobs.get((stage, lang_code)) != JobStatus.COMPLETED:
                errors.append(f"Job {stage}/{lang_code} not completed")

    original_path = storage_root / "original.mp4"
    if original_path.exists() and _sha256(original_path) != original_sha:
        errors.append("Original MP4 SHA-256 changed")

    return errors


async def main() -> int:
    settings = get_settings()
    use_mock = os.getenv("E2E_MOCK_TRANSLATION", "").lower() in ("1", "true", "yes")

    if not settings.openai_api_key and not use_mock:
        print("ERROR: OPENAI_API_KEY is not set. Set E2E_MOCK_TRANSLATION=1 for stub.")
        return 1

    if use_mock:
        import app.workers.pipeline_worker as pw
        from tests.stub_translation import StubTranslationProvider
        pw.get_translation_provider = lambda: StubTranslationProvider()
        print("NOTE: Using stub translations (E2E_MOCK_TRANSLATION=1)")

    ffmpeg = FFmpegService()
    if not ffmpeg.is_available():
        print("ERROR: FFmpeg is not available on PATH")
        return 1

    fixture_dir = Path(_E2E_TMP) / "fixtures"
    fixtures = generate_fixtures(fixture_dir)
    await ensure_admin_user(_repo)

    storage = get_storage()
    video_id, original_sha = await _create_video_record(fixtures, storage, ffmpeg)
    print(f"Created video {video_id}")

    await run_pipeline(str(video_id))
    video = await _poll_video_status(video_id)
    report_errors = await _print_full_report(video_id, fixtures, original_sha, video)
    assert_errors = await _assert_success(video_id, original_sha, video)

    all_errors = report_errors + assert_errors
    if all_errors:
        print(f"\n=== E2E FAILED ({len(all_errors)} errors) ===")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("\n=== E2E PASSED ===")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(asyncio.run(main()))
