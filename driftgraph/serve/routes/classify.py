"""driftgraph/serve/routes/classify.py

API routes for rule-based, fully offline text extraction & document classification.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from driftgraph.config import config
from driftgraph.classifier.models import ClassificationResult
from driftgraph.classifier.rule_based import DocumentClassifier

router = APIRouter(prefix="/api/classify", tags=["Classification"])

_classifier = DocumentClassifier()


class ClassifyTextRequest(BaseModel):
    text: str
    filename: Optional[str] = "document.txt"


@router.post("", response_model=ClassificationResult)
async def classify_text(req: ClassifyTextRequest):
    """Classify text using the rule-based, fully offline classifier."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    return _classifier.classify_text(req.text, filename=req.filename or "document.txt")


@router.post("/file", response_model=ClassificationResult)
async def classify_file(file: UploadFile = File(...)):
    """Extract text from an uploaded file and classify it."""
    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Try utf-8 decoding or fallback
    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = content_bytes.decode("latin-1", errors="ignore")

    return _classifier.classify_text(text, filename=file.filename or "uploaded_doc.txt")


@router.post("/note/{note_id}", response_model=ClassificationResult)
async def classify_saved_note(note_id: str, update_tags: bool = False):
    """Classify an existing note in notes_dir by its note_id."""
    notes_dir = Path(config.paths.notes_dir)
    target_file = None
    for p in notes_dir.glob("*.md"):
        if p.stem.lower().replace(" ", "_") == note_id.lower():
            target_file = p
            break

    if not target_file or not target_file.exists():
        raise HTTPException(status_code=404, detail=f"Note not found for ID: {note_id}")

    raw_content = target_file.read_text(encoding="utf-8")
    # Strip YAML frontmatter if present for text stats
    lines = raw_content.splitlines()
    body_lines = []
    in_fm = False
    for line in lines:
        if line.strip() == "---":
            in_fm = not in_fm
            continue
        if not in_fm:
            body_lines.append(line)

    body_text = "\n".join(body_lines)
    result = _classifier.classify_text(body_text, filename=target_file.name)

    if update_tags:
        # Append tags to frontmatter if desired
        tags_line = f"tags: {result.auto_tags}\n"
        if "tags:" in raw_content:
            import re
            updated = re.sub(r"tags:\s*\[.*?\]", f"tags: {result.auto_tags}", raw_content)
        else:
            updated = raw_content.replace("---\n", f"---\n{tags_line}", 1)
        target_file.write_text(updated, encoding="utf-8")

    return result
