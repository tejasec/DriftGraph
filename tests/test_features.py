"""
Comprehensive tests for newly added features from Feature Ideas.md:
- Rule-based document classification (offline, ASCII terminal formatting, sentiment, priority, auto-tags)
- Graph Intelligence & Analytics (God nodes, shortest path narrative, surprising connections, suggested questions, subgraph)
- Voice Assistant RAG (quick-answer mode, conversational memory, audio transcription, voice-to-note)
- Note Templates & Multi-source Ingestion (web scraping, template instantiation)
- Note CRUD & Export Endpoints (CSV, Markdown digest, Vector Embeddings, Notes repository)
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from driftgraph.serve.app import app
from driftgraph.config import config as global_config
from driftgraph.classifier.rule_based import DocumentClassifier
from driftgraph.classifier.models import ClassificationResult
from driftgraph.analytics.graph_analytics import GraphAnalyticsEngine
from driftgraph.analytics.models import GraphAnalyticsReport
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.graph.models import Node, Edge, Community
from driftgraph.voice.transcriber import AudioTranscriber
from driftgraph.voice.memory import ConversationMemoryManager
from driftgraph.voice.router import VoiceAssistant
from driftgraph.voice.models import VoiceRequest
from driftgraph.sources.templates import list_templates, get_template, render_template
from driftgraph.sources.web_scraper import clean_html_to_markdown


# ============================================================================
# 1. Document Classifier Tests
# ============================================================================

def test_document_classifier_categories():
    classifier = DocumentClassifier()
    legal_text = (
        "This agreement and contract specifies the indemnification, liability, and governing law. "
        "The breach of clause 4 shall lead to termination and arbitration under the jurisdiction of the court."
    )
    res = classifier.classify(legal_text, filename="contract.pdf")
    assert res.top_category == "Legal"
    assert res.categories[0].category == "Legal"
    assert res.categories[0].percentage > 30.0

    tech_text = (
        "The microservice architecture uses FastAPI, SQLite database, FAISS vector embeddings, "
        "and a NetworkX graph pipeline to optimize query latency and backend runtime."
    )
    res_tech = classifier.classify(tech_text, filename="architecture.md")
    assert res_tech.top_category == "Technical"


def test_document_classifier_word_char_counts():
    classifier = DocumentClassifier()
    text = "Hello world! This is a test document."
    res = classifier.classify(text, filename="test.txt")
    assert res.word_count == 7
    assert res.char_count == len(text)


def test_document_classifier_ascii_box():
    classifier = DocumentClassifier()
    sample_text = (
        "This contract outlines the legal agreement, liabilities, and intellectual property terms for both parties."
    )
    res = classifier.classify(sample_text, filename="document.pdf")
    ascii_output = res.ascii_box
    
    # Must contain the exact decorative frame characters from Feature Ideas.md
    assert "╔══════════════════════════════════════════════════════╗" in ascii_output
    assert "║       📄 Text Extraction & Classification Tool       ║" in ascii_output
    assert "║              Rule-Based · Fully Offline               ║" in ascii_output
    assert "╚══════════════════════════════════════════════════════╝" in ascii_output
    assert "📄 document.pdf" in ascii_output
    assert "▶" in ascii_output
    assert "%" in ascii_output


def test_document_classifier_sentiment_and_priority():
    classifier = DocumentClassifier()
    urgent_negative = (
        "CRITICAL ALERT: Severe failure in server pipeline! Immediate action required. "
        "Fatal defect causing major error and risk of total shutdown."
    )
    res = classifier.classify(urgent_negative)
    assert res.priority in ("urgent", "high")
    assert res.sentiment == "negative"

    calm_positive = (
        "We achieved great success today. The team improved efficiency and celebrated outstanding progress."
    )
    res_pos = classifier.classify(calm_positive)
    assert res_pos.sentiment == "positive"
    assert res_pos.priority in ("low", "medium")


def test_document_classifier_auto_tags_and_entities():
    classifier = DocumentClassifier()
    text = (
        "DriftGraph is a high-performance Knowledge Graph system with FAISS vectors, "
        "FastAPI endpoints, and NetworkX topological analysis."
    )
    res = classifier.classify(text)
    assert len(res.auto_tags) > 0
    assert any("technical" in tag or "prio" in tag or "sentiment" in tag for tag in res.auto_tags)

    # Check contextual entities
    assert len(res.contextual_entities) > 0
    first_ent = res.contextual_entities[0]
    assert first_ent.origin_url.startswith("https://")
    assert first_ent.search_url.startswith("https://duckduckgo.com/")


# ============================================================================
# 2. Graph Analytics & Intelligence Tests
# ============================================================================

@pytest.fixture
async def sample_graph_storage(tmp_path):
    db_file = tmp_path / "analytics_test.db"
    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    # Create nodes
    nodes = [
        Node(id="node_python", name="Python", type="TECHNOLOGY", description="Programming language", degree=4, community_id=1),
        Node(id="node_fastapi", name="FastAPI", type="FRAMEWORK", description="Modern web framework", degree=3, community_id=1),
        Node(id="node_faiss", name="FAISS", type="LIBRARY", description="Vector similarity search", degree=2, community_id=2),
        Node(id="node_networkx", name="NetworkX", type="LIBRARY", description="Complex network graph library", degree=2, community_id=2),
        Node(id="node_rag", name="GraphRAG", type="CONCEPT", description="Graph-augmented retrieval", degree=3, community_id=2),
    ]

    # Create edges
    edges = [
        Edge(id="e1", source="node_python", target="node_fastapi", predicate="POWERS", weight=1.0),
        Edge(id="e2", source="node_fastapi", target="node_rag", predicate="EXPOSES_API_FOR", weight=1.0),
        Edge(id="e3", source="node_python", target="node_faiss", predicate="BINDS_TO", weight=1.0),
        Edge(id="e4", source="node_python", target="node_networkx", predicate="EXECUTES", weight=1.0),
        Edge(id="e5", source="node_networkx", target="node_rag", predicate="ENABLES_GRAPH_IN", weight=1.0),
    ]

    # Communities
    communities = [
        Community(id=1, level=0, name="Web & Core Tech", node_ids=["node_python", "node_fastapi"], summary="Core web stack"),
        Community(id=2, level=0, name="Graph & Vector AI", node_ids=["node_faiss", "node_networkx", "node_rag"], summary="Graph AI stack"),
    ]

    await storage.save_graph(nodes, edges, communities)
    return storage


@pytest.mark.asyncio
async def test_graph_analytics_report(sample_graph_storage):
    engine = GraphAnalyticsEngine(sample_graph_storage)
    report = await engine.generate_report()

    assert report.node_count == 5
    assert report.edge_count == 5
    # Python and FastAPI are top central hubs
    top_god = report.god_nodes[0]
    assert top_god.name in ("Python", "FastAPI")
    assert top_god.hub_score > 0

    # Surprising connections (bridging community 1 and 2)
    assert len(report.surprising_connections) > 0
    first_bridge = report.surprising_connections[0]
    assert first_bridge.source_community_id != first_bridge.target_community_id

    # Suggested questions
    assert len(report.suggested_questions) > 0


@pytest.mark.asyncio
async def test_graph_analytics_shortest_path(sample_graph_storage):
    engine = GraphAnalyticsEngine(sample_graph_storage)
    
    # Path from FastAPI to FAISS
    path_res = await engine.find_shortest_path("FastAPI", "FAISS")
    assert path_res.path_found is True
    assert path_res.hops > 0
    assert "FastAPI" in path_res.node_sequence
    assert "FAISS" in path_res.node_sequence
    assert len(path_res.steps) > 0
    assert "FastAPI" in path_res.narrative

    # Unresolvable node
    path_missing = await engine.find_shortest_path("NonExistentA", "NonExistentB")
    assert path_missing.path_found is False
    assert "Could not resolve" in path_missing.narrative


@pytest.mark.asyncio
async def test_graph_analytics_subgraph(sample_graph_storage):
    engine = GraphAnalyticsEngine(sample_graph_storage)
    sub = await engine.extract_subgraph(entity_name="Python", depth=1)
    
    assert len(sub.nodes) >= 3
    node_names = [n["name"] for n in sub.nodes]
    assert "Python" in node_names


# ============================================================================
# 3. Voice Assistant & Memory Tests
# ============================================================================

def test_audio_transcriber_info_and_fallback():
    transcriber = AudioTranscriber()
    fake_audio = b"\x00" * 32000  # Approx 1 second
    duration, sr, ch = transcriber.get_audio_info(fake_audio)
    assert duration > 0.4
    assert sr == 16000
    assert ch == 1


@pytest.mark.asyncio
async def test_audio_transcriber_marker_decoding():
    transcriber = AudioTranscriber()
    simulated_speech = b"SomeHeaderDG_VOICE_TEXT:What is the role of FAISS in DriftGraph?\x00TrailingData"
    text = await transcriber.transcribe(simulated_speech)
    assert text == "What is the role of FAISS in DriftGraph?"


def test_conversation_memory_manager():
    memory = ConversationMemoryManager(max_history_turns=6)
    session = "test_sess_1"

    memory.add_user_message(session, "Hello")
    memory.add_assistant_message(session, "Hi there!")
    memory.add_user_message(session, "What is DriftGraph?")
    memory.add_assistant_message(session, "DriftGraph is a GraphRAG system.")

    history_prompt = memory.format_history_prompt(session)
    assert "User: Hello" in history_prompt
    assert "Assistant: DriftGraph is a GraphRAG system." in history_prompt

    memory.clear_session(session)
    assert memory.get_session(session).turns == []


@pytest.mark.asyncio
async def test_voice_assistant_quick_answer(sample_graph_storage):
    class MockQueryEngine:
        def __init__(self, storage):
            self.storage = storage

    assistant = VoiceAssistant(query_engine=MockQueryEngine(sample_graph_storage))
    req = VoiceRequest(query="Python", quick_answer=True)
    resp = await assistant.process_voice_query(req)

    assert resp.mode_used == "quick"
    assert "Quick Answer:" in resp.text_answer
    assert "Python" in resp.text_answer
    assert len(resp.sources) > 0


@pytest.mark.asyncio
async def test_voice_assistant_record_to_note(tmp_path, monkeypatch):
    notes_dir = tmp_path / "voice_notes"
    notes_dir.mkdir()
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    class MockQueryEngine:
        pass

    assistant = VoiceAssistant(query_engine=MockQueryEngine())
    audio_data = b"AudioHeaderDG_VOICE_TEXT:Discussing the quarterly budget, expenditures, and fiscal profit.\x00"
    res = await assistant.record_voice_to_note(audio_data, title="Quarterly Financial Sync")

    assert res.id.startswith("quarterly_financial_sync")
    assert res.source_type == "voice"
    assert res.top_category == "Financial"

    # Verify file was written
    note_files = list(notes_dir.glob("*.md"))
    assert len(note_files) == 1
    content = note_files[0].read_text(encoding="utf-8")
    assert "Quarterly Financial Sync" in content
    assert "source_type: voice" in content


# ============================================================================
# 4. Note Templates & Web Scraper Tests
# ============================================================================

def test_note_templates():
    tpls = list_templates()
    assert len(tpls) >= 5
    ids = {t.id for t in tpls}
    assert "meeting" in ids
    assert "research" in ids
    assert "concept" in ids
    assert "daily_log" in ids
    assert "literature" in ids

    rendered = render_template("meeting", {"title": "Sprint Planning", "date": "2026-09-18", "attendees": "Alice, Bob"})
    assert "# Meeting: Sprint Planning" in rendered
    assert "Alice, Bob" in rendered
    assert "## Action Items" in rendered


def test_clean_html_to_markdown():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Article &amp; Insights</title></head>
    <body>
        <nav><a href="/">Home</a></nav>
        <header>Header content</header>
        <h1>Main Article Title</h1>
        <p>This is the <strong>first</strong> paragraph introducing the subject.</p>
        <p>Here is an <em>emphasized</em> insight with a <a href="https://example.com">link</a>.</p>
        <ul>
            <li>First key takeaway</li>
            <li>Second key takeaway</li>
        </ul>
        <footer>Footer advertisement &copy; 2026</footer>
        <script>console.log("bad");</script>
    </body>
    </html>
    """
    title, markdown = clean_html_to_markdown(html)
    assert title == "Test Article   Insights"
    assert "# Main Article Title" in markdown
    assert "**first**" in markdown
    assert "*emphasized*" in markdown
    assert "- First key takeaway" in markdown
    assert "console.log" not in markdown
    assert "Footer advertisement" not in markdown


# ============================================================================
# 5. FastAPI Endpoints Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_classify_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/classify",
            json={"text": "The patient was prescribed pharmaceutical therapy to treat the clinical symptoms of the disease."}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["top_category"] == "Medical Health"
        assert "╔════" in data["ascii_box"]
        assert len(data["categories"]) > 0


@pytest.mark.asyncio
async def test_note_templates_api(tmp_path, monkeypatch):
    notes_dir = tmp_path / "notes_api"
    notes_dir.mkdir()
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List templates
        resp = await ac.get("/api/notes/templates")
        assert resp.status_code == 200
        templates = resp.json()
        assert len(templates) >= 5

        # 2. Instantiate template
        inst_resp = await ac.post(
            "/api/notes/templates/concept/instantiate",
            json={"title": "Graph Partitioning", "values": {"concept_name": "Graph Partitioning", "domain": "Graph Theory"}}
        )
        assert inst_resp.status_code == 200
        inst_data = inst_resp.json()
        assert inst_data["filename"].endswith(".md")
        assert len(list(notes_dir.glob("*.md"))) == 1


@pytest.mark.asyncio
async def test_notes_crud_api(tmp_path, monkeypatch):
    notes_dir = tmp_path / "crud_notes"
    notes_dir.mkdir()
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    # Create a test note file
    note_file = notes_dir / "knowledge_graph.md"
    note_file.write_text(
        "---\n"
        "title: Knowledge Graph Guide\n"
        "date: 2026-09-18\n"
        "source_type: markdown\n"
        "tags: ['graph', 'ai']\n"
        "---\n\n"
        "# Knowledge Graph Guide\n\n"
        "A knowledge graph organizes entities and relations into a structured network.\n",
        encoding="utf-8"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List notes
        resp = await ac.get("/api/notes")
        assert resp.status_code == 200
        summaries = resp.json()
        assert len(summaries) == 1
        note_id = summaries[0]["id"]

        # 2. Get note detail
        detail_resp = await ac.get(f"/api/notes/{note_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["title"] == "Knowledge Graph Guide"
        assert "Knowledge Graph Guide" in detail["content"]

        # 3. Update note
        updated_content = detail["content"] + "\nAdding a new section on graph embeddings."
        put_resp = await ac.put(f"/api/notes/{note_id}", json={"content": updated_content})
        assert put_resp.status_code == 200

        # Verify update on disk
        refreshed_text = note_file.read_text(encoding="utf-8")
        assert "Adding a new section on graph embeddings." in refreshed_text

        # 4. Delete note (permanent purge)
        del_resp = await ac.delete(f"/api/notes/{note_id}?permanent=true")
        assert del_resp.status_code == 200
        assert not note_file.exists()


@pytest.mark.asyncio
async def test_export_formats_api(tmp_path, monkeypatch):
    # Setup test DB with nodes and edges
    db_file = tmp_path / "export_test.db"
    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()
    
    nodes = [Node(id="n1", name="Python", type="TECHNOLOGY", degree=1, description="Language")]
    edges = [Edge(id="e1", source="n1", target="n1", predicate="SELF", weight=1.0)]
    await storage.save_graph(nodes, edges, [])
    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # CSV export
        resp_csv = await ac.get("/api/export?format=csv")
        assert resp_csv.status_code == 200
        assert "record_type,id,source_or_name" in resp_csv.text
        assert "node,n1,Python" in resp_csv.text

        # Markdown digest export
        resp_md = await ac.get("/api/export?format=markdown")
        assert resp_md.status_code == 200
        assert "# DriftGraph Knowledge Graph Digest" in resp_md.text
        assert "Python" in resp_md.text

        # Embeddings export
        resp_emb = await ac.get("/api/export/embeddings")
        assert resp_emb.status_code == 200
        emb_data = resp_emb.json()
        assert "index_type" in emb_data

        # Notes export
        resp_notes = await ac.get("/api/export/notes?format=json")
        assert resp_notes.status_code == 200
        notes_list = resp_notes.json()
        assert isinstance(notes_list, list)
        assert len(notes_list) > 0
        assert "filename" in notes_list[0]


@pytest.mark.asyncio
async def test_graph_analytics_api(tmp_path, monkeypatch):
    db_file = tmp_path / "analytics_api.db"
    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    nodes = [
        Node(id="n_a", name="AlgA", type="ALGO", degree=1),
        Node(id="n_b", name="AlgB", type="ALGO", degree=1),
    ]
    edges = [Edge(id="e_ab", source="n_a", target="n_b", predicate="DERIVES_FROM", weight=1.0)]
    await storage.save_graph(nodes, edges, [])
    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Analytics report
        rep_resp = await ac.get("/api/graph/analytics")
        assert rep_resp.status_code == 200
        rep_data = rep_resp.json()
        assert rep_data["node_count"] == 2
        assert rep_data["edge_count"] == 1

        # Path endpoint
        path_resp = await ac.post("/api/graph/analytics/path", json={"source": "AlgA", "target": "AlgB"})
        assert path_resp.status_code == 200
        path_data = path_resp.json()
        assert path_data["path_found"] is True

        # Questions endpoint
        q_resp = await ac.get("/api/graph/analytics/questions")
        assert q_resp.status_code == 200
        assert isinstance(q_resp.json(), list)


@pytest.mark.asyncio
async def test_voice_memory_clear_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/voice/memory/clear", data={"session_id": "test_session_clear"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
