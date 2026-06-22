from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from .cache import TTLCache, make_cache_key
from .chunking import chunk_document
from .document_loader import load_text_document
from .models import AssistantState, SearchHit
from .retrieval import HybridRetriever, informative_tokens
from .sample_data import SAMPLE_DOCUMENTS


FOLLOW_UP_RE = re.compile(r"^(那|那么|它|这个|这种|上述|如果|还有|what about)", re.I)
GREETING_RE = re.compile(r"^(你好|您好|hello|hi|嗨)[！!。.？?\s]*$", re.I)
IDENTITY_RE = re.compile(
    r"(公司(叫|名称|名字)|你是谁|你叫什么|what.*company|who are you)", re.I
)


class EmployeeAssistant:
    def __init__(
        self,
        *,
        source_path: str | Path | None = None,
        kb_version: str | None = None,
    ):
        documents = (
            [load_text_document(source_path)]
            if source_path is not None
            else SAMPLE_DOCUMENTS
        )
        chunks = [
            chunk
            for document in documents
            for chunk in chunk_document(document)
        ]
        if not chunks:
            raise ValueError("知识库没有产生任何可检索文本块。")
        self.retriever = HybridRetriever(chunks)
        self.cache = TTLCache(ttl_seconds=300)
        self.kb_version = kb_version or "|".join(
            sorted({chunk.version for chunk in chunks})
        )
        self.source_path = str(Path(source_path).resolve()) if source_path else None
        self.graph = self._build_graph()

    def _rewrite_query(self, state: AssistantState) -> dict[str, Any]:
        question = state["question"].strip()
        history = state.get("history", [])
        standalone = question
        if history and FOLLOW_UP_RE.search(question):
            previous_questions = [
                item["content"]
                for item in history
                if item.get("role") == "user" and item.get("content")
            ]
            if previous_questions:
                standalone = f"{previous_questions[-1]}；追问：{question}"
        cache_key = make_cache_key(
            tenant_id=state.get("tenant_id", "default"),
            user_groups=state.get("user_groups", []),
            kb_version=self.kb_version,
            question=standalone,
        )
        return {
            "standalone_question": standalone,
            "cache_key": cache_key,
            "kb_version": self.kb_version,
        }

    @staticmethod
    def _after_rewrite(state: AssistantState) -> str:
        question = state["question"].strip()
        if GREETING_RE.fullmatch(question):
            return "smalltalk"
        if IDENTITY_RE.search(question):
            return "identity"
        return "cache_lookup"

    @staticmethod
    def _smalltalk(_: AssistantState) -> dict[str, Any]:
        return {
            "answer": (
                "你好！我是企业雇员助手。你可以问我年假、病假、法定节假日、"
                "调休、上海办公室交通报销等演示政策问题。"
            ),
            "citations": [],
            "route": "smalltalk",
            "diagnostics": {"cache_hit": False},
        }

    @staticmethod
    def _identity(_: AssistantState) -> dict[str, Any]:
        return {
            "answer": (
                "我是这个项目中的企业雇员助手原型。当前演示知识库没有配置"
                "公司正式名称，因此我不能可靠回答公司叫什么。"
            ),
            "citations": [],
            "route": "identity",
            "diagnostics": {"cache_hit": False},
        }

    def _cache_lookup(self, state: AssistantState) -> dict[str, Any]:
        return {"cached_answer": self.cache.get(state["cache_key"])}

    @staticmethod
    def _after_cache(state: AssistantState) -> str:
        return "cache_hit" if state.get("cached_answer") else "retrieve"

    @staticmethod
    def _use_cached_answer(state: AssistantState) -> dict[str, Any]:
        cached = state["cached_answer"] or {}
        return {
            "answer": cached.get("answer", ""),
            "citations": cached.get("citations", []),
            "route": "cache_hit",
            "diagnostics": {"cache_hit": True},
        }

    def _retrieve(self, state: AssistantState) -> dict[str, Any]:
        hits = self.retriever.search(
            state["standalone_question"],
            user_groups=state.get("user_groups", []),
            top_k=5,
        )
        return {"hits": hits, "diagnostics": {"cache_hit": False}}

    @staticmethod
    def _grade_evidence(state: AssistantState) -> dict[str, Any]:
        hits = state.get("hits", [])
        query_terms = informative_tokens(state["standalone_question"])
        best_overlap = 0.0
        for hit in hits:
            chunk_terms = informative_tokens(hit.chunk.text)
            best_overlap = max(
                best_overlap,
                len(query_terms & chunk_terms) / max(1, len(query_terms)),
            )
        sufficient = bool(hits) and best_overlap >= 0.18
        diagnostics = dict(state.get("diagnostics", {}))
        diagnostics.update({"best_term_overlap": round(best_overlap, 3)})
        return {"evidence_sufficient": sufficient, "diagnostics": diagnostics}

    @staticmethod
    def _after_grade(state: AssistantState) -> str:
        return "answer" if state.get("evidence_sufficient") else "refuse"

    @staticmethod
    def _answer(state: AssistantState) -> dict[str, Any]:
        hits: list[SearchHit] = state.get("hits", [])
        query_terms = informative_tokens(state["standalone_question"])
        supported_hits = [
            hit
            for hit in hits
            if query_terms.intersection(informative_tokens(hit.chunk.text))
        ]
        top = supported_hits[:3]
        evidence = []
        citations = []
        for index, hit in enumerate(top, 1):
            text = hit.chunk.text.split("\n", 2)[-1].strip()
            evidence.append(f"[{index}] {text}")
            citations.append(
                {
                    "id": str(index),
                    "title": hit.chunk.title,
                    "section": hit.chunk.section,
                    "url": hit.chunk.source_url,
                    "version": hit.chunk.version,
                    "effective_date": hit.chunk.effective_date,
                }
            )
        answer = "根据当前可访问的公司政策：\n\n" + "\n\n".join(evidence)
        answer += "\n\n请以引用原文及其生效日期为准；涉及个人例外情况请联系 HR/行政。"
        return {"answer": answer, "citations": citations, "route": "grounded_answer"}

    @staticmethod
    def _refuse(_: AssistantState) -> dict[str, Any]:
        return {
            "answer": (
                "我在你当前有权限访问的政策中没有找到足够证据，因此不猜测答案。"
                "请补充地区、部门或政策名称，或联系 HR/行政确认。"
            ),
            "citations": [],
            "route": "insufficient_evidence",
        }

    def _cache_write(self, state: AssistantState) -> dict[str, Any]:
        if state.get("route") == "grounded_answer":
            self.cache.set(
                state["cache_key"],
                {
                    "answer": state["answer"],
                    "citations": state.get("citations", []),
                },
            )
        return {}

    def _build_graph(self):
        workflow = StateGraph(AssistantState)
        workflow.add_node("rewrite_query", self._rewrite_query)
        workflow.add_node("smalltalk", self._smalltalk)
        workflow.add_node("identity", self._identity)
        workflow.add_node("cache_lookup", self._cache_lookup)
        workflow.add_node("use_cached_answer", self._use_cached_answer)
        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("grade_evidence", self._grade_evidence)
        workflow.add_node("answer", self._answer)
        workflow.add_node("refuse", self._refuse)
        workflow.add_node("cache_write", self._cache_write)

        workflow.add_edge(START, "rewrite_query")
        workflow.add_conditional_edges(
            "rewrite_query",
            self._after_rewrite,
            {
                "smalltalk": "smalltalk",
                "identity": "identity",
                "cache_lookup": "cache_lookup",
            },
        )
        workflow.add_edge("smalltalk", END)
        workflow.add_edge("identity", END)
        workflow.add_conditional_edges(
            "cache_lookup",
            self._after_cache,
            {"cache_hit": "use_cached_answer", "retrieve": "retrieve"},
        )
        workflow.add_edge("use_cached_answer", END)
        workflow.add_edge("retrieve", "grade_evidence")
        workflow.add_conditional_edges(
            "grade_evidence",
            self._after_grade,
            {"answer": "answer", "refuse": "refuse"},
        )
        workflow.add_edge("answer", "cache_write")
        workflow.add_edge("cache_write", END)
        workflow.add_edge("refuse", END)
        return workflow.compile(checkpointer=InMemorySaver())

    def ask(
        self,
        question: str,
        *,
        thread_id: str = "demo",
        tenant_id: str = "example-corp",
        user_groups: list[str] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> AssistantState:
        return self.graph.invoke(
            {
                "question": question,
                "tenant_id": tenant_id,
                "user_groups": user_groups or ["all-employees-cn"],
                "history": history or [],
            },
            config={"configurable": {"thread_id": thread_id}},
        )
