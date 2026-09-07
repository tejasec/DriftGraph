"""
SentenceTransformer embedding wrapper (all-MiniLM-L6-v2 / BGE-small).
"""

from typing import List, Optional
import numpy as np
import structlog
from driftgraph.embed.base import BaseEmbedder
from driftgraph.embed.models import EmbeddingConfig
from driftgraph.config import config as app_config

logger = structlog.get_logger(__name__)

_MODEL_CACHE = {}


class SBERTEmbedder(BaseEmbedder):
    """Sentence-Transformers embedder running locally on CPU/GPU."""

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        # Prefer explicit config; otherwise fall back to the app config.yaml
        # (model / device / batch_size / normalize), then the hardcoded default.
        if config is None:
            model_name = getattr(app_config.embedding, "model", "sentence-transformers/all-MiniLM-L6-v2")
            config = EmbeddingConfig(
                model_name=model_name,
                device=str(getattr(app_config.embedding, "device", "cpu")),
                batch_size=int(getattr(app_config.embedding, "batch_size", 32)),
                normalize=bool(getattr(app_config.embedding, "normalize", True)),
                dimension=int(getattr(app_config.embedding, "dimension", 384)),
            )
        self.config = config
        self._model = None
        self._dim = self.config.dimension
        self._init_model()

    def _init_model(self):
        model_name = self.config.model_name
        if model_name in _MODEL_CACHE:
            self._model = _MODEL_CACHE[model_name]
            return

        try:
            from sentence_transformers import SentenceTransformer
            logger.info("loading_sbert_model", model=model_name, device=self.config.device)
            self._model = SentenceTransformer(model_name, device=self.config.device)
            _MODEL_CACHE[model_name] = self._model
            # Update dimension dynamically from model
            if hasattr(self._model, "get_embedding_dimension"):
                self._dim = self._model.get_embedding_dimension()
            else:
                self._dim = self._model.get_sentence_embedding_dimension()
        except Exception as e:
            logger.warning("sbert_load_failed_using_mock", error=str(e), model=model_name)
            self._model = None

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed list of texts into dense vectors [N, D]."""
        if not texts:
            return np.empty((0, self._dim), dtype=np.float32)

        if self._model is not None:
            embeddings = self._model.encode(
                texts,
                batch_size=self.config.batch_size,
                show_progress_bar=False,
                normalize_embeddings=self.config.normalize,
                convert_to_numpy=True
            )
            return embeddings.astype(np.float32)
        else:
            # Deterministic pseudo-embedding fallback for environments where model weights aren't cached
            return self._fallback_embed(texts)

    def embed_query(self, text: str) -> np.ndarray:
        """Embed single query string."""
        return self.embed_texts([text])[0]

    def _fallback_embed(self, texts: List[str]) -> np.ndarray:
        """Deterministic hashing fallback embedding for testing / fallback."""
        vectors = []
        for text in texts:
            rng = np.random.RandomState(abs(hash(text)) % (2**32))
            vec = rng.randn(self._dim).astype(np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append(vec)
        return np.array(vectors, dtype=np.float32)
