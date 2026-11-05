"""Groq LLM translation provider (OpenAI-compatible API)."""

from openai import AsyncOpenAI

from app.config.logging import get_logger
from app.config.settings import get_settings
from app.services.translation.base import (
    SegmentInput,
    SegmentOutput,
    TranslationContext,
    TranslationProvider,
)
from app.services.translation.common import build_translation_messages, parse_translation_response

logger = get_logger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqTranslationProvider(TranslationProvider):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.groq_api_key.strip():
            raise ValueError("GROQ_API_KEY is not configured")
        self.client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url=GROQ_BASE_URL,
        )
        self.model = settings.groq_model

    @property
    def provider_name(self) -> str:
        return "groq"

    async def translate_batch(
        self,
        segments: list[SegmentInput],
        context: TranslationContext,
    ) -> list[SegmentOutput]:
        system_prompt, user_prompt = build_translation_messages(segments, context)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return parse_translation_response(content, segments)
        except Exception as exc:
            logger.error("Groq translation failed: %s", exc)
            raise
