from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    id: str
    title: str
    section: str
    url: str
    version: str
    effective_date: str


class IngestResponse(BaseModel):
    document_id: str
    chunks_added: int
    kb_version: str
    message: str = "ingested"


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    route: str
    diagnostics: dict[str, object] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    app_name: str
    document_count: int
    chunk_count: int
    kb_version: str

