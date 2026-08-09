import asyncio
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentChunk
from app.services.embeddings import embed


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    rank: int
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int
    chunk_index: int
    content: str
    similarity: float


class RetrievalService:
    async def retrieve(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        document_ids: list[uuid.UUID],
        query: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            raise ValueError("Query cannot be blank")
        if not document_ids:
            raise ValueError("At least one document must be selected")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        query_vector = (await asyncio.to_thread(embed, [query]))[0]
        statement = (
            select(
                DocumentChunk,
                Document,
                (1 - DocumentChunk.embedding.cosine_distance(query_vector)).label("similarity"),
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(Document.user_id == user_id, DocumentChunk.document_id.in_(document_ids))
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(top_k)
        )
        rows = (await session.execute(statement)).all()
        seen: set[str] = set()
        results: list[RetrievedChunk] = []
        for chunk, document, similarity in rows:
            if chunk.content in seen:
                continue
            seen.add(chunk.content)
            results.append(
                RetrievedChunk(
                    rank=len(results) + 1,
                    chunk_id=chunk.id,
                    document_id=document.id,
                    document_name=document.original_filename,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    similarity=float(similarity),
                )
            )
        return results
