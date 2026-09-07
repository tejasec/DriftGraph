"""
Gensim Word2Vec baseline embedder for ablation comparisons.
"""

from typing import List, Optional
import numpy as np
import structlog
from driftgraph.embed.base import BaseEmbedder

logger = structlog.get_logger(__name__)


class Word2VecEmbedder(BaseEmbedder):
    """Word2Vec baseline embedder using average word vectors."""

    def __init__(self, vector_size: int = 384, min_count: int = 1, window: int = 5):
        self._dim = vector_size
        self.min_count = min_count
        self.window = window
        self.model = None

    @property
    def dimension(self) -> int:
        return self._dim

    def fit(self, corpus_texts: List[str]):
        """Train Word2Vec model on corpus sentences."""
        try:
            from gensim.models import Word2Vec
            tokenized_corpus = [text.lower().split() for text in corpus_texts if text.strip()]
            if not tokenized_corpus:
                return

            self.model = Word2Vec(
                sentences=tokenized_corpus,
                vector_size=self._dim,
                window=self.window,
                min_count=self.min_count,
                workers=2,
                epochs=10
            )
            logger.info("word2vec_trained", vocab_size=len(self.model.wv), dim=self._dim)
        except Exception as e:
            logger.warning("word2vec_training_failed", error=str(e))
            self.model = None

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Compute average word embedding for each document."""
        if not texts:
            return np.empty((0, self._dim), dtype=np.float32)

        vectors = []
        for text in texts:
            tokens = [w.lower() for w in text.split()]
            if self.model is not None and tokens:
                vecs = [self.model.wv[w] for w in tokens if w in self.model.wv]
                if vecs:
                    avg_vec = np.mean(vecs, axis=0)
                    norm = np.linalg.norm(avg_vec)
                    if norm > 0:
                        avg_vec = avg_vec / norm
                    vectors.append(avg_vec.astype(np.float32))
                    continue

            # Fallback zero vector or random hash
            rng = np.random.RandomState(abs(hash(text)) % (2**32))
            vec = rng.randn(self._dim).astype(np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append(vec)

        return np.array(vectors, dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_texts([text])[0]
