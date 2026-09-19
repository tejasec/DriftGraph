"""
Vector Index Store using FAISS with metadata tracking and cosine similarity fallback.
"""

from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class VectorIndex:
    """FAISS-backed vector index for chunk and node embeddings."""

    def __init__(self, dimension: int = 384, index_path: Optional[str] = None):
        self.dimension = dimension
        self.index_path = Path(index_path) if index_path else None
        self.id_to_index: Dict[str, int] = {}
        self.index_to_id: Dict[int, str] = {}
        self.vectors: Optional[np.ndarray] = None
        self._faiss_index = None
        self._init_faiss()

    def _init_faiss(self):
        try:
            import faiss
            # Inner product for normalized embeddings = Cosine Similarity
            self._faiss_index = faiss.IndexFlatIP(self.dimension)
        except Exception as e:
            logger.warning("faiss_not_available_using_numpy_fallback", error=str(e))
            self._faiss_index = None

    def add(self, ids: List[str], vectors: np.ndarray):
        """Add vectors with corresponding IDs."""
        if len(ids) == 0 or len(vectors) == 0:
            return

        vectors = vectors.astype(np.float32)
        # Normalize
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_vecs = vectors / norms

        start_idx = len(self.index_to_id)
        for i, item_id in enumerate(ids):
            idx = start_idx + i
            self.id_to_index[item_id] = idx
            self.index_to_id[idx] = item_id

        if self._faiss_index is not None:
            self._faiss_index.add(normalized_vecs)

        if self.vectors is None:
            self.vectors = normalized_vecs
        else:
            self.vectors = np.vstack([self.vectors, normalized_vecs])

    def remove_ids(self, ids: List[str]):
        """Remove vectors matching the given IDs and rebuild FAISS index."""
        if not ids or self.vectors is None or len(self.index_to_id) == 0:
            return

        remove_set = set(ids)
        surviving_pairs = [
            (idx, item_id)
            for idx, item_id in sorted(self.index_to_id.items())
            if item_id not in remove_set
        ]

        if len(surviving_pairs) == len(self.index_to_id):
            return  # No target IDs found

        surviving_indices = [idx for idx, _ in surviving_pairs]
        surviving_ids = [item_id for _, item_id in surviving_pairs]

        if surviving_indices:
            surviving_vecs = self.vectors[surviving_indices]
        else:
            surviving_vecs = np.empty((0, self.dimension), dtype=np.float32)

        # Re-initialize index and metadata
        self.id_to_index = {}
        self.index_to_id = {}
        self.vectors = None
        self._init_faiss()

        if len(surviving_ids) > 0 and len(surviving_vecs) > 0:
            self.add(surviving_ids, surviving_vecs)

        if self.index_path:
            self.save()

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search top_k closest items given a query vector. Returns [(id, score)]."""
        if self.vectors is None or len(self.index_to_id) == 0:
            return []

        q_vec = query_vector.reshape(1, -1).astype(np.float32)
        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm

        top_k = min(top_k, len(self.index_to_id))

        if self._faiss_index is not None and self._faiss_index.ntotal > 0:
            scores, indices = self._faiss_index.search(q_vec, top_k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx in self.index_to_id:
                    results.append((self.index_to_id[idx], float(score)))
            return results
        else:
            # NumPy Cosine Similarity fallback
            scores = np.dot(self.vectors, q_vec.T).flatten()
            top_indices = np.argsort(scores)[::-1][:top_k]
            return [(self.index_to_id[idx], float(scores[idx])) for idx in top_indices if idx in self.index_to_id]

    def save(self, path: Optional[str] = None):
        """Save FAISS index and metadata to disk."""
        target_path = Path(path) if path else self.index_path
        if not target_path:
            return

        target_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path = target_path.with_suffix(".meta.npy")

        if self._faiss_index is not None:
            try:
                import faiss
                faiss.write_index(self._faiss_index, str(target_path))
            except Exception as e:
                logger.warning("failed_to_save_faiss_index", error=str(e))

        # Save numpy vectors and metadata
        if self.vectors is not None:
            np.save(target_path.with_suffix(".vec.npy"), self.vectors)
            np.save(meta_path, {"id_to_index": self.id_to_index, "index_to_id": self.index_to_id}, allow_pickle=True)

    def load(self, path: Optional[str] = None) -> bool:
        """Load FAISS index and metadata from disk."""
        target_path = Path(path) if path else self.index_path
        if not target_path or not target_path.exists():
            return False

        meta_path = target_path.with_suffix(".meta.npy")
        if meta_path.exists():
            meta = np.load(meta_path, allow_pickle=True).item()
            self.id_to_index = meta.get("id_to_index", {})
            self.index_to_id = meta.get("index_to_id", {})

        vec_path = target_path.with_suffix(".vec.npy")
        if vec_path.exists():
            self.vectors = np.load(vec_path)

        if self._faiss_index is not None and target_path.exists():
            try:
                import faiss
                self._faiss_index = faiss.read_index(str(target_path))
                return True
            except Exception:
                pass

        return self.vectors is not None
