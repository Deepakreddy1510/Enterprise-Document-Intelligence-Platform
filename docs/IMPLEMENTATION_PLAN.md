# Implementation Plan — Enterprise RAG Assistant

## Scope
A manageable, placement-ready multi-user PDF RAG application. Users authenticate, upload PDFs, monitor processing, select documents in persistent conversations, and receive Gemini answers grounded in pgvector-retrieved pages.

## Decisions
- **Modular monolith:** Next.js and FastAPI are independently runnable but one repository and relational model.
- **PostgreSQL + pgvector:** one source of truth for user ownership, metadata, and 384-dimensional normalized BGE vectors. This removes a second vector-service synchronization problem; it suits small-to-medium data volumes.
- **BackgroundTasks:** lightweight asynchronous ingestion for local deployment; restart interruption is explicitly handled, but Celery/Redis is future work.
- **Sentence-aware chunks:** configurable 400/500/60/40 target/max/overlap/min settings preserve sentence boundaries while controlling retrieval context.

## Delivery path
1. Schema and secure cookie authentication.
2. PDF validation, local storage, page extraction, chunking, BGE embeddings, pgvector indexing.
3. Ownership-filtered retrieval, Gemini context/citation validation, persistent conversations.
4. Responsive frontend, tests, Docker Compose, and documentation.

## Future roadmap
Hybrid lexical/vector retrieval, Qdrant, reranking, semantic chunking, OCR, Celery/Redis, object storage, refresh sessions, workspaces, evaluation datasets, monitoring, CI/CD, and cloud deployment are intentionally not part of this implementation.
