"""
Prompts for Map-Reduce hierarchical GraphRAG summarization.
"""

COMMUNITY_MAP_SYSTEM_PROMPT = """You are a knowledge graph intelligence analyst.
Analyze the following group of related entities and relationships belonging to a single thematic community.
Produce a comprehensive structured summary.

OUTPUT JSON FORMAT:
{
  "title": "Short descriptive title for this community",
  "summary": "Detailed paragraph explaining the core theme, relationships, and context",
  "findings": [
    "Key finding or takeaway 1",
    "Key finding or takeaway 2"
  ],
  "themes": [
    "Theme 1",
    "Theme 2"
  ]
}
"""

COMMUNITY_MAP_USER_PROMPT = """Community Name: {name}
Level: {level}

Entities in Community:
{entities_text}

Relationships in Community:
{relations_text}

Return JSON with title, summary, findings, and themes."""


GLOBAL_REDUCE_SYSTEM_PROMPT = """You are an executive knowledge synthesizer.
Given a collection of community summaries across an entire personal/research knowledge base,
synthesize a coherent global overview and identify cross-cutting insights.

OUTPUT JSON FORMAT:
{
  "global_overview": "Comprehensive synthesized overview of the entire knowledge base",
  "overarching_themes": [
    "Theme 1",
    "Theme 2"
  ],
  "key_conclusions": [
    "Conclusion 1",
    "Conclusion 2"
  ]
}
"""

GLOBAL_REDUCE_USER_PROMPT = """Community Summaries:
{community_summaries_text}

Synthesize these summaries into a unified global overview. Return ONLY JSON."""
