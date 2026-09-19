"""driftgraph/ingest/ocr.py

Comprehensive OCR ingestion adapter for DriftGraph:
- Multi-engine support: Tesseract, Google Vision, and Local Heuristic
- Multi-language selection with runtime language discovery
- Word & line text segments with confidence scores and normalized bounding boxes
- Visual result highlighting and error marking (< 60% confidence / artifacts)
- Table detection and Markdown table structure preservation
- Layout preservation (multi-column reading order, headings, lists)
- Configurable OCR speed modes: fast (150 DPI), balanced (300 DPI), accurate (350 DPI)
- Async execution with run_in_executor and content-hash caching
- Batch document processing for concurrent ingest
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Optional, List, Dict, Any

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from pypdf import PdfReader

from driftgraph.config import config as app_config
from driftgraph.ingest.models import Note, NoteMetadata
from driftgraph.ingest.ocr_models import (
    OCRPage,
    TextSegment,
    TableStructure,
    OCROptions,
    BatchOCRResult,
)
from driftgraph.ingest.ocr_engines import (
    get_ocr_engine,
    list_available_engines,
    _generate_preview_base64,
)
from driftgraph.ingest.ocr_layout import detect_tables, reconstruct_layout_markdown

_executor = ThreadPoolExecutor(max_workers=4)


# ---------------------------------------------------------------- detection

def has_text_layer(pdf_path: Path, sample_pages: int = 3) -> bool:
    """True if the PDF already contains selectable text (skip OCR)."""
    try:
        reader = PdfReader(str(pdf_path))
        if not reader.pages:
            return False
        for page in reader.pages[:sample_pages]:
            text = (page.extract_text() or "").strip()
            if text:
                return True
        return False
    except Exception:
        return False


def get_installed_languages() -> List[str]:
    """Return all language packs installed for Tesseract."""
    try:
        langs = pytesseract.get_languages()
        return sorted([l for l in langs if l != "osd"])
    except Exception:
        return ["eng"]


# ------------------------------------------------------------- preprocessing

def preprocess(image: Image.Image | np.ndarray, speed_mode: str = "balanced") -> np.ndarray:
    """
    Grayscale -> noise filter -> binarize -> deskew.
    Speed modes:
      - 'fast': rapid grayscale + Otsu, skip deskew if skew is low
      - 'balanced': median blur + Otsu binarization + deskew
      - 'accurate': bilateral filter + contrast equalization + Otsu + deskew
    """
    if isinstance(image, Image.Image):
        img_np = np.array(image.convert("RGB"))
    else:
        img_np = image

    if len(img_np.shape) == 3:
        if img_np.shape[2] == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        elif img_np.shape[2] == 4:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGBA2GRAY)
        else:
            gray = img_np[:, :, 0]
    else:
        gray = img_np

    if speed_mode == "fast":
        # Fast path: minimal blur and direct threshold
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    elif speed_mode == "accurate":
        # Accurate path: contrast normalization, bilateral filter, Otsu, deskew
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        denoised = cv2.bilateralFilter(enhanced, 5, 50, 50)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return _deskew(binary)

    else:
        # Balanced path (default): median blur + Otsu + deskew
        blurred = cv2.medianBlur(gray, 3)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return _deskew(binary)


def _deskew(binary: np.ndarray) -> np.ndarray:
    """Detect skew angle via minAreaRect and rotate image back to horizontal."""
    coords = cv2.findNonZero(255 - binary)
    if coords is None or len(coords) < 50:
        return binary

    rect = cv2.minAreaRect(coords)
    (cx, cy), (w, h), angle = rect

    if w < h:
        angle = -(90 + angle) if angle < -45 else (90 - angle) if angle > 45 else angle
    else:
        if angle < -45:
            angle = -(90 + angle)

    if abs(angle) < 0.3 or abs(angle) > 15:
        return binary

    bh, bw = binary.shape
    m = cv2.getRotationMatrix2D((bw // 2, bh // 2), angle, 1.0)
    rotated = cv2.warpAffine(
        binary, m, (bw, bh),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )
    _, cleaned = cv2.threshold(rotated, 127, 255, cv2.THRESH_BINARY)
    return cleaned


# -------------------------------------------------------------------- OCR core

def _get_dpi_for_speed(speed_mode: str) -> int:
    """DPI profile for selected speed mode."""
    if speed_mode == "fast":
        return 150
    elif speed_mode == "accurate":
        return 350
    return getattr(app_config.ocr, "dpi", 300)


def _ocr_page_sync(
    image: Image.Image,
    page_number: int,
    options: OCROptions,
) -> OCRPage:
    """Synchronous single-page OCR with preprocessing and engine dispatch."""
    processed = preprocess(image, speed_mode=options.speed_mode)
    engine = get_ocr_engine(options.engine)
    return engine.ocr_page(image, page_number, options, processed_binary=processed)


def _ocr_sync(path: Path, options: OCROptions) -> List[OCRPage]:
    """
    Synchronous document extraction.
    For PDFs, pages with selectable text extract digital text directly (skipping OCR).
    Only scanned pages are converted to images and passed to the OCR engine.
    """
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        pages: List[OCRPage] = []
        try:
            reader = PdfReader(str(path))
            total_pages = len(reader.pages)
        except Exception:
            reader = None
            total_pages = 0

        dpi = options.dpi or _get_dpi_for_speed(options.speed_mode)

        for i in range(total_pages):
            page_num = i + 1
            text = (reader.pages[i].extract_text() or "").strip() if reader else ""

            if text:
                # Text layer present on this page: skip OCR entirely!
                try:
                    box = reader.pages[i].mediabox
                    w, h = int(box.width), int(box.height)
                except Exception:
                    w, h = 800, 1100

                # Generate digital text segments for result highlighting
                words = text.split()
                segments = []
                for idx, w_str in enumerate(words):
                    segments.append(TextSegment(
                        id=f"p{page_num}_w_{idx + 1}",
                        text=w_str,
                        confidence=100.0,
                        bbox=(0, 0, 0, 0),
                        norm_bbox=(0.0, 0.0, 0.0, 0.0),
                        page_number=page_num,
                        is_error=False,
                        segment_type="word"
                    ))

                # Render preview thumbnail if requested
                preview_b64 = None
                if options.generate_preview:
                    try:
                        rendered = convert_from_path(str(path), dpi=100, first_page=page_num, last_page=page_num)
                        if rendered:
                            preview_b64 = _generate_preview_base64(rendered[0])
                    except Exception:
                        pass

                pages.append(OCRPage(
                    page_number=page_num,
                    text=text,
                    mean_confidence=100.0,
                    width=w,
                    height=h,
                    segments=segments,
                    tables=[],
                    preview_image_base64=preview_b64,
                ))
            else:
                # Scanned page without selectable text: render image and run OCR
                images = convert_from_path(
                    str(path),
                    dpi=dpi,
                    first_page=page_num,
                    last_page=page_num,
                )
                if images:
                    page_res = _ocr_page_sync(images[0], page_num, options)
                    pages.append(page_res)
        return pages

    # Standard image file (PNG, JPG, TIFF, etc.)
    image = Image.open(path).convert("RGB")
    return [_ocr_page_sync(image, 1, options)]


# --------------------------------------------------------------- public API

def _cache_path(path: Path, cache_dir: Path, options: OCROptions) -> Path:
    hasher = hashlib.sha256()
    hasher.update(path.read_bytes())
    digest = hasher.hexdigest()[:16]
    engine_tag = options.engine
    lang_tag = options.lang.replace("+", "_")
    speed_tag = options.speed_mode
    return cache_dir / f"{path.stem}-{digest}-{engine_tag}-{lang_tag}-{speed_tag}.json"


async def ocr_document(
    path: Path,
    cache_dir: Optional[Path] = None,
    psm: Optional[int] = None,
    lang: Optional[str] = None,
    dpi: Optional[int] = None,
    min_confidence: Optional[float] = None,
    engine: Optional[str] = None,
    speed_mode: Optional[str] = None,
    error_confidence_threshold: Optional[float] = None,
    preserve_tables: Optional[bool] = None,
    preserve_layout: Optional[bool] = None,
    generate_preview: bool = True,
) -> List[OCRPage]:
    """
    OCR or extract text from one document, with a content-hash cache so rebuilds never re-OCR.
    Uses run_in_executor to avoid blocking the async event loop.
    Supports engine selection, multi-language, speed modes, table detection, and result highlighting.
    """
    c_dir = cache_dir or Path(app_config.ocr.cache_dir)
    c_dir.mkdir(parents=True, exist_ok=True)

    use_speed = speed_mode or getattr(app_config.ocr, "speed_mode", "balanced")
    options = OCROptions(
        engine=engine or getattr(app_config.ocr, "engine", "tesseract"),
        lang=lang or getattr(app_config.ocr, "lang", "eng"),
        psm=psm if psm is not None else getattr(app_config.ocr, "psm", 6),
        dpi=dpi or _get_dpi_for_speed(use_speed),
        speed_mode=use_speed,
        min_confidence=min_confidence if min_confidence is not None else getattr(app_config.ocr, "min_confidence", 60.0),
        error_confidence_threshold=error_confidence_threshold if error_confidence_threshold is not None else getattr(app_config.ocr, "error_confidence_threshold", 60.0),
        preserve_tables=preserve_tables if preserve_tables is not None else getattr(app_config.ocr, "table_detection", True),
        preserve_layout=preserve_layout if preserve_layout is not None else getattr(app_config.ocr, "layout_preservation", True),
        generate_preview=generate_preview,
        google_vision_api_key=getattr(app_config.ocr, "google_vision_api_key", None),
    )

    cache_file = _cache_path(path, c_dir, options)
    if cache_file.exists():
        raw = json.loads(cache_file.read_text(encoding="utf-8"))
        pages = []
        for p in raw:
            segments = [TextSegment(**s) for s in p.get("segments", [])]
            tables = [TableStructure(**t) for t in p.get("tables", [])]
            pages.append(OCRPage(
                page_number=p["page_number"],
                text=p["text"],
                mean_confidence=p["mean_confidence"],
                width=p["width"],
                height=p["height"],
                segments=segments,
                tables=tables,
                preview_image_base64=p.get("preview_image_base64"),
            ))
        return pages

    loop = asyncio.get_running_loop()
    pages = await loop.run_in_executor(_executor, _ocr_sync, path, options)

    # Serialize to cache
    serialized = []
    for p in pages:
        d = asdict(p)
        serialized.append(d)
    cache_file.write_text(json.dumps(serialized, indent=2), encoding="utf-8")

    return pages


async def batch_ocr_documents(
    paths: List[Path],
    cache_dir: Optional[Path] = None,
    concurrency: int = 3,
    **ocr_kwargs,
) -> BatchOCRResult:
    """
    Process multiple documents concurrently, bounded by an asyncio Semaphore.
    Returns an aggregated BatchOCRResult with stats and per-document outputs.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _process_one(path: Path) -> Dict[str, Any]:
        async with semaphore:
            try:
                pages = await ocr_document(path, cache_dir=cache_dir, **ocr_kwargs)
                mean_conf = round(sum(p.mean_confidence for p in pages) / max(1, len(pages)), 2)
                err_count = sum(len(p.error_segments) for p in pages)
                tbl_count = sum(len(p.tables) for p in pages)
                return {
                    "path": str(path),
                    "filename": path.name,
                    "status": "success",
                    "pages_count": len(pages),
                    "mean_confidence": mean_conf,
                    "errors_count": err_count,
                    "tables_count": tbl_count,
                    "pages": pages,
                    "markdown": pages_to_markdown(pages, path.stem),
                }
            except Exception as e:
                return {
                    "path": str(path),
                    "filename": path.name,
                    "status": "failed",
                    "error": str(e),
                    "pages_count": 0,
                    "mean_confidence": 0.0,
                    "errors_count": 0,
                    "tables_count": 0,
                    "pages": [],
                    "markdown": "",
                }

    doc_results = await asyncio.gather(*[_process_one(p) for p in paths])

    successful = [d for d in doc_results if d["status"] == "success"]
    failed = [d for d in doc_results if d["status"] == "failed"]
    total_pages = sum(d["pages_count"] for d in successful)
    avg_conf = (
        round(sum(d["mean_confidence"] for d in successful) / len(successful), 2)
        if successful
        else 0.0
    )
    total_errors = sum(d["errors_count"] for d in successful)
    total_tables = sum(d["tables_count"] for d in successful)

    return BatchOCRResult(
        total_documents=len(paths),
        successful_documents=len(successful),
        failed_documents=len(failed),
        total_pages=total_pages,
        mean_confidence=avg_conf,
        total_errors_marked=total_errors,
        total_tables_detected=total_tables,
        documents=doc_results,
    )


def pages_to_markdown(pages: List[OCRPage], title: str) -> str:
    """Render OCR output back to Markdown preserving page breaks, headings, and tables."""
    parts = [f"# {title}", ""]
    for page in pages:
        text = page.text.strip()
        if not text:
            continue
        parts.append(f"## Page {page.page_number}")
        parts.append("")
        parts.append(text)
        parts.append("")
    return "\n".join(parts)


def ocr_pages_to_note(
    pages: List[OCRPage],
    source_path: Path,
    title: Optional[str] = None,
    engine: str = "tesseract",
    speed_mode: str = "balanced",
) -> Note:
    """
    Convert OCR/document pages into a Note model with source_type='ocr' for provenance.
    """
    doc_title = title or source_path.stem.replace("_", " ").replace("-", " ").title()
    markdown_content = pages_to_markdown(pages, doc_title)
    note_id = source_path.stem.lower().replace(" ", "_").replace("-", "_")

    mean_conf = round(
        sum(p.mean_confidence for p in pages) / max(1, len(pages)), 2
    ) if pages else 0.0

    total_errors = sum(len(p.error_segments) for p in pages)
    total_tables = sum(len(p.tables) for p in pages)

    metadata = NoteMetadata(
        title=doc_title,
        tags=["ocr", "document"],
        date=date.today().isoformat(),
        source_file=str(source_path.resolve()),
        source_type="ocr",
        extra={
            "page_count": len(pages),
            "mean_confidence": mean_conf,
            "errors_marked": total_errors,
            "tables_detected": total_tables,
            "engine": engine,
            "speed_mode": speed_mode,
        }
    )

    return Note(
        id=note_id,
        content=markdown_content.strip(),
        raw_content=markdown_content,
        metadata=metadata,
    )


async def process_document_to_note(
    path: Path,
    cache_dir: Optional[Path] = None,
    title: Optional[str] = None,
    **ocr_kwargs,
) -> Note:
    """Convenience helper: OCR/extract document and return a Note ready for chunking."""
    pages = await ocr_document(path, cache_dir=cache_dir, **ocr_kwargs)
    return ocr_pages_to_note(
        pages,
        source_path=path,
        title=title,
        engine=ocr_kwargs.get("engine", "tesseract"),
        speed_mode=ocr_kwargs.get("speed_mode", "balanced"),
    )


PSM_BY_LAYOUT = {
    "auto": 3,          # fully automatic page segmentation
    "columns": 4,       # single column of variable-size text
    "block": 6,         # single uniform block of text
    "single_line": 7,   # treated as a single text line
    "sparse": 11,       # sparse text, find as much as possible
}
