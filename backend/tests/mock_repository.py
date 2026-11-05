"""In-memory repository for unit tests — no Supabase required."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any

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
)


class InMemoryRepository:
  def __init__(self) -> None:
    self.users: dict[uuid.UUID, dict] = {}
    self.videos: dict[uuid.UUID, dict] = {}
    self.languages: dict[uuid.UUID, dict] = {}
    self.segments: dict[uuid.UUID, dict] = {}
    self.audio: dict[uuid.UUID, dict] = {}
    self.jobs: dict[uuid.UUID, dict] = {}
    self.translations: dict[tuple[uuid.UUID, str], dict] = {}

  async def get_user_by_email(self, email: str) -> User | None:
    for row in self.users.values():
      if row["email"] == email:
        return User(id=row["id"], email=row["email"], password_hash=row["password_hash"], role=row.get("role", "admin"))
    return None

  async def create_user(self, email: str, password_hash: str, role: str = "admin") -> User:
    uid = uuid.uuid4()
    self.users[uid] = {"id": uid, "email": email, "password_hash": password_hash, "role": role}
    return await self.get_user_by_email(email)

  async def create_video(
    self,
    title: str,
    description: str,
    created_by: uuid.UUID,
    status: VideoStatus = VideoStatus.DRAFT,
    video_id: uuid.UUID | None = None,
    **extra: Any,
  ) -> Video:
    vid = video_id or uuid.uuid4()
    now = datetime.now(timezone.utc)
    self.videos[vid] = {
      "id": vid, "title": title, "description": description, "created_by": created_by,
      "status": status.value, "created_at": now, "updated_at": now, **extra,
    }
    return self._video(vid)

  def _video(self, vid: uuid.UUID) -> Video:
    r = self.videos[vid]
    return Video(
      id=r["id"], title=r["title"], description=r.get("description", ""),
      original_video_key=r.get("original_video_key"), thumbnail_key=r.get("thumbnail_key"),
      voice_key=r.get("voice_key"), music_key=r.get("music_key"), srt_key=r.get("srt_key"),
      duration_ms=r.get("duration_ms"), status=VideoStatus(r["status"]),
      result_meta=r.get("result_meta"), created_by=r.get("created_by"),
      created_at=r.get("created_at"), updated_at=r.get("updated_at"),
    )

  async def get_video(self, video_id: uuid.UUID) -> Video | None:
    return self._video(video_id) if video_id in self.videos else None

  async def get_video_with_relations(self, video_id: uuid.UUID) -> Video | None:
    v = await self.get_video(video_id)
    if not v:
      return None
    v.languages = await self.list_video_languages(video_id)
    v.translations = await self.list_video_translations(video_id)
    v.jobs = await self.list_jobs(video_id)
    return v

  async def list_videos(self, status: VideoStatus | None = None) -> list[Video]:
    out = []
    for vid in self.videos:
      v = self._video(vid)
      if status is None or v.status == status:
        out.append(v)
    return out

  async def update_video(self, video_id: uuid.UUID, **fields: Any) -> Video:
    row = self.videos[video_id]
    for k, v in fields.items():
      row[k] = v.value if isinstance(v, VideoStatus) else v
    row["updated_at"] = datetime.now(timezone.utc)
    return self._video(video_id)

  async def delete_video(self, video_id: uuid.UUID) -> None:
    self.videos.pop(video_id, None)

  async def upsert_video_translation(self, video_id, language_code, title, description=""):
    from app.models.db import VideoTranslation
    key = (video_id, language_code)
    row = self.translations.get(key, {"id": uuid.uuid4(), "video_id": video_id, "language_code": language_code})
    row.update({"title": title, "description": description})
    self.translations[key] = row
    return VideoTranslation(**row)

  async def list_video_translations(self, video_id):
    from app.models.db import VideoTranslation
    return [VideoTranslation(**row) for (vid, _), row in self.translations.items() if vid == video_id]

  async def get_video_translation(self, video_id, language_code):
    from app.models.db import VideoTranslation
    row = self.translations.get((video_id, language_code))
    return VideoTranslation(**row) if row else None

  async def create_video_language(self, video_id: uuid.UUID, language_code: str, status: LanguageStatus = LanguageStatus.PENDING) -> VideoLanguage:
    lid = uuid.uuid4()
    self.languages[lid] = {
      "id": lid, "video_id": video_id, "language_code": language_code, "status": status.value,
    }
    return self._lang(lid)

  def _lang(self, lid: uuid.UUID) -> VideoLanguage:
    r = self.languages[lid]
    return VideoLanguage(
      id=r["id"], video_id=r["video_id"], language_code=r["language_code"],
      subtitle_key=r.get("subtitle_key"), status=LanguageStatus(r["status"]),
    )

  async def get_video_language(self, video_id: uuid.UUID, language_code: str) -> VideoLanguage | None:
    for lid, r in self.languages.items():
      if r["video_id"] == video_id and r["language_code"] == language_code:
        return self._lang(lid)
    return None

  async def list_video_languages(self, video_id, *, with_segments=False, with_audio=False, language_codes=None) -> list[VideoLanguage]:
    langs = []
    for lid, r in self.languages.items():
      if r["video_id"] != video_id:
        continue
      if language_codes and r["language_code"] not in language_codes:
        continue
      lang = self._lang(lid)
      if with_audio:
        lang.audio_track = await self.get_audio_track(lid)
      if with_segments:
        lang.segments = await self.list_segments(lid)
      langs.append(lang)
    return langs

  async def update_video_language(self, lang_id: uuid.UUID, **fields: Any) -> VideoLanguage:
    row = self.languages[lang_id]
    for k, v in fields.items():
      row[k] = v.value if isinstance(v, LanguageStatus) else v
    return self._lang(lang_id)

  async def delete_segments_for_language(self, video_language_id: uuid.UUID) -> None:
    to_del = [sid for sid, s in self.segments.items() if s["video_language_id"] == video_language_id]
    for sid in to_del:
      del self.segments[sid]

  async def create_segments(self, segments: list[dict]) -> None:
    for seg in segments:
      sid = uuid.uuid4()
      self.segments[sid] = {**seg, "id": sid}

  async def list_segments(self, video_language_id: uuid.UUID) -> list[SubtitleSegment]:
    segs = [s for s in self.segments.values() if s["video_language_id"] == str(video_language_id) or s["video_language_id"] == video_language_id]
    segs.sort(key=lambda x: x["sequence"])
    return [SubtitleSegment(
      id=s["id"], video_language_id=uuid.UUID(str(s["video_language_id"])),
      sequence=s["sequence"], start_ms=s["start_ms"], end_ms=s["end_ms"],
      source_text=s.get("source_text", ""), translated_text=s.get("translated_text", ""),
      alignment_meta=s.get("alignment_meta"),
    ) for s in segs]

  async def update_segment(self, segment_id: uuid.UUID, **fields: Any) -> None:
    self.segments[segment_id].update(fields)

  async def get_segment_by_sequence(self, video_language_id: uuid.UUID, sequence: int) -> SubtitleSegment | None:
    for s in self.segments.values():
      vlid = s["video_language_id"]
      if (vlid == video_language_id or str(vlid) == str(video_language_id)) and s["sequence"] == sequence:
        return SubtitleSegment(
          id=s["id"], video_language_id=uuid.UUID(str(vlid)),
          sequence=s["sequence"], start_ms=s["start_ms"], end_ms=s["end_ms"],
          source_text=s.get("source_text", ""), translated_text=s.get("translated_text", ""),
        )
    return None

  async def get_audio_track(self, video_language_id: uuid.UUID) -> AudioTrack | None:
    for a in self.audio.values():
      if a["video_language_id"] == video_language_id:
        return AudioTrack(id=a["id"], video_language_id=a["video_language_id"], audio_key=a["audio_key"],
                          duration_ms=a.get("duration_ms"), mix_config=a.get("mix_config"))
    return None

  async def upsert_audio_track(self, video_language_id, audio_key, duration_ms, mix_config) -> AudioTrack:
    existing = await self.get_audio_track(video_language_id)
    if existing:
      self.audio[existing.id].update({"audio_key": audio_key, "duration_ms": duration_ms, "mix_config": mix_config})
      return await self.get_audio_track(video_language_id)
    aid = uuid.uuid4()
    self.audio[aid] = {"id": aid, "video_language_id": video_language_id, "audio_key": audio_key,
                      "duration_ms": duration_ms, "mix_config": mix_config}
    return await self.get_audio_track(video_language_id)

  async def upsert_job(self, video_id, pipeline_run_id, stage, language_code, status, progress, error_message=None) -> ProcessingJob:
    for j in self.jobs.values():
      if (j["video_id"] == video_id and j["pipeline_run_id"] == pipeline_run_id
          and j["stage"] == stage and j.get("language_code") == language_code):
        j.update({"status": status.value, "progress": progress, "error_message": error_message})
        return self._job(j)
    jid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    self.jobs[jid] = {
      "id": jid, "video_id": video_id, "pipeline_run_id": pipeline_run_id,
      "stage": stage, "language_code": language_code, "status": status.value,
      "progress": progress, "error_message": error_message, "retry_count": 0,
      "created_at": now, "updated_at": now,
    }
    return self._job(self.jobs[jid])

  def _job(self, j: dict) -> ProcessingJob:
    return ProcessingJob(
      id=j["id"], video_id=j["video_id"], pipeline_run_id=j["pipeline_run_id"],
      stage=j["stage"], language_code=j.get("language_code"), status=JobStatus(j["status"]),
      progress=j["progress"], error_message=j.get("error_message"), retry_count=j.get("retry_count", 0),
      started_at=j.get("started_at"), completed_at=j.get("completed_at"), created_at=j.get("created_at"),
    )

  async def get_job(self, video_id, pipeline_run_id, stage, language_code):
    for j in self.jobs.values():
      if j["video_id"] == video_id and j["pipeline_run_id"] == pipeline_run_id and j["stage"] == stage and j.get("language_code") == language_code:
        return self._job(j)
    return None

  async def get_finalize_job(self, video_id: uuid.UUID) -> ProcessingJob | None:
    jobs = [j for j in self.jobs.values() if j["video_id"] == video_id and j["stage"] == "finalize"]
    if not jobs:
      return None
    return self._job(jobs[-1])

  async def list_jobs(self, video_id: uuid.UUID) -> list[ProcessingJob]:
    return [self._job(j) for j in self.jobs.values() if j["video_id"] == video_id]
