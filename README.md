# DriftGraph

**Reconstruct any knowledge graph using only the embeddings of your notes** — streamed into your browser as a live, explorable web of ideas.

DriftGraph is a local-first research platform and desktop application that turns a folder of plain Markdown notes, digital documents, scanned papers, and web articles into a fully connected **interactive Knowledge Graph**. It embeds every sentence into a dense vector space with lightweight Sentence-BERT models, extracts latent entities and typed relationships via an on-device Large Language Model (or hosted API), and structures your knowledge into hierarchical communities using the Leiden algorithm. The result is streamed into an Obsidian-style galaxy visualization in your browser: every note *drifts* organically into the graph.

**Notes in, Drift out.** No sign-up, no cloud dependency, no telemetry, and zero recurring API costs.

---

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Sentence-BERT](https://img.shields.io/badge/Embeddings-all--MiniLM--L6--v2-orange.svg)](https://www.sbert.net)
[![FAISS](https://img.shields.io/badge/Vector_Store-FAISS-green.svg)](https://github.com/facebookresearch/faiss)
[![SQLite FTS5](https://img.shields.io/badge/Database-SQLite_FTS5-blue.svg)](https://sqlite.org/fts5.html)
[![Ollama & API](https://img.shields.io/badge/LLM-Ollama_%7C_OpenAI--Compatible-purple.svg)](https://ollama.com)
[![Test Suite](https://img.shields.io/badge/Tests-117_Passing-brightgreen.svg)](https://docs.pytest.org)

---

## ✨ Features

- **🔒 Local-First & 100% Private** — No accounts, no cloud dependencies; your notes, embeddings, and graph stay entirely on your local machine in SQLite and FAISS.
- **🌌 Obsidian-Style Galaxy Canvas & Dual-Level Cytoscape** — Custom layered HTML5 Canvas 2D engine (`ObsidianGalaxyEngine`) with Barnes-Hut Quadtree hit-testing running at a silky 60 FPS:
  - Concentric core hubs clustered via force-directed spring physics.
  - Peripheral singletons and leaf nodes distributed in sunflower orbital shells using Fermat's golden spiral ($\theta = n \times 137.508^\circ$).
  - Scoped cursor physics: full-screen ambient radial repulsion on the Hero Landing screen; strictly disabled on the Explorer canvas for zero cursor-scatter and instant hover hit-testing.
  - Dual-level abstraction: Toggle seamlessly between Level 0 (Leiden Communities) and Level 1 (Entities & Concepts).
- **🎨 Categorical Semantic Color Coding** — Multi-hue palette mapped deterministically to detected Leiden communities
- **⚡ Starburst Hover & Proximity Labeling** — Hovering over any node instantly illuminates its 1-hop incoming and outgoing connections into colored vector lines, spotlights neighboring nodes, and renders a clean monospaced proximity pill (`JetBrains Mono`) with zero resting clutter.
- **🧠 Automated Knowledge Graph Assembly** — Entities, concepts, and multi-relational edges are extracted automatically from raw prose via local Ollama (`llama3.1:8b-instruct`) or hosted OpenAI-compatible APIs without manual tagging.
- **🔗 Latent Semantic Auto-Linking** — Notes link to each other dynamically whenever cosine similarity across Sentence-BERT embeddings exceeds a configurable threshold ($\ge 0.70$), eliminating manual `[[wiki-links]]`.
- **🔍 GraphRAG Dual-Engine Q&A** — Intelligent dual-mode synthesis:
  - **Global Search**: Answers macro-level corpus synthesis questions (*"What are the overarching research themes?"*) by aggregating hierarchical community summaries via Map-Reduce.
  - **Local Search**: Traverses entity neighborhoods, dense FAISS vector similarity, and SQLite FTS5 lexical indexing for precise point-factual retrieval (*"What mechanisms are used in Project Alpha?"*).
- **📄 Multi-Engine Document OCR Pipeline** — Ingest scanned PDFs, images, and whiteboards via multi-engine fallback (Tesseract, EasyOCR, DocTR, Apple Vision) with column-aware heuristic layout analysis and table extraction.
- **🎙️ End-to-End Voice Assistant (Voice RAG)** — Speak questions directly using the browser Speech Recognition API (`POST /api/voice/ask`), retrieve grounded graph context, stream synthesized audio via ElevenLabs TTS (`/api/voice/audio/{id}`) or browser `speechSynthesis`, and watch cited entity nodes light up with glowing attention halos on the canvas.
- **🏷️ Text Taxonomy Classification Studio** — 100% offline rule-based classification studio (`POST /api/classify`) with confidence meters and ASCII hierarchical decision tree outputs.
- **📊 Graph Intelligence & Centrality Analytics** — Identify "God Nodes" (high betweenness and degree centrality), locate cross-community semantic bridges, trace 2-hop navigation paths between any two ideas, and auto-generate synthesis boundary questions.
- **💾 Multi-Format Export & Serialization** — Export graphs to JSON, high-resolution PNG, SVG, interactive HTML bundles, or semantic web standards (RDF/Turtle `.ttl` and JSON-LD `.jsonld`).
- **🚀 Hosted API "Demo Mode"** — Dual-provider configuration allowing public hosting or deployment on lightweight non-GPU machines via OpenAI-compatible endpoints (`LLM_API_KEY`) while keeping local-first Ollama as default.
- **🔬 Benchmarked & Evaluated** — Includes SBERT vs. Word2Vec embedding ablation studies, RAGAS/TruLens retrieval metrics, and `psutil` memory and latency profiling across all pipeline stages.

---

## 🎬 How It Works (System Architecture & Pipeline)

```
 Raw Markdown Notes / Scanned OCR Documents
                    │
                    ▼
 ┌──────────────────────────────────────┐
 │ 1. Ingestion & Layout Parsing        │  strip frontmatter, clean prose,
 │    (mistune, PyMuPDF, OCR engines)   │  column-aware reading order analysis
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │ 2. Sentence & Semantic Chunking      │  sliding window chunker with
 │    (driftgraph.ingest.chunker)       │  contextual provenance tracking
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │ 3. Dense Vector Embedding            │  Sentence-BERT (all-MiniLM-L6-v2)
 │    (sentence-transformers)           │  384-d vectors, CPU-optimized
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │ 4. Entity & Relation Extraction      │  local on-device LLM via Ollama
 │    (driftgraph.extract)              │  or hosted OpenAI-compatible API
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │ 5. Graph Assembly & Deduplication    │  NetworkX multi-graph, entity canonicalization,
 │    (driftgraph.graph.builder)        │  cosine similarity edge thresholding
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │ 6. Hierarchical Leiden Partitioning  │  multi-level community clustering
 │    (leidenalg / python-louvain)      │  (Level 0 communities, Level 1 entities)
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │ 7. Community Summaries (Map-Reduce)  │  hierarchical LLM summarization
 │    (driftgraph.summarize)            │  generating global sensemaking reports
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │ 8. Persistence (SQLite + FAISS)      │  SQLite relational tables + FTS5 search
 │    (driftgraph.graph.storage)        │  FAISS IndexFlatIP dense vector store
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │ 9. Dual-Engine Retrieval & Voice     │  Global Map-Reduce + Local Hybrid Search;
 │    (driftgraph.query & voice)        │  ElevenLabs TTS audio streaming
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │ 10. Galaxy Engine Visualization      │  60 FPS Dual-Canvas 2D Engine, Quadtree,
 │     (frontend/assets/js)             │  scoped physics & Obsidian galaxy topology
 └──────────────────────────────────────┘
```

---

## 🧱 Tech Stack

| Layer | Technology | Primary Purpose |
| :--- | :--- | :--- |
| **Frontend Framework** | Vanilla HTML5 / Modern CSS / JavaScript (ES2022) | Single-file reactive workbench; zero heavy frontend bundle dependencies |
| **Primary Graph Canvas** | Layered HTML5 Canvas 2D (`ObsidianGalaxyEngine`) | 60 FPS dual-canvas rendering (background topology + interactive starburst layer) |
| **Spatial Indexing** | 2D Barnes-Hut Quadtree | Instantaneous $O(\log n)$ hover detection, collision testing, and proximity labeling |
| **Physics Simulation** | Dedicated Web Worker (`physics.worker.js`) | Off-main-thread Hooke's law springs, Coulomb repulsion, and elastic collisions ($e \approx 0.5$) |
| **Fallback Graph Canvas** | Cytoscape.js (`cytoscape.js`) | Hierarchical compound graph rendering, Level 0 community clustering |
| **Backend Framework** | Python 3.11+, FastAPI, Uvicorn | High-performance asynchronous REST API with `--reload-exclude` for database stability |
| **Relational Database** | SQLite3 (`aiosqlite`) with FTS5 virtual tables | Persistent graph nodes, edges, community summaries, and instant lexical full-text search |
| **Vector Index** | FAISS (`faiss-cpu`, `IndexFlatIP`) | Fast dense vector similarity search across 384-dimensional embeddings |
| **NLP Embeddings** | `sentence-transformers` (`all-MiniLM-L6-v2`) | Lightweight CPU-optimized 384-d dense vector embeddings |
| **Baseline Embeddings** | Gensim (`Word2Vec`), TF-IDF | Embedding ablation benchmarks and comparative evaluation |
| **Local LLM Engine** | [Ollama](https://ollama.com) (`llama3.1:8b-instruct-q4_K_M`, `mistral`) | 100% private, on-device entity-relation extraction and community summarization |
| **Hosted LLM Engine** | OpenAI-Compatible API (`driftgraph.extract.api_client`) | Demo mode support for Groq, Together, OpenAI, or LiteLLM endpoints |
| **Graph Algorithms** | NetworkX, `leidenalg`, `python-louvain` | Knowledge graph topology, degree/betweenness centrality, and Leiden modularity |
| **Document OCR** | PyMuPDF (`fitz`), Pillow, Tesseract / EasyOCR / DocTR | Multi-engine PDF/image ingestion with heuristic spatial column-layout analysis |
| **Voice & Speech** | ElevenLabs API, Web Speech API, `window.speechSynthesis` | Voice recording, grounded GraphRAG query dispatch, and real-time audio playback |
| **Testing & Evaluation** | Pytest, `pytest-asyncio`, `psutil`, RAGAS / TruLens | Unit, integration, and performance benchmarking (117 tests passing) |

---

## 🐳 Run It Yourself

DriftGraph is designed to run effortlessly on any local machine. You can use local Ollama (default) or a hosted API key (demo mode).

### Prerequisites

- **Python 3.11+**
- **uv** (recommended for ultra-fast setup) or standard `python -m venv` / `pip`
- **Ollama** (for local-first extraction) *or* an **OpenAI-compatible API key** (for demo mode)

---

### Setup & Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/tejasec/DriftGraph.git
cd drift-graph
```

#### 2. Create Virtual Environment & Install Dependencies

**Using `uv` (Recommended):**
```bash
uv sync
```

**Using standard `pip`:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# for Windows
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

---

### Configuration & LLM Selection

DriftGraph supports two operational modes configured in `config.yaml`:

#### Mode 1: Local-First with Ollama (Default)
Recommended for privacy and offline usage:
```bash
# Pull the recommended extraction model
ollama pull llama3.1:8b-instruct-q4_K_M
ollama serve
```

In `config.yaml`:
```yaml
llm:
  provider: ollama
  base_url: http://localhost:11434/v1
  model: llama3.1:8b-instruct-q4_K_M
```

#### Mode 2: Hosted API "Demo Mode" (No Local GPU Required)
Ideal for cloud deployment, lightweight laptops, or public demos:
```bash
# 1. Export your API key
export LLM_API_KEY="your-actual-api-key"
```

In `config.yaml`:
```yaml
llm:
  provider: openai_compatible
  base_url: https://api.groq.com/openai/v1  # or Together, OpenAI, etc.
  model: llama-3.1-8b-instant
  api_key_env: LLM_API_KEY
```

> **Security Note:** The API key *never* appears in `config.yaml`. DriftGraph reads only the environment variable name at runtime.

---

### Running DriftGraph

#### 1. Build the Knowledge Graph from Notes
Populate `./data/notes` with your markdown files, then run the pipeline:
```bash
uv run python -m driftgraph.main build --notes ./data/notes
```

#### 2. Launch the Web Server & UI
```bash
uv run python -m driftgraph.main serve --host 0.0.0.0 --port 8000 --reload
```
*Note: The `--reload` flag automatically excludes database and index files (`data/*`, `*.db*`, `*.index`) to prevent server restart loops during SQLite writes.*

#### 3. Open the Interactive Workbench
Open your browser and navigate to:
```
http://localhost:8000
```
- **Landing Hero View**: Explore the ambient particle force field, learn system capabilities from the *"What it does"* popover, or click **"Open Graph Explorer"** for a screen-wide slide transition into the active 2-pane workbench.
- **Graph Explorer**: Pan, zoom, click, and drag nodes in the Obsidian galaxy engine.
- **Note Editor**: Draft notes with real-time auto-saving, preview rendering, and dynamic latent semantic link discovery.
- **Voice Query**: Click `🎙 Voice query` in the toolbar to speak your questions and listen to grounded audio responses.
- **OCR Ingest**: Upload PDF documents or scanned images to parse tables and text directly into new knowledge nodes.
- **Classifier Studio**: Test offline taxonomy categorizations on any custom text snippet.

---

### Command Line Interface (CLI)

DriftGraph includes a rich CLI for automated scripting and terminal queries:

```bash
# Build knowledge graph
uv run python -m driftgraph.main build --notes ./data/notes

# Query the graph (Global Synthesis Mode)
uv run python -m driftgraph.main query "What are the core research themes?" --mode global

# Query the graph (Local Neighborhood Mode)
uv run python -m driftgraph.main query "Who is Alice Chen and what does she work on?" --mode local

# Start the web server
uv run python -m driftgraph.main serve --host 0.0.0.0 --port 8000

# Run the SBERT vs Word2Vec embedding ablation study
uv run python -m driftgraph.main ablation --notes ./data/notes
```

---

## 📁 Project Layout

```
driftgraph/
├── analytics/              # Graph intelligence: God nodes, bridges, 2-hop navigation paths
├── classifier/             # 100% offline rule-based text taxonomy classification studio
├── embed/                  # Sentence-BERT (all-MiniLM-L6-v2) & Word2Vec baseline encoders
├── eval/                   # RAGAS metrics, ablation studies, and psutil benchmark runner
├── extract/                # Ollama & OpenAI-compatible LLM extraction clients and prompts
├── graph/                  # KnowledgeGraphBuilder, SQLite storage (FTS5), FAISS index, Leiden clustering
├── ingest/                 # Markdown chunker, parser, and multi-engine document OCR pipeline
├── query/                  # GraphRAG query engine: Global Map-Reduce & Local Hybrid retrieval
├── serve/                  # FastAPI web server, routers (graph, voice, notes, OCR, analytics)
├── voice/                  # Speech recognition handlers, ElevenLabs TTS client, audio caching
├── config.py               # Central Pydantic application configuration
└── main.py                 # Primary CLI entrypoint (build, serve, query, ablation)
frontend/
├── assets/
│   ├── js/
│   │   ├── galaxy-engine.js       # High-performance 2D layered canvas engine with Quadtree hit-testing
│   │   ├── physics.worker.js      # Off-main-thread Web Worker force-directed physics simulation
│   │   └── physics-controller.js  # Context-aware scoped mouse physics (hero repulsion vs explorer hover)
│   └── css/                       # Modular design styles
└── index.html                     # Responsive 2-pane workbench, cytoscape styles, modals, and voice UI
data/
├── notes/                  # Markdown notes directory
├── driftgraph.db           # SQLite database with FTS5 lexical indexes
├── faiss.index             # FAISS dense vector index
└── exports/                # Graph exports (.json, .ttl, .jsonld)
tests/                      # Automated test suite (117 tests covering all subsystems)
config.yaml                 # System settings, thresholds, model identifiers, and OCR options
pyproject.toml              # Build specifications, package dependencies, and CLI script definitions
```

---

## 📚 Research Foundation

DriftGraph evaluates whether **lightweight, CPU-viable embedding models** (125M–220M parameters, 384 dimensions) can match or outperform heavy multi-billion-parameter cloud baselines on local knowledge graph generation, entity resolution, and Leiden community partitioning.

### Primary Foundational Literature

1. **Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks**  
   — Nils Reimers & Iryna Gurevych (2019)  
   - [arXiv:1908.10084](https://arxiv.org/abs/1908.10084) | [GitHub Repository](https://github.com/UKPLab/sentence-transformers)  
   *Contribution:* Demonstrates that Siamese and triplet network structures produce semantically meaningful 384-dimensional sentence embeddings that can be compared via cosine similarity with sub-millisecond latency on standard CPUs.

2. **From Local to Global: A Graph RAG Approach to Query-Focused Summarization**  
   — Darren Edge et al., Microsoft Research (2024)  
   - [arXiv:2404.16130](https://arxiv.org/abs/2404.16130) | [Microsoft Research Project](https://www.microsoft.com/en-us/research/project/graphrag/)  
   *Contribution:* Establishes the GraphRAG framework: hierarchical clustering via the Leiden algorithm followed by Map-Reduce summarization to answer global corpus-wide queries that fail in standard vector RAG.

3. **AutoKG: Efficient Automated Knowledge Graph Generation for Language Models**  
   — Bohan Chen, Andrea L. Bertozzi (2023)  
   - [arXiv:2311.14740](https://arxiv.org/abs/2311.14740) | [IEEE BigData 2023](https://doi.org/10.1109/BigData59044.2023.10386454)  
   *Contribution:* Validates that compact, prompt-guided language models can extract high-fidelity knowledge triples without massive parameter overhead.

4. **DistilBERT, a distilled version of BERT: Smaller, Faster, Cheaper and Lighter**  
   — Victor Sanh et al., Hugging Face (2019)  
   - [arXiv:1910.01108](https://arxiv.org/abs/1910.01108)  
   *Contribution:* Demonstrates knowledge distillation to compress transformer architectures by 40% while preserving 97% of language understanding performance on commodity hardware.

5. **Context Graph: Modeling Hyper-Relational Context for Multi-Hop Graph Reasoning**  
   — Chengjin Xu et al. (2024)  
   - [arXiv:2406.11160](https://arxiv.org/abs/2406.11160)  
   *Contribution:* Informs how hyper-relational nodes and edges capture situational and provenance context during multi-hop graph retrieval.

---

## 🔬 Evaluation & Benchmarks

DriftGraph is continuously benchmarked across four dimensions:

1. **Retrieval Quality (RAGAS Metrics)**:
   - **Context Precision**: Evaluates whether retrieved graph nodes and community reports directly align with the query topic.
   - **Faithfulness**: Measures whether synthesized answers are strictly grounded in graph citations without hallucination.
   - **Answer Relevance**: Quantifies how completely the generated answer satisfies the user's information need.
2. **Embedding Ablation Study**:
   - Compares Sentence-BERT (`all-MiniLM-L6-v2`) against Word2Vec baselines and TF-IDF representations.
   - Evaluates cosine similarity distributions, clustering quality, and semantic edge accuracy across semantic relatedness regions (STR).
   - Run directly via: `uv run python -m driftgraph.main ablation`.
3. **Hardware Efficiency & Profiling**:
   - Memory footprint monitored with `psutil`: runs comfortably within $\le 512\text{ MB}$ of RAM.
   - CPU-only execution: Sentence-BERT embeddings generate in $\le 15\text{ ms}$ per sentence on consumer Intel/AMD/Apple Silicon CPUs.
4. **Automated Verification**:
   - Comprehensive test suite covering graph assembly, scoped physics, OCR, voice RAG, auto-linking, zero-state creation, and REST endpoints:
   ```bash
   uv run pytest
   ============================= 117 passed in 18.92s =============================
   ```

---

## 🚀 Roadmap & Future Scope

- [x] Obsidian-style 2D galaxy canvas with Fermat sunflower spiral layout and Quadtree hit-testing.
- [x] Scoped cursor physics separating ambient hero repulsion from functional explorer hover detection.
- [x] Dual-level GraphRAG (Level 0 Communities & Level 1 Entities) with Map-Reduce global search.
- [x] Multi-engine document OCR pipeline (Tesseract, EasyOCR, DocTR) with layout analysis.
- [x] End-to-end Voice Assistant RAG with ElevenLabs TTS streaming and canvas highlighting.
- [x] Offline rule-based taxonomy classification studio with ASCII trees.
- [x] Hosted API "Demo Mode" supporting Groq, Together, and OpenAI endpoints.
- [ ] Multi-source vault synchronization (direct two-way sync with Obsidian vaults and Notion workspaces).
- [ ] Zotero academic library import with automated citation extraction.
- [ ] 3D WebGL / Three.js galaxy render mode for massive knowledge graphs (> 10,000 nodes).
- [ ] Cross-lingual embedding support for multilingual notes and queries.
- [ ] Mobile companion interface (PWA / Android Lexitalk stack).

---

## 📄 License

DriftGraph is licensed under the [MIT License](LICENSE).
---

*Notes in, Drift out.*
