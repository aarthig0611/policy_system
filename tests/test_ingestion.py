"""Tests for document parsing and chunking."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from policy_system.ingestion.chunker import DocumentChunker
from policy_system.ingestion.parsers.base import ParsedDocument, ParsedPage
from policy_system.ingestion.parsers.text_parser import TextParser
from policy_system.ingestion.pipeline import chunk_document


class TestTextParser:
    def test_parse_text_file(self, tmp_path: Path):
        content = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        f = tmp_path / "test.txt"
        f.write_text(content)

        parser = TextParser()
        assert parser.supports(f)
        doc = parser.parse(f, title="Test")

        assert doc.title == "Test"
        assert doc.page_count >= 1
        assert any("Paragraph one" in p.text for p in doc.pages)

    def test_parse_markdown_file(self, tmp_path: Path):
        content = "# Header\n\nSome content.\n\n## Section 2\n\nMore content."
        f = tmp_path / "test.md"
        f.write_text(content)

        parser = TextParser()
        assert parser.supports(f)
        doc = parser.parse(f)
        assert doc.page_count >= 1

    def test_unsupported_extension(self):
        parser = TextParser()
        assert not parser.supports("file.xyz")

    def test_missing_file_raises(self):
        from policy_system.core.exceptions import IngestError
        parser = TextParser()
        with pytest.raises(IngestError):
            parser.parse("/nonexistent/path/file.txt")

    def test_empty_file_returns_no_pages(self, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        parser = TextParser()
        doc = parser.parse(f)
        assert doc.page_count == 0


class TestChunker:
    def _make_doc(self, text: str) -> ParsedDocument:
        return ParsedDocument(
            source_path="test.txt",
            title="Test Doc",
            pages=[ParsedPage(page_number=1, text=text, paragraphs=[text])],
        )

    def test_chunk_produces_chunks(self):
        doc = self._make_doc("Word " * 200)
        chunks = chunk_document(doc, "doc-1", ["role-1"])
        assert len(chunks) > 0

    def test_chunk_id_is_stable(self):
        doc = self._make_doc("Some policy text about MFA requirements.")
        c1 = chunk_document(doc, "doc-stable", ["role-1"])
        c2 = chunk_document(doc, "doc-stable", ["role-1"])
        assert [c.chunk_id for c in c1] == [c.chunk_id for c in c2]

    def test_allowed_roles_propagated(self):
        doc = self._make_doc("Policy text.")
        chunks = chunk_document(doc, "doc-2", ["role-a", "role-b"])
        for c in chunks:
            assert "role-a" in c.allowed_roles
            assert "role-b" in c.allowed_roles

    def test_is_archived_propagated(self):
        doc = self._make_doc("Archived policy text.")
        chunks = chunk_document(doc, "doc-3", ["role-1"], is_archived=True)
        assert all(c.is_archived for c in chunks)

    def test_empty_document_returns_no_chunks(self):
        doc = ParsedDocument(source_path="empty.txt", title="Empty", pages=[])
        chunks = chunk_document(doc, "doc-empty", ["role-1"])
        assert chunks == []

    def test_page_number_tracked(self):
        doc = ParsedDocument(
            source_path="test.txt",
            title="Test",
            pages=[
                ParsedPage(page_number=3, text="Page three content. " * 20, paragraphs=[]),
            ],
        )
        chunks = chunk_document(doc, "doc-4", ["role-1"])
        assert all(c.page_number == 3 for c in chunks)
