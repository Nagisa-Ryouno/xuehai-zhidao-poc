# -*- coding: utf-8 -*-
"""
test_quiz_replanning_integration.py
P0-8 Task 5: 测验答题闭环与路径重规划 API 集成测试

测试用例：
1. test_01_submit_quiz_triggers_replanning_in_response:
   提交作答，断言响应包含完整的 replanning (canonical_payload 与 audit_metadata)；
2. test_02_get_student_path_states_endpoint:
   验证 GET /api/students/{id}/path-states 返回 200 及对应节点状态字典；
3. test_03_nonexistent_student_path_states_404:
   验证查询未知学生路径状态返回 404；
4. test_04_direct_service_dependency_injection:
   直接调用 submit_quiz_answer 传入 path_states_file 与 states_file，验证显式依赖注入有效，状态正确写入传入文件。
"""

import importlib
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

import bkt_service
import bkt_state_service
import event_service
import path_replanning_service
from path_replanning_service import PathAction, ReplanningReasonCode
import path_state_service
from path_state_service import PathState
import quiz_service

_api_mod = importlib.import_module("04_api")
app = _api_mod.app


class TestQuizReplanningIntegration(unittest.TestCase):
    def setUp(self):
        # 隔离事件、BKT 状态与路径状态落盘文件
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_events_file = Path(self.temp_dir.name) / "test_events.jsonl"
        self.temp_bkt_states_file = Path(self.temp_dir.name) / "test_bkt_states.json"
        self.temp_processed_file = Path(self.temp_dir.name) / "test_processed.json"
        self.temp_path_states_file = Path(self.temp_dir.name) / "test_path_states.json"

        # 备份全局路径
        self.orig_events_file = event_service.DEFAULT_EVENTS_FILE
        self.orig_bkt_states_file = bkt_state_service.DEFAULT_STATES_FILE
        self.orig_processed_file = bkt_state_service.DEFAULT_PROCESSED_FILE
        self.orig_path_states_file = path_state_service.DEFAULT_PATH_STATES_FILE

        # 重定向全局路径
        event_service.DEFAULT_EVENTS_FILE = self.temp_events_file
        bkt_state_service.DEFAULT_STATES_FILE = self.temp_bkt_states_file
        bkt_state_service.DEFAULT_PROCESSED_FILE = self.temp_processed_file
        path_state_service.DEFAULT_PATH_STATES_FILE = self.temp_path_states_file

        self.client = TestClient(app)

    def tearDown(self):
        # 恢复全局路径
        event_service.DEFAULT_EVENTS_FILE = self.orig_events_file
        bkt_state_service.DEFAULT_STATES_FILE = self.orig_bkt_states_file
        bkt_state_service.DEFAULT_PROCESSED_FILE = self.orig_processed_file
        path_state_service.DEFAULT_PATH_STATES_FILE = self.orig_path_states_file
        self.temp_dir.cleanup()

    def test_01_submit_quiz_triggers_replanning_in_response(self):
        """Test 1: 提交作答，断言响应包含完整的 replanning (canonical_payload 与 audit_metadata)"""
        payload = {
            "student_id": "S001",
            "question_id": "Q-K08-01",
            "selected_option": "A",
            "time_spent_ms": 3000,
        }
        response = self.client.post("/api/quiz/submit", json=payload)
        self.assertEqual(response.status_code, 200, f"提交失败: {response.text}")
        data = response.json()

        self.assertIn("replanning", data, "响应中必须包含 replanning 字段")
        self.assertIsNotNone(data["replanning"], "replanning 字段不能为 None")
        replanning = data["replanning"]

        # 断言独立审计元数据
        self.assertIn("audit_metadata", replanning)
        audit = replanning["audit_metadata"]
        self.assertIn("decision_id", audit)
        self.assertIn("timestamp", audit)
        self.assertEqual(audit["trace_id"], data["event_id"], "trace_id 必须与 event_id 一致")

        # 断言确定性规范业务载荷
        self.assertIn("canonical_payload", replanning)
        canonical = replanning["canonical_payload"]
        self.assertEqual(canonical["rule_version"], "v1.0")
        self.assertEqual(canonical["student_id"], "S001")
        self.assertEqual(canonical["knowledge_id"], "K08")
        self.assertIn("before_mastery", canonical)
        self.assertIn("after_mastery", canonical)
        self.assertIn("before_path_state", canonical)
        self.assertIn("after_path_state", canonical)
        self.assertIn("action", canonical)
        self.assertIn("reason_code", canonical)
        self.assertIn("affected_nodes", canonical)

    def test_02_get_student_path_states_endpoint(self):
        """Test 2: 验证 GET /api/students/{id}/path-states 返回 200 及对应节点状态字典"""
        # 预设指定状态
        path_state_service.set_path_state(
            "S001", "K01", PathState.AVAILABLE, states_file=self.temp_path_states_file
        )
        path_state_service.set_path_state(
            "S001", "K02", PathState.LOCKED, states_file=self.temp_path_states_file
        )

        response = self.client.get("/api/students/S001/path-states")
        self.assertEqual(response.status_code, 200, f"查询失败: {response.text}")
        data = response.json()

        self.assertEqual(data["student_id"], "S001")
        self.assertIn("states", data)
        self.assertIsInstance(data["states"], dict)
        self.assertEqual(data["states"].get("K01"), "AVAILABLE")
        self.assertEqual(data["states"].get("K02"), "LOCKED")

    def test_03_nonexistent_student_path_states_404(self):
        """Test 3: 验证查询未知学生路径状态返回 404"""
        response = self.client.get("/api/students/S_NONEXISTENT_999/path-states")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)

    def test_04_direct_service_dependency_injection(self):
        """Test 4: 直接调用 submit_quiz_answer 传入 path_states_file 与 states_file，验证显式依赖注入有效，状态正确写入传入文件"""
        custom_dir = Path(self.temp_dir.name) / "custom_injection"
        custom_dir.mkdir(parents=True, exist_ok=True)
        custom_path_states_file = custom_dir / "custom_path_states.json"
        custom_bkt_states_file = custom_dir / "custom_bkt_states.json"
        custom_events_file = custom_dir / "custom_events.jsonl"
        custom_processed_file = custom_dir / "custom_processed.json"

        # 初始路径状态: K01 为 IN_PROGRESS, K02 为 LOCKED
        path_state_service.set_path_state(
            "S001", "K01", PathState.IN_PROGRESS, states_file=custom_path_states_file
        )
        path_state_service.set_path_state(
            "S001", "K02", PathState.LOCKED, states_file=custom_path_states_file
        )

        # 初始 BKT 状态: K01 接近掌握门槛 (0.75)
        bkt_state_service.save_state(
            bkt_service.BKTState(
                student_id="S001",
                knowledge_id="K01",
                mastery_probability=0.75,
                attempts=2,
                correct_attempts=2,
                incorrect_attempts=0,
                consecutive_correct=2,
                consecutive_incorrect=0,
            ),
            states_file=custom_bkt_states_file,
        )

        # Q-K01-01 正确答案为 B
        req = quiz_service.QuizSubmitRequest(
            student_id="S001",
            question_id="Q-K01-01",
            selected_option="B",
        )

        resp = quiz_service.submit_quiz_answer(
            req,
            events_file=custom_events_file,
            states_file=custom_bkt_states_file,
            processed_file=custom_processed_file,
            path_states_file=custom_path_states_file,
        )

        # 验证返回的 replanning 信封
        self.assertIsNotNone(resp.replanning, "直接调用服务并注入参数时，应返回 replanning 信封")
        canonical = resp.replanning.canonical_payload
        self.assertEqual(canonical.action, PathAction.UNLOCK_DOWNSTREAM)
        self.assertEqual(canonical.reason_code, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED)
        self.assertEqual(canonical.after_path_state, PathState.COMPLETED)

        # 验证状态正确写入传入的 custom_path_states_file
        self.assertTrue(custom_path_states_file.exists(), "注入的 path_states_file 必须已生成")
        k01_state = path_state_service.get_path_state("S001", "K01", states_file=custom_path_states_file)
        k02_state = path_state_service.get_path_state("S001", "K02", states_file=custom_path_states_file)
        self.assertEqual(k01_state, PathState.COMPLETED)
        self.assertEqual(k02_state, PathState.AVAILABLE)

        # 验证全局默认路径文件未被修改
        default_k01 = path_state_service.get_path_state("S001", "K01", states_file=self.temp_path_states_file)
        self.assertNotEqual(default_k01, PathState.COMPLETED)
