"""Tests for Supabase repository update/select behavior."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.integrations.supabase.database import RepositoryError, SupabaseRepository


def _mock_response(data: list):
    resp = MagicMock()
    resp.data = data
    return resp


@pytest.mark.asyncio
async def test_update_video_requires_select_to_return_row():
    video_id = uuid.uuid4()
    row = {
        "id": str(video_id),
        "title": "Test",
        "description": "",
        "original_video_key": "video/x/original.mp4",
        "thumbnail_key": None,
        "voice_key": None,
        "music_key": None,
        "srt_key": "video/x/source.srt",
        "duration_ms": None,
        "status": "draft",
        "result_meta": None,
        "created_by": str(uuid.uuid4()),
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }

    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.execute.return_value = _mock_response([row])

    table = MagicMock()
    table.update.return_value = chain

    client = MagicMock()
    client.table.return_value = table

    repo = SupabaseRepository(client=client)
    result = await repo.update_video(video_id, original_video_key="video/x/original.mp4")

    assert result.id == video_id
    table.update.assert_called_once()
    chain.select.assert_called_once_with("*")
    chain.eq.assert_called_once_with("id", str(video_id))


@pytest.mark.asyncio
async def test_update_video_raises_when_no_rows_matched():
    video_id = uuid.uuid4()

    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.execute.return_value = _mock_response([])

    client = MagicMock()
    client.table.return_value.update.return_value = chain

    repo = SupabaseRepository(client=client)

    with pytest.raises(RepositoryError, match="Video returned no rows"):
        await repo.update_video(video_id, title="Missing")
