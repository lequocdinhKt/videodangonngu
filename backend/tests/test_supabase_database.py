"""Supabase database repository tests with in-memory mock."""

from __future__ import annotations

import uuid

import pytest

from app.models.db import JobStatus, LanguageStatus, ProcessingStage, User, VideoStatus
from tests.mock_repository import InMemoryRepository


@pytest.fixture
def repo() -> InMemoryRepository:
    return InMemoryRepository()


@pytest.mark.asyncio
async def test_create_user_and_video(repo: InMemoryRepository):
    user = await repo.create_user("admin@test.com", "hash")
    assert user.email == "admin@test.com"
    video = await repo.create_video("Test", "desc", user.id)
    assert video.title == "Test"
    assert video.status == VideoStatus.DRAFT


@pytest.mark.asyncio
async def test_unique_video_language(repo: InMemoryRepository):
    user = await repo.create_user("a@b.com", "h")
    video = await repo.create_video("T", "", user.id)
    await repo.create_video_language(video.id, "en-US")
    lang2 = await repo.create_video_language(video.id, "en-US")
    langs = await repo.list_video_languages(video.id)
    assert len(langs) == 2


@pytest.mark.asyncio
async def test_subtitle_segments(repo: InMemoryRepository):
    user = await repo.create_user("a@b.com", "h")
    video = await repo.create_video("T", "", user.id)
    lang = await repo.create_video_language(video.id, "vi-VN")
    await repo.create_segments([
        {"video_language_id": str(lang.id), "sequence": 1, "start_ms": 0, "end_ms": 1000,
         "source_text": "hi", "translated_text": "hi"},
    ])
    segs = await repo.list_segments(lang.id)
    assert len(segs) == 1
    assert segs[0].sequence == 1


@pytest.mark.asyncio
async def test_processing_job_with_pipeline_run(repo: InMemoryRepository):
    user = await repo.create_user("a@b.com", "h")
    video = await repo.create_video("T", "", user.id)
    run_id = uuid.uuid4()
    job = await repo.upsert_job(
        video.id, run_id, ProcessingStage.PARSE.value, None,
        JobStatus.RUNNING, 50,
    )
    assert job.pipeline_run_id == run_id
    assert job.progress == 50
    job2 = await repo.upsert_job(
        video.id, run_id, ProcessingStage.PARSE.value, None,
        JobStatus.COMPLETED, 100,
    )
    assert job2.id == job.id
    assert job2.status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_published_video_filter(repo: InMemoryRepository):
    user = await repo.create_user("a@b.com", "h")
    v1 = await repo.create_video("Pub", "", user.id)
    await repo.update_video(v1.id, status=VideoStatus.PUBLISHED)
    await repo.create_video("Draft", "", user.id)
    published = await repo.list_videos(status=VideoStatus.PUBLISHED)
    assert len(published) == 1
    assert published[0].title == "Pub"


@pytest.mark.asyncio
async def test_audio_track_upsert(repo: InMemoryRepository):
    user = await repo.create_user("a@b.com", "h")
    video = await repo.create_video("T", "", user.id)
    lang = await repo.create_video_language(video.id, "en-US")
    track = await repo.upsert_audio_track(lang.id, "video/x/audio/en.mp3", 5000, {"mixed": False})
    assert track.audio_key.endswith("en.mp3")
    track2 = await repo.upsert_audio_track(lang.id, "video/x/audio/en.mp3", 6000, {"mixed": True})
    assert track2.duration_ms == 6000
