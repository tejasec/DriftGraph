---
title: "GraphRAG Architecture and Pipeline"
tags: [graphrag, architecture, pipeline, nlp]
---

# GraphRAG Architecture and Pipeline

GraphRAG combines knowledge graphs with Retrieval-Augmented Generation to address the limitations of pure vector search. While traditional RAG retrieves isolated chunks based on embedding similarity, GraphRAG maps the relationships between entities across documents.

## Key Pipeline Stages

1. **Semantic Ingestion & Chunking**: Markdown documents are parsed into semantically coherent chunks while preserving AST structure, header provenance, and wikilinks.
2. **Entity & Relation Extraction**: Language models extract subject-predicate-object triples, mapping out domain concepts and directed relationships.
3. **Leiden Community Detection**: Hierarchical clustering groups related entities into modular communities at multiple levels of granularity.
4. **Map-Reduce Summarization**: High-level community summaries are generated in parallel, enabling global thematic synthesis.
5. **Dual-Route Retrieval**: Queries route dynamically between Global Search (thematic overview) and Local Search (pinpoint factual retrieval).
