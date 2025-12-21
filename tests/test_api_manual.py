"""Tests for the manual context ingestion API endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from ai_wingman.api.manual import app


@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_manual_context_endpoint(clean_db):
    """Manual API should accept payloads and persist context."""

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/context/manual",
            json={
                "content": "Manual API content",
                "user_id": "api-user",
                "metadata": {"origin": "api-test"},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is True
    assert payload["version"] == 1
    assert payload["record_id"]
