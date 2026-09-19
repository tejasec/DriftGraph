"""
Parser for converting raw LLM JSON outputs into structured Entity and Relation models.
"""

import json
import re
from typing import List, Tuple, Dict, Any
import structlog
from driftgraph.extract.models import Entity, Relation, ExtractionResult

logger = structlog.get_logger(__name__)


def clean_json_text(text: str) -> str:
    """Strip markdown backticks, explanations, or trailing commas from LLM output."""
    text = text.strip()
    # Remove markdown code fence ```json ... ```
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Find the outermost JSON object { ... }
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        text = match.group(1)

    return text


def _safe_float(value: Any, default: float) -> float:
    """Coerce a value to float, falling back to default on non-numeric input."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_llm_extraction_response(
    raw_response: str,
    chunk_id: str
) -> ExtractionResult:
    """Parse JSON string into ExtractionResult."""
    cleaned = clean_json_text(raw_response)
    try:
        data = json.loads(cleaned)
    except Exception as e:
        logger.warning("failed_to_parse_llm_json_fallback_heuristic", error=str(e), raw=raw_response[:200])
        return fallback_heuristic_extraction(raw_response, chunk_id)

    if not isinstance(data, dict):
        logger.warning("llm_json_not_an_object_fallback_heuristic", raw=raw_response[:200])
        return fallback_heuristic_extraction(raw_response, chunk_id)

    entities: List[Entity] = []
    relations: List[Relation] = []

    for ent_data in data.get("entities", []):
        if isinstance(ent_data, dict) and ent_data.get("name"):
            entities.append(Entity(
                name=str(ent_data.get("name")).strip(),
                type=str(ent_data.get("type", "CONCEPT")).strip().upper(),
                description=str(ent_data.get("description", "")).strip() if ent_data.get("description") else None,
                source_chunk_id=chunk_id,
                confidence=_safe_float(ent_data.get("confidence"), 0.95)
            ))

    for rel_data in data.get("relations", []):
        if isinstance(rel_data, dict) and rel_data.get("subject") and rel_data.get("object"):
            relations.append(Relation(
                subject=str(rel_data.get("subject")).strip(),
                predicate=str(rel_data.get("predicate", "RELATES_TO")).strip().upper().replace(" ", "_"),
                object=str(rel_data.get("object")).strip(),
                description=str(rel_data.get("description", "")).strip() if rel_data.get("description") else None,
                source_chunk_id=chunk_id,
                confidence=_safe_float(rel_data.get("confidence"), 0.90)
            ))

    return ExtractionResult(chunk_id=chunk_id, entities=entities, relations=relations)


def fallback_heuristic_extraction(text: str, chunk_id: str) -> ExtractionResult:
    """
    Lightweight rule-based fallback entity/relation extractor.
    Extracts capitalized noun phrases and bold/code terms if Ollama is not running.
    """
    entities: Dict[str, Entity] = {}
    relations: List[Relation] = []

    # Extract bold terms **term** or `code`
    markup_terms = re.findall(r"\*\*([^*]+)\*\*|`([^`]+)`", text)
    for m in markup_terms:
        is_code = bool(m[1])
        term = (m[0] or m[1]).strip()
        if len(term) > 2 and len(term) < 50:
            entities[term.lower()] = Entity(
                name=term,
                type="TECHNOLOGY" if is_code else "CONCEPT",
                description=f"Extracted from {chunk_id}",
                source_chunk_id=chunk_id,
                confidence=0.8
            )

    # Capitalized multi-word named entities: e.g., "Alice Chen", "Project Alpha", "Sentence-BERT"
    cap_terms = re.findall(r"\b([A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)*)\b", text)
    for term in cap_terms:
        term = term.strip()
        if len(term) > 2 and term.lower() not in {"the", "this", "that", "there", "with", "from", "when"}:
            if term.lower() not in entities:
                ent_type = "PERSON" if len(term.split()) == 2 and not any(char.isdigit() for char in term) else "CONCEPT"
                entities[term.lower()] = Entity(
                    name=term,
                    type=ent_type,
                    description=f"Extracted entity from note chunk",
                    source_chunk_id=chunk_id,
                    confidence=0.75
                )

    ent_list = list(entities.values())
    # Link adjacent entities found in the chunk
    for i in range(len(ent_list) - 1):
        subj = ent_list[i].name
        obj = ent_list[i + 1].name
        if subj.lower() != obj.lower():
            relations.append(Relation(
                subject=subj,
                predicate="RELATES_TO",
                object=obj,
                description=f"Co-occurrence relationship in {chunk_id}",
                source_chunk_id=chunk_id,
                confidence=0.70
            ))

    return ExtractionResult(chunk_id=chunk_id, entities=ent_list, relations=relations)
