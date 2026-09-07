---
title: "Weekly Sync - Jan 15"
tags: [meeting, team, planning, roadmap]
date: 2024-01-15
---

# Weekly Sync - Jan 15

## Attendees
- Alice Chen
- Bob Smith
- Carol Williams

## Discussion

**Alice Chen** presented the Q1 roadmap for DriftGraph. Key priorities:
1. Complete the Markdown ingestion and chunking pipeline.
2. Benchmark embedding models (Sentence-BERT vs Word2Vec baseline).
3. Implement the GraphRAG hierarchical Map-Reduce summarization engine.

**Bob Smith** raised concerns about API query latency with large graphs.
**Carol Williams** suggested using FAISS with Inner Product indexing for fast local similarity search alongside SQLite FTS5.

## Action Items

- [ ] Alice Chen: Finalize GraphRAG architecture documentation.
- [ ] Bob Smith: Implement `/api/query` and Cytoscape.js visualization.
- [ ] Carol Williams: Run ablation study and RAGAS benchmark on embedding models.
