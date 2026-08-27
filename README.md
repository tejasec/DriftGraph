# Drift Graph

**Reconstruct any knowledge graph using only the embeddings of your notes** — streamed into browser as a live, explorable web of ideas.

Drift Graph is a local-first research project that turns a folder of plain Markdown notes (Or Digital Document of Notes) into a fully connected **knowledge graph**. It extracts the *subjects* of your notes with a lightweight AI model, embeds every sentence into a dense vector space, and then lets an on-device LLM discover the entities and relationships hidden between them. The result is shown in your browser: every note *drifts* into the graph.

**Notes in, Drift out.** No sign-up, no cloud, no install beyond Python and Ollama.

## ✨ Features (To be Added)
- **Local-first and private** — no accounts, no cloud dependency; your notes and graph stay on your machine (SQLite).
- **Automatic knowledge graph generation** — entities and relationships are extracted from your notes without manual linking.
- **Relationship-aware notes** — notes link to each other semantically, not just by exact keyword match.
- **Semantic linking via lightweight embeddings** — small SBERT models (`all-MiniLM-L6-v2`) run on CPU, no GPU required.
- **Interactive graph view** — browse nodes and edges in the browser with force-directed layouts, color-coded categories, and click-to-inspect.
- **Community detection** — Leiden algorithm groups related concepts so you can see the thematic structure of your whole corpus at a glance.
- **Query-focused Q&A** — answer *global* questions ("What are the main themes?") using hierarchical community summaries, the GraphRAG way.
- **Fast full-text search** — SQLite FTS5 for instant keyword lookup alongside semantic search.
- **Voice assistant support** — speak a question, get an answer grounded in your graph (ElevenLabs + VibeVoice).
- **Export & sharing** — export the graph as JSON, PNG, PDF, or interactive HTML; serialize triples in RDF/Turtle and JSON-LD.
- **Benchmarked, not guessed** — every pipeline stage is evaluated with RAGAS/TruLens and profiled with `psutil` for memory and latency.

## 🎬 How it works (A Markdown Visualization)

```
Raw Markdown Notes
       │
       ▼
┌──────────────────────────┐
│ 1. Ingestion & Parsing    │  strip frontmatter, clean prose
│    (pathlib, mistune, re) │
└───────────┬──────────────┘
            ▼
┌──────────────────────────┐
│ 2. Chunking               │  sentence + semantic chunks
└───────────┬──────────────┘
            ▼
┌──────────────────────────┐
│ 3. Embedding              │  Sentence-BERT (all-MiniLM-L6-v2)
│    (sentence-transformers)│  384-d vectors, CPU-friendly
└───────────┬──────────────┘
            ▼
┌──────────────────────────┐
│ 4. Entity & Relation       │  on-device LLM via Ollama
│    Extraction             │  (Llama 3 / Mistral, quantized)
└───────────┬──────────────┘
            ▼
┌──────────────────────────┐
│ 5. Graph Assembly         │  NetworkX nodes + typed edges,
│    + Deduplication        │  embeddings stored per node
└───────────┬──────────────┘
            ▼
┌──────────────────────────┐
│ 6. Community Detection    │  Leiden partitioning into a
│    (Hierarchical)         │  hierarchy of communities
└───────────┬──────────────┘
            ▼
┌──────────────────────────┐
│ 7. Community Summaries    │  Map→Reduce LLM summaries
└───────────┬──────────────┘
            ▼
┌──────────────────────────┐
│ 8. Query & Answer         │  global Q&A from summaries,
│                           │  local Q&A from vector + FTS5
└──────────────────────────┘
```

**The research angle:** this project evaluates whether *lightweight* embedding models (125 M–220 M parameters, 384-d vectors, CPU-only) can match or beat heavy baselines on knowledge-graph generation — and where KG augmentation gives the biggest wins (high-semantic-relatedness regions).

For the full design — memory budgets, the wire protocol, concurrency model, and pipeline stages — see **ARCHITECTURE.md** *(coming soon)*.

## 🧱 Tech stack

| Layer | Technology |
| ----- | ---------- |
| Frontend | HTML / CSS / JavaScript, D3.js or Cytoscape.js (graph rendering) |
| Backend | Python 3.11+, FastAPI, SQLite (FTS5), Bash/Shell automation |
| NLP & Embeddings | sentence-transformers (`all-MiniLM-L6-v2`), Gensim (Word2Vec baseline), spaCy (NER) |
| LLM & Extraction | Ollama (local Llama 3 / Mistral, quantized) |
| Graph & Vector Store | NetworkX, FAISS or ChromaDB |
| Voice | ElevenLabs API, Microsoft VibeVoice, litellm |
| Evaluation & Benchmarking | RAGAS / TruLens, `psutil`, `time` |
| Parsing | `python-frontmatter`, `mistune`, `regex` |

## 🐳 Run it yourself

The app is meant to be used locally — but the pipeline is a self-contained set of Python modules if you want to run your own.

**Prerequisites**

- Python 3.11+
- [Ollama](https://ollama.com) (for the on-device entity/relation extraction LLM)

**Setup**

```bash
# 1. Clone the repo
git clone https://github.com/your-username/drift-graph.git
cd drift-graph

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Pull a local LLM for extraction
ollama pull llama3

# 5. Point Drift Graph at your notes and run the pipeline
python -m driftgraph.build --notes ./path/to/your/notes

# 6. Serve the web app
python -m driftgraph.serve
```

Then open `http://localhost:8000`, drop your notes in, and watch them drift into the graph.

## 📁 Project layout (File Structure)

```
driftgraph/
  ├── ingest/               # markdown parsing, frontmatter stripping, chunking
  ├── embed/                # sentence-transformers encoders + baselines
  ├── extract/              # Ollama entity/relation extraction prompts
  ├── graph/                # NetworkX assembly, dedup, Leiden communities
  ├── summarize/            # hierarchical community summaries (Map→Reduce)
  ├── query/                # global (GraphRAG) + local (vector/FTS5) Q&A
  ├── voice/                # ElevenLabs / VibeVoice / litellm integration
  ├── eval/                 # RAGAS/TruLens metrics + psutil benchmarks
  └── serve/                # FastAPI backend + static frontend
frontend/                   # interactive graph UI (D3.js/Cytoscape.js)
data/                       # sqlite.db, vector index, graph exports (.ttl, .jsonld)
tests/                      # unit + pipeline tests
requirements.txt
ARCHITECTURE.md             # full technical design (coming soon)
```

## 📚 Research foundation

This project combines two lines of research into one evaluable system:

1. **Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks**
   — Nils Reimers & Iryna Gurevych (2019)
   - arXiv: https://arxiv.org/abs/1908.10084
   - GitHub (official implementation): https://github.com/UKPLab/sentence-transformers

2. **From Local to Global: A Graph RAG Approach to Query-Focused Summarization**
   — Darren Edge et al., Microsoft Research (2024)
   - arXiv: https://arxiv.org/abs/2404.16130
   - Microsoft Research blog: https://www.microsoft.com/en-us/research/blog/graphrag-unlocking-llm-discovery-on-narrative-private-data/
   - GraphRAG docs: https://microsoft.github.io/graphrag/

Supporting literature:

- **Knowledge Graphs** — Aidan Hogan et al. (2021), ACM Computing Surveys — https://arxiv.org/abs/2003.02320
- **DistilBERT: a distilled version of BERT** — Victor Sanh et al. (2019) — https://arxiv.org/abs/1910.01108
- **Personal Knowledge Graphs: A Research Agenda** — Krisztian Balog & Tom Kenter (2019) — https://dl.acm.org/doi/10.1145/3341981.3344241
- **Awesome-GraphRAG** — curated references — https://github.com/DEEP-PolyU/Awesome-GraphRAG

**Research topic:** *Evaluating Lightweight Embeddings for Local Knowledge Graph Generation.*

## 🔬 Evaluation

- **Retrieval quality** — Context Precision, Faithfulness, Answer Relevance via RAGAS/TruLens.
- **Triple validity** — Precision / Recall / F1 on entity-relation extraction against a labeled subset.
- **Semantic closeness** — cosine similarity, RMSE, and Pearson correlation across STR (semantic relatedness) regions to show *where* KG augmentation helps most.
- **Efficiency** — per-stage memory (RAM) and latency (ms) across embedding models, proving local / CPU-only viability.

## 🚀 Future Scope

- OCR support for PDFs, images, and scanned documents (Tesseract).
- Multi-source import — Obsidian, Notion, Zotero, and web scraping into one unified graph.
- Real-time collaboration and multi-user support.
- 3D graph rendering and animated transitions.
- Self-improving graph — new notes re-tune communities automatically.
- Multilingual notes and multilingual voice queries.
- Android companion app (Lexitalk-style) built on the voice stack.

---

*Building as a final-year NLP research project. Notes in, Drift out.*
