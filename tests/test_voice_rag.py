"""
Tests for End-to-End Voice Assistant RAG and Grounded Graph Integration.
Verifies:
- POST /api/voice/ask endpoint contract (quick_mode and full graph RAG mode)
- GET /api/voice/audio/{audio_id} audio streaming endpoint
- Conversational session memory tracking
- ElevenLabs TTS audio synthesis & fallback behavior
- Frontend index.html and galaxy-engine.js voice integration and canvas highlighting contracts
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient, ASGITransport

from driftgraph.serve.app import create_app
from driftgraph.voice.models import VoiceRequest, VoiceResponse
from driftgraph.voice.elevenlabs import ElevenLabsClient
from driftgraph.voice.router import VoiceAssistant, VOICE_AUDIO_CACHE
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.graph.models import Node, Edge, Community


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def sample_graph_storage(tmp_path):
    db_file = tmp_path / "voice_test.db"
    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    nodes = [
        Node(id="node_a", name="Transformers", type="MODEL", description="Attention-based neural architecture", degree=3, community_id=1),
        Node(id="node_b", name="Attention", type="MECHANISM", description="Multi-head scaled dot product attention", degree=2, community_id=1),
    ]
    edges = [
        Edge(id="e1", source="node_a", target="node_b", predicate="USES", weight=1.0),
    ]
    communities = [
        Community(id=1, level=0, name="Transformers", node_ids=["node_a", "node_b"], summary="Neural attention models"),
    ]
    await storage.save_graph(nodes, edges, communities)
    return storage


@pytest.mark.asyncio
async def test_voice_ask_quick_mode(client):
    """POST /api/voice/ask in quick_mode=True returns direct entity matches and cited_node_ids."""
    payload = {
        "query": "Neural Networks",
        "quick_mode": True,
        "session_id": "test_quick_session"
    }
    resp = await client.post("/api/voice/ask", json=payload)
    assert resp.status_code == 200, f"Error: {resp.text}"

    data = resp.json()
    assert "answer" in data
    assert "text_answer" in data
    assert data["answer"] == data["text_answer"]
    assert data["mode_used"] == "quick"
    assert "cited_node_ids" in data
    assert isinstance(data["cited_node_ids"], list)
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert "citations" in data
    assert data["session_id"] == "test_quick_session"


@pytest.mark.asyncio
async def test_voice_ask_audio_streaming(client):
    """POST /api/voice/ask with mocked TTS returns audio_url and GET /api/voice/audio/{id} streams MP3 bytes."""
    fake_mp3 = b"\xff\xfb\x90\x44\x00\x00\x00\x00\x00"  # mock MP3 frame header
    with patch.object(ElevenLabsClient, "text_to_speech_bytes", new_callable=AsyncMock) as mock_tts:
        mock_tts.return_value = fake_mp3

        # Force TTS client in route to have a key
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test_key_123"}):
            payload = {
                "query": "What is DriftGraph?",
                "quick_mode": True,
                "session_id": "test_audio_session"
            }
            resp = await client.post("/api/voice/ask", json=payload)
            assert resp.status_code == 200

            data = resp.json()
            assert data["audio_base64"] is not None
            assert data["audio_url"] is not None
            assert data["audio_url"].startswith("/api/voice/audio/")

            # Stream audio from the returned audio_url
            audio_resp = await client.get(data["audio_url"])
            assert audio_resp.status_code == 200
            assert audio_resp.headers["content-type"] == "audio/mpeg"
            assert audio_resp.content == fake_mp3


@pytest.mark.asyncio
async def test_voice_audio_not_found(client):
    """GET /api/voice/audio/{unknown_id} returns HTTP 404."""
    resp = await client.get("/api/voice/audio/non_existent_audio_id")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_voice_ask_alias_route(client):
    """POST /api/voice/query acts as a compatible alias for /api/voice/ask."""
    payload = {
        "query": "Deep Learning",
        "quick_answer": True,
        "session_id": "test_alias_session"
    }
    resp = await client.post("/api/voice/query", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data["answer"]
    assert data["session_id"] == "test_alias_session"


@pytest.mark.asyncio
async def test_voice_conversational_memory_multiturn(sample_graph_storage):
    """Voice assistant retains conversational turns across multi-turn queries."""
    class MockQueryEngine:
        def __init__(self, storage):
            self.storage = storage

        async def query(self, req):
            from driftgraph.query.models import QueryResponse, Citation
            return QueryResponse(
                query=req.query,
                mode_used="local",
                answer=f"Processed query with history context: {req.query}",
                citations=[Citation(source_type="node", id="node_a", text_snippet="Sample node A", score=1.0)]
            )

    assistant = VoiceAssistant(query_engine=MockQueryEngine(sample_graph_storage))

    # Turn 1
    req1 = VoiceRequest(query="Tell me about Transformers", session_id="multi_turn_session")
    res1 = await assistant.process_voice_query(req1)
    assert "Transformers" in res1.answer
    assert "node_a" in res1.cited_node_ids

    # Turn 2
    req2 = VoiceRequest(query="How does attention work?", session_id="multi_turn_session")
    res2 = await assistant.process_voice_query(req2)
    assert "attention" in res2.answer

    # Verify session history in memory manager (2 user + 2 assistant turns = 4)
    session = assistant.memory.get_session("multi_turn_session")
    assert len(session.turns) == 4
    assert session.turns[0].role == "user"
    assert session.turns[0].content == "Tell me about Transformers"
    assert session.turns[2].role == "user"
    assert session.turns[2].content == "How does attention work?"


def test_frontend_voice_integration_contracts():
    """Verify frontend/index.html and galaxy-engine.js have the Voice RAG integration contracts."""
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")

    # Toolbar voice button & mic auto-trigger
    assert 'id="voiceQueryBtn"' in content
    assert 'openModal("modalVoice")' in content
    assert 'fetch("/api/voice/ask"' in content

    # Grounded canvas node highlighting
    assert "function highlightCitedNodes(nodeIds)" in content
    assert "window.galaxyEngine.highlightNodes(nodeIds)" in content
    assert "node.highlight" in content

    # Audio playback streaming
    assert "new Audio(" in content
    assert "window.speechSynthesis" in content

    # GalaxyEngine highlightNodes contract
    engine_path = Path(__file__).parent.parent / "frontend" / "assets" / "js" / "galaxy-engine.js"
    assert engine_path.exists()
    engine_content = engine_path.read_text(encoding="utf-8")
    assert "highlightNodes(ids)" in engine_content
    assert "this.highlightedNodeIds" in engine_content
