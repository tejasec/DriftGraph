"""
Tests for API-backed Demo Mode, OpenAI-compatible client, and secrets hygiene.
"""

import os
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from driftgraph.config import Config, LLMConfig
from driftgraph.extract.models import ExtractionConfig, ExtractionResult, Entity, Relation
from driftgraph.extract.ollama_client import OllamaExtractionClient
from driftgraph.extract.api_client import APIExtractionClient, call_chat_completion
from driftgraph.extract import get_extraction_client
from driftgraph.ingest.models import Chunk


def test_config_llm_defaults():
    """Verify default LLM configuration maintains local-first Ollama defaults."""
    cfg = Config.load("config.yaml")
    assert cfg.llm.provider == "ollama"
    assert "llama3.1" in cfg.llm.model
    assert cfg.llm.api_key_env == "LLM_API_KEY"
    assert "LLM_API_KEY" in cfg.llm.api_key_env


def test_startup_validation_fails_without_key(monkeypatch):
    """With provider: openai_compatible and no key, app must fail at startup with a readable error."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    llm_cfg = LLMConfig(provider="openai_compatible", api_key_env="LLM_API_KEY")

    with pytest.raises(ValueError) as exc_info:
        llm_cfg.validate_provider()

    err_msg = str(exc_info.value)
    assert "openai_compatible" in err_msg
    assert "LLM_API_KEY" in err_msg
    assert "missing or empty" in err_msg


def test_startup_validation_succeeds_with_key(monkeypatch):
    """With provider: openai_compatible and key present, validation passes."""
    monkeypatch.setenv("LLM_API_KEY", "test-demo-key-12345")
    llm_cfg = LLMConfig(provider="openai_compatible", api_key_env="LLM_API_KEY")
    llm_cfg.validate_provider()
    assert llm_cfg.get_api_key() == "test-demo-key-12345"


def test_startup_validation_ollama_does_not_require_key(monkeypatch):
    """With provider: ollama, validation passes even if key is unset."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    llm_cfg = LLMConfig(provider="ollama", api_key_env="LLM_API_KEY")
    llm_cfg.validate_provider()


def test_create_app_fails_at_startup_when_key_missing(monkeypatch):
    """create_app must fail fast at startup if provider is openai_compatible and key is missing."""
    from driftgraph.serve.app import create_app
    from driftgraph.config import config as global_config
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(global_config.llm, "provider", "openai_compatible")

    with pytest.raises(ValueError) as exc_info:
        create_app()

    assert "LLM_API_KEY" in str(exc_info.value)


def test_api_client_interface_matches_ollama():
    """APIExtractionClient must implement the exact same interface as OllamaExtractionClient."""
    ollama_methods = {m for m in dir(OllamaExtractionClient) if not m.startswith("_")}
    api_methods = {m for m in dir(APIExtractionClient) if not m.startswith("_")}

    for method in ["is_available", "extract_from_chunk", "extract_batch", "close"]:
        assert method in ollama_methods, f"Missing {method} on OllamaExtractionClient"
        assert method in api_methods, f"Missing {method} on APIExtractionClient"


@pytest.mark.asyncio
async def test_api_client_extraction_and_retry(monkeypatch):
    """Verify APIExtractionClient parses LLM responses and retries with backoff on 429."""
    from openai import RateLimitError
    import httpx

    chunk = Chunk(
        id="chunk_test_1",
        note_id="note_test",
        source_file="sample.md",
        text="GraphRAG connects knowledge graphs to vector search.",
        chunk_index=0,
        start_char=0,
        end_char=52,
        token_count=10,
    )

    client = APIExtractionClient(ExtractionConfig(
        model="llama3.1:8b-instruct-q4_K_M",
        base_url="http://localhost:11434/v1",
        api_key="mock-test-key",
        max_retries=2
    ))

    # Mock chat completion response
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps({
        "entities": [
            {"name": "GraphRAG", "type": "FRAMEWORK", "description": "Graph RAG system"},
            {"name": "Vector Search", "type": "TECHNOLOGY", "description": "Vector similarity search"}
        ],
        "relations": [
            {"subject": "GraphRAG", "predicate": "CONNECTS_TO", "object": "Vector Search", "description": "Links graph with vector"}
        ]
    })
    mock_response = MagicMock(choices=[mock_choice])

    # First call raises RateLimitError (429), second call succeeds
    req = httpx.Request("POST", "http://test/v1/chat/completions")
    resp_429 = httpx.Response(429, request=req)
    rate_err = RateLimitError(message="Rate limit exceeded", response=resp_429, body={"error": "rate_limited"})

    call_count = 0

    async def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise rate_err
        return mock_response

    monkeypatch.setattr(client.client.chat.completions, "create", mock_create)

    # Execute extraction
    result = await client.extract_from_chunk(chunk)
    await client.close()

    assert call_count == 2
    assert isinstance(result, ExtractionResult)
    assert len(result.entities) == 2
    assert result.entities[0].name == "GraphRAG"
    assert len(result.relations) == 1
    assert result.relations[0].predicate == "CONNECTS_TO"


@pytest.mark.asyncio
async def test_secrets_hygiene_status_endpoint(monkeypatch):
    """The API key must NEVER be returned by any API endpoint or exposed to the frontend."""
    from driftgraph.config import config as global_config
    secret_key = "super-secret-production-token-do-not-leak"
    monkeypatch.setenv("LLM_API_KEY", secret_key)
    monkeypatch.setattr(global_config.llm, "provider", "openai_compatible")

    from driftgraph.serve.app import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/status")
        assert resp.status_code == 200
        raw_text = resp.text
        # Critical security assertion: secret_key MUST NEVER appear anywhere in the response
        assert secret_key not in raw_text
        data = resp.json()
        assert data["llm"]["provider"] == "openai_compatible"
        assert "api_key" not in data["llm"]


@pytest.mark.asyncio
async def test_build_and_query_openai_compatible_mode(tmp_path, monkeypatch):
    """With provider: openai_compatible and LLM_API_KEY set, a build and query both succeed."""
    from driftgraph.config import config as global_config
    from driftgraph.main import build_pipeline
    from driftgraph.query import QueryEngine, QueryRequest
    from driftgraph.embed import SBERTEmbedder
    from driftgraph.graph import SQLiteStorage, VectorIndex

    # Set up temp paths and environment
    db_path = str(tmp_path / "test_demo.db")
    vec_path = str(tmp_path / "test_demo.index")
    notes_dir = str(tmp_path / "demo_notes")
    os.makedirs(notes_dir, exist_ok=True)

    # Write a clean demo note
    sample_note = tmp_path / "demo_notes" / "sample.md"
    sample_note.write_text(
        "# DriftGraph Demo\n\nGraphRAG enables structured retrieval over knowledge graphs.",
        encoding="utf-8"
    )

    monkeypatch.setenv("LLM_API_KEY", "test-demo-key-12345")
    monkeypatch.setattr(global_config.llm, "provider", "openai_compatible")
    monkeypatch.setattr(global_config.database, "sqlite_path", db_path)
    monkeypatch.setattr(global_config.database, "vector_index_path", vec_path)

    # Mock call_chat_completion to return responses without needing real network calls
    async def mock_call_chat(*args, **kwargs):
        messages = kwargs.get("messages", [])
        if kwargs.get("response_format", {}).get("type") == "json_object":
            return json.dumps({
                "entities": [{"name": "DriftGraph", "type": "SYSTEM"}, {"name": "GraphRAG", "type": "METHOD"}],
                "relations": [{"subject": "DriftGraph", "predicate": "USES", "object": "GraphRAG"}],
                "low_level": ["DriftGraph", "GraphRAG"],
                "high_level": ["Knowledge Graphs"]
            })
        return "DriftGraph is a GraphRAG knowledge graph assistant."

    monkeypatch.setattr("driftgraph.extract.api_client.call_chat_completion", mock_call_chat)

    async def mock_extract(self, chunk):
        return ExtractionResult(
            chunk_id=chunk.id,
            entities=[
                Entity(name="DriftGraph", type="SYSTEM", description="System"),
                Entity(name="GraphRAG", type="METHOD", description="Method")
            ],
            relations=[
                Relation(subject="DriftGraph", predicate="USES", object="GraphRAG", description="Uses")
            ]
        )

    monkeypatch.setattr("driftgraph.extract.api_client.APIExtractionClient.extract_from_chunk", mock_extract)

    # Run build pipeline
    await build_pipeline(notes_dir)

    # Verify build artifacts created
    assert os.path.exists(db_path)
    assert os.path.exists(vec_path)

    # Run query
    embedder = SBERTEmbedder()
    vec_index = VectorIndex(dimension=embedder.dimension, index_path=vec_path)
    assert vec_index.load()
    storage = SQLiteStorage(db_path=db_path)
    await storage.initialize_schema()

    engine = QueryEngine(
        embedder=embedder,
        vector_index=vec_index,
        storage=storage,
        llm_provider="openai_compatible",
        llm_api_key="test-demo-key-12345"
    )

    # Global search query
    res_global = await engine.query(QueryRequest(query="What is DriftGraph?", mode="global"))
    assert res_global.answer
    assert res_global.mode_used == "global"

    # Local search query
    res_local = await engine.query(QueryRequest(query="DriftGraph details", mode="local"))
    assert res_local.answer
    assert res_local.mode_used == "local"


def test_demo_corpus_and_precomputed_artifacts_present():
    """Verify small non-private demo corpus and precomputed database exist."""
    assert os.path.isdir("data/demo_notes")
    demo_files = [f for f in os.listdir("data/demo_notes") if f.endswith(".md")]
    assert len(demo_files) >= 3, "Expected at least 3 markdown files in data/demo_notes"

    assert os.path.exists("data/driftgraph.db"), "Expected precomputed data/driftgraph.db"
    assert os.path.exists("data/faiss.index"), "Expected precomputed data/faiss.index"
