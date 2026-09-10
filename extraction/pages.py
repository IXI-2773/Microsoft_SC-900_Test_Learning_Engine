from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXTRACTOR_VERSION = "sc900-extractor-v1"
MIN_PAGE_TEXT_CHARS = 40


class PdfExtractionError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str
    character_count: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PdfDocumentText:
    source_path: str
    source_document_id: str
    source_title: str
    page_count: int
    pages: tuple[PageText, ...]
    extraction_method: str
    extractor_version: str
    warnings: tuple[str, ...]
    encrypted: bool = False


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _insufficient_text(pages: tuple[PageText, ...]) -> bool:
    if not pages:
        return True
    return all(page.character_count < MIN_PAGE_TEXT_CHARS for page in pages)


def _from_engine(path: Path, password: str | None) -> PdfDocumentText | None:
    try:
        from pdf_extractor_engine import (  # type: ignore[import-not-found]
            ExtractionOptions,
            ExtractionRequest,
            ExtractionSource,
            SourceKind,
            extract_pdf,
            fingerprint_source_bytes,
        )
    except ImportError:
        return None
    data = path.read_bytes()
    source = ExtractionSource(
        source_kind=SourceKind.PATH,
        source_name=path.name,
        path=path,
        content_length=len(data),
        source_fingerprint=fingerprint_source_bytes(data),
        password=password,
    )
    result = extract_pdf(ExtractionRequest(source=source, options=ExtractionOptions(normalize_whitespace=True)))
    pages = tuple(
        PageText(
            page_number=int(page.page_number),
            text=str(page.text or ""),
            character_count=len(str(page.text or "").strip()),
            warnings=(),
        )
        for page in result.pages
    )
    warnings = ["OCR_REQUIRED"] if _insufficient_text(pages) else ()
    encrypted = bool(getattr(result.document, "encrypted", False))
    if encrypted and not any(str(page.text or "").strip() for page in result.pages):
        raise PdfExtractionError("UNSUPPORTED_ENCRYPTION", "PDF is encrypted and no authorized password was accepted.")
    return PdfDocumentText(
        source_path=str(path),
        source_document_id=_sha256_file(path),
        source_title=path.stem,
        page_count=len(pages),
        pages=pages,
        extraction_method="pdf_extractor_engine",
        extractor_version=EXTRACTOR_VERSION,
        warnings=tuple(warnings),
        encrypted=encrypted,
    )


def _from_pypdf(path: Path, password: str | None) -> PdfDocumentText:
    from pypdf import PdfReader
    from pypdf.errors import FileNotDecryptedError, PdfReadError

    try:
        reader = PdfReader(str(path))
    except PdfReadError as error:
        raise PdfExtractionError("UNREADABLE_PDF", f"PDF could not be read: {error}") from error
    if reader.is_encrypted:
        if not password:
            raise PdfExtractionError("UNSUPPORTED_ENCRYPTION", "PDF is encrypted; authorized password is required.")
        try:
            decrypted = reader.decrypt(password)
        except Exception as error:  # pragma: no cover - pypdf raises several decrypt errors
            raise PdfExtractionError(
                "UNSUPPORTED_ENCRYPTION", f"PDF encryption could not be unlocked: {error}"
            ) from error
        if decrypted == 0:
            raise PdfExtractionError(
                "UNSUPPORTED_ENCRYPTION", "PDF encryption could not be unlocked with the supplied password."
            )
    pages: list[PageText] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except FileNotDecryptedError as error:
            raise PdfExtractionError("UNSUPPORTED_ENCRYPTION", str(error)) from error
        except Exception:
            pages.append(PageText(page_number=index, text="", character_count=0, warnings=("UNREADABLE_PAGE",)))
            continue
        stripped = text.strip()
        page_warnings = ("INSUFFICIENT_TEXT",) if len(stripped) < MIN_PAGE_TEXT_CHARS else ()
        pages.append(PageText(page_number=index, text=text, character_count=len(stripped), warnings=page_warnings))
    document_pages = tuple(pages)
    document_warnings: list[str] = []
    if _insufficient_text(document_pages):
        document_warnings.append("OCR_REQUIRED")
    return PdfDocumentText(
        source_path=str(path),
        source_document_id=_sha256_file(path),
        source_title=path.stem,
        page_count=len(document_pages),
        pages=document_pages,
        extraction_method="pypdf",
        extractor_version=EXTRACTOR_VERSION,
        warnings=tuple(document_warnings),
    )


def extract_pdf_pages(path: Path, *, password: str | None = None) -> PdfDocumentText:
    if not path.exists():
        raise PdfExtractionError("MISSING_PDF", f"PDF not found: {path}")
    engine_document = _from_engine(path, password)
    if engine_document is not None:
        return engine_document
    return _from_pypdf(path, password)


def document_as_dict(document: PdfDocumentText) -> dict[str, Any]:
    return {
        "source_path": document.source_path,
        "source_document_id": document.source_document_id,
        "source_title": document.source_title,
        "page_count": document.page_count,
        "extraction_method": document.extraction_method,
        "extractor_version": document.extractor_version,
        "warnings": list(document.warnings),
    }
