"""Translation factory tests."""

import pytest

import app.config.settings as settings_mod
from app.services.translation.factory import get_translation_provider, validate_translation_config


def _reset_settings():
    settings_mod._settings = None


def test_get_groq_provider(monkeypatch):
    monkeypatch.setenv("TRANSLATION_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key")
    _reset_settings()

    provider = get_translation_provider()
    assert provider.provider_name == "groq"


def test_validate_groq_missing_key(monkeypatch):
    monkeypatch.setenv("TRANSLATION_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")
    _reset_settings()

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        validate_translation_config()
