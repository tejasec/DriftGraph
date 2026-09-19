---
title: "Dual-Route Query Routing and RAG Search"
tags: [query-engine, global-search, local-search, graphrag]
---

# Dual-Route Query Routing and RAG Search

DriftGraph's query engine intelligently inspects incoming questions and routes them to the optimal retrieval strategy.

## Global Search vs. Local Search

- **Global Search**: Tailored for broad, holistic questions such as *"What are the main themes across my research?"* or *"Summarize key trends in my notes."* It evaluates hierarchical Leiden community summaries to synthesize comprehensive answers.
- **Local Search**: Optimized for specific, entity-centric questions like *"How does FAISS interact with Sentence-BERT?"* It performs hybrid vector and FTS5 keyword retrieval, followed by 1-hop knowledge graph expansion.

## Grounded Synthesis & Citations

Every generated answer references citations with note titles, source types (chunk or community), and confidence scores, grounding responses and preventing LLM hallucinations.
