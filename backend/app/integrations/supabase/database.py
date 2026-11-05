"""Supabase database repository — centralized data access."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.integrations.supabase.client import get_supabase_client
from app.models.db import (
    AudioTrack,
    JobStatus,
    LanguageStatus,
    ProcessingJob,
    SubtitleSegment,
    User,
    Video,
    VideoLanguage,
    VideoStatus,
    VideoTranslation,
)

logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    """Raised when a DB operation did not affect or return the expected row."""


def _single_row(resp: Any, *, entity: str, entity_id: str) -> dict[str, Any]:
    if resp.data:
        return resp.data[0]
    raise RepositoryError(f"{entity} returned no rows for id={entity_id}")


def _parse_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _parse_dt(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _row_to_user(row: dict[str, Any]) -> User:
    return User(
        id=_parse_uuid(row["id"]),
        email=row["email"],
        password_hash=row["password_hash"],
        role=row.get("role", "admin"),
        created_at=_parse_dt(row.get("created_at")),
    )


def _row_to_video(row: dict[str, Any]) -> Video:
    return Video(
        id=_parse_uuid(row["id"]),
        title=row["title"],
        description=row.get("description", ""),
        original_video_key=row.get("original_video_key"),
        thumbnail_key=row.get("thumbnail_key"),
        voice_key=row.get("voice_key"),
        music_key=row.get("music_key"),
        srt_key=row.get("srt_key"),
        duration_ms=row.get("duration_ms"),
        status=VideoStatus(row["status"]),
        result_meta=row.get("result_meta"),
        created_by=_parse_uuid(row.get("created_by")),
        created_at=_parse_dt(row.get("created_at")),
        updated_at=_parse_dt(row.get("updated_at")),
    )


def _row_to_language(row: dict[str, Any]) -> VideoLanguage:
    return VideoLanguage(
        id=_parse_uuid(row["id"]),
        video_id=_parse_uuid(row["video_id"]),
        language_code=row["language_code"],
        subtitle_key=row.get("subtitle_key"),
        status=LanguageStatus(row["status"]),
        created_at=_parse_dt(row.get("created_at")),
        updated_at=_parse_dt(row.get("updated_at")),
    )


def _row_to_translation(row: dict[str, Any]) -> VideoTranslation:
    return VideoTranslation(
        id=_parse_uuid(row["id"]),
        video_id=_parse_uuid(row["video_id"]),
        language_code=row["language_code"],
        title=row["title"],
        description=row.get("description", ""),
        created_at=_parse_dt(row.get("created_at")),
        updated_at=_parse_dt(row.get("updated_at")),
    )


def _row_to_segment(row: dict[str, Any]) -> SubtitleSegment:
    return SubtitleSegment(
        id=_parse_uuid(row["id"]),
        video_language_id=_parse_uuid(row["video_language_id"]),
        sequence=row["sequence"],
        start_ms=row["start_ms"],
        end_ms=row["end_ms"],
        source_text=row.get("source_text", ""),
        translated_text=row.get("translated_text", ""),
        alignment_meta=row.get("alignment_meta"),
    )


def _row_to_audio(row: dict[str, Any]) -> AudioTrack:
    return AudioTrack(
        id=_parse_uuid(row["id"]),
        video_language_id=_parse_uuid(row["video_language_id"]),
        audio_key=row["audio_key"],
        duration_ms=row.get("duration_ms"),
        mix_config=row.get("mix_config"),
    )


def _row_to_job(row: dict[str, Any]) -> ProcessingJob:
    return ProcessingJob(
        id=_parse_uuid(row["id"]),
        video_id=_parse_uuid(row["video_id"]),
        pipeline_run_id=_parse_uuid(row["pipeline_run_id"]),
        stage=row["stage"],
        language_code=row.get("language_code"),
        status=JobStatus(row["status"]),
        progress=row.get("progress", 0),
        error_message=row.get("error_message"),
        retry_count=row.get("retry_count", 0),
        started_at=_parse_dt(row.get("started_at")),
        completed_at=_parse_dt(row.get("completed_at")),
        created_at=_parse_dt(row.get("created_at")),
        updated_at=_parse_dt(row.get("updated_at")),
    )


class SupabaseRepository:
    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    async def _run(self, fn):
        return await asyncio.to_thread(fn)

    # --- Users ---

    async def get_user_by_email(self, email: str) -> User | None:
        def _query():
            resp = self.client.table("users").select("*").eq("email", email).limit(1).execute()
            return resp.data[0] if resp.data else None

        row = await self._run(_query)
        return _row_to_user(row) if row else None

    async def create_user(self, email: str, password_hash: str, role: str = "admin") -> User:
        payload = {"email": email, "password_hash": password_hash, "role": role}

        def _insert():
            resp = self.client.table("users").insert(payload).execute()
            return resp.data[0]

        return _row_to_user(await self._run(_insert))

    # --- Videos ---

    async def create_video(
        self,
        title: str,
        description: str,
        created_by: uuid.UUID,
        status: VideoStatus = VideoStatus.DRAFT,
    ) -> Video:
        payload = {
            "title": title,
            "description": description,
            "created_by": str(created_by),
            "status": status.value,
        }

        def _insert():
            resp = self.client.table("videos").insert(payload).execute()
            return resp.data[0]

        return _row_to_video(await self._run(_insert))

    async def get_video(self, video_id: uuid.UUID) -> Video | None:
        def _query():
            resp = self.client.table("videos").select("*").eq("id", str(video_id)).limit(1).execute()
            return resp.data[0] if resp.data else None

        row = await self._run(_query)
        return _row_to_video(row) if row else None

    async def get_video_with_relations(self, video_id: uuid.UUID) -> Video | None:
        video = await self.get_video(video_id)
        if not video:
            return None
        video.languages = await self.list_video_languages(video_id, with_segments=False)
        video.translations = await self.list_video_translations(video_id)
        video.jobs = await self.list_jobs(video_id)
        return video

    async def list_videos(self, status: VideoStatus | None = None) -> list[Video]:
        def _query():
            q = self.client.table("videos").select("*").order("created_at", desc=True)
            if status is not None:
                q = q.eq("status", status.value)
            return q.execute().data

        rows = await self._run(_query)
        return [_row_to_video(r) for r in rows]

    async def update_video(self, video_id: uuid.UUID, **fields: Any) -> Video:
        payload = dict(fields)
        if "status" in payload and isinstance(payload["status"], VideoStatus):
            payload["status"] = payload["status"].value
        if "created_by" in payload and payload["created_by"] is not None:
            payload["created_by"] = str(payload["created_by"])
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        vid = str(video_id)

        def _update():
            resp = (
                self.client.table("videos")
                .update(payload)
                .eq("id", vid)
                .select("*")
                .execute()
            )
            logger.info(
                "update_video id=%s fields=%s returned_rows=%d",
                vid,
                sorted(payload.keys()),
                len(resp.data or []),
            )
            return _single_row(resp, entity="Video", entity_id=vid)

        return _row_to_video(await self._run(_update))

    async def delete_video(self, video_id: uuid.UUID) -> None:
        def _delete():
            self.client.table("videos").delete().eq("id", str(video_id)).execute()

        await self._run(_delete)

    # --- Localized titles and descriptions ---

    async def upsert_video_translation(
        self,
        video_id: uuid.UUID,
        language_code: str,
        title: str,
        description: str = "",
    ) -> VideoTranslation:
        payload = {
            "video_id": str(video_id),
            "language_code": language_code,
            "title": title,
            "description": description,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        def _upsert():
            resp = self.client.table("video_translations").upsert(
                payload, on_conflict="video_id,language_code"
            ).execute()
            return resp.data[0]

        return _row_to_translation(await self._run(_upsert))

    async def list_video_translations(self, video_id: uuid.UUID) -> list[VideoTranslation]:
        def _query():
            return (
                self.client.table("video_translations")
                .select("*")
                .eq("video_id", str(video_id))
                .execute()
                .data
            )

        return [_row_to_translation(row) for row in await self._run(_query)]

    async def get_video_translation(
        self, video_id: uuid.UUID, language_code: str
    ) -> VideoTranslation | None:
        def _query():
            resp = (
                self.client.table("video_translations")
                .select("*")
                .eq("video_id", str(video_id))
                .eq("language_code", language_code)
                .limit(1)
                .execute()
            )
            return resp.data[0] if resp.data else None

        row = await self._run(_query)
        return _row_to_translation(row) if row else None

    # --- Video languages ---

    async def create_video_language(
        self,
        video_id: uuid.UUID,
        language_code: str,
        status: LanguageStatus = LanguageStatus.PENDING,
    ) -> VideoLanguage:
        payload = {
            "video_id": str(video_id),
            "language_code": language_code,
            "status": status.value,
        }

        def _insert():
            resp = self.client.table("video_languages").insert(payload).execute()
            return resp.data[0]

        return _row_to_language(await self._run(_insert))

    async def get_video_language(
        self, video_id: uuid.UUID, language_code: str
    ) -> VideoLanguage | None:
        def _query():
            resp = (
                self.client.table("video_languages")
                .select("*")
                .eq("video_id", str(video_id))
                .eq("language_code", language_code)
                .limit(1)
                .execute()
            )
            return resp.data[0] if resp.data else None

        row = await self._run(_query)
        return _row_to_language(row) if row else None

    async def list_video_languages(
        self,
        video_id: uuid.UUID,
        *,
        with_segments: bool = False,
        with_audio: bool = False,
        language_codes: list[str] | None = None,
    ) -> list[VideoLanguage]:
        def _query():
            q = self.client.table("video_languages").select("*").eq("video_id", str(video_id))
            if language_codes:
                q = q.in_("language_code", language_codes)
            return q.execute().data

        langs = [_row_to_language(r) for r in await self._run(_query)]
        for lang in langs:
            if with_audio:
                lang.audio_track = await self.get_audio_track(lang.id)
            if with_segments:
                lang.segments = await self.list_segments(lang.id)
        return langs

    async def update_video_language(self, lang_id: uuid.UUID, **fields: Any) -> VideoLanguage:
        payload = dict(fields)
        if "status" in payload and isinstance(payload["status"], LanguageStatus):
            payload["status"] = payload["status"].value
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()

        def _update():
            resp = (
                self.client.table("video_languages")
                .update(payload)
                .eq("id", str(lang_id))
                .select("*")
                .execute()
            )
            return _single_row(resp, entity="VideoLanguage", entity_id=str(lang_id))

        return _row_to_language(await self._run(_update))

    # --- Subtitle segments ---

    async def delete_segments_for_language(self, video_language_id: uuid.UUID) -> None:
        def _delete():
            self.client.table("subtitle_segments").delete().eq(
                "video_language_id", str(video_language_id)
            ).execute()

        await self._run(_delete)

    async def create_segments(self, segments: list[dict[str, Any]]) -> None:
        if not segments:
            return

        def _insert():
            self.client.table("subtitle_segments").insert(segments).execute()

        await self._run(_insert)

    async def list_segments(self, video_language_id: uuid.UUID) -> list[SubtitleSegment]:
        def _query():
            resp = (
                self.client.table("subtitle_segments")
                .select("*")
                .eq("video_language_id", str(video_language_id))
                .order("sequence")
                .execute()
            )
            return resp.data

        return [_row_to_segment(r) for r in await self._run(_query)]

    async def update_segment(self, segment_id: uuid.UUID, **fields: Any) -> None:
        def _update():
            self.client.table("subtitle_segments").update(fields).eq("id", str(segment_id)).execute()

        await self._run(_update)

    async def get_segment_by_sequence(
        self, video_language_id: uuid.UUID, sequence: int
    ) -> SubtitleSegment | None:
        def _query():
            resp = (
                self.client.table("subtitle_segments")
                .select("*")
                .eq("video_language_id", str(video_language_id))
                .eq("sequence", sequence)
                .limit(1)
                .execute()
            )
            return resp.data[0] if resp.data else None

        row = await self._run(_query)
        return _row_to_segment(row) if row else None

    # --- Audio tracks ---

    async def get_audio_track(self, video_language_id: uuid.UUID) -> AudioTrack | None:
        def _query():
            resp = (
                self.client.table("audio_tracks")
                .select("*")
                .eq("video_language_id", str(video_language_id))
                .limit(1)
                .execute()
            )
            return resp.data[0] if resp.data else None

        row = await self._run(_query)
        return _row_to_audio(row) if row else None

    async def upsert_audio_track(
        self,
        video_language_id: uuid.UUID,
        audio_key: str,
        duration_ms: int | None,
        mix_config: dict[str, Any] | None,
    ) -> AudioTrack:
        existing = await self.get_audio_track(video_language_id)
        payload = {
            "video_language_id": str(video_language_id),
            "audio_key": audio_key,
            "duration_ms": duration_ms,
            "mix_config": mix_config,
        }

        def _upsert():
            if existing:
                resp = (
                    self.client.table("audio_tracks")
                    .update(payload)
                    .eq("id", str(existing.id))
                    .select("*")
                    .execute()
                )
            else:
                resp = self.client.table("audio_tracks").insert(payload).execute()
            return _single_row(resp, entity="AudioTrack", entity_id=str(existing.id if existing else video_language_id))

        return _row_to_audio(await self._run(_upsert))

    # --- Processing jobs ---

    async def upsert_job(
        self,
        video_id: uuid.UUID,
        pipeline_run_id: uuid.UUID,
        stage: str,
        language_code: str | None,
        status: JobStatus,
        progress: int,
        error_message: str | None = None,
    ) -> ProcessingJob:
        now = datetime.now(timezone.utc).isoformat()
        existing = await self.get_job(video_id, pipeline_run_id, stage, language_code)
        payload: dict[str, Any] = {
            "video_id": str(video_id),
            "pipeline_run_id": str(pipeline_run_id),
            "stage": stage,
            "language_code": language_code,
            "status": status.value,
            "progress": progress,
            "error_message": error_message,
            "updated_at": now,
        }
        if status == JobStatus.RUNNING and (not existing or not existing.started_at):
            payload["started_at"] = now
        if status in (JobStatus.COMPLETED, JobStatus.FAILED):
            payload["completed_at"] = now

        def _write():
            if existing:
                resp = (
                    self.client.table("processing_jobs")
                    .update(payload)
                    .eq("id", str(existing.id))
                    .select("*")
                    .execute()
                )
                entity_id = str(existing.id)
            else:
                resp = self.client.table("processing_jobs").insert(payload).execute()
                entity_id = str(video_id)
            return _single_row(resp, entity="ProcessingJob", entity_id=entity_id)

        return _row_to_job(await self._run(_write))

    async def get_job(
        self,
        video_id: uuid.UUID,
        pipeline_run_id: uuid.UUID,
        stage: str,
        language_code: str | None,
    ) -> ProcessingJob | None:
        def _query():
            q = (
                self.client.table("processing_jobs")
                .select("*")
                .eq("video_id", str(video_id))
                .eq("pipeline_run_id", str(pipeline_run_id))
                .eq("stage", stage)
            )
            if language_code is None:
                q = q.is_("language_code", "null")
            else:
                q = q.eq("language_code", language_code)
            resp = q.limit(1).execute()
            return resp.data[0] if resp.data else None

        row = await self._run(_query)
        return _row_to_job(row) if row else None

    async def get_finalize_job(self, video_id: uuid.UUID) -> ProcessingJob | None:
        def _query():
            resp = (
                self.client.table("processing_jobs")
                .select("*")
                .eq("video_id", str(video_id))
                .eq("stage", "finalize")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            return resp.data[0] if resp.data else None

        row = await self._run(_query)
        return _row_to_job(row) if row else None

    async def list_jobs(self, video_id: uuid.UUID) -> list[ProcessingJob]:
        def _query():
            resp = (
                self.client.table("processing_jobs")
                .select("*")
                .eq("video_id", str(video_id))
                .order("created_at")
                .execute()
            )
            return resp.data

        return [_row_to_job(r) for r in await self._run(_query)]


_repo: SupabaseRepository | None = None


def get_repository() -> SupabaseRepository:
    global _repo
    if _repo is None:
        _repo = SupabaseRepository()
    return _repo


def reset_repository() -> None:
    global _repo
    _repo = None
