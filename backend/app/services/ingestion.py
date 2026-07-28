import asyncio
import logging

from sqlalchemy import delete, insert, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Document, DocumentChunk
from app.services.embeddings import embed, split_tokens, token_count
from app.services.pdf import chunk_pages, extract_pages

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 32
DATABASE_BATCH_SIZE = 100


async def _mark_failed(document_id: str, message: str) -> None:
    """Record a processing failure with a fresh database session."""
    async with SessionLocal() as session:
        document = await session.scalar(
            select(Document).where(Document.id == document_id)
        )

        if document is None:
            return

        document.status = "failed"
        document.processing_error = message[:500]
        await session.commit()


async def process_document(document_id: str) -> None:
    try:
        async with SessionLocal() as session:
            document = await session.scalar(
                select(Document).where(Document.id == document_id)
            )

            if document is None or document.status not in {
                "pending",
                "processing",
            }:
                return

            document.status = "processing"
            document.processing_error = None
            await session.commit()

            document_id_value = document.id
            filename = document.stored_filename

    except Exception as exc:
        logger.exception(
            "Document processing could not start for document %s",
            document_id,
        )
        await _mark_failed(
            document_id,
            f"Processing could not start: {type(exc).__name__}: {exc}",
        )
        return

    try:
        settings = get_settings()

        pages = await asyncio.to_thread(
            extract_pages,
            str(settings.upload_directory / filename),
        )

        chunks = await asyncio.to_thread(
            chunk_pages,
            document_id_value,
            pages,
            settings.chunk_target_tokens,
            settings.chunk_max_tokens,
            settings.chunk_overlap_tokens,
            settings.chunk_min_tokens,
            token_count,
            split_tokens,
        )

        if not chunks:
            raise ValueError(
                "No useful text chunks were found. "
                "The PDF may be scanned or contain no extractable text."
            )

    except Exception as exc:
        logger.exception(
            "PDF extraction or chunking failed for document %s",
            document_id,
        )
        await _mark_failed(
            document_id,
            f"PDF processing failed: {type(exc).__name__}: {exc}",
        )
        return

    try:
        vectors: list[list[float]] = []

        for offset in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[offset : offset + EMBED_BATCH_SIZE]
            batch_texts = [chunk.content for chunk in batch]

            batch_vectors = await asyncio.to_thread(
                embed,
                batch_texts,
            )
            vectors.extend(batch_vectors)

        if len(vectors) != len(chunks):
            raise RuntimeError(
                "The embedding count does not match the chunk count."
            )

    except Exception as exc:
        logger.exception(
            "Embedding generation failed for document %s",
            document_id,
        )
        await _mark_failed(
            document_id,
            f"Embedding failed: {type(exc).__name__}: {exc}",
        )
        return

    try:
        async with SessionLocal() as session:
            document = await session.scalar(
                select(Document).where(Document.id == document_id)
            )

            if document is None or document.status != "processing":
                return

            await session.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.document_id == document.id
                )
            )

            pending_rows: list[dict[str, object]] = []

            for chunk, vector in zip(chunks, vectors, strict=True):
                pending_rows.append(
                    {
                        "id": chunk.id,
                        "document_id": document.id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "page_number": chunk.page_number,
                        "token_count": chunk.token_count,
                        "character_count": len(chunk.content),
                        "embedding": vector,
                        "embedding_model": settings.embedding_model,
                        "chunking_configuration": (
                            "sentence-aware-tokenizer-v1"
                        ),
                    }
                )

                if len(pending_rows) >= DATABASE_BATCH_SIZE:
                    await session.execute(
                        insert(DocumentChunk.__table__),
                        pending_rows,
                    )
                    pending_rows = []

            if pending_rows:
                await session.execute(
                    insert(DocumentChunk.__table__),
                    pending_rows,
                )

            document.status = "ready"
            document.page_count = len(pages)
            document.chunk_count = len(chunks)
            document.processing_error = None

            await session.commit()

            logger.info(
                "Indexed document %s: %d pages and %d chunks",
                document_id,
                len(pages),
                len(chunks),
            )

    except Exception as exc:
        logger.exception(
            "Database indexing failed for document %s",
            document_id,
        )
        await _mark_failed(
            document_id,
            f"Indexing failed: {type(exc).__name__}: {exc}",
        )