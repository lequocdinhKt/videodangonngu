import re

from app.services.subtitle.models import SubtitleEntry


class SRTParseError(Exception):
    pass


TIMESTAMP_PATTERN = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})$"
)


def timestamp_to_ms(h: str, m: str, s: str, ms: str) -> int:
    return int(h) * 3_600_000 + int(m) * 60_000 + int(s) * 1_000 + int(ms)


def ms_to_vtt_timestamp(ms: int) -> str:
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1_000
    ms %= 1_000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def parse_srt(content: str) -> tuple[list[SubtitleEntry], list[str]]:
    if content.startswith("\ufeff"):
        content = content[1:]
    content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not content:
        return [], []

    blocks = re.split(r"\n\n+", content)
    subtitles: list[SubtitleEntry] = []
    warnings: list[str] = []

    for block_num, block in enumerate(blocks, start=1):
        lines = block.split("\n")
        if len(lines) < 2:
            warnings.append(f"Block {block_num}: insufficient lines, skipped")
            continue

        index_line = lines[0].strip()
        if not index_line.isdigit():
            warnings.append(f"Block {block_num}: invalid index '{index_line}', skipped")
            continue
        index = int(index_line)

        ts_match = TIMESTAMP_PATTERN.match(lines[1].strip())
        if not ts_match:
            raise SRTParseError(f"Block {block_num}: invalid timestamp line '{lines[1]}'")

        start_ms = timestamp_to_ms(*ts_match.groups()[:4])
        end_ms = timestamp_to_ms(*ts_match.groups()[4:])
        if end_ms <= start_ms:
            raise SRTParseError(f"Subtitle {index}: end time must be after start time")

        text = "\n".join(line.rstrip() for line in lines[2:]).strip()
        block_warnings: list[str] = []
        if not text:
            block_warnings.append("empty text")

        subtitles.append(
            SubtitleEntry(
                index=index,
                start_ms=start_ms,
                end_ms=end_ms,
                duration_ms=end_ms - start_ms,
                text=text,
                warnings=block_warnings,
            )
        )

    return subtitles, warnings


def segments_to_vtt(segments: list[dict]) -> str:
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = ms_to_vtt_timestamp(seg["start_ms"])
        end = ms_to_vtt_timestamp(seg["end_ms"])
        text = seg.get("translated_text") or seg.get("text", "")
        lines.append(str(seg["sequence"]))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def segments_to_srt(segments: list[dict]) -> str:
    lines: list[str] = []
    for seg in segments:
        start = _ms_to_srt_timestamp(seg["start_ms"])
        end = _ms_to_srt_timestamp(seg["end_ms"])
        text = seg.get("translated_text") or seg.get("text", "")
        lines.append(str(seg["sequence"]))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def _ms_to_srt_timestamp(ms: int) -> str:
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1_000
    ms %= 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
