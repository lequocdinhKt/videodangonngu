"""Domain models and enums — schema contract for Supabase tables."""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class VideoStatus(str, enum.Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    READY_FOR_REVIEW = "ready_for_review"
    PUBLISHED = "published"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


class LanguageStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStage(str, enum.Enum):
    UPLOAD = "upload"
    PARSE = "parse"
    TRANSLATE = "translate"
    VALIDATE = "validate"
    TTS = "tts"
    ALIGN = "align"
    MIX = "mix"
    SUBTITLE_EXPORT = "subtitle_export"
    FINALIZE = "finalize"


@dataclass
class User:
    id: uuid.UUID
    email: str
    password_hash: str
    role: str = "admin"
    created_at: datetime | None = None


@dataclass
class Video:
    id: uuid.UUID
    title: str
    description: str = ""
    original_video_key: str | None = None
    thumbnail_key: str | None = None
    voice_key: str | None = None
    music_key: str | None = None
    srt_key: str | None = None
    duration_ms: int | None = None
    status: VideoStatus = VideoStatus.DRAFT
    result_meta: dict[str, Any] | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    languages: list[VideoLanguage] = field(default_factory=list)
    jobs: list[ProcessingJob] = field(default_factory=list)


@dataclass
class VideoLanguage:
    id: uuid.UUID
    video_id: uuid.UUID
    language_code: str
    subtitle_key: str | None = None
    status: LanguageStatus = LanguageStatus.PENDING
    created_at: datetime | None = None
    updated_at: datetime | None = None
    segments: list[SubtitleSegment] = field(default_factory=list)
    audio_track: AudioTrack | None = None


@dataclass
class SubtitleSegment:
    id: uuid.UUID
    video_language_id: uuid.UUID
    sequence: int
    start_ms: int
    end_ms: int
    source_text: str = ""
    translated_text: str = ""
    alignment_meta: dict[str, Any] | None = None


@dataclass
class AudioTrack:
    id: uuid.UUID
    video_language_id: uuid.UUID
    audio_key: str
    duration_ms: int | None = None
    mix_config: dict[str, Any] | None = None


@dataclass
class ProcessingJob:
    id: uuid.UUID
    video_id: uuid.UUID
    pipeline_run_id: uuid.UUID
    stage: str
    language_code: str | None = None
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    error_message: str | None = None
    retry_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
