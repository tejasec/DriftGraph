"""driftgraph/classifier/rule_based.py

Rule-based, fully offline text extraction & classification tool.
Complies with Feature Ideas.md specifications:
- Multi-category topic scoring (Legal, Financial, HR/Admin, Technical, Academic, Medical, Creative)
- Visual block ASCII progress bars (████░░░░) and formatted terminal box
- Auto-tagging: Topic, Sentiment, Priority
- Contextual entity generation links (origin web resources & connected concepts)
"""

from __future__ import annotations

import re
import urllib.parse
from collections import Counter
from typing import Dict, List, Optional, Tuple, Set

from driftgraph.classifier.models import (
    CategoryScore,
    ClassificationResult,
    ContextualEntity,
)


CATEGORIES: Dict[str, Set[str]] = {
    "Legal": {
        "agreement", "contract", "jurisdiction", "liability", "liabilities", "party",
        "parties", "terms", "clause", "compliance", "plaintiff", "defendant", "statutory",
        "indemnification", "whereas", "warranties", "intellectual property", "arbitration",
        "governing law", "confidentiality", "severability", "termination", "breach",
        "infringement", "remedies", "indemnity", "disclaimer", "covenant"
    },
    "Financial": {
        "revenue", "profit", "budget", "expenditure", "fiscal", "balance sheet",
        "valuation", "interest", "equity", "dividend", "cost", "costs", "q1", "q2", "q3", "q4",
        "audit", "cash flow", "income statement", "ebitda", "capital", "assets", "liabilities",
        "debt", "investment", "portfolio", "margin", "tax", "amortization", "depreciation"
    },
    "Hr Administrative": {
        "employee", "employees", "payroll", "onboarding", "personnel", "leave", "salary",
        "performance review", "manager", "policy", "benefits", "candidate", "interview",
        "resignation", "recruitment", "workplace", "attendance", "probation", "human resources",
        "job description", "compensation", "severance", "compliance officer"
    },
    "Technical": {
        "architecture", "api", "pipeline", "database", "latency", "algorithm", "microservice",
        "python", "server", "framework", "docker", "git", "vector", "embedding", "graph",
        "backend", "frontend", "sqlite", "query", "fastapi", "networkx", "faiss", "endpoint",
        "deploy", "repository", "async", "cache", "throughput", "runtime", "client"
    },
    "Academic Research": {
        "methodology", "hypothesis", "dataset", "citation", "literature", "abstract",
        "empirical", "experiment", "experiments", "publication", "findings", "evaluations",
        "benchmark", "framework", "ablation", "sota", "qualitative", "quantitative", "survey",
        "peer review", "proceedings", "conference", "theorem", "lemma", "proof"
    },
    "Medical Health": {
        "patient", "clinical", "diagnosis", "therapy", "pharmaceutical", "symptoms", "efficacy",
        "treatment", "dosage", "trial", "trials", "pathology", "disease", "syndrome", "hospital",
        "biomedical", "physician", "protocol", "remission", "prescription", "adverse event"
    },
    "Creative Personal": {
        "journal", "reflection", "brainstorm", "narrative", "inspiration", "travel", "thoughts",
        "ideas", "memory", "goals", "memoir", "story", "character", "sketch", "notes", "daily",
        "log", "mindset", "philosophy", "creative", "vision", "habit", "routine"
    }
}

SENTIMENT_POSITIVE = {
    "achieve", "success", "successful", "improve", "improved", "improvement", "benefit",
    "optimal", "effective", "efficient", "excellent", "gain", "prosper", "advantage", "growth",
    "high-quality", "breakthrough", "innovative", "reliable", "scalable", "delight"
}

SENTIMENT_NEGATIVE = {
    "error", "failure", "failed", "risk", "risks", "liability", "vulnerability", "breach",
    "loss", "losses", "penalty", "severe", "decline", "defect", "bottleneck", "harm", "dispute",
    "conflict", "violation", "delay", "degraded"
}

PRIORITY_URGENT = {
    "urgent", "critical", "immediate", "immediately", "deadline", "asap", "p0", "blocker",
    "emergency", "action required", "mandatory", "fatal"
}

PRIORITY_HIGH = {
    "high priority", "important", "essential", "priority", "upcoming", "q1 goal", "milestone",
    "crucial", "must have", "key deliverable"
}

PRIORITY_LOW = {
    "optional", "nice to have", "backlog", "future", "someday", "low priority", "p3", "fyi",
    "informational", "minor"
}


def make_ascii_bar(percent: float, bar_length: int = 20) -> str:
    """Generate a Unicode block progress bar (e.g. ████████████████░░░░)."""
    fraction = max(0.0, min(100.0, percent)) / 100.0
    filled = int(round(fraction * bar_length))
    empty = bar_length - filled
    return "█" * filled + "░" * empty


class DocumentClassifier:
    """Rule-based, fully offline text extractor & document classifier."""

    def classify_text(
        self,
        text: str,
        filename: str = "document.pdf",
        graph_connected_nodes: Optional[Dict[str, List[str]]] = None
    ) -> ClassificationResult:
        """
        Extract statistics, classify topics by rule-based keyword match, and format output.
        """
        cleaned = text.strip()
        words = re.findall(r"\b[A-Za-z0-9_-]+\b", cleaned)
        word_count = len(words)
        char_count = len(cleaned)
        line_count = len(cleaned.splitlines()) if cleaned else 0

        lower_text = cleaned.lower()

        # 1. Topic Category Scoring
        raw_scores: Dict[str, float] = {}
        matched_dict: Dict[str, List[str]] = {}

        for cat, keywords in CATEGORIES.items():
            count = 0.0
            matched_kws = []
            for kw in keywords:
                # Find occurrences of keyword/phrase
                if " " in kw:
                    occ = lower_text.count(kw)
                    if occ > 0:
                        count += occ * 2.0  # higher weight for multi-word phrases
                        matched_kws.append(kw)
                else:
                    pattern = rf"\b{re.escape(kw)}\b"
                    found = len(re.findall(pattern, lower_text))
                    if found > 0:
                        count += found
                        matched_kws.append(kw)

            raw_scores[cat] = count
            matched_dict[cat] = matched_kws

        total_score = sum(raw_scores.values())

        categories_res: List[CategoryScore] = []
        if total_score > 0:
            # Sort categories by raw score descending
            sorted_cats = sorted(raw_scores.items(), key=lambda x: x[1], reverse=True)
            for cat, score in sorted_cats:
                if score > 0:
                    pct = round((score / total_score) * 100.0, 1)
                    categories_res.append(CategoryScore(
                        category=cat,
                        percentage=pct,
                        raw_score=round(score, 1),
                        matched_keywords=matched_dict[cat][:6],
                        progress_bar=make_ascii_bar(pct, 20),
                    ))
        else:
            # Fallback if no specific keywords matched
            categories_res.append(CategoryScore(
                category="General",
                percentage=100.0,
                raw_score=1.0,
                matched_keywords=[],
                progress_bar=make_ascii_bar(100.0, 20),
            ))

        top_cat = categories_res[0].category if categories_res else "General"

        # 2. Build the ASCII Terminal Box
        ascii_box = self._render_ascii_box(filename, word_count, char_count, categories_res)

        # 3. Sentiment Estimation
        pos_count = sum(len(re.findall(rf"\b{re.escape(w)}\b", lower_text)) for w in SENTIMENT_POSITIVE)
        neg_count = sum(len(re.findall(rf"\b{re.escape(w)}\b", lower_text)) for w in SENTIMENT_NEGATIVE)
        sent_denom = max(1, pos_count + neg_count)
        sent_score = round((pos_count - neg_count) / sent_denom, 2)
        if sent_score > 0.2:
            sentiment = "positive"
        elif sent_score < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # 4. Priority Estimation
        urgent_matches = sum(1 for kw in PRIORITY_URGENT if kw in lower_text)
        high_matches = sum(1 for kw in PRIORITY_HIGH if kw in lower_text)
        low_matches = sum(1 for kw in PRIORITY_LOW if kw in lower_text)

        if urgent_matches > 0:
            priority = "urgent"
        elif high_matches > 0:
            priority = "high"
        elif low_matches > 0:
            priority = "low"
        else:
            priority = "medium"

        # 5. Auto-tagging
        auto_tags = [top_cat.lower().replace(" ", "_")]
        for c in categories_res[1:3]:
            if c.percentage >= 15.0:
                auto_tags.append(c.category.lower().replace(" ", "_"))
        auto_tags.append(f"sentiment_{sentiment}")
        auto_tags.append(f"prio_{priority}")

        # Add top matched keywords as sub-tags
        top_kws = [kw.replace(" ", "_") for c in categories_res for kw in c.matched_keywords[:2]]
        for kw in top_kws:
            if kw not in auto_tags and len(auto_tags) < 8:
                auto_tags.append(kw)

        # 6. Contextual Entity Generation (Origin Links & Connected Concepts)
        contextual_entities: List[ContextualEntity] = []
        # Extract prominent nouns/entities (capitalized terms or top keywords)
        caps = re.findall(r"\b[A-Z][a-zA-Z0-9_-]{2,}\b", cleaned)
        cap_counts = Counter(caps)
        prominent = [term for term, _ in cap_counts.most_common(5) if term.lower() not in {"the", "this", "that", "page", "table"}]

        for term in prominent:
            encoded = urllib.parse.quote_plus(term)
            origin_url = f"https://en.wikipedia.org/wiki/{encoded}"
            search_url = f"https://duckduckgo.com/?q={encoded}"
            connected = []
            if graph_connected_nodes and term.lower() in graph_connected_nodes:
                connected = graph_connected_nodes[term.lower()][:4]

            contextual_entities.append(ContextualEntity(
                entity=term,
                category=top_cat,
                origin_url=origin_url,
                search_url=search_url,
                connected_concepts=connected,
            ))

        return ClassificationResult(
            filename=filename,
            word_count=word_count,
            char_count=char_count,
            line_count=line_count,
            top_category=top_cat,
            categories=categories_res,
            ascii_box=ascii_box,
            auto_tags=auto_tags,
            sentiment=sentiment,
            sentiment_score=sent_score,
            priority=priority,
            contextual_entities=contextual_entities,
        )

    def _render_ascii_box(
        self,
        filename: str,
        word_count: int,
        char_count: int,
        categories: List[CategoryScore],
    ) -> str:
        """Format the exact ASCII box as shown in Feature Ideas.md."""
        lines = [
            "╔══════════════════════════════════════════════════════╗",
            "║       📄 Text Extraction & Classification Tool       ║",
            "║              Rule-Based · Fully Offline               ║",
            "╚══════════════════════════════════════════════════════╝",
            "",
            "────────────────────────────────────────────────────────────",
            f"📄 {filename}",
            f"   {word_count:,} words · {char_count:,} characters",
            "",
        ]

        for idx, cat in enumerate(categories[:5]):
            pointer = "▶" if idx == 0 else " "
            lines.append(f"   {pointer} {cat.progress_bar} {cat.percentage:>5.1f}%  {cat.category}")

        return "\n".join(lines)

    classify = classify_text
