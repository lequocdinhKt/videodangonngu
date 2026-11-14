from __future__ import annotations

import pytest

from app.core.auth import hash_password
from app.services.translation.base import SegmentOutput


async def _login(client, repo):
    await repo.create_user("admin-metadata@test.local", hash_password("strong-test-password"))
    response = await client.post(
        "/api/admin/auth/login",
        json={"email": "admin-metadata@test.local", "password": "strong-test-password"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_generate_metadata_translation_returns_three_editable_drafts(app_client, memory_repo, monkeypatch):
    class StubProvider:
        async def translate_batch(self, segments, context):
            return [
                SegmentOutput(1, 0, 1, segments[0].source_text, f"{context.target_language} title"),
                SegmentOutput(2, 1, 2, segments[1].source_text, f"{context.target_language} description"),
            ]

    import app.api.routes.admin as admin_routes
    monkeypatch.setattr(admin_routes, "validate_translation_config", lambda: None)
    monkeypatch.setattr(admin_routes, "get_translation_provider", lambda: StubProvider())
    headers = await _login(app_client, memory_repo)

    response = await app_client.post(
        "/api/admin/translations/generate",
        headers=headers,
        json={"title": "Tiêu đề nguồn", "description": "Mô tả nguồn"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["translations"] == [
        {"language_code": "en-US", "title": "en-US title", "description": "en-US description"},
        {"language_code": "ru-RU", "title": "ru-RU title", "description": "ru-RU description"},
        {"language_code": "zh-CN", "title": "zh-CN title", "description": "zh-CN description"},
    ]


@pytest.mark.asyncio
async def test_generate_metadata_translation_requires_vietnamese_source(app_client, memory_repo):
    headers = await _login(app_client, memory_repo)
    response = await app_client.post(
        "/api/admin/translations/generate", headers=headers, json={"title": "", "description": "Mô tả"}
    )
    assert response.status_code == 422
