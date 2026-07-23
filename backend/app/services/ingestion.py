import asyncio

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Document, DocumentChunk
from app.services.embeddings import embed, split_tokens, token_count
from app.services.pdf import chunk_pages, extract_pages


async def _mark_failed(document_id: str, message: str) -> None:
    """Use a fresh session so a failed write never reuses a rolled-back transaction."""
    async with SessionLocal() as session:
        document = await session.scalar(select(Document).where(Document.id == document_id))
        if document is None:
            return
        document.status = "failed"
        document.processing_error = message[:500]
        await session.commit()


async def process_document(document_id: str) -> None:
    try:
        async with SessionLocal() as session:
            document = await session.scalar(select(Document).where(Document.id == document_id))
            if document is None or document.status not in {"pending", "processing"}:
                return
            document.status = "processing"
            document.processing_error = None
            await session.commit()
            document_id_value = document.id
            filename = document.stored_filename
    except Exception:
        await _mark_failed(document_id, "Document processing could not start. Please retry.")
        return

    try:
        settings = get_settings()
        pages = await asyncio.to_thread(extract_pages, str(settings.upload_directory / filename))
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
            raise ValueError("No useful text chunks were found")
        vectors = await asyncio.to_thread(embed, [chunk.content for chunk in chunks])
    except Exception as exc:
        await _mark_failed(document_id, str(exc) or "Document processing failed. Please retry.")
        return

    try:
        async with SessionLocal() as session:
            document = await session.scalar(select(Document).where(Document.id == document_id))
            if document is None or document.status != "processing":
                return
            await session.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
            )
            session.add_all(
                [
                    DocumentChunk(
                        id=chunk.id,
                        document_id=document.id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        token_count=chunk.token_count,
                        character_count=len(chunk.content),
                        embedding=vector,
                        embedding_model=settings.embedding_model,
                        chunking_configuration="sentence-aware-tokenizer-v1",
                    )
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ]
            )
            document.status = "ready"
            document.page_count = len(pages)
            document.chunk_count = len(chunks)
            document.processing_error = None
            await session.commit()
    except Exception:
        await _mark_failed(document_id, "Indexing failed. Please retry the document.")
