from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class VideoStatus(str, Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    READY_FOR_REVIEW = "ready_for_review"
    PUBLISHED = "published"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


class LanguageStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VideoLanguageResponse(BaseModel):
    language_code: str
    subtitle_url: str | None = None
    audio_url: str | None = None
    status: LanguageStatus

    model_config = {"from_attributes": True}


class VideoResponse(BaseModel):
    id: UUID
    title: str
    description: str
    status: VideoStatus
    duration_ms: int | None = None
    thumbnail_url: str | None = None
    video_url: str | None = None
    languages: list[VideoLanguageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int


class ProcessingJobResponse(BaseModel):
    id: UUID
    pipeline_run_id: UUID
    stage: str
    language_code: str | None
    status: JobStatus
    progress: int
    error_message: str | None
    retry_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VideoCreateResponse(BaseModel):
    id: UUID
    title: str
    status: VideoStatus
    message: str = "Video created successfully"


class GenerateResponse(BaseModel):
    message: str
    video_id: UUID


class PreviewResponse(BaseModel):
    video_id: UUID
    status: VideoStatus
    video_url: str | None
    thumbnail_url: str | None
    languages: list[VideoLanguageResponse]
    jobs: list[ProcessingJobResponse]


class QRResponse(BaseModel):
    url: str
    qr_image_base64: str
