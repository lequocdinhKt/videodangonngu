from __future__ import annotations

import pytest

from app.core.auth import hash_password


SRT = b"""1
00:00:00,000 --> 00:00:02,000
Xin chao Viet Nam.

2
00:00:02,100 --> 00:00:04,000
Du lieu phu de demo.
"""


async def _login(client, repo):
    await repo.create_user("admin@test.local", hash_password("strong-test-password"))
    response = await client.post(
        "/api/admin/auth/login",
        json={"email": "admin@test.local", "password": "strong-test-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _upload(client, headers, video_id, kind, filename, content_type, data, language=None):
    suffix = f"?language_code={language}" if language else ""
    response = await client.post(
        f"/api/admin/videos/{video_id}/upload/{kind}{suffix}",
        headers=headers,
        files={"file": (filename, data, content_type)},
    )
    assert response.status_code == 200, response.text
    key = response.json()["key"]
    complete = await client.post(
        f"/api/admin/videos/{video_id}/assets/complete",
        headers=headers,
        json={"kind": kind, "key": key, "language_code": language},
    )
    assert complete.status_code == 200, complete.text


@pytest.mark.asyncio
async def test_subtitle_only_publish_workflow(app_client, memory_repo):
    headers = await _login(app_client, memory_repo)
    translations = [
        {"language_code": "vi-VN", "title": "Hoi An", "description": "Demo"},
        {"language_code": "en-US", "title": "Hoi An", "description": "Demo"},
        {"language_code": "ru-RU", "title": "Хойан", "description": "Демо"},
        {"language_code": "zh-CN", "title": "会安", "description": "演示"},
    ]
    created = await app_client.post(
        "/api/admin/videos/draft", headers=headers, json={"translations": translations}
    )
    assert created.status_code == 201, created.text
    video_id = created.json()["id"]

    await _upload(app_client, headers, video_id, "video", "demo.mp4", "video/mp4", b"demo-mp4")
    await _upload(app_client, headers, video_id, "thumbnail", "demo.webp", "image/webp", b"demo-webp")
    for code in ("vi-VN", "en-US", "ru-RU", "zh-CN"):
        await _upload(app_client, headers, video_id, "subtitle", f"{code}.srt", "application/x-subrip", SRT, code)

    early = await app_client.post(f"/api/admin/videos/{video_id}/publish", headers=headers)
    assert early.status_code == 400
    assert "subtitle:en-US" in early.json()["detail"]

    for code in ("en-US", "ru-RU", "zh-CN"):
        track = await app_client.get(f"/api/admin/videos/{video_id}/subtitles/{code}", headers=headers)
        assert track.status_code == 200
        assert track.json()["status"] == "ready_for_review"
        approved = await app_client.put(
            f"/api/admin/videos/{video_id}/subtitles/{code}",
            headers=headers,
            json={"cues": track.json()["cues"], "approved": True},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "completed"

    published = await app_client.post(f"/api/admin/videos/{video_id}/publish", headers=headers)
    assert published.status_code == 200, published.text

    public = await app_client.get(f"/api/videos/{video_id}?lang=zh-CN")
    assert public.status_code == 200
    assert public.json()["title"] == "会安"
    assert "audio_url" not in public.text


@pytest.mark.asyncio
async def test_upload_validation_and_qr(app_client, memory_repo):
    headers = await _login(app_client, memory_repo)
    qr = await app_client.get("/api/admin/qr", headers=headers)
    assert qr.status_code == 200
    assert qr.json()["qr_image_base64"].startswith("data:image/png;base64,")
    assert qr.json()["qr_svg_base64"].startswith("data:image/svg+xml;base64,")

    created = await app_client.post(
        "/api/admin/videos/draft",
        headers=headers,
        json={"translations": [{"language_code": "vi-VN", "title": "Demo", "description": ""}]},
    )
    video_id = created.json()["id"]
    invalid = await app_client.post(
        f"/api/admin/videos/{video_id}/upload-url",
        headers=headers,
        json={"kind": "video", "filename": "bad.mov", "content_type": "video/quicktime", "size_bytes": 20},
    )
    assert invalid.status_code == 400
