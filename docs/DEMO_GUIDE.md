# Demo guide

1. Set the required values in `deployment/.env` and start Compose.
2. Register, log in, and upload two text-based PDFs.
3. Watch each record move from pending/processing to ready; retry a failed file if necessary.
4. Create a conversation, select both ready PDFs, and ask a question.
5. Show the Markdown answer and click a valid `[S1]` source marker to open its document name, page, similarity ranking score, and stored passage.
6. Reload the browser to demonstrate persisted messages and citations.
7. Delete a PDF and explain the database foreign-key cascade removes chunks and conversation membership.
8. Explain that BackgroundTasks is intentionally lightweight and non-durable; Celery/Redis is deferred future work.

A live Gemini demo requires a user-supplied `GEMINI_API_KEY`; no fake answer is generated without it.
