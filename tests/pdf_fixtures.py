from __future__ import annotations

from io import BytesIO
from pathlib import Path


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _content_stream(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    commands = ["BT", "/F1 11 Tf", "50 760 Td"]
    for index, line in enumerate(lines):
        if index:
            commands.append("0 -14 Td")
        commands.append(f"({_escape(line[:180])}) Tj")
    commands.append("ET")
    return "\n".join(commands)


def build_text_pdf_bytes(page_texts: list[str]) -> bytes:
    if not page_texts:
        raise ValueError("at least one page is required")
    font_obj = 3
    parts: dict[int, bytes] = {
        1: b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        3: b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    }
    page_ids: list[int] = []
    next_id = 4
    for text in page_texts:
        page_id = next_id
        content_id = next_id + 1
        next_id += 2
        page_ids.append(page_id)
        stream = _content_stream(text).encode("latin-1", "replace")
        parts[content_id] = (
            f"{content_id} 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream\nendobj\n"
        )
        parts[page_id] = (
            f"{page_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_obj} 0 R >> >> >>\nendobj\n"
        ).encode("latin-1")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    parts[2] = f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(page_texts)} >>\nendobj\n".encode("latin-1")
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    order = [1, 2, 3] + sorted(key for key in parts if key >= 4)
    body = header
    offsets = {0: 0}
    for object_id in order:
        offsets[object_id] = len(body)
        body += parts[object_id]
    xref_start = len(body)
    max_id = max(order)
    xref = [f"xref\n0 {max_id + 1}\n", "0000000000 65535 f \n"]
    for object_id in range(1, max_id + 1):
        xref.append(f"{offsets.get(object_id, 0):010d} 00000 n \n")
    trailer = f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n"
    return body + "".join(xref).encode("ascii") + trailer.encode("ascii")


def write_text_pdf(path: Path, page_texts: list[str]) -> Path:
    path.write_bytes(build_text_pdf_bytes(page_texts))
    return path


def build_encrypted_pdf_bytes(password: str = "secret") -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt(password)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
