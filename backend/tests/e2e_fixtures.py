"""Generate minimal real media fixtures for E2E pipeline tests via FFmpeg."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

SAMPLE_SRT = """1
00:00:01,000 --> 00:00:04,000
Xin chào và chào mừng bạn đến Hội An.

2
00:00:04,500 --> 00:00:08,000
Đây là thành phố cổ tuyệt đẹp.
"""

DURATION_SEC = 8


@dataclass
class E2EFixtures:
    video: Path
    srt: Path
    voice: Path
    music: Path


def _run_ffmpeg(args: list[str], ffmpeg: str = "ffmpeg") -> None:
    cmd = [ffmpeg, "-y", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr.strip()}")


def generate_fixtures(output_dir: Path, ffmpeg: str = "ffmpeg") -> E2EFixtures:
    output_dir.mkdir(parents=True, exist_ok=True)

    srt_path = output_dir / "test.srt"
    srt_path.write_text(SAMPLE_SRT, encoding="utf-8")

    video_path = output_dir / "test.mp4"
    _run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c=black:s=640x360:d={DURATION_SEC}",
        "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100:duration={DURATION_SEC}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        str(video_path),
    ], ffmpeg)

    voice_path = output_dir / "voice_vi.mp3"
    _run_ffmpeg([
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={DURATION_SEC}",
        "-codec:a", "libmp3lame", "-q:a", "2",
        str(voice_path),
    ], ffmpeg)

    music_path = output_dir / "music.mp3"
    _run_ffmpeg([
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={DURATION_SEC}",
        "-codec:a", "libmp3lame", "-q:a", "2",
        str(music_path),
    ], ffmpeg)

    return E2EFixtures(video=video_path, srt=srt_path, voice=voice_path, music=music_path)


def ffmpeg_available(ffmpeg: str = "ffmpeg") -> bool:
    try:
        result = subprocess.run([ffmpeg, "-version"], capture_output=True, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        return False
