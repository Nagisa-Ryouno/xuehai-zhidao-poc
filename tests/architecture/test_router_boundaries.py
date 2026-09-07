# -*- coding: utf-8 -*-
"""
tests.architecture.test_router_boundaries
Invariant 02: Router 纯协议适配器边界测试

验证规则：
1. app/api/routers/ 下的所有路由模块必须是纯协议适配器，严禁直接包含业务持久化或计算逻辑。
2. 严禁直接导入 app.infrastructure 基础设施仓储层（必须通过应用服务层委派）。
3. 严禁引入 openpyxl、requests 等底层 I/O 库。
4. 严禁直接进行磁盘文件读写 (open, read_text, write_text, json.load, json.dump)。
"""

import ast
from pathlib import Path
import unittest

from app.core.config import settings

ROUTERS_DIR = settings.PROJECT_ROOT / "app" / "api" / "routers"

FORBIDDEN_ROUTER_IMPORTS = (
    "openpyxl",
    "requests",
    "app.infrastructure",
)

FORBIDDEN_IO_FUNCS = {"open"}
FORBIDDEN_IO_ATTRS = {"read_text", "write_text", "read_bytes", "write_bytes"}
FORBIDDEN_JSON_IO = {"load", "dump"}


class TestRouterBoundaries(unittest.TestCase):
    """路由层架构边界测试"""

    def test_routers_have_no_infrastructure_or_raw_io_imports(self):
        """验证 app/api/routers/ 不直接依赖基础设施层或文件处理库"""
        py_files = [p for p in ROUTERS_DIR.glob("*.py") if p.name != "__init__.py"]
        self.assertTrue(len(py_files) > 0, "未发现 app/api/routers/*.py 模块")

        violations = []
        for py_file in py_files:
            rel_path = py_file.relative_to(settings.PROJECT_ROOT)
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in FORBIDDEN_ROUTER_IMPORTS:
                            if alias.name == forbidden or alias.name.startswith(f"{forbidden}."):
                                violations.append(
                                    f"{rel_path}:{node.lineno} - 违规导入: 'import {alias.name}'"
                                )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for forbidden in FORBIDDEN_ROUTER_IMPORTS:
                        if module == forbidden or module.startswith(f"{forbidden}."):
                            imported = ", ".join(a.name for a in node.names)
                            violations.append(
                                f"{rel_path}:{node.lineno} - 违规导入: 'from {module} import {imported}'"
                            )

        self.assertEqual(
            violations,
            [],
            f"路由层违规依赖基础设施层或底层 I/O 库:\n" + "\n".join(violations),
        )

    def test_routers_have_no_direct_disk_io_calls(self):
        """验证 app/api/routers/ 不包含任何直接磁盘 I/O 调用"""
        py_files = [p for p in ROUTERS_DIR.glob("*.py") if p.name != "__init__.py"]
        violations = []

        for py_file in py_files:
            rel_path = py_file.relative_to(settings.PROJECT_ROOT)
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_IO_FUNCS:
                        violations.append(
                            f"{rel_path}:{node.lineno} - 违规直接调用文件 I/O: {node.func.id}()"
                        )
                    elif isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_IO_ATTRS:
                        violations.append(
                            f"{rel_path}:{node.lineno} - 违规直接调用文件读写方法: .{node.func.attr}()"
                        )
                    elif isinstance(node.func, ast.Attribute):
                        if (
                            isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "json"
                            and node.func.attr in FORBIDDEN_JSON_IO
                        ):
                            violations.append(
                                f"{rel_path}:{node.lineno} - 违规调用 json.{node.func.attr}() (磁盘 I/O 应在仓储层)"
                            )

        self.assertEqual(
            violations,
            [],
            f"路由层发现直接磁盘 I/O 调用 (必须由 Service/Repository 负责):\n" + "\n".join(violations),
        )
