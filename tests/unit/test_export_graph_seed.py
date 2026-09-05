# -*- coding: utf-8 -*-
import unittest
import json
from pathlib import Path
from app.core.config import settings

class TestGraphSeedExport(unittest.TestCase):
    def test_exported_graph_seed_structure(self):
        seed_path = settings.KNOWLEDGE_GRAPH_FILE
        self.assertTrue(seed_path.exists(), f"Missing {seed_path}")
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        
        self.assertIn("knowledge_points", data)
        self.assertIn("edges", data)
        self.assertIn("student_records", data)
        
        # 严格验证 30 个知识点
        self.assertEqual(len(data["knowledge_points"]), 30)
        self.assertIn("K01", data["knowledge_points"])
        self.assertIn("K30", data["knowledge_points"])
        
        # 严格验证 42 条前置依赖边
        self.assertEqual(len(data["edges"]), 42)
        
        # 严格验证 S001-S005 五名学生的 60 条学习记录
        self.assertEqual(set(data["student_records"].keys()), {"S001", "S002", "S003", "S004", "S005"})
        total_records = sum(len(recs) for recs in data["student_records"].values())
        self.assertEqual(total_records, 60)
