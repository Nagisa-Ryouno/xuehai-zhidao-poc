# -*- coding: utf-8 -*-
"""
tests.architecture.test_service_boundaries
Invariant 03: Service 不依赖 Web Framework

验证规则：
1. app/services/ 下的所有 Python 模块绝对禁止 import fastapi 及其子模块。
2. 特别严禁直接从 fastapi 引入 HTTPException。
3. 业务异常必须由应用层/领域层以纯 Python 异常表示，由表现层 Router 统一映射为 HTTP 状态码。
"""

import ast
from pathlib import Path
import unittest

from app.core.config import settings

SERVICES_DIR = settings.PROJECT_ROOT / "app" / "services"


class TestServiceBoundaries(unittest.TestCase):
    """应用服务层 Web 框架解耦适应度测试"""

    def test_services_have_no_fastapi_dependency(self):
        """验证 app/services/ 下任何文件均无 fastapi 依赖"""
        py_files = list(SERVICES_DIR.glob("*.py"))
        self.assertTrue(len(py_files) > 0, "未发现 app/services/*.py 文件")

        violations = []
        for py_file in py_files:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "fastapi" or alias.name.startswith("fastapi."):
                            violations.append(
                                f"{py_file.name}:{node.lineno} - 违规导入 'import {alias.name}'"
                            )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module == "fastapi" or module.startswith("fastapi."):
                        imported_names = [a.name for a in node.names]
                        violations.append(
                            f"{py_file.name}:{node.lineno} - 违规导入 'from {module} import {', '.join(imported_names)}'"
                        )

        self.assertEqual(
            violations,
            [],
            f"发现应用服务层违规依赖 Web 框架 (FastAPI):\n" + "\n".join(violations),
        )
