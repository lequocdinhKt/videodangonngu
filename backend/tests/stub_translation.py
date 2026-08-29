"""Deterministic stub translations for E2E pipeline testing without OpenAI."""

from app.services.translation.base import (
    SegmentInput,
    SegmentOutput,
    TranslationContext,
    TranslationProvider,
)

STUB_TRANSLATIONS = {
    "en-US": {
        1: "Hello and welcome to Hoi An.",
        2: "This is a beautiful ancient city.",
    },
    "ru-RU": {
        1: "Здравствуйте и добро пожаловать в Хойан.",
        2: "Это прекрасный древний город.",
    },
    "zh-CN": {
        1: "您好，欢迎来到会安。",
        2: "这是一座美丽的古城。",
    },
}


class StubTranslationProvider(TranslationProvider):
    @property
    def provider_name(self) -> str:
        return "stub"

    async def translate_batch(
        self,
        segments: list[SegmentInput],
        context: TranslationContext,
    ) -> list[SegmentOutput]:
        lang_map = STUB_TRANSLATIONS.get(context.target_language, {})
        return [
            SegmentOutput(
                sequence=s.sequence,
                start_ms=s.start_ms,
                end_ms=s.end_ms,
                source_text=s.source_text,
                translated_text=lang_map.get(s.sequence, f"[{context.target_language}] {s.source_text}"),
            )
            for s in segments
        ]
