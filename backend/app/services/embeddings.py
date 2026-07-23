from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


@lru_cache
def model() -> SentenceTransformer:
    """Load the single configured model once per process."""
    return SentenceTransformer(get_settings().embedding_model)


def token_count(text: str) -> int:
    """Count model tokenizer tokens without adding special tokens."""
    return len(model().tokenizer.encode(text, add_special_tokens=False))


def split_tokens(text: str, maximum: int) -> list[str]:
    """Split only an oversized sentence by the embedding tokenizer."""
    tokenizer = model().tokenizer
    ids = tokenizer.encode(text, add_special_tokens=False)
    return [
        tokenizer.decode(ids[offset : offset + maximum]).strip()
        for offset in range(0, len(ids), maximum)
    ]


def embed(texts: list[str]) -> list[list[float]]:
    vectors = model().encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
    if any(len(vector) != get_settings().embedding_dimension for vector in vectors):
        raise RuntimeError("Embedding model dimension does not match EMBEDDING_DIMENSION")
    return vectors
