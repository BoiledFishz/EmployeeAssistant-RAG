from __future__ import annotations

import re

from .models import Chunk, Document


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
PLAIN_HEADING_RE = re.compile(
    r"^\s*(?:第[一二三四五六七八九十百0-9]+[章节条]|"
    r"[一二三四五六七八九十]+[、.]|[0-9]+(?:\.[0-9]+)*[、.\s])\s*(.+?)\s*$",
    re.MULTILINE,
)


def _sections(text: str) -> list[tuple[str, str]]:
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        matches = list(PLAIN_HEADING_RE.finditer(text))
    if not matches:
        return [("正文", text.strip())]
    result: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        heading = match.group(match.lastindex or 1).strip()
        result.append((heading, text[start:end].strip()))
    return result


def _windows(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = max(text.rfind("。", start, end), text.rfind("\n", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return [chunk for chunk in chunks if chunk]


def chunk_document(
    document: Document,
    child_size: int = 900,
    child_overlap: int = 120,
) -> list[Chunk]:
    """Structure-aware parent-child chunks.

    Section text is retained as parent context while smaller child windows are
    indexed. In production, headings, page numbers, tables and list boundaries
    should come from a layout-aware PDF parser.
    """
    chunks: list[Chunk] = []
    for section_index, (section, parent_text) in enumerate(_sections(document.text)):
        for child_index, child_text in enumerate(
            _windows(parent_text, child_size, child_overlap)
        ):
            chunks.append(
                Chunk(
                    chunk_id=f"{document.doc_id}:{section_index}:{child_index}",
                    doc_id=document.doc_id,
                    title=document.title,
                    section=section,
                    text=f"{document.title}\n{section}\n{child_text}",
                    source_url=document.source_url,
                    department=document.department,
                    allowed_groups=document.allowed_groups,
                    version=document.version,
                    effective_date=document.effective_date,
                    parent_text=parent_text,
                )
            )
    return chunks
