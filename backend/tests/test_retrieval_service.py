import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.retrieval import RetrievalService


@pytest.mark.asyncio
async def test_retrieval_offloads_query_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_to_thread(function: object, texts: list[str]) -> list[list[float]]:
        assert texts == ["question"]
        return [[0.0] * 384]

    execution = MagicMock()
    execution.all.return_value = []
    session = AsyncMock()
    session.execute.return_value = execution
    monkeypatch.setattr("app.services.retrieval.asyncio.to_thread", fake_to_thread)
    results = await RetrievalService().retrieve(
        session, uuid.uuid4(), [uuid.uuid4()], "question", 5
    )
    assert results == []
    session.execute.assert_awaited_once()
