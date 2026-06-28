from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class IngestRequest(BaseModel):
    """Payload for adding documents into the in-memory vector store."""

    text: str | None = Field(default=None, description="Raw policy text to ingest.")
    source_path: str | None = Field(
        default=None,
        description="Optional local text file path, for example data/hr.txt.",
    )
    title: str = Field(default="HR policy", description="Document title.")
    source_url: str | None = Field(default=None, description="Original document URL.")
    department: str = Field(default="HR", description="Owning department.")
    allowed_groups: list[str] = Field(
        default_factory=lambda: ["all-employees-cn"],
        description="ACL groups allowed to retrieve this document.",
    )
    version: str | None = Field(default=None, description="Knowledge version.")
    effective_date: str = Field(default="未在文档中标注")

    @model_validator(mode="after")
    def require_text_or_path(self) -> "IngestRequest":
        if not self.text and not self.source_path:
            raise ValueError("text 和 source_path 至少提供一个")
        return self


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, description="User question.")
    tenant_id: str = "example-corp"
    user_groups: list[str] = Field(default_factory=lambda: ["all-employees-cn"])
    thread_id: str = "default"
    history: list[dict[str, str]] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)

