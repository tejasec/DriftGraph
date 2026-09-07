---
title: "Research Ideas and Literature"
tags: [research, nlp, embeddings, graphrag]
date: 2024-01-20
---

# Research Foundation: GraphRAG & Lightweight Embeddings

DriftGraph investigates whether lightweight Sentence-BERT embeddings (`all-MiniLM-L6-v2`, 384 dimensions) can generate high-quality knowledge graphs on CPU-only edge hardware.

## Key Papers

1. **Sentence-BERT**: Sentence Embeddings using Siamese BERT-Networks (Reimers & Gurevych, 2019).
2. **From Local to Global**: A Graph RAG Approach to Query-Focused Summarization (Microsoft Research, 2024).

## Hypotheses

- **Hypothesis 1**: Leiden community detection over extracted entity graphs provides richer global question answering than standard vector RAG.
- **Hypothesis 2**: Hybrid search combining dense embeddings with BM25 (SQLite FTS5) reduces hallucination on entity-specific fact retrieval.
- **Hypothesis 3**: 384-dimensional embeddings provide equivalent top-k retrieval accuracy to 1536-d models with 75% lower memory footprint.
