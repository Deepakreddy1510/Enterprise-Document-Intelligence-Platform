# API Reference

All application endpoints are under `/api/v1`; browser requests use the HttpOnly `access_token` cookie.

| Area | Endpoints |
| --- | --- |
| Operational | `GET /health`, `GET /readiness` |
| Authentication | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Documents | `POST /documents` (multipart `files`), `GET /documents`, `GET /documents/{id}`, `GET /documents/{id}/status`, `POST /documents/{id}/retry`, `DELETE /documents/{id}` |
| Conversations | `POST/GET /conversations`, `GET/PATCH/DELETE /conversations/{id}`, `POST /conversations/{id}/documents`, `DELETE /conversations/{id}/documents/{document_id}` |
| RAG chat | `POST /conversations/{id}/messages` with `{ "content": "..." }` |

Every document and conversation route resolves the user from the cookie and filters the query by that user. The chat response returns structured sources; the browser never derives citations itself.

`POST /messages` returns `503` when `GEMINI_API_KEY` is absent, `502` for provider failure, and `422` when no selected ready documents exist.
