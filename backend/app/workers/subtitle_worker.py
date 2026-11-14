"""Background subtitle-only translation pipeline.

Generated translations remain drafts in ``ready_for_review`` until an admin
approves them. Target languages run concurrently to shorten the wait, while
batches within each language stay sequential to avoid provider rate limits.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.integrations.supabase.database import get_repository
from app.models.db import JobStatus, LanguageStatus, VideoStatus
from app.services.storage.local import get_storage
from app.services.subtitle.parser import segments_to_vtt
from app.services.translation.base import SegmentInput, TranslationContext
from app.services.translation.factory import get_translation_provider

logger = logging.getLogger(__name__)

TARGET_LANGUAGES = ("en-US", "ru-RU", "zh-CN")
BATCH_SIZE = 12
_active_tasks: dict[str, asyncio.Task] = {}


def is_subtitle_pipeline_active(video_id: str) -> bool:
    task = _active_tasks.get(video_id)
    return task is not None and not task.done()


async def _write_vtt(video_id, language, segments, storage, repo) -> None:
    short = language.language_code.split("-")[0]
    key = f"video/{video_id}/subtitle/{short}.vtt"
    data = segments_to_vtt([
        {
            "sequence": item.sequence,
            "start_ms": item.start_ms,
            "end_ms": item.end_ms,
            "translated_text": item.translated_text or item.source_text,
        }
        for item in segments
    ])
    await storage.save_file(key, data.encode("utf-8"))
    await repo.update_video_language(language.id, subtitle_key=key, status=LanguageStatus.READY_FOR_REVIEW)


async def _translate_language(*, video_id, run_id, video, source_segments, language_code, provider, repo, storage) -> bool:
    """Translate one target language and persist determinate batch progress."""
    language = await repo.get_video_language(video_id, language_code)
    if not language:
        language = await repo.create_video_language(video_id, language_code)
    await repo.update_video_language(language.id, status=LanguageStatus.PROCESSING)
    await repo.upsert_job(video_id, run_id, "translate", language_code, JobStatus.RUNNING, 0)

    try:
        translated = []
        total_segments = len(source_segments)
        for offset in range(0, total_segments, BATCH_SIZE):
            batch = source_segments[offset:offset + BATCH_SIZE]
            outputs = await provider.translate_batch(
                [SegmentInput(sequence=item.sequence, start_ms=item.start_ms, end_ms=item.end_ms,
                              source_text=item.source_text or item.translated_text) for item in batch],
                TranslationContext(title=video.title, description=video.description, target_language=language_code),
            )
            translated.extend(outputs)
            await repo.upsert_job(
                video_id, run_id, "translate", language_code, JobStatus.RUNNING,
                min(90, round(len(translated) / total_segments * 90)),
            )

        await repo.delete_segments_for_language(language.id)
        await repo.create_segments([
            {"video_language_id": str(language.id), "sequence": item.sequence,
             "start_ms": item.start_ms, "end_ms": item.end_ms,
             "source_text": item.source_text, "translated_text": item.translated_text}
            for item in translated
        ])
        language.segments = await repo.list_segments(language.id)
        await _write_vtt(video_id, language, language.segments, storage, repo)
        await repo.upsert_job(video_id, run_id, "translate", language_code, JobStatus.COMPLETED, 100)
        return True
    except Exception as exc:
        logger.exception("Subtitle translation failed for %s / %s", video_id, language_code)
        detail = str(exc)
        if getattr(exc, "status_code", None) == 429 or "rate limit" in detail.lower():
            detail = "Groq rate limit reached. Please wait and try again, or upload an SRT manually."
        await repo.update_video_language(language.id, status=LanguageStatus.FAILED)
        await repo.upsert_job(video_id, run_id, "translate", language_code, JobStatus.FAILED, 0, detail)
        return False


async def run_subtitle_pipeline(video_id: str, language_codes: list[str] | None = None) -> None:
    repo = get_repository()
    storage = get_storage()
    vid = uuid.UUID(video_id)
    run_id = uuid.uuid4()
    targets = [code for code in (language_codes or TARGET_LANGUAGES) if code != "vi-VN"]

    try:
        video = await repo.get_video(vid)
        if not video:
            raise ValueError("Video not found")
        source_language = await repo.get_video_language(vid, "vi-VN")
        if not source_language:
            raise ValueError("Vietnamese subtitle track is missing")
        source_segments = await repo.list_segments(source_language.id)
        if not source_segments:
            raise ValueError("Vietnamese subtitle has no cues")
        if not targets:
            await repo.update_video(vid, status=VideoStatus.READY_FOR_REVIEW)
            return

        provider = get_translation_provider()
        results = await asyncio.gather(*[
            _translate_language(video_id=vid, run_id=run_id, video=video, source_segments=source_segments,
                                language_code=code, provider=provider, repo=repo, storage=storage)
            for code in targets
        ])
        all_succeeded = all(results)
        await repo.update_video(vid, status=VideoStatus.READY_FOR_REVIEW if all_succeeded else VideoStatus.REQUIRES_REVIEW)
        await repo.upsert_job(
            vid, run_id, "finalize", None,
            JobStatus.COMPLETED if all_succeeded else JobStatus.FAILED,
            100, None if all_succeeded else "One or more subtitle translations failed.",
        )
    except Exception as exc:
        logger.exception("Subtitle translation pipeline failed for %s", video_id)
        await repo.update_video(vid, status=VideoStatus.FAILED)
        await repo.upsert_job(vid, run_id, "finalize", None, JobStatus.FAILED, 0, str(exc))


def start_subtitle_pipeline(video_id: str, language_codes: list[str] | None = None) -> None:
    if is_subtitle_pipeline_active(video_id):
        return
    task = asyncio.create_task(run_subtitle_pipeline(video_id, language_codes))
    _active_tasks[video_id] = task

    def _cleanup(done: asyncio.Task) -> None:
        _active_tasks.pop(video_id, None)
        if not done.cancelled() and done.exception():
            logger.error("Subtitle pipeline task failed: %s", done.exception())

    task.add_done_callback(_cleanup)
