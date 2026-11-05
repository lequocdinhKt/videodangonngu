import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.config.settings import get_settings
from app.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TimelineSegment:
    path: Path
    start_ms: int
    duration_ms: int


class FFmpegService:
    def __init__(self) -> None:
        settings = get_settings()
        self.ffmpeg = settings.ffmpeg_path
        self.ffprobe = settings.ffprobe_path

    def is_available(self) -> bool:
        try:
            result = subprocess.run([self.ffmpeg, "-version"], capture_output=True, check=False)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _run(self, args: list[str], timeout: int = 300) -> None:
        cmd = [self.ffmpeg, "-y", *args]
        logger.debug("FFmpeg: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr.strip()}")

    def get_duration_ms(self, path: Path) -> int:
        result = subprocess.run(
            [
                self.ffprobe, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
        return int(round(float(result.stdout.strip()) * 1000))

    def extract_audio(self, video_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["-i", str(video_path), "-vn", "-codec:a", "libmp3lame", "-q:a", "2", str(output_path)])
        return output_path

    def extract_thumbnail(self, video_path: Path, output_path: Path, time_sec: float = 1.0) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["-ss", str(time_sec), "-i", str(video_path), "-vframes", "1", "-q:v", "2", str(output_path)])
        return output_path

    def add_silence(self, input_path: Path, output_path: Path, pad_ms: int) -> Path:
        if pad_ms <= 0:
            self.export_mp3(input_path, output_path)
            return output_path
        pad_sec = pad_ms / 1000.0
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["-i", str(input_path), "-af", f"apad=pad_dur={pad_sec:.6f}", "-codec:a", "libmp3lame", "-q:a", "2", str(output_path)])
        return output_path

    def change_tempo(self, input_path: Path, output_path: Path, factor: float) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        factor = max(0.5, min(2.0, factor))
        self._run(["-i", str(input_path), "-filter:a", f"atempo={factor:.6f}", "-codec:a", "libmp3lame", "-q:a", "2", str(output_path)])
        return output_path

    def normalize_audio(self, input_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["-i", str(input_path), "-af", "loudnorm", "-codec:a", "libmp3lame", "-q:a", "2", str(output_path)])
        return output_path

    def export_mp3(self, input_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["-i", str(input_path), "-codec:a", "libmp3lame", "-q:a", "2", str(output_path)])
        return output_path

    def generate_silence(self, output_path: Path, duration_ms: int) -> Path:
        duration_sec = duration_ms / 1000.0
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run([
            "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100:duration={duration_sec:.6f}",
            "-codec:a", "libmp3lame", "-q:a", "2", str(output_path),
        ])
        return output_path

    def concat_segments(self, segments: list[Path], output_path: Path) -> Path:
        if not segments:
            raise ValueError("No segments to concatenate")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        list_file = output_path.parent / "concat_list.txt"
        lines = [f"file '{str(seg.resolve()).replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'" for seg in segments]
        list_file.write_text("\n".join(lines), encoding="utf-8")
        self._run(["-f", "concat", "-safe", "0", "-i", str(list_file), "-codec:a", "libmp3lame", "-q:a", "2", str(output_path)], timeout=600)
        list_file.unlink(missing_ok=True)
        return output_path

    def trim_to_duration(self, input_path: Path, output_path: Path, duration_ms: int) -> Path:
        if duration_ms <= 0:
            raise ValueError("Duration must be positive")
        duration_sec = duration_ms / 1000.0
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run([
            "-i", str(input_path),
            "-af", f"apad=whole_dur={duration_sec:.6f},atrim=0:{duration_sec:.6f}",
            "-codec:a", "libmp3lame", "-q:a", "2",
            str(output_path),
        ])
        return output_path

    def mix_voice_and_music(
        self,
        voice_path: Path,
        music_path: Path,
        output_path: Path,
        music_volume_db: float = -18.0,
        duration_ms: int | None = None,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        voice_ms = duration_ms or self.get_duration_ms(voice_path)
        duration_sec = voice_ms / 1000.0
        filter_complex = (
            f"[0:a]atrim=0:{duration_sec:.6f},asetpts=PTS-STARTPTS[voice];"
            f"[1:a]volume={music_volume_db}dB,atrim=0:{duration_sec:.6f},asetpts=PTS-STARTPTS[music];"
            f"[voice][music]amix=inputs=2:duration=first:dropout_transition=0"
        )
        self._run([
            "-i", str(voice_path), "-i", str(music_path),
            "-filter_complex", filter_complex,
            "-t", f"{duration_sec:.6f}",
            "-codec:a", "libmp3lame", "-q:a", "2", str(output_path),
        ])
        return output_path

    def place_on_timeline(self, segments: list[TimelineSegment], total_ms: int, output_path: Path) -> Path:
        if total_ms <= 0:
            raise ValueError("Total duration must be positive")
        work_dir = output_path.parent / "timeline_work"
        work_dir.mkdir(parents=True, exist_ok=True)
        ordered: list[Path] = []
        cursor_ms = 0

        for i, seg in enumerate(segments):
            if seg.start_ms > cursor_ms:
                gap_path = work_dir / f"gap_{i}.mp3"
                self.generate_silence(gap_path, seg.start_ms - cursor_ms)
                ordered.append(gap_path)
                cursor_ms = seg.start_ms
            ordered.append(seg.path)
            cursor_ms = seg.start_ms + seg.duration_ms

        if cursor_ms < total_ms:
            tail_path = work_dir / "tail_silence.mp3"
            self.generate_silence(tail_path, total_ms - cursor_ms)
            ordered.append(tail_path)

        return self.concat_segments(ordered, output_path)
