"""
Entity resolution and deduplication logic.
"""

from typing import List, Dict, Tuple, Set
import re
import difflib
from driftgraph.extract.models import Entity, Relation


def normalize_entity_name(name: str) -> str:
    """Canonical normalization: lowercase, strip punctuation and extra spaces."""
    cleaned = re.sub(r"[^\w\s\-]", "", name).strip().lower()
    return re.sub(r"\s+", " ", cleaned)


class EntityDeduplicator:
    """Merges and canonicalizes extracted entities and re-links relations."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def deduplicate(
        self,
        entities: List[Entity],
        relations: List[Relation]
    ) -> Tuple[List[Entity], List[Relation]]:
        """Deduplicate entities based on normalized names and string similarity."""
        canonical_map: Dict[str, Entity] = {}
        alias_to_canonical: Dict[str, str] = {}

        for ent in entities:
            norm_name = normalize_entity_name(ent.name)
            if not norm_name:
                continue

            # Check if there is an exact or fuzzy match in existing canonical entities
            matched_canonical = None
            if norm_name in canonical_map:
                matched_canonical = norm_name
            else:
                for existing_norm in canonical_map:
                    sim = difflib.SequenceMatcher(None, norm_name, existing_norm).ratio()
                    if sim >= self.similarity_threshold:
                        matched_canonical = existing_norm
                        break

            if matched_canonical:
                # Merge into existing canonical entity
                existing_ent = canonical_map[matched_canonical]
                alias_to_canonical[ent.name] = existing_ent.name
                alias_to_canonical[norm_name] = existing_ent.name
                # Prefer more detailed description and higher confidence
                if ent.description and (not existing_ent.description or len(ent.description) > len(existing_ent.description)):
                    existing_ent.description = ent.description
                existing_ent.confidence = max(existing_ent.confidence, ent.confidence)
            else:
                # Register new canonical entity
                canonical_map[norm_name] = Entity(
                    name=ent.name.strip(),
                    type=ent.type,
                    description=ent.description,
                    source_chunk_id=ent.source_chunk_id,
                    confidence=ent.confidence
                )
                alias_to_canonical[ent.name] = ent.name.strip()
                alias_to_canonical[norm_name] = ent.name.strip()

        deduped_entities = list(canonical_map.values())

        # Update relations to point to canonical entity names and remove duplicates
        seen_relations: Set[Tuple[str, str, str]] = set()
        deduped_relations: List[Relation] = []

        for rel in relations:
            norm_subj = normalize_entity_name(rel.subject)
            norm_obj = normalize_entity_name(rel.object)

            canon_subj = alias_to_canonical.get(rel.subject, alias_to_canonical.get(norm_subj, rel.subject.strip()))
            canon_obj = alias_to_canonical.get(rel.object, alias_to_canonical.get(norm_obj, rel.object.strip()))

            # Ignore self-loops
            if canon_subj.lower() == canon_obj.lower():
                continue

            rel_key = (canon_subj.lower(), rel.predicate.upper(), canon_obj.lower())
            if rel_key not in seen_relations:
                seen_relations.add(rel_key)
                deduped_relations.append(Relation(
                    subject=canon_subj,
                    predicate=rel.predicate.upper(),
                    object=canon_obj,
                    description=rel.description,
                    confidence=rel.confidence,
                    source_chunk_id=rel.source_chunk_id
                ))

        return deduped_entities, deduped_relations
