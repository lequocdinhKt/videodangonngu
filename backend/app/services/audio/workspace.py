import shutil
from pathlib import Path
from uuid import UUID

from app.config.logging import get_logger
from app.config.settings import get_settings

logger = get_logger(__name__)

_TEMP_GLOBS = (
    "voice_*.mp3",
    "mixed_*.mp3",
    "vi_mixed.mp3",
    "extracted_audio.mp3",
    "*_work.mp3",
    "concat_list.txt",
)


def workspace_root(video_id: str | UUID) -> Path:
    settings = get_settings()
    root = Path(settings.workspace_dir) / str(video_id)
    root.mkdir(parents=True, exist_ok=True)
    return root


def compute_timeline_duration_ms(video_duration_ms: int | None, srt_end_ms: int) -> int:
    """Timeline must be at least as long as the source video when duration is known."""
    video_ms = video_duration_ms or 0
    if video_ms <= 0:
        return max(srt_end_ms, 0)
    return max(srt_end_ms, video_ms)


def cleanup_workspace(video_id: str | UUID) -> None:
    """Remove temporary workspace artifacts; never delete final subtitle/audio assets."""
    root = workspace_root(video_id)
    if not root.exists():
        return

    for subdir in ("segments", "timeline_work"):
        path = root / subdir
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    for pattern in _TEMP_GLOBS:
        for path in root.glob(pattern):
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Failed to remove workspace temp file %s: %s", path, exc)

    logger.debug("Cleaned workspace for video %s", video_id)
