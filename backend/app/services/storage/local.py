import asyncio
from pathlib import Path

import aiofiles

from app.config.settings import get_settings
from app.services.storage.base import BaseStorage


class LocalStorageProvider(BaseStorage):
    def __init__(self) -> None:
        settings = get_settings()
        self.root = Path(settings.storage_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def save_file(self, key: str, source: Path | bytes) -> str:
        dest = self._full_path(key)
        if isinstance(source, Path):
            async with aiofiles.open(source, "rb") as src, aiofiles.open(dest, "wb") as dst:
                while chunk := await src.read(1024 * 1024):
                    await dst.write(chunk)
        else:
            async with aiofiles.open(dest, "wb") as f:
                await f.write(source)
        return key

    async def get_path(self, key: str) -> Path:
        return self._full_path(key)

    async def download_to_path(self, key: str, dest: Path) -> Path:
        src = self._full_path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(src, "rb") as s, aiofiles.open(dest, "wb") as d:
            while chunk := await s.read(1024 * 1024):
                await d.write(chunk)
        return dest

    async def get_url(self, key: str, *, expires_in: int | None = None) -> str:
        return f"/api/media/{key}"

    async def get_signed_url(self, key: str, expires_in: int | None = None) -> str:
        return await self.get_url(key, expires_in=expires_in)

    async def delete(self, key: str) -> None:
        path = self._full_path(key)
        if path.exists():
            path.unlink()

    async def exists(self, key: str) -> bool:
        return self._full_path(key).exists()


_storage: BaseStorage | None = None


def get_storage() -> BaseStorage:
    global _storage
    if _storage is None:
        settings = get_settings()
        if settings.storage_provider == "supabase":
            from app.services.storage.supabase import SupabaseStorageProvider

            _storage = SupabaseStorageProvider()
        elif settings.storage_provider in ("s3", "r2"):
            from app.services.storage.s3 import S3StorageProvider

            _storage = S3StorageProvider()
        else:
            _storage = LocalStorageProvider()
    return _storage


def reset_storage() -> None:
    global _storage
    _storage = None
