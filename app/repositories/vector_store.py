from __future__ import annotations

import hashlib
from pathlib import Path

from employee_assistant.chunking import chunk_document
from employee_assistant.document_loader import read_text_file
from employee_assistant.models import Chunk, Document, SearchHit
from employee_assistant.retrieval import HybridRetriever


class VectorStoreRepository:
    """Repository layer for vector/BM25 storage and retrieval.

    The prototype keeps everything in memory. In production this class is the
    replacement seam for OpenSearch, Elasticsearch, Milvus, pgvector, etc.
    """

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._chunks: list[Chunk] = []
        self._retriever: HybridRetriever | None = None
        self.kb_version = "empty"

    @property
    def document_count(self) -> int:
        return len(self._documents)

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def ingest_text(
        self,
        *,
        text: str,
        title: str,
        source_url: str,
        department: str,
        allowed_groups: list[str],
        version: str | None,
        effective_date: str,
    ) -> tuple[Document, int]:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("知识库文本为空，请先提供 HR/行政/政策文档内容")

        content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
        document = Document(
            doc_id=f"doc-{content_hash[:16]}",
            title=title,
            text=clean_text,
            source_url=source_url,
            department=department,
            allowed_groups=frozenset(allowed_groups),
            version=version or content_hash[:12],
            effective_date=effective_date,
        )
        chunks = chunk_document(document)

        self._documents[document.doc_id] = document
        existing_ids = {chunk.chunk_id for chunk in chunks}
        self._chunks = [
            chunk for chunk in self._chunks if chunk.chunk_id not in existing_ids
        ]
        self._chunks.extend(chunks)
        self._rebuild_index()
        return document, len(chunks)

    def ingest_file(
        self,
        *,
        source_path: str,
        title: str | None,
        department: str,
        allowed_groups: list[str],
        version: str | None,
        effective_date: str,
    ) -> tuple[Document, int]:
        path = Path(source_path).expanduser().resolve()
        text, _ = read_text_file(path)
        return self.ingest_text(
            text=text,
            title=title or path.stem,
            source_url=path.as_uri(),
            department=department,
            allowed_groups=allowed_groups,
            version=version,
            effective_date=effective_date,
        )

    def search(
        self,
        query: str,
        *,
        user_groups: list[str],
        top_k: int,
    ) -> list[SearchHit]:
        if self._retriever is None:
            return []
        return self._retriever.search(query, user_groups=user_groups, top_k=top_k)

    def _rebuild_index(self) -> None:
        self._retriever = HybridRetriever(self._chunks) if self._chunks else None
        versions = sorted({chunk.version for chunk in self._chunks})
        self.kb_version = "|".join(versions) if versions else "empty"

