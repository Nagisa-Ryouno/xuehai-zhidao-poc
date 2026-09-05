# -*- coding: utf-8 -*-
"""
test_quiz_bkt_integration.py
P0-7：Quiz -> Event -> BKT 自动化流式闭环端到端集成测试

覆盖 10 大核心测试用例：
1. Test 1: 答对题目自动触发 BKT 更新 (无需额外调用 update 接口，mastery > 0.20)
2. Test 2: 答错题目自动触发 BKT 更新 (mastery < 0.20)
3. Test 3: 连续三次作答自动流式演进 (Wrong -> Right -> Right => 0.8118)
4. Test 4: 学习事件确实持久化至 JSONL (含完整 student_id, knowledge_id, time_spent_ms)
5. Test 5: BKT 状态确实持久化至 JSON (bkt_states.json 存在 S001:K08 记录)
6. Test 6: 重复消费 event_id 不产生二次更新 (严格幂等保证)
7. Test 7: Quiz API 返回结果包含闭环确认字段与原有判题契约完整性
8. Test 8: 提交无效题目 ID 报 404，严禁产生 Event，严禁变更 BKT
9. Test 9: 提交非法选项报 422，严禁产生 Event，严禁变更 BKT
10. Test 10: BKT 处理异常时保留原始 Event (事实来源)，但绝不伪装更新成功
"""

import json
import tempfile
import unittest
import importlib
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

import event_service
import quiz_service
import bkt_service
import bkt_state_service
import bkt_event_processor

from app.main import app


class TestQuizBKTIntegration(unittest.TestCase):
    def setUp(self):
        # 创建完全隔离的测试临时目录与文件
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_events_file = Path(self.temp_dir.name) / "test_p07_events.jsonl"
        self.temp_states_file = Path(self.temp_dir.name) / "test_p07_states.json"
        self.temp_processed_file = Path(self.temp_dir.name) / "test_p07_processed.json"

        # 备份全局路径配置
        self.orig_events_file = event_service.DEFAULT_EVENTS_FILE
        self.orig_states_file = bkt_state_service.DEFAULT_STATES_FILE
        self.orig_processed_file = bkt_state_service.DEFAULT_PROCESSED_FILE

        # 重定向全局配置至隔离环境
        event_service.DEFAULT_EVENTS_FILE = self.temp_events_file
        bkt_state_service.DEFAULT_STATES_FILE = self.temp_states_file
        bkt_state_service.DEFAULT_PROCESSED_FILE = self.temp_processed_file

        self.client = TestClient(app)

    def tearDown(self):
        # 恢复全局配置并清理临时目录
        event_service.DEFAULT_EVENTS_FILE = self.orig_events_file
        bkt_state_service.DEFAULT_STATES_FILE = self.orig_states_file
        bkt_state_service.DEFAULT_PROCESSED_FILE = self.orig_processed_file
        self.temp_dir.cleanup()

    def test_01_submit_correct_answer_automatically_updates_bkt(self):
        """Test 1: 答对自动触发 BKT 更新 (无需额外调用 update 接口，mastery > 0.20)"""
        # Q-K08-01 正确答案为 A
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "A",
            "time_spent_ms": 4250,
        }
        response = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(response.status_code, 200, f"提交失败: {response.text}")
        data = response.json()
        self.assertTrue(data["is_correct"])

        # 核心断言：不需要再调用 /api/learning-state/update，BKT 状态必须已被自动更新
        bkt_state = bkt_state_service.get_state(
            "S001", "K08", states_file=self.temp_states_file, auto_init=False
        )
        self.assertEqual(bkt_state.attempts, 1)
        self.assertEqual(bkt_state.correct_attempts, 1)
        self.assertEqual(bkt_state.incorrect_attempts, 0)
        self.assertEqual(bkt_state.consecutive_correct, 1)
        # 单次答对理论手算值: 9.8 / 17 ≈ 0.576470588
        expected_mastery = 9.8 / 17.0
        self.assertAlmostEqual(bkt_state.mastery_probability, expected_mastery, places=5)
        self.assertGreater(bkt_state.mastery_probability, 0.20)

    def test_02_submit_incorrect_answer_automatically_updates_bkt(self):
        """Test 2: 答错自动触发 BKT 更新 (mastery 由 0.20 下降至约 0.1273)"""
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "B",  # 错误选项
            "time_spent_ms": 3100,
        }
        response = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["is_correct"])

        bkt_state = bkt_state_service.get_state(
            "S001", "K08", states_file=self.temp_states_file, auto_init=False
        )
        self.assertEqual(bkt_state.attempts, 1)
        self.assertEqual(bkt_state.correct_attempts, 0)
        self.assertEqual(bkt_state.incorrect_attempts, 1)
        self.assertEqual(bkt_state.consecutive_incorrect, 1)
        # 单次答错理论手算值: 4.2 / 33 ≈ 0.1272727
        expected_mastery = 4.2 / 33.0
        self.assertAlmostEqual(bkt_state.mastery_probability, expected_mastery, places=5)
        self.assertLess(bkt_state.mastery_probability, 0.20)

    def test_03_three_consecutive_attempts_automatic_streaming(self):
        """Test 3: 连续三次作答自动流式演进 (Wrong -> Right -> Right => 0.8118)"""
        # 1. 错 (Q-K08-01 选 B)
        res1 = self.client.post("/api/quiz/submit", json={
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "B",
            "time_spent_ms": 2500,
        })
        self.assertEqual(res1.status_code, 200)

        # 2. 对 (Q-K08-01 选 A)
        res2 = self.client.post("/api/quiz/submit", json={
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "A",
            "time_spent_ms": 3200,
        })
        self.assertEqual(res2.status_code, 200)

        # 3. 对 (Q-K08-02 选 C)
        res3 = self.client.post("/api/quiz/submit", json={
            "student_id": "S001",
            "question_id": "Q-K08-02",
            "selected_option": "C",
            "time_spent_ms": 4100,
        })
        self.assertEqual(res3.status_code, 200)

        # 查询最终状态
        final_state = bkt_state_service.get_state(
            "S001", "K08", states_file=self.temp_states_file, auto_init=False
        )
        self.assertEqual(final_state.attempts, 3)
        self.assertEqual(final_state.correct_attempts, 2)
        self.assertEqual(final_state.incorrect_attempts, 1)
        self.assertEqual(final_state.consecutive_correct, 2)
        # 与 P0-6 已验证的三步数学推导结果严格一致
        self.assertAlmostEqual(final_state.mastery_probability, 0.8118, places=3)

    def test_04_learning_event_persistence_verification(self):
        """Test 4: 学习事件确实持久化至 JSONL (含完整 student_id, knowledge_id, time_spent_ms)"""
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "A",
            "time_spent_ms": 5200,
        }
        res = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(res.status_code, 200)
        event_id = res.json()["event_id"]

        # 检查持久化事件文件
        self.assertTrue(self.temp_events_file.exists())
        lines = self.temp_events_file.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)

        event_obj = json.loads(lines[0])
        self.assertEqual(event_obj["event_id"], event_id)
        self.assertEqual(event_obj["student_id"], "S001")
        self.assertEqual(event_obj["knowledge_id"], "K08")
        self.assertEqual(event_obj["event_type"], "QUESTION_ATTEMPT")
        self.assertEqual(event_obj["payload"]["question_id"], "Q-K08-01")
        self.assertEqual(event_obj["payload"]["is_correct"], True)
        self.assertEqual(event_obj["payload"]["time_spent_ms"], 5200)
        self.assertIn("server_timestamp", event_obj)

    def test_05_bkt_state_persistence_verification(self):
        """Test 5: BKT 状态确实持久化至 JSON (bkt_states.json 存在 S001:K08 记录)"""
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "A",
        }
        res = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(res.status_code, 200)
        event_id = res.json()["event_id"]

        self.assertTrue(self.temp_states_file.exists())
        states_dict = json.loads(self.temp_states_file.read_text(encoding="utf-8"))
        self.assertIn("S001:K08", states_dict)
        entry = states_dict["S001:K08"]
        self.assertEqual(entry["student_id"], "S001")
        self.assertEqual(entry["knowledge_id"], "K08")
        self.assertEqual(entry["last_event_id"], event_id)
        self.assertEqual(entry["attempts"], 1)

    def test_06_idempotent_event_replay(self):
        """Test 6: 重复消费 event_id 不产生二次更新 (严格幂等保证)"""
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "A",
        }
        res = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(res.status_code, 200)
        event_id = res.json()["event_id"]

        # 获取当前状态
        state_after_submit = bkt_state_service.get_state(
            "S001", "K08", states_file=self.temp_states_file
        )
        self.assertEqual(state_after_submit.attempts, 1)
        mastery_once = state_after_submit.mastery_probability

        # 模拟重复触发同一 event_id 的消费
        dup_event = bkt_event_processor.find_event_by_id(
            event_id, events_file=self.temp_events_file
        )
        self.assertIsNotNone(dup_event)
        dup_res = bkt_event_processor.process_event(
            dup_event,
            states_file=self.temp_states_file,
            processed_file=self.temp_processed_file,
        )
        self.assertEqual(dup_res.status, "already_processed")
        self.assertFalse(dup_res.changed)

        # 检查 BKT 状态未发生二次更新
        state_after_dup = bkt_state_service.get_state(
            "S001", "K08", states_file=self.temp_states_file
        )
        self.assertEqual(state_after_dup.attempts, 1)
        self.assertAlmostEqual(state_after_dup.mastery_probability, mastery_once, places=6)

    def test_07_quiz_submit_response_contract_and_closed_loop_confirmation(self):
        """Test 7: Quiz API 返回结果保留原有判题字段并包含 learning_state 闭环信息"""
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "A",
            "time_spent_ms": 3500,
        }
        res = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # 原有契约必须 100% 保持
        self.assertIn("is_correct", data)
        self.assertIn("correct_option", data)
        self.assertIn("explanation", data)
        self.assertIn("knowledge_id", data)
        self.assertIn("question_id", data)
        self.assertIn("event_id", data)

        # 增量闭环字段确认
        self.assertIn("learning_state", data)
        self.assertIsNotNone(data["learning_state"])
        self.assertTrue(data["learning_state"]["updated"])
        self.assertAlmostEqual(
            data["learning_state"]["mastery_probability"], 9.8 / 17.0, places=5
        )

    def test_08_invalid_question_id_does_not_trigger_bkt(self):
        """Test 8: 提交无效题目 ID 报 404，严禁产生 Event，严禁变更 BKT"""
        payload = {
            "student_id": "S001",
            "question_id": "Q-NONEXISTENT-999",
            "selected_option": "A",
        }
        res = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(res.status_code, 404)

        # 严禁写入事件
        if self.temp_events_file.exists():
            self.assertEqual(self.temp_events_file.read_text(encoding="utf-8").strip(), "")

        # 严禁生成/修改 BKT 状态
        if self.temp_states_file.exists():
            states = json.loads(self.temp_states_file.read_text(encoding="utf-8"))
            self.assertEqual(len(states), 0)

    def test_09_invalid_option_key_does_not_trigger_bkt(self):
        """Test 9: 提交非法选项报 422，严禁产生 Event，严禁变更 BKT"""
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "Z",
        }
        res = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(res.status_code, 422)

        # 严禁写入事件与状态
        if self.temp_events_file.exists():
            self.assertEqual(self.temp_events_file.read_text(encoding="utf-8").strip(), "")
        if self.temp_states_file.exists():
            states = json.loads(self.temp_states_file.read_text(encoding="utf-8"))
            self.assertEqual(len(states), 0)

    def test_10_bkt_failure_does_not_fake_success(self):
        """Test 10: BKT 处理异常时保留原始 Event (事实来源)，但绝不伪装更新成功"""
        # 模拟 BKT Processor 在处理时抛出异常
        with patch.object(
            bkt_event_processor,
            "process_event",
            side_effect=RuntimeError("Simulated BKT storage disk failure"),
        ):
            payload = {
                "student_id": "S001",
                "question_id": "Q-K08-01",
                "selected_option": "A",
            }
            res = self.client.post("/api/quiz/submit", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()

            # 核心断言：Event 必须依然成功保存！(事实来源不丢失)
            self.assertTrue(self.temp_events_file.exists())
            event_id = data["event_id"]
            saved_event = bkt_event_processor.find_event_by_id(
                event_id, events_file=self.temp_events_file
            )
            self.assertIsNotNone(saved_event, "即使 BKT 失败，Event 必须完整持久化！")

            # 核心断言：绝不伪装更新成功 (updated 必须为 False)
            self.assertIn("learning_state", data)
            self.assertFalse(data["learning_state"]["updated"])
            self.assertIsNone(data["learning_state"]["mastery_probability"])


if __name__ == "__main__":
    unittest.main()
