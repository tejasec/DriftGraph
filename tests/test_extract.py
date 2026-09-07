"""
Tests for Entity and Relation extraction.
"""

import pytest
from driftgraph.extract.parser import parse_llm_extraction_response, fallback_heuristic_extraction
from driftgraph.ingest.models import Chunk


def test_parse_llm_extraction_response():
    raw_json = """
    {
      "entities": [
        {"name": "FastAPI", "type": "TECHNOLOGY", "description": "Web framework"},
        {"name": "Alice Chen", "type": "PERSON", "description": "Tech Lead"}
      ],
      "relations": [
        {"subject": "Alice Chen", "predicate": "LEADS", "object": "FastAPI"}
      ]
    }
    """
    res = parse_llm_extraction_response(raw_json, "chunk_1")
    assert len(res.entities) == 2
    assert len(res.relations) == 1
    assert res.entities[0].name == "FastAPI"
    assert res.relations[0].predicate == "LEADS"


def test_fallback_heuristic_extraction():
    text = "Alice Chen developed **DriftGraph** using `FastAPI` and `Sentence-BERT`."
    res = fallback_heuristic_extraction(text, "chunk_2")

    assert len(res.entities) >= 2
    entity_names = [e.name.lower() for e in res.entities]
    assert "driftgraph" in entity_names or "fastapi" in entity_names
