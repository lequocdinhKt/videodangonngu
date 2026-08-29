from pathlib import Path

from app.services.audio.ffmpeg_service import FFmpegService, TimelineSegment


def assemble_language_track(
    ffmpeg: FFmpegService,
    segments: list[dict],
    segment_audio_paths: dict[int, Path],
    total_ms: int,
    output_path: Path,
) -> Path:
    timeline_segments: list[TimelineSegment] = []
    for seg in sorted(segments, key=lambda s: s["sequence"]):
        audio_path = segment_audio_paths.get(seg["sequence"])
        if audio_path and audio_path.exists():
            duration_ms = ffmpeg.get_duration_ms(audio_path)
            timeline_segments.append(
                TimelineSegment(path=audio_path, start_ms=seg["start_ms"], duration_ms=duration_ms)
            )
    return ffmpeg.place_on_timeline(timeline_segments, total_ms, output_path)
