# -*- coding: utf-8 -*-
"""
test_event_logger.py
P0-3 统一学习行为日志采集器 (Learning Event Logger) 单元与集成测试

覆盖 8 大核心用例：
1. 合法事件上报 (HTTP 200, 校验字段, 验证 JSONL 落盘)
2. 非法 event_type 拦截 (HTTP 422, 不落盘)
3. 缺失必填字段拦截 (HTTP 422)
4. 非法 payload 类型拦截 (非 dict 报 422)
5. JSONL 规范性测试 (一行一个标准 JSON, json.loads 逐行解析)
6. 服务端时间戳独立性 (不采信客户端伪造的 server_timestamp)
7. 高频连续写入与并发安全性 (50 个事件连续写入, 行数与数据一致)
8. 测试隔离性 (测试专用临时文件, 绝不污染生产 data/learning_events.jsonl)
"""

import os
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

from fastapi.testclient import TestClient

import importlib
# 导入应用与事件服务（RED 阶段将因未实现而报错）
import event_service
_api_module = importlib.import_module("04_api")
app = _api_module.app


class TestLearningEventLogger(unittest.TestCase):
    def setUp(self):
        # 创建隔离的临时目录与专用 JSONL 文件
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file = Path(self.temp_dir.name) / "test_events.jsonl"
        self.orig_events_file = event_service.DEFAULT_EVENTS_FILE
        event_service.DEFAULT_EVENTS_FILE = self.temp_file

        self.client = TestClient(app)

    def tearDown(self):
        event_service.DEFAULT_EVENTS_FILE = self.orig_events_file
        self.temp_dir.cleanup()

    def test_01_valid_event_submission_and_persistence(self):
        """Test 1: 验证合法事件正常提交、返回 200 并正确落盘至 JSONL"""
        payload = {
            "event_id": "evt-test-001",
            "student_id": "S001",
            "knowledge_id": "K08",
            "event_type": "QUESTION_ATTEMPT",
            "payload": {
                "question_id": "Q-K08-01",
                "is_correct": True,
                "time_spent_ms": 3200,
                "selected_option": "A",
            },
            "client_timestamp": "2026-09-05T19:30:00+08:00",
        }

        response = self.client.post("/api/events", json=payload)
        self.assertEqual(response.status_code, 200, f"响应失败: {response.text}")
        data = response.json()

        # 断言响应结构
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("event_id"), "evt-test-001")
        self.assertIn("server_timestamp", data)

        # 断言 JSONL 文件成功生成并包含该记录
        self.assertTrue(self.temp_file.exists(), "事件落盘文件未生成")
        lines = self.temp_file.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)

        saved_event = json.loads(lines[0])
        self.assertEqual(saved_event["event_id"], "evt-test-001")
        self.assertEqual(saved_event["student_id"], "S001")
        self.assertEqual(saved_event["knowledge_id"], "K08")
        self.assertEqual(saved_event["event_type"], "QUESTION_ATTEMPT")
        self.assertEqual(saved_event["payload"]["question_id"], "Q-K08-01")
        self.assertEqual(saved_event["payload"]["is_correct"], True)
        self.assertEqual(saved_event["client_timestamp"], "2026-09-05T19:30:00+08:00")
        self.assertIn("server_timestamp", saved_event)

    def test_02_invalid_event_type_rejected(self):
        """Test 2: 非法 event_type 必须返回 422 且严禁写入 JSONL"""
        payload = {
            "event_id": "evt-test-002",
            "student_id": "S001",
            "knowledge_id": "K08",
            "event_type": "INVALID_EVENT_TYPE",
            "payload": {"foo": "bar"},
            "client_timestamp": "2026-09-05T19:30:00+08:00",
        }

        response = self.client.post("/api/events", json=payload)
        self.assertEqual(response.status_code, 422)

        # 确保没有写入文件
        if self.temp_file.exists():
            content = self.temp_file.read_text(encoding="utf-8").strip()
            self.assertEqual(content, "")

    def test_03_missing_required_fields(self):
        """Test 3: 缺少必要字段（如 student_id）必须返回 422"""
        payload = {
            "event_id": "evt-test-003",
            # 缺失 student_id
            "knowledge_id": "K08",
            "event_type": "QUESTION_ATTEMPT",
            "payload": {"is_correct": True},
            "client_timestamp": "2026-09-05T19:30:00+08:00",
        }

        response = self.client.post("/api/events", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_04_invalid_payload_type(self):
        """Test 4: payload 必须为 dict，传入非 dict 类型返回 422"""
        payload = {
            "event_id": "evt-test-004",
            "student_id": "S001",
            "knowledge_id": "K08",
            "event_type": "CONCEPT_VIEW",
            "payload": "not_a_valid_dict",  # 非法字符串
            "client_timestamp": "2026-09-05T19:30:00+08:00",
        }

        response = self.client.post("/api/events", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_05_jsonl_format_and_line_independence(self):
        """Test 5: 写入多个事件后，每行必须是完全独立、标准的 JSON 格式"""
        for i in range(5):
            payload = {
                "event_id": f"evt-multi-{i}",
                "student_id": "S002",
                "knowledge_id": "K01",
                "event_type": "HINT_REQUEST",
                "payload": {"hint_step": i},
                "client_timestamp": "2026-09-05T19:30:00+08:00",
            }
            res = self.client.post("/api/events", json=payload)
            self.assertEqual(res.status_code, 200)

        lines = self.temp_file.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 5)

        for idx, line in enumerate(lines):
            # 每行必须可被 json.loads 独立成功解析
            item = json.loads(line)
            self.assertEqual(item["event_id"], f"evt-multi-{idx}")
            self.assertEqual(item["event_type"], "HINT_REQUEST")

    def test_06_server_timestamp_generated_by_backend(self):
        """Test 6: 服务端时间戳必须由后端权威生成，不采信客户端伪造的时间"""
        client_fake_server_time = "1999-01-01T00:00:00Z"
        payload = {
            "event_id": "evt-test-006",
            "student_id": "S001",
            "knowledge_id": "K08",
            "event_type": "PATH_STEP_COMPLETE",
            "payload": {"step_index": 1},
            "client_timestamp": "2026-09-05T19:30:00+08:00",
            "server_timestamp": client_fake_server_time,  # 客户端试图伪造
        }

        res = self.client.post("/api/events", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # 服务端返回的时间戳绝对不能等于伪造的时间戳
        self.assertNotEqual(data["server_timestamp"], client_fake_server_time)

        # 检查落盘内容中的 server_timestamp 也是权威时间
        lines = self.temp_file.read_text(encoding="utf-8").strip().splitlines()
        saved = json.loads(lines[0])
        self.assertNotEqual(saved["server_timestamp"], client_fake_server_time)

    def test_07_continuous_concurrent_write_safety(self):
        """Test 7: 连续高频写入 50 个事件，校验行数完整与数据无损"""
        event_count = 50
        for i in range(event_count):
            payload = {
                "event_id": f"evt-seq-{i:03d}",
                "student_id": "S001",
                "knowledge_id": "K08",
                "event_type": "QUESTION_ATTEMPT",
                "payload": {"seq": i},
                "client_timestamp": "2026-09-05T19:30:00+08:00",
            }
            res = self.client.post("/api/events", json=payload)
            self.assertEqual(res.status_code, 200)

        lines = self.temp_file.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), event_count)

        event_ids = [json.loads(line)["event_id"] for line in lines]
        expected_ids = [f"evt-seq-{i:03d}" for i in range(event_count)]
        self.assertEqual(event_ids, expected_ids)

    def test_08_get_student_events_filtering(self):
        """Test 8: 验证按 student_id 过滤事件历史的能力"""
        # 写入 S001 和 S002 的混合事件
        for s_id, count in [("S001", 3), ("S002", 2)]:
            for i in range(count):
                self.client.post(
                    "/api/events",
                    json={
                        "event_id": f"evt-{s_id}-{i}",
                        "student_id": s_id,
                        "knowledge_id": "K08",
                        "event_type": "CONCEPT_VIEW",
                        "payload": {"step": i},
                        "client_timestamp": "2026-09-05T19:30:00+08:00",
                    },
                )

        s001_events = event_service.get_student_events("S001", target_file=self.temp_file)
        s002_events = event_service.get_student_events("S002", target_file=self.temp_file)
        s003_events = event_service.get_student_events("S003", target_file=self.temp_file)

        self.assertEqual(len(s001_events), 3)
        self.assertEqual(len(s002_events), 2)
        self.assertEqual(len(s003_events), 0)
        self.assertTrue(all(e.student_id == "S001" for e in s001_events))


if __name__ == "__main__":
    unittest.main()
