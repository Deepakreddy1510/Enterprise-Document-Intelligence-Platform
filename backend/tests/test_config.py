import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-enough-length")
from app.core.config import Settings


def test_chunk_bounds():
    assert Settings(jwt_secret_key="x" * 16).embedding_dimension == 384
