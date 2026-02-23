"""Plain text / Markdown parser — splits by blank lines into paragraphs, groups into pages."""

from __future__ import annotations

import re
from pathlib import Path

from backend.core.exceptions import IngestError
from backend.ingestion.parsers.base import DocumentParser, ParsedDocument, ParsedPage

_SUPPORTED = {".txt", ".md", ".markdown", ".rst"}
_PARAS_PER_PAGE = 15


class TextParser(DocumentParser):
    """Parse plain text and Markdown files."""

    def supports(self, file_path: str | Path) -> bool:
        return Path(file_path).suffix.lower() in _SUPPORTED

    def parse(self, file_path: str | Path, title: str | None = None) -> ParsedDocument:
        path = Path(file_path)
        if not path.exists():
            raise IngestError(f"File not found: {file_path}")
        if not self.supports(path):
            raise IngestError(f"TextParser does not support file type: {path.suffix}")

        display_title = title or path.stem

        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            raise IngestError(f"Failed to read {file_path}: {exc}") from exc

        all_paragraphs = [p.strip() for p in re.split(r"\n{2,}", raw) if p.strip()]

        if not all_paragraphs:
            return ParsedDocument(source_path=str(path), title=display_title, pages=[])

        pages = []
        for page_idx, start in enumerate(range(0, len(all_paragraphs), _PARAS_PER_PAGE), start=1):
            chunk_paras = all_paragraphs[start : start + _PARAS_PER_PAGE]
            page_text = "\n\n".join(chunk_paras)
            pages.append(
                ParsedPage(
                    page_number=page_idx,
                    text=page_text,
                    paragraphs=chunk_paras,
                )
            )

        return ParsedDocument(source_path=str(path), title=display_title, pages=pages)
