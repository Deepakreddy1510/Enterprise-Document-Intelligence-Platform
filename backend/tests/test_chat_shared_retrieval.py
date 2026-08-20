import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.routes import Ask, message
from app.models import Conversation, User
from app.services.retrieval import RetrievalService


@pytest.mark.asyncio
async def test_chat_uses_shared_retrieval_and_does_not_invoke_ragas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(id=uuid.uuid4(), email="owner@example.com", password_hash="hash")
    conversation = Conversation(id=uuid.uuid4(), user_id=user.id, title="test")
    document_id = uuid.uuid4()
    session = MagicMock()
    session.scalar = AsyncMock(return_value=conversation)
    selected = MagicMock()
    selected.all.return_value = [document_id]
    session.scalars = AsyncMock(return_value=selected)
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    retrieve = AsyncMock(return_value=[])
    ragas = AsyncMock(side_effect=AssertionError("RAGAS must not run during chat"))
    monkeypatch.setattr(RetrievalService, "retrieve", retrieve)
    monkeypatch.setattr("app.evaluation.ragas_eval.RagasEvaluator.evaluate", ragas)

    response = await message(conversation.id, Ask(content="question"), user, session)

    retrieve.assert_awaited_once_with(session, user.id, [document_id], "question", 6)
    ragas.assert_not_awaited()
    assert response["sources"] == []


@pytest.mark.asyncio
async def test_retrieval_statement_contains_ownership_and_selected_document_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock()
    execution = MagicMock()
    execution.all.return_value = []
    session.execute = AsyncMock(return_value=execution)

    async def fake_to_thread(function: object, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384]

    monkeypatch.setattr("app.services.retrieval.asyncio.to_thread", fake_to_thread)
    user_id, document_id = uuid.uuid4(), uuid.uuid4()
    await RetrievalService().retrieve(session, user_id, [document_id], "question", 5)
    statement = session.execute.await_args.args[0]
    sql = str(statement)
    assert "documents.user_id" in sql
    assert "document_chunks.document_id IN" in sql
