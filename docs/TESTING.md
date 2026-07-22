# Testing

Unit tests cover configuration, PDF cleaning/chunk determinism and minimum filtering, password hashing, and JWT expiry. Frontend tests cover Markdown/citation behavior. Database-dependent ownership, pgvector, ingestion, Gemini-mocking, and workflow tests are the next verification priority once Python 3.11 dependencies and Docker are available.

Run locally:
```bash
cd backend && python3.11 -m pip install -e . && pytest tests
npm --prefix frontend install
npm --prefix frontend run lint && npm --prefix frontend run typecheck && npm --prefix frontend run test
```

Normal tests must mock Gemini; live provider testing is manual and requires `GEMINI_API_KEY`.
