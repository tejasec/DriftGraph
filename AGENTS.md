# DriftGraph Agent Instructions

## Project Goal
Build a local-first GraphRAG system (DriftGraph) that converts Markdown notes into an interactive knowledge graph with semantic linking, community detection, and query-focused Q&A.

## Architecture
- **Ingestion**: `pathlib`, `mistune`, `python-frontmatter` → semantic chunking with provenance
- **Embedding**: `sentence-transformers` (`all-MiniLM-L6-v2`, 384-d) + Gensim Word2Vec baseline
- **Extraction**: Ollama (`llama3.1:8b-instruct-q4_K_M`) for entity/relation extraction with JSON schema validation & fallback heuristics
- **Graph**: NetworkX `MultiDiGraph` + `leidenalg` / community detection for hierarchical partitioning
- **Vector Store**: FAISS (in-memory + disk index) + cosine similarity
- **Relational DB**: SQLite with FTS5 for full-text search & entity/edge/community persistence
- **Summarization**: Hierarchical Map-Reduce over Leiden communities (GraphRAG pattern)
- **Query Engine**: Intelligent query router dispatching to Global Search (community summaries) or Local Search (hybrid FAISS + FTS5)
- **API**: FastAPI backend + static frontend (Cytoscape.js force-directed graph UI)
- **Evaluation**: psutil latency/memory benchmarks, RAGAS/TruLens metric harness, and embedding ablation studies

## Coding Standards
- Type hints everywhere (Python 3.11+)
- Async/await for I/O operations (FastAPI, Ollama client, file operations)
- Pydantic v2 for configuration and data schemas
- Structured logging with clean fallbacks
- Unit and pipeline tests with pytest
