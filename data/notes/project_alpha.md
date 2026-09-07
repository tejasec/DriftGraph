---
title: "Project Alpha"
tags: [project, backend, api, graphrag]
date: 2024-01-15
---

# Project Alpha

Project Alpha is a **FastAPI-based backend service** for the DriftGraph system.
It handles note ingestion, embedding generation, and graph construction.

## Key Components

- **Ingestion Service**: Parses Markdown files, strips YAML frontmatter, and performs semantic sentence chunking.
- **Embedding Service**: Uses `sentence-transformers/all-MiniLM-L6-v2` for 384-d dense vector embeddings on CPU.
- **Graph Service**: Builds a NetworkX graph with entity and relation extraction via Ollama.
- **Community Detection**: Applies Leiden partitioning to cluster related conceptual nodes.

## Team

- **Alice Chen** (Tech Lead) - oversees architecture and GraphRAG design.
- **Bob Smith** (Backend Engineer) - implements the API layer and SQLite FTS5 persistence.
- **Carol Williams** (ML Engineer) - optimizes embedding pipelines and benchmarks retrieval quality.

## Dependencies

Requires Python 3.11+, Ollama running locally with Llama 3.1 8B model.
