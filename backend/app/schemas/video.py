from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


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
    READY_FOR_REVIEW = "ready_for_review"
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


class VideoTranslationInput(BaseModel):
    language_code: str
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=5000)


class VideoTranslationResponse(VideoTranslationInput):
    model_config = {"from_attributes": True}


class VideoDraftCreate(BaseModel):
    translations: list[VideoTranslationInput]

    @field_validator("translations")
    @classmethod
    def validate_translations(cls, value: list[VideoTranslationInput]):
        codes = [item.language_code for item in value]
        if "vi-VN" not in codes:
            raise ValueError("Vietnamese title and description are required")
        if len(codes) != len(set(codes)):
            raise ValueError("Duplicate translation language")
        return value


class VideoLanguageResponse(BaseModel):
    language_code: str
    subtitle_url: str | None = None
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
    translations: list[VideoTranslationResponse] = Field(default_factory=list)
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
    message: str = "Video draft created"


class GenerateResponse(BaseModel):
    message: str
    video_id: UUID


class PreviewResponse(BaseModel):
    video_id: UUID
    status: VideoStatus
    title: str
    description: str
    video_url: str | None
    thumbnail_url: str | None
    languages: list[VideoLanguageResponse]
    translations: list[VideoTranslationResponse]
    jobs: list[ProcessingJobResponse]


class UploadUrlRequest(BaseModel):
    kind: Literal["video", "thumbnail", "subtitle"]
    filename: str
    content_type: str
    size_bytes: int = Field(gt=0)
    language_code: str | None = None


class UploadUrlResponse(BaseModel):
    key: str
    upload_url: str | None = None
    fallback_url: str | None = None
    method: Literal["PUT", "POST"]
    headers: dict[str, str] = Field(default_factory=dict)


class AssetCompleteRequest(BaseModel):
    kind: Literal["video", "thumbnail", "subtitle"]
    key: str
    language_code: str | None = None


class SubtitleCue(BaseModel):
    id: UUID | None = None
    sequence: int = Field(gt=0)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str = Field(max_length=4000)

    @field_validator("end_ms")
    @classmethod
    def end_after_start(cls, value: int, info):
        start = info.data.get("start_ms")
        if start is not None and value <= start:
            raise ValueError("end_ms must be greater than start_ms")
        return value


class SubtitleCuesResponse(BaseModel):
    language_code: str
    status: LanguageStatus
    cues: list[SubtitleCue]


class SubtitleCuesUpdate(BaseModel):
    cues: list[SubtitleCue]
    approved: bool = False


class QRResponse(BaseModel):
    url: str
    qr_image_base64: str
    qr_svg_base64: str
