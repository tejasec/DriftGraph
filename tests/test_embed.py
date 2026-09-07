"""
Tests for Embeddings (SBERT & Word2Vec).
"""

import pytest
import numpy as np
from driftgraph.embed import SBERTEmbedder, Word2VecEmbedder


def test_sbert_embedder():
    embedder = SBERTEmbedder()
    texts = ["GraphRAG uses hierarchical Leiden communities.", "FastAPI serves REST endpoints."]
    vectors = embedder.embed_texts(texts)

    assert isinstance(vectors, np.ndarray)
    assert vectors.shape[0] == 2
    assert vectors.shape[1] == embedder.dimension

    query_vec = embedder.embed_query("GraphRAG query")
    assert query_vec.shape[0] == embedder.dimension


def test_word2vec_baseline():
    w2v = Word2VecEmbedder(vector_size=64)
    corpus = ["DriftGraph builds knowledge graphs from markdown notes.", "Sentence transformers produce embeddings."]
    w2v.fit(corpus)
    vecs = w2v.embed_texts(corpus)

    assert vecs.shape[0] == 2
    assert vecs.shape[1] == 64
