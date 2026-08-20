import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_token, current_user, hash_password, verify_password
from app.db.session import get_session
from app.models import (
    Conversation,
    ConversationDocument,
    Document,
    DocumentChunk,
    Message,
    MessageSource,
    User,
)
from app.services.ingestion import process_document
from app.services.rag import generate_grounded_answer
from app.services.retrieval import RetrievalService

router = APIRouter()


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ConversationIn(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)


class Rename(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class DocIds(BaseModel):
    document_ids: list[uuid.UUID] = Field(min_length=1)


class Ask(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


def user_out(u: User):
    return {"id": str(u.id), "email": u.email}


def doc_out(d: Document):
    return {
        "id": str(d.id),
        "original_filename": d.original_filename,
        "status": d.status,
        "processing_error": d.processing_error,
        "page_count": d.page_count,
        "chunk_count": d.chunk_count,
        "created_at": d.created_at,
    }


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "api"}


@router.get("/readiness")
async def readiness(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ready", "dependencies": {"postgres": "ready"}}
    except Exception:
        raise HTTPException(503, "Database is not ready")


@router.post("/auth/register", status_code=201)
async def register(
    data: Credentials, response: Response, session: AsyncSession = Depends(get_session)
):
    if await session.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "Email is already registered")
    user = User(email=data.email.lower(), password_hash=hash_password(data.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    _set_cookie(response, create_token(str(user.id)))
    return user_out(user)


@router.post("/auth/login")
async def login(
    data: Credentials, response: Response, session: AsyncSession = Depends(get_session)
):
    user = await session.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    _set_cookie(response, create_token(str(user.id)))
    return user_out(user)


def _set_cookie(response: Response, token: str):
    s = get_settings()
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        samesite="none" if s.environment == "production" else "lax",
        secure=s.environment == "production",
        max_age=s.jwt_access_token_expire_minutes * 60,
        path="/",
    )


@router.post("/auth/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")


@router.get("/auth/me")
async def me(user: User = Depends(current_user)):
    return user_out(user)


@router.post("/documents", status_code=202)
async def upload(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    """Validate the whole batch before writing; clean files if its database write fails."""
    settings = get_settings()
    settings.upload_directory.mkdir(parents=True, exist_ok=True)
    candidates: list[tuple[str, bytes, str, str]] = []
    for file in files:
        name = Path(file.filename or "").name
        if not name.lower().endswith(".pdf") or file.content_type not in {
            "application/pdf",
            "application/x-pdf",
        }:
            raise HTTPException(415, "Only PDF files are accepted")
        content = await file.read()
        if not content:
            raise HTTPException(422, f"{name}: empty files are not accepted")
        if len(content) > settings.max_pdf_size_mb * 1024 * 1024:
            raise HTTPException(413, f"{name}: PDF exceeds the configured upload limit")
        checksum = hashlib.sha256(content).hexdigest()
        candidates.append((name, content, checksum, f"{uuid.uuid4()}.pdf"))
    checksums = [candidate[2] for candidate in candidates]
    if len(checksums) != len(set(checksums)):
        raise HTTPException(409, "The upload batch contains duplicate PDF content")
    existing = set(
        (
            await session.scalars(
                select(Document.checksum).where(
                    Document.user_id == user.id, Document.checksum.in_(checksums)
                )
            )
        ).all()
    )
    duplicate = next((name for name, _, checksum, _ in candidates if checksum in existing), None)
    if duplicate:
        raise HTTPException(409, f"Duplicate PDF: {duplicate}")
    written: list[Path] = []
    documents: list[Document] = []
    try:
        for name, content, checksum, stored in candidates:
            path = settings.upload_directory / stored
            path.write_bytes(content)
            written.append(path)
            document = Document(
                user_id=user.id,
                original_filename=name,
                stored_filename=stored,
                file_size=len(content),
                checksum=checksum,
                status="pending",
            )
            session.add(document)
            documents.append(document)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        for path in written:
            path.unlink(missing_ok=True)
        raise HTTPException(500, "The PDF batch could not be saved. Please try again.") from exc
    for document in documents:
        background.add_task(process_document, str(document.id))
    return [doc_out(document) for document in documents]


@router.get("/documents")
async def documents(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return [
        doc_out(x)
        for x in (
            await session.scalars(
                select(Document)
                .where(Document.user_id == user.id)
                .order_by(Document.created_at.desc())
            )
        ).all()
    ]


async def owned_document(document_id: uuid.UUID, user: User, session: AsyncSession) -> Document:
    doc = await session.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.get("/documents/{document_id}")
async def document(
    document_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return doc_out(await owned_document(document_id, user, session))


@router.get("/documents/{document_id}/status")
async def document_status(
    document_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return doc_out(await owned_document(document_id, user, session))


@router.post("/documents/{document_id}/retry", status_code=202)
async def retry(
    document_id: uuid.UUID,
    background: BackgroundTasks,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    d = await owned_document(document_id, user, session)
    if d.status != "failed":
        raise HTTPException(409, "Only failed documents can be retried")
    d.status = "pending"
    d.processing_error = None
    await session.commit()
    background.add_task(process_document, str(d.id))
    return doc_out(d)


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    d = await owned_document(document_id, user, session)
    path = get_settings().upload_directory / d.stored_filename
    await session.delete(d)
    await session.commit()
    path.unlink(missing_ok=True)


async def owned_conversation(cid: uuid.UUID, user: User, session: AsyncSession) -> Conversation:
    c = await session.scalar(
        select(Conversation).where(Conversation.id == cid, Conversation.user_id == user.id)
    )
    if not c:
        raise HTTPException(404, "Conversation not found")
    return c


@router.post("/conversations", status_code=201)
async def create_conversation(
    data: ConversationIn,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    c = Conversation(user_id=user.id, title=data.title)
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return {"id": str(c.id), "title": c.title, "documents": [], "messages": []}


@router.get("/conversations")
async def conversations(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return [
        {"id": str(c.id), "title": c.title, "created_at": c.created_at}
        for c in (
            await session.scalars(
                select(Conversation)
                .where(Conversation.user_id == user.id)
                .order_by(Conversation.updated_at.desc())
            )
        ).all()
    ]


@router.get("/conversations/{conversation_id}")
async def conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    c = await owned_conversation(conversation_id, user, session)
    ids = (
        await session.scalars(
            select(ConversationDocument.document_id).where(
                ConversationDocument.conversation_id == c.id
            )
        )
    ).all()
    msgs = (
        await session.scalars(
            select(Message).where(Message.conversation_id == c.id).order_by(Message.created_at)
        )
    ).all()
    return {
        "id": str(c.id),
        "title": c.title,
        "documents": [str(i) for i in ids],
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
                "sources": [
                    {
                        "citation_id": source.citation_id,
                        "page": source.page_number,
                        "similarity": source.similarity,
                        "content": source.content_snapshot,
                        "chunk_id": str(source.chunk_id),
                        "document_name": document_name,
                    }
                    for source, document_name in (
                        await session.execute(
                            select(MessageSource, Document.original_filename)
                            .join(DocumentChunk, MessageSource.chunk_id == DocumentChunk.id)
                            .join(Document, DocumentChunk.document_id == Document.id)
                            .where(MessageSource.message_id == m.id, Document.user_id == user.id)
                        )
                    ).all()
                ],
            }
            for m in msgs
        ],
    }


@router.patch("/conversations/{conversation_id}")
async def rename(
    conversation_id: uuid.UUID,
    data: Rename,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    c = await owned_conversation(conversation_id, user, session)
    c.title = data.title
    await session.commit()
    return {"id": str(c.id), "title": c.title}


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.delete(await owned_conversation(conversation_id, user, session))
    await session.commit()


@router.post("/conversations/{conversation_id}/documents")
async def set_docs(
    conversation_id: uuid.UUID,
    data: DocIds,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    c = await owned_conversation(conversation_id, user, session)
    docs = (
        await session.scalars(
            select(Document).where(
                Document.id.in_(data.document_ids),
                Document.user_id == user.id,
                Document.status == "ready",
            )
        )
    ).all()
    if len(docs) != len(set(data.document_ids)):
        raise HTTPException(422, "Every selected document must be owned and ready")
    await session.execute(
        delete(ConversationDocument).where(ConversationDocument.conversation_id == c.id)
    )
    session.add_all([ConversationDocument(conversation_id=c.id, document_id=d.id) for d in docs])
    await session.commit()
    return {"document_ids": [str(d.id) for d in docs]}


@router.delete("/conversations/{conversation_id}/documents/{document_id}", status_code=204)
async def remove_doc(
    conversation_id: uuid.UUID,
    document_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    c = await owned_conversation(conversation_id, user, session)
    await session.execute(
        delete(ConversationDocument).where(
            ConversationDocument.conversation_id == c.id,
            ConversationDocument.document_id == document_id,
        )
    )
    await session.commit()


@router.post("/conversations/{conversation_id}/messages")
async def message(
    conversation_id: uuid.UUID,
    data: Ask,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    c = await owned_conversation(conversation_id, user, session)
    ids = (
        await session.scalars(
            select(ConversationDocument.document_id).where(
                ConversationDocument.conversation_id == c.id
            )
        )
    ).all()
    if not ids:
        raise HTTPException(422, "Select at least one ready document before asking a question")
    retrieved = await RetrievalService().retrieve(
        session, user.id, list(ids), data.content, get_settings().retrieval_top_k
    )
    if not retrieved:
        human = Message(conversation_id=c.id, role="user", content=data.content)
        assistant = Message(
            conversation_id=c.id,
            role="assistant",
            content="The selected documents do not contain enough indexed context to answer this question.",
        )
        session.add_all([human, assistant])
        await session.commit()
        return {
            "conversation_id": str(c.id),
            "message_id": str(assistant.id),
            "answer": assistant.content,
            "sources": [],
        }
    history_rows = (
        await session.scalars(
            select(Message)
            .where(Message.conversation_id == c.id)
            .order_by(Message.created_at.desc())
            .limit(get_settings().chat_history_message_limit)
        )
    ).all()
    try:
        generated = await generate_grounded_answer(
            data.content,
            retrieved,
            [(item.role, item.content) for item in reversed(history_rows)],
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            502, "Gemini could not generate an answer. Please try again later."
        ) from exc
    answer = generated.answer
    human = Message(conversation_id=c.id, role="user", content=data.content)
    assistant = Message(conversation_id=c.id, role="assistant", content=answer)
    session.add_all([human, assistant])
    await session.flush()
    payload = []
    for item in retrieved:
        citation_id = f"S{item.rank}"
        if citation_id in generated.cited_ids:
            session.add(
                MessageSource(
                    message_id=assistant.id,
                    chunk_id=item.chunk_id,
                    citation_id=citation_id,
                    similarity=item.similarity,
                    page_number=item.page_number,
                    content_snapshot=item.content,
                )
            )
            payload.append(
                {
                    "citation_id": citation_id,
                    "document_id": str(item.document_id),
                    "document_name": item.document_name,
                    "page": item.page_number,
                    "chunk_id": str(item.chunk_id),
                    "chunk_index": item.chunk_index,
                    "similarity": item.similarity,
                    "content": item.content,
                }
            )
    await session.commit()
    return {
        "conversation_id": str(c.id),
        "message_id": str(assistant.id),
        "answer": answer,
        "sources": payload,
    }
