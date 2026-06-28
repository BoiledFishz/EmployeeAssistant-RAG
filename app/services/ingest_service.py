from __future__ import annotations

from app.repositories.vector_store import VectorStoreRepository
from app.schemas.request import IngestRequest
from app.schemas.response import IngestResponse


class IngestService:
    """Business logic for loading documents into the knowledge base."""

    def __init__(self, vector_store: VectorStoreRepository) -> None:
        self.vector_store = vector_store

    def ingest(self, request: IngestRequest) -> IngestResponse:
        if request.source_path:
            document, chunks_added = self.vector_store.ingest_file(
                source_path=request.source_path,
                title=request.title,
                department=request.department,
                allowed_groups=request.allowed_groups,
                version=request.version,
                effective_date=request.effective_date,
            )
        else:
            document, chunks_added = self.vector_store.ingest_text(
                text=request.text or "",
                title=request.title,
                source_url=request.source_url or "memory://manual-ingest",
                department=request.department,
                allowed_groups=request.allowed_groups,
                version=request.version,
                effective_date=request.effective_date,
            )

        return IngestResponse(
            document_id=document.doc_id,
            chunks_added=chunks_added,
            kb_version=self.vector_store.kb_version,
        )

