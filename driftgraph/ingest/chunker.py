"""
Chunking strategy for DriftGraph notes: sliding window with semantic sentence boundaries.
"""

from typing import List
import re
from driftgraph.ingest.models import Note, Chunk


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences while respecting abbreviations and code blocks."""
    # Split on periods, exclamation marks, question marks followed by whitespace or newline
    sentence_pattern = r"(?<=[.!?])\s+(?=[A-Z0-9#\-\*])|\n\n+"
    sentences = re.split(sentence_pattern, text)
    return [s.strip() for s in sentences if s and s.strip()]


def approximate_token_count(text: str) -> int:
    """Rough token estimation (words * 1.3 or whitespace split)."""
    words = text.split()
    return max(1, int(len(words) * 1.3))


def chunk_note(
    note: Note,
    target_tokens: int = 256,
    overlap_tokens: int = 40,
    min_tokens: int = 20
) -> List[Chunk]:
    """
    Split a note into overlapping chunks respecting sentence boundaries.
    """
    sentences = split_into_sentences(note.content)
    if not sentences:
        return []

    chunks: List[Chunk] = []
    current_sentences: List[str] = []
    current_token_count = 0
    chunk_index = 0

    for sent in sentences:
        sent_tokens = approximate_token_count(sent)

        # If adding sentence exceeds target and we already have some sentences
        if current_token_count + sent_tokens > target_tokens and current_sentences:
            chunk_text = " ".join(current_sentences).strip()
            if current_token_count >= min_tokens:
                start_char = note.content.find(chunk_text[:30]) if chunk_text else 0
                end_char = start_char + len(chunk_text) if start_char >= 0 else len(chunk_text)

                chunk = Chunk(
                    id=f"{note.id}_chunk_{chunk_index}",
                    note_id=note.id,
                    source_file=note.metadata.source_file,
                    chunk_index=chunk_index,
                    text=chunk_text,
                    start_char=max(0, start_char),
                    end_char=max(0, end_char),
                    token_count=current_token_count,
                    metadata={
                        "title": note.metadata.title,
                        "tags": note.metadata.tags,
                        "date": note.metadata.date,
                        "source_type": note.metadata.source_type,
                    }
                )
                chunks.append(chunk)
                chunk_index += 1

            # Retain overlap sentences
            overlap_count = 0
            overlap_sentences: List[str] = []
            for s in reversed(current_sentences):
                s_tokens = approximate_token_count(s)
                if overlap_count + s_tokens <= overlap_tokens:
                    overlap_sentences.insert(0, s)
                    overlap_count += s_tokens
                else:
                    break

            current_sentences = overlap_sentences
            current_token_count = sum(approximate_token_count(s) for s in current_sentences)

        current_sentences.append(sent)
        current_token_count += sent_tokens

    # Append remaining chunk
    if current_sentences:
        chunk_text = " ".join(current_sentences).strip()
        if chunk_text:
            start_char = note.content.find(chunk_text[:30]) if chunk_text else 0
            end_char = start_char + len(chunk_text) if start_char >= 0 else len(chunk_text)

            chunk = Chunk(
                id=f"{note.id}_chunk_{chunk_index}",
                note_id=note.id,
                source_file=note.metadata.source_file,
                chunk_index=chunk_index,
                text=chunk_text,
                start_char=max(0, start_char),
                end_char=max(0, end_char),
                token_count=approximate_token_count(chunk_text),
                metadata={
                    "title": note.metadata.title,
                    "tags": note.metadata.tags,
                    "date": note.metadata.date,
                    "source_type": note.metadata.source_type,
                }
            )
            chunks.append(chunk)

    return chunks


def chunk_notes(
    notes: List[Note],
    target_tokens: int = 256,
    overlap_tokens: int = 40
) -> List[Chunk]:
    """Chunk multiple notes into a flat list of Chunk objects."""
    all_chunks: List[Chunk] = []
    for note in notes:
        all_chunks.extend(chunk_note(note, target_tokens=target_tokens, overlap_tokens=overlap_tokens))
    return all_chunks
