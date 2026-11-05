from __future__ import annotations

import base64
import io
import mimetypes
from pathlib import Path
from typing import Annotated
from uuid import UUID

import qrcode
import qrcode.image.svg
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.config.settings import get_settings
from app.core.auth import create_access_token, get_current_user, verify_password
from app.core.deps import get_repo
from app.integrations.supabase.database import SupabaseRepository
from app.models.db import LanguageStatus, User, Video, VideoStatus
from app.schemas.video import (
    AssetCompleteRequest,
    GenerateResponse,
    LoginRequest,
    PreviewResponse,
    ProcessingJobResponse,
    QRResponse,
    SubtitleCue,
    SubtitleCuesResponse,
    SubtitleCuesUpdate,
    TokenResponse,
    UploadUrlRequest,
    UploadUrlResponse,
    VideoCreateResponse,
    VideoDraftCreate,
    VideoLanguageResponse,
    VideoListResponse,
    VideoResponse,
    VideoTranslationResponse,
)
from app.services.audio.ffmpeg_service import FFmpegService
from app.services.storage.errors import storage_http_exception
from app.services.storage.local import get_storage
from app.services.subtitle.parser import SRTParseError, parse_srt, segments_to_vtt
from app.services.subtitle.validator import validate_srt_structure
from app.services.translation.factory import validate_translation_config
from app.workers.subtitle_worker import is_subtitle_pipeline_active, start_subtitle_pipeline

router = APIRouter(prefix="/api/admin", tags=["admin"])

LANG_CODE_MAP = {"vi": "vi-VN", "en": "en-US", "ru": "ru-RU", "zh": "zh-CN"}
SUPPORTED_LANGUAGES = tuple(LANG_CODE_MAP.values())
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_SUBTITLE_TYPES = {
    "application/x-subrip",
    "application/octet-stream",
    "text/plain",
    "text/srt",
}


def _admin_stream_url(video_id: UUID, resource: str, lang_code: str | None = None) -> str:
    if resource in {"original", "thumbnail"}:
        return f"/api/admin/videos/{video_id}/stream/{resource}"
    if resource == "subtitle" and lang_code:
        return f"/api/admin/videos/{video_id}/stream/subtitle/{lang_code}"
    raise ValueError(f"Unknown admin stream resource: {resource}")


def _media_type_for_key(key: str) -> str:
    return mimetypes.guess_type(key)[0] or "application/octet-stream"


async def _file_response_for_key(storage, key: str) -> FileResponse:
    path = await storage.get_path(key)
    return FileResponse(path, media_type=_media_type_for_key(key))


def _localized_text(video: Video, language_code: str) -> tuple[str, str]:
    selected = next((item for item in video.translations if item.language_code == language_code), None)
    fallback = next((item for item in video.translations if item.language_code == "vi-VN"), None)
    item = selected or fallback
    return (item.title, item.description) if item else (video.title, video.description)


async def _video_response(video: Video, storage, language_code: str = "vi-VN") -> VideoResponse:
    if not video.languages:
        raise RuntimeError("Video languages must be loaded before serialization")
    title, description = _localized_text(video, language_code)
    langs = [
        VideoLanguageResponse(
            language_code=lang.language_code,
            subtitle_url=(
                _admin_stream_url(video.id, "subtitle", lang.language_code)
                if lang.subtitle_key else None
            ),
            status=lang.status,
        )
        for lang in video.languages
    ]
    return VideoResponse(
        id=video.id,
        title=title,
        description=description,
        status=video.status,
        duration_ms=video.duration_ms,
        thumbnail_url=_admin_stream_url(video.id, "thumbnail") if video.thumbnail_key else None,
        video_url=_admin_stream_url(video.id, "original") if video.original_video_key else None,
        languages=langs,
        translations=[VideoTranslationResponse.model_validate(item) for item in video.translations],
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


def _check_size(size_bytes: int, max_mb: int) -> None:
    if size_bytes > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {max_mb}MB limit")


def _validate_language(code: str | None) -> str:
    normalized = LANG_CODE_MAP.get(code or "", code or "")
    if normalized not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language")
    return normalized


def _asset_key(video_id: UUID, body: UploadUrlRequest) -> str:
    suffix = Path(body.filename).suffix.lower()
    if body.kind == "video":
        if suffix != ".mp4" or body.content_type not in {"video/mp4", "application/octet-stream"}:
            raise HTTPException(status_code=400, detail="Video must be MP4")
        _check_size(body.size_bytes, get_settings().max_upload_mb)
        return f"video/{video_id}/original.mp4"
    if body.kind == "thumbnail":
        if suffix not in ALLOWED_IMAGE_EXTENSIONS or not body.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Thumbnail must be JPG, PNG or WebP")
        _check_size(body.size_bytes, 10)
        return f"video/{video_id}/thumbnail{suffix}"
    code = _validate_language(body.language_code)
    if suffix != ".srt" or body.content_type not in ALLOWED_SUBTITLE_TYPES:
        raise HTTPException(status_code=400, detail="Subtitle must be SRT")
    _check_size(body.size_bytes, get_settings().max_subtitle_mb)
    return f"video/{video_id}/upload/{code.split('-')[0]}.srt"


async def _save_file(storage, key: str, data: bytes) -> None:
    try:
        await storage.save_file(key, data)
    except Exception as exc:
        raise storage_http_exception(exc) from exc


async def _ingest_subtitle(
    repo: SupabaseRepository,
    storage,
    video: Video,
    language_code: str,
    source_key: str,
    *,
    approved: bool,
) -> None:
    path = await storage.get_path(source_key)
    try:
        raw = path.read_text(encoding="utf-8-sig")
        entries, warnings = parse_srt(raw)
    except (UnicodeDecodeError, SRTParseError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid SRT: {exc}") from exc
    validation = validate_srt_structure(entries)
    if not entries or not validation.valid:
        details = validation.errors or warnings or ["Subtitle has no cues"]
        raise HTTPException(status_code=400, detail="; ".join(details[:8]))

    language = await repo.get_video_language(video.id, language_code)
    if not language:
        language = await repo.create_video_language(video.id, language_code)
    await repo.delete_segments_for_language(language.id)
    await repo.create_segments([
        {
            "video_language_id": str(language.id),
            "sequence": item.index,
            "start_ms": item.start_ms,
            "end_ms": item.end_ms,
            "source_text": item.text if language_code == "vi-VN" else "",
            "translated_text": item.text,
        }
        for item in entries
    ])
    vtt_key = f"video/{video.id}/subtitle/{language_code.split('-')[0]}.vtt"
    await storage.save_file(vtt_key, segments_to_vtt([
        {
            "sequence": item.index,
            "start_ms": item.start_ms,
            "end_ms": item.end_ms,
            "translated_text": item.text,
        }
        for item in entries
    ]).encode("utf-8"))
    await repo.update_video_language(
        language.id,
        subtitle_key=vtt_key,
        status=LanguageStatus.COMPLETED if approved else LanguageStatus.READY_FOR_REVIEW,
    )
    if language_code == "vi-VN":
        await repo.update_video(video.id, srt_key=source_key)


async def _load_video_relations(repo: SupabaseRepository, video_id: UUID) -> Video:
    video = await repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    video.languages = await repo.list_video_languages(video_id)
    video.translations = await repo.list_video_translations(video_id)
    return video


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
    for video in videos:
        video.languages = await repo.list_video_languages(video.id)
        video.translations = await repo.list_video_translations(video.id)
        items.append(await _video_response(video, storage))
    return VideoListResponse(items=items, total=len(items))


@router.post("/videos/draft", response_model=VideoCreateResponse, status_code=201)
async def create_video_draft(
    body: VideoDraftCreate,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    user: User = Depends(get_current_user),
):
    vi = next(item for item in body.translations if item.language_code == "vi-VN")
    video = await repo.create_video(vi.title, vi.description, user.id)
    for code in SUPPORTED_LANGUAGES:
        await repo.create_video_language(video.id, code)
    for item in body.translations:
        code = _validate_language(item.language_code)
        await repo.upsert_video_translation(video.id, code, item.title, item.description)
    return VideoCreateResponse(id=video.id, title=video.title, status=video.status)


@router.put("/videos/{video_id}/translations")
async def update_video_translations(
    video_id: UUID,
    body: VideoDraftCreate,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    video = await repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    for item in body.translations:
        code = _validate_language(item.language_code)
        await repo.upsert_video_translation(video_id, code, item.title, item.description)
        if code == "vi-VN":
            await repo.update_video(video_id, title=item.title, description=item.description)
    return {"message": "Translations updated"}


@router.post("/videos/{video_id}/upload-url", response_model=UploadUrlResponse)
async def create_upload_url(
    video_id: UUID,
    body: UploadUrlRequest,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    if not await repo.get_video(video_id):
        raise HTTPException(status_code=404, detail="Video not found")
    key = _asset_key(video_id, body)
    storage = get_storage()
    upload_url = await storage.create_upload_url(key, body.content_type)
    if upload_url:
        return UploadUrlResponse(
            key=key,
            upload_url=upload_url,
            method="PUT",
            headers={"Content-Type": body.content_type},
        )
    lang_query = f"?language_code={body.language_code}" if body.language_code else ""
    return UploadUrlResponse(
        key=key,
        fallback_url=f"/api/admin/videos/{video_id}/upload/{body.kind}{lang_query}",
        method="POST",
    )


@router.post("/videos/{video_id}/upload/{kind}")
async def upload_asset_fallback(
    video_id: UUID,
    kind: str,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
    file: UploadFile = File(...),
    language_code: str | None = Query(None),
):
    if not await repo.get_video(video_id):
        raise HTTPException(status_code=404, detail="Video not found")
    data = await file.read()
    body = UploadUrlRequest(
        kind=kind,
        filename=file.filename or "",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        language_code=language_code,
    )
    key = _asset_key(video_id, body)
    await _save_file(get_storage(), key, data)
    return {"key": key}


@router.post("/videos/{video_id}/assets/complete")
async def complete_asset(
    video_id: UUID,
    body: AssetCompleteRequest,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    video = await repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    expected_prefix = f"video/{video_id}/"
    if not body.key.startswith(expected_prefix) or ".." in body.key:
        raise HTTPException(status_code=400, detail="Invalid asset key")
    storage = get_storage()
    if not await storage.exists(body.key):
        raise HTTPException(status_code=400, detail="Uploaded object was not found")

    if body.kind == "video":
        updates = {"original_video_key": body.key}
        ffmpeg = FFmpegService()
        if ffmpeg.is_available():
            try:
                updates["duration_ms"] = ffmpeg.get_duration_ms(await storage.get_path(body.key))
            except Exception:
                pass
        await repo.update_video(video_id, **updates)
    elif body.kind == "thumbnail":
        await repo.update_video(video_id, thumbnail_key=body.key)
    else:
        code = _validate_language(body.language_code)
        await _ingest_subtitle(
            repo,
            storage,
            video,
            code,
            body.key,
            approved=code == "vi-VN",
        )
    return {"message": "Asset registered", "key": body.key}


# Backwards-compatible small/local upload endpoint.
@router.post("/videos", response_model=VideoCreateResponse, status_code=201)
async def create_video_legacy(
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    user: User = Depends(get_current_user),
    title: str = Form(...),
    description: str = Form(""),
    video: UploadFile = File(...),
    subtitle: UploadFile = File(...),
    thumbnail: UploadFile | None = File(None),
):
    draft = await create_video_draft(
        VideoDraftCreate(translations=[{"language_code": "vi-VN", "title": title, "description": description}]),
        repo,
        user,
    )
    storage = get_storage()
    video_data = await video.read()
    subtitle_data = await subtitle.read()
    video_key = _asset_key(draft.id, UploadUrlRequest(
        kind="video", filename=video.filename or "", content_type=video.content_type or "video/mp4", size_bytes=len(video_data)
    ))
    subtitle_key = _asset_key(draft.id, UploadUrlRequest(
        kind="subtitle", filename=subtitle.filename or "", content_type=subtitle.content_type or "application/x-subrip", size_bytes=len(subtitle_data), language_code="vi-VN"
    ))
    await _save_file(storage, video_key, video_data)
    await _save_file(storage, subtitle_key, subtitle_data)
    await complete_asset(draft.id, AssetCompleteRequest(kind="video", key=video_key), repo, user)
    await complete_asset(draft.id, AssetCompleteRequest(kind="subtitle", key=subtitle_key, language_code="vi-VN"), repo, user)
    if thumbnail and thumbnail.filename:
        data = await thumbnail.read()
        key = _asset_key(draft.id, UploadUrlRequest(
            kind="thumbnail", filename=thumbnail.filename, content_type=thumbnail.content_type or "image/jpeg", size_bytes=len(data)
        ))
        await _save_file(storage, key, data)
        await complete_asset(draft.id, AssetCompleteRequest(kind="thumbnail", key=key), repo, user)
    return draft


@router.post("/videos/{video_id}/generate", response_model=GenerateResponse, status_code=202)
async def generate_video(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    video = await repo.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if is_subtitle_pipeline_active(str(video_id)):
        raise HTTPException(status_code=409, detail="Subtitle translation is already running")
    try:
        validate_translation_config()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    source = await repo.get_video_language(video_id, "vi-VN")
    if not source or not await repo.list_segments(source.id):
        raise HTTPException(status_code=400, detail="Vietnamese SRT is required")
    await repo.update_video(video_id, status=VideoStatus.PROCESSING)
    start_subtitle_pipeline(str(video_id))
    return GenerateResponse(message="Draft translation started", video_id=video_id)


@router.post("/videos/{video_id}/regenerate/{lang_code}", response_model=GenerateResponse, status_code=202)
async def regenerate_language(
    video_id: UUID,
    lang_code: str,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    code = _validate_language(lang_code)
    if code == "vi-VN":
        raise HTTPException(status_code=400, detail="Vietnamese is the source language")
    try:
        validate_translation_config()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await repo.update_video(video_id, status=VideoStatus.PROCESSING)
    start_subtitle_pipeline(str(video_id), [code])
    return GenerateResponse(message=f"Regenerating {code}", video_id=video_id)


@router.get("/videos/{video_id}/subtitles/{lang_code}", response_model=SubtitleCuesResponse)
async def get_subtitle_cues(
    video_id: UUID,
    lang_code: str,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    code = _validate_language(lang_code)
    language = await repo.get_video_language(video_id, code)
    if not language:
        raise HTTPException(status_code=404, detail="Subtitle track not found")
    segments = await repo.list_segments(language.id)
    return SubtitleCuesResponse(
        language_code=code,
        status=language.status,
        cues=[SubtitleCue(
            id=item.id,
            sequence=item.sequence,
            start_ms=item.start_ms,
            end_ms=item.end_ms,
            text=item.translated_text or item.source_text,
        ) for item in segments],
    )


@router.put("/videos/{video_id}/subtitles/{lang_code}", response_model=SubtitleCuesResponse)
async def update_subtitle_cues(
    video_id: UUID,
    lang_code: str,
    body: SubtitleCuesUpdate,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    code = _validate_language(lang_code)
    language = await repo.get_video_language(video_id, code)
    if not language:
        raise HTTPException(status_code=404, detail="Subtitle track not found")
    await repo.delete_segments_for_language(language.id)
    await repo.create_segments([
        {
            "video_language_id": str(language.id),
            "sequence": cue.sequence,
            "start_ms": cue.start_ms,
            "end_ms": cue.end_ms,
            "source_text": cue.text if code == "vi-VN" else "",
            "translated_text": cue.text,
        }
        for cue in body.cues
    ])
    key = f"video/{video_id}/subtitle/{code.split('-')[0]}.vtt"
    await get_storage().save_file(key, segments_to_vtt([
        {"sequence": cue.sequence, "start_ms": cue.start_ms, "end_ms": cue.end_ms, "translated_text": cue.text}
        for cue in body.cues
    ]).encode("utf-8"))
    language = await repo.update_video_language(
        language.id,
        subtitle_key=key,
        status=LanguageStatus.COMPLETED if body.approved else LanguageStatus.READY_FOR_REVIEW,
    )
    return await get_subtitle_cues(video_id, code, repo, _)


@router.get("/videos/{video_id}/jobs", response_model=list[ProcessingJobResponse])
async def get_jobs(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    return [ProcessingJobResponse.model_validate(item) for item in await repo.list_jobs(video_id)]


@router.post("/videos/{video_id}/publish")
async def publish_video(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    video = await _load_video_relations(repo, video_id)
    missing: list[str] = []
    if not video.original_video_key:
        missing.append("video")
    if not video.thumbnail_key:
        missing.append("thumbnail")
    translations = {item.language_code: item for item in video.translations}
    tracks = {item.language_code: item for item in video.languages}
    for code in SUPPORTED_LANGUAGES:
        if code not in translations or not translations[code].title.strip():
            missing.append(f"metadata:{code}")
        if code not in tracks or tracks[code].status != LanguageStatus.COMPLETED or not tracks[code].subtitle_key:
            missing.append(f"subtitle:{code}")
    if missing:
        raise HTTPException(status_code=400, detail="Missing or unapproved: " + ", ".join(missing))
    await repo.update_video(video_id, status=VideoStatus.PUBLISHED)
    return {"message": "Published", "video_id": str(video_id)}


@router.post("/videos/{video_id}/unpublish")
async def unpublish_video(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    if not await repo.get_video(video_id):
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
    storage = get_storage()
    for key in [video.original_video_key, video.thumbnail_key, video.srt_key]:
        if key:
            await storage.delete(key)
    for language in await repo.list_video_languages(video_id):
        if language.subtitle_key:
            await storage.delete(language.subtitle_key)
    await repo.delete_video(video_id)
    return {"message": "Deleted"}


@router.get("/videos/{video_id}/preview", response_model=PreviewResponse)
async def preview_video(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    video = await repo.get_video_with_relations(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return PreviewResponse(
        video_id=video.id,
        status=video.status,
        title=video.title,
        description=video.description,
        video_url=_admin_stream_url(video_id, "original") if video.original_video_key else None,
        thumbnail_url=_admin_stream_url(video_id, "thumbnail") if video.thumbnail_key else None,
        languages=[VideoLanguageResponse(
            language_code=item.language_code,
            subtitle_url=_admin_stream_url(video_id, "subtitle", item.language_code) if item.subtitle_key else None,
            status=item.status,
        ) for item in video.languages],
        translations=[VideoTranslationResponse.model_validate(item) for item in video.translations],
        jobs=[ProcessingJobResponse.model_validate(item) for item in video.jobs],
    )


@router.get("/videos/{video_id}/stream/original")
async def stream_original_video(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    video = await repo.get_video(video_id)
    if not video or not video.original_video_key:
        raise HTTPException(status_code=404, detail="Video not found")
    return await _file_response_for_key(get_storage(), video.original_video_key)


@router.get("/videos/{video_id}/stream/thumbnail")
async def stream_thumbnail(
    video_id: UUID,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    video = await repo.get_video(video_id)
    if not video or not video.thumbnail_key:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return await _file_response_for_key(get_storage(), video.thumbnail_key)


@router.get("/videos/{video_id}/stream/subtitle/{lang}")
async def stream_subtitle(
    video_id: UUID,
    lang: str,
    repo: Annotated[SupabaseRepository, Depends(get_repo)],
    _: User = Depends(get_current_user),
):
    language = await repo.get_video_language(video_id, _validate_language(lang))
    if not language or not language.subtitle_key:
        raise HTTPException(status_code=404, detail="Subtitle not found")
    return await _file_response_for_key(get_storage(), language.subtitle_key)


@router.get("/qr", response_model=QRResponse)
async def get_qr(_: User = Depends(get_current_user)):
    url = get_settings().public_base_url.rstrip("/") + "/"
    png = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=4)
    png.add_data(url)
    png.make(fit=True)
    png_buffer = io.BytesIO()
    png.make_image(fill_color="#0f172a", back_color="white").save(png_buffer, format="PNG")

    svg_buffer = io.BytesIO()
    qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage).save(svg_buffer)
    return QRResponse(
        url=url,
        qr_image_base64="data:image/png;base64," + base64.b64encode(png_buffer.getvalue()).decode(),
        qr_svg_base64="data:image/svg+xml;base64," + base64.b64encode(svg_buffer.getvalue()).decode(),
    )
