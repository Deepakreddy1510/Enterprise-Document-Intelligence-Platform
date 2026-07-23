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

## Correctness follow-up implemented in code
- Sentence Transformer `encode`, tokenizer work, PyMuPDF extraction, and Gemini generation are dispatched with `asyncio.to_thread` so synchronous SDK/model calls do not block the request event loop.
- Ingestion now starts and indexes through separate clean sessions, rolls back failed batch writes, then records a bounded user-facing failed status through a fresh transaction.
- Chunk sizing now counts the configured embedding tokenizer's real tokens. Sentence boundaries and tokenizer-token overlap are preserved; only a single oversized sentence is split by the tokenizer.
- Gemini prompts use `CHAT_HISTORY_MESSAGE_LIMIT` and label history separately from retrieved evidence; both are explicitly untrusted.
- Upload validates a whole batch before files are written and deletes all written paths if the database commit fails. Same-batch duplicate content is rejected.
- Migration `002_add_query_indexes` adds corrective query indexes without modifying the initial immutable migration.
- Citation rendering now parses one complete Markdown document using safe citation links, preserving Markdown structures such as lists and tables.

## Correctness follow-up verification
- Passed: `git diff --check`, `ruff format --check backend`, `ruff check backend`, and `mypy backend/app`.
- `pytest backend/tests` now discovers repository-local test modules but cannot import required Python packages in this runner (`pydantic`, `jwt`, `fitz`); install the Python 3.11 project dependencies before treating test results as valid.
- `npm --prefix frontend install` remains blocked by registry `403 Forbidden` for `@tailwindcss/postcss`. As a consequence lint, typecheck, Vitest, and Next build all failed only because their dependency binaries/types are unavailable; no frontend result is claimed as passing.
- Docker is absent, so Compose config/startup, migration execution, endpoint smoke tests, full PDF workflow, and live Gemini calls remain unverified.

## Query embedding offload follow-up
- The conversation message route now delegates query embedding to `embed_query_in_thread`, which invokes the local Sentence Transformer through `asyncio.to_thread` before pgvector search.
- Added a behavioral async mock test that verifies the route helper dispatches the actual embedding callable and returns the thread-pool result.
- GitHub PR mergeability cannot be inspected from this runner: there is no configured Git remote and the GitHub CLI is not installed. No local branch conflict is present (`git status` is clean before this change); GitHub's reported non-mergeable state therefore cannot be diagnosed or resolved here.
