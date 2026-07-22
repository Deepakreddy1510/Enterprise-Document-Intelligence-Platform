from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


@lru_cache
def model() -> SentenceTransformer:
    return SentenceTransformer(get_settings().embedding_model)


def embed(texts: list[str]) -> list[list[float]]:
    vectors = model().encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
    if any(len(v) != get_settings().embedding_dimension for v in vectors):
        raise RuntimeError("Embedding model dimension does not match EMBEDDING_DIMENSION")
    return vectors
