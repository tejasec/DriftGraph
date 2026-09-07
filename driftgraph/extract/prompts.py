"""
Structured prompt templates for Knowledge Graph extraction.
"""

ENTITY_RELATION_SYSTEM_PROMPT = """You are an expert knowledge graph architect.
Your task is to extract meaningful entities and directed relations from the given text passage.

GUIDELINES:
1. Identify key entities: Concepts, Technologies, People, Organizations, Locations, Events, Artifacts.
2. Identify directed relationships between these entities in the form: (subject, predicate, object).
3. Normalize entity names (e.g., use "FastAPI" rather than "fastapi backend framework").
4. Output MUST be valid JSON conforming strictly to the requested schema.

OUTPUT JSON SCHEMA:
{
  "entities": [
    {
      "name": "Entity Name",
      "type": "CONCEPT | PERSON | ORGANIZATION | TECHNOLOGY | ARTIFACT | TOPIC",
      "description": "Brief description of what this entity is in context"
    }
  ],
  "relations": [
    {
      "subject": "Entity A",
      "predicate": "USES | CREATED_BY | IMPLEMENTS | PART_OF | RELATES_TO | MAINTAINS | DISCUSSES",
      "object": "Entity B",
      "description": "Brief context about the relationship"
    }
  ]
}
"""

EXTRACTION_USER_PROMPT_TEMPLATE = """Extract entities and relations from the following text chunk:

---
{text}
---

Return ONLY JSON. Do not include markdown code blocks or any explanation outside JSON."""
