"""driftgraph/sources package"""

from driftgraph.sources.templates import (
    NoteTemplate,
    list_templates,
    get_template,
    render_template,
    TEMPLATES,
)
from driftgraph.sources.web_scraper import scrape_and_create_note, clean_html_to_markdown

__all__ = [
    "NoteTemplate",
    "list_templates",
    "get_template",
    "render_template",
    "TEMPLATES",
    "scrape_and_create_note",
    "clean_html_to_markdown",
]
