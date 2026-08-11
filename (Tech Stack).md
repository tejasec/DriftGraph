
## 1. Core Programming Languages

- **Python (3.11+):** The absolute backbone of the project. Required for processing natural language, running machine learning models, and building the data pipelines.
- **Bash / Shell Scripting:** Crucial for writing automation scripts to monitor system resource metrics (CPU, RAM, and disk I/O latency) natively during the benchmarking phase.
- **HTML / CSS / JavaScript:** Used exclusively to render, interact with, and browse the final generated Knowledge Graph inside a standard web browser without needing heavy client applications.

## 2. NLP & Embedding Frameworks

- **Sentence-Transformers:** A lightweight Python framework used to compute dense vector embeddings for notes using small, efficient models like `all-MiniLM-L6-v2`.
- **Gensim:** A robust, highly efficient library used to implement the traditional baseline model (**Word2Vec**) for comparative analysis.
- **Ollama:** A local execution engine that runs highly optimized, quantized Large Language Models (like Llama 3 or Mistral) completely offline for the entity and relation extraction phases.
- **spaCy:** Lightweight Named Entity Recognition (NER) for entity extraction in the graph-building pipeline.

## 3. Data Ingestion & Parsing

- **Tree-Sitter / Built-in Python I/O:** Python's native file-handling utilities (`pathlib`, `os`) alongside regex (`re`) to clean Markdown files, strip frontmatter, and isolate raw content blocks.
- **Markdown / Frontmatter Toolkits:** Libraries like `python-frontmatter` or `mistune` to cleanly separate metadata tags from actual prose blocks before vectorization.

## 4. Graph & Vector Storage

- **NetworkX:** A native Python library for studying graphs and networks. Handles graph structures (nodes, edges, and communities) completely *in-memory*, avoiding the overhead of a heavy external database server.
- **FAISS (Facebook AI Similarity Search) or ChromaDB:** Extremely fast, lightweight vector similarity search libraries that run completely locally to store and query text embeddings.
- **SQLite (FTS5):** Local-first storage for notes and metadata, with full-text search built in — no accounts, no cloud dependency.

## 5. LLM / Voice Stack

- **ElevenLabs API:** Text-to-speech and voice synthesis for the voice assistant.
- **Microsoft VibeVoice:** https://github.com/microsoft/VibeVoice — real-time voice interaction layer.
- **litellm:** https://github.com/BerriAI/litellm — unified LLM routing, so model calls are swappable.

## 7. Evaluation & System Benchmarking

- **RAGAS / TruLens:** Modern evaluation frameworks used to mathematically measure the RAG system's **Context Precision**, **Faithfulness**, and **Answer Relevance**.
- **Psutil & time (Python standard libraries):** Custom evaluation scripts to track exactly how much memory (RAM) is consumed and how long (in milliseconds) it takes to generate and query the graph across different embedding models.
- **Fine-tuning comparison:** 3-way ablation — off-the-shelf vs. domain-fine-tuned lightweight embeddings vs. heavy baselines — to measure the lift from domain adaptation.

## 8. GraphRAG Pipeline (Backbone)

Document → Chunking → Entity/Relati# DriftGraph - GraphRAG
on Extraction (Ollama) → Knowledge Graph (NetworkX) → Community Partitioning (Leiden) → Hierarchical Community Summaries (Map→Reduce) → Query-Focused Answer Synthesis
