"""Regression tests for the fixed two-slot public library."""

from __future__ import annotations

import pytest

from app.core.auth import hash_password
from app.models.db import VideoStatus


async def _login(client, repo):
    await repo.create_user("slots-admin@test.local", hash_password("strong-test-password"))
    response = await client.post(
        "/api/admin/auth/login",
        json={"email": "slots-admin@test.local", "password": "strong-test-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_public_slots_keep_two_chapters_and_hide_drafts(app_client, memory_repo):
    user = await memory_repo.create_user("owner@test.local", "hash")
    draft = await memory_repo.create_video("Draft", "", user.id)
    published = await memory_repo.create_video("Published", "", user.id)
    await memory_repo.update_video(published.id, status=VideoStatus.PUBLISHED)
    await memory_repo.set_public_video_slot("chapter-1", draft.id)
    await memory_repo.set_public_video_slot("chapter-2", published.id)

    response = await app_client.get("/api/video-slots?lang=vi-VN")

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["slot_key"] for item in items] == ["chapter-1", "chapter-2"]
    assert items[0]["video"] is None
    assert items[1]["video"]["id"] == str(published.id)


@pytest.mark.asyncio
async def test_admin_can_assign_a_video_to_one_slot_only(app_client, memory_repo):
    headers = await _login(app_client, memory_repo)
    user = await memory_repo.get_user_by_email("slots-admin@test.local")
    video = await memory_repo.create_video("Chapter video", "", user.id)

    assigned = await app_client.put(
        "/api/admin/video-slots/chapter-1", headers=headers, json={"video_id": str(video.id)}
    )
    duplicate = await app_client.put(
        "/api/admin/video-slots/chapter-2", headers=headers, json={"video_id": str(video.id)}
    )

    assert assigned.status_code == 200, assigned.text
    assert duplicate.status_code == 409
