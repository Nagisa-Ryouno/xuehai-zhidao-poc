# -*- coding: utf-8 -*-
"""
tests.architecture.test_runtime_dependencies
Invariant 04 & 05: 运行时依赖轻量化与图谱数据访问收敛性测试

验证规则：
1. Invariant 04: app/ 整个运行时代码树中绝不依赖 openpyxl。
   Excel 解析属于离线数据清洗管线 (scripts/data_pipeline/)，运行时完全由 JSON 驱动。
2. Invariant 05: 内部图谱底层属性 `_raw_knowledge_points` 严格封装，
   除了知识图谱自身服务/仓储外，全系统其他业务模块绝不得直接读取或耦合此私有字典。
"""

import ast
from pathlib import Path
import unittest

from app.core.config import settings

APP_DIR = settings.PROJECT_ROOT / "app"


class TestRuntimeDependencies(unittest.TestCase):
    """运行时依赖与内部数据封装架构适应度测试"""

    def test_invariant_04_zero_openpyxl_in_app(self):
        """验证整个 app/ 目录绝不 import openpyxl"""
        py_files = list(APP_DIR.rglob("*.py"))
        self.assertTrue(len(py_files) > 0, "未发现 app/ 目录下的 Python 文件")

        violations = []
        for py_file in py_files:
            rel_path = py_file.relative_to(settings.PROJECT_ROOT)
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "openpyxl" or alias.name.startswith("openpyxl."):
                            violations.append(
                                f"{rel_path}:{node.lineno} - 违规导入: 'import {alias.name}'"
                            )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module == "openpyxl" or module.startswith("openpyxl."):
                        imported = ", ".join(a.name for a in node.names)
                        violations.append(
                            f"{rel_path}:{node.lineno} - 违规导入: 'from {module} import {imported}'"
                        )

        self.assertEqual(
            violations,
            [],
            f"app/ 运行时目录违规引入 openpyxl:\n" + "\n".join(violations),
        )

    def test_invariant_05_raw_knowledge_points_confined(self):
        """验证全系统除 knowledge_graph 服务/仓储外，绝无其他模块访问 _raw_knowledge_points"""
        py_files = list(APP_DIR.rglob("*.py"))
        allowed_files = {
            Path("app/services/knowledge_graph_service.py"),
            Path("app/infrastructure/persistence/knowledge_graph_repository.py"),
        }

        violations = []
        for py_file in py_files:
            rel_path = py_file.relative_to(settings.PROJECT_ROOT)
            if rel_path in allowed_files:
                continue

            content = py_file.read_text(encoding="utf-8")
            if "_raw_knowledge_points" in content:
                violations.append(
                    f"{rel_path} - 违规访问未脱敏的内部字典 '_raw_knowledge_points' (破坏图谱公开契约)"
                )

        self.assertEqual(
            violations,
            [],
            f"发现外部模块非法侵入图谱内部数据结构:\n" + "\n".join(violations),
        )
