# Interview guide

Explain that PostgreSQL + pgvector was chosen because relational ownership, document metadata, and 384-dimensional embeddings remain together; Qdrant is unnecessary at this scale. HNSW cosine distance ranks semantic candidates but does not quantify answer confidence.

`BAAI/bge-small-en-v1.5` is local, 384-dimensional, and normalized for cosine retrieval. Query and document embeddings must share the same model/preprocessing; a model change means documents need reprocessing.

Sentence-aware chunks preserve meaning better than arbitrary splits; target/max/overlap are configurable because context coverage, duplication, retrieval precision, and LLM context cost trade off. Citations are valid only when a Gemini `[S#]` marker maps to a server retrieval result.

BackgroundTasks keeps the demo deployable but is non-durable, so startup marks interrupted jobs failed. Celery/Redis is a future scaling path. User isolation is enforced by JWT-derived IDs in every parent query, vector query, deletion, and conversation document assignment.
