# -*- coding: utf-8 -*-
"""
tests.unit.test_app_endpoints
验证 app.main 挂载的全部 18 个 API 契约端点
"""

import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

import event_service
import bkt_state_service
import path_state_service
from app.main import app


class TestAppEndpoints(unittest.TestCase):
    """测试 app.main 暴露的全部端点契约"""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.temp_events_file = Path(cls.temp_dir.name) / "test_events.jsonl"
        cls.temp_states_file = Path(cls.temp_dir.name) / "test_bkt_states.json"
        cls.temp_path_states_file = Path(cls.temp_dir.name) / "test_path_states.json"

        cls.orig_events = event_service.DEFAULT_EVENTS_FILE
        cls.orig_states = bkt_state_service.DEFAULT_STATES_FILE
        cls.orig_path_states = path_state_service.DEFAULT_PATH_STATES_FILE

        event_service.DEFAULT_EVENTS_FILE = cls.temp_events_file
        bkt_state_service.DEFAULT_STATES_FILE = cls.temp_states_file
        path_state_service.DEFAULT_PATH_STATES_FILE = cls.temp_path_states_file

        os.environ["LLM_PROVIDER"] = "mock"
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        event_service.DEFAULT_EVENTS_FILE = cls.orig_events
        bkt_state_service.DEFAULT_STATES_FILE = cls.orig_states
        path_state_service.DEFAULT_PATH_STATES_FILE = cls.orig_path_states
        cls.temp_dir.cleanup()

    # 1. Root & Health & Overview
    def test_01_root(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("message", data)
        self.assertEqual(data["version"], "0.2.0")

    def test_02_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def test_03_overview(self):
        res = self.client.get("/api/overview")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["student_count"], 5)
        self.assertEqual(len(data["students"]), 5)

    # 2. Students & Profile & Dashboard & Reports
    def test_04_students_list(self):
        res = self.client.get("/api/students")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 5)
        self.assertEqual(len(data["students"]), 5)

    def test_05_student_profile(self):
        res = self.client.get("/api/students/S001/profile")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["student"]["student_id"], "S001")

    def test_06_student_profile_not_found(self):
        res = self.client.get("/api/students/S999/profile")
        self.assertEqual(res.status_code, 404)

    def test_07_student_report(self):
        res = self.client.get("/api/students/S001/report")
        self.assertEqual(res.status_code, 200)
        self.assertIn("diagnosis", res.json())

    def test_08_all_reports(self):
        res = self.client.get("/api/reports")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 5)

    def test_09_student_dashboard(self):
        res = self.client.get("/api/students/S001/dashboard")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("profile", data)
        self.assertIn("learning_path", data)
        self.assertIn("report", data)

    # 3. Learning Paths & States
    def test_10_student_learning_path(self):
        res = self.client.get("/api/students/S001/learning-path")
        self.assertEqual(res.status_code, 200)
        self.assertIn("learning_path", res.json())

    def test_11_all_learning_paths(self):
        res = self.client.get("/api/learning-paths")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 5)

    def test_12_student_path_states(self):
        res = self.client.get("/api/students/S001/path-states")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["student_id"], "S001")
        self.assertIsInstance(data["states"], dict)

    # 4. Knowledge Graph
    def test_13_knowledge_graph(self):
        res = self.client.get("/api/students/S001/knowledge-graph")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["nodes"]), 30)
        self.assertEqual(len(data["edges"]), 42)

    # 5. Assistant
    def test_14_assistant_greeting(self):
        res = self.client.get("/api/students/S001/assistant/greeting")
        self.assertEqual(res.status_code, 200)
        self.assertIn("greeting", res.json())

    def test_15_assistant_chat(self):
        res = self.client.post(
            "/api/students/S001/assistant",
            json={"message": "我的成绩怎么样？"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("answer", data)

    def test_16_assistant_chat_empty_message(self):
        res = self.client.post(
            "/api/students/S001/assistant",
            json={"message": "   "},
        )
        self.assertEqual(res.status_code, 400)

    # 6. Events
    def test_17_events_submit(self):
        res = self.client.post(
            "/api/events",
            json={
                "event_id": "evt-app-main-001",
                "student_id": "S001",
                "knowledge_id": "K08",
                "event_type": "QUESTION_ATTEMPT",
                "payload": {"is_correct": True},
                "client_timestamp": "2026-09-06T00:00:00Z",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")

    # 7. Quiz
    def test_18_quiz_questions(self):
        res = self.client.get("/api/quiz/K08")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["knowledge_id"], "K08")
        self.assertTrue(len(data["questions"]) > 0)

    # 8. Learning State
    def test_19_knowledge_state(self):
        res = self.client.get("/api/students/S001/knowledge-state/K08")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["student_id"], "S001")
        self.assertEqual(data["knowledge_id"], "K08")
