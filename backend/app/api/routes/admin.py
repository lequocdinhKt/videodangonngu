import io
import base64
from typing import Annotated
from uuid import UUID

import qrcode
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.config.settings import get_settings
from app.core.auth import create_access_token, get_current_user, verify_password
from app.core.deps import get_repo
from app.integrations.supabase.database import SupabaseRepository
from app.models.db import LanguageStatus, User, Video, VideoLanguage, VideoStatus
from app.schemas.video import (
    GenerateResponse,
    LoginRequest,
    PreviewResponse,
    ProcessingJobResponse,
    QRResponse,
    TokenResponse,
    VideoCreateResponse,
    VideoLanguageResponse,
    VideoListResponse,
    VideoResponse,
)
from app.services.audio.ffmpeg_service import FFmpegService
from app.services.storage.local import get_storage
from app.workers.pipeline_worker import start_pipeline

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def _video_response(video: Video, storage) -> VideoResponse:
    langs = []
    for lang in video.languages:
        audio_url = None
        if lang.audio_track:
            audio_url = await storage.get_url(lang.audio_track.audio_key)
        subtitle_url = await storage.get_url(lang.subtitle_key) if lang.subtitle_key else None
        langs.append(
            VideoLanguageResponse(
                language_code=lang.language_code,
                subtitle_url=subtitle_url,
                audio_url=audio_url,
                status=lang.status,
            )
        )
    return VideoResponse(
        id=video.id,
        title=video.title,
        description=video.description,
        status=video.status,
        duration_ms=video.duration_ms,
        thumbnail_url=await storage.get_url(video.thumbnail_key) if video.thumbnail_key else None,
        video_url=await storage.get_url(video.original_video_key) if video.original_video_key else None,
        languages=langs,
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


def _check_upload_size(data: bytes, max_mb: int) -> None:
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {max_mb}MB limit")


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, repo: Annotated[SupabaseRepository, Depends(get_repo)]):
    user = await repo.get_user_by_email(body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.email))


@router.get("/videos", response_model=VideoListResponse)
async def list_videos(
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    storage = get_storage()
    videos = await repo.list_videos()
    items = []
    for v in videos:
        v.languages = await repo.list_video_languages(v.id, with_audio=True)
        items.append(await _video_response(v, storage))
    return VideoListResponse(items=items, total=len(items))


@router.post("/videos", response_model=VideoCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_video(
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    user: User = Depends(get_current_user),
    title: str = Form(...),
    description: str = Form(""),
    video: UploadFile = File(...),
    subtitle: UploadFile = File(...),
    voice: UploadFile | None = File(None),
    music: UploadFile | None = File(None),
):
    settings = get_settings()
    storage = get_storage()
    ffmpeg = FFmpegService()

    if not video.filename or not video.filename.lower().endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Video must be MP4")
    if not subtitle.filename or not subtitle.filename.lower().endswith(".srt"):
        raise HTTPException(status_code=400, detail="Subtitle must be SRT")

    vid = await repo.create_video(title=title, description=description, created_by=user.id)

    video_key = f"video/{vid.id}/original.mp4"
    srt_key = f"video/{vid.id}/source.srt"
    video_data = await video.read()
    srt_data = await subtitle.read()
    _check_upload_size(video_data, settings.max_upload_mb)
    _check_upload_size(srt_data, settings.max_upload_mb)
    await storage.save_file(video_key, video_data)
    await storage.save_file(srt_key, srt_data)

    updates: dict = {"original_video_key": video_key, "srt_key": srt_key}

    if voice and voice.filename:
        voice_key = f"video/{vid.id}/voice_vi.mp3"
        voice_data = await voice.read()
        _check_upload_size(voice_data, settings.max_upload_mb)
        await storage.save_file(voice_key, voice_data)
        updates["voice_key"] = voice_key

    if music and music.filename:
        music_key = f"video/{vid.id}/music.mp3"
        music_data = await music.read()
        _check_upload_size(music_data, settings.max_upload_mb)
        await storage.save_file(music_key, music_data)
        updates["music_key"] = music_key

    video_path = await storage.get_path(video_key)
    if ffmpeg.is_available():
        try:
            updates["duration_ms"] = ffmpeg.get_duration_ms(video_path)
            thumb_key = f"video/{vid.id}/thumbnail.jpg"
            thumb_path = await storage.get_path(thumb_key)
            ffmpeg.extract_thumbnail(video_path, thumb_path)
            await storage.save_file(thumb_key, thumb_path.read_bytes())
            updates["thumbnail_key"] = thumb_key
        except Exception:
            pass

    vid = await repo.update_video(vid.id, **updates)

    for lang_code in settings.supported_languages:
        await repo.create_video_language(vid.id, lang_code)

    return VideoCreateResponse(id=vid.id, title=vid.title, status=vid.status)


@router.post("/videos/{video_id}/generate", response_model=GenerateResponse, status_code=202)
async def generate_video(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    video = await repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    await repo.update_video(video_id, status=VideoStatus.PROCESSING)
    start_pipeline(str(video_id))
    return GenerateResponse(message="Processing started", video_id=video_id)


@router.post("/videos/{video_id}/regenerate/{lang_code}", response_model=GenerateResponse, status_code=202)
async def regenerate_language(
    video_id: UUID,
    lang_code: str,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    video = await repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    await repo.update_video(video_id, status=VideoStatus.PROCESSING)
    start_pipeline(str(video_id), language_codes=[lang_code])
    return GenerateResponse(message=f"Regenerating {lang_code}", video_id=video_id)


@router.get("/videos/{video_id}/jobs", response_model=list[ProcessingJobResponse])
async def get_jobs(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    jobs = await repo.list_jobs(video_id)
    return [ProcessingJobResponse.model_validate(j) for j in jobs]


@router.post("/videos/{video_id}/publish")
async def publish_video(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    video = await repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status not in (VideoStatus.READY_FOR_REVIEW, VideoStatus.DRAFT):
        if video.status != VideoStatus.PUBLISHED:
            raise HTTPException(status_code=400, detail=f"Cannot publish video in status {video.status}")
    await repo.update_video(video_id, status=VideoStatus.PUBLISHED)
    return {"message": "Published", "video_id": str(video_id)}


@router.post("/videos/{video_id}/unpublish")
async def unpublish_video(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    video = await repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    await repo.update_video(video_id, status=VideoStatus.READY_FOR_REVIEW)
    return {"message": "Unpublished", "video_id": str(video_id)}


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    video = await repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    await repo.delete_video(video_id)
    return {"message": "Deleted"}


@router.get("/videos/{video_id}/preview", response_model=PreviewResponse)
async def preview_video(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    storage = get_storage()
    video = await repo.get_video_with_relations(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    langs = []
    for lang in video.languages:
        audio_url = await storage.get_url(lang.audio_track.audio_key) if lang.audio_track else None
        subtitle_url = await storage.get_url(lang.subtitle_key) if lang.subtitle_key else None
        langs.append(
            VideoLanguageResponse(
                language_code=lang.language_code,
                subtitle_url=subtitle_url,
                audio_url=audio_url,
                status=lang.status,
            )
        )

    return PreviewResponse(
        video_id=video.id,
        status=video.status,
        video_url=await storage.get_url(video.original_video_key) if video.original_video_key else None,
        thumbnail_url=await storage.get_url(video.thumbnail_key) if video.thumbnail_key else None,
        languages=langs,
        jobs=[ProcessingJobResponse.model_validate(j) for j in video.jobs],
    )


@router.get("/qr", response_model=QRResponse)
async def get_qr(_: User = Depends(get_current_user)):
    settings = get_settings()
    url = settings.public_base_url
    qr = qrcode.make(url)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return QRResponse(url=url, qr_image_base64=f"data:image/png;base64,{b64}")
