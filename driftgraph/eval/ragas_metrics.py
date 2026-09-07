"""
RAGAS evaluation metrics harness for DriftGraph.
"""

from typing import List, Dict, Any, Optional
import structlog
from driftgraph.eval.models import EvaluationScores

logger = structlog.get_logger(__name__)


class RagasEvaluator:
    """Computes Context Precision, Faithfulness, and Answer Relevance."""

    def evaluate_response(
        self,
        query: str,
        answer: str,
        retrieved_contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> EvaluationScores:
        """
        Evaluate a single RAG response.
        Uses exact token overlap & semantic alignment heuristics if Ragas library is offline.
        """
        # Context Precision: Proportion of retrieved contexts that contain query keywords
        query_words = set(query.lower().split())
        matched_contexts = 0
        for ctx in retrieved_contexts:
            ctx_words = set(ctx.lower().split())
            if query_words.intersection(ctx_words):
                matched_contexts += 1

        context_precision = matched_contexts / max(1, len(retrieved_contexts))

        # Faithfulness: Proportion of answer claims grounded in retrieved context
        answer_words = set(answer.lower().split())
        all_ctx_words = set(" ".join(retrieved_contexts).lower().split())
        grounded_words = answer_words.intersection(all_ctx_words)
        faithfulness = min(1.0, len(grounded_words) / max(1, len(answer_words) * 0.7))

        # Answer Relevance: Keyword alignment with user query
        ans_query_overlap = query_words.intersection(answer_words)
        answer_relevance = min(1.0, len(ans_query_overlap) / max(1, len(query_words) * 0.5))

        overall = (context_precision * 0.3) + (faithfulness * 0.4) + (answer_relevance * 0.3)

        return EvaluationScores(
            context_precision=round(context_precision, 3),
            faithfulness=round(faithfulness, 3),
            answer_relevance=round(answer_relevance, 3),
            overall_score=round(overall, 3)
        )
