"""Simple PDF report generation helpers for backend exports."""
from __future__ import annotations

from datetime import date
from typing import Any


def build_transaction_pdf_report(
    portfolio_id: int,
    transactions: list[dict[str, Any]],
    range_label: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> bytes:
    """Create a lightweight PDF report for a transaction list with a spreadsheet-style table."""
    header_values = ("Date", "Type", "Qty", "Price", "Amount", "Details")
    table_rows: list[tuple[str, ...]] = []

    for tx in transactions:
        ts_value = tx.get("ts")
        ts_text = ts_value.strftime("%Y-%m-%d %H:%M") if hasattr(ts_value, "strftime") else str(ts_value)
        quantity = tx.get("quantity", 0)
        table_rows.append(
            (
                ts_text,
                str(tx.get("trans_type") or ""),
                _format_quantity(quantity),
                _format_decimal(tx.get("price", 0)),
                _format_decimal(tx.get("amount", 0)),
                str(tx.get("trans_details") or ""),
            )
        )

    rows_per_page = 24
    pages: list[list[tuple[str, ...]]] = []
    for index in range(0, len(table_rows), rows_per_page):
        pages.append(table_rows[index : index + rows_per_page])

    if not pages:
        pages = [[]]

    objects: list[tuple[int, str]] = []
    object_counter = 1

    def add_object(payload: str) -> int:
        nonlocal object_counter
        obj_num = object_counter
        object_counter += 1
        objects.append((obj_num, payload))
        return obj_num

    catalog_id = add_object("<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add_object("<< /Type /Pages /Kids [] /Count 0 >>")
    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    bold_font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    page_ids: list[int] = []
    content_payloads: list[tuple[int, str]] = []
    total_pages = len(pages)
    for page_number, page_rows in enumerate(pages, start=1):
        content_stream = _build_page_content_stream(
            portfolio_id=portfolio_id,
            range_label=range_label,
            start_date=start_date,
            end_date=end_date,
            page_number=page_number,
            total_pages=total_pages,
            header_values=header_values,
            table_rows=page_rows,
        )
        content_id = add_object(f"<< /Length {len(content_stream.encode('latin-1'))} >>\nstream\n{content_stream}\nendstream")
        content_payloads.append((content_id, content_stream))

    for content_id, _ in content_payloads:
        page_id = add_object(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R /F2 {bold_font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    page_refs = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_payload = f"<< /Type /Pages /Kids [{page_refs}] /Count {len(page_ids)} >>"
    objects[1] = (pages_id, pages_payload)
    objects[0] = (catalog_id, "<< /Type /Catalog /Pages 2 0 R >>")
    objects[2] = (font_id, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects[3] = (bold_font_id, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj_num, payload in objects:
        offsets.append(len(pdf))
        pdf.extend(f"{obj_num} 0 obj\n".encode("latin-1"))
        pdf.extend(payload.encode("latin-1"))
        pdf.extend(b"\nendobj\n")

    startxref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF\n".encode("latin-1")
    )
    return bytes(pdf)


def _build_page_content_stream(
    *,
    portfolio_id: int,
    range_label: str,
    start_date: date | None,
    end_date: date | None,
    page_number: int,
    total_pages: int,
    header_values: tuple[str, ...],
    table_rows: list[tuple[str, ...]],
) -> str:
    lines: list[str] = []
    lines.append("0 0 0 RG")
    lines.append("BT /F2 16 Tf 40 760 Td (Portfolio Transaction Report) Tj ET")
    lines.append("BT /F1 9 Tf 40 742 Td (Portfolio ID: 1) Tj ET")
    lines.append(f"BT /F1 9 Tf 40 728 Td (Range: { _escape_pdf_text(range_label) }) Tj ET")

    if start_date is not None:
        lines.append(f"BT /F1 9 Tf 40 714 Td (From: {start_date.isoformat()}) Tj ET")
    if end_date is not None:
        lines.append(f"BT /F1 9 Tf 40 700 Td (To: {end_date.isoformat()}) Tj ET")

    if total_pages > 1:
        lines.append(f"BT /F1 8 Tf 470 760 Td (Page {page_number}/{total_pages}) Tj ET")

    table_left = 34
    table_top = 660
    row_height = 18
    col_widths = (90, 40, 35, 50, 58, 220)
    table_width = sum(col_widths)
    table_bottom = table_top - row_height * (len(table_rows) + 1)

    lines.append("0.92 0.94 0.98 rg")
    lines.append(f"{table_left} {table_top - row_height} {table_width} {row_height} re f")
    lines.append("0 0 0 rg")

    lines.append(f"{table_left} {table_top} m {table_left + table_width} {table_top} l S")
    for row_index in range(len(table_rows) + 2):
        y = table_top - row_height * row_index
        lines.append(f"{table_left} {y} m {table_left + table_width} {y} l S")

    x = table_left
    for column_width in col_widths:
        lines.append(f"{x} {table_top} m {x} {table_bottom} l S")
        x += column_width

    header_y = table_top - 12
    lines.append("BT /F2 8.5 Tf 0 0 0 rg")
    current_x = table_left + 3
    current_y = header_y
    for index, value in enumerate(header_values):
        text = _truncate_text(value, col_widths[index] - 4)
        lines.append(f"BT /F2 8.5 Tf {current_x} {current_y} Td ({_escape_pdf_text(text)}) Tj ET")
        current_x += col_widths[index]

    if not table_rows:
        lines.append("BT /F1 9 Tf 40 620 Td (No transactions found for the selected period.) Tj ET")
        return "\n".join(lines)

    for row_index, row_values in enumerate(table_rows, start=1):
        row_y = table_top - row_height * row_index - 12
        current_x = table_left + 3
        for index, value in enumerate(row_values):
            text = _truncate_text(value, col_widths[index] - 4)
            lines.append(f"BT /F1 8.2 Tf {current_x} {row_y} Td ({_escape_pdf_text(text)}) Tj ET")
            current_x += col_widths[index]

    return "\n".join(lines)


def _truncate_text(value: str, max_width: int) -> str:
    text = str(value)
    if len(text) <= max_width:
        return text
    if max_width <= 3:
        return text[:max_width]
    return text[: max_width - 3] + "..."


def _format_quantity(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError, OverflowError):
        try:
            return str(float(value))
        except (TypeError, ValueError):
            return str(value)


def _format_decimal(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
