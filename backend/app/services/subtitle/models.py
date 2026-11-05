from dataclasses import dataclass, field


@dataclass
class SubtitleEntry:
    index: int
    start_ms: int
    end_ms: int
    duration_ms: int
    text: str
    warnings: list[str] = field(default_factory=list)
