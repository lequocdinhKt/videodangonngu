"""ARQ worker for background pipeline processing."""

from __future__ import annotations

from arq.connections import RedisSettings

from app.config.settings import get_settings
from app.workers.pipeline_worker import run_pipeline


async def process_video(ctx, video_id: str, language_codes: list[str] | None = None) -> None:
    await run_pipeline(video_id, language_codes)


class WorkerSettings:
    functions = [process_video]

    @staticmethod
    def redis_settings() -> RedisSettings:
        settings = get_settings()
        return RedisSettings.from_dsn(settings.redis_url)


async def startup(ctx) -> None:
    from app.config.logging import setup_logging
    setup_logging()


async def shutdown(ctx) -> None:
    pass
