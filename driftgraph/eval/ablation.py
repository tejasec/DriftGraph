"""
Ablation Study: Comparing lightweight Sentence-BERT vs Word2Vec baseline.
"""

from typing import List, Dict, Any
import numpy as np
import structlog

from driftgraph.embed.sbert import SBERTEmbedder
from driftgraph.embed.baseline import Word2VecEmbedder
from driftgraph.ingest.models import Chunk

logger = structlog.get_logger(__name__)


class AblationStudy:
    """Compares embedding models on retrieval coherence and vector properties."""

    def __init__(self):
        self.sbert = SBERTEmbedder()
        self.w2v = Word2VecEmbedder(vector_size=384)

    def run_comparison(self, chunks: List[Chunk]) -> Dict[str, Any]:
        texts = [c.text for c in chunks]
        if not texts:
            return {"error": "No chunks provided for ablation."}

        # Train Word2Vec on texts
        self.w2v.fit(texts)

        # Generate vectors
        sbert_vecs = self.sbert.embed_texts(texts)
        w2v_vecs = self.w2v.embed_texts(texts)

        # Compute pairwise cosine similarities
        def avg_pairwise_sim(matrix: np.ndarray) -> float:
            if len(matrix) <= 1:
                return 1.0
            sims = np.dot(matrix, matrix.T)
            np.fill_diagonal(sims, 0.0)
            return float(np.sum(sims) / (len(matrix) * (len(matrix) - 1)))

        sbert_sim = avg_pairwise_sim(sbert_vecs)
        w2v_sim = avg_pairwise_sim(w2v_vecs)

        results = {
            "num_samples": len(texts),
            "sbert": {
                "model": "all-MiniLM-L6-v2",
                "dimension": self.sbert.dimension,
                "avg_pairwise_similarity": round(sbert_sim, 4),
            },
            "word2vec_baseline": {
                "model": "Word2Vec (Gensim)",
                "dimension": self.w2v.dimension,
                "avg_pairwise_similarity": round(w2v_sim, 4),
            }
        }
        logger.info("ablation_study_completed", sbert_sim=sbert_sim, w2v_sim=w2v_sim)
        return results
