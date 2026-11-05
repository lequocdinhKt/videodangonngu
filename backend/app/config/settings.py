from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "development"
    skip_supabase_validation: bool = False

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    supabase_storage_bucket: str = "video-assets"
    signed_url_expires_seconds: int = 7200

    redis_url: str = "redis://localhost:6379"

    storage_provider: str = "supabase"
    storage_dir: str = "./storage"
    s3_bucket: str = ""
    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""

    jwt_secret: str = "replace-with-a-random-64-character-secret"
    jwt_expire_minutes: int = 1440
    admin_email: str = "admin@example.com"
    admin_password: str = "replace-with-a-strong-password"

    openai_api_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    translation_provider: str = "groq"
    translation_model: str = "gpt-4o"
    tts_provider: str = "edge"

    tts_voice_vi: str = "vi-VN-HoaiMyNeural"
    tts_voice_en: str = "en-US-JennyNeural"
    tts_voice_ru: str = "ru-RU-SvetlanaNeural"
    tts_voice_zh: str = "zh-CN-XiaoxiaoNeural"

    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    music_volume_db: float = -18.0
    voice_normalize: bool = True  # applied before final audio export when True
    max_speed_factor: float = 1.10
    alignment_retry_threshold: float = 1.30
    voice_separation_enabled: bool = True  # allows fallback audio extraction from video
    audio_drift_tolerance_ms: int = 100  # reserved for timeline drift checks

    cors_origins: str = "http://localhost:5173"
    public_base_url: str = "http://localhost:5173"

    use_arq: bool = False
    tts_concurrency: int = 3
    max_upload_mb: int = 500
    max_subtitle_mb: int = 5

    supported_languages: list[str] = ["vi-VN", "en-US", "ru-RU", "zh-CN"]
    target_languages: list[str] = ["en-US", "ru-RU", "zh-CN"]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def workspace_dir(self) -> str:
        return "./workspace"

    def validate_supabase_config(self) -> None:
        if self.skip_supabase_validation:
            return
        missing: list[str] = []
        if not self.supabase_url.strip():
            missing.append("SUPABASE_URL")
        if not self.supabase_service_role_key.strip():
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if self.storage_provider == "supabase" and not self.supabase_storage_bucket.strip():
            missing.append("SUPABASE_STORAGE_BUCKET")
        if missing:
            raise ValueError(
                f"Missing required Supabase configuration: {', '.join(missing)}. "
                "Set SKIP_SUPABASE_VALIDATION=true only in unit tests."
            )

    def validate_storage_config(self) -> None:
        if self.storage_provider not in ("s3", "r2"):
            return
        missing: list[str] = []
        if not self.s3_bucket.strip():
            missing.append("S3_BUCKET")
        if not self.s3_endpoint.strip():
            missing.append("S3_ENDPOINT")
        if not self.s3_access_key.strip():
            missing.append("S3_ACCESS_KEY")
        if not self.s3_secret_key.strip():
            missing.append("S3_SECRET_KEY")
        if missing:
            raise ValueError(
                f"Missing required R2/S3 storage configuration: {', '.join(missing)}. "
                "See huongdanchuyen.md for setup."
            )

    def validate_translation_config(self) -> None:
        if self.translation_provider == "groq" and not self.groq_api_key.strip():
            raise ValueError(
                "Missing GROQ_API_KEY. Set TRANSLATION_PROVIDER=groq and add key — see huongdan-groq.md"
            )
        if self.translation_provider == "openai" and not self.openai_api_key.strip():
            raise ValueError(
                "Missing OPENAI_API_KEY. Set TRANSLATION_PROVIDER=openai and add key."
            )

    def validate_production_config(self) -> None:
        if not self.is_production:
            return
        if self.jwt_secret.startswith(("change-me", "replace-with")):
            raise ValueError("JWT_SECRET must be changed in production")
        if self.admin_password.startswith("replace-with"):
            raise ValueError("ADMIN_PASSWORD must be changed in production")
        self.validate_supabase_config()
        self.validate_storage_config()


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
