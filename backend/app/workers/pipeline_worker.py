import asyncio
import json
import re
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

from app.config.logging import get_logger
from app.config.settings import get_settings
from app.integrations.supabase.database import get_repository
from app.models.db import (
    JobStatus,
    LanguageStatus,
    ProcessingStage,
    VideoStatus,
)
from app.services.audio.alignment import AlignmentResult, apply_alignment
from app.services.audio.ffmpeg_service import FFmpegService
from app.services.audio.timeline import assemble_language_track
from app.services.audio.workspace import cleanup_workspace, compute_timeline_duration_ms, workspace_root
from app.services.storage.local import get_storage
from app.services.subtitle.parser import parse_srt, segments_to_vtt
from app.services.subtitle.validator import validate_translation
from app.services.translation.base import SegmentInput, SegmentOutput, TranslationContext
from app.services.translation.factory import get_translation_provider
from app.services.tts.cache import TTSCache
from app.services.tts.edge_tts_engine import get_tts_engine, get_voice_for_language

logger = get_logger(__name__)

_active_tasks: dict[str, asyncio.Task] = {}


def is_pipeline_active(video_id: str) -> bool:
    task = _active_tasks.get(video_id)
    return task is not None and not task.done()

TRANSLATION_BATCH_SIZE = 12
TRANSLATION_CONTEXT_OVERLAP = 3


async def _load_existing_quality_flags(video_id: uuid.UUID) -> list[str]:
    repo = get_repository()
    job = await repo.get_finalize_job(video_id)
    if not job or not job.error_message:
        return []
    try:
        payload = json.loads(job.error_message)
        flags = payload.get("quality_flags", [])
        return flags if isinstance(flags, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _flag_belongs_to_language(flag: str, lang_code: str) -> bool:
    return f":{lang_code}:" in flag or flag.endswith(f":{lang_code}")


def _merge_quality_flags(existing: list[str], new_flags: list[str], regenerated_langs: list[str]) -> list[str]:
    if not regenerated_langs:
        return existing + new_flags
    kept = [
        flag for flag in existing
        if not any(_flag_belongs_to_language(flag, lang) for lang in regenerated_langs)
    ]
    return kept + new_flags


def _extract_topic(video) -> str:
    text = f"{video.title} {video.description}".strip()
    if not text:
        return ""
    words = re.findall(r"[A-Za-zÀ-ỹ]{4,}", text)
    return " ".join(dict.fromkeys(words[:8]))


def _extract_proper_nouns(video, segments: list) -> list[str]:
    nouns: list[str] = []
    title_words = re.findall(r"[A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+)*", video.title or "")
    nouns.extend(title_words)
    for seg in segments:
        for match in re.findall(
            r"[A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+)*",
            getattr(seg, "source_text", "") or "",
        ):
            if match not in nouns:
                nouns.append(match)
    return nouns[:20]


def _build_glossary(video) -> dict[str, str]:
    glossary: dict[str, str] = {}
    if video.title:
        glossary[video.title] = video.title
    return glossary


def _segment_dict(seg) -> dict:
    return {
        "sequence": seg.sequence,
        "start_ms": seg.start_ms,
        "end_ms": seg.end_ms,
        "source_text": seg.source_text,
    }


def _build_translation_context(
    video,
    lang_code: str,
    vi_segments: list,
    batch_start: int,
    batch_end: int,
    *,
    concise: bool = False,
) -> TranslationContext:
    preceding = [_segment_dict(s) for s in vi_segments[max(0, batch_start - TRANSLATION_CONTEXT_OVERLAP):batch_start]]
    following = [
        _segment_dict(s)
        for s in vi_segments[batch_end:min(len(vi_segments), batch_end + TRANSLATION_CONTEXT_OVERLAP)]
    ]
    return TranslationContext(
        title=video.title,
        description=video.description,
        topic=_extract_topic(video),
        glossary=_build_glossary(video),
        proper_nouns=_extract_proper_nouns(video, vi_segments),
        target_language=lang_code,
        preceding_segments=preceding,
        following_segments=following,
        concise=concise,
    )


async def _translate_segments(
    translator,
    video,
    lang_code: str,
    vi_segments: list,
    *,
    concise: bool = False,
    on_batch: Callable[[int, int], Awaitable[None]] | None = None,
) -> list[SegmentOutput]:
    all_translated: list[SegmentOutput] = []
    total = len(vi_segments)
    for i in range(0, total, TRANSLATION_BATCH_SIZE):
        if on_batch:
            await on_batch(i, total)
        batch = vi_segments[i:i + TRANSLATION_BATCH_SIZE]
        context = _build_translation_context(
            video, lang_code, vi_segments, i, i + len(batch), concise=concise,
        )
        inputs = [
            SegmentInput(sequence=s.sequence, start_ms=s.start_ms, end_ms=s.end_ms, source_text=s.source_text)
            for s in batch
        ]
        outputs = await translator.translate_batch(inputs, context)
        all_translated.extend(outputs)
    return all_translated


async def _get_vi_segments(video_id: uuid.UUID) -> list:
    repo = get_repository()
    vi_lang = await repo.get_video_language(video_id, "vi-VN")
    if not vi_lang:
        return []
    return await repo.list_segments(vi_lang.id)


async def run_pipeline(video_id: str, language_codes: list[str] | None = None) -> None:
    settings = get_settings()
    storage = get_storage()
    ffmpeg = FFmpegService()
    tts = get_tts_engine()
    cache = TTSCache()
    translator = get_translation_provider()
    repo = get_repository()
    vid = uuid.UUID(video_id)
    pipeline_run_id = uuid.uuid4()
    is_regenerate = bool(language_codes)
    langs_to_process = language_codes or settings.target_languages

    video = await repo.get_video_with_relations(vid)
    if not video:
        logger.error("Video %s not found", video_id)
        return

    existing_flags = await _load_existing_quality_flags(vid) if is_regenerate else []
    await repo.update_video(vid, status=VideoStatus.PROCESSING)

    if not is_regenerate:
        await repo.upsert_job(
            vid, pipeline_run_id, ProcessingStage.PARSE.value, None,
            JobStatus.RUNNING, 5,
        )

    quality_flags: list[str] = []

    try:
        if is_regenerate:
            vi_segments = await _get_vi_segments(vid)
            if not vi_segments:
                raise RuntimeError("Cannot regenerate: Vietnamese subtitle segments not found")
            srt_end_ms = max((s.end_ms for s in vi_segments), default=0)
        else:
            await repo.upsert_job(
                vid, pipeline_run_id, ProcessingStage.PARSE.value, None,
                JobStatus.RUNNING, 10,
            )

            srt_path = await storage.get_path(video.srt_key)
            srt_content = srt_path.read_text(encoding="utf-8-sig")
            subtitles, _ = parse_srt(srt_content)

            vi_lang = await repo.get_video_language(vid, "vi-VN")
            if not vi_lang:
                vi_lang = await repo.create_video_language(vid, "vi-VN", LanguageStatus.PROCESSING)
            else:
                await repo.update_video_language(vi_lang.id, status=LanguageStatus.PROCESSING)

            await repo.delete_segments_for_language(vi_lang.id)
            await repo.create_segments([
                {
                    "video_language_id": str(vi_lang.id),
                    "sequence": sub.index,
                    "start_ms": sub.start_ms,
                    "end_ms": sub.end_ms,
                    "source_text": sub.text,
                    "translated_text": sub.text,
                }
                for sub in subtitles
            ])
            await repo.upsert_job(
                vid, pipeline_run_id, ProcessingStage.PARSE.value, None,
                JobStatus.COMPLETED, 18,
            )
            srt_end_ms = subtitles[-1].end_ms if subtitles else 0

        total_ms = compute_timeline_duration_ms(video.duration_ms, srt_end_ms)

        for lang_idx, lang_code in enumerate(langs_to_process):
            base_progress = 20 + int((lang_idx / max(len(langs_to_process), 1)) * 70)
            lang_flags = await _process_language(
                vid, video, lang_code, total_ms, pipeline_run_id,
                storage, ffmpeg, tts, cache, translator, base_progress,
            )
            quality_flags.extend(lang_flags)

        if not is_regenerate:
            vi_flags = await _finalize_vietnamese(vid, video, total_ms, storage, ffmpeg)
            quality_flags.extend(vi_flags)
            await _export_subtitles(vid, storage, pipeline_run_id)
        else:
            await _export_subtitles(vid, storage, pipeline_run_id, language_codes=langs_to_process)

        merged_flags = _merge_quality_flags(existing_flags, quality_flags, langs_to_process if is_regenerate else [])
        new_status = VideoStatus.REQUIRES_REVIEW if merged_flags else VideoStatus.READY_FOR_REVIEW
        await repo.update_video(vid, status=new_status, result_meta={"quality_flags": merged_flags} if merged_flags else None)

        finalize_msg = json.dumps({"quality_flags": merged_flags}) if merged_flags else None
        await repo.upsert_job(
            vid, pipeline_run_id, ProcessingStage.FINALIZE.value, None,
            JobStatus.COMPLETED, 100, finalize_msg,
        )
        logger.info("Pipeline complete for video %s (status=%s)", video_id, new_status.value)

    except Exception as exc:
        logger.exception("Pipeline failed for video %s: %s", video_id, exc)
        await repo.update_video(vid, status=VideoStatus.FAILED)
        await repo.upsert_job(
            vid, pipeline_run_id, ProcessingStage.FINALIZE.value, None,
            JobStatus.FAILED, 0, str(exc),
        )
    finally:
        cleanup_workspace(vid)


async def _process_language(
    vid, video, lang_code, total_ms, pipeline_run_id,
    storage, ffmpeg, tts, cache, translator, base_progress,
) -> list[str]:
    repo = get_repository()
    quality_flags: list[str] = []
    settings = get_settings()

    await repo.upsert_job(
        vid, pipeline_run_id, ProcessingStage.TRANSLATE.value, lang_code,
        JobStatus.RUNNING, base_progress,
    )

    lang = await repo.get_video_language(vid, lang_code)
    if not lang:
        lang = await repo.create_video_language(vid, lang_code, LanguageStatus.PROCESSING)
    else:
        await repo.update_video_language(lang.id, status=LanguageStatus.PROCESSING)

    vi_segments = await _get_vi_segments(vid)
    if not vi_segments:
        raise RuntimeError(f"No Vietnamese segments available for translating {lang_code}")

    async def _on_translate_batch(batch_start: int, total: int) -> None:
        pct = base_progress + int((batch_start / max(total, 1)) * 8)
        await repo.upsert_job(
            vid, pipeline_run_id, ProcessingStage.TRANSLATE.value, lang_code,
            JobStatus.RUNNING, pct,
        )

    all_translated = await _translate_segments(
        translator, video, lang_code, vi_segments, on_batch=_on_translate_batch,
    )

    source_dicts = [
        {"sequence": s.sequence, "start_ms": s.start_ms, "end_ms": s.end_ms, "source_text": s.source_text}
        for s in vi_segments
    ]
    trans_dicts = [
        {"sequence": t.sequence, "start_ms": t.start_ms, "end_ms": t.end_ms, "translated_text": t.translated_text}
        for t in all_translated
    ]

    await repo.upsert_job(
        vid, pipeline_run_id, ProcessingStage.VALIDATE.value, lang_code,
        JobStatus.RUNNING, base_progress + 3,
    )

    validation = validate_translation(source_dicts, trans_dicts)
    if not validation.valid:
        logger.warning("Translation validation failed for %s: %s", lang_code, validation.errors)
        all_translated = await _translate_segments(translator, video, lang_code, vi_segments)
        trans_dicts = [
            {"sequence": t.sequence, "start_ms": t.start_ms, "end_ms": t.end_ms, "translated_text": t.translated_text}
            for t in all_translated
        ]
        retry_validation = validate_translation(source_dicts, trans_dicts)
        if not retry_validation.valid:
            logger.warning("Translation validation still failing for %s: %s", lang_code, retry_validation.errors)
            quality_flags.append(f"validation_failed:{lang_code}")

    await repo.upsert_job(
        vid, pipeline_run_id, ProcessingStage.VALIDATE.value, lang_code,
        JobStatus.COMPLETED, base_progress + 5,
    )

    await repo.delete_segments_for_language(lang.id)
    translated_by_seq = {t.sequence: t for t in all_translated}
    await repo.create_segments([
        {
            "video_language_id": str(lang.id),
            "sequence": t.sequence,
            "start_ms": t.start_ms,
            "end_ms": t.end_ms,
            "source_text": next((s.source_text for s in vi_segments if s.sequence == t.sequence), ""),
            "translated_text": t.translated_text,
        }
        for t in all_translated
    ])

    await repo.upsert_job(
        vid, pipeline_run_id, ProcessingStage.TRANSLATE.value, lang_code,
        JobStatus.COMPLETED, base_progress + 10,
    )

    workspace = workspace_root(vid) / "segments" / lang_code
    workspace.mkdir(parents=True, exist_ok=True)
    voice = get_voice_for_language(lang_code)
    segment_paths: dict[int, Path] = {}

    await repo.upsert_job(
        vid, pipeline_run_id, ProcessingStage.TTS.value, lang_code,
        JobStatus.RUNNING, base_progress + 15,
    )

    total_segments = len(all_translated)
    for seg_idx, t in enumerate(all_translated):
        if seg_idx == 0 or seg_idx == total_segments - 1 or seg_idx % 5 == 0:
            pct = base_progress + 15 + int((seg_idx / max(total_segments, 1)) * 10)
            await repo.upsert_job(
                vid, pipeline_run_id, ProcessingStage.TTS.value, lang_code,
                JobStatus.RUNNING, pct,
            )
        raw_path = workspace / f"{t.sequence:05d}_raw.mp3"
        final_path = workspace / f"{t.sequence:05d}_final.mp3"
        cached = cache.get_cached(tts.provider_name, lang_code, voice, t.translated_text)
        if cached:
            raw_path = cached
        else:
            await tts.synthesize(t.translated_text, lang_code, voice, raw_path)
            await cache.store(tts.provider_name, lang_code, voice, t.translated_text, raw_path)

        target_ms = t.end_ms - t.start_ms
        align_result = apply_alignment(ffmpeg, raw_path, final_path, target_ms)

        if align_result.status == "needs_retranslate":
            concise_ctx = _build_translation_context(
                video, lang_code, vi_segments, 0, len(vi_segments), concise=True,
            )
            shorter = await translator.translate_batch(
                [SegmentInput(sequence=t.sequence, start_ms=t.start_ms, end_ms=t.end_ms, source_text=t.source_text)],
                concise_ctx,
            )
            if shorter:
                t = shorter[0]
                translated_by_seq[t.sequence] = t
                await tts.synthesize(t.translated_text, lang_code, voice, raw_path)
                align_result = apply_alignment(ffmpeg, raw_path, final_path, target_ms)

        if align_result.status == "needs_retranslate":
            quality_flags.append(f"alignment_failed:{lang_code}:seg{t.sequence}")
            align_result = AlignmentResult(
                speed_factor=1.0,
                silence_added_ms=float(target_ms),
                status="alignment_failed",
                warning=align_result.warning,
                final_duration_ms=target_ms,
                tts_duration_ms=align_result.tts_duration_ms,
                target_duration_ms=target_ms,
            )
            ffmpeg.generate_silence(final_path, target_ms)
        elif align_result.status == "warning":
            quality_flags.append(f"alignment_warning:{lang_code}:seg{t.sequence}")

        segment_paths[t.sequence] = final_path

        seg = await repo.get_segment_by_sequence(lang.id, t.sequence)
        if seg:
            await repo.update_segment(seg.id, translated_text=t.translated_text, alignment_meta={
                "speed_factor": align_result.speed_factor,
                "tts_duration_ms": align_result.tts_duration_ms,
                "target_duration_ms": align_result.target_duration_ms,
                "status": align_result.status,
                "warning": align_result.warning,
            })

    await repo.upsert_job(
        vid, pipeline_run_id, ProcessingStage.TTS.value, lang_code,
        JobStatus.COMPLETED, base_progress + 25,
    )
    await repo.upsert_job(
        vid, pipeline_run_id, ProcessingStage.ALIGN.value, lang_code,
        JobStatus.COMPLETED, base_progress + 30,
    )

    seg_dicts = [{"sequence": t.sequence, "start_ms": t.start_ms, "end_ms": t.end_ms} for t in all_translated]
    voice_track = workspace_root(vid) / f"voice_{lang_code}.mp3"
    assemble_language_track(ffmpeg, seg_dicts, segment_paths, total_ms, voice_track)

    if settings.voice_normalize:
        normalized = workspace_root(vid) / f"voice_{lang_code}_norm.mp3"
        ffmpeg.normalize_audio(voice_track, normalized)
        voice_track = normalized

    final_audio_key = f"video/{vid}/audio/{lang_code.split('-')[0]}.mp3"
    mix_config: dict = {"mixed": False}

    if video.music_key:
        music_path = await storage.get_path(video.music_key)
        mixed = workspace_root(vid) / f"mixed_{lang_code}.mp3"
        ffmpeg.mix_voice_and_music(voice_track, music_path, mixed, settings.music_volume_db, duration_ms=total_ms)
        await storage.save_file(final_audio_key, mixed)
        mix_config = {
            "music_key": video.music_key,
            "music_volume_db": settings.music_volume_db,
            "mixed": True,
            "timeline_duration_ms": total_ms,
        }
    else:
        if ffmpeg.get_duration_ms(voice_track) != total_ms:
            trimmed = workspace_root(vid) / f"voice_{lang_code}_trimmed.mp3"
            ffmpeg.trim_to_duration(voice_track, trimmed, total_ms)
            voice_track = trimmed
        await storage.save_file(final_audio_key, voice_track)

    final_path = await storage.get_path(final_audio_key)
    await repo.upsert_audio_track(
        lang.id, final_audio_key, ffmpeg.get_duration_ms(final_path), mix_config,
    )
    await repo.update_video_language(lang.id, status=LanguageStatus.COMPLETED)

    await repo.upsert_job(
        vid, pipeline_run_id, ProcessingStage.MIX.value, lang_code,
        JobStatus.COMPLETED, base_progress + 40,
    )
    return quality_flags


async def _finalize_vietnamese(vid, video, total_ms, storage, ffmpeg) -> list[str]:
    repo = get_repository()
    quality_flags: list[str] = []
    settings = get_settings()
    vi_lang = await repo.get_video_language(vid, "vi-VN")
    if not vi_lang:
        return quality_flags

    ws = workspace_root(vid)
    vi_key = f"video/{vid}/audio/vi.mp3"
    mix_config: dict = {"mixed": False}

    if video.voice_key:
        voice_path = await storage.get_path(video.voice_key)
        if settings.voice_normalize:
            normalized = ws / "vi_voice_norm.mp3"
            ffmpeg.normalize_audio(voice_path, normalized)
            voice_path = normalized
        if video.music_key:
            music_path = await storage.get_path(video.music_key)
            mixed = ws / "vi_mixed.mp3"
            ffmpeg.mix_voice_and_music(
                voice_path, music_path, mixed, settings.music_volume_db, duration_ms=total_ms,
            )
            await storage.save_file(vi_key, mixed)
            mix_config = {
                "music_key": video.music_key,
                "music_volume_db": settings.music_volume_db,
                "mixed": True,
                "timeline_duration_ms": total_ms,
            }
        else:
            trimmed = ws / "vi_voice_trimmed.mp3"
            ffmpeg.trim_to_duration(voice_path, trimmed, total_ms)
            await storage.save_file(vi_key, trimmed)
    elif video.original_video_key and settings.voice_separation_enabled:
        quality_flags.append("voice_fallback_extracted")
        extracted = ws / "extracted_audio.mp3"
        video_path = await storage.get_path(video.original_video_key)
        ffmpeg.extract_audio(video_path, extracted)
        trimmed = ws / "vi_extracted_trimmed.mp3"
        ffmpeg.trim_to_duration(extracted, trimmed, total_ms)
        await storage.save_file(vi_key, trimmed)
    elif video.original_video_key:
        quality_flags.append("voice_separation_disabled")
        extracted = ws / "extracted_audio.mp3"
        video_path = await storage.get_path(video.original_video_key)
        ffmpeg.extract_audio(video_path, extracted)
        trimmed = ws / "vi_extracted_trimmed.mp3"
        ffmpeg.trim_to_duration(extracted, trimmed, total_ms)
        await storage.save_file(vi_key, trimmed)

    final_path = await storage.get_path(vi_key)
    if final_path.exists():
        await repo.upsert_audio_track(
            vi_lang.id, vi_key, ffmpeg.get_duration_ms(final_path), mix_config,
        )
        await repo.update_video_language(vi_lang.id, status=LanguageStatus.COMPLETED)

    return quality_flags


async def _export_subtitles(
    vid, storage, pipeline_run_id: uuid.UUID, language_codes: list[str] | None = None,
) -> None:
    repo = get_repository()
    await repo.upsert_job(
        vid, pipeline_run_id, ProcessingStage.SUBTITLE_EXPORT.value, None,
        JobStatus.RUNNING, 90,
    )

    langs = await repo.list_video_languages(
        vid, with_segments=True, language_codes=language_codes,
    )
    for lang in langs:
        segments = sorted(lang.segments, key=lambda s: s.sequence)
        vtt_data = segments_to_vtt([
            {
                "sequence": s.sequence,
                "start_ms": s.start_ms,
                "end_ms": s.end_ms,
                "translated_text": s.translated_text or s.source_text,
            }
            for s in segments
        ])
        lang_short = lang.language_code.split("-")[0]
        key = f"video/{vid}/subtitle/{lang_short}.vtt"
        await storage.save_file(key, vtt_data.encode("utf-8"))
        await repo.update_video_language(lang.id, subtitle_key=key)

    await repo.upsert_job(
        vid, pipeline_run_id, ProcessingStage.SUBTITLE_EXPORT.value, None,
        JobStatus.COMPLETED, 95,
    )


def start_pipeline(video_id: str, language_codes: list[str] | None = None) -> None:
    if is_pipeline_active(video_id):
        return

    settings = get_settings()
    if settings.use_arq:
        async def _enqueue() -> None:
            from arq import create_pool
            from app.workers.arq_worker import WorkerSettings

            redis = await create_pool(WorkerSettings.redis_settings())
            await redis.enqueue_job("process_video", video_id, language_codes)

        asyncio.create_task(_enqueue())
        return

    task = asyncio.create_task(run_pipeline(video_id, language_codes))
    _active_tasks[video_id] = task

    def _cleanup(t: asyncio.Task) -> None:
        _active_tasks.pop(video_id, None)
        if t.exception():
            logger.error("Pipeline task failed for %s: %s", video_id, t.exception())

    task.add_done_callback(_cleanup)
