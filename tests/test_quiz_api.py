# -*- coding: utf-8 -*-
"""
test_quiz_api.py
P0-4 分知识点微测验题库与 API 单元与集成测试

覆盖 10 大核心测试用例：
1. GET /api/quiz/{knowledge_id} 正常查询，验证字段完整且严防答案泄露
2. GET /api/quiz/UNKNOWN 未知知识点返回 404
3. 题目数量与题库定义断言 (K08 至少 2~3 道题)
4. POST /api/quiz/submit 提交正确答案 (HTTP 200, is_correct=True, 返回解析)
5. POST /api/quiz/submit 提交错误答案 (HTTP 200, is_correct=False, 返回解析)
6. 提交不存在的 question_id 拦截 (HTTP 404, 不产生事件)
7. 提交非法选项 key 拦截 (HTTP 422, 不产生事件)
8. 答题成功自动触发 LearningEvent (QUESTION_ATTEMPT 落盘)
9. Event 中 knowledge_id 必须由服务端权威确定 (防客户端篡改)
10. 题库数据结构完整性离线校验 (无重复 ID, 知识点 100% 存在, 答案合法)
"""

import json
import tempfile
import unittest
import importlib
from pathlib import Path

from fastapi.testclient import TestClient

import bkt_state_service
import event_service
import quiz_service
_api_module = importlib.import_module("04_api")
app = _api_module.app


class TestQuizApi(unittest.TestCase):
    def setUp(self):
        # 隔离事件与 BKT 状态落盘文件，避免污染生产环境
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_events_file = Path(self.temp_dir.name) / "test_quiz_events.jsonl"
        self.temp_states_file = Path(self.temp_dir.name) / "test_quiz_states.json"
        self.temp_processed_file = Path(self.temp_dir.name) / "test_quiz_processed.json"

        self.orig_events_file = event_service.DEFAULT_EVENTS_FILE
        self.orig_states_file = bkt_state_service.DEFAULT_STATES_FILE
        self.orig_processed_file = bkt_state_service.DEFAULT_PROCESSED_FILE

        event_service.DEFAULT_EVENTS_FILE = self.temp_events_file
        bkt_state_service.DEFAULT_STATES_FILE = self.temp_states_file
        bkt_state_service.DEFAULT_PROCESSED_FILE = self.temp_processed_file

        self.client = TestClient(app)

    def tearDown(self):
        event_service.DEFAULT_EVENTS_FILE = self.orig_events_file
        bkt_state_service.DEFAULT_STATES_FILE = self.orig_states_file
        bkt_state_service.DEFAULT_PROCESSED_FILE = self.orig_processed_file
        self.temp_dir.cleanup()

    def test_01_get_quiz_by_knowledge_id_success_and_no_leak(self):
        """Test 1: 查询知识点微测验题目，验证公共字段完整且绝对不泄露正确答案"""
        response = self.client.get("/api/quiz/K08")
        self.assertEqual(response.status_code, 200, f"请求失败: {response.text}")
        data = response.json()

        self.assertEqual(data["knowledge_id"], "K08")
        self.assertIn("knowledge_name", data)
        self.assertIn("questions", data)
        self.assertGreaterEqual(len(data["questions"]), 2, "K08 至少应包含 2 道测验题")

        for q in data["questions"]:
            self.assertIn("question_id", q)
            self.assertEqual(q["knowledge_id"], "K08")
            self.assertIn("stem", q)
            self.assertIn("options", q)
            self.assertIsInstance(q["options"], list)
            self.assertGreaterEqual(len(q["options"]), 2)

            # 严格安全契约：学生端查询接口绝对禁止包含 answer、correct_answer 或 explanation
            self.assertNotIn("answer", q, "致命安全漏洞：向学生暴露了 answer 字段！")
            self.assertNotIn("correct_answer", q, "致命安全漏洞：向学生暴露了 correct_answer 字段！")
            self.assertNotIn("explanation", q, "做题前不应提前暴露题目解析")

    def test_02_get_quiz_unknown_knowledge_id_404(self):
        """Test 2: 查询不存在的知识点返回明确的 404 错误"""
        response = self.client.get("/api/quiz/K_UNKNOWN_999")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)

    def test_03_quiz_question_count_and_content(self):
        """Test 3: 验证核心知识点题库数量与题目格式"""
        response = self.client.get("/api/quiz/K08")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        questions = data["questions"]
        q_ids = [q["question_id"] for q in questions]
        self.assertIn("Q-K08-01", q_ids)
        self.assertIn("Q-K08-02", q_ids)

    def test_04_submit_correct_answer(self):
        """Test 4: 提交正确答案，服务端返回 is_correct=True 与题目解析"""
        # Q-K08-01 设定正确答案为 A（降价总收益增加）
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "A",
            "time_spent_ms": 4500,
        }
        response = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(response.status_code, 200, f"提交失败: {response.text}")
        res = response.json()

        self.assertEqual(res["is_correct"], True)
        self.assertEqual(res["correct_option"], "A")
        self.assertEqual(res["question_id"], "Q-K08-01")
        self.assertEqual(res["knowledge_id"], "K08")
        self.assertIn("explanation", res)
        self.assertIn("event_id", res)

    def test_05_submit_incorrect_answer(self):
        """Test 5: 提交错误答案，服务端返回 is_correct=False 与题目解析"""
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "B",  # 错误选项
            "time_spent_ms": 3800,
        }
        response = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(response.status_code, 200)
        res = response.json()

        self.assertEqual(res["is_correct"], False)
        self.assertEqual(res["correct_option"], "A")
        self.assertEqual(res["question_id"], "Q-K08-01")
        self.assertEqual(res["knowledge_id"], "K08")
        self.assertIn("explanation", res)

    def test_06_submit_invalid_question_id_404(self):
        """Test 6: 提交不存在的题目 ID 报 404，且绝不写入 LearningEvent"""
        payload = {
            "student_id": "S001",
            "question_id": "Q-NONEXISTENT-999",
            "selected_option": "A",
        }
        response = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(response.status_code, 404)

        # 验证未生成学习事件
        if self.temp_events_file.exists():
            content = self.temp_events_file.read_text(encoding="utf-8").strip()
            self.assertEqual(content, "")

    def test_07_submit_invalid_option_key_422(self):
        """Test 7: 提交非法选项 key（不在题目选项集合中）返回 422，不产生学习事件"""
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "Z",  # 非法选项
        }
        response = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(response.status_code, 422)

        # 验证未生成学习事件
        if self.temp_events_file.exists():
            content = self.temp_events_file.read_text(encoding="utf-8").strip()
            self.assertEqual(content, "")

    def test_08_submit_automatically_records_learning_event(self):
        """Test 8: 成功判题后自动生成 QUESTION_ATTEMPT 事件并落盘"""
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-02",
            "selected_option": "C",
            "time_spent_ms": 6200,
        }
        response = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(response.status_code, 200)

        # 检查事件文件落盘
        self.assertTrue(self.temp_events_file.exists())
        lines = self.temp_events_file.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)

        event_data = json.loads(lines[0])
        self.assertEqual(event_data["student_id"], "S001")
        self.assertEqual(event_data["knowledge_id"], "K08")
        self.assertEqual(event_data["event_type"], "QUESTION_ATTEMPT")
        self.assertEqual(event_data["payload"]["question_id"], "Q-K08-02")
        self.assertEqual(event_data["payload"]["selected_option"], "C")
        self.assertEqual(event_data["payload"]["time_spent_ms"], 6200)
        self.assertIn("is_correct", event_data["payload"])

    def test_09_event_knowledge_id_server_authoritative(self):
        """Test 9: 验证 LearningEvent 中的 knowledge_id 100% 由服务端题库决定"""
        # 即使客户端试图不带 knowledge_id 或提供任意值，事件仍准确绑定题库真实的 K08
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "A",
        }
        res = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(res.status_code, 200)

        events = event_service.get_student_events("S001", target_file=self.temp_events_file)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].knowledge_id, "K08")

    def test_10_offline_quiz_bank_integrity(self):
        """Test 10: 离线校验完整题库质量与真实知识点对齐度"""
        all_questions = quiz_service.get_all_questions()
        self.assertGreater(len(all_questions), 0, "题库不能为空")

        seen_ids = set()
        for q in all_questions:
            # 1. question_id 唯一
            self.assertNotIn(q.question_id, seen_ids, f"重复题目 ID: {q.question_id}")
            seen_ids.add(q.question_id)

            # 2. knowledge_id 必须存在于 30 个真实知识点中
            self.assertTrue(
                quiz_service.is_valid_knowledge_id(q.knowledge_id),
                f"题目 {q.question_id} 关联了非法知识点 {q.knowledge_id}"
            )

            # 3. 题干与解析非空
            self.assertTrue(bool(q.stem.strip()), f"{q.question_id} 题干为空")
            self.assertTrue(bool(q.explanation.strip()), f"{q.question_id} 解析为空")

            # 4. 选项格式与正确答案合法
            self.assertGreaterEqual(len(q.options), 2, f"{q.question_id} 选项少于 2 个")
            option_keys = {opt.key for opt in q.options}
            self.assertIn(
                q.answer,
                option_keys,
                f"{q.question_id} 正确答案 {q.answer} 不在选项列表 {option_keys} 中"
            )


if __name__ == "__main__":
    unittest.main()
