# -*- coding: utf-8 -*-
"""
test_bkt_api.py
P0-6 BKT 知识状态查询与事件触发 API 集成测试

覆盖 8 大核心测试用例：
1. GET /api/students/{student_id}/knowledge-state/{knowledge_id} 初次查询自动返回合法初始状态 (P(L0)=0.20, percent=20.0)
2. 查询不存在的学生抛出 404
3. 查询不存在的知识点抛出 404
4. POST /api/learning-state/update 正常更新现有 QUESTION_ATTEMPT 事件
5. POST /api/learning-state/update 重复调用同一 event_id 验证幂等性 (status="already_processed")
6. POST /api/learning-state/update 传入不存在的 event_id 返回 404
7. POST /api/learning-state/update 消费非 QUESTION_ATTEMPT 事件返回 status="ignored"
8. GET 返回模型结构与字段完整性 (mastery_probability, mastery_percent, attempts, etc.)
"""

import json
import tempfile
import unittest
import importlib
from pathlib import Path
from fastapi.testclient import TestClient

import bkt_service
import bkt_state_service
import bkt_event_processor
import event_service
from app.main import app


class TestBKTAPI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_states_file = Path(self.temp_dir.name) / "test_api_bkt_states.json"
        self.temp_processed_file = Path(self.temp_dir.name) / "test_api_processed.json"
        self.temp_events_file = Path(self.temp_dir.name) / "test_api_events.jsonl"

        # 隔离全局配置
        self.orig_states_file = bkt_state_service.DEFAULT_STATES_FILE
        self.orig_processed_file = bkt_state_service.DEFAULT_PROCESSED_FILE
        self.orig_events_file = event_service.DEFAULT_EVENTS_FILE

        bkt_state_service.DEFAULT_STATES_FILE = self.temp_states_file
        bkt_state_service.DEFAULT_PROCESSED_FILE = self.temp_processed_file
        event_service.DEFAULT_EVENTS_FILE = self.temp_events_file

        self.client = TestClient(app)

    def tearDown(self):
        if app is not None and bkt_service is not None and hasattr(bkt_service, "BKTParameters"):
            bkt_state_service.DEFAULT_STATES_FILE = self.orig_states_file
            bkt_state_service.DEFAULT_PROCESSED_FILE = self.orig_processed_file
            event_service.DEFAULT_EVENTS_FILE = self.orig_events_file
        self.temp_dir.cleanup()

    def test_01_get_initial_knowledge_state(self):
        """Test 1: S001 查询 K08 状态，若无做题记录，自动返回 P(L0)=0.20, percent=20.0"""
        res = self.client.get("/api/students/S001/knowledge-state/K08")
        self.assertEqual(res.status_code, 200, f"请求失败: {res.text}")
        data = res.json()

        self.assertEqual(data["student_id"], "S001")
        self.assertEqual(data["knowledge_id"], "K08")
        self.assertAlmostEqual(data["mastery_probability"], 0.20, places=4)
        self.assertAlmostEqual(data["mastery_percent"], 20.0, places=2)
        self.assertEqual(data["attempts"], 0)
        self.assertEqual(data["correct_attempts"], 0)
        self.assertEqual(data["incorrect_attempts"], 0)

    def test_02_get_unknown_student_404(self):
        """Test 2: 查询系统中不存在的学生 ID 返回 404"""
        res = self.client.get("/api/students/S999_UNKNOWN/knowledge-state/K08")
        self.assertEqual(res.status_code, 404)

    def test_03_get_unknown_knowledge_404(self):
        """Test 3: 查询不存在的知识点 ID 返回 404"""
        res = self.client.get("/api/students/S001/knowledge-state/K999_UNKNOWN")
        self.assertEqual(res.status_code, 404)

    def test_04_update_event_trigger(self):
        """Test 4: 先落盘一条学习事件，然后调用 POST /api/learning-state/update 触发更新"""
        # 1. 创建并记录一条 QUESTION_ATTEMPT 事件
        evt_in = event_service.LearningEventCreate(
            event_id="evt-api-01",
            student_id="S001",
            knowledge_id="K08",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-K08-01", "is_correct": True},
            client_timestamp="2026-09-05T20:30:00+08:00",
        )
        stored_evt = event_service.record_event(evt_in, target_file=self.temp_events_file)

        # 2. 调用更新接口
        res = self.client.post("/api/learning-state/update", json={"event_id": stored_evt.event_id})
        self.assertEqual(res.status_code, 200, f"更新失败: {res.text}")
        data = res.json()

        self.assertEqual(data["status"], "updated")
        self.assertEqual(data["event_id"], stored_evt.event_id)
        self.assertEqual(data["student_id"], "S001")
        self.assertEqual(data["knowledge_id"], "K08")
        self.assertTrue(data["changed"])
        self.assertAlmostEqual(data["before"], 0.20, places=4)
        self.assertGreater(data["after"], 0.20)

        # 3. 再次 GET 查询状态，断言已同步变更
        res_get = self.client.get("/api/students/S001/knowledge-state/K08")
        self.assertEqual(res_get.status_code, 200)
        state_data = res_get.json()
        self.assertEqual(state_data["attempts"], 1)
        self.assertEqual(state_data["correct_attempts"], 1)
        self.assertAlmostEqual(state_data["mastery_probability"], data["after"], places=4)

    def test_05_idempotent_api_update(self):
        """Test 5: 同一 event_id 连续两次触发 update，第二次返回 already_processed 且 changed=False"""
        evt_in = event_service.LearningEventCreate(
            event_id="evt-api-idem",
            student_id="S001",
            knowledge_id="K08",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-K08-01", "is_correct": True},
            client_timestamp="2026-09-05T20:31:00+08:00",
        )
        event_service.record_event(evt_in, target_file=self.temp_events_file)

        res1 = self.client.post("/api/learning-state/update", json={"event_id": "evt-api-idem"})
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["status"], "updated")

        res2 = self.client.post("/api/learning-state/update", json={"event_id": "evt-api-idem"})
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["status"], "already_processed")
        self.assertFalse(res2.json()["changed"])

    def test_06_nonexistent_event_404(self):
        """Test 6: 触发不存在的 event_id 返回 404"""
        res = self.client.post("/api/learning-state/update", json={"event_id": "evt-nonexistent-999"})
        self.assertEqual(res.status_code, 404)

    def test_07_ignore_non_question_attempt_event(self):
        """Test 7: 触发非 QUESTION_ATTEMPT 事件返回 ignored 且 changed=False"""
        evt_in = event_service.LearningEventCreate(
            event_id="evt-api-hint",
            student_id="S001",
            knowledge_id="K08",
            event_type="HINT_REQUEST",
            payload={"question_id": "Q-K08-01"},
            client_timestamp="2026-09-05T20:32:00+08:00",
        )
        event_service.record_event(evt_in, target_file=self.temp_events_file)

        res = self.client.post("/api/learning-state/update", json={"event_id": "evt-api-hint"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ignored")
        self.assertFalse(res.json()["changed"])

    def test_08_get_model_schema_completeness(self):
        """Test 8: 校验 GET 返回的 BKTStateResponse 字段契约完整性"""
        res = self.client.get("/api/students/S001/knowledge-state/K08")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        required_keys = [
            "student_id",
            "knowledge_id",
            "mastery_probability",
            "mastery_percent",
            "attempts",
            "correct_attempts",
            "incorrect_attempts",
            "consecutive_correct",
            "consecutive_incorrect",
            "last_updated",
            "last_event_id",
        ]
        for key in required_keys:
            self.assertIn(key, data, f"缺少关键返回字段: {key}")


if __name__ == "__main__":
    unittest.main()

