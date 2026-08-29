from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, public
from app.config.logging import setup_logging
from app.config.settings import get_settings
from app.core.auth import ensure_admin_user
from app.integrations.supabase.database import get_repository
from app.services.audio.ffmpeg_service import FFmpegService


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    settings.validate_production_config()
    repo = get_repository()
    await ensure_admin_user(repo)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Video Localization Platform", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(admin.router)
    app.include_router(public.router)

    @app.get("/api/health")
    async def health():
        ffmpeg = FFmpegService()
        return {
            "status": "ok",
            "ffmpeg": ffmpeg.is_available(),
        }

    return app


app = create_app()
