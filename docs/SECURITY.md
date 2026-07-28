# Security notes

Implemented controls: Argon2 password hashes, signed short-lived HttpOnly JWT cookies, `SameSite=Lax`, production-only Secure cookies, CORS credential configuration, ownership-scoped SQLAlchemy queries, UUID upload names, PDF extension/MIME/size checks, no public uploads directory, sanitized API errors, and React Markdown rendering without `dangerouslySetInnerHTML`.

Uploaded documents are untrusted. The Gemini instruction says source text cannot override system instructions, and only server-provided source IDs can be persisted as citations.

This is a placement project, not a claim of complete enterprise security. Missing rate limiting, refresh sessions, malware scanning, durable jobs, encrypted object storage, and audit infrastructure are intentional deferred work.
