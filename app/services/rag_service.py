from __future__ import annotations

import re

from app.repositories.vector_store import VectorStoreRepository
from app.schemas.request import QueryRequest
from app.schemas.response import Citation, QueryResponse
from employee_assistant.cache import TTLCache, make_cache_key
from employee_assistant.models import SearchHit
from employee_assistant.retrieval import informative_tokens


FOLLOW_UP_RE = re.compile(r"^(那个|那么|这个|这种|上述|如果|还有|what about)", re.I)
GREETING_RE = re.compile(r"^(你好|您好|hello|hi|嗨)[！!。.\s]*$", re.I)
IDENTITY_RE = re.compile(r"(公司(叫|名称|名字)|你是谁|你叫什么|what.*company|who are you)", re.I)


class RagService:
    """RAG orchestration layer.

    This keeps business decisions out of the routers: query rewriting, cache,
    retrieval, evidence gating, answer construction and refusal behavior.
    """

    def __init__(self, vector_store: VectorStoreRepository) -> None:
        self.vector_store = vector_store
        self.cache = TTLCache(ttl_seconds=300)

    def query(self, request: QueryRequest) -> QueryResponse:
        question = request.question.strip()
        standalone_question = self._rewrite_follow_up(question, request.history)

        if GREETING_RE.fullmatch(question):
            return QueryResponse(
                answer="你好！我是企业雇员助手，可以回答 HR、行政、报销、休假和公司政策相关问题。",
                route="smalltalk",
                diagnostics={"cache_hit": False},
            )

        if IDENTITY_RE.search(question):
            return QueryResponse(
                answer="我是这个项目中的企业雇员助手原型。当前知识库未配置公司正式名称，所以我不能猜测公司叫什么。",
                route="identity",
                diagnostics={"cache_hit": False},
            )

        cache_key = make_cache_key(
            tenant_id=request.tenant_id,
            user_groups=request.user_groups,
            kb_version=self.vector_store.kb_version,
            question=standalone_question,
        )
        cached = self.cache.get(cache_key)
        if cached:
            return QueryResponse(
                answer=str(cached.get("answer", "")),
                citations=[Citation(**item) for item in cached.get("citations", [])],
                route="cache_hit",
                diagnostics={"cache_hit": True},
            )

        hits = self.vector_store.search(
            standalone_question,
            user_groups=request.user_groups,
            top_k=request.top_k,
        )
        sufficient, best_overlap = self._has_sufficient_evidence(
            standalone_question, hits
        )
        if not sufficient:
            return QueryResponse(
                answer="我在你当前有权限访问的政策中没有找到足够证据，因此不猜测答案。请补充地区、部门或政策名称，或联系 HR/行政确认。",
                route="insufficient_evidence",
                diagnostics={
                    "cache_hit": False,
                    "best_term_overlap": round(best_overlap, 3),
                    "kb_version": self.vector_store.kb_version,
                },
            )

        response = self._build_grounded_answer(standalone_question, hits)
        self.cache.set(
            cache_key,
            {
                "answer": response.answer,
                "citations": [citation.model_dump() for citation in response.citations],
            },
        )
        response.diagnostics.update(
            {
                "cache_hit": False,
                "best_term_overlap": round(best_overlap, 3),
                "kb_version": self.vector_store.kb_version,
            }
        )
        return response

    @staticmethod
    def _rewrite_follow_up(
        question: str, history: list[dict[str, str]]
    ) -> str:
        if not history or not FOLLOW_UP_RE.search(question):
            return question
        previous_questions = [
            item["content"]
            for item in history
            if item.get("role") == "user" and item.get("content")
        ]
        if not previous_questions:
            return question
        return f"{previous_questions[-1]}；追问：{question}"

    @staticmethod
    def _has_sufficient_evidence(
        question: str, hits: list[SearchHit]
    ) -> tuple[bool, float]:
        query_terms = informative_tokens(question)
        best_overlap = 0.0
        for hit in hits:
            chunk_terms = informative_tokens(hit.chunk.text)
            best_overlap = max(
                best_overlap,
                len(query_terms & chunk_terms) / max(1, len(query_terms)),
            )
        return bool(hits) and best_overlap >= 0.18, best_overlap

    @staticmethod
    def _build_grounded_answer(
        question: str, hits: list[SearchHit]
    ) -> QueryResponse:
        query_terms = informative_tokens(question)
        supported_hits = [
            hit for hit in hits if query_terms.intersection(informative_tokens(hit.chunk.text))
        ]
        evidence: list[str] = []
        citations: list[Citation] = []
        for index, hit in enumerate(supported_hits[:3], 1):
            text = hit.chunk.text.split("\n", 2)[-1].strip()
            evidence.append(f"[{index}] {text}")
            citations.append(
                Citation(
                    id=str(index),
                    title=hit.chunk.title,
                    section=hit.chunk.section,
                    url=hit.chunk.source_url,
                    version=hit.chunk.version,
                    effective_date=hit.chunk.effective_date,
                )
            )

        answer = "根据当前可访问的公司政策：\n\n" + "\n\n".join(evidence)
        answer += "\n\n请以引用原文及其生效日期为准；涉及个人例外情况请联系 HR/行政。"
        return QueryResponse(
            answer=answer,
            citations=citations,
            route="grounded_answer",
            diagnostics={},
        )

