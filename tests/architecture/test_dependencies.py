# -*- coding: utf-8 -*-
"""
tests.architecture.test_dependencies
Invariant 11: 单向分层依赖架构适应度函数 (Layered Architecture Fitness Test)

分层单向依赖规则 (Dependency Inversion / Layered Rules)：
1. app/core (核心常数与配置):
   - 处于系统基底，严禁依赖任何其他内部层 (domain, infrastructure, services, api)。
2. app/domain (纯领域实体、值对象与数学核心):
   - 仅允许依赖 app.core。
   - 严禁依赖 infrastructure, services, api。
3. app/infrastructure (底层存储仓储与外部客户端):
   - 仅允许依赖 app.core 与 app.domain。
   - 严禁依赖 services, api。
4. app/services (应用服务与业务编排):
   - 允许依赖 app.core, app.domain, app.infrastructure。
   - 严禁逆向依赖表现层 app.api。
5. app/api (表现层 Router 与 Schemas):
   - 允许依赖 app.core, app.domain, app.services。
   - 严禁直接依赖 app.infrastructure（禁止绕过服务层直连仓储）。
"""

import ast
from pathlib import Path
import unittest

from app.core.config import settings

APP_DIR = settings.PROJECT_ROOT / "app"

LAYER_DIRECTORIES = {
    "core": APP_DIR / "core",
    "domain": APP_DIR / "domain",
    "infrastructure": APP_DIR / "infrastructure",
    "services": APP_DIR / "services",
    "api": APP_DIR / "api",
}

# 每层允许依赖的目标层白名单
ALLOWED_DEPENDENCIES = {
    "core": {"core"},
    "domain": {"core", "domain"},
    "infrastructure": {"core", "domain", "infrastructure"},
    "services": {"core", "domain", "infrastructure", "services"},
    "api": {"core", "domain", "services", "api"},
}


class TestArchitectureDependencies(unittest.TestCase):
    """分层单向依赖适应度函数"""

    def test_strict_unidirectional_layer_dependencies(self):
        """AST 遍历全系统模块，严格验证分层单向流动，杜绝反向与跨层越权依赖"""
        violations = []

        for layer_name, layer_path in LAYER_DIRECTORIES.items():
            self.assertTrue(layer_path.exists(), f"分层目录缺失: {layer_path}")
            py_files = list(layer_path.rglob("*.py"))

            for py_file in py_files:
                rel_path = py_file.relative_to(settings.PROJECT_ROOT)
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

                for node in ast.walk(tree):
                    imported_modules = []
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported_modules.append((alias.name, node.lineno))
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        imported_modules.append((module, node.lineno))

                    for mod_name, lineno in imported_modules:
                        if mod_name.startswith("app."):
                            parts = mod_name.split(".")
                            if len(parts) >= 2:
                                target_layer = parts[1]
                                allowed = ALLOWED_DEPENDENCIES.get(layer_name, set())
                                if target_layer not in allowed:
                                    violations.append(
                                        f"[{layer_name.upper()} 违规越权] {rel_path}:{lineno} -> 导入 '{mod_name}' "
                                        f"(层 '{layer_name}' 仅允许依赖: {sorted(allowed)})"
                                    )

        self.assertEqual(
            violations,
            [],
            f"检测到违反分层单向依赖规则的代码导入:\n" + "\n".join(violations),
        )
