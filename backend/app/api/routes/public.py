from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse

from app.config.settings import get_settings
from app.core.deps import get_repo
from app.integrations.supabase.database import SupabaseRepository
from app.models.db import Video, VideoStatus
from app.schemas.video import (
    VideoLanguageResponse,
    VideoListResponse,
    VideoResponse,
    VideoTranslationResponse,
)
from app.services.storage.local import get_storage

router = APIRouter(prefix="/api", tags=["public"])

LANG_CODE_MAP = {"vi": "vi-VN", "en": "en-US", "ru": "ru-RU", "zh": "zh-CN"}
SUPPORTED_LANGUAGES = tuple(LANG_CODE_MAP.values())


def _normalize_language(value: str) -> str:
    code = LANG_CODE_MAP.get(value, value)
    return code if code in SUPPORTED_LANGUAGES else "vi-VN"


def _localized_text(video: Video, language_code: str) -> tuple[str, str]:
    selected = next((item for item in video.translations if item.language_code == language_code), None)
    fallback = next((item for item in video.translations if item.language_code == "vi-VN"), None)
    item = selected or fallback
    return (item.title, item.description) if item else (video.title, video.description)


async def _video_response(video: Video, language_code: str) -> VideoResponse:
    storage = get_storage()
    title, description = _localized_text(video, language_code)
    local_storage = get_settings().storage_provider == "local"
    return VideoResponse(
        id=video.id,
        title=title,
        description=description,
        status=video.status,
        duration_ms=video.duration_ms,
        thumbnail_url=(
            f"/api/videos/{video.id}/stream/thumbnail" if local_storage
            else await storage.get_url(video.thumbnail_key)
        ) if video.thumbnail_key else None,
        video_url=(
            f"/api/videos/{video.id}/stream/original" if local_storage
            else await storage.get_url(video.original_video_key)
        ) if video.original_video_key else None,
        languages=[VideoLanguageResponse(
            language_code=item.language_code,
            subtitle_url=(
                f"/api/videos/{video.id}/subtitles/{item.language_code}.vtt"
                if item.subtitle_key else None
            ),
            status=item.status,
        ) for item in video.languages if item.subtitle_key],
        translations=[VideoTranslationResponse.model_validate(item) for item in video.translations],
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


async def _require_published_video(repo: SupabaseRepository, video_id: UUID) -> Video:
    video = await repo.get_video(video_id)
    if not video or video.status != VideoStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/videos", response_model=VideoListResponse)
async def list_published_videos(
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    lang: str = Query("vi-VN"),
):
    code = _normalize_language(lang)
    videos = await repo.list_videos(status=VideoStatus.PUBLISHED)
    items = []
    for video in videos:
        video.languages = await repo.list_video_languages(video.id)
        video.translations = await repo.list_video_translations(video.id)
        items.append(await _video_response(video, code))
    return VideoListResponse(items=items, total=len(items))


@router.get("/videos/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    lang: str = Query("vi-VN"),
):
    video = await _require_published_video(repo, video_id)
    video.languages = await repo.list_video_languages(video_id)
    video.translations = await repo.list_video_translations(video_id)
    return await _video_response(video, _normalize_language(lang))


@router.get("/videos/{video_id}/subtitles/{lang}.vtt")
async def get_subtitle(
    video_id: UUID,
    lang: str,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
):
    await _require_published_video(repo, video_id)
    code = _normalize_language(lang)
    language = await repo.get_video_language(video_id, code)
    if not language or not language.subtitle_key:
        raise HTTPException(status_code=404, detail="Subtitle not found")
    storage = get_storage()
    if get_settings().storage_provider == "local":
        return FileResponse(await storage.get_path(language.subtitle_key), media_type="text/vtt")
    signed = await storage.get_signed_url(language.subtitle_key)
    return RedirectResponse(url=signed, status_code=302)


@router.get("/videos/{video_id}/stream/original")
async def stream_original(video_id: UUID, repo: Annotated[SupabaseRepository, Depends(get_repo)]):
    video = await _require_published_video(repo, video_id)
    if not video.original_video_key or get_settings().storage_provider != "local":
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(await get_storage().get_path(video.original_video_key), media_type="video/mp4")


@router.get("/videos/{video_id}/stream/thumbnail")
async def stream_thumbnail(video_id: UUID, repo: Annotated[SupabaseRepository, Depends(get_repo)]):
    video = await _require_published_video(repo, video_id)
    if not video.thumbnail_key or get_settings().storage_provider != "local":
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(await get_storage().get_path(video.thumbnail_key))
