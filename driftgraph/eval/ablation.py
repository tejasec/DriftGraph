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

    async def compare_retrieval_modes(
        self,
        query: str,
        storage: Any,
        vector_index: Any,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Ablation study comparing standard 2-channel hybrid retrieval vs
        3-channel LightRAG dual-level retrieval.
        """
        import time
        from driftgraph.query.local import LocalSearchEngine

        engine_standard = LocalSearchEngine(
            embedder=self.sbert,
            vector_index=vector_index,
            storage=storage,
            dual_level=False
        )
        engine_dual = LocalSearchEngine(
            embedder=self.sbert,
            vector_index=vector_index,
            storage=storage,
            dual_level=True
        )

        t0 = time.perf_counter()
        resp_standard = await engine_standard.search(query, top_k=top_k)
        lat_standard = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        resp_dual = await engine_dual.search(query, top_k=top_k)
        lat_dual = (time.perf_counter() - t1) * 1000.0

        standard_chunks = [c.id for c in resp_standard.citations if c.source_type == "chunk"]
        dual_chunks = [c.id for c in resp_dual.citations if c.source_type == "chunk"]
        dual_nodes = [c.id for c in resp_dual.citations if c.source_type == "node"]

        overlap = len(set(standard_chunks) & set(dual_chunks))
        jaccard = overlap / max(len(set(standard_chunks) | set(dual_chunks)), 1)

        return {
            "query": query,
            "standard_hybrid": {
                "chunk_ids": standard_chunks,
                "latency_ms": round(lat_standard, 2),
                "citations_count": len(resp_standard.citations)
            },
            "dual_level": {
                "chunk_ids": dual_chunks,
                "entity_node_ids": dual_nodes,
                "latency_ms": round(lat_dual, 2),
                "citations_count": len(resp_dual.citations),
                "trace": resp_dual.retrieval_trace
            },
            "metrics": {
                "chunk_overlap_count": overlap,
                "jaccard_similarity": round(jaccard, 3),
                "latency_delta_ms": round(lat_dual - lat_standard, 2)
            }
        }
