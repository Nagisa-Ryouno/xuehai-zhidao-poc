# -*- coding: utf-8 -*-
"""
tests/unit/test_knowledge_graph_service.py
知识图谱服务公共契约与学生图谱生成单元测试
"""

import unittest
from app.services.knowledge_graph_service import knowledge_graph_service


class TestKnowledgeGraphServiceContract(unittest.TestCase):
    def test_public_query_methods(self):
        self.assertTrue(knowledge_graph_service.is_valid_knowledge_id("K08"))
        self.assertFalse(knowledge_graph_service.is_valid_knowledge_id("INVALID_ID"))

        # 校验 K08 (需求价格弹性) 前置与后继
        prereqs = knowledge_graph_service.get_prerequisites("K08")
        successors = knowledge_graph_service.get_successors("K08")
        self.assertIn("K04", prereqs)
        self.assertIn("K09", successors)
        self.assertIn("K11", successors)

        kp = knowledge_graph_service.get_knowledge_point("K08")
        self.assertIsNotNone(kp)
        self.assertEqual(kp["knowledge_name"], "需求价格弹性")

        all_ids = knowledge_graph_service.get_all_knowledge_point_ids()
        self.assertEqual(len(all_ids), 30)
        self.assertIn("K01", all_ids)
        self.assertIn("K30", all_ids)

    def test_student_graph_generation(self):
        graph = knowledge_graph_service.get_student_knowledge_graph("S001")
        self.assertEqual(graph["student_id"], "S001")
        self.assertEqual(graph["stats"]["total_nodes"], 30)
        self.assertEqual(graph["stats"]["total_edges"], 42)
        self.assertEqual(len(graph["nodes"]), 30)
        self.assertEqual(len(graph["edges"]), 42)
