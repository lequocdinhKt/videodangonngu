"""Centralized Supabase client — service role key, backend only."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config.settings import get_settings

if TYPE_CHECKING:
    from supabase import Client

_client: Client | None = None


def get_supabase_client() -> Client:
    """Return a singleton Supabase client using the service role key."""
    global _client
    if _client is None:
        settings = get_settings()
        settings.validate_supabase_config()
        from supabase import create_client

        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


def reset_supabase_client() -> None:
    """Clear cached client (for tests)."""
    global _client
    _client = None
