from __future__ import annotations

import hashlib
from pathlib import Path

from .models import Document


SUPPORTED_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030")


def read_text_file(path: str | Path) -> tuple[str, str]:
    source = Path(path).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"知识库文件不存在：{source}")
    if not source.is_file():
        raise ValueError(f"知识库路径不是文件：{source}")
    if source.stat().st_size == 0:
        raise ValueError(
            f"知识库文件为空：{source}。请先把 HR 文档内容保存到该文件。"
        )

    raw = source.read_bytes()
    for encoding in SUPPORTED_ENCODINGS:
        try:
            text = raw.decode(encoding)
            if text.strip():
                return text.strip(), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError(
        f"无法识别知识库编码：{source}。请将文件保存为 UTF-8 或 GB18030。"
    )


def load_text_document(path: str | Path) -> Document:
    source = Path(path).expanduser().resolve()
    text, _ = read_text_file(source)
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return Document(
        doc_id=f"file-{content_hash[:16]}",
        title=source.stem,
        text=text,
        source_url=source.as_uri(),
        department="HR",
        allowed_groups=frozenset({"all-employees-cn"}),
        version=content_hash[:12],
        effective_date="未在文档中标注",
    )

