"""
Tests for Query Router and Engine.
"""

from driftgraph.query.router import QueryRouter


def test_query_router():
    router = QueryRouter()

    assert router.route("What are the main themes across my notes?") == "global"
    assert router.route("Give an overview of the whole project") == "global"
    assert router.route("Who is Alice Chen?") == "local"
    assert router.route("What embeddings are used?") == "local"
    assert router.route("What embeddings are used?", explicit_mode="global") == "global"
