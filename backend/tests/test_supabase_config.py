"""Supabase configuration validation tests."""

from __future__ import annotations

import os

import pytest

import app.config.settings as settings_mod
from app.integrations.supabase.client import get_supabase_client, reset_supabase_client


@pytest.fixture(autouse=True)
def _reset_settings():
    settings_mod._settings = None
    reset_supabase_client()
    yield
    settings_mod._settings = None
    reset_supabase_client()


def test_validate_supabase_config_requires_url_and_key():
    os.environ["SKIP_SUPABASE_VALIDATION"] = "false"
    os.environ["SUPABASE_URL"] = ""
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
    settings = settings_mod.Settings()
    with pytest.raises(ValueError, match="SUPABASE_URL"):
        settings.validate_supabase_config()


def test_validate_supabase_config_passes_when_complete():
    os.environ["SUPABASE_URL"] = "https://example.supabase.co"
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"
    os.environ["SUPABASE_STORAGE_BUCKET"] = "video-assets"
    settings = settings_mod.Settings()
    settings.validate_supabase_config()


def test_skip_supabase_validation_for_tests():
    os.environ["SKIP_SUPABASE_VALIDATION"] = "true"
    os.environ["SUPABASE_URL"] = ""
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
    settings = settings_mod.Settings()
    settings.validate_supabase_config()


def test_production_guard_rejects_weak_jwt():
    os.environ["ENV"] = "production"
    os.environ["JWT_SECRET"] = "change-me-in-production"
    os.environ["SUPABASE_URL"] = "https://example.supabase.co"
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "key"
    settings = settings_mod.Settings()
    with pytest.raises(ValueError, match="JWT_SECRET"):
        settings.validate_production_config()


def test_get_supabase_client_singleton(monkeypatch):
    os.environ["SKIP_SUPABASE_VALIDATION"] = "false"
    os.environ["SUPABASE_URL"] = "https://example.supabase.co"
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-key"

    created: list[object] = []

    def fake_create(url, key):
        client = object()
        created.append(client)
        return client

    import supabase as supabase_mod

    monkeypatch.setattr(supabase_mod, "create_client", fake_create)

    first = get_supabase_client()
    second = get_supabase_client()
    assert first is second
    assert len(created) == 1
