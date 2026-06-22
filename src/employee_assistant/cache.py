from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass


def make_cache_key(
    *,
    tenant_id: str,
    user_groups: list[str],
    kb_version: str,
    question: str,
) -> str:
    payload = {
        "tenant": tenant_id,
        "groups": sorted(user_groups),
        "kb_version": kb_version,
        "question": " ".join(question.lower().split()),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class CacheEntry:
    value: dict[str, object]
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: int = 300, max_entries: int = 10_000):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._items: dict[str, CacheEntry] = {}

    def get(self, key: str) -> dict[str, object] | None:
        entry = self._items.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.time():
            self._items.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: dict[str, object]) -> None:
        if len(self._items) >= self.max_entries:
            oldest = min(self._items, key=lambda item: self._items[item].expires_at)
            self._items.pop(oldest, None)
        self._items[key] = CacheEntry(
            value=value, expires_at=time.time() + self.ttl_seconds
        )

