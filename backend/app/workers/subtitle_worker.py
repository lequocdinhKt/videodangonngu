"""Background subtitle-only translation pipeline.

Audio/TTS processing intentionally does not run here. Generated translations are
drafts and remain in ``ready_for_review`` until an admin approves them.
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


async def _write_vtt(video_id, lang, segments, storage, repo) -> None:
    short = lang.language_code.split("-")[0]
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
    await repo.update_video_language(
        lang.id,
        subtitle_key=key,
        status=LanguageStatus.READY_FOR_REVIEW,
    )


async def run_subtitle_pipeline(video_id: str, language_codes: list[str] | None = None) -> None:
    repo = get_repository()
    storage = get_storage()
    vid = uuid.UUID(video_id)
    run_id = uuid.uuid4()
    targets = [code for code in (language_codes or TARGET_LANGUAGES) if code != "vi-VN"]

    current_language: str | None = None
    try:
        video = await repo.get_video(vid)
        if not video:
            raise ValueError("Video not found")
        source_lang = await repo.get_video_language(vid, "vi-VN")
        if not source_lang:
            raise ValueError("Vietnamese subtitle track is missing")
        source_segments = await repo.list_segments(source_lang.id)
        if not source_segments:
            raise ValueError("Vietnamese subtitle has no cues")

        provider = get_translation_provider()
        total_targets = max(len(targets), 1)
        for target_index, code in enumerate(targets):
            current_language = code
            target = await repo.get_video_language(vid, code)
            if not target:
                target = await repo.create_video_language(vid, code)
            await repo.update_video_language(target.id, status=LanguageStatus.PROCESSING)
            await repo.upsert_job(
                vid, run_id, "translate", code, JobStatus.RUNNING,
                10 + int(target_index / total_targets * 70),
            )

            translated = []
            for offset in range(0, len(source_segments), BATCH_SIZE):
                batch = source_segments[offset:offset + BATCH_SIZE]
                outputs = await provider.translate_batch(
                    [
                        SegmentInput(
                            sequence=item.sequence,
                            start_ms=item.start_ms,
                            end_ms=item.end_ms,
                            source_text=item.source_text or item.translated_text,
                        )
                        for item in batch
                    ],
                    TranslationContext(
                        title=video.title,
                        description=video.description,
                        target_language=code,
                    ),
                )
                translated.extend(outputs)

            await repo.delete_segments_for_language(target.id)
            await repo.create_segments([
                {
                    "video_language_id": str(target.id),
                    "sequence": item.sequence,
                    "start_ms": item.start_ms,
                    "end_ms": item.end_ms,
                    "source_text": item.source_text,
                    "translated_text": item.translated_text,
                }
                for item in translated
            ])
            target.segments = await repo.list_segments(target.id)
            await _write_vtt(vid, target, target.segments, storage, repo)
            await repo.upsert_job(
                vid, run_id, "translate", code, JobStatus.COMPLETED,
                20 + int((target_index + 1) / total_targets * 70),
            )

        await repo.update_video(vid, status=VideoStatus.READY_FOR_REVIEW)
        await repo.upsert_job(vid, run_id, "finalize", None, JobStatus.COMPLETED, 100)
    except Exception as exc:
        logger.exception("Subtitle translation failed for %s", video_id)
        detail = str(exc)
        status_code = getattr(exc, "status_code", None)
        if status_code == 429 or "rate limit" in detail.lower():
            detail = "Groq rate limit reached. Please wait and try again, or upload an SRT manually."
        if current_language:
            language = await repo.get_video_language(vid, current_language)
            if language:
                await repo.update_video_language(language.id, status=LanguageStatus.FAILED)
        await repo.update_video(vid, status=VideoStatus.FAILED)
        await repo.upsert_job(
            vid, run_id, "translate", current_language, JobStatus.FAILED, 0, detail
        )


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
