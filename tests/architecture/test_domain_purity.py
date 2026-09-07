# -*- coding: utf-8 -*-
"""
tests.architecture.test_domain_purity
Invariant 01: Domain 纯内存与零 I/O 架构适应度测试

验证规则：
1. app/domain/ 下的所有 Python 模块绝不依赖 Web 框架 (fastapi, starlette 等)。
2. app/domain/ 绝不依赖外层架构 (app.services, app.infrastructure, app.api)。
3. app/domain/ 绝不引入任何非标准第三方 I/O 库 (requests, openpyxl 等)。
4. app/domain/ 绝不包含任何直接文件系统 I/O 或网络 I/O 调用 (open, read_text, write_text, json.load, json.dump 等)。
5. 领域计算必须是纯内存 (In-Memory)、确定性的数学与规则裁决。
"""

import ast
from pathlib import Path
import unittest

from app.core.config import settings

DOMAIN_DIR = settings.PROJECT_ROOT / "app" / "domain"

FORBIDDEN_MODULE_PREFIXES = (
    "fastapi",
    "starlette",
    "requests",
    "openpyxl",
    "urllib",
    "http.client",
    "socket",
    "app.services",
    "app.infrastructure",
    "app.api",
)

FORBIDDEN_BUILTIN_FUNCS = {"open"}
FORBIDDEN_METHOD_ATTRS = {"read_text", "write_text", "read_bytes", "write_bytes"}
FORBIDDEN_JSON_IO = {"load", "dump"}  # load/dump are file-based; loads/dumps are in-memory string


class TestDomainPurity(unittest.TestCase):
    """领域层纯洁性测试"""

    def test_domain_has_no_external_or_outer_layer_imports(self):
        """验证 app/domain/ 绝不引入 forbidden 模块"""
        py_files = list(DOMAIN_DIR.rglob("*.py"))
        self.assertTrue(len(py_files) > 0, "未发现 app/domain/ 下的 Python 模块")

        violations = []
        for py_file in py_files:
            rel_path = py_file.relative_to(settings.PROJECT_ROOT)
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in FORBIDDEN_MODULE_PREFIXES:
                            if alias.name == forbidden or alias.name.startswith(f"{forbidden}."):
                                violations.append(
                                    f"{rel_path}:{node.lineno} - 违规导入: 'import {alias.name}'"
                                )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for forbidden in FORBIDDEN_MODULE_PREFIXES:
                        if module == forbidden or module.startswith(f"{forbidden}."):
                            imported = ", ".join(a.name for a in node.names)
                            violations.append(
                                f"{rel_path}:{node.lineno} - 违规导入: 'from {module} import {imported}'"
                            )

        self.assertEqual(
            violations,
            [],
            f"领域层违规导入外部依赖或外层模块:\n" + "\n".join(violations),
        )

    def test_domain_has_no_file_or_network_io_calls(self):
        """验证 app/domain/ 绝不进行磁盘或网络 I/O 调用"""
        py_files = list(DOMAIN_DIR.rglob("*.py"))
        violations = []

        for py_file in py_files:
            rel_path = py_file.relative_to(settings.PROJECT_ROOT)
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # 检查内置 open() 函数调用
                    if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_BUILTIN_FUNCS:
                        violations.append(
                            f"{rel_path}:{node.lineno} - 违规调用内置 I/O 函数: {node.func.id}()"
                        )
                    # 检查 Path 对象的 read_text / write_text 调用
                    elif isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_METHOD_ATTRS:
                        violations.append(
                            f"{rel_path}:{node.lineno} - 违规调用文件 I/O 方法: .{node.func.attr}()"
                        )
                    # 检查 json.load / json.dump 文件操作（注意：允许 json.loads / json.dumps 纯内存字符串操作）
                    elif isinstance(node.func, ast.Attribute):
                        if (
                            isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "json"
                            and node.func.attr in FORBIDDEN_JSON_IO
                        ):
                            violations.append(
                                f"{rel_path}:{node.lineno} - 违规调用文件流序列化: json.{node.func.attr}() (应使用内存序列化 json.{node.func.attr}s)"
                            )

        self.assertEqual(
            violations,
            [],
            f"领域层检测到违规 I/O 调用 (必须纯内存):\n" + "\n".join(violations),
        )
