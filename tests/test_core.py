import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from employee_assistant.cache import make_cache_key
from employee_assistant.chunking import chunk_document
from employee_assistant.document_loader import load_text_document
from employee_assistant.graph import EmployeeAssistant
from employee_assistant.models import Document
from employee_assistant.retrieval import HybridRetriever
from employee_assistant.sample_data import SAMPLE_DOCUMENTS


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.chunks = [
            chunk
            for document in SAMPLE_DOCUMENTS
            for chunk in chunk_document(document)
        ]
        self.retriever = HybridRetriever(self.chunks)

    def test_structure_aware_chunking_preserves_section(self):
        document = Document(
            doc_id="x",
            title="测试",
            text="# A\n第一段。\n# B\n第二段。",
            source_url="x",
            department="HR",
            allowed_groups=frozenset(),
            version="1",
            effective_date="2026-01-01",
        )
        chunks = chunk_document(document, child_size=20, child_overlap=2)
        self.assertEqual(["A", "B"], [chunk.section for chunk in chunks])

    def test_acl_filtering_happens_before_ranking(self):
        hits = self.retriever.search(
            "薪酬校准",
            user_groups=["all-employees-cn"],
            top_k=10,
        )
        self.assertNotIn(
            "hr-manager-comp-2026", {hit.chunk.doc_id for hit in hits}
        )

    def test_manager_can_retrieve_restricted_policy(self):
        hits = self.retriever.search(
            "薪酬校准",
            user_groups=["people-managers"],
            top_k=3,
        )
        self.assertEqual("hr-manager-comp-2026", hits[0].chunk.doc_id)

    def test_unrelated_visible_policy_does_not_contain_sensitive_terms(self):
        hits = self.retriever.search(
            "经理薪酬校准规则是什么",
            user_groups=["all-employees-cn"],
            top_k=10,
        )
        self.assertFalse(
            any("薪酬校准" in hit.chunk.text for hit in hits),
            "ACL filtering must not expose restricted text",
        )

    def test_cache_key_is_acl_and_version_scoped(self):
        common = {"tenant_id": "t", "question": "年假"}
        employee = make_cache_key(
            **common, user_groups=["employee"], kb_version="v1"
        )
        manager = make_cache_key(
            **common, user_groups=["manager"], kb_version="v1"
        )
        changed = make_cache_key(
            **common, user_groups=["employee"], kb_version="v2"
        )
        self.assertNotEqual(employee, manager)
        self.assertNotEqual(employee, changed)

    def test_holiday_policy_is_in_demo_knowledge_base(self):
        hits = self.retriever.search(
            "法定节假日有哪些",
            user_groups=["all-employees-cn"],
            top_k=3,
        )
        self.assertEqual("hr-holiday-cn-2026", hits[0].chunk.doc_id)

    def test_company_name_question_does_not_return_policy_evidence(self):
        result = EmployeeAssistant().ask("公司叫什么？", thread_id="identity-test")
        self.assertEqual("identity", result["route"])
        self.assertEqual([], result["citations"])

    def test_external_hr_text_is_loaded_for_rag(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "hr.txt"
            path.write_text("# 年假\n员工每年享有十五天年假。", encoding="utf-8")
            assistant = EmployeeAssistant(source_path=path)
            result = assistant.ask("年假有多少天？", thread_id="external-file")
            self.assertEqual("grounded_answer", result["route"])
            self.assertIn("十五天", result["answer"])
            self.assertEqual("hr", result["citations"][0]["title"])

    def test_empty_external_file_fails_fast(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "hr.txt"
            path.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "文件为空"):
                load_text_document(path)


if __name__ == "__main__":
    unittest.main()
