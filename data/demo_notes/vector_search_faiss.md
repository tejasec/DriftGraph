---
title: "Vector Embeddings and FAISS Indexing"
tags: [embeddings, vector-search, faiss, sbert]
---

# Vector Embeddings and FAISS Indexing

Dense vector representations enable semantic retrieval by encoding textual meaning into continuous geometric vector spaces.

## Sentence-BERT & Embedding Dimensions

DriftGraph utilizes `all-MiniLM-L6-v2`, producing 384-dimensional dense vectors. These embeddings capture subtle conceptual nuances, synonyms, and semantic proximity across note chunks.

## FAISS In-Memory & Disk Index

Facebook AI Similarity Search (FAISS) provides highly optimized vector search:
- **Inner Product Metric**: Embeddings are L2-normalized upon indexing, transforming cosine similarity into fast inner product dot products.
- **Index Persistence**: Vectors and ID mappings are serialized to disk (`faiss.index`, `faiss.meta.npy`, `faiss.vec.npy`) for instant sub-millisecond warm starts.
- **Hybrid Fusion**: Vector similarity scores combine with SQLite FTS5 full-text keyword scores using Reciprocal Rank Fusion (RRF).
