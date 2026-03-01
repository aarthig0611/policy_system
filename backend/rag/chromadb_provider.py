"""
ChromaDB implementation of the RAGProvider interface.

Security invariant: similarity_search MUST apply allowed_roles and is_archived
as pre-filters at the ChromaDB metadata level — never as post-filters in Python.

ChromaDB pre-filtering note: role-based where clauses have ~3-5x latency overhead
vs. unfiltered search, but stays sub-second at expected scale (10k-100k chunks).
This overhead is the cost of correct security — do not remove the pre-filter.

Single-process constraint: ChromaDB embedded mode is NOT safe with multiple workers.
Run uvicorn with --workers 1.
"""

from __future__ import annotations

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.config import settings
from backend.core.exceptions import RAGProviderError
from backend.core.models import Chunk, RetrievedChunk


class ChromaDBProvider:
    """
    ChromaDB-backed RAGProvider.

    Chunks are stored with metadata:
      - chunk_id: for idempotent re-ingestion
      - doc_id: links back to SQL documents table
      - doc_title: display title for citations
      - page_number, para_number: citation info
      - is_archived: archive toggle filter
      - allowed_roles_*: one boolean key per role UUID

    Role pre-filtering uses ChromaDB's metadata where clause.
    Because ChromaDB doesn't support array-contains natively, we store each
    allowed role as a separate boolean metadata key: f"role_{role_id}" = True.
    The where clause is an $or over all the user's role keys.
    """

    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        self._persist_dir = persist_dir or settings.chroma_persist_dir
        self._collection_name = collection_name or settings.chroma_collection_name
        self._client = chromadb.PersistentClient(
            path=self._persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # RAGProvider interface
    # ------------------------------------------------------------------

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """
        Add or replace chunks in ChromaDB.

        Embeddings must be pre-computed and stored in chunk.metadata["embedding"].
        Raises RAGProviderError if embeddings are missing.
        """
        if not chunks:
            return

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for chunk in chunks:
            embedding = chunk.metadata.get("embedding")
            if embedding is None:
                raise RAGProviderError(
                    f"Chunk {chunk.chunk_id} is missing embedding. "
                    "Embed chunks before calling add_chunks()."
                )

            # Build role metadata: one boolean key per allowed role
            role_meta = {f"role_{role_id}": True for role_id in chunk.allowed_roles}

            meta = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "doc_title": chunk.doc_title,
                "page_number": chunk.page_number if chunk.page_number is not None else -1,
                "para_number": chunk.para_number if chunk.para_number is not None else -1,
                "is_archived": chunk.is_archived,
                **role_meta,
            }

            ids.append(chunk.chunk_id)
            embeddings.append(embedding)
            documents.append(chunk.text)
            metadatas.append(meta)

        # ChromaDB upsert is idempotent
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def similarity_search(
        self,
        query_embedding: list[float],
        allowed_role_ids: list[str],
        top_k: int = 5,
        include_archived: bool = False,
        score_threshold: float = 0.0,
    ) -> list[RetrievedChunk]:
        """
        SECURITY-CRITICAL: role filtering happens here at the DB level.

        Constructs a ChromaDB where clause that:
        1. Filters to chunks where at least one of the user's roles is in allowed_roles
        2. Optionally excludes archived chunks

        Returns empty list (not an error) when no chunks match — the query engine
        handles the CrossDomainPermissionRequired signal.
        """
        if not allowed_role_ids:
            return []

        # Build role filter: at least one role key must be True
        if len(allowed_role_ids) == 1:
            role_filter = {f"role_{allowed_role_ids[0]}": {"$eq": True}}
        else:
            role_filter = {
                "$or": [{f"role_{rid}": {"$eq": True}} for rid in allowed_role_ids]
            }

        # Combine with archive filter
        if not include_archived:
            where = {"$and": [role_filter, {"is_archived": {"$eq": False}}]}
        else:
            where = role_filter

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            # ChromaDB raises if collection is empty or where returns no candidates
            if "no documents" in str(exc).lower() or "collection" in str(exc).lower():
                return []
            raise RAGProviderError(f"ChromaDB query failed: {exc}") from exc

        if not results or not results["ids"] or not results["ids"][0]:
            return []

        chunks = []
        for doc_text, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity score: 1 - (distance / 2)
            score = 1.0 - (distance / 2.0)

            # Drop chunks that fall below the quality threshold
            if score_threshold > 0.0 and score < score_threshold:
                continue

            page_num = meta.get("page_number", -1)
            para_num = meta.get("para_number", -1)

            chunks.append(
                RetrievedChunk(
                    chunk_id=meta.get("chunk_id", ""),
                    doc_id=meta.get("doc_id", ""),
                    doc_title=meta.get("doc_title", ""),
                    text=doc_text,
                    score=score,
                    page_number=page_num if page_num >= 0 else None,
                    para_number=para_num if para_num >= 0 else None,
                    is_archived=meta.get("is_archived", False),
                )
            )

        return chunks

    def delete_by_doc_id(self, doc_id: str) -> int:
        """Delete all chunks for a document. Returns count deleted."""
        try:
            existing = self._collection.get(where={"doc_id": {"$eq": doc_id}})
            count = len(existing["ids"])
            if count > 0:
                self._collection.delete(where={"doc_id": {"$eq": doc_id}})
            return count
        except Exception as exc:
            raise RAGProviderError(f"Failed to delete chunks for doc {doc_id}: {exc}") from exc

    def update_archived_status(self, doc_id: str, is_archived: bool) -> int:
        """Update is_archived metadata flag for all chunks of a document."""
        try:
            existing = self._collection.get(
                where={"doc_id": {"$eq": doc_id}},
                include=["metadatas", "documents", "embeddings"],
            )
            count = len(existing["ids"])
            if count == 0:
                return 0

            updated_metadatas = []
            for meta in existing["metadatas"]:
                updated_meta = {**meta, "is_archived": is_archived}
                updated_metadatas.append(updated_meta)

            self._collection.update(
                ids=existing["ids"],
                metadatas=updated_metadatas,
            )
            return count
        except Exception as exc:
            raise RAGProviderError(
                f"Failed to update archived status for doc {doc_id}: {exc}"
            ) from exc

    def get_chunk_count(self) -> int:
        """Return total number of chunks stored."""
        return self._collection.count()
