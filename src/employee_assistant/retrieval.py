from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict

from .models import Chunk, SearchHit


CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
WORD_RE = re.compile(r"[a-zA-Z0-9_-]+")


def tokenize(text: str) -> list[str]:
    tokens = [token.lower() for token in WORD_RE.findall(text)]
    for sequence in CJK_RE.findall(text):
        tokens.extend(sequence)
        tokens.extend(
            sequence[index : index + 2] for index in range(len(sequence) - 1)
        )
    return tokens


def informative_tokens(text: str) -> set[str]:
    """Tokens useful for evidence gating; Chinese unigrams are too permissive."""
    return {token for token in tokenize(text) if len(token) >= 2}


def hash_embedding(text: str, dimensions: int = 384) -> list[float]:
    """Deterministic local embedding for the demo; not a production model."""
    vector = [0.0] * dimensions
    tokens = tokenize(text)
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        index = value % dimensions
        sign = 1.0 if value & 1 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class HybridRetriever:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self._tokens = {chunk.chunk_id: tokenize(chunk.text) for chunk in chunks}
        self._vectors = {
            chunk.chunk_id: hash_embedding(chunk.text) for chunk in chunks
        }
        self._document_frequency: Counter[str] = Counter()
        for tokens in self._tokens.values():
            self._document_frequency.update(set(tokens))

    def _bm25(self, query: str, chunk: Chunk) -> float:
        query_tokens = tokenize(query)
        terms = Counter(self._tokens[chunk.chunk_id])
        document_length = max(1, sum(terms.values()))
        average_length = max(
            1,
            sum(len(tokens) for tokens in self._tokens.values()) / len(self._tokens),
        )
        score = 0.0
        k1, b = 1.5, 0.75
        for token in query_tokens:
            frequency = terms[token]
            if not frequency:
                continue
            n = self._document_frequency[token]
            idf = math.log(1 + (len(self.chunks) - n + 0.5) / (n + 0.5))
            numerator = frequency * (k1 + 1)
            denominator = frequency + k1 * (
                1 - b + b * document_length / average_length
            )
            score += idf * numerator / denominator
        return score

    def search(
        self,
        query: str,
        *,
        user_groups: list[str],
        top_k: int = 5,
        candidate_k: int = 20,
    ) -> list[SearchHit]:
        groups = set(user_groups)
        # Security boundary: unauthorized chunks never enter candidate ranking.
        visible = [
            chunk
            for chunk in self.chunks
            if not chunk.allowed_groups or chunk.allowed_groups.intersection(groups)
        ]
        query_vector = hash_embedding(query)
        dense = sorted(
            visible,
            key=lambda chunk: cosine(query_vector, self._vectors[chunk.chunk_id]),
            reverse=True,
        )[:candidate_k]
        lexical = sorted(
            visible, key=lambda chunk: self._bm25(query, chunk), reverse=True
        )[:candidate_k]

        dense_rank = {chunk.chunk_id: rank for rank, chunk in enumerate(dense, 1)}
        lexical_rank = {chunk.chunk_id: rank for rank, chunk in enumerate(lexical, 1)}
        by_id = {chunk.chunk_id: chunk for chunk in visible}
        fused: defaultdict[str, float] = defaultdict(float)
        for chunk_id, rank in dense_rank.items():
            fused[chunk_id] += 1 / (60 + rank)
        for chunk_id, rank in lexical_rank.items():
            fused[chunk_id] += 1 / (60 + rank)

        ranked_ids = sorted(fused, key=fused.get, reverse=True)[:top_k]
        return [
            SearchHit(
                chunk=by_id[chunk_id],
                score=fused[chunk_id],
                dense_rank=dense_rank.get(chunk_id),
                lexical_rank=lexical_rank.get(chunk_id),
            )
            for chunk_id in ranked_ids
        ]
