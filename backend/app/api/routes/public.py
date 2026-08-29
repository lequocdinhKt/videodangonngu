from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.core.deps import get_repo
from app.integrations.supabase.database import SupabaseRepository
from app.models.db import Video, VideoStatus
from app.schemas.video import VideoLanguageResponse, VideoListResponse, VideoResponse
from app.services.storage.local import get_storage

router = APIRouter(prefix="/api", tags=["public"])

LANG_CODE_MAP = {"vi": "vi-VN", "en": "en-US", "ru": "ru-RU", "zh": "zh-CN"}


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


async def _require_published_video(repo: SupabaseRepository, video_id: UUID) -> Video:
    video = await repo.get_video(video_id)
    if not video or video.status != VideoStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/videos", response_model=VideoListResponse)
async def list_published_videos(repo: Annotated[SupabaseRepository, Depends(get_repo)]):
    storage = get_storage()
    videos = await repo.list_videos(status=VideoStatus.PUBLISHED)
    items = []
    for v in videos:
        v.languages = await repo.list_video_languages(v.id, with_audio=True)
        items.append(await _video_response(v, storage))
    return VideoListResponse(items=items, total=len(items))


@router.get("/videos/{video_id}", response_model=VideoResponse)
async def get_video(video_id: UUID, repo: Annotated[SupabaseRepository, Depends(get_repo)]):
    storage = get_storage()
    video = await _require_published_video(repo, video_id)
    video.languages = await repo.list_video_languages(video_id, with_audio=True)
    return await _video_response(video, storage)


@router.get("/videos/{video_id}/subtitles/{lang}.vtt")
async def get_subtitle(
    video_id: UUID,
    lang: str,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
):
    await _require_published_video(repo, video_id)
    lang_code = LANG_CODE_MAP.get(lang, lang)
    vl = await repo.get_video_language(video_id, lang_code)
    if not vl or not vl.subtitle_key:
        raise HTTPException(status_code=404, detail="Subtitle not found")
    storage = get_storage()
    signed = await storage.get_signed_url(vl.subtitle_key)
    return RedirectResponse(url=signed, status_code=302)


@router.get("/videos/{video_id}/audio/{lang}.mp3")
async def get_audio(
    video_id: UUID,
    lang: str,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
):
    await _require_published_video(repo, video_id)
    lang_code = LANG_CODE_MAP.get(lang, lang)
    vl = await repo.get_video_language(video_id, lang_code)
    if not vl:
        raise HTTPException(status_code=404, detail="Audio not found")
    audio = await repo.get_audio_track(vl.id)
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    storage = get_storage()
    signed = await storage.get_signed_url(audio.audio_key)
    return RedirectResponse(url=signed, status_code=302)
