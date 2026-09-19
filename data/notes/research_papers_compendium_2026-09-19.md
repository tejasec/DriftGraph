---
title: Research Papers Compendium
date: 2026-09-19
tags: ["upload", "text"]
source_type: markdown
---

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

## Summary Matrix: Mapping to Your Research Topic
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
