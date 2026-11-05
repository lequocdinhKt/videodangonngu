"""Shared pytest configuration."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest

import app.config.settings as settings_mod
import app.integrations.supabase.database as db_mod
from app.integrations.supabase.client import reset_supabase_client
from app.services.storage.local import reset_storage
from tests.mock_repository import InMemoryRepository


def pytest_configure(config: pytest.Config) -> None:
    os.environ["SKIP_SUPABASE_VALIDATION"] = "true"
    os.environ["STORAGE_PROVIDER"] = "local"
    os.environ["STORAGE_DIR"] = "./test_storage"
    settings_mod._settings = None
    reset_supabase_client()
    reset_storage()


@pytest.fixture
def memory_repo(monkeypatch) -> InMemoryRepository:
    repo = InMemoryRepository()
    monkeypatch.setattr(db_mod, "_repo", repo)
    yield repo
    db_mod.reset_repository()


@pytest.fixture
async def app_client(memory_repo: InMemoryRepository) -> AsyncIterator:
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
