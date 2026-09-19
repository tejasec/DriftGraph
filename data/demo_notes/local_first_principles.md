---
title: "Local-First Software and Data Ownership"
tags: [local-first, sqlite, privacy, architecture]
---

# Local-First Software and Data Ownership

Local-first software ensures users retain full ownership, sovereignty, and control of their personal data without mandatory cloud dependencies.

## Core Tenets in DriftGraph

1. **Embedded SQLite & FTS5**: All graph nodes, edges, notes, and community summaries are stored in a local SQLite file (`driftgraph.db`), providing ACID transactions and full-text search.
2. **Zero Mandatory Cloud Lock-in**: By default, DriftGraph runs entirely on-device using local Ollama models and local embedding models.
3. **Interactive Client-Side Canvas**: Cytoscape.js and HTML5 dual-canvas engines perform force-directed layout and 60 FPS physics simulations directly inside the user's browser.
4. **Hosted Demo Mode**: An explicit opt-in allows public demo hosting via OpenAI-compatible APIs without sacrificing the local-first default.
