from functools import lru_cache

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME, device="cpu")


def embed(texts: list[str]) -> np.ndarray:
    """L2-normalised sentence embeddings (cosine similarity == dot product)."""
    return _model().encode(texts, batch_size=64, normalize_embeddings=True,
                           show_progress_bar=False).astype(np.float32)
