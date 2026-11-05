import re
from dataclasses import dataclass


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]


def validate_translation(
    source_segments: list[dict],
    translated_segments: list[dict],
) -> ValidationResult:
    errors: list[str] = []

    if len(source_segments) != len(translated_segments):
        errors.append(
            f"Segment count mismatch: source={len(source_segments)} translated={len(translated_segments)}"
        )

    for i, (src, tr) in enumerate(zip(source_segments, translated_segments)):
        seq = src.get("sequence", i + 1)
        if not tr.get("translated_text", "").strip():
            errors.append(f"Segment {seq}: empty translation")
        if src.get("start_ms") != tr.get("start_ms") or src.get("end_ms") != tr.get("end_ms"):
            errors.append(f"Segment {seq}: timestamp mismatch")
        src_nums = set(re.findall(r"\d+(?:[.,]\d+)?", src.get("source_text", "")))
        tr_text = tr.get("translated_text", "")
        for num in src_nums:
            normalized = num.replace(",", ".")
            if num not in tr_text and normalized not in tr_text:
                errors.append(f"Segment {seq}: possible missing number '{num}'")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_srt_structure(subtitles: list) -> ValidationResult:
    errors: list[str] = []
    prev_end = 0
    for sub in subtitles:
        if sub.end_ms <= sub.start_ms:
            errors.append(f"Subtitle {sub.index}: invalid time range")
        if sub.start_ms < prev_end:
            errors.append(f"Subtitle {sub.index}: overlaps previous subtitle")
        prev_end = sub.end_ms
        if not sub.text.strip():
            errors.append(f"Subtitle {sub.index}: empty text")
    return ValidationResult(valid=len(errors) == 0, errors=errors)
