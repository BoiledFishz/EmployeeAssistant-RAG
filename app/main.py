from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.config.settings import settings
from app.repositories.vector_store import VectorStoreRepository
from app.routers import ingest, query
from app.schemas.request import IngestRequest
from app.schemas.response import HealthResponse
from app.services.ingest_service import IngestService
from app.services.rag_service import RagService


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    vector_store = VectorStoreRepository()
    ingest_service = IngestService(vector_store)
    rag_service = RagService(vector_store)

    default_path = settings.default_data_path
    if default_path.exists() and default_path.is_file() and default_path.stat().st_size > 0:
        ingest_service.ingest(
            IngestRequest(
                source_path=str(default_path),
                title=default_path.stem,
                allowed_groups=list(settings.default_user_groups),
            )
        )

    app.state.vector_store = vector_store
    app.state.ingest_service = ingest_service
    app.state.rag_service = rag_service

    app.include_router(ingest.router)
    app.include_router(query.router)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        store: VectorStoreRepository = app.state.vector_store
        return HealthResponse(
            status="ok",
            app_name=settings.app_name,
            document_count=store.document_count,
            chunk_count=store.chunk_count,
            kb_version=store.kb_version,
        )

    return app


app = create_app()

