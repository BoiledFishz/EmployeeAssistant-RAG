from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings kept deliberately small for the prototype."""

    app_name: str = "Employee RAG Assistant"
    default_data_path: Path = Path("data/hr.txt")
    default_tenant_id: str = "example-corp"
    default_user_groups: tuple[str, ...] = ("all-employees-cn",)
    retrieval_top_k: int = 5


settings = Settings()

