from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from extraction.pages import PdfExtractionError, extract_pdf_pages
from tests.pdf_fixtures import build_encrypted_pdf_bytes, write_text_pdf


class PageExtractionTests(unittest.TestCase):
    def test_text_pdf_preserves_page_numbers_and_text(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf = write_text_pdf(
                Path(tmp) / "guide.pdf",
                [
                    "SC-900 original study page one.\nMicrosoft Entra ID manages identities.",
                    "Page two continues the original study notes.",
                ],
            )
            document = extract_pdf_pages(pdf)
            self.assertEqual(2, document.page_count)
            self.assertEqual([1, 2], [page.page_number for page in document.pages])
            self.assertIn("Microsoft Entra ID manages identities.", document.pages[0].text)
            self.assertIn("Page two continues", document.pages[1].text)
            self.assertEqual(document.pages[0].page_number, 1)
            self.assertIn(document.extraction_method, {"pypdf", "pdf_extractor_engine"})
            self.assertTrue(document.source_document_id)

    def test_insufficient_text_is_flagged_without_ocr(self) -> None:
        with TemporaryDirectory() as tmp:
            pdf = write_text_pdf(Path(tmp) / "scan.pdf", [" ", "  "])
            document = extract_pdf_pages(pdf)
            self.assertIn("OCR_REQUIRED", document.warnings)
            self.assertEqual(2, document.page_count)

    def test_encrypted_pdf_fails_closed(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "locked.pdf"
            path.write_bytes(build_encrypted_pdf_bytes("secret"))
            with self.assertRaises(PdfExtractionError) as error:
                extract_pdf_pages(path)
            self.assertEqual("UNSUPPORTED_ENCRYPTION", error.exception.code)


if __name__ == "__main__":
    unittest.main()
