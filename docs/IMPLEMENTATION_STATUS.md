# Implementation Status

## Implemented in code
- Cookie JWT registration/login/logout/current-user and ownership-scoped APIs.
- PDF-only validation, UUID local storage, duplicate checksum detection, FastAPI BackgroundTasks ingestion, PyMuPDF extraction, configurable sentence-aware chunks, normalized BGE embeddings, pgvector storage/retrieval, and Gemini source-ID validation.
- Conversation create/list/open/rename/delete, selected-document management, persisted messages, persisted source snapshots, empty-index insufficient-context persistence, and document/chunk/conversation-membership cascades.
- Responsive dashboard with real document upload/status polling/retry/delete, conversation sidebar, document selection, chat composer, Markdown rendering, structured citation cards, and Escape-close source dialog.
- Alembic pgvector migration, Docker Compose definition, configuration template, static checks, and focused unit tests.

## Implemented but not verified in this runner
Docker startup, Alembic execution, database integration tests, frontend install/lint/type/test/build, full upload-to-chat flow, and live Gemini generation. Docker is not installed; npm registry access returns 403; the host is Python 3.14 without the Python 3.11 project dependencies.

## Required manual values
`POSTGRES_PASSWORD`, a 16+ character `JWT_SECRET_KEY`, and `GEMINI_API_KEY`. `GEMINI_MODEL` defaults to `gemini-2.0-flash` but may need changing for the supplied key.

## Deferred by scope
Durable background workers, hybrid retrieval, reranking, OCR, non-PDF formats, refresh tokens, workspaces, evaluation dashboards, CI/CD, monitoring, object storage, and cloud deployment.

## Local verification commands
```bash
cp deployment/.env.example deployment/.env
# edit deployment/.env
docker compose -f deployment/docker-compose.yml up --build
cd backend && python3.11 -m pip install -e . && pytest tests
npm --prefix frontend install
npm --prefix frontend run lint && npm --prefix frontend run typecheck && npm --prefix frontend run test && npm --prefix frontend run build
```

## Latest runner results
- `git diff --check`, `ruff format --check backend`, `ruff check backend`, and `mypy backend/app` passed.
- `pytest backend/tests` did not collect because this runner's Python 3.14 environment lacks the project runtime packages (`jwt`, `pydantic`, PyMuPDF) and differs from the pinned Python 3.11 target.
- `npm --prefix frontend install` was blocked by a registry `403 Forbidden` for `@tailwindcss/postcss`; no frontend checks were claimed as passed.
- Docker/Compose and migrations remain unverified because `docker` is not installed.
