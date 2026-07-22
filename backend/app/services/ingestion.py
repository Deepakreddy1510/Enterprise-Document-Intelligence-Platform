from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Document, DocumentChunk
from app.services.embeddings import embed
from app.services.pdf import chunk_pages, extract_pages


async def process_document(document_id: str) -> None:
    async with SessionLocal() as s:
        doc = await s.scalar(select(Document).where(Document.id == document_id))
        if not doc or doc.status not in {"pending", "processing"}:
            return
        doc.status = "processing"
        await s.commit()
        try:
            pages = extract_pages(str(get_settings().upload_directory / doc.stored_filename))
            chunks = chunk_pages(
                doc.id,
                pages,
                get_settings().chunk_target_tokens,
                get_settings().chunk_max_tokens,
                get_settings().chunk_overlap_tokens,
                get_settings().chunk_min_tokens,
            )
            if not chunks:
                raise ValueError("No useful text chunks were found")
            vectors = embed([c.content for c in chunks])
            await s.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
            s.add_all(
                [
                    DocumentChunk(
                        id=c.id,
                        document_id=doc.id,
                        chunk_index=c.chunk_index,
                        content=c.content,
                        page_number=c.page_number,
                        token_count=c.token_count,
                        character_count=len(c.content),
                        embedding=v,
                        embedding_model=get_settings().embedding_model,
                        chunking_configuration="sentence-aware-v1",
                    )
                    for c, v in zip(chunks, vectors, strict=True)
                ]
            )
            doc.status = "ready"
            doc.page_count = len(pages)
            doc.chunk_count = len(chunks)
            doc.processing_error = None
        except Exception as exc:
            doc.status = "failed"
            doc.processing_error = str(exc)[:500]
        await s.commit()
