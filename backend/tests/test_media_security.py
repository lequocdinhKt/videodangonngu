"""Public API media access security tests."""

from __future__ import annotations

import uuid

import pytest

from app.models.db import LanguageStatus, VideoStatus


@pytest.mark.asyncio
async def test_unpublished_video_returns_404(app_client, memory_repo):
    user = await memory_repo.create_user("admin@test.com", "hash")
    video = await memory_repo.create_video("Draft", "", user.id)
    response = await app_client.get(f"/api/videos/{video.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_published_video_accessible(app_client, memory_repo):
    user = await memory_repo.create_user("admin@test.com", "hash")
    video = await memory_repo.create_video("Pub", "", user.id)
    await memory_repo.update_video(video.id, status=VideoStatus.PUBLISHED, original_video_key="video/x/original.mp4")
    lang = await memory_repo.create_video_language(video.id, "en-US", LanguageStatus.COMPLETED)
    await memory_repo.update_video_language(lang.id, subtitle_key="video/x/subtitle/en.vtt")
    await memory_repo.upsert_audio_track(lang.id, "video/x/audio/en.mp3", 1000, None)

    response = await app_client.get(f"/api/videos/{video.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Pub"


@pytest.mark.asyncio
async def test_unpublished_subtitle_returns_404(app_client, memory_repo):
    user = await memory_repo.create_user("admin@test.com", "hash")
    video = await memory_repo.create_video("Draft", "", user.id)
    lang = await memory_repo.create_video_language(video.id, "en-US")
    await memory_repo.update_video_language(lang.id, subtitle_key="video/x/subtitle/en.vtt")
    response = await app_client.get(f"/api/videos/{video.id}/subtitles/en.vtt")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_media_endpoint_removed(app_client):
    response = await app_client.get("/api/media/video/some/file.mp4")
    assert response.status_code == 404
