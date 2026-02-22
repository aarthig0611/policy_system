"""Abstract base class for document parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedPage:
    """A single parsed page or section from a document."""

    page_number: int
    text: str
    paragraphs: list[str] = field(default_factory=list)


@dataclass
class ParsedDocument:
    """Output from a document parser: ordered list of pages with text."""

    source_path: str
    title: str
    pages: list[ParsedPage] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)


class DocumentParser(ABC):
    """Abstract base for all document parsers."""

    @abstractmethod
    def parse(self, file_path: str | Path, title: str | None = None) -> ParsedDocument:
        """
        Parse a document file and return a ParsedDocument.

        Args:
            file_path: Path to the file to parse.
            title: Optional display title; falls back to filename if None.

        Returns:
            ParsedDocument with pages and paragraphs populated.
        """
        ...

    @abstractmethod
    def supports(self, file_path: str | Path) -> bool:
        """Return True if this parser handles the given file type."""
        ...
