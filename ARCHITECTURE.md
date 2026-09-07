# DriftGraph System Architecture & Research Design

## 1. System Overview

**DriftGraph** is a local-first, privacy-preserving GraphRAG system designed to convert personal Markdown note repositories into an interactive, navigable Knowledge Graph with hierarchical summarization and dual-mode query answering.

```
                    ┌────────────────────────┐
                    │   Raw Markdown Notes   │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ 1. Ingestion & Parser  │ (pathlib, frontmatter, mistune)
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ 2. Semantic Chunker    │ (sentence boundaries + sliding window)
                    └───────────┬────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│ 3. Embedding Pipeline        │        │ 4. Extraction Engine         │
│    - Sentence-BERT (384-d)   │        │    - Local Ollama LLM        │
│    - Word2Vec Baseline       │        │    - JSON Schema Triples     │
└──────────────┬───────────────┘        └──────────────┬───────────────┘
               │                                       │
               └───────────────────┬───────────────────┘
                                   ▼
                    ┌────────────────────────┐
                    │ 5. Graph Assembly &    │ (NetworkX MultiDiGraph,
                    │    Entity Resolution   │  dedup fuzzy matching)
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ 6. Leiden Community    │ (Hierarchical multi-level
                    │    Detection           │  partitioning)
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ 7. Map-Reduce Summary  │ (Map: Community summaries,
                    │    Synthesis           │  Reduce: Global synthesis)
                    └───────────┬────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│ 8. SQLite + FTS5 & FAISS     │        │ 9. FastAPI & Cytoscape.js    │
│    - Relational schema       │        │    - Interactive Web UI      │
│    - Hybrid vector/BM25      │        │    - Global & Local Q&A      │
└──────────────────────────────┘        └──────────────────────────────┘
```

---

## 2. Research Hypothesis & Novelty

1. **Lightweight Embedding Efficacy**:
   Can small, CPU-friendly embedding models (e.g. `sentence-transformers/all-MiniLM-L6-v2` at 384 dimensions) provide comparable knowledge clustering and retrieval precision compared to cloud models (1536+ dimensions), while reducing memory footprint by over 70%?

2. **Hierarchical GraphRAG over Flat Vector RAG**:
   Community summarization via Leiden partitioning enables the system to answer abstract, corpus-wide synthesis questions ("What are the overarching themes?") that flat vector similarity search fails to capture.

3. **Hybrid Local Search (FAISS IP + SQLite FTS5 BM25)**:
   Combining dense semantic embeddings with exact lexical matching via Reciprocal Rank Fusion (RRF) eliminates entity hallucinations in targeted fact retrieval.

---

## 3. Pipeline Modules

| Module | Description | Key Technologies |
|---|---|---|
| `driftgraph/ingest/` | Strips YAML frontmatter, extracts metadata provenance, chunks into sentence-aware segments (~256-512 tokens). | `python-frontmatter`, `mistune`, `aiofiles` |
| `driftgraph/embed/` | Generates 384-d normalized embeddings on CPU; trains Gensim Word2Vec for baseline ablation. | `sentence-transformers`, `gensim`, `numpy` |
| `driftgraph/extract/` | Extracts structured `(Subject, Predicate, Object)` triples with few-shot JSON formatting and robust heuristic fallbacks. | `ollama`, `httpx`, Pydantic v2 |
| `driftgraph/graph/` | Entity deduplication, NetworkX multi-directed graph assembly, Leiden community detection, and FAISS indexing. | `networkx`, `leidenalg`, `faiss-cpu` |
| `driftgraph/summarize/` | GraphRAG Map-Reduce pipeline generating per-community and root-level global summaries. | Ollama / Map-Reduce |
| `driftgraph/query/` | QueryRouter dispatches to Global GraphRAG or Local Hybrid (FAISS + SQLite FTS5 BM25). | SQLite FTS5, FAISS, RRF |
| `driftgraph/serve/` | FastAPI backend serving Cytoscape.js force-directed graph UI and real-time Q&A endpoints. | `fastapi`, `uvicorn`, Cytoscape.js |
| `driftgraph/eval/` | Stage latency, peak memory (RSS MB), CPU %, RAGAS metric harness, and embedding ablation runner. | `psutil`, `ragas` |
