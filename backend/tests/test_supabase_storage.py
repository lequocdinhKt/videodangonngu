"""Supabase storage provider tests with local fallback."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.storage.local import LocalStorageProvider, reset_storage


@pytest.fixture
def storage(tmp_path, monkeypatch):
    import app.config.settings as settings_mod

    monkeypatch.setenv("STORAGE_PROVIDER", "local")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    settings_mod._settings = None
    reset_storage()
    return LocalStorageProvider()


@pytest.mark.asyncio
async def test_save_and_exists(storage: LocalStorageProvider, tmp_path):
    key = "video/test/original.mp4"
    await storage.save_file(key, b"video-data")
    assert await storage.exists(key)
    path = await storage.get_path(key)
    assert path.read_bytes() == b"video-data"


@pytest.mark.asyncio
async def test_download_to_path(storage: LocalStorageProvider, tmp_path):
    key = "video/test/file.mp3"
    await storage.save_file(key, b"audio")
    dest = tmp_path / "downloaded.mp3"
    await storage.download_to_path(key, dest)
    assert dest.read_bytes() == b"audio"


@pytest.mark.asyncio
async def test_delete(storage: LocalStorageProvider):
    key = "video/test/del.vtt"
    await storage.save_file(key, b"vtt")
    assert await storage.exists(key)
    await storage.delete(key)
    assert not await storage.exists(key)


@pytest.mark.asyncio
async def test_get_signed_url_local_returns_media_path(storage: LocalStorageProvider):
    url = await storage.get_signed_url("video/x/a.mp3")
    assert url == "/api/media/video/x/a.mp3"
