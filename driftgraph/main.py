"""
Main CLI entrypoint for DriftGraph.
"""

import sys
import asyncio
import argparse
import uvicorn
from pathlib import Path

from driftgraph.config import config
from driftgraph.ingest import parse_markdown_directory, chunk_notes
from driftgraph.embed import SBERTEmbedder
from driftgraph.extract import get_extraction_client
from driftgraph.extract.models import ExtractionConfig
from driftgraph.graph import KnowledgeGraphBuilder, SQLiteStorage, VectorIndex, EntityDeduplicator, CommunityDetector
from driftgraph.graph.layout import compute_forceatlas2_layout, apply_layout_to_nodes
from driftgraph.summarize import CommunitySummarizer
from driftgraph.summarize.models import SummaryConfig
from driftgraph.query import QueryEngine, QueryRequest
from driftgraph.eval import BenchmarkRunner, AblationStudy


async def build_pipeline(notes_dir: str):
    """Run full Knowledge Graph generation pipeline."""
    config.validate_startup()
    print(f"\n🚀 [DriftGraph] Starting build pipeline on notes directory: {notes_dir}")
    runner = BenchmarkRunner()

    # 1. Ingest
    with runner.measure("Ingestion & Parsing"):
        notes = await parse_markdown_directory(notes_dir)
        chunks = chunk_notes(notes)
    ocr_notes = [n for n in notes if getattr(n.metadata, "source_type", None) == "ocr"]
    if ocr_notes:
        ocr_pages = sum(n.metadata.extra.get("page_count", 1) for n in ocr_notes)
        print(f"  ✓ Ingested {len(ocr_notes)} OCR documents ({ocr_pages} pages).")
    print(f"  ✓ Parsed {len(notes)} notes into {len(chunks)} semantic chunks.")

    if not chunks:
        print("  ⚠️ No chunks found to index. Exiting.")
        return

    # 2. Embedding
    with runner.measure("Sentence-BERT Embedding", items_count=len(chunks)):
        embedder = SBERTEmbedder()
        chunk_texts = [c.text for c in chunks]
        vectors = embedder.embed_texts(chunk_texts)

        vec_index = VectorIndex(dimension=embedder.dimension, index_path=config.database.vector_index_path)
        chunk_ids = [c.id for c in chunks]
        vec_index.add(chunk_ids, vectors)
        vec_index.save()
    print(f"  ✓ Generated {len(vectors)} embeddings ({embedder.dimension}-d) & saved FAISS index.")

    # 3. Extraction
    with runner.measure("Entity & Relation Extraction"):
        extractor = get_extraction_client()
        extractions = await extractor.extract_batch(chunks)
        await extractor.close()
    print(f"  ✓ Extracted entities and relationships from {len(extractions)} chunks.")

    # 4. Graph Assembly & Community Detection
    with runner.measure("Graph Assembly & Leiden Partitioning"):
        builder = KnowledgeGraphBuilder(
            embedder=embedder,
            deduplicator=EntityDeduplicator(similarity_threshold=config.graph.similarity_threshold),
            community_detector=CommunityDetector(
                resolution=config.graph.community_resolution,
                min_community_size=config.graph.min_community_size,
                max_levels=config.graph.max_levels
            )
        )
        nodes, edges, communities = builder.build_from_extractions(extractions)
        layout_coords = compute_forceatlas2_layout((nodes, edges))
        apply_layout_to_nodes(nodes, layout_coords)
    print(f"  ✓ Built Knowledge Graph & Layout: {len(nodes)} nodes, {len(edges)} edges, {len(communities)} communities.")

    # 5. Summarization (Map-Reduce)
    with runner.measure("Hierarchical Map-Reduce Summaries"):
        summarizer = CommunitySummarizer(SummaryConfig(
            provider=config.llm.provider,
            model=config.llm.model,
            base_url=config.llm.base_url,
            api_key=config.llm.get_api_key(),
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            timeout=config.llm.timeout
        ))
        summary_result = await summarizer.summarize_all(communities, nodes, edges)
        await summarizer.close()
    print(f"  ✓ Generated summaries across {len(summary_result.community_summaries)} communities.")

    # 6. SQLite Persistence
    with runner.measure("SQLite Persistence & FTS5 Indexing"):
        storage = SQLiteStorage(db_path=config.database.sqlite_path)
        await storage.initialize_schema()
        await storage.save_notes_and_chunks(notes, chunks)
        await storage.save_graph(nodes, edges, communities)
        if summary_result.global_summary:
            await storage.save_meta("global_summary", summary_result.global_summary)
        if summary_result.key_themes:
            await storage.save_meta("key_themes", summary_result.key_themes)
    print(f"  ✓ Persisted nodes, edges, and summaries to SQLite: {config.database.sqlite_path}")

    report = runner.generate_report()
    print(f"\n✨ [DriftGraph] Build finished in {report.total_latency_ms:.2f} ms | Peak RSS: {report.max_rss_mb:.2f} MB\n")


async def run_query(query_text: str, mode: str = "auto"):
    """Run CLI query against the graph."""
    config.validate_startup()
    print(f"\n🔍 [DriftGraph] Querying: '{query_text}' (Mode: {mode})")
    embedder = SBERTEmbedder()
    vec_index = VectorIndex(dimension=embedder.dimension, index_path=config.database.vector_index_path)
    vec_index.load()
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    await storage.initialize_schema()

    engine = QueryEngine(
        embedder=embedder,
        vector_index=vec_index,
        storage=storage,
        llm_model=config.llm.model,
        llm_base_url=config.llm.base_url,
        top_k=config.retrieval.top_k,
        hybrid_alpha=config.retrieval.hybrid_alpha,
        llm_temperature=config.llm.temperature,
        llm_provider=config.llm.provider,
        llm_api_key=config.llm.get_api_key()
    )

    req = QueryRequest(query=query_text, mode=mode)
    res = await engine.query(req)

    print(f"\n💡 [Answer] (Mode: {res.mode_used} | Latency: {res.latency_ms} ms)")
    print(f"{res.answer}\n")
    if res.citations:
        print("📌 Citations:")
        for c in res.citations:
            print(f"  - [{c.source_type.upper()}] {c.title or c.id}: {c.text_snippet[:100]}...")
    print()


def run_server(host: str, port: int, reload: bool = False):
    """Start FastAPI server with Uvicorn."""
    config.validate_startup()
    print(f"\n🌐 [DriftGraph] Serving on http://{host}:{port}")
    if reload:
        uvicorn.run(
            "driftgraph.serve.app:app",
            host=host,
            port=port,
            reload=True,
            reload_excludes=["data/*", "*.db*", "*.db-journal", "*.db-wal", "*.db-shm", "*.index", "*.npy", "data/**"]
        )
    else:
        uvicorn.run("driftgraph.serve.app:app", host=host, port=port, reload=False)


def run_ablation(notes_dir: str):
    """Run embedding ablation study."""
    async def _inner():
        notes = await parse_markdown_directory(notes_dir)
        chunks = chunk_notes(notes)
        study = AblationStudy()
        res = study.run_comparison(chunks)
        print("\n📊 Ablation Study Results:")
        import json
        print(json.dumps(res, indent=2))
    asyncio.run(_inner())


def cli_entrypoint():
    parser = argparse.ArgumentParser(prog="driftgraph", description="DriftGraph Local GraphRAG CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Build
    build_p = subparsers.add_parser("build", help="Build knowledge graph from notes")
    build_p.add_argument("--notes", default=config.paths.notes_dir, help="Path to markdown notes directory")

    # Serve
    serve_p = subparsers.add_parser("serve", help="Start FastAPI web server and UI")
    serve_p.add_argument("--host", default=config.server.host, help="Host address")
    serve_p.add_argument("--port", type=int, default=config.server.port, help="Port")
    serve_p.add_argument("--reload", action="store_true", help="Enable auto-reload with data path exclusion")

    # Query
    query_p = subparsers.add_parser("query", help="Query the knowledge graph")
    query_p.add_argument("query", help="Question or query string")
    query_p.add_argument("--mode", default="auto", choices=["auto", "global", "local"], help="Query mode")

    # Ablation
    ablation_p = subparsers.add_parser("ablation", help="Run embedding ablation benchmark")
    ablation_p.add_argument("--notes", default=config.paths.notes_dir, help="Notes directory")

    args = parser.parse_args()

    if args.command == "build":
        asyncio.run(build_pipeline(args.notes))
    elif args.command == "serve":
        run_server(args.host, args.port, reload=args.reload)
    elif args.command == "query":
        asyncio.run(run_query(args.query, mode=args.mode))
    elif args.command == "ablation":
        run_ablation(args.notes)
    else:
        parser.print_help()


if __name__ == "__main__":
    cli_entrypoint()
