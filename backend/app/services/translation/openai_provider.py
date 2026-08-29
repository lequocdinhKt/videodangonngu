import json

from openai import AsyncOpenAI

from app.config.settings import get_settings
from app.config.logging import get_logger
from app.services.translation.base import (
    SegmentInput,
    SegmentOutput,
    TranslationContext,
    TranslationProvider,
)

logger = get_logger(__name__)

LANGUAGE_NAMES = {
    "en-US": "English (US)",
    "ru-RU": "Russian",
    "zh-CN": "Chinese Simplified (Mandarin)",
    "vi-VN": "Vietnamese",
}


class OpenAITranslationProvider(TranslationProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key or "sk-placeholder")
        self.model = settings.translation_model

    @property
    def provider_name(self) -> str:
        return "openai"

    async def translate_batch(
        self,
        segments: list[SegmentInput],
        context: TranslationContext,
    ) -> list[SegmentOutput]:
        lang_name = LANGUAGE_NAMES.get(context.target_language, context.target_language)
        segments_json = [
            {"sequence": s.sequence, "start_ms": s.start_ms, "end_ms": s.end_ms, "text": s.source_text}
            for s in segments
        ]

        preceding = [
            {"sequence": s.get("sequence"), "text": s.get("source_text", s.get("text", ""))}
            for s in context.preceding_segments
        ]
        following = [
            {"sequence": s.get("sequence"), "text": s.get("source_text", s.get("text", ""))}
            for s in context.following_segments
        ]

        concise_note = ""
        if context.concise:
            concise_note = (
                "\nIMPORTANT: Make each translation noticeably shorter while preserving "
                "all facts, names, and meaning. Optimize for spoken delivery length."
            )

        topic_line = f"Topic: {context.topic}\n" if context.topic else ""
        system_prompt = f"""You are a professional subtitle translator for video narration.
Translate Vietnamese subtitles to {lang_name}.

PRIORITY ORDER (never violate):
1. Semantic accuracy — preserve exact meaning
2. Contextual accuracy — understand adjacent segments as connected narrative
3. Preserve proper nouns, place names, numbers, dates, units, technical terms exactly
4. Natural target-language expression for narration style
5. Only then optimize sentence length for speech{concise_note}

RULES:
- Return ONLY valid JSON object with key "segments"
- Each item: {{"sequence": N, "translated_text": "..."}}
- Same number of segments as input
- Do NOT change timestamps
- Do NOT merge or split segments
- Do NOT add explanations or markdown
- Sentences may span multiple segments — translate each segment's portion naturally
- Use preceding/following context for continuity but only translate the requested segments

Video title: {context.title}
{topic_line}Description: {context.description}
Glossary: {json.dumps(context.glossary, ensure_ascii=False)}
Proper nouns: {', '.join(context.proper_nouns) if context.proper_nouns else 'none'}"""

        context_block = ""
        if preceding:
            context_block += f"\nPreceding context (do NOT translate):\n{json.dumps(preceding, ensure_ascii=False)}"
        if following:
            context_block += f"\nFollowing context (do NOT translate):\n{json.dumps(following, ensure_ascii=False)}"

        user_prompt = (
            f"Translate these subtitle segments:\n{json.dumps(segments_json, ensure_ascii=False)}"
            f"{context_block}"
        )

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
            parsed = json.loads(content)
            translations = parsed if isinstance(parsed, list) else parsed.get("segments", parsed.get("translations", []))
            trans_map = {t["sequence"]: t["translated_text"] for t in translations}

            return [
                SegmentOutput(
                    sequence=s.sequence,
                    start_ms=s.start_ms,
                    end_ms=s.end_ms,
                    source_text=s.source_text,
                    translated_text=trans_map.get(s.sequence, s.source_text),
                )
                for s in segments
            ]
        except Exception as exc:
            logger.error("Translation failed: %s", exc)
            raise


def get_translation_provider() -> TranslationProvider:
    settings = get_settings()
    if settings.translation_provider == "openai":
        return OpenAITranslationProvider()
    raise ValueError(f"Unknown translation provider: {settings.translation_provider}")
