"""Translation provider factory."""

from app.config.settings import get_settings
from app.services.translation.base import TranslationProvider
from app.services.translation.groq_provider import GroqTranslationProvider
from app.services.translation.openai_provider import OpenAITranslationProvider


def get_translation_provider() -> TranslationProvider:
    settings = get_settings()
    if settings.translation_provider == "groq":
        return GroqTranslationProvider()
    if settings.translation_provider == "openai":
        return OpenAITranslationProvider()
    raise ValueError(f"Unknown translation provider: {settings.translation_provider}")


def validate_translation_config() -> None:
    settings = get_settings()
    if settings.translation_provider == "groq" and not settings.groq_api_key.strip():
        raise ValueError("GROQ_API_KEY is required when TRANSLATION_PROVIDER=groq")
    if settings.translation_provider == "openai" and not settings.openai_api_key.strip():
        raise ValueError("OPENAI_API_KEY is required when TRANSLATION_PROVIDER=openai")
