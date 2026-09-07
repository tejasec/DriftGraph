"""
Markdown and frontmatter parser for DriftGraph.
"""

from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import re
import aiofiles
import frontmatter

from driftgraph.ingest.models import Note, NoteMetadata


def clean_frontmatter_fallback(content: str) -> Tuple[Dict[str, Any], str]:
    """Fallback frontmatter extractor using regex if python-frontmatter encounters issues."""
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(pattern, content, re.DOTALL)
    if match:
        meta_str = match.group(1)
        body = content[match.end():]
        metadata = {}
        for line in meta_str.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                metadata[key.strip()] = val.strip()
        return metadata, body
    return {}, content


def extract_title_fallback(body: str, filename: str) -> str:
    """Extract first H1 heading or use filename stem."""
    match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return Path(filename).stem


async def parse_markdown_file(file_path: Path) -> Optional[Note]:
    """Parse a single markdown file into a Note model."""
    if not file_path.exists() or not file_path.is_file():
        return None

    async with aiofiles.open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw_text = await f.read()

    try:
        post = frontmatter.loads(raw_text)
        metadata_dict = dict(post.metadata)
        body = post.content
    except Exception:
        metadata_dict, body = clean_frontmatter_fallback(raw_text)

    # Normalize tags
    tags = metadata_dict.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.strip("[]").split(",") if t.strip()]

    title = metadata_dict.get("title") or extract_title_fallback(body, file_path.name)
    date_val = str(metadata_dict.get("date", "")) if metadata_dict.get("date") else None

    metadata = NoteMetadata(
        title=title,
        tags=tags,
        date=date_val,
        source_file=str(file_path.resolve()),
        extra={k: v for k, v in metadata_dict.items() if k not in ["title", "tags", "date"]}
    )

    note_id = file_path.stem.lower().replace(" ", "_")

    return Note(
        id=note_id,
        content=body.strip(),
        raw_content=raw_text,
        metadata=metadata
    )


async def parse_markdown_directory(directory_path: str | Path) -> List[Note]:
    """Recursively discover and parse all markdown notes in a directory."""
    dir_p = Path(directory_path)
    if not dir_p.exists():
        return []

    notes: List[Note] = []
    # Match .md and .markdown
    files = list(dir_p.rglob("*.md")) + list(dir_p.rglob("*.markdown"))
    for file_p in sorted(files):
        note = await parse_markdown_file(file_p)
        if note and note.content:
            notes.append(note)

    return notes
