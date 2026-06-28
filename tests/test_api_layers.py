import unittest

from app.repositories.vector_store import VectorStoreRepository
from app.schemas.request import IngestRequest, QueryRequest
from app.services.ingest_service import IngestService
from app.services.rag_service import RagService


class ApiLayerTests(unittest.TestCase):
    def setUp(self):
        self.vector_store = VectorStoreRepository()
        self.ingest_service = IngestService(self.vector_store)
        self.rag_service = RagService(self.vector_store)

    def test_ingest_then_query_returns_grounded_answer(self):
        ingest_result = self.ingest_service.ingest(
            IngestRequest(
                title="HR政策",
                text="# 年假\n员工每年享有十五天年假。年假申请至少提前三个工作日提交。",
                allowed_groups=["all-employees-cn"],
            )
        )

        self.assertGreater(ingest_result.chunks_added, 0)
        result = self.rag_service.query(
            QueryRequest(
                question="年假有多少天？",
                user_groups=["all-employees-cn"],
            )
        )

        self.assertEqual("grounded_answer", result.route)
        self.assertIn("十五天", result.answer)
        self.assertEqual("HR政策", result.citations[0].title)

    def test_query_without_ingested_documents_refuses(self):
        result = self.rag_service.query(QueryRequest(question="年假多少天？"))

        self.assertEqual("insufficient_evidence", result.route)
        self.assertEqual([], result.citations)

    def test_repository_acl_filters_before_ranking(self):
        self.ingest_service.ingest(
            IngestRequest(
                title="经理薪酬政策",
                text="# 校准\n年度薪酬校准仅 people managers 和 HR 可见。",
                allowed_groups=["people-managers", "hr"],
            )
        )

        employee_result = self.rag_service.query(
            QueryRequest(
                question="薪酬校准规则是什么？",
                user_groups=["all-employees-cn"],
            )
        )
        manager_result = self.rag_service.query(
            QueryRequest(
                question="薪酬校准规则是什么？",
                user_groups=["people-managers"],
            )
        )

        self.assertEqual("insufficient_evidence", employee_result.route)
        self.assertEqual("grounded_answer", manager_result.route)


if __name__ == "__main__":
    unittest.main()
