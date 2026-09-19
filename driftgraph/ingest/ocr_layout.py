"""driftgraph/ingest/ocr_layout.py

Layout analysis and structure preservation for OCR output:
- Table detection and Markdown table synthesis (grid lines + alignment clustering)
- Multi-column reading order detection (column-first sorting vs naive row interlacing)
- Heading and list item detection with Markdown emission
"""

from __future__ import annotations

import re
from typing import List, Tuple, Optional
import cv2
import numpy as np

from driftgraph.ingest.ocr_models import TextSegment, TableStructure


def detect_tables(
    binary_image: np.ndarray,
    page_number: int,
    segments: List[TextSegment],
) -> List[TableStructure]:
    """
    Detect tables using morphological operations (horizontal & vertical grid line intersection)
    combined with word spatial clustering. Reconstructs Markdown tables.
    """
    if binary_image is None or len(binary_image.shape) < 2:
        return []

    h, w = binary_image.shape[:2]
    # Invert binary image so lines are white on black
    inv = 255 - binary_image if np.mean(binary_image) > 127 else binary_image

    # Horizontal and vertical kernels scaled to image size
    scale_h = max(15, w // 40)
    scale_v = max(15, h // 40)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (scale_h, 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, scale_v))

    h_lines = cv2.morphologyEx(inv, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(inv, cv2.MORPH_OPEN, v_kernel)

    table_mask = cv2.add(h_lines, v_lines)
    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    tables: List[TableStructure] = []
    min_table_w = w * 0.25
    min_table_h = h * 0.08

    for idx, cnt in enumerate(contours):
        x, y, tw, th = cv2.boundingRect(cnt)
        if tw < min_table_w or th < min_table_h:
            continue

        # Collect text segments inside this table bounding box
        table_segs = [
            s for s in segments
            if (x - 10 <= s.bbox[0] <= x + tw + 10) and (y - 10 <= s.bbox[1] <= y + th + 10)
        ]
        if len(table_segs) < 4:
            continue

        # Group segments into rows by Y overlap
        rows_data = _cluster_segments_into_table_grid(table_segs)
        if len(rows_data) < 2:
            continue

        # Build Markdown and HTML representation
        headers = rows_data[0]
        data_rows = rows_data[1:]

        # Normalize column count across all rows
        max_cols = max(len(r) for r in rows_data)
        if max_cols < 2:
            continue

        normalized_headers = headers + [""] * (max_cols - len(headers))
        normalized_data = [r + [""] * (max_cols - len(r)) for r in data_rows]

        md_lines = [
            "| " + " | ".join(c.replace("|", "\\|") for c in normalized_headers) + " |",
            "| " + " | ".join(["---"] * max_cols) + " |",
        ]
        for row in normalized_data:
            md_lines.append("| " + " | ".join(c.replace("|", "\\|") for c in row) + " |")

        md_text = "\n".join(md_lines)

        html_parts = ["<table class=\"ocr-table\"><thead><tr>"]
        for h_col in normalized_headers:
            html_parts.append(f"<th>{h_col}</th>")
        html_parts.append("</tr></thead><tbody>")
        for row in normalized_data:
            html_parts.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
        html_parts.append("</tbody></table>")

        tables.append(TableStructure(
            table_id=f"page_{page_number}_table_{idx + 1}",
            page_number=page_number,
            bbox=(x, y, tw, th),
            headers=normalized_headers,
            rows=normalized_data,
            markdown=md_text,
            html="".join(html_parts)
        ))

    # Also check for borderless / alignment-based tables if no bordered tables found
    if not tables:
        borderless = _detect_borderless_tables(segments, page_number, w, h)
        if borderless:
            tables.extend(borderless)

    return tables


def _cluster_segments_into_table_grid(segments: List[TextSegment]) -> List[List[str]]:
    """Group text segments into rows based on Y-proximity, then sort columns by X."""
    if not segments:
        return []

    # Sort primarily by Y
    sorted_by_y = sorted(segments, key=lambda s: s.bbox[1])
    rows: List[List[TextSegment]] = []

    for seg in sorted_by_y:
        matched_row = False
        for row in rows:
            # Average Y of row
            avg_y = sum(s.bbox[1] for s in row) / len(row)
            avg_h = sum(s.bbox[3] for s in row) / len(row)
            if abs(seg.bbox[1] - avg_y) <= avg_h * 0.75:
                row.append(seg)
                matched_row = True
                break
        if not matched_row:
            rows.append([seg])

    grid: List[List[str]] = []
    for row in rows:
        row_sorted = sorted(row, key=lambda s: s.bbox[0])
        # Merge segments that are extremely close horizontally (part of the same cell)
        cells: List[str] = []
        curr_cell = [row_sorted[0].text]
        for i in range(1, len(row_sorted)):
            prev_s = row_sorted[i - 1]
            curr_s = row_sorted[i]
            x_gap = curr_s.bbox[0] - (prev_s.bbox[0] + prev_s.bbox[2])
            if x_gap < prev_s.bbox[3] * 1.5:  # small gap within same cell
                curr_cell.append(curr_s.text)
            else:
                cells.append(" ".join(curr_cell).strip())
                curr_cell = [curr_s.text]
        cells.append(" ".join(curr_cell).strip())
        grid.append(cells)

    return grid


def _detect_borderless_tables(
    segments: List[TextSegment],
    page_number: int,
    page_width: int,
    page_height: int,
) -> List[TableStructure]:
    """Fallback detector for borderless aligned tabular columns."""
    grid = _cluster_segments_into_table_grid(segments)
    if len(grid) < 3:
        return []

    # Check if multiple consecutive rows have the same column count (>= 2 columns)
    counts = [len(r) for r in grid]
    from collections import Counter
    mode_count, occurrences = Counter(counts).most_common(1)[0]
    if mode_count < 2 or occurrences < 3:
        return []

    candidate_rows = [r for r in grid if len(r) == mode_count]
    if len(candidate_rows) < 3:
        return []

    headers = candidate_rows[0]
    data_rows = candidate_rows[1:]

    md_lines = [
        "| " + " | ".join(c.replace("|", "\\|") for c in headers) + " |",
        "| " + " | ".join(["---"] * mode_count) + " |",
    ]
    for r in data_rows:
        md_lines.append("| " + " | ".join(c.replace("|", "\\|") for c in r) + " |")

    return [TableStructure(
        table_id=f"page_{page_number}_table_borderless_1",
        page_number=page_number,
        bbox=(0, 0, page_width, page_height),
        headers=headers,
        rows=data_rows,
        markdown="\n".join(md_lines),
        html=""
    )]


def detect_columns_and_sort_reading_order(
    segments: List[TextSegment],
    page_width: int,
) -> List[TextSegment]:
    """
    Detect multi-column layouts (e.g. 2-column or 3-column documents)
    and order segments column-first (reading down Column 1, then Column 2)
    to prevent naive left-to-right interlacing across columns.
    """
    if len(segments) < 10:
        return sorted(segments, key=lambda s: (s.bbox[1], s.bbox[0]))

    mid_x = page_width / 2.0
    left_segs = [s for s in segments if s.bbox[0] + s.bbox[2] <= mid_x * 1.05]
    right_segs = [s for s in segments if s.bbox[0] >= mid_x * 0.95]

    # If significant text is neatly split between left and right halves (2 columns)
    if len(left_segs) >= 4 and len(right_segs) >= 4 and (len(left_segs) + len(right_segs)) > len(segments) * 0.7:
        # Full-width headers (spanned across top)
        spanned_top = [s for s in segments if s not in left_segs and s not in right_segs and s.bbox[1] < min(s.bbox[1] for s in left_segs + right_segs) + 50]
        remaining = [s for s in segments if s not in left_segs and s not in right_segs and s not in spanned_top]

        sorted_spanned = sorted(spanned_top, key=lambda s: (s.bbox[1], s.bbox[0]))
        sorted_left = sorted(left_segs, key=lambda s: (s.bbox[1], s.bbox[0]))
        sorted_right = sorted(right_segs, key=lambda s: (s.bbox[1], s.bbox[0]))
        sorted_rest = sorted(remaining, key=lambda s: (s.bbox[1], s.bbox[0]))

        return sorted_spanned + sorted_left + sorted_right + sorted_rest

    # Single column: sort by Y then X
    return sorted(segments, key=lambda s: (s.bbox[1], s.bbox[0]))


def reconstruct_layout_markdown(
    segments: List[TextSegment],
    tables: List[TableStructure],
    page_width: int,
    page_height: int,
) -> str:
    """
    Assemble structured Markdown preserving headings, lists, tables, and paragraphs.
    """
    if not segments and not tables:
        return ""

    ordered_segments = detect_columns_and_sort_reading_order(segments, page_width)

    # Exclude segments that belong to detected tables (to avoid duplicating table text)
    table_bboxes = [t.bbox for t in tables]

    def in_any_table(seg: TextSegment) -> bool:
        for tx, ty, tw, th in table_bboxes:
            if tx <= seg.bbox[0] <= tx + tw and ty <= seg.bbox[1] <= ty + th:
                return True
        return False

    free_segments = [s for s in ordered_segments if not in_any_table(s)]

    # Compute median line height for heading detection
    heights = [s.bbox[3] for s in free_segments if s.bbox[3] > 0]
    median_h = np.median(heights) if heights else 14.0

    lines: List[List[TextSegment]] = []
    for s in free_segments:
        matched = False
        for line in lines:
            avg_y = sum(seg.bbox[1] for seg in line) / len(line)
            avg_h = sum(seg.bbox[3] for seg in line) / len(line)
            if abs(s.bbox[1] - avg_y) <= avg_h * 0.6:
                line.append(s)
                matched = True
                break
        if not matched:
            lines.append([s])

    md_paragraphs: List[str] = []
    prev_y = -1
    current_para: List[str] = []

    for line in lines:
        line_sorted = sorted(line, key=lambda s: s.bbox[0])
        line_text = " ".join(s.text for s in line_sorted).strip()
        if not line_text:
            continue

        line_h = sum(s.bbox[3] for s in line_sorted) / len(line_sorted)
        line_y = line_sorted[0].bbox[1]

        # 1. Heading Detection
        if line_h >= median_h * 1.5 and len(line_text.split()) <= 12:
            if current_para:
                md_paragraphs.append(" ".join(current_para))
                current_para = []
            prefix = "# " if line_h >= median_h * 2.0 else "## "
            clean_title = re.sub(r"^#+\s*", "", line_text)
            md_paragraphs.append(f"{prefix}{clean_title}")
            prev_y = line_y
            continue

        # 2. List Item Detection
        list_match = re.match(r"^([•\-\*]|\d+[\.\)])\s*(.+)$", line_text)
        if list_match:
            if current_para:
                md_paragraphs.append(" ".join(current_para))
                current_para = []
            marker, rest = list_match.groups()
            std_marker = "*" if marker in ["•", "-", "*"] else marker
            md_paragraphs.append(f"{std_marker} {rest}")
            prev_y = line_y
            continue

        # 3. Paragraph separation by vertical gap
        if prev_y > 0 and (line_y - prev_y) > median_h * 2.2:
            if current_para:
                md_paragraphs.append(" ".join(current_para))
                current_para = []

        current_para.append(line_text)
        prev_y = line_y

    if current_para:
        md_paragraphs.append(" ".join(current_para))

    # Append any detected tables
    if tables:
        for t in tables:
            if t.markdown:
                md_paragraphs.append(t.markdown)

    return "\n\n".join(p for p in md_paragraphs if p.strip())
