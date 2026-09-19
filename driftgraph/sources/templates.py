"""driftgraph/sources/templates.py

Template system for saving and reusing common structured note formats:
- Meeting Notes
- Research Paper Analysis
- Concept Definition
- Daily Reflection Log
- Literature Reference Note
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel


class NoteTemplate(BaseModel):
    id: str
    name: str
    description: str
    category: str
    tags: List[str]
    markdown_scaffold: str


TEMPLATES: Dict[str, NoteTemplate] = {
    "meeting": NoteTemplate(
        id="meeting",
        name="Meeting Notes",
        description="Structured format for team discussions, decisions, and action items.",
        category="Workplace",
        tags=["meeting", "work", "action_items"],
        markdown_scaffold="""# Meeting: {title}

**Date**: {date}
**Attendees**: {attendees}

## Objective
Brief summary of why this meeting took place.

## Discussion & Agenda
- Topic 1: Discussion points...
- Topic 2: Discussion points...

## Key Decisions
- [x] Decision 1: Details...

## Action Items
- [ ] @assignee: Deliverable by [deadline]
"""
    ),
    "research": NoteTemplate(
        id="research",
        name="Research Paper Summary",
        description="Comprehensive framework for academic literature analysis.",
        category="Academic",
        tags=["research", "paper", "literature"],
        markdown_scaffold="""# Paper: {title}

**Authors**: {authors}
**Publication**: {publication} ({date})

## Abstract & Core Thesis
High-level summary of the paper's core hypothesis.

## Methodology & Architecture
- Data collection & benchmark dataset
- Model architecture / experimental setup

## Key Findings & Empirical Results
- Finding 1: Results and metrics...
- Finding 2: Ablation comparisons...

## Critical Assessment & Limitations
- Weaknesses or constraints identified in the methodology...

## Open Questions & Future Work
- Follow-up research questions...
"""
    ),
    "concept": NoteTemplate(
        id="concept",
        name="Concept Definition",
        description="Deep dive concept definition with examples and relational linking.",
        category="Knowledge",
        tags=["concept", "definition", "foundations"],
        markdown_scaffold="""# Concept: {title}

## Formal Definition
Precise definition and mathematical or theoretical formulation.

## Key Principles & Components
1. **Component A**: Role and significance.
2. **Component B**: Role and significance.

## Real-World Examples
- *Example 1*: Concrete implementation or case study.

## Interconnections & Contrasts
- Closely related to: [[RelatedConcept]]
- Contrasts with: [[OpposingConcept]]
"""
    ),
    "daily_log": NoteTemplate(
        id="daily_log",
        name="Daily Reflection Log",
        description="Daily progress log, discoveries, breakthroughs, and blockers.",
        category="Personal",
        tags=["daily", "reflection", "journal"],
        markdown_scaffold="""# Daily Log: {date}

## Today's Core Focus
- Main priority achieved today...

## Discoveries & Breakthroughs
- Insight 1: What did I learn today?
- Insight 2: New connections formed...

## Progress & Completed Tasks
- [x] Completed task 1
- [x] Completed task 2

## Blockers & Next Actions
- [ ] Tomorrow's priority...
"""
    ),
    "literature": NoteTemplate(
        id="literature",
        name="Literature Reference Note",
        description="Note tracking reference citations and key takeaways from books or articles.",
        category="Reference",
        tags=["literature", "citation", "reference"],
        markdown_scaffold="""# Literature Note: {title}

**Source**: {source}
**Author**: {author}

## Summary of Arguments
Core takeaways from the source material.

## Notable Quotations
> "Direct memorable quote from the text."

## Personal Synthesis & Applications
How does this apply to my current projects and knowledge graph?
"""
    )
}


def list_templates() -> List[NoteTemplate]:
    """Return all available note templates."""
    return list(TEMPLATES.values())


def get_template(template_id: str) -> Optional[NoteTemplate]:
    """Retrieve a template by its ID."""
    return TEMPLATES.get(template_id)


def render_template(template_id: str, values: Dict[str, str]) -> str:
    """Populate template scaffold with provided values."""
    tpl = TEMPLATES.get(template_id)
    if not tpl:
        raise ValueError(f"Template '{template_id}' not found.")

    scaffold = tpl.markdown_scaffold
    for key, val in values.items():
        scaffold = scaffold.replace(f"{{{key}}}", val)

    # Clean any remaining placeholders
    import re
    scaffold = re.sub(r"\{[a-zA-Z0-9_]+\}", "...", scaffold)
    return scaffold
