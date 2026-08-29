import hashlib
from pathlib import Path

import aiofiles

from app.config.settings import get_settings


class TTSCache:
    def __init__(self) -> None:
        settings = get_settings()
        self.cache_dir = Path(settings.workspace_dir) / "cache" / "tts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, provider: str, language: str, voice: str, text: str) -> str:
        raw = f"{provider}|{language}|{voice}|{text}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get_cached(self, provider: str, language: str, voice: str, text: str) -> Path | None:
        path = self.cache_dir / f"{self._key(provider, language, voice, text)}.mp3"
        return path if path.exists() else None

    async def store(self, provider: str, language: str, voice: str, text: str, source: Path) -> Path:
        dest = self.cache_dir / f"{self._key(provider, language, voice, text)}.mp3"
        async with aiofiles.open(source, "rb") as src, aiofiles.open(dest, "wb") as dst:
            await dst.write(await src.read())
        return dest
