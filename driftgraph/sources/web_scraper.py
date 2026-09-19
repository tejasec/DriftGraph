"""driftgraph/sources/web_scraper.py

Web scraping & article extraction module:
- Ingests web pages into clean Markdown notes with metadata provenance
- Extracts titles, main article content, headings, and paragraph text
- Strips script, style, nav, and advertisement tags
"""

from __future__ import annotations

import asyncio
import re
from datetime import date
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import httpx
import structlog

from driftgraph.config import config
from driftgraph.classifier.rule_based import DocumentClassifier

logger = structlog.get_logger(__name__)


def clean_html_to_markdown(html_text: str) -> Tuple[str, str]:
    """
    Extract title and convert core HTML elements into clean Markdown.
    Returns (title, markdown_content).
    """
    # 1. Extract Title
    title_match = re.search(r"<title>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Web Article"
    # Clean HTML entities
    title = re.sub(r"&[a-zA-Z0-9#]+;", " ", title).strip()

    # 2. Strip scripts, styles, iframes, navs, footers, headers
    cleaned = re.sub(r"<(script|style|nav|footer|header|iframe|noscript)[^>]*>.*?</\1>", "", html_text, flags=re.IGNORECASE | re.DOTALL)

    # 3. Convert headings
    cleaned = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", cleaned, flags=re.IGNORECASE | re.DOTALL)

    # 4. Convert paragraphs & breaks
    cleaned = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)

    # 5. Convert list items
    cleaned = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", cleaned, flags=re.IGNORECASE | re.DOTALL)

    # 6. Convert strong/em
    cleaned = re.sub(r"<(strong|b)[^>]*>(.*?)</\1>", r"**\2**", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<(em|i)[^>]*>(.*?)</\1>", r"*\2*", cleaned, flags=re.IGNORECASE | re.DOTALL)

    # 7. Strip all remaining HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)

    # 8. Normalize whitespace
    lines = [line.strip() for line in cleaned.splitlines()]
    non_empty = [line for line in lines if line]
    markdown_body = "\n\n".join(non_empty)

    return title, markdown_body


async def scrape_and_create_note(
    url: str,
    custom_title: Optional[str] = None,
    auto_classify: bool = True
) -> Dict[str, Any]:
    """
    Fetch a web page, extract readable article text, and save as a markdown note.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 DriftGraph/1.0"
    }

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html_content = resp.text

    extracted_title, body = clean_html_to_markdown(html_content)
    final_title = (custom_title or "").strip() or extracted_title

    tags = ["web", "scraped"]
    top_cat = None
    if auto_classify:
        classifier = DocumentClassifier()
        cls_res = classifier.classify_text(body, filename=f"{final_title}.html")
        top_cat = cls_res.top_category
        tags.extend(cls_res.auto_tags[:3])

    today_iso = date.today().isoformat()
    clean_stem = re.sub(r"[^\w\s-]", "", final_title).strip().lower()
    clean_stem = re.sub(r"\s+", "_", clean_stem)[:40] or "web_article"

    notes_dir = Path(config.paths.notes_dir)
    notes_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{clean_stem}_{today_iso}.md"
    note_path = notes_dir / filename

    md_content = (
        "---\n"
        f"title: \"{final_title.replace(chr(34), '')}\"\n"
        f"date: {today_iso}\n"
        f"source_url: \"{url}\"\n"
        f"source_type: web\n"
        f"tags: {tags}\n"
        "---\n\n"
        f"# {final_title}\n\n"
        f"**Source**: [{url}]({url})\n\n"
        f"{body}\n"
    )

    await asyncio.to_thread(note_path.write_text, md_content, encoding="utf-8")
    note_id = note_path.stem.lower().replace(" ", "_")

    return {
        "id": note_id,
        "filename": filename,
        "title": final_title,
        "source_url": url,
        "tags": tags,
        "top_category": top_cat,
        "word_count": len(body.split()),
        "message": f"Successfully ingested web article into {filename}",
    }
