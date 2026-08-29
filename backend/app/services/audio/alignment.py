from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from app.config.logging import get_logger
from app.config.settings import get_settings
from app.services.audio.ffmpeg_service import FFmpegService

logger = get_logger(__name__)


@dataclass
class AlignmentResult:
    speed_factor: float
    silence_added_ms: float
    status: Literal["completed", "warning", "needs_retranslate", "alignment_failed"]
    warning: Optional[str] = None
    final_duration_ms: int = 0
    tts_duration_ms: int = 0
    target_duration_ms: int = 0


def compute_alignment(
    tts_duration_ms: int,
    target_duration_ms: int,
    max_speed: float | None = None,
    retry_threshold: float | None = None,
) -> AlignmentResult:
    settings = get_settings()
    max_speed = max_speed or settings.max_speed_factor
    retry_threshold = retry_threshold or settings.alignment_retry_threshold

    if target_duration_ms <= 0:
        return AlignmentResult(
            speed_factor=1.0, silence_added_ms=0.0, status="warning",
            warning="Target duration is zero", final_duration_ms=tts_duration_ms,
            tts_duration_ms=tts_duration_ms, target_duration_ms=target_duration_ms,
        )

    ratio = tts_duration_ms / target_duration_ms

    if tts_duration_ms <= target_duration_ms:
        return AlignmentResult(
            speed_factor=1.0,
            silence_added_ms=float(target_duration_ms - tts_duration_ms),
            status="completed",
            final_duration_ms=target_duration_ms,
            tts_duration_ms=tts_duration_ms,
            target_duration_ms=target_duration_ms,
        )

    if ratio <= max_speed:
        return AlignmentResult(
            speed_factor=ratio, silence_added_ms=0.0, status="completed",
            final_duration_ms=target_duration_ms,
            tts_duration_ms=tts_duration_ms, target_duration_ms=target_duration_ms,
        )

    if ratio <= retry_threshold:
        return AlignmentResult(
            speed_factor=max_speed,
            silence_added_ms=max(0.0, float(target_duration_ms - int(tts_duration_ms / max_speed))),
            status="warning",
            warning=f"Required {ratio:.2f}x speed, capped at {max_speed}x",
            final_duration_ms=target_duration_ms,
            tts_duration_ms=tts_duration_ms,
            target_duration_ms=target_duration_ms,
        )

    return AlignmentResult(
        speed_factor=max_speed, silence_added_ms=0.0, status="needs_retranslate",
        warning=f"Ratio {ratio:.2f}x exceeds threshold {retry_threshold}; needs shorter translation",
        final_duration_ms=int(tts_duration_ms / max_speed),
        tts_duration_ms=tts_duration_ms, target_duration_ms=target_duration_ms,
    )


def apply_alignment(
    ffmpeg: FFmpegService,
    input_path: Path,
    output_path: Path,
    target_duration_ms: int,
) -> AlignmentResult:
    settings = get_settings()
    actual_ms = ffmpeg.get_duration_ms(input_path)
    match = compute_alignment(actual_ms, target_duration_ms)

    logger.info(
        "[ALIGNMENT] target=%dms tts=%dms speed=%.2fx status=%s",
        target_duration_ms, actual_ms, match.speed_factor, match.status,
    )

    if match.status == "needs_retranslate":
        match.final_duration_ms = actual_ms
        return match

    work_path = output_path.parent / f"{output_path.stem}_work.mp3"
    current = input_path

    if match.speed_factor != 1.0:
        ffmpeg.change_tempo(current, work_path, match.speed_factor)
        current = work_path

    if match.silence_added_ms > 0:
        ffmpeg.add_silence(current, output_path, int(match.silence_added_ms))
    elif current != output_path:
        ffmpeg.export_mp3(current, output_path)
    else:
        ffmpeg.export_mp3(input_path, output_path)

    if work_path.exists() and work_path != output_path:
        work_path.unlink(missing_ok=True)

    match.final_duration_ms = ffmpeg.get_duration_ms(output_path)
    return match
