"""tests/test_ocr.py

Comprehensive tests for DriftGraph OCR document ingestion:
- Scanned image & PDF fixtures with golden-text assertion
- Preprocessing (grayscale -> median blur -> Otsu -> deskew)
- Text-layer detection (has_text_layer) so text PDFs skip OCR
- Content-hash caching so rebuilds never re-OCR
- Markdown emission and chunking with provenance metadata (source_type="ocr")
- BenchmarkRunner per-page latency & RSS profiling
- Configuration exposure for psm and lang
- FastAPI /api/ingest/upload endpoint integration
"""

import asyncio
import io
from pathlib import Path
import cv2
import numpy as np
import pytest
from PIL import Image
from httpx import AsyncClient, ASGITransport

from driftgraph.config import config
from driftgraph.eval.benchmark import BenchmarkRunner
from driftgraph.ingest import chunk_notes
from driftgraph.ingest.models import NoteMetadata
from driftgraph.ingest.ocr import (
    OCRPage,
    has_text_layer,
    preprocess,
    _deskew,
    ocr_document,
    pages_to_markdown,
    ocr_pages_to_note,
    process_document_to_note,
    batch_ocr_documents,
    get_installed_languages,
)
from driftgraph.ingest.ocr_models import (
    OCROptions,
    TextSegment,
    TableStructure,
    BatchOCRResult,
)
from driftgraph.ingest.ocr_engines import (
    get_ocr_engine,
    list_available_engines,
    TesseractEngine,
    GoogleVisionEngine,
    LocalHeuristicEngine,
)
from driftgraph.ingest.ocr_layout import (
    detect_tables,
    _detect_borderless_tables,
    detect_columns_and_sort_reading_order,
    reconstruct_layout_markdown,
)
from driftgraph.serve.app import app

GOLDEN_TEXT = "DriftGraph Knowledge Graph OCR Pipeline"


@pytest.fixture
def scanned_image_fixture(tmp_path: Path) -> Path:
    """
    Generate a small synthetic scanned document fixture with skew and Otsu binarization characteristics.
    """
    width, height = 900, 260
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Render golden text
    cv2.putText(
        img,
        GOLDEN_TEXT,
        (40, 140),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )

    # Introduce a 3-degree rotation skew to simulate physical scanner feed
    matrix = cv2.getRotationMatrix2D((width // 2, height // 2), 3.0, 1.0)
    skewed = cv2.warpAffine(img, matrix, (width, height), borderValue=(255, 255, 255))

    img_path = tmp_path / "scanned_doc.png"
    Image.fromarray(skewed).save(str(img_path))
    return img_path


@pytest.fixture
def scanned_pdf_fixture(scanned_image_fixture: Path, tmp_path: Path) -> Path:
    """Convert scanned image into a PDF without any digital text layer."""
    pdf_path = tmp_path / "scanned_invoice.pdf"
    img = Image.open(scanned_image_fixture)
    img.save(str(pdf_path), "PDF", resolution=150.0)
    return pdf_path


@pytest.fixture
def digital_pdf_fixture(tmp_path: Path) -> Path:
    """Create a minimal valid PDF containing an embedded selectable text layer."""
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 58 >>\nstream\n"
        b"BT\n/F1 20 Tf\n80 700 Td\n(Selectable Digital Text in DriftGraph) Tj\nET\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000353 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n427\n%%EOF\n"
    )
    p = tmp_path / "digital_doc.pdf"
    p.write_bytes(pdf_bytes)
    return p


# ---------------------------------------------------------------- Tests

def test_config_exposure():
    """Verify psm and lang are exposed in configuration."""
    assert hasattr(config, "ocr")
    assert config.ocr.psm in [3, 4, 6, 7, 11]
    assert config.ocr.lang == "eng"
    assert config.ocr.dpi == 300
    assert config.ocr.min_confidence >= 50.0


def test_preprocessing_and_deskew(scanned_image_fixture: Path):
    """Test preprocessing: grayscale -> median blur -> Otsu -> deskew."""
    image = Image.open(scanned_image_fixture)
    binary = preprocess(image)

    assert isinstance(binary, np.ndarray)
    assert len(binary.shape) == 2  # Grayscale / binarized
    assert np.all(np.isin(binary, [0, 255]))  # Otsu binary values only

    # Text pixels should exist
    assert np.sum(binary == 0) > 100


def test_has_text_layer_detection(scanned_pdf_fixture: Path, digital_pdf_fixture: Path):
    """Verify that text-based PDFs are recognized and scanned PDFs skip text layer."""
    assert not has_text_layer(scanned_pdf_fixture), "Scanned PDF must not have a text layer"
    assert has_text_layer(digital_pdf_fixture), "Digital PDF must have a selectable text layer"


@pytest.mark.asyncio
async def test_ocr_extraction_golden_text(scanned_image_fixture: Path, tmp_path: Path):
    """Run OCR on the scanned fixture and verify golden text extraction with confidence."""
    cache_dir = tmp_path / "cache"
    pages = await ocr_document(scanned_image_fixture, cache_dir=cache_dir)

    assert len(pages) == 1
    page = pages[0]
    assert page.page_number == 1
    assert page.mean_confidence >= 60.0

    # Golden text assertions
    extracted = page.text
    assert "DriftGraph" in extracted
    assert "OCR" in extracted or "Knowledge" in extracted


@pytest.mark.asyncio
async def test_content_hash_caching(scanned_image_fixture: Path, tmp_path: Path):
    """Verify that OCR output is cached by content hash so rebuilds never re-OCR."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # First run: processes and caches
    pages_first = await ocr_document(scanned_image_fixture, cache_dir=cache_dir)
    cached_files = list(cache_dir.glob("*.json"))
    assert len(cached_files) == 1

    # Mutate cache file to verify second call reads directly from disk
    cached_file = cached_files[0]
    data = cached_file.read_text(encoding="utf-8")
    tampered = data.replace("DriftGraph", "DriftGraphCachedRebuild")
    cached_file.write_text(tampered, encoding="utf-8")

    # Second run: should hit cache directly
    pages_second = await ocr_document(scanned_image_fixture, cache_dir=cache_dir)
    assert "DriftGraphCachedRebuild" in pages_second[0].text


@pytest.mark.asyncio
async def test_digital_pdf_skips_ocr(digital_pdf_fixture: Path, tmp_path: Path):
    """Digital PDFs with text layer extract selectable text directly, skipping OCR."""
    cache_dir = tmp_path / "cache"
    pages = await ocr_document(digital_pdf_fixture, cache_dir=cache_dir)

    assert len(pages) == 1
    assert pages[0].mean_confidence == 100.0  # direct digital extraction
    assert "Selectable Digital Text" in pages[0].text


def test_markdown_emission_and_provenance(tmp_path: Path):
    """Verify emitting Markdown from pages and feeding to chunk_notes with source_type='ocr'."""
    page1 = OCRPage(page_number=1, text="First page content discussing knowledge graphs.", mean_confidence=92.0, width=800, height=1100)
    page2 = OCRPage(page_number=2, text="Second page content covering community detection.", mean_confidence=89.0, width=800, height=1100)

    # 1. Emit Markdown
    md = pages_to_markdown([page1, page2], "Graph Architecture")
    assert "# Graph Architecture" in md
    assert "## Page 1" in md
    assert "First page content" in md
    assert "## Page 2" in md
    assert "Second page content" in md

    # 2. Construct Note with provenance
    note = ocr_pages_to_note([page1, page2], source_path=tmp_path / "architecture.pdf", title="Graph Architecture")
    assert note.metadata.source_type == "ocr"
    assert note.metadata.title == "Graph Architecture"
    assert note.metadata.extra["page_count"] == 2

    # 3. Feed to existing chunk_notes
    chunks = chunk_notes([note], target_tokens=64, overlap_tokens=10)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.metadata["source_type"] == "ocr"
        assert chunk.metadata["title"] == "Graph Architecture"


def test_benchmark_runner_ocr_reporting():
    """Verify BenchmarkRunner reports per-page latency and peak RSS for OCR pages."""
    runner = BenchmarkRunner()

    # Measure batch OCR pages
    with runner.measure_ocr(page_count=4, stage_name="OCR Document Ingestion"):
        # simulate work
        _ = sum(i * i for i in range(50000))

    report = runner.generate_report()
    assert len(report.stages) == 1
    metric = report.stages[0]

    assert metric.items_processed == 4
    assert metric.per_page_latency_ms is not None
    assert metric.per_page_latency_ms > 0
    assert metric.peak_rss_mb > 0
    assert "rss_mb" in metric.extra

    # Direct per-page record
    page_metric = runner.record_ocr_page(page_num=5, latency_ms=45.2, peak_rss_mb=128.5)
    assert page_metric.stage_name == "OCR Page 5"
    assert page_metric.latency_ms == 45.2
    assert page_metric.peak_rss_mb == 128.5
    assert page_metric.per_page_latency_ms == 45.2


@pytest.mark.asyncio
async def test_api_upload_endpoint(scanned_image_fixture: Path, tmp_path: Path, monkeypatch):
    """Test FastAPI /api/ingest/upload endpoint with multipart upload."""
    notes_dir = tmp_path / "notes"
    data_dir = tmp_path / "data"
    notes_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config.paths, "notes_dir", str(notes_dir))
    monkeypatch.setattr(config.paths, "data_dir", str(data_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with open(scanned_image_fixture, "rb") as f:
            files = {"file": ("test_scanned.png", f, "image/png")}
            data = {"title": "Uploaded Test Document"}
            resp = await client.post("/api/ingest/upload", files=files, data=data)

        assert resp.status_code == 200
        res = resp.json()
        assert res["source_type"] == "ocr"
        assert res["title"] == "Uploaded Test Document"
        assert res["pages_count"] == 1
        assert "DriftGraph" in res["markdown_content"]


# ---------------------------------------------------------------- Advanced OCR Tests

def test_multiple_ocr_engines_and_fallback(scanned_image_fixture: Path):
    """Verify engine factory, registry listing, and cloud fallback behaviors."""
    tess = get_ocr_engine("tesseract")
    assert isinstance(tess, TesseractEngine)
    assert tess.name == "tesseract"
    assert tess.is_available() is True
    assert tess.is_cloud is False

    local = get_ocr_engine("local")
    assert isinstance(local, LocalHeuristicEngine)
    assert local.name == "local"
    assert local.is_available() is True

    gv = get_ocr_engine("google_vision")
    assert isinstance(gv, GoogleVisionEngine)
    assert gv.name == "google_vision"
    assert gv.is_cloud is True

    # Unknown engine falls back to default safely
    unknown = get_ocr_engine("unknown_nonexistent")
    assert isinstance(unknown, TesseractEngine)

    # Registry enumeration
    engines = list_available_engines()
    engine_names = [e["name"] for e in engines]
    assert "tesseract" in engine_names
    assert "google_vision" in engine_names
    assert "local" in engine_names

    # Test GoogleVisionEngine graceful fallback when API key is unset
    img = Image.open(scanned_image_fixture)
    gv_page = gv.ocr_page(img, page_number=1, options=OCROptions())
    assert isinstance(gv_page, OCRPage)
    assert gv_page.mean_confidence > 0
    assert "DriftGraph" in gv_page.text


def test_language_selection(scanned_image_fixture: Path):
    """Verify runtime language detection and multi-language option passing."""
    langs = get_installed_languages()
    assert isinstance(langs, list)
    assert "eng" in langs

    # Test OCR with explicit language parameter
    tess = TesseractEngine()
    img = Image.open(scanned_image_fixture)
    page = tess.ocr_page(img, page_number=1, options=OCROptions(lang="eng"))
    assert page.mean_confidence > 0
    assert "DriftGraph" in page.text


def test_confidence_scores_highlighting_and_error_marking(scanned_image_fixture: Path):
    """Verify segment-level confidence, normalized bbox overlays, and error marking."""
    tess = TesseractEngine()
    img = Image.open(scanned_image_fixture)
    # Set high threshold (e.g. 99.0) to guarantee some segments are flagged as errors for review
    options = OCROptions(error_confidence_threshold=99.0, generate_preview=True)
    page = tess.ocr_page(img, page_number=1, options=options)

    assert len(page.segments) > 0
    for seg in page.segments:
        assert isinstance(seg.confidence, float)
        assert 0.0 <= seg.confidence <= 100.0
        # Check normalized bounding box in [0.0, 1.0] for UI visual highlighting overlay
        assert len(seg.norm_bbox) == 4
        nx, ny, nw, nh = seg.norm_bbox
        assert 0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0
        assert 0.0 <= nw <= 1.0 and 0.0 <= nh <= 1.0

        if seg.confidence < 99.0:
            assert seg.is_error is True
            assert seg.error_reason is not None

    # Error segments property
    assert len(page.error_segments) > 0
    assert all(s.is_error for s in page.error_segments)

    # Preview image base64 check for UI rendering
    assert page.preview_image_base64 is not None
    assert page.preview_image_base64.startswith("data:image/jpeg;base64,")


def test_table_preservation_grid():
    """Verify grid table detection, row/column alignment, and markdown table synthesis."""
    w, h = 800, 400
    # Create white canvas (255)
    canvas = np.ones((h, w), dtype=np.uint8) * 255

    # Draw table bounding box and grid lines in black (0)
    tx, ty, tw, th = 100, 100, 600, 180
    cv2.rectangle(canvas, (tx, ty), (tx + tw, ty + th), 0, 3)
    # Horizontal divider between header and data
    cv2.line(canvas, (tx, ty + 60), (tx + tw, ty + 60), 0, 2)
    # Vertical dividers for 3 columns
    cv2.line(canvas, (tx + 200, ty), (tx + 200, ty + th), 0, 2)
    cv2.line(canvas, (tx + 400, ty), (tx + 400, ty + th), 0, 2)

    # Synthetic text segments inside table cells
    segments = [
        # Headers (row 0)
        TextSegment(id="h1", text="Component", confidence=95.0, bbox=(120, 120, 100, 25), norm_bbox=(0.15, 0.3, 0.12, 0.06), page_number=1),
        TextSegment(id="h2", text="Version", confidence=95.0, bbox=(320, 120, 80, 25), norm_bbox=(0.4, 0.3, 0.1, 0.06), page_number=1),
        TextSegment(id="h3", text="Status", confidence=95.0, bbox=(520, 120, 80, 25), norm_bbox=(0.65, 0.3, 0.1, 0.06), page_number=1),
        # Row 1
        TextSegment(id="r1", text="Tesseract", confidence=92.0, bbox=(120, 190, 100, 25), norm_bbox=(0.15, 0.47, 0.12, 0.06), page_number=1),
        TextSegment(id="r2", text="5.5.0", confidence=90.0, bbox=(320, 190, 60, 25), norm_bbox=(0.4, 0.47, 0.08, 0.06), page_number=1),
        TextSegment(id="r3", text="Active", confidence=94.0, bbox=(520, 190, 70, 25), norm_bbox=(0.65, 0.47, 0.09, 0.06), page_number=1),
    ]

    tables = detect_tables(canvas, page_number=1, segments=segments)
    assert len(tables) == 1
    tbl = tables[0]
    assert tbl.page_number == 1
    assert "Component" in tbl.headers
    assert "Version" in tbl.headers
    assert "Status" in tbl.headers
    assert any("Tesseract" in str(r) for r in tbl.rows)
    assert "| Component | Version | Status |" in tbl.markdown
    assert "| --- | --- | --- |" in tbl.markdown
    assert "<table" in tbl.html


def test_borderless_table_fallback():
    """Verify fallback detection of borderless aligned tabular columns."""
    segments = [
        # Row 1: Header
        TextSegment(id="s1", text="Name", confidence=95.0, bbox=(50, 50, 80, 20), norm_bbox=(0.05, 0.05, 0.08, 0.02), page_number=1),
        TextSegment(id="s2", text="Metric", confidence=95.0, bbox=(250, 50, 80, 20), norm_bbox=(0.25, 0.05, 0.08, 0.02), page_number=1),
        TextSegment(id="s3", text="Value", confidence=95.0, bbox=(450, 50, 80, 20), norm_bbox=(0.45, 0.05, 0.08, 0.02), page_number=1),
        # Row 2
        TextSegment(id="s4", text="ItemA", confidence=95.0, bbox=(50, 90, 80, 20), norm_bbox=(0.05, 0.09, 0.08, 0.02), page_number=1),
        TextSegment(id="s5", text="Latency", confidence=95.0, bbox=(250, 90, 80, 20), norm_bbox=(0.25, 0.09, 0.08, 0.02), page_number=1),
        TextSegment(id="s6", text="12ms", confidence=95.0, bbox=(450, 90, 80, 20), norm_bbox=(0.45, 0.09, 0.08, 0.02), page_number=1),
        # Row 3
        TextSegment(id="s7", text="ItemB", confidence=95.0, bbox=(50, 130, 80, 20), norm_bbox=(0.05, 0.13, 0.08, 0.02), page_number=1),
        TextSegment(id="s8", text="Memory", confidence=95.0, bbox=(250, 130, 80, 20), norm_bbox=(0.25, 0.13, 0.08, 0.02), page_number=1),
        TextSegment(id="s9", text="84MB", confidence=95.0, bbox=(450, 130, 80, 20), norm_bbox=(0.45, 0.13, 0.08, 0.02), page_number=1),
    ]

    tables = _detect_borderless_tables(segments, page_number=1, page_width=800, page_height=600)
    assert len(tables) == 1
    assert "Name" in tables[0].headers
    assert "| Name | Metric | Value |" in tables[0].markdown


def test_multicolumn_reading_order_and_layout():
    """Verify column-first reading order prevents naive horizontal interlacing."""
    # 5 segments in left column, 5 in right column, interleaved by Y
    segments = [
        # Left column (x=50..250)
        TextSegment(id="l1", text="Left Para 1", confidence=95.0, bbox=(50, 100, 150, 25), norm_bbox=(0.05, 0.1, 0.15, 0.025), page_number=1),
        TextSegment(id="l2", text="Left Para 2", confidence=95.0, bbox=(50, 140, 150, 25), norm_bbox=(0.05, 0.14, 0.15, 0.025), page_number=1),
        TextSegment(id="l3", text="Left Para 3", confidence=95.0, bbox=(50, 180, 150, 25), norm_bbox=(0.05, 0.18, 0.15, 0.025), page_number=1),
        TextSegment(id="l4", text="Left Para 4", confidence=95.0, bbox=(50, 220, 150, 25), norm_bbox=(0.05, 0.22, 0.15, 0.025), page_number=1),
        TextSegment(id="l5", text="Left Para 5", confidence=95.0, bbox=(50, 260, 150, 25), norm_bbox=(0.05, 0.26, 0.15, 0.025), page_number=1),

        # Right column (x=550..750)
        TextSegment(id="r1", text="Right Para 1", confidence=95.0, bbox=(550, 110, 150, 25), norm_bbox=(0.55, 0.11, 0.15, 0.025), page_number=1),
        TextSegment(id="r2", text="Right Para 2", confidence=95.0, bbox=(550, 150, 150, 25), norm_bbox=(0.55, 0.15, 0.15, 0.025), page_number=1),
        TextSegment(id="r3", text="Right Para 3", confidence=95.0, bbox=(550, 190, 150, 25), norm_bbox=(0.55, 0.19, 0.15, 0.025), page_number=1),
        TextSegment(id="r4", text="Right Para 4", confidence=95.0, bbox=(550, 230, 150, 25), norm_bbox=(0.55, 0.23, 0.15, 0.025), page_number=1),
        TextSegment(id="r5", text="Right Para 5", confidence=95.0, bbox=(550, 270, 150, 25), norm_bbox=(0.55, 0.27, 0.15, 0.025), page_number=1),
    ]

    ordered = detect_columns_and_sort_reading_order(segments, page_width=1000)
    ordered_texts = [s.text for s in ordered]

    # All left column segments MUST precede all right column segments
    left_indices = [ordered_texts.index(f"Left Para {i}") for i in range(1, 6)]
    right_indices = [ordered_texts.index(f"Right Para {i}") for i in range(1, 6)]
    assert max(left_indices) < min(right_indices), "Left column should be fully read before Right column"

    # Test layout markdown synthesis
    md = reconstruct_layout_markdown(segments, tables=[], page_width=1000, page_height=800)
    assert "Left Para 1" in md
    assert "Right Para 1" in md


def test_ocr_speed_modes(scanned_image_fixture: Path):
    """Verify OCR speed control profiles (fast vs accurate)."""
    tess = TesseractEngine()
    img = Image.open(scanned_image_fixture)

    fast_opts = OCROptions(speed_mode="fast")
    acc_opts = OCROptions(speed_mode="accurate")

    fast_page = tess.ocr_page(img, page_number=1, options=fast_opts)
    acc_page = tess.ocr_page(img, page_number=1, options=acc_opts)

    assert "DriftGraph" in fast_page.text
    assert "DriftGraph" in acc_page.text


@pytest.mark.asyncio
async def test_batch_ocr_processing(scanned_image_fixture: Path, digital_pdf_fixture: Path, tmp_path: Path):
    """Verify batch processing across multiple heterogeneous files."""
    cache_dir = tmp_path / "cache"
    result = await batch_ocr_documents(
        [scanned_image_fixture, digital_pdf_fixture],
        cache_dir=cache_dir,
    )

    assert isinstance(result, BatchOCRResult)
    assert result.total_documents == 2
    assert result.successful_documents == 2
    assert result.failed_documents == 0
    assert result.total_pages == 2
    assert result.mean_confidence > 0.0
    assert len(result.documents) == 2


@pytest.mark.asyncio
async def test_api_batch_upload_and_info(scanned_image_fixture: Path, tmp_path: Path, monkeypatch):
    """Test /api/ingest/ocr/info and /api/ingest/upload-batch endpoints."""
    notes_dir = tmp_path / "notes"
    data_dir = tmp_path / "data"
    notes_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config.paths, "notes_dir", str(notes_dir))
    monkeypatch.setattr(config.paths, "data_dir", str(data_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Info endpoint
        info_resp = await client.get("/api/ingest/ocr/info")
        assert info_resp.status_code == 200
        info = info_resp.json()
        assert "tesseract" in [e["name"] for e in info["engines"]]
        assert "eng" in info["installed_languages"]
        assert "balanced" in info["speed_modes"]

        # 2. Batch upload endpoint
        with open(scanned_image_fixture, "rb") as f1, open(scanned_image_fixture, "rb") as f2:
            files = [
                ("files", ("doc1.png", f1.read(), "image/png")),
                ("files", ("doc2.png", f2.read(), "image/png")),
            ]
            batch_resp = await client.post(
                "/api/ingest/upload-batch",
                files=files,
                data={"engine": "tesseract", "speed_mode": "fast", "language": "eng"},
            )

        assert batch_resp.status_code == 200
        batch_res = batch_resp.json()
        assert batch_res["total_documents"] == 2
        assert batch_res["successful_documents"] == 2
        assert batch_res["total_pages"] == 2


@pytest.mark.asyncio
async def test_api_ocr_correct_endpoint(tmp_path: Path, monkeypatch):
    """Test inline OCR correction endpoint /api/ingest/ocr/correct."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config.paths, "notes_dir", str(notes_dir))

    test_file = notes_dir / "sample_ocr_note.md"
    test_file.write_text(
        "---\ntitle: Sample Note\nsource_type: ocr\n---\n\nInitial content with DrlftGrph spelling error.",
        encoding="utf-8",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/ingest/ocr/correct",
            json={
                "filename": "sample_ocr_note.md",
                "old_text": "DrlftGrph",
                "new_text": "DriftGraph",
            },
        )
        assert resp.status_code == 200
        res = resp.json()
        assert res["status"] == "success"

    # Verify file content was corrected on disk
    updated_content = test_file.read_text(encoding="utf-8")
    assert "DriftGraph spelling error" in updated_content
    assert "DrlftGrph" not in updated_content

