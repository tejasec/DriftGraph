# DriftGraph — Model Selection, Infrastructure & Backend Requirements

Based on your project architecture, research documentation, and codebase for DriftGraph, here is a comprehensive breakdown of your AI model selection, infrastructure needs, and data/backend requirements.

---

## 1. AI Model Selection: GPT vs. BERT for DriftGraph

In DriftGraph, the goal is to reconstruct a knowledge graph from notes, link concepts semantically, and perform GraphRAG sensemaking.

Rather than choosing strictly between GPT or BERT, your project actually requires a **dual (hybrid) model approach**, using each architecture for what it is mathematically designed to do best.

```
                 ┌─────────────────────────────────────────────────────────┐
                 │                 RAW MARKDOWN NOTES                      │
                 └────────────────────────────┬────────────────────────────┘
                                              │
                                              ▼
        ┌─────────────────────────────────────────────────────────────────────────┐
        │       BERT / SBERT (Encoder-Only: all-MiniLM-L6-v2 / BGE-Small)         │
        │  • Dense Sentence Embeddings (384-d)                                    │
        │  • Pairwise Cosine Similarity (Auto-linking notes)                     │
        │  • Fast CPU Vector Retrieval & Semantic Drift Benchmarks                │
        └─────────────────────────────┬───────────────────────────────────────────┘
                                      │
                                      ▼
        ┌─────────────────────────────────────────────────────────────────────────┐
        │         GRAPH TOPOLOGY & CLUSTERING (NetworkX + Leiden)                 │
        │  • Graph assembly, typed edges, community partitioning                  │
        └─────────────────────────────┬───────────────────────────────────────────┘
                                      │
                                      ▼
        ┌─────────────────────────────────────────────────────────────────────────┐
        │        GPT / Autoregressive LLM (Decoder-Only: Llama-3 / Phi-3 / Qwen)   │
        │  • Complex Relation & Triplet Extraction (Subject-Predicate-Object)     │
        │  • Hierarchical Community Summarization (Map-Reduce)                    │
        │  • Natural Language Query Synthesis & Voice RAG Answers                 │
        └─────────────────────────────────────────────────────────────────────────┘
```

---

### Key Differences: GPT vs. BERT

|Feature / Dimension|BERT (Encoder-Only)|GPT / Generative LLMs (Decoder-Only)|
|---|---|---|
|Attention Mechanism|Bidirectional: Attends to tokens before and after simultaneously.|Causal / Unidirectional: Attends only to previous (left) tokens.|
|Training Objective|Masked Language Modeling (MLM): Fills in masked words ([MASK]).|Autoregressive (Next-token prediction): Predicts the next word in sequence.|
|Primary Strength|Rich semantic contextual representations, embeddings, token classification.|Text generation, multi-hop reasoning, open-ended question answering, synthesis.|
|Text Generation|❌ Cannot generate fluent paragraphs or summaries.|✅ Native capability for fluent, grounded prose.|
|Sentence Embeddings|⭐ Superior & Efficient (via Siamese SBERT networks).|⚠ Suboptimal out-of-the-box; requires specialized pooling and high compute.|
|Computational Footprint|Very Low (22M–110M params, 80–400 MB RAM, fast on CPU).|Moderate to High (3B–8B params, 2–6 GB RAM for quantized models).|

---

### Which Model to Choose for Each DriftGraph Stage?

#### 1. Note Embedding & Semantic Linking: Use BERT (Sentence-Transformers)

- **Why:** You need to compute 384-dimensional dense vectors for every sentence/note to calculate cosine similarity thresholds (e.g., auto-linking notes when similarity > 0.18).
- **Recommended Models:**
    - `sentence-transformers/all-MiniLM-L6-v2` (22M params, 384-d, ultra-lightweight, CPU friendly).
    - `BAAI/bge-small-en-v1.5` (33M params, 384-d, top-tier retrieval performance on MTEB).
- **Why not GPT here:** Running a GPT model just to produce sentence embeddings is 20×–50× slower, consumes gigabytes of memory, and requires extra pooling layers without giving better cosine similarity clustering than fine-tuned SBERT.

#### 2. Entity & Relation Extraction: Hybrid (spaCy / BERT or Small GPT)

- **Lightweight Baseline:** spaCy (`en_core_web_sm`) or a fine-tuned BERT token classifier for standard Named Entity Recognition (NER).
- **Deep Semantic Extraction:** A small, quantized local GPT/decoder model via Ollama (e.g., `llama3:8b-instruct-q4_K_M` or `qwen2.5:3b`) using structured JSON schema prompts to extract complex predicates like `[:ProjectLead] -> [:requiresSkill] -> [:TeamLeadership]`.

#### 3. Community Summarization & Global Sensemaking (GraphRAG): Use GPT / Autoregressive LLM

- **Why:** The core innovation of GraphRAG (Edge et al., 2024) is taking clusters of nodes detected by Leiden and running Map-Reduce summarization to synthesize global themes ("What are the core ideas across all notes?"). BERT cannot generate text, so an autoregressive LLM is essential here.
- **Recommended Models (Local/Offline via Ollama):**
    - `llama3.1:8b-instruct-q4_K_M` (standard research benchmark).
    - `phi3.5:3.8b-mini-instruct` or `qwen2.5:3b-instruct` (if targeting low RAM / laptop CPU constraints).

---

## 2. Infrastructure Requirements

To keep DriftGraph aligned with its local-first, CPU-viable research thesis, the infrastructure footprint should remain lean:

### Hardware & Compute Budgets

- **Minimum Spec (CPU-Only):**
    - 4-Core x86_64 or Apple Silicon CPU.
    - 8 GB – 16 GB RAM (allocating ~500 MB for SBERT/FastAPI and ~3.5–5 GB for a 4-bit quantized 3B–8B LLM).
- **Storage:** < 2 GB for application code, vector index, and SQLite database; ~4.5 GB for model weights via Ollama.

### Software & Runtime Stack

- **Embedding Inference:** Python 3.11+ with `sentence-transformers` (PyTorch CPU / ONNX Runtime via `fastembed`).
- **LLM Engine:** [Ollama](https://ollama.com/) or `llama-cpp-python` serving GGUF models locally with zero cloud dependencies.
- **Graph Compute:** `networkx` for in-memory graph representation and community detection (`leidenalg` / `python-igraph` or `scipy`).
- **Evaluation & Benchmarking:**
    - System metrics: Python `psutil` + `time` (measuring latency in ms, peak RSS memory in MB).
    - Quality metrics: `ragas` / `trulens` (measuring Context Precision, Faithfulness, and Answer Relevance).

---

## 3. Does Your Project Require a Backend and Database?

### Yes, absolutely.

While your static frontend prototype (`DriftGraph UI.html`) simulates graph rendering in Cytoscape.js using hardcoded mock arrays, a real DriftGraph system cannot function purely in the browser without a backend and database.

Here is why both are strictly necessary:

```
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                          CLIENT LAYER (Browser)                             │
  │       HTML5 / CSS / Vanilla JS / Cytoscape.js / D3.js (Force-Directed Graph)│
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                          │ HTTP REST / WebSockets (FastAPI)
                                          ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                     LOCAL BACKEND ENGINE (FastAPI)                          │
  │  ├── Ingestion & Chunking (mistune, python-frontmatter)                     │
  │  ├── SBERT Pipeline (sentence-transformers / ONNX)                          │
  │  ├── Graph Manager (NetworkX, Leiden partitioning)                          │
  │  └── GraphRAG Controller (Ollama extraction & Map-Reduce summarization)     │
  └──────────────────────┬───────────────────────────────┬──────────────────────┘
                         │                               │
                         ▼                               ▼
  ┌─────────────────────────────────────────┐  ┌────────────────────────────────┐
  │       EMBEDDED RELATIONAL DB            │  │      LOCAL VECTOR INDEX        │
  │   SQLite (FTS5 full-text search)        │  │     FAISS / ChromaDB           │
  │   • Notes metadata & clean text         │  │     • 384-d note vectors       │
  │   • Graph nodes, edges, weights         │  │     • Fast nearest-neighbor   │
  │   • Leiden community hierarchy          │  │       similarity lookup        │
  └─────────────────────────────────────────┘  └────────────────────────────────┘
```

---

### Why a Backend is Mandatory

1. **Heavy ML Model Execution:**
    - Browser JavaScript cannot efficiently run PyTorch-based Sentence-BERT or 8B parameter LLMs locally.
    - A Python backend (FastAPI / Uvicorn) acts as the orchestration bridge: it loads the SBERT model once into memory, exposes fast REST or WebSocket endpoints (e.g., `/api/embed`, `/api/extract-triples`, `/api/query-graph`), and streams results to the UI.
2. **Local File System Parsing & Ingestion:**
    - Browsers operate in a sandboxed security environment and cannot scan a local directory of Markdown files (`./path/to/your/notes`), watch for file changes, or strip YAML frontmatter cleanly.
    - The Python backend handles file I/O (`pathlib`), markdown AST cleaning (`mistune`, `python-frontmatter`), and regex processing.
3. **Graph Algorithms & Pipeline Coordination:**
    - Partitioning thousands of nodes using the Leiden algorithm and running Map-Reduce summarization passes requires graph libraries (`networkx`, `scipy`) that reside in Python.
4. **Profiling & Research Benchmarking:**
    - Your research objective (Evaluating Lightweight Embeddings) requires logging RAM usage, disk I/O, and latency per pipeline step via `psutil`. This is only possible in a native backend runtime.

---

### Why a Database is Mandatory (and Which One to Use)

Without a database, every time the user refreshes the page or opens the app, the system would have to re-parse all notes, re-calculate all 384-d embeddings, re-run expensive similarity matrices (O(N²)), and re-generate community summaries.

#### Specific Scenarios Requiring Storage:

1. **Vector Caching & Similarity Indexing:**
    - When a user adds or edits a single note, you should only embed that one note and query the existing vector store for top-k nearest neighbors in milliseconds.
    - Recommended Vector Store: FAISS (`faiss-cpu`) or ChromaDB. Both run in-process, produce zero external server overhead, and persist cleanly to local disk.
2. **Full-Text Search (FTS) & Hybrid Retrieval:**
    - GraphRAG combines semantic search (vectors) with lexical search (exact keywords like names or IDs).
    - Recommended Relational Store: SQLite with the FTS5 extension.
        - Single self-contained file (e.g. `data/driftgraph.db`).
        - Zero configuration, local-first, blazing fast.
        - Stores note records, chunk metadata, node IDs, edge weights, and community summaries.
3. **Graph Topology Persistence & Export:**
    - Persisting nodes, edges, community cluster IDs, and export formats (RDF/Turtle `.ttl` and JSON-LD) so the graph state survives app restarts without re-clustering.

---

## Summary Recommendation

|Project Component|Recommended Solution|Justification|
|---|---|---|
|Embedding Model|Sentence-BERT (`all-MiniLM-L6-v2` or `bge-small-en-v1.5`)|384-d vectors, <100 MB RAM, CPU-friendly, ideal for auto-linking notes and computing semantic closeness.|
|Generative LLM|Ollama (`llama3.1:8b` or `qwen2.5:3b`)|Quantized local execution for triplet extraction, Leiden community summaries, and Q&A.|
|Backend Framework|Python 3.11 + FastAPI|Lightweight, native async support, direct access to PyTorch, NetworkX, and system profiling.|
|Database Setup|SQLite (FTS5) + FAISS (local)|100% local-first, zero cloud dependencies, single-file storage, instantaneous hybrid (keyword + vector) search.|