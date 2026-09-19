"""driftgraph/ingest/ocr_models.py

Data models for OCR document ingestion:
- Word and line text segments with confidence scores & bounding boxes
- Table structures with rows, columns, and Markdown representation
- Enhanced OCRPage with error markings and visual preview data
- OCROptions for engines, speed modes, and multi-language selection
- BatchOCRResult for multi-document processing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TextSegment:
    """An individual extracted text element (word, line, cell, heading)."""
    id: str
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, width, height) in pixels
    norm_bbox: Tuple[float, float, float, float]  # (norm_x, norm_y, norm_w, norm_h) in [0.0, 1.0]
    page_number: int
    is_error: bool = False
    error_reason: Optional[str] = None
    segment_type: str = "word"  # word, line, heading, list_item, table_cell


@dataclass
class TableStructure:
    """A detected table with rows, columns, and Markdown representation."""
    table_id: str
    page_number: int
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    markdown: str = ""
    html: str = ""


@dataclass
class OCRPage:
    """Represents a single processed page with text, confidence, segments, tables, and preview."""
    page_number: int
    text: str
    mean_confidence: float
    width: int
    height: int
    segments: List[TextSegment] = field(default_factory=list)
    tables: List[TableStructure] = field(default_factory=list)
    preview_image_base64: Optional[str] = None

    @property
    def error_segments(self) -> List[TextSegment]:
        """Return all segments marked as OCR errors or needing review."""
        return [s for s in self.segments if s.is_error]

    @property
    def high_confidence_count(self) -> int:
        return sum(1 for s in self.segments if s.confidence >= 80.0)

    @property
    def medium_confidence_count(self) -> int:
        return sum(1 for s in self.segments if 60.0 <= s.confidence < 80.0)

    @property
    def low_confidence_count(self) -> int:
        return sum(1 for s in self.segments if s.confidence < 60.0)


@dataclass
class OCROptions:
    """Execution options for OCR processing."""
    engine: str = "tesseract"  # tesseract, google_vision, local
    lang: str = "eng"
    psm: int = 6
    dpi: int = 300
    speed_mode: str = "balanced"  # fast, balanced, accurate
    min_confidence: float = 60.0
    error_confidence_threshold: float = 60.0
    preserve_tables: bool = True
    preserve_layout: bool = True
    generate_preview: bool = True
    google_vision_api_key: Optional[str] = None


@dataclass
class BatchOCRResult:
    """Aggregated results across multiple batch-processed documents."""
    total_documents: int
    successful_documents: int
    failed_documents: int
    total_pages: int
    mean_confidence: float
    total_errors_marked: int
    total_tables_detected: int
    documents: List[Dict[str, Any]] = field(default_factory=list)
