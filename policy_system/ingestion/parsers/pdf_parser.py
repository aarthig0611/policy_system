"""PDF parser using pypdf — page-level text extraction with paragraph detection."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from policy_system.core.exceptions import IngestError
from policy_system.ingestion.parsers.base import DocumentParser, ParsedDocument, ParsedPage


def _split_paragraphs(text: str) -> list[str]:
    """Split page text into paragraphs by blank lines, stripping empties."""
    paragraphs = re.split(r"\n{2,}", text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


class PDFParser(DocumentParser):
    """Parse PDF files using pypdf. Extracts text page-by-page."""

    def supports(self, file_path: str | Path) -> bool:
        return Path(file_path).suffix.lower() == ".pdf"

    def parse(self, file_path: str | Path, title: str | None = None) -> ParsedDocument:
        path = Path(file_path)
        if not path.exists():
            raise IngestError(f"File not found: {file_path}")
        if not self.supports(path):
            raise IngestError(f"PDFParser does not support file type: {path.suffix}")

        display_title = title or path.stem

        try:
            reader = PdfReader(str(path))
        except Exception as exc:
            raise IngestError(f"Failed to open PDF {file_path}: {exc}") from exc

        pages = []
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                raw_text = page.extract_text() or ""
            except Exception:
                raw_text = ""

            paragraphs = _split_paragraphs(raw_text)
            pages.append(
                ParsedPage(
                    page_number=page_num,
                    text=raw_text.strip(),
                    paragraphs=paragraphs,
                )
            )

        return ParsedDocument(source_path=str(path), title=display_title, pages=pages)
