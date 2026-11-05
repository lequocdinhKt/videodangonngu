from pathlib import Path

import edge_tts

from app.config.logging import get_logger
from app.services.tts.base import TTSEngine

logger = get_logger(__name__)


class EdgeTTSEngine(TTSEngine):
    @property
    def provider_name(self) -> str:
        return "edge"

    async def synthesize(
        self,
        text: str,
        language: str,
        voice: str,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(output_path))
        return output_path


def get_tts_engine() -> TTSEngine:
    from app.config.settings import get_settings

    settings = get_settings()
    if settings.tts_provider == "edge":
        return EdgeTTSEngine()
    raise ValueError(f"Unknown TTS provider: {settings.tts_provider}")


def get_voice_for_language(language_code: str) -> str:
    from app.config.settings import get_settings

    settings = get_settings()
    mapping = {
        "vi-VN": settings.tts_voice_vi,
        "en-US": settings.tts_voice_en,
        "ru-RU": settings.tts_voice_ru,
        "zh-CN": settings.tts_voice_zh,
    }
    return mapping.get(language_code, settings.tts_voice_en)
