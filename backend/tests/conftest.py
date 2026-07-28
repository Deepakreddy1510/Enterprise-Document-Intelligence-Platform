import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-enough-length")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://enterprise_rag:test@localhost:5432/enterprise_rag_test"
)
