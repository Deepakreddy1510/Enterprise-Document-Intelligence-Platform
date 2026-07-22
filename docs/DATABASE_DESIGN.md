# Database design

The initial Alembic migration enables `vector` and creates `users`, `documents`, `document_chunks`, `conversations`, `conversation_documents`, `messages`, and `message_sources`.

- `documents.user_id` and `conversations.user_id` are the ownership boundaries.
- `documents` has a per-user SHA-256 uniqueness constraint; document chunks cascade on deletion.
- `document_chunks.embedding` is `vector(384)` and has an HNSW cosine index.
- `conversation_documents` models many selected documents per conversation and cascades when either side is removed.
- messages cascade with a conversation; sources cascade with a message and use a snapshot of the cited passage.

API queries always constrain user-owned parent rows; frontend IDs are never trusted as an ownership claim.
