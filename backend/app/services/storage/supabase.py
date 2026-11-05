"""Supabase Storage provider — private bucket with signed URLs."""

from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path

import aiofiles

from app.config.settings import get_settings
from app.integrations.supabase.client import get_supabase_client
from app.services.storage.base import BaseStorage


class SupabaseStorageProvider(BaseStorage):
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.supabase_storage_bucket
        self.default_expires = settings.signed_url_expires_seconds
        self._local_cache = Path(settings.workspace_dir) / "storage_cache"
        self._local_cache.mkdir(parents=True, exist_ok=True)

    def _client(self):
        return get_supabase_client()

    async def _run(self, fn):
        return await asyncio.to_thread(fn)

    async def save_file(self, key: str, source: Path | bytes) -> str:
        settings = get_settings()

        if isinstance(source, Path):
            async with aiofiles.open(source, "rb") as f:
                data = await f.read()
        else:
            data = source

        content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"

        def _upload():
            return self._client().storage.from_(self.bucket).upload(
                key,
                data,
                file_options={"content-type": content_type, "upsert": "true"},
            )

        await self._run(_upload)
        cached = self._local_cache / key
        cached.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(cached, "wb") as f:
            await f.write(data)
        return key

    async def get_path(self, key: str) -> Path:
        """Return local cached path; download from Supabase if missing."""
        cached = self._local_cache / key
        if cached.exists():
            return cached
        cached.parent.mkdir(parents=True, exist_ok=True)
        return await self.download_to_path(key, cached)

    async def download_to_path(self, key: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)

        def _download():
            return self._client().storage.from_(self.bucket).download(key)

        data = await self._run(_download)
        async with aiofiles.open(dest, "wb") as f:
            await f.write(data)
        return dest

    async def get_signed_url(self, key: str, expires_in: int | None = None) -> str:
        ttl = expires_in if expires_in is not None else self.default_expires

        def _sign():
            return self._client().storage.from_(self.bucket).create_signed_url(key, ttl)

        result = await self._run(_sign)
        if isinstance(result, dict):
            signed = result.get("signedURL") or result.get("signedUrl")
            if signed:
                return signed
        raise RuntimeError(f"Failed to create signed URL for {key}")

    async def get_url(self, key: str, *, expires_in: int | None = None) -> str:
        return await self.get_signed_url(key, expires_in=expires_in)

    async def delete(self, key: str) -> None:
        def _delete():
            self._client().storage.from_(self.bucket).remove([key])

        await self._run(_delete)
        cached = self._local_cache / key
        if cached.exists():
            cached.unlink()

    async def exists(self, key: str) -> bool:
        cached = self._local_cache / key
        if cached.exists():
            return True

        def _list():
            folder = str(Path(key).parent).replace("\\", "/")
            if folder == ".":
                folder = ""
            name = Path(key).name
            items = self._client().storage.from_(self.bucket).list(folder)
            return any(item.get("name") == name for item in (items or []))

        try:
            return await self._run(_list)
        except Exception:
            return False
