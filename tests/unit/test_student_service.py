# -*- coding: utf-8 -*-
"""
tests/unit/test_student_service.py
学生与学习路径应用服务单元测试
"""

import unittest
from app.services.student_service import student_service
from app.services.path_service import path_service


class TestStudentAndPathService(unittest.TestCase):
    def test_student_dashboard_aggregation(self):
        dashboard = student_service.get_student_dashboard("S001")
        self.assertIsNotNone(dashboard)
        self.assertEqual(dashboard["student_id"], "S001")
        self.assertIn("profile", dashboard)
        self.assertIn("learning_path", dashboard)
        self.assertIn("report", dashboard)
        self.assertEqual(dashboard["profile"]["student"]["student_name"], "张同学")

    def test_nonexistent_student_dashboard_returns_none(self):
        dashboard = student_service.get_student_dashboard("S999")
        self.assertIsNone(dashboard)

    def test_system_overview(self):
        overview = student_service.get_system_overview()
        self.assertEqual(overview["student_count"], 5)
        self.assertEqual(len(overview["students"]), 5)

    def test_learning_path_service(self):
        path_data = path_service.get_student_learning_path("S001")
        self.assertIsNotNone(path_data)
        self.assertIn("learning_path", path_data)
        all_paths = path_service.get_all_learning_paths()
        self.assertEqual(len(all_paths), 5)
