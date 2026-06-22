from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    text: str
    source_url: str
    department: str
    allowed_groups: frozenset[str]
    version: str
    effective_date: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    section: str
    text: str
    source_url: str
    department: str
    allowed_groups: frozenset[str]
    version: str
    effective_date: str
    parent_text: str


@dataclass(frozen=True)
class SearchHit:
    chunk: Chunk
    score: float
    dense_rank: int | None = None
    lexical_rank: int | None = None


class AssistantState(TypedDict, total=False):
    question: str
    standalone_question: str
    tenant_id: str
    user_groups: list[str]
    history: list[dict[str, str]]
    cache_key: str
    cached_answer: dict[str, object] | None
    hits: list[SearchHit]
    evidence_sufficient: bool
    answer: str
    citations: list[dict[str, str]]
    route: str
    kb_version: str
    diagnostics: dict[str, object]

