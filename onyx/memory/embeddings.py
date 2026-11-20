"""Embedding generation and vector similarity calculations."""

import re
from typing import List
import numpy as np


class LocalEmbeddingProvider:
    """Local, deterministic embedding generator with subword character n-gram hashing."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _hash_token(self, token: str, seed: int = 0) -> int:
        h = seed
        for ch in token:
            h = (h * 37 + ord(ch)) & 0xFFFFFFFF
        return h % self.dimension

    def embed_text(self, text: str) -> List[float]:
        """Generate a dense, normalized vector embedding using bag-of-words and char n-grams."""
        vec = np.zeros(self.dimension, dtype=np.float32)
        clean_text = text.lower()
        words = re.findall(r"\b\w+\b", clean_text)
        if not words:
            return vec.tolist()

        for word in words:
            # Word bucket
            w_idx = self._hash_token(word, seed=13)
            vec[w_idx] += 2.0

            # Subword 3-grams for morphological/fuzzy matching
            if len(word) >= 3:
                for i in range(len(word) - 2):
                    ngram = word[i:i+3]
                    n_idx = self._hash_token(ngram, seed=7)
                    vec[n_idx] += 0.5

        # L2 Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two float vectors (-1.0 to 1.0)."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
