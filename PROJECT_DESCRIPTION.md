# DriftGraph: Comprehensive System Architecture, Operational Manual, & Visual Graph Evaluation Framework

> **System Moniker**: DriftGraph ("*Notes in, Drift out.*")  
> **System Purpose**: Local-First GraphRAG & Automatic Knowledge Graph Discovery from Markdown Notes  
> **Document Role**: Master Reference Specification for AI Coding Agents, LLMs, and Human Systems Engineers  

---

## 1. Executive Summary & Core Objectives

### 1.1 Project Identity & High-Level Vision
**DriftGraph** is a local-first, privacy-preserving knowledge discovery and Retrieval-Augmented Generation (GraphRAG) platform. It ingests folders of unstructured Markdown notes, digital documents, scanned papers, and web articles, transforming them into an interactive, multi-relational Knowledge Graph with multi-level hierarchical community clustering and grounded question-answering capabilities.

Unlike cloud-dependent knowledge systems or conventional vector-only semantic search engines, DriftGraph runs entirely on consumer hardware. It eliminates recurring API expenses, third-party data transmission, and manual bi-directional linking (`[[wiki-links]]`) by unifying lightweight CPU-optimized embedding models, local quantized Large Language Models (via [Ollama](https://ollama.com)), graph topological analysis (via [NetworkX](https://networkx.org)), and a dual-storage persistence architecture (SQLite with FTS5 lexical indexing alongside [FAISS](https://github.com/facebookresearch/faiss) dense vector indexing).

---

### 1.2 Core Problems Solved

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             THE THREE CORE PROBLEMS                              │
├─────────────────────────┬────────────────────────────┬───────────────────────────┤
│   Vector RAG Blindspot  │ Cloud Lock-In & Privacy    │ Manual Organization       │
├─────────────────────────┼────────────────────────────┼───────────────────────────┤
│ Standard Vector RAG is  │ Commercial GraphRAG tools  │ Tools like Obsidian,      │
│ incapable of answering  │ require continuous cloud   │ Roam, and Notion require  │
│ corpus-wide global      │ API access, transmitting   │ exhausting manual tagging │
│ sensemaking queries     │ sensitive private notes    │ and wiki-linking.         │
│ ("What are the main     │ to third parties.          │                           │
│ themes across my work?")│                            │ DriftGraph automates      │
│                         │ DriftGraph operates 100%   │ semantic link discovery   │
│ DriftGraph solves this  │ offline on consumer CPUs   │ and community formation   │
│ via Leiden Map-Reduce.  │ with zero telemetry.       │ through latent inference. │
└─────────────────────────┴────────────────────────────┴───────────────────────────┘
```

1. **The Vector RAG "Global Query" Blindspot**: Conventional vector databases chunk text and retrieve chunks via cosine similarity against a query embedding. While this works well for point-factual queries (*"What is Alice's phone number?"*), it catastrophically fails for global thematic synthesis (*"What overarching research directions emerge across all notes?"*). DriftGraph implements the hierarchical GraphRAG paradigm: partitioning the graph into modular communities (via the Leiden algorithm) and generating pre-computed Map-Reduce summaries at every hierarchical tier.
2. **Cloud Lock-In and Privacy Hazards**: Notes contain proprietary research, personal reflections, legal documents, and intellectual property. DriftGraph guarantees absolute local residency. All vector embeddings, entity extractions, graph operations, database queries, and neural inferences execute on local CPU/RAM or local Ollama instances.
3. **Manual Note-Linking Fatigue**: Modern personal knowledge management (PKM) systems place the burden of linking on the user. Unlinked notes become isolated data silos. DriftGraph reconstructs latent semantic bridges and multi-hop relationships automatically, allowing notes to "drift" organically into an interactive topology.

---

### 1.3 Academic Research Thesis
DriftGraph was conceived and architected as a final-year Natural Language Processing research project.

> **Research Hypothesis**:  
> *Can lightweight, CPU-viable embedding models (~22M–110M parameters, 384 dimensions, e.g., `sentence-transformers/all-MiniLM-L6-v2`) match or outperform heavy multi-billion-parameter cloud embeddings in local knowledge graph assembly, entity resolution, and Leiden community partitioning, while maintaining a sub-100MB RAM footprint and sub-50ms CPU latency?*

Supporting foundational literature:
# Research Papers Compendium: Knowledge Graphs, Embeddings & RAG

---

## 1. AutoKG: Efficient Automated Knowledge Graph Generation for Language Models

- **Authors:** Bohan Chen, Andrea L. Bertozzi
- **Year & Venue:** 2023 | IEEE International Conference on Big Data (BigData 2023)

### Direct Links
| Resource Type | Link |
| :--- | :--- |
| **arXiv (Free Abstract)** | [arXiv:2311.14740](https://arxiv.org/abs/2311.14740) |
| **arXiv Direct PDF** | [Download PDF](https://arxiv.org/pdf/2311.14740) |
| **IEEE Xplore DOI** | [10.1109/BigData59044.2023.10386454](https://doi.org/10.1109/BigData59044.2023.10386454) |
| **GitHub Repository** | [wispcarey/AutoKG](https://github.com/wispcarey/AutoKG) |

### Key Points from the Paper
- **Problem:** Conventional knowledge graph construction (KGC) pipelines rely heavily on human annotations, domain heuristics, or high-latency closed-source LLMs (like GPT-4), making dynamic, automated local KG generation prohibitively slow and expensive for constrained compute environments.
- **Solution:** AutoKG introduces an end-to-end automated framework designed to leverage compact, lightweight language models and prompt-guided workflows to extract entities, relationships, and properties without requiring massive parameter overhead.
- **Pipeline:**
  $$\text{Raw Documents} \longrightarrow \text{Chunking \& Preprocessing} \longrightarrow \text{Lightweight Open-Source LLM Extraction} \longrightarrow \text{Canonicalization \& Deduplication} \longrightarrow \text{Graph Formation} \longrightarrow \text{Downstream Retrieval}$$
- **Key Results:** Achieves comparable relation extraction precision and graph utility to massive commercial LLMs while drastically reducing compute resources, validating the feasibility of edge/local automated knowledge graph generation.
- **Relevance to Your Research:** Highly relevant. Provides concrete techniques for using lightweight models to automatically construct local knowledge graphs.

---

## 2. Context Graph

- **Authors:** Chengjin Xu, Muzhi Li, Changhe Yang, Xinyu Jiang, Lumingyuan Tang, Yu Qi, Jiaoyan Guo
- **Year & Venue:** 2024 | arXiv Preprint (cs.AI)

### Direct Links
| Resource Type | Link |
| :--- | :--- |
| **arXiv (Free Abstract)** | [arXiv:2406.11160](https://arxiv.org/abs/2406.11160) |
| **arXiv Direct PDF** | [Download PDF](https://arxiv.org/pdf/2406.11160) |
| **Semantic Scholar** | [Paper Details](https://www.semanticscholar.org/paper/Context-Graph-Xu-Li/0b45700810ff40854d6f859fb16f498c3971cbfb) |

### Key Points from the Paper
- **Problem:** Traditional Knowledge Graphs model facts strictly as static flat triples $(h, r, t)$ (head, relation, tail). This format discards critical contextual modifiers such as temporal validity, spatial condition, conditionality, and source scope, which leads to ambiguity during multi-hop graph reasoning.
- **Solution:** Introduces the **Context Graph** paradigm, which models context explicitly as first-class hyper-relational nodes and edges, accompanied by a Context Graph Reasoning architecture ($CGR^3$) to capture multi-layered situational knowledge.
- **Pipeline:**
  $$\text{Semi-structured / Text Data} \longrightarrow \text{Context Decomposition} \longrightarrow \text{Hyper-relational Node Linking} \longrightarrow \text{Context-Aware GNN Embedding} \longrightarrow \text{Multi-hop Reasoning}$$
- **Key Results:** Demonstrates marked improvements over standard KG embedding baselines on complex reasoning and question answering tasks where truth values depend strictly on contextual constraints.
- **Relevance to Your Research:** Informs how local knowledge graphs can store contextual attributes without exploding in dimensionality.

---

## 3. DistilBERT, a Distilled Version of BERT: Smaller, Faster, Cheaper and Lighter

- **Authors:** Victor Sanh, Lysandre Debut, Julien Chaumond, Thomas Wolf (Hugging Face)
- **Year & Venue:** 2019 | NeurIPS EMC^2 Workshop

### Direct Links
| Resource Type | Link |
| :--- | :--- |
| **arXiv (Free Abstract)** | [arXiv:1910.01108](https://arxiv.org/abs/1910.01108) |
| **arXiv Direct PDF** | [Download PDF](https://arxiv.org/pdf/1910.01108) |
| **GitHub (Hugging Face)** | [huggingface/transformers (DistilBERT)](https://github.com/huggingface/transformers/tree/main/examples/research_projects/distillation) |

### Key Points from the Paper
- **Problem:** Pre-trained transformer models such as BERT are computationally heavy and have significant memory footprints, limiting their execution on resource-constrained hardware or in low-latency production setups.
- **Solution:** Applies knowledge distillation during pre-training to compress BERT-base into a 6-layer architecture (reducing parameters by 40%), while initializing the student from alternating layers of the teacher.
- **Objective Function:** Trained using a triple loss function combining distillation loss, masked language modeling loss, and cosine embedding loss:
  $$\mathcal{L}_{total} = \alpha\, \mathcal{L}_{ce} + \beta\, \mathcal{L}_{mlm} + \gamma\, \mathcal{L}_{cos}$$
- **Key Results:** Retains **97%** of BERT’s full language understanding performance on the GLUE benchmark, while running **60% faster** and consuming **40% less memory**.
- **Relevance to Your Research:** Primary candidate for the "lightweight embedding backbone" in local graph generation pipelines.

---

## 4. From Local to Global: A Graph RAG Approach to Query-Focused Summarization

- **Authors:** Darren Edge, Ha Trinh, Newman Cheng, Joshua Bradley, Alex Chao, Apurva Mody, Steven Truitt, Dasha Metropolitansky, Robert Osazuwa Ness, Jonathan Larson (Microsoft Research)
- **Year & Venue:** 2024 | arXiv Preprint (cs.CL)

### Direct Links
| Resource Type | Link |
| :--- | :--- |
| **arXiv (Free Abstract)** | [arXiv:2404.16130](https://arxiv.org/abs/2404.16130) |
| **arXiv Direct PDF** | [Download PDF](https://arxiv.org/pdf/2404.16130) |
| **Microsoft Research Page** | [GraphRAG Publication Hub](https://www.microsoft.com/en-us/research/project/graphrag/publications/) |
| **Official GitHub** | [microsoft/graphrag](https://github.com/microsoft/graphrag) |

### Key Points from the Paper
- **Problem:** Conventional vector-similarity RAG fails on global questions (e.g., *"What are the primary themes across this dataset?"*) because vector search only retrieves locally isolated text chunks rather than synthesizing dataset-wide semantics.
- **Solution:** GraphRAG extracts an entity-relation knowledge graph from documents, clusters related entities into hierarchical communities using the Leiden algorithm, generates modular summaries for each community, and executes Map-Reduce answer generation at query time.
- **Pipeline:**
  $$\text{Text Chunks} \longrightarrow \text{Entity/Relation Extraction} \longrightarrow \text{Knowledge Graph Construction} \longrightarrow \text{Leiden Community Detection} \longrightarrow \text{Hierarchical Summaries} \longrightarrow \text{Map-Reduce Synthesis}$$
- **Key Results:** Significant gains in answer comprehensiveness, thematic diversity, and factual recall over standard vector RAG on corpora comprising millions of tokens.
- **Relevance to Your Research:** One of your foundational pillars. Demonstrates how graph-based structuring solves high-level summarization and reasoning tasks.

---

## 5. Joint Beamforming and Power Control for D2D-Assisted Integrated Sensing and Communication Networks

- **Authors:** Zhenyu Xue, Yuang Chen, Hancheng Lu, Baolin Chong, Wanqing Zhao, Dan Zhao
- **Year & Venue:** 2024 | IEEE GLOBECOM 2024 / arXiv:2408.09844

### Direct Links
| Resource Type | Link |
| :--- | :--- |
| **arXiv (Free Abstract)** | [arXiv:2408.09844](https://arxiv.org/abs/2408.09844) |
| **arXiv Direct PDF** | [Download PDF](https://arxiv.org/pdf/2408.09844) |
| **Semantic Scholar** | [Paper Record](https://www.semanticscholar.org/paper/Cooperative-Sensing-Beamforming-in-D2D-enhanced-Lu-Guo/4de9bdf9ea58cf3ea88dea0469ab2ac5ad251b3c) |

### Key Points from the Paper
- **Clarification Note:** *This paper corresponds to arXiv identifier `2408.09844`.*
- **Problem:** Integrated Sensing and Communication (ISAC) networks face performance trade-offs between radar target tracking and high-speed data transmission due to cross-tier interference and power constraints in Device-to-Device (D2D) cellular architectures.
- **Solution:** Formulates a joint optimization problem coordinating transmit beamforming at base stations and power allocation across local D2D links to maximize radar beampattern gain subject to strict communication Quality of Service (QoS).
- **Optimization Strategy:** Decomposes non-convex constraints using Fractional Programming (FP) and Successive Convex Approximation (SCA), solved via an iterative Alternating Optimization (AO) framework.
- **Key Results:** Yields sharp radar sensing beams with minimal main-lobe distortion while preserving full multi-user communication throughput over uncoordinated baselines.

---

## 6. Knowledge Graphs

- **Authors:** Aidan Hogan, Eva Blomqvist, Michael Cochez, Claudia d'Amato, Gerard de Melo, Claudio Gutierrez, Sabrina Kirrane, José Emilio Labra Gayo, Roberto Navigli, Sebastian Neumaier, Axel-Cyrille Ngonga Ngomo, Axel Polleres, Sabbir M. Rashid, Anisa Rula, Lukas Schmelzeisen, Juan Sequeda, Steffen Staab, Antoine Zimmermann
- **Year & Venue:** 2021 | ACM Computing Surveys (CSUR), Vol. 54, No. 4

### Direct Links
| Resource Type | Link |
| :--- | :--- |
| **ACM Digital Library** | [10.1145/3447772](https://dl.acm.org/doi/10.1145/3447772) |
| **arXiv (Free Abstract)** | [arXiv:2003.02320](https://arxiv.org/abs/2003.02320) |
| **arXiv Direct PDF** | [Download PDF](https://arxiv.org/pdf/2003.02320) |

### Key Points from the Paper
- **Problem:** Knowledge graph literature had been fractured across disparate sub-disciplines (Semantic Web standards, graph database systems, neural knowledge representations, and symbolic reasoning), lacking a unified taxonomy.
- **Solution:** Delivers the authoritative comprehensive survey and reference architecture detailing graph data models, schema languages, deductive semantics, and inductive representation learning.
- **Core Coverage:**
  - **Data Models:** Directed Edge-labelled Graphs, Property Graphs, RDF triples.
  - **Deductive Reasoning:** Description Logics, OWL, Datalog, SHACL constraints.
  - **Inductive Learning:** Translational embeddings ($\text{TransE}$), tensor factorizations ($\text{ComplEx}$), and Graph Neural Networks (GNNs).
  - **Lifecycle:** Extraction, Canonicalization, Quality Assessment, and Refinement.
- **Relevance to Your Research:** Serves as the primary theoretical baseline for graph representations, triple definitions, and schema construction.

---

## 7. Knowledge Graphs Meet Multi-Modal Learning: A Comprehensive Survey

- **Authors:** Zhuo Chen, Yichi Zhang, Yin Fang, Yuxia Geng, Lingbing Guo, Xiang Chen, Qian Li, Mengshu Sun, Jiaoyan Chen, Xiaoze Liu, Jeff Z. Pan, Huajun Chen
- **Year & Venue:** 2024 | arXiv Preprint (cs.AI)

### Direct Links
| Resource Type | Link |
| :--- | :--- |
| **arXiv (Free Abstract)** | [arXiv:2402.05391](https://arxiv.org/abs/2402.05391) |
| **arXiv Direct PDF** | [Download PDF](https://arxiv.org/pdf/2402.05391) |
| **GitHub Repository** | [zjukg/KG-MM-Survey](https://github.com/zjukg/KG-MM-Survey) |

### Key Points from the Paper
- **Problem:** Real-world knowledge is inherently multi-modal (text, vision, audio), but classical KGs remain strictly symbolic and textual. Conversely, Vision-Language Models (VLMs) often suffer from hallucinations and lack structured, interpretable grounding.
- **Solution:** A taxonomy structuring the field into two complementary paradigms:
  1. **KG4MM:** Applying structured knowledge graphs to guide, align, and ground multi-modal perception and generation.
  2. **MM4KG:** Leveraging multi-modal signals (images, diagrams, video) to construct, complete, and enrich knowledge graphs.
- **Key Results:** Reviews over 300 papers, identifying common embedding spaces that combine multi-modal features with structural graph embeddings for enhanced multi-modal RAG and link prediction.
- **Relevance to Your Research:** Useful for extending local text-based knowledge graphs to incorporate non-textual attributes or diagrammatic documentation.

---

## 8. LightRAG: Simple and Fast Retrieval-Augmented Generation

- **Authors:** Zirui Guo, Lianghao Xia, Yanhua Yu, Tu Ao, Chao Huang
- **Year & Venue:** 2024 / 2025 | arXiv Preprint / EMNLP Findings

### Direct Links
| Resource Type | Link |
| :--- | :--- |
| **arXiv (Free Abstract)** | [arXiv:2410.05779](https://arxiv.org/abs/2410.05779) |
| **arXiv Direct PDF** | [Download PDF](https://arxiv.org/pdf/2410.05779) |
| **GitHub Repository** | [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) |

### Key Points from the Paper
- **Problem:** Microsoft GraphRAG requires substantial compute resources: it makes extensive LLM calls during indexing, relies on slow community detection, cannot easily handle real-time incremental graph updates, and struggles with unified low-level vs. high-level query retrieval.
- **Solution:** LightRAG introduces a dual-level graph indexing and retrieval framework that efficiently captures both fine-grained entity details and broad relational themes, while supporting continuous, incremental graph updating with minimal LLM calls.
- **Dual-Level Retrieval Mechanism:**
  - **Low-Level Retrieval:** Retrieves specific entities and their direct 1-hop neighborhoods for factual queries.
  - **High-Level Retrieval:** Aggregates broader relational themes and interconnected subgraphs for abstract thematic queries.
- **Key Results:** Outperforms GraphRAG and Vector RAG in both response quality and comprehensiveness while reducing token consumption and indexing time by up to an order of magnitude.
- **Relevance to Your Research:** Directly aligns with your research goal. LightRAG illustrates how to keep graph-based RAG computationally lightweight and fast on local machines.

---

## 9. MMKG: Multi-Modal Knowledge Graphs

- **Authors:** Ye Liu, Hui Li, Alberto Garcia-Duran, Mathias Niepert, Daniel Onoro-Rubio, David S. Rosenblum
- **Year & Venue:** 2019 | Extended Semantic Web Conference (ESWC 2019)

### Direct Links
| Resource Type | Link |
| :--- | :--- |
| **arXiv (Free Abstract)** | [arXiv:1903.05485](https://arxiv.org/abs/1903.05485) |
| **arXiv Direct PDF** | [Download PDF](https://arxiv.org/pdf/1903.05485) |
| **GitHub Benchmark Data** | [nle-ai/MMKG](https://github.com/nle-ai/MMKG) |

### Key Points from the Paper
- **Problem:** Existing link prediction and entity alignment benchmarks (such as FB15k and DB15k) evaluated purely symbolic graph structures, lacking synchronized multi-modal data (images, numerical attributes) to test multi-modal representation learning.
- **Solution:** Introduces MMKG, a standardized collection of multi-modal knowledge graph benchmarks (FB15k-MM, DB15k, and YAGO15k) containing numerical attributes and image associations, alongside multi-modal embedding baselines.
- **Pipeline:**
  $$\text{KG Triples } (h, r, t) + \text{Numerical Attributes } \mathbf{x}_{num} + \text{Images } \mathbf{x}_{img} \longrightarrow \text{Multi-Modal Fusion} \longrightarrow \text{Entity Alignment / Link Prediction}$$
- **Key Results:** Demonstrates that multi-modal fusion improves link prediction and cross-graph entity matching over purely topological or relation-only models.
- **Relevance to Your Research:** Provides standard benchmarking methodologies for evaluating feature-augmented knowledge graphs.

---

## 10. Personal Knowledge Graphs: A Research Agenda

- **Authors:** Krisztian Balog, Tom Kenter
- **Year & Venue:** 2019 | ACM International Conference on the Theory of Information Retrieval (ICTIR 2019)

### Direct Links
| Resource Type | Link |
| :--- | :--- |
| **ACM Digital Library** | [10.1145/3341981.3344241](https://dl.acm.org/doi/10.1145/3341981.3344241) |
| **Author Free PDF** | [Download PDF (krisztianbalog.com)](https://krisztianbalog.com/files/ictir2019-pkg.pdf) |
| **Google Research Publication** | [Google Research Hub](https://research.google/pubs/personal-knowledge-graphs-a-research-agenda/) |

### Key Points from the Paper
- **Problem:** World knowledge graphs (Wikidata, DBpedia, Google Knowledge Graph) capture public facts but lack private, user-centric contexts (preferences, personal relations, device interactions, and routines) necessary for individualized AI assistants.
- **Solution:** Formalizes the concept of Personal Knowledge Graphs (PKGs) and maps out a foundational research agenda covering PKG definition, extraction, enrichment, representation, privacy management, and downstream conversational tasks.
- **Key Dimensions:**
  - **Schema & Extraction:** Extracting entities and relations from fragmented personal data (emails, chats, notes, calendar events).
  - **Privacy & Ownership:** On-device storage, local inference, and fine-grained data access controls.
  - **Applications:** Personalized information retrieval, proactive suggestions, and context-aware dialogue systems.
- **Relevance to Your Research:** Defines why local, lightweight KG generation is essential—enabling private, on-device user graphs without cloud data leakage.

---

## 11. Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks

- **Authors:** Nils Reimers, Iryna Gurevych
- **Year & Venue:** 2019 | Empirical Methods in Natural Language Processing (EMNLP 2019)

### Direct Links
| Resource Type | Link |
| :--- | :--- |
| **arXiv (Free Abstract)** | [arXiv:1908.10084](https://arxiv.org/abs/1908.10084) |
| **arXiv Direct PDF** | [Download PDF](https://arxiv.org/pdf/1908.10084) |
| **Official GitHub** | [UKPLab/sentence-transformers](https://github.com/UKPLab/sentence-transformers) |

### Key Points from the Paper
- **Problem:** Standard BERT does not generate standalone sentence embeddings. Computing semantic similarity between pairs requires feeding both sentences into the network simultaneously ($O(n^2)$ complexity), which takes ~65 hours to find the most similar pair among 10,000 sentences—rendering clustering and vector search unfeasible.
- **Solution:** SBERT modifies BERT using a siamese/triplet network architecture with mean-pooling to produce fixed-dimensional dense vector embeddings for individual sentences, enabling cosine similarity calculations in milliseconds ($O(n)$ encoding + instant search).
- **Architecture & Losses:**
  - Siamese network with tied weights for sentence pairs $(u, v)$.
  - **Classification Objective:** Linear classifier trained on concatenation $(u, v, |u - v|)$.
  - **Regression Objective:** Mean squared error on cosine similarity $\cos(u, v)$.
  - **Triplet Objective:** Distance minimization between anchor, positive, and negative embeddings.
- **Key Results:** Decreases semantic search runtime from **65 hours to 5 seconds** while achieving superior correlation on Semantic Textual Similarity (STS) benchmarks compared to InferSent and Universal Sentence Encoder.
- **Relevance to Your Research:** The foundational embedding model for generating dense representations of entity labels, relation mentions, and text units during local knowledge graph construction.

---

## Summary Matrix: Mapping to Research Topic
*Evaluating Lightweight Embeddings for Local Knowledge Graph Generation*

| Paper | Focus Area | Role in Your Proposed Architecture |
| :--- | :--- | :--- |
| **SBERT** (Reimers et al.) | Dense Sentence Embeddings | Fast node/relation embedding, entity linking, and similarity clustering |
| **DistilBERT** (Sanh et al.) | Compact Pre-trained Encoders | Lightweight backbone for local on-device inference without GPU clusters |
| **GraphRAG** (Edge et al.) | Graph Summarization & Retrieval | Macro-architecture for community detection and query-focused retrieval |
| **LightRAG** (Guo et al.) | Efficient Dual-Level Graph RAG | Low-cost incremental indexing and dual-level local graph retrieval |
| **AutoKG** (Chen et al.) | Automated Extraction | Pipeline template for open-source, prompt-based entity-relation extraction |
| **Context Graph** (Xu et al.) | Hyper-relational Structure | Managing contextual constraints and metadata on local graph nodes |
| **Personal KGs** (Balog et al.) | User-Centric Representation | Motivation and application scope for local, privacy-preserving graph storage |
| **Hogan et al. Survey** | Theoretical Foundations | Standard taxonomy for graph data models and representation learning |





---

## 2. End-to-End System Architecture & Data Flow

DriftGraph executes as a coordinated multi-stage pipeline where raw textual data flows through ingestion, chunking, embedding, extraction, assembly, partitioning, summarization, persistence, and intelligent query dispatch.

### 2.1 Architectural Flowchart
```mermaid
flowchart TD
    subgraph S1 ["1. Multi-Source Ingestion & Preprocessing"]
        A1["Markdown Notes (*.md)"] --> B1["Prose & Frontmatter Parser<br/>(pathlib, python-frontmatter, mistune)"]
        A2["Scanned PDFs & Images"] --> B2["Multi-Engine OCR Studio<br/>(Tesseract, Layout & Table Detector)"]
        A3["Web URLs & Articles"] --> B3["Web Article Scraper<br/>(HTML to Clean Markdown & Auto-Tagger)"]
        B1 & B2 & B3 --> C1["Semantic Chunker<br/>(Sentence boundaries, 256-512 tokens, 32-token overlap)"]
    end

    subgraph S2 ["2. Dual Embedding & Extraction Layer"]
        C1 --> D1["SBERT Vectorizer<br/>(all-MiniLM-L6-v2, 384-d, L2 Norm)"]
        C1 --> D2["Local Ollama Client<br/>(llama3.1:8b-instruct-q4_K_M / qwen2.5:3b)"]
        D1 --> E1["FAISS Vector Store<br/>(IndexFlatIP, In-Memory + Disk)"]
        D2 --> E2["Extracted Knowledge Triples<br/>(Subject, Predicate, Object, Confidence)"]
    end

    subgraph S3 ["3. Graph Assembly & Community Partitioning"]
        E2 --> F1["Entity Resolver & Deduplicator<br/>(Fuzzy String Match + Cosine Similarity)"]
        F1 --> F2["NetworkX MultiDiGraph<br/>(Typed Edges, Provenance & Weights)"]
        F2 --> F3["Hierarchical Leiden Partitioning<br/>(Multi-scale Resolution Clustering)"]
    end

    subgraph S4 ["4. Hierarchical Map-Reduce Summarization"]
        F3 --> G1["Level 1/2 Community Summaries (Map)<br/>(Thematic Findings, Entity Rolodex, Narrative)"]
        G1 --> G2["Level 0 Global Corpus Summary (Reduce)<br/>(Overarching Core Themes & Cross-Domain Insights)"]
    end

    subgraph S5 ["5. Dual Persistence Engine"]
        B1 & C1 & F2 & F3 & G1 & G2 --> H1[("SQLite Database (driftgraph.db)<br/>Relational Tables: notes, chunks, nodes, edges, comms")]
        H1 --> H2["SQLite FTS5 Virtual Tables<br/>(BM25 Full-Text Lexical Search)"]
        E1 --> H3["Serialized FAISS Index<br/>(faiss.index on disk)"]
    end

    subgraph S6 ["6. Query Routing & Dual-Search Engine"]
        UserQuery["User Natural Language Query"] --> QueryRouter{"Intelligent Intent Router"}
        QueryRouter -->|"Global Thematic Query<br/>(e.g., 'What are the main themes?')| GlobalEngine["Global Search Engine<br/>(Map-Reduce over Leiden Summaries)"]
        QueryRouter -->|"Local Factual Query<br/>(e.g., 'What is Project Alpha?')| LocalEngine["Local Hybrid Search Engine<br/>(FAISS Dense + SQLite FTS5 Lexical)"]
        LocalEngine --> RRF["Reciprocal Rank Fusion (RRF, k=60)<br/>Score = 1/(60 + r_dense) + 1/(60 + r_lex)"]
        GlobalEngine & RRF --> AnswerSynth["LLM Context Synthesis<br/>(Grounded Answer + Markdown Source Citations)"]
    end

    subgraph S7 ["7. Visual Interface & Auxiliary Studios"]
        AnswerSynth --> FastAPIApp["FastAPI Asynchronous REST Backend"]
        FastAPIApp --> UI["Interactive 2-Pane Studio Workspace<br/>(Cytoscape.js Force Canvas + Note Editor)"]
        FastAPIApp --> Voice["Voice Assistant RAG (ElevenLabs / VibeVoice)"]
        FastAPIApp --> Analytics["Graph Intelligence Studio (God Nodes & Path Explorer)"]
        FastAPIApp --> Classifier["Offline Rule-Based Text Classifier (6 Domains)"]
    end
```

---

### 2.2 Detailed Pipeline Stages & Transformations

#### Stage 1: Ingestion & Provenance Parsing
- **Prose Stripping**: In [`driftgraph.ingest.parser`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/ingest/parser.py), `python-frontmatter` extracts YAML metadata (`title`, `date`, `tags`) while preserving clean body text. Fallback regex patterns ensure malformed frontmatter does not halt ingestion.
- **Semantic Chunking**: In [`driftgraph.ingest.chunker`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/ingest/chunker.py), text is segmented using sentence-boundary detection. Chunks are sized between 256 and 512 tokens with a 32-token sliding overlap. Every chunk maintains explicit provenance: `note_id`, `chunk_index`, `start_char`, `end_char`, and token length.

#### Stage 2: Dense Vectorization
- **Embedding Generation**: In [`driftgraph.embed.sbert`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/embed/sbert.py), each chunk is encoded via `sentence-transformers/all-MiniLM-L6-v2` into a 384-dimensional dense vector.
- **Normalization**: Vectors are strictly L2-normalized ($||\mathbf{v}||_2 = 1.0$), enabling inner product operations in FAISS to precisely evaluate cosine similarity:
  $$\text{sim}(\mathbf{u}, \mathbf{v}) = \mathbf{u} \cdot \mathbf{v} = \sum_{i=1}^{384} u_i v_i$$

#### Stage 3: Entity & Relation Triple Extraction
- **On-Device LLM Prompting**: In [`driftgraph.extract.ollama_client`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/extract/ollama_client.py), chunks are passed to a local Ollama model (default: `llama3.1:8b-instruct-q4_K_M`).
- **Structured Output**: Few-shot prompt templates ([`prompts.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/extract/prompts.py)) instruct the model to produce strict JSON arrays containing:
  - `name`: Entity identifier
  - `type`: Semantic category (`CONCEPT`, `PERSON`, `ORGANIZATION`, `TECHNOLOGY`, `PROJECT`)
  - `description`: Contextual explanation
  - Triples: `(subject, predicate, object)` with relationship descriptions
- **Heuristic Fallback**: In [`driftgraph.extract.parser`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/extract/parser.py), if Ollama emits malformed JSON or markdown codeblocks, a fallback regex parser recovers triples via grammar-based text extraction patterns.

#### Stage 4: Graph Assembly & Entity Resolution
- **Normalization & Deduplication**: In [`driftgraph.graph.dedup`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/graph/dedup.py), entity names are normalized (trimmed, lowercased, punctuation-stripped). Cosine similarity across entity description embeddings resolves near-duplicate entities (e.g., `"SBERT"` and `"Sentence-BERT"`).
- **NetworkX Topology**: In [`driftgraph.graph.builder`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/graph/builder.py), an in-memory `MultiDiGraph` is populated. Nodes represent resolved entities with properties (`type`, `degree`, `community`, `provenance_chunks`); directed edges carry predicates, descriptions, and occurrence weights.

#### Stage 5: Hierarchical Leiden Community Detection
- **Community Partitioning**: In [`driftgraph.graph.communities`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/graph/communities.py), the Leiden algorithm optimizes modularity across multiple resolution parameters:
  - **Level 0 (Macro)**: Broad global topic clusters (e.g., "Deep Learning", "Software Architecture").
  - **Level 1 (Meso/Micro)**: Fine-grained sub-communities and localized entity cliques.
- **Fallbacks**: If the `leidenalg` C-extensions are unavailable on the host system, the engine gracefully falls back to the Louvain algorithm (`python-louvain`) or greedy modularity optimization.

#### Stage 6: Hierarchical Map-Reduce Summaries
- **Map Step**: In [`driftgraph.summarize.map_reduce`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/summarize/map_reduce.py), for each detected community, all internal nodes, edges, and provenance chunks are compiled into a prompt. The local LLM generates an executive community report detailing primary themes, key findings, and member entities.
- **Reduce Step**: Level 1 community reports are consolidated into an overarching Level 0 corpus summary.
- **Context Compression**: By answering global queries from pre-computed community reports rather than raw text chunks, DriftGraph achieves a **9× to 43× token compression**, allowing exhaustive corpus Q&A to execute on 8B-parameter local models without context truncation.

#### Stage 7: Dual Persistence Layer
- **SQLite Storage**: In [`driftgraph.graph.storage`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/graph/storage.py), structured data persists in `data/driftgraph.db` using relational tables (`notes`, `chunks`, `nodes`, `edges`, `communities`, `metadata`).
- **Full-Text Search (FTS5)**: Dedicated SQLite FTS5 virtual tables (`chunks_fts`, `communities_fts`) index prose with the Porter stemming tokenizer for sub-millisecond keyword retrieval.
- **Vector Storage**: In [`driftgraph.graph.vector_store`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/graph/vector_store.py), chunk embeddings are stored in a FAISS `IndexFlatIP` vector index and serialized to `data/faiss.index`.

#### Stage 8: Dual-Mode Query Routing & Answering
- **Intent Classifier**: In [`driftgraph.query.router`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/query/router.py), user queries are classified into **Global** (thematic/summarization) or **Local** (factual/relational) mode.
- **Global Search**: In [`driftgraph.query.global_search`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/query/global_search.py), queries are mapped against Level 0/1 community reports. Key community findings are aggregated and synthesized into an overarching narrative.
- **Local Hybrid Search**: In [`driftgraph.query.local`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/query/local.py), queries trigger parallel retrieval:
  1. Dense semantic search via FAISS (`IndexFlatIP`).
  2. Lexical keyword search via SQLite FTS5 BM25.
  3. **Reciprocal Rank Fusion (RRF)**: Merges ranked results using constant $k=60$:
     $$RRF\_Score(d) = \frac{1}{60 + \text{rank}_{\text{dense}}(d)} + \frac{1}{60 + \text{rank}_{\text{lexical}}(d)}$$
  Top chunks and their immediate 1-hop knowledge graph neighborhood are supplied to the LLM, synthesizing a response with strict Markdown source citations (`[NOTE: filename]`).

---

## 3. Comprehensive Subsystem & Module Catalog

| Subsystem Module | Core Responsibilities & Classes | Key Source Files |
| :--- | :--- | :--- |
| **`driftgraph.ingest`** | Parsing Markdown frontmatter, cleaning raw text, semantic token chunking, and multi-engine document OCR. | [`parser.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/ingest/parser.py)<br/>[`chunker.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/ingest/chunker.py)<br/>[`ocr.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/ingest/ocr.py)<br/>[`ocr_engines.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/ingest/ocr_engines.py)<br/>[`ocr_layout.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/ingest/ocr_layout.py)<br/>[`ocr_models.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/ingest/ocr_models.py) |
| **`driftgraph.embed`** | Sentence-BERT vectorization (`all-MiniLM-L6-v2`, 384-d, L2 norm), Gensim Word2Vec baseline encoder, abstract embedding interface. | [`sbert.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/embed/sbert.py)<br/>[`baseline.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/embed/baseline.py)<br/>[`base.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/embed/base.py)<br/>[`models.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/embed/models.py) |
| **`driftgraph.extract`** | Asynchronous HTTP extraction client for Ollama, few-shot JSON schema prompt engineering, robust regex heuristic fallback parser. | [`ollama_client.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/extract/ollama_client.py)<br/>[`prompts.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/extract/prompts.py)<br/>[`parser.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/extract/parser.py)<br/>[`models.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/extract/models.py) |
| **`driftgraph.graph`** | In-memory NetworkX `MultiDiGraph` construction, entity resolution and deduplication, hierarchical Leiden clustering, SQLite async storage with FTS5, FAISS index management, RDF serialization (Turtle, JSON-LD). | [`builder.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/graph/builder.py)<br/>[`dedup.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/graph/dedup.py)<br/>[`communities.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/graph/communities.py)<br/>[`storage.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/graph/storage.py)<br/>[`vector_store.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/graph/vector_store.py)<br/>[`schema.sql`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/graph/schema.sql) |
| **`driftgraph.summarize`**| Hierarchical community Map-Reduce summarizer generating structured thematic reports with emergent findings. | [`map_reduce.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/summarize/map_reduce.py)<br/>[`prompts.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/summarize/prompts.py)<br/>[`models.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/summarize/models.py) |
| **`driftgraph.query`** | Intelligent Query Router, Global GraphRAG search over Leiden community reports, Local hybrid search combining FAISS and FTS5 via Reciprocal Rank Fusion, unified engine orchestrator. | [`router.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/query/router.py)<br/>[`global_search.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/query/global_search.py)<br/>[`local.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/query/local.py)<br/>[`engine.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/query/engine.py)<br/>[`models.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/query/models.py) |
| **`driftgraph.analytics`**| Graph Intelligence Studio: topological vital stats (density, modularity, connectivity), God Nodes (hub centrality), emergent boundary inquiry questions, surprising cross-community bridges, 2-hop Path Explorer ("What connects X to Y?"). | [`graph_analytics.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/analytics/graph_analytics.py)<br/>[`models.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/analytics/models.py) |
| **`driftgraph.classifier`**| 100% offline rule-based text taxonomy classifier across 6 specialized domains (Legal, Financial, Technical, HR/Admin, Academic, Medical) with diagnostic terminal and ASCII report generation. | [`rule_based.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/classifier/rule_based.py)<br/>[`models.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/classifier/models.py) |
| **`driftgraph.sources`** | Ingestion source adapters: structured note template instantiation (`Meeting`, `Concept`, `Literature`) and web article scraper with auto-tagging. | [`templates.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/sources/templates.py)<br/>[`web_scraper.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/sources/web_scraper.py) |
| **`driftgraph.voice`** | Voice Assistant RAG: ElevenLabs TTS streaming, Microsoft VibeVoice integration, conversation session memory, quick-answer direct graph lookup. | [`router.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/voice/router.py)<br/>[`memory.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/voice/memory.py)<br/>[`models.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/voice/models.py) |
| **`driftgraph.eval`** | System performance profiler (`psutil` RAM RSS, latency ms), embedding ablation harness (SBERT vs Word2Vec), RAGAS/TruLens metric evaluation. | [`benchmark.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/eval/benchmark.py)<br/>[`ablation.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/eval/ablation.py)<br/>[`ragas_metrics.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/eval/ragas_metrics.py)<br/>[`models.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/eval/models.py) |
| **`driftgraph.serve`** | FastAPI application factory, CORS and static frontend mounting, REST routing for ingestion, query, graph topology, analytics, classifier, notes, voice, and exports. | [`app.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/serve/app.py)<br/>[`routes/`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/serve/routes) |
| **`frontend`** | Interactive 2-pane IDE split workbench, Cytoscape.js force-directed canvas with ResizeObserver, real-time sidebar note search with autocomplete dropdown, draggable resizers with window drag-shields, modal card gallery, OCR studio, classifier studio. | [`frontend/index.html`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/frontend/index.html) |
| **`driftgraph.main`** | Unified CLI entrypoint supporting commands: `build`, `serve`, `query`, `ablation`. | [`main.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/main.py) |

---

## 4. Technologies, Runtime Stack, & Hard System Constraints

### 4.1 Technology Stack Matrix

| Technology | Layer | Role in DriftGraph | Rationale & Selection Criteria |
| :--- | :--- | :--- | :--- |
| **Python 3.11+** | Backend Runtime | Core pipeline and API execution | Native async/await event loops, typing support, and dominant NLP ecosystem. |
| **FastAPI + Uvicorn** | Web Framework | Asynchronous REST backend & static serving | Sub-millisecond latency, automatic OpenAPI schemas, native async I/O. |
| **Sentence-Transformers** | NLP Embeddings | Dense vector embeddings (`all-MiniLM-L6-v2`) | 384 dimensions, CPU-only execution, <100MB RAM footprint, high semantic relatedness correlation. |
| **Gensim** | NLP Baseline | Word2Vec continuous bag-of-words / skip-gram | Rigorous research baseline for embedding ablation comparisons. |
| **Ollama** | LLM Engine | On-device quantized inference (`llama3.1:8b`) | Fully offline, zero API fees, local data residency, GGUF/4-bit quantization efficiency. |
| **NetworkX** | Graph Topology | In-memory `MultiDiGraph` assembly & traversal | Native Python, fast graph algorithms, zero external graph DB installation. |
| **Leidenalg / Louvain** | Graph Clustering | Hierarchical community partitioning | Optimal modularity, avoids disconnected communities common in Louvain. |
| **SQLite + FTS5** | Storage & Lexical | Relational persistence + BM25 keyword search | Zero-configuration single-file database (`driftgraph.db`), ACID compliant, sub-ms FTS5 search. |
| **FAISS (`faiss-cpu`)** | Vector Index | In-memory inner-product vector store | Exact cosine search (`IndexFlatIP`), zero GPU requirement, instant disk serialization. |
| **Cytoscape.js** | Graph UI | Browser force-directed visualization | CSS-like graph stylesheet, compound community nodes, CoSE physics simulation. |
| **ElevenLabs / VibeVoice**| Voice Layer | Text-to-Speech & streaming voice assistant | Graph-grounded audible answers with conversational session memory. |
| **Tesseract OCR** | Document Ingest | Optical character recognition on scanned docs | Multi-engine layout preservation, table extraction, and confidence scoring. |
| **psutil** | Evaluation | Memory (RSS) & latency benchmarking | Exact hardware footprint accounting across all pipeline stages. |

---

### 4.2 Non-Negotiable Coding Rules & Invariants for Agents

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          AGENT CODING INVARIANTS                                 │
├─────────────────────────┬────────────────────────────┬───────────────────────────┤
│    Local-First / CPU    │     Asynchronous I/O       │    Pydantic v2 Syntax     │
│ Core pipeline must run  │ All network, database, and │ Use model_dump(),         │
│ on consumer CPUs with   │ Ollama calls must use      │ model_validate(). Never   │
│ <100MB embedding RAM.   │ async/await patterns.      │ use deprecated v1 dict(). │
├─────────────────────────┼────────────────────────────┼───────────────────────────┤
│    SQLite FTS5 Sync     │    2-Pane Flexbox UI       │  ResizeObserver Canvas    │
│ Keep relational tables  │ Never insert a 3rd column  │ Always observe canvas wrap│
│ and FTS5 virtual tables │ into .app-body. Modals     │ and call cy.resize()      │
│ strictly synchronized.  │ handle extra dashboards.   │ on container adjustments. │
└─────────────────────────┴────────────────────────────┴───────────────────────────┘
```

1. **Local-First & CPU Viability**: Core pipeline stages (chunking, vectorization, graph construction, community detection, local search) must execute entirely on CPU without requiring an external GPU or remote cloud services. Memory allocation for the embedding model must stay below 100 MB RAM. Total pipeline execution should comfortably operate within 4 GB–8 GB system RAM.
2. **Asynchronous Execution Pattern**: All FastAPI endpoints, SQLite database operations (`aiosqlite`), file I/O operations (`aiofiles`), and Ollama client calls must be strictly non-blocking using Python's `async`/`await` pattern.
3. **Strict Pydantic v2 Compliance**: All data models, API payloads, and config schemas must use modern Pydantic v2 idioms:
   - Use `model.model_dump()` (never `.dict()`).
   - Use `model.model_validate()` (never `.parse_obj()`).
   - Use `Field(default=..., description=...)` for metadata.
4. **SQLite FTS5 Synchronization**: Any create, update, or delete operation affecting `notes` or `chunks` must execute atomic synchronization against the FTS5 virtual tables (`chunks_fts`, `communities_fts`). Orphaned FTS5 entries corrupt hybrid search ranking.
5. **Frontend Workspace Layout Rules**:
   - The main workspace (`.app-body`) is strictly a **2-pane Flexbox layout**:
     $$\text{[ Editor Sidebar } \mid \text{ Vertical Resizer } \mid \text{ Graph Canvas ]}$$
   - Never insert a persistent 3rd horizontal column into `.app-body`. Auxiliary features (Notes gallery, OCR Studio, Classifier Studio, Graph Intelligence) must open in slide-out drawers or modal sheets (`.modal`).
   - `.split-graph` must have `flex: 1; width: 100%; min-width: 20%; overflow: hidden; height: 100%;`.
   - Cytoscape container must be observed by a native `ResizeObserver` on `.graph-canvas-wrap` to automatically trigger `window.cy.resize()` on split-divider or window adjustments.
   - Resizer dividers (`#splitDivider`, `#horizontalSplitDivider`) must bind drag listeners to `window`/`document` and toggle `.drag-shield` to prevent canvas event capture during mouse/touch dragging.

---

## 5. Visual Graph Architecture: Requirements Profile & Evaluation Framework

A vital requirement of DriftGraph is presenting personal knowledge as a living, explorable web where notes "drift" into clusters. Below is the comprehensive evaluation framework and comparative scorecard across five leading graph visualization architectures.

### 5.1 Visual Graph Requirements Profile for DriftGraph

1. **Scale & Node Capacity**:
   - *Target Range*: 100 to 5,000 entities/nodes and 200 to 15,000 edges for personal knowledge bases.
   - *Upper Bound / Stress Target*: Fluid interactivity up to 20,000 nodes for power users or multi-year digital archives.
2. **Hierarchical Community Representation**:
   - Must natively or semi-natively represent multi-scale hierarchies:
     - **Level 0 (Macro)**: Community clusters displayed as cohesive visual groups or compound parent boundaries.
     - **Level 1 (Micro)**: Granular concept nodes, entity attributes, and relationship edges.
   - Smooth semantic zoom transitions between macro-clusters and micro-entities.
3. **Graph Layout Physics & Ergonomics**:
   - Force-directed physics (spring forces for edges, electrostatic repulsion for nodes) with cluster cohesion forces.
   - Fast stabilization (under 2 seconds for 1,000 nodes) with worker-based physics to avoid freezing the browser UI thread.
4. **Interactive Inspections & Path Navigation**:
   - Click-to-focus: Neighborhood highlighting with dimming of unrelated nodes.
   - Path Explorer: Visual path highlighting across multi-hop chains ("What connects X to Y?").
   - Edge labels: Readable relation predicates that fade or declutter gracefully on zoom-out.
5. **Integration & Responsiveness**:
   - Zero-build or minimal static file delivery: Compatible with lightweight, self-contained serving from FastAPI.
   - Responsive container integration: Immediate redraw inside resizable split-pane containers via `ResizeObserver`.
   - Dynamic dark/light theme switching with instant color-scheme updates.

---

### 5.2 In-Depth Analysis of Candidate Architectures

#### Candidate 1: Cytoscape.js (Current Baseline)
- **Technology**: HTML5 Canvas (2D multi-layer canvas pipeline) + Web Worker physics.
- **Strengths**:
  - *Native Compound Nodes*: Out-of-the-box support for hierarchical parent-child nodes, making Level 0 Leiden community bounding boxes easy to represent.
  - *CSS-like Graph Stylesheet*: Declarative, clean styling syntax (`style: [ { selector: 'node[community=0]', style: { 'background-color': '#2FD9C4' } } ]`).
  - *Extensive Ecosystem*: Rich plugins for layouts (CoSE, Cola, Dagre, Concentric) and path-finding algorithms (Dijkstra, A*).
  - *Ease of Integration*: Standalone single-file bundle (`cytoscape.min.js`), zero build step required.
- **Weaknesses**:
  - *Scale Ceiling*: 2D Canvas rendering begins dropping frames below 60 FPS when element counts exceed 2,500–3,000 nodes.
  - *Physics Overhead*: The CoSE layout algorithm is computationally demanding on large graphs without aggressive worker offloading.
  - *No Native 3D/Particles*: Cannot produce 3D particle storm animations without external WebGL layers.

#### Candidate 2: Sigma.js v2 + Graphology
- **Technology**: WebGL (2D hardware-accelerated shaders) + Graphology data structures.
- **Strengths**:
  - *Unrivaled 2D Scalability*: Easily renders 10,000 to 100,000+ nodes and edges at a silky 60 FPS by offloading rendering to WebGL vertex and fragment shaders.
  - *Workerized Physics*: Built-in ForceAtlas2 layout runs seamlessly in dedicated Web Workers without stuttering user interaction.
  - *Memory Efficiency*: Graphology graph structures are optimized for minimal memory allocations.
- **Weaknesses**:
  - *Compound Node Limitations*: Lacks native nested compound nodes. Visualizing Leiden communities requires custom convex hull calculations or Voronoi overlay shaders.
  - *Styling Rigidity*: Programmatic shader-based styling is significantly less flexible than Cytoscape's CSS selectors.
  - *Build Tooling*: Modern Sigma v2 typically expects an npm/bundler workflow (esbuild/vite) rather than a trivial static script tag.

#### Candidate 3: 3D Force-Graph (Three.js / WebGL by Vasturiano)
- **Technology**: WebGL 3D (Three.js) + `d3-force-3d` physics simulation.
- **Strengths**:
  - *Literal "Drift" Visual Metaphor*: Stunning 3D particle clouds where notes fly through space and drift into galaxy-like community clusters.
  - *High Performance*: WebGL handles 10,000+ nodes with high frame rates.
  - *Cinematic Camera Navigation*: Smooth camera fly-to animations when inspecting nodes or tracing multi-hop paths.
  - *Particle Links*: Flowing directional particles along edges visually demonstrate relationship directionality and data flow.
- **Weaknesses**:
  - *Text Legibility & Clutter*: 3D text billboards can become unreadable and overlap in dense clusters without careful camera angles.
  - *Community Bounding Complexity*: Displaying hierarchical community boundaries in 3D requires rendering transparent volumetric bounding spheres or convex polyhedra.
  - *Workspace Density*: In a split-screen IDE workbench (where the graph shares screen width with a markdown editor), 3D camera controls can feel cumbersome compared to 2D pan/zoom.

#### Candidate 4: D3.js Force Simulation (`d3-force` + SVG/Canvas)
- **Technology**: SVG or Canvas 2D + D3 physics engine.
- **Strengths**:
  - *Ultimate Architectural Freedom*: Complete low-level control over custom force functions, collision radii, and visual encodings.
  - *Convex Community Hulls*: Simple computation of SVG convex hulls (`d3.polygonHull`) around Leiden community nodes.
  - *Industry Ubiquity*: Deep documentation and massive open-source recipe repositories.
- **Weaknesses**:
  - *High Engineering Burden*: D3 is a visualization primitives library, not a graph application framework. Hit-testing, quadtrees, edge label positioning, dragging math, and level-of-detail zooming must be written by hand.
  - *SVG Bottleneck*: SVG DOM nodes collapse in performance past 500–800 nodes (Canvas D3 is faster but requires writing manual hit-detection quadtrees).

#### Candidate 5: AntV G6 v5 (Alibaba)
- **Technology**: Canvas 2D & WebGL hybrid engine.
- **Strengths**:
  - *Native "Combos"*: Built-in first-class support for hierarchical community clusters (Combos) that can expand, collapse, and exert combo-specific physics forces.
  - *Layout Richness*: Includes specialized algorithms like Combo Force, Fruchterman, ForceAtlas2, and Concentric out of the box.
  - *Modern Animations*: Rich state transitions (hover, select, active) with smooth interpolation.
- **Weaknesses**:
  - *Documentation Quirks*: Primarily maintained by the Ant Group with occasional documentation translation gaps.
  - *Bundle Weight*: Larger runtime footprint compared to Cytoscape or Sigma.

---

### 5.3 Comparative Evaluation Rubric

To provide an objective ranking, each visual architecture is evaluated across five weighted criteria reflecting DriftGraph's engineering requirements:

| Evaluation Criterion | Weight | Definition & Architectural Requirement |
| :--- | :---: | :--- |
| **1. Hierarchical & Community Support** | **25%** | Ability to visually represent multi-level Leiden communities (nested hulls, compound nodes, or combo clusters) with semantic zoom between Level 0 and Level 1. |
| **2. Integration Simplicity & Local Serving** | **20%** | Zero-build static browser delivery, ease of styling, integration with FastAPI, and fluid behavior inside resizable CSS Flexbox splits via `ResizeObserver`. |
| **3. Interactive Ergonomics & Path Tracing** | **20%** | Built-in neighborhood focus, edge inspection, click handling, and visual multi-hop path exploration ("What connects X to Y?"). |
| **4. Rendering Scalability (1k–10k Nodes)** | **20%** | Frame rate stability (60 FPS), physics convergence speed, and CPU/GPU memory footprint under moderate to large personal note corpora. |
| **5. "Drift" Visual Metaphor & Aesthetic Polish** | **15%** | Organic visual feeling, particle animations, dynamic transitions, and modern dark-mode aesthetic appeal. |

---

### 5.4 Ranked Scorecard

Scores are rated on a scale of 1 to 10 (1 = Poor / Complex, 10 = Exceptional / Turnkey):

| Evaluation Dimension (Weight) | Cytoscape.js | Sigma.js v2 | 3D Force-Graph | D3.js (Force) | AntV G6 v5 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Community Hierarchy (25%)** | **9.0** | 5.5 | 6.0 | 7.5 | **9.5** |
| **2. Integration & Ergonomics (20%)** | **9.5** | 7.0 | 8.0 | 5.0 | 6.5 |
| **3. Interactive Path Tracing (20%)** | **9.5** | 7.5 | 8.0 | 6.0 | 8.5 |
| **4. Rendering Scalability (20%)** | 7.0 | **10.0** | **9.5** | 5.5 | 8.0 |
| **5. "Drift" Aesthetic Polish (15%)** | 8.0 | 8.0 | **10.0** | 7.5 | 8.5 |
| **Weighted Total Score (100%)** | **8.58 / 10** | **7.40 / 10** | **8.15 / 10** | **6.18 / 10** | **8.30 / 10** |
| **Overall Recommendation Rank** | **#1 (Primary 2D)** | **#4** | **#3 (Best Immersive)**| **#5** | **#2 (Runner-Up 2D)** |

---

### 5.5 Architectural Recommendations & Migration Path

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         VISUAL GRAPH STRATEGY                                    │
├────────────────────────────────────────┬─────────────────────────────────────────┤
│   Primary Engine: Cytoscape.js         │   Optional Horizon: 3D Force-Graph      │
├────────────────────────────────────────┼─────────────────────────────────────────┤
│ Retain Cytoscape.js for the core 2D    │ Provide an optional 3D WebGL            │
│ studio workspace. Its compound nodes,  │ particle view for whole-graph           │
│ CSS styling, and sub-second layout     │ presentations and immersive             │
│ convergence perfectly match personal   │ exploration, leveraging the existing    │
│ knowledge graphs (<3,000 nodes).       │ /api/graph Cytoscape JSON payload.      │
└────────────────────────────────────────┴─────────────────────────────────────────┘
```

1. **Retain Cytoscape.js for Core Studio Workspace (Rank #1)**:
   - For typical personal vaults (100–3,000 entities), Cytoscape.js is the superior choice. Its CSS stylesheet architecture, native compound nodes for Leiden communities, and rich event ecosystem provide the cleanest integration with zero build tooling.
2. **AntV G6 v5 as the Best 2D Alternative (Rank #2)**:
   - If DriftGraph expands into heavy enterprise vaults (5,000–20,000 nodes) requiring native nested community "Combos" and WebGL acceleration, AntV G6 v5 is the natural successor to Cytoscape.js.
3. **Dual-Mode 2D/3D Horizon (Rank #3 for Immersion)**:
   - DriftGraph's API endpoint [`/api/graph`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/serve/routes/graph.py) outputs standard Cytoscape elements `{ data: { id, label, community, ... } }`.
   - A secondary, full-screen **"Cosmic Drift" 3D View** (powered by `3d-force-graph` via a single `<script>` tag) can be added as a toggleable overlay without altering backend data structures.

---

## 6. Database Schemas, Storage DDL, & API Wire Protocols

### 6.1 Relational & Full-Text Search DDL ([`driftgraph/graph/schema.sql`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/graph/schema.sql))

```sql
-- 1. Notes Master Table
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    raw_content TEXT NOT NULL,
    cleaned_content TEXT NOT NULL,
    frontmatter_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Semantic Chunks Table
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Extracted Knowledge Graph Nodes
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'CONCEPT',
    description TEXT,
    community_id INTEGER DEFAULT 0,
    degree INTEGER DEFAULT 0,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Extracted Knowledge Graph Edges
CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    predicate TEXT NOT NULL,
    description TEXT,
    weight REAL DEFAULT 1.0,
    provenance_chunk_ids TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Hierarchical Leiden Communities
CREATE TABLE IF NOT EXISTS communities (
    id INTEGER PRIMARY KEY,
    level INTEGER NOT NULL DEFAULT 0,
    parent_id INTEGER,
    name TEXT NOT NULL,
    summary TEXT,
    findings_json TEXT,
    node_ids_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Full-Text Search Virtual Tables (FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    id UNINDEXED,
    note_id UNINDEXED,
    text,
    tokenize = 'porter'
);

CREATE VIRTUAL TABLE IF NOT EXISTS communities_fts USING fts5(
    id UNINDEXED,
    name,
    summary,
    tokenize = 'porter'
);
```

---

### 6.2 REST API Specification

| HTTP Method | Route Endpoint | Purpose & Description | Payload / Query Parameters | Response Format |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/ingest` | Triggers markdown re-chunking and graph pipeline rebuild. | `{"rebuild": true, "notes_dir": "./data/notes"}` | `{"status": "ok", "nodes_count": int, "edges_count": int}` |
| `POST` | `/api/query` | Executes intelligent dual-mode question answering. | `{"query": str, "mode": "auto"\|"global"\|"local", "top_k": 5}` | `{"answer": str, "mode": str, "citations": [...]}` |
| `GET` | `/api/graph` | Returns nodes and edges formatted for Cytoscape.js. | `?level=1` | `[{"data": {"id": str, "label": str, "community": int, ...}}]` |
| `GET` | `/api/graph/stats`| Returns node count, edge count, and community metrics. | *None* | `{"node_count": int, "edge_count": int, "community_count": int}` |
| `GET` | `/api/graph/communities` | Retrieves Leiden community summaries and findings. | *None* | `[{"id": int, "name": str, "summary": str, "findings": [...]}]` |
| `GET` | `/api/graph/analytics` | Graph Intelligence: God Nodes, boundary questions, bridges. | *None* | `{"god_nodes": [...], "suggested_questions": [...], "bridges": [...]}` |
| `POST` | `/api/graph/path` | Traces 2-hop navigation path between any two concepts. | `{"source": str, "target": str}` | `{"found": bool, "path": [...], "explanation": str}` |
| `POST` | `/api/classify` | 100% offline rule-based text taxonomy classifier. | `{"text": str}` | `{"top_category": str, "scores": {...}, "ascii_box": str}` |
| `POST` | `/api/ocr/upload`| Multi-engine document OCR upload with layout analysis. | `multipart/form-data` (file: PDF/image) | `{"text": str, "confidence": float, "tables": [...], "errors": [...]}` |
| `GET` | `/api/notes` | Lists all indexed notes with tags and previews. | *None* | `[{"id": str, "title": str, "word_count": int, "tags": [...]}]` |
| `GET` | `/api/notes/{id}` | Retrieves raw content of a specific note. | *Path parameter* | `{"id": str, "title": str, "content": str}` |
| `DELETE` | `/api/notes/{id}` | Deletes a note and clears associated chunks. | *Path parameter* | `{"status": "deleted", "id": str}` |
| `GET` | `/api/export/{fmt}`| Exports graph in `json`, RDF `turtle` (`.ttl`), or `jsonld`. | *Path parameter* | Raw text / JSON attachment |
| `POST` | `/api/voice/ask` | Voice query endpoint returning synthesized answer & audio. | `{"query": str, "quick_mode": bool}` | `{"answer": str, "audio_url": str, "session_id": str}` |

---

## 7. Developer & Coding Agent Playbook (Extension Recipes)

When modifying or expanding DriftGraph, follow these concrete operational patterns:

### Recipe 1: Adding a New REST Route
1. Define request and response schemas in `driftgraph/<subsystem>/models.py` using Pydantic v2.
2. Implement route handler in a module under [`driftgraph/serve/routes/`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/serve/routes/).
3. Include the router in [`driftgraph/serve/app.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/serve/app.py) using `app.include_router(new_router, prefix="/api")`.
4. Add automated unit test in `tests/test_api.py`.

### Recipe 2: Adding a New Extraction Entity Type or Prompt
1. Update `ENTITY_TYPES` list in [`driftgraph/extract/prompts.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/extract/prompts.py).
2. Modify few-shot JSON example in `EXTRACTION_SYSTEM_PROMPT`.
3. Add regex pattern rule in [`driftgraph/extract/parser.py`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/driftgraph/extract/parser.py) for fallback resilience.
4. Update entity color encoding in Cytoscape stylesheets in [`frontend/index.html`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/frontend/index.html).

### Recipe 3: Adding a New Frontend Modal or Action
1. Add modal structure under `<!-- MODALS -->` in [`frontend/index.html`](file:///home/tejas/Documents/College%20Files/DriftGraph/AGY/Project%20Map/frontend/index.html) following the standard pattern:
   ```html
   <div class="modal" id="modalCustom">
     <div class="modal-backdrop" data-close="modalCustom"></div>
     <div class="modal-sheet">
       <div class="modal-head">
         <h2 class="modal-title">Custom Tool</h2>
         <button class="close-btn" data-close="modalCustom">✕</button>
       </div>
       <div class="modal-body">...</div>
     </div>
   </div>
   ```
2. Trigger modal opening using helper `openModal("modalCustom")`.
3. Never append floating sidebars into `.app-body`—preserve the 2-pane workbench layout.

---

## 8. Verification & CLI Operations Reference

### 8.1 Primary CLI Commands
```bash
# 1. Rebuild knowledge graph from Markdown notes folder
python -m driftgraph.main build --notes ./data/notes

# 2. Query the knowledge graph from terminal
python -m driftgraph.main query "What are the core research themes?" --mode global
python -m driftgraph.main query "What is Project Alpha?" --mode local

# 3. Launch FastAPI backend and serve static frontend (http://localhost:8000)
python -m driftgraph.main serve --host 0.0.0.0 --port 8000

# 4. Run SBERT vs Word2Vec embedding ablation study
python -m driftgraph.main ablation --notes ./data/notes
```

### 8.2 Test Suite Execution
DriftGraph uses `pytest` with `pytest-asyncio`. Run all tests using `uv`:
```bash
/home/tejas/.local/bin/uv run pytest
```
Current test suite status: **56 tests passing across all ingestion, embedding, extraction, graph, OCR, query, and API suites.**
