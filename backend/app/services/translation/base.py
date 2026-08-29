from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TranslationContext:
    title: str = ""
    description: str = ""
    topic: str = ""
    glossary: dict[str, str] = field(default_factory=dict)
    proper_nouns: list[str] = field(default_factory=list)
    target_language: str = ""
    preceding_segments: list[dict] = field(default_factory=list)
    following_segments: list[dict] = field(default_factory=list)
    concise: bool = False


@dataclass
class SegmentInput:
    sequence: int
    start_ms: int
    end_ms: int
    source_text: str


@dataclass
class SegmentOutput:
    sequence: int
    start_ms: int
    end_ms: int
    source_text: str
    translated_text: str


class TranslationProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def translate_batch(
        self,
        segments: list[SegmentInput],
        context: TranslationContext,
    ) -> list[SegmentOutput]: ...
