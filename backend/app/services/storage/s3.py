"""S3-compatible storage (Cloudflare R2, AWS S3, …)."""

from __future__ import annotations

import asyncio
import mimetypes
import shutil
from pathlib import Path

import aiofiles
import boto3
from botocore.config import Config

from app.config.settings import get_settings
from app.services.storage.base import BaseStorage


class S3StorageProvider(BaseStorage):
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.s3_bucket
        self.default_expires = settings.signed_url_expires_seconds
        self._local_cache = Path(settings.workspace_dir) / "storage_cache"
        self._local_cache.mkdir(parents=True, exist_ok=True)
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

    async def _run(self, fn):
        return await asyncio.to_thread(fn)

    async def save_file(self, key: str, source: Path | bytes) -> str:
        content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
        cached = self._local_cache / key
        cached.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(source, Path):
            await self._run(lambda: self._client.upload_file(
                str(source), self.bucket, key, ExtraArgs={"ContentType": content_type}
            ))
            if source.resolve() != cached.resolve():
                await asyncio.to_thread(shutil.copyfile, source, cached)
        else:
            await self._run(lambda: self._client.put_object(
                Bucket=self.bucket, Key=key, Body=source, ContentType=content_type
            ))
            async with aiofiles.open(cached, "wb") as f:
                await f.write(source)
        return key

    async def get_path(self, key: str) -> Path:
        cached = self._local_cache / key
        if cached.exists():
            return cached
        cached.parent.mkdir(parents=True, exist_ok=True)
        return await self.download_to_path(key, cached)

    async def download_to_path(self, key: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)

        await self._run(lambda: self._client.download_file(self.bucket, key, str(dest)))
        return dest

    async def get_signed_url(self, key: str, expires_in: int | None = None) -> str:
        ttl = expires_in if expires_in is not None else self.default_expires

        def _sign():
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=ttl,
            )

        return await self._run(_sign)

    async def get_url(self, key: str, *, expires_in: int | None = None) -> str:
        return await self.get_signed_url(key, expires_in=expires_in)

    async def create_upload_url(
        self, key: str, content_type: str, expires_in: int = 900
    ) -> str:
        def _sign():
            return self._client.generate_presigned_url(
                "put_object",
                Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
                ExpiresIn=expires_in,
            )

        return await self._run(_sign)

    async def delete(self, key: str) -> None:
        def _delete():
            self._client.delete_object(Bucket=self.bucket, Key=key)

        await self._run(_delete)
        cached = self._local_cache / key
        if cached.exists():
            cached.unlink()

    async def exists(self, key: str) -> bool:
        cached = self._local_cache / key
        if cached.exists():
            return True

        def _head():
            self._client.head_object(Bucket=self.bucket, Key=key)

        try:
            await self._run(_head)
            return True
        except Exception:
            return False
