# Implementation Status

## Completed
Repository structure; FastAPI routes; SQLAlchemy models; pgvector Alembic migration; cookie JWT authentication; ownership-scoped document and conversation routes; PDF upload validation/storage; BackgroundTasks ingestion; PyMuPDF extraction; sentence-aware chunking; BGE embedding service; pgvector retrieval query; Gemini grounded generation with source-ID validation; basic Next.js account and document UI; Docker Compose; core documentation.

## Partially completed
Frontend conversation/chat experience is represented by backend APIs but needs a fuller interactive UI. Integration verification requires Docker and a Gemini key. Automated test suite currently emphasizes pure chunking/configuration behavior and requires expansion before production use.

## Deferred
All roadmap items in `IMPLEMENTATION_PLAN.md`, plus robust rate limiting, comprehensive audit logs, and durable queues.

## Manual requirements
Set `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `GEMINI_API_KEY`, and optionally `GEMINI_MODEL` in `deployment/.env`.

## Next action
Run Compose, migrations, and API workflow verification after installing dependencies and providing secrets.

## Verification record
- `ruff format --check backend`: passed after formatting migration scripts.
- `ruff check backend`: passed.
- `mypy backend/app`: passed.
- `pytest backend/tests`: blocked: the host Python 3.14 environment has not installed project dependencies (`pydantic`, `PyMuPDF`) and does not match required Python 3.11.
- `npm --prefix frontend install`: blocked with registry `403 Forbidden` for `@types/node`; frontend lint/type/build/tests could not run.
- Docker is unavailable in this environment (`docker: command not found`), so Compose validation, migrations, and end-to-end API checks are unverified.
