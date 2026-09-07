# -*- coding: utf-8 -*-
"""
tests.architecture.test_data_lifecycle
Invariant 06: 数据生命周期三层隔离架构适应度测试

验证规则：
1. data/raw/：必须包含原始数据源 economics_learning_demo.xlsx，作为只读离线源。
2. data/seeds/：必须包含全套冷启动种子数据（5个核心 JSON 文件）：
   - student_profiles.json (5 名学生 S001~S005)
   - learning_paths.json (5 条初始学习路径)
   - student_reports.json (5 份学情报告)
   - quiz_bank.json (8 个核心考点 / 13 道试题)
   - knowledge_graph.json (30 个知识点 K01~K30, 42 条前置依赖边, 60 条学生学习记录)
3. data/runtime/：运行时动态生成数据必须且只能存在于 runtime 目录，且 git-tracked 文件数严格为 0。
"""

import json
import subprocess
import unittest
from pathlib import Path

from app.core.config import settings


class TestDataLifecycle(unittest.TestCase):
    """数据生命周期三层物理隔离测试"""

    def test_raw_data_layer_exists(self):
        """验证 data/raw/ 包含原始 Excel 资产"""
        self.assertTrue(settings.RAW_DIR.exists(), "data/raw/ 目录不存在")
        excel_file = settings.RAW_DIR / "economics_learning_demo.xlsx"
        self.assertTrue(excel_file.exists(), f"缺失原始 Excel 文件: {excel_file}")
        self.assertGreater(excel_file.stat().st_size, 0, "原始 Excel 文件为空")

    def test_seeds_data_layer_complete_and_valid(self):
        """验证 data/seeds/ 包含完整合法的 5 份只读种子数据"""
        self.assertTrue(settings.SEEDS_DIR.exists(), "data/seeds/ 目录不存在")

        # 1. student_profiles.json
        profiles_file = settings.SEEDS_DIR / "student_profiles.json"
        self.assertTrue(profiles_file.exists(), "缺失 student_profiles.json 种子")
        profiles = json.loads(profiles_file.read_text(encoding="utf-8"))
        self.assertEqual(len(profiles), 5, "student_profiles 种子必须包含 5 个学生")
        self.assertEqual(set(profiles.keys()), {"S001", "S002", "S003", "S004", "S005"})

        # 2. learning_paths.json
        paths_file = settings.SEEDS_DIR / "learning_paths.json"
        self.assertTrue(paths_file.exists(), "缺失 learning_paths.json 种子")
        paths = json.loads(paths_file.read_text(encoding="utf-8"))
        self.assertEqual(len(paths), 5, "learning_paths 种子必须包含 5 个学生的路径")

        # 3. student_reports.json
        reports_file = settings.SEEDS_DIR / "student_reports.json"
        self.assertTrue(reports_file.exists(), "缺失 student_reports.json 种子")
        reports = json.loads(reports_file.read_text(encoding="utf-8"))
        self.assertEqual(len(reports), 5, "student_reports 种子必须包含 5 份报告")

        # 4. quiz_bank.json (8 知识点 / 13 道题)
        quiz_file = settings.SEEDS_DIR / "quiz_bank.json"
        self.assertTrue(quiz_file.exists(), "缺失 quiz_bank.json 种子")
        quizzes = json.loads(quiz_file.read_text(encoding="utf-8"))
        self.assertEqual(len(quizzes), 13, "quiz_bank 种子必须严格保持 13 道题")
        covered_kps = {q["knowledge_id"] for q in quizzes}
        self.assertEqual(len(covered_kps), 8, "quiz_bank 种子必须覆盖 8 个考点")

        # 5. knowledge_graph.json (30 节点 / 42 边 / 60 条学习记录)
        kg_file = settings.SEEDS_DIR / "knowledge_graph.json"
        self.assertTrue(kg_file.exists(), "缺失 knowledge_graph.json 种子")
        kg = json.loads(kg_file.read_text(encoding="utf-8"))
        self.assertEqual(len(kg.get("knowledge_points", {})), 30, "知识图谱必须包含 30 个考点 (K01~K30)")
        self.assertEqual(len(kg.get("edges", [])), 42, "知识图谱必须包含 42 条前置边")
        total_records = sum(len(r) for r in kg.get("student_records", {}).values())
        self.assertEqual(total_records, 60, "知识图谱必须包含 60 条学生历史学习记录")

    def test_runtime_data_layer_untracked_by_git(self):
        """验证 data/runtime/ 下零 Git 追踪文件，确保动态产物不污染代码库"""
        result = subprocess.run(
            ["git", "ls-files", "data/runtime"],
            capture_output=True,
            text=True,
            cwd=str(settings.PROJECT_ROOT),
        )
        tracked_files = [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]
        self.assertEqual(
            tracked_files,
            [],
            f"data/runtime/ 目录下存在被 Git 追踪的运行时文件: {tracked_files}",
        )
