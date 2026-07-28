import os
import uuid

import pytest
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models import Document, DocumentChunk, User
from app.services.retrieval import RetrievalService

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 with migrated PostgreSQL/pgvector",
    ),
]


@pytest.mark.asyncio
async def test_retrieval_enforces_owner_and_selected_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id, other_id = uuid.uuid4(), uuid.uuid4()
    selected_id, unselected_id, other_document_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    selected_chunk_id, unselected_chunk_id, other_chunk_id = (
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
    )
    vector = [0.0] * 383 + [1.0]

    async def fake_to_thread(function: object, texts: list[str]) -> list[list[float]]:
        return [vector]

    monkeypatch.setattr("app.services.retrieval.asyncio.to_thread", fake_to_thread)
    async with SessionLocal() as session:
        session.add_all(
            [
                User(id=owner_id, email=f"owner-{owner_id}@example.com", password_hash="x"),
                User(id=other_id, email=f"other-{other_id}@example.com", password_hash="x"),
                Document(
                    id=selected_id,
                    user_id=owner_id,
                    original_filename="selected.pdf",
                    stored_filename=f"{selected_id}.pdf",
                    file_size=1,
                    checksum=uuid.uuid4().hex,
                    status="ready",
                ),
                Document(
                    id=unselected_id,
                    user_id=owner_id,
                    original_filename="unselected.pdf",
                    stored_filename=f"{unselected_id}.pdf",
                    file_size=1,
                    checksum=uuid.uuid4().hex,
                    status="ready",
                ),
                Document(
                    id=other_document_id,
                    user_id=other_id,
                    original_filename="other.pdf",
                    stored_filename=f"{other_document_id}.pdf",
                    file_size=1,
                    checksum=uuid.uuid4().hex,
                    status="ready",
                ),
            ]
        )
        await session.flush()
        for chunk_id, document_id, content in (
            (selected_chunk_id, selected_id, "selected content"),
            (unselected_chunk_id, unselected_id, "unselected content"),
            (other_chunk_id, other_document_id, "other owner content"),
        ):
            session.add(
                DocumentChunk(
                    id=chunk_id,
                    document_id=document_id,
                    chunk_index=0,
                    content=content,
                    page_number=1,
                    token_count=2,
                    character_count=len(content),
                    embedding=vector,
                    embedding_model="test",
                    chunking_configuration="test",
                )
            )
        await session.commit()
        try:
            results = await RetrievalService().retrieve(
                session, owner_id, [selected_id], "question", 5
            )
            assert [item.chunk_id for item in results] == [selected_chunk_id]
        finally:
            await session.execute(delete(User).where(User.id.in_([owner_id, other_id])))
            await session.commit()
