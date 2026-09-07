# -*- coding: utf-8 -*-
"""
tests.architecture.test_api_contract
Invariant 07 & 08: API 公开契约与前端绑定冻结测试

验证规则：
1. Invariant 07: 后端必须严格暴露全部 18 个核心 API 端点与 1 个根端点，
   HTTP Method 与 Path 必须 100% 保持一致，绝对禁止破坏性漂移。
2. Invariant 08: 前端 API 契约冻结，frontend/src/api.ts 自 Phase 2.1 起不得发生非授权破坏性修改。
"""

import subprocess
import unittest
from fastapi.routing import APIRoute

from app.core.config import settings
from app.main import app

EXPECTED_API_ENDPOINTS = {
    ("GET", "/"),
    ("GET", "/api/health"),
    ("GET", "/api/overview"),
    ("GET", "/api/students"),
    ("GET", "/api/students/{student_id}/profile"),
    ("GET", "/api/students/{student_id}/dashboard"),
    ("GET", "/api/students/{student_id}/report"),
    ("GET", "/api/reports"),
    ("GET", "/api/students/{student_id}/learning-path"),
    ("GET", "/api/learning-paths"),
    ("GET", "/api/students/{student_id}/path-states"),
    ("GET", "/api/students/{student_id}/knowledge-graph"),
    ("GET", "/api/students/{student_id}/knowledge-state/{knowledge_id}"),
    ("POST", "/api/learning-state/update"),
    ("POST", "/api/events"),
    ("GET", "/api/students/{student_id}/assistant/greeting"),
    ("POST", "/api/students/{student_id}/assistant"),
    ("GET", "/api/quiz/{knowledge_id}"),
    ("POST", "/api/quiz/submit"),
}


class TestApiContract(unittest.TestCase):
    """API 契约一致性测试"""

    def test_invariant_07_all_api_endpoints_registered_and_frozen(self):
        """验证所有 19 个端点 (18 API + 1 Root) 精确注册且无意外路由"""
        actual_endpoints = set()
        for route in app.routes:
            if isinstance(route, APIRoute):
                # 排除 FastAPI 内部文档与 OpenAPI 端点
                if route.path in {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}:
                    continue
                for method in route.methods:
                    if method != "HEAD":
                        actual_endpoints.add((method, route.path))

        missing = EXPECTED_API_ENDPOINTS - actual_endpoints
        extra = actual_endpoints - EXPECTED_API_ENDPOINTS

        self.assertEqual(
            missing,
            set(),
            f"API 契约出现缺失端点:\n{missing}",
        )
        self.assertEqual(
            extra,
            set(),
            f"API 契约出现未授权的新增端点:\n{extra}",
        )
        self.assertEqual(
            len(actual_endpoints),
            19,
            f"期望 19 个端点 (18 API + 1 Root)，实际注册了 {len(actual_endpoints)} 个",
        )

    def test_invariant_08_frontend_api_frozen(self):
        """验证 frontend/src/api.ts 契约完整性 (Invariant 08 Frontend API Frozen)"""
        api_ts = settings.PROJECT_ROOT / "frontend" / "src" / "api.ts"
        self.assertTrue(api_ts.exists(), "frontend/src/api.ts 必须存在")

        content = api_ts.read_text(encoding="utf-8")
        self.assertIn("const API_BASE = '/api';", content)

        # 验证前端核心端点调用完整存在
        frontend_endpoint_tokens = [
            "${API_BASE}/health",
            "'/overview'",
            "'/students'",
            "`/students/${studentId}/dashboard`",
            "`/students/${studentId}/profile`",
            "`/students/${studentId}/learning-path`",
            "`/students/${studentId}/report`",
            "`/students/${studentId}/assistant`",
            "`/students/${studentId}/assistant/greeting`",
            "`/students/${studentId}/knowledge-graph`",
            "`/quiz/${knowledgeId}`",
            "'/quiz/submit'",
        ]
        for ep in frontend_endpoint_tokens:
            self.assertIn(ep, content, f"前端 api.ts 缺少对端点 {ep} 的调用")
