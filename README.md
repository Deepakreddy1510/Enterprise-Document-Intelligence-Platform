# Enterprise Document Intelligence Platform

A full-stack, multi-user Retrieval-Augmented Generation (RAG) application for uploading PDF documents, indexing them with local embeddings, retrieving relevant chunks with PostgreSQL + pgvector, and generating grounded answers with Google Gemini and page-level citations.


## Architecture / Workflow



```text
docs/architecture-workflow.png
```


<p align="center">
  <img src="docs/architecture-workflow.png" alt="Enterprise RAG Assistant end-to-end workflow" width="100%">
</p>

> **Chunking note:** The implementation uses **sentence-aware, tokenizer-based, bounded variable-size chunking**, not strict fixed-size chunking. Current defaults are target 400 tokens, max 500, overlap 60, minimum 40.

```mermaid
flowchart TD
    U[User] --> FE[Next.js Frontend]
    FE --> API[FastAPI Backend]

    API --> AUTH[JWT HttpOnly Cookie Auth]
    API --> UP[PDF Upload]
    API --> CHAT[RAG Chat]

    UP --> PDF[PyMuPDF Extraction]
    PDF --> CHUNK[Sentence + Token Aware Chunking]
    CHUNK --> EMB[BAAI/bge-small-en-v1.5]
    EMB --> DB[(PostgreSQL + pgvector)]

    CHAT --> QEMB[Embed Query]
    QEMB --> DB
    DB --> RET[Cosine Similarity Top-k]
    RET --> CTX[Grounded Context]
    CTX --> GEMINI[Google Gemini]
    GEMINI --> ANSWER[Answer + Page Citations]
    ANSWER --> FE
```

## What the Project Does

The system lets a user register or log in, upload one or more PDFs, wait for background ingestion, select documents for a conversation, ask questions, and receive grounded answers with page-level sources.

```text
PDF
 ↓
PyMuPDF extraction
 ↓
Text cleaning
 ↓
Sentence-aware + tokenizer-aware chunking
 ↓
BGE embeddings
 ↓
PostgreSQL + pgvector
 ↓
User question
 ↓
Query embedding
 ↓
Cosine similarity search
 ↓
Top-k chunks
 ↓
Grounded Gemini prompt
 ↓
Answer + citations
```

## Core Features

- Multi-user registration and login
- JWT authentication using HttpOnly cookies
- User-owned document isolation
- Multi-PDF upload
- PDF MIME/type, empty-file, size, and duplicate-content validation
- Background ingestion with FastAPI `BackgroundTasks`
- PDF extraction with PyMuPDF
- BGE embeddings with `BAAI/bge-small-en-v1.5`
- 384-dimensional vectors
- PostgreSQL 16 + pgvector
- HNSW cosine-similarity vector index
- Global top-k retrieval across selected documents
- Exact retrieved-content deduplication
- Grounded Gemini generation
- Page-level citations and source snapshots
- Persistent conversations and messages
- Alembic migrations
- Docker Compose local environment
- Deterministic retrieval evaluation
- Optional offline RAGAS evaluation

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript |
| Backend | FastAPI, Python 3.11 |
| Database | PostgreSQL 16 |
| Vector Search | pgvector |
| ORM | SQLAlchemy Async + asyncpg |
| PDF Parsing | PyMuPDF |
| Embeddings | Sentence Transformers |
| Embedding Model | `BAAI/bge-small-en-v1.5` |
| LLM | Google Gemini |
| Authentication | JWT + HttpOnly cookie |
| Password Hashing | Argon2 |
| Migrations | Alembic |
| Evaluation | Retrieval metrics + RAGAS |
| Orchestration | Docker Compose |

## RAG Design

### Chunking

Each PDF page is processed independently. Text is split into sentences, counted using the real BGE tokenizer, combined around the target size, capped at the configured maximum, and overlapped with neighboring chunks.

```text
CHUNK_TARGET_TOKENS=400
CHUNK_MAX_TOKENS=500
CHUNK_OVERLAP_TOKENS=60
CHUNK_MIN_TOKENS=40
```

Chunks preserve page boundaries to support page-level citations.

### Embeddings

The same model embeds both document chunks and user queries:

```text
BAAI/bge-small-en-v1.5
```

Vector dimension:

```text
384
```

### Retrieval

The query is embedded and ranked with pgvector cosine distance. Retrieval is restricted by authenticated user ID and selected document IDs.

```text
RETRIEVAL_TOP_K=6
```

Cosine similarity is a ranking signal, not a confidence score.

### Generation

Retrieved chunks are labeled as sources such as `[S1]`, `[S2]`, and passed with recent conversation history to Gemini. The final response includes normalized citations that can be opened in the UI.

## Project Structure

```text
Enterprise-Document-Intelligence-Platform/
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py
│   │   ├── api/v1/routes.py
│   │   ├── core/config.py
│   │   ├── core/security.py
│   │   ├── db/session.py
│   │   ├── models/entities.py
│   │   ├── services/
│   │   │   ├── embeddings.py
│   │   │   ├── ingestion.py
│   │   │   ├── pdf.py
│   │   │   ├── rag.py
│   │   │   └── retrieval.py
│   │   └── evaluation/
│   ├── migrations/
│   ├── evaluation/
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── app/
│   ├── components/
│   ├── lib/api.ts
│   └── tests/
├── deployment/
│   ├── .env.example
│   └── docker-compose.yml
├── docs/
├── Makefile
└── README.md
```

## Reliability and Conflict Handling

### Duplicate PDFs

A SHA-256 checksum is calculated for each uploaded PDF. Duplicate content is rejected for the same user, including duplicates inside one multi-file batch.

### Upload Validation

The backend checks PDF extension/MIME type, empty files, maximum file size, duplicate content, and ownership constraints before ingestion.

### Failed Multi-file Uploads

The upload route validates the batch before persistence. If a database write fails after files are written, newly written files are cleaned up where possible.

### Interrupted Processing

The project uses FastAPI `BackgroundTasks`, not Celery/Redis. If the backend restarts while a document is still marked `processing`, startup marks that document as failed instead of leaving it stuck forever.

### Retrieval Isolation

Every retrieval query filters by the authenticated user and selected document IDs before ranking chunks.

### Retrieval Deduplication

Exact duplicate chunk text is removed from the final retrieved set.

### Grounding

Gemini is prompted with retrieved source context. If useful context is unavailable, the system is designed to respond with insufficient-information behavior rather than treating vector similarity as factual certainty.

## Prerequisites

Recommended Docker setup:

- Git
- Docker Desktop
- Google Gemini API key

Manual development also requires:

- Python 3.11
- Node.js 20+ / 22+
- npm
- PostgreSQL 16 + pgvector

## Clone the Repository

```bash
git clone https://github.com/Deepakreddy1510/Enterprise-Document-Intelligence-Platform.git
cd Enterprise-Document-Intelligence-Platform
```

To use the current development branch:

```bash
git checkout feat/offline-ragas-evaluation
```

## Configure Environment Variables

Windows CMD:

```cmd
copy deployment\.env.example deployment\.env
```

macOS/Linux:

```bash
cp deployment/.env.example deployment/.env
```

Edit `deployment/.env`.

At minimum configure:

```env
ENVIRONMENT=development
LOG_LEVEL=INFO

POSTGRES_DB=enterprise_rag
POSTGRES_USER=enterprise_rag
POSTGRES_PASSWORD=CHANGE_THIS_PASSWORD

JWT_SECRET_KEY=CHANGE_THIS_TO_A_LONG_RANDOM_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-3.6-flash

EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=384

CHUNK_TARGET_TOKENS=400
CHUNK_MAX_TOKENS=500
CHUNK_OVERLAP_TOKENS=60
CHUNK_MIN_TOKENS=40

RETRIEVAL_TOP_K=6
CHAT_HISTORY_MESSAGE_LIMIT=8
MAX_PDF_SIZE_MB=20

UPLOAD_DIRECTORY=/app/uploads
FRONTEND_ORIGIN=http://localhost:3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Use a Gemini model that is available to your API key.

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Never commit `.env`, API keys, database passwords, or JWT secrets.

## Recommended Setup: Docker Compose

From the repository root:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml up --build
```

Services:

```text
PostgreSQL + pgvector
        ↓
FastAPI backend
        ↓
Next.js frontend
```

Open:

```text
Frontend:        http://localhost:3000
FastAPI:         http://localhost:8000
Swagger docs:    http://localhost:8000/docs
Health:          http://localhost:8000/api/v1/health
Readiness:       http://localhost:8000/api/v1/readiness
```

Run in background:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml up -d
```

View logs:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml logs -f
```

Stop:

```bash
docker compose --env-file deployment/.env -f deployment/docker-compose.yml down
```

Do **not** use `down -v` unless you intentionally want to delete PostgreSQL and uploaded-PDF volumes.

## Manual Backend Setup with Virtual Environment

### Start PostgreSQL + pgvector

Example:

```cmd
docker run --name enterprise-rag-postgres -e POSTGRES_DB=enterprise_rag -e POSTGRES_USER=enterprise_rag -e POSTGRES_PASSWORD=dev_password -p 5432:5432 -d pgvector/pgvector:pg16
```

### Create virtual environment

```cmd
cd backend
py -3.11 -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
python -m pip install --upgrade pip
pip install -e .
```

Backend dependencies are declared in `backend/pyproject.toml`.

### Create `backend/.env`

```env
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://enterprise_rag:dev_password@localhost:5432/enterprise_rag
JWT_SECRET_KEY=YOUR_LONG_RANDOM_SECRET
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-3.6-flash
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=384
UPLOAD_DIRECTORY=../uploads
FRONTEND_ORIGIN=http://localhost:3000
```

### Apply migrations

```bash
alembic upgrade head
```

The migration enables the `vector` extension and creates the `vector(384)` column and HNSW cosine index.

### Run FastAPI

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Manual Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Run:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

## How to Use

1. Register or log in.
2. Upload one or more text-based PDFs.
3. Wait until each PDF is `ready`.
4. Create/open a conversation.
5. Select documents.
6. Ask a question.
7. Review the grounded answer.
8. Open citations to inspect source content and page numbers.

For a first test, use a small text-based PDF rather than a scanned PDF.

## Database and Persistence

PostgreSQL stores relational application data and embeddings.

Core tables include:

```text
users
documents
document_chunks
conversations
conversation_documents
messages
message_sources
```

Docker Compose uses named volumes:

```text
postgres_data
uploads
```

## API

Base URL:

```text
http://localhost:8000/api/v1
```

Important endpoints include:

```text
GET  /health
GET  /readiness
POST /auth/register
POST /auth/login
POST /auth/logout
GET  /auth/me
POST /documents
GET  /documents
```

Additional conversation, document-selection, chat, and source routes are implemented in:

```text
backend/app/api/v1/routes.py
```

Swagger:

```text
http://localhost:8000/docs
```

## Offline Evaluation

Evaluation is separate from live chat.

### Retrieval Metrics

The deterministic evaluator measures:

```text
Hit@1
Hit@3
Hit@5
MRR
Recall@5
retrieval latency
```

Example:

```cmd
cd backend
python -m app.evaluation.cli --dataset evaluation/cases.jsonl --user-email user@example.com --top-k 5 --mode retrieval --output evaluation/results.json
```

### Optional RAGAS Metrics

The offline RAGAS layer evaluates:

```text
Faithfulness
Answer Relevancy
Context Precision
Context Recall
Factual Correctness
```

RAGAS is not invoked by normal chatbot requests and consumes Gemini quota.

Example:

```bash
RAGAS_ENABLED=true python -m app.evaluation.cli --dataset evaluation/cases.jsonl --user-email user@example.com --top-k 5 --mode all --max-concurrency 1 --output evaluation/results-ragas.json
```

Do not treat failed evaluator runs or placeholder zero values as benchmark results.

See `backend/evaluation/README.md` for dataset methodology.

## Testing

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm run test
```

Lint:

```bash
cd backend
ruff check app tests
```

```bash
cd frontend
npm run lint
```

Type checking:

```bash
cd backend
mypy app
```

```bash
cd frontend
npm run typecheck
```

The repository also includes Makefile commands such as:

```bash
make lint
make typecheck
make test
make build
make up
make down
make logs
make migrate
```

## Cloud Deployment Status

The application is **not yet a completed public cloud deployment**.

Current target architecture:

```text
Browser
   ↓
Vercel / Next.js
   ↓
Container-hosted FastAPI backend
   ↓
Managed PostgreSQL + pgvector
   ↓
Google Gemini API
```

An initial Render Free backend deployment exceeded the available 512 MB memory while starting the Python/ML stack. This is currently being treated as a deployment-capacity issue around PyTorch/Sentence Transformers rather than an application/database logic failure.

Remaining production work includes:

- reduce backend memory use or use a larger instance
- validate BGE embedding inference in production
- add persistent PDF storage
- deploy the Next.js frontend
- set production CORS/cookie configuration
- run end-to-end production tests for auth, upload, retrieval, Gemini generation, conversations, and citations

Until then, Docker Compose is the supported local runtime.

## Current Limitations

Not currently included:

- OCR for scanned PDFs
- DOCX/TXT ingestion
- Celery/Redis
- hybrid BM25 + dense retrieval
- reranking
- Qdrant
- complex workspaces/RBAC
- refresh-token rotation
- production monitoring
- full CI/CD
- durable cloud object storage
- completed public deployment

## Security Notes

- Never commit `.env`.
- Never commit Gemini keys, database passwords, or JWT secrets.
- JWTs are stored in HttpOnly cookies.
- Production cookies use secure settings.
- Retrieval is restricted to the authenticated user's selected documents.
- Cloud deployment should use HTTPS and persistent private storage.

## Why PostgreSQL + pgvector?

Using one PostgreSQL database for relational data and vectors keeps the system simpler while preserving document ownership and metadata filtering transactionally.

For a small-to-medium private document assistant this avoids synchronization complexity between a relational database and a separate vector database while still providing cosine-ranked semantic retrieval.

## Future Improvements

Possible future improvements:

```text
Reranking
Hybrid search
OCR
DOCX/TXT ingestion
Durable background jobs
Cloud object storage
Production deployment
CI/CD
Monitoring
Custom domain
Expanded evaluation dataset
A/B retrieval experiments
```

These should be added only when they provide measurable value.

## Repository

https://github.com/Deepakreddy1510/Enterprise-Document-Intelligence-Platform

---

Built as an end-to-end RAG engineering project covering document ingestion, token-aware chunking, embeddings, vector retrieval, grounded generation, citations, persistence, evaluation, testing, Dockerization, and deployment engineering.
