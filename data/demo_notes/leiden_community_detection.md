---
title: "Hierarchical Leiden Community Detection"
tags: [leiden, graph-algorithms, communities, clustering]
---

# Hierarchical Leiden Community Detection

Graph partition algorithms group strongly interconnected nodes into modular semantic clusters, revealing the natural topic boundaries within personal notes.

## The Leiden Algorithm vs. Louvain

The Leiden algorithm improves upon traditional Louvain modularity optimization:
- **Connectedness Guarantee**: Leiden guarantees that all communities are well-connected and eliminates disconnected sub-communities.
- **Fast Convergence**: Multi-level refinement rapidly clusters graphs containing thousands of nodes and relations.
- **Resolution Tuning**: A tunable resolution parameter controls cluster granularity, producing hierarchical levels (from macro topics to micro sub-themes).

## Knowledge Graph Synthesis

In DriftGraph, Leiden communities partition the NetworkX knowledge graph. Each community is assigned a color palette and summarized using map-reduce LLM prompts.
