# -*- coding: utf-8 -*-
"""
gateway.tests.test_failure_isolation
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage D: Gateway Failure Isolation Contracts (极端故障隔离契约测试)

核心断言：
1. Provider Timeout -> HTTP 504 JSON (error: GATEWAY_TIMEOUT, 无 traceback)
2. Provider Exception -> HTTP 502 JSON (error: BAD_GATEWAY, 无 traceback)
3. Unhandled Server Crash -> HTTP 500 JSON (error: GATEWAY_INTERNAL_ERROR, 无 traceback)
4. Traceback & File Paths Isolation -> 所有错误响应绝不泄露 Python Traceback 或 .py 源码路径
5. Secret Isolation -> 敏感 Secret 绝不在异常响应、日志体或错误消息中泄露
6. Schema Validation Isolation -> 422 校验失败安全受控，杜绝异常堆栈泄露
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from gateway.adapter import (
    AIProviderAdapter,
    ProviderException,
    ProviderTimeoutError,
    set_provider,
)
from gateway.api import app
from gateway.models import LearningPromptContext, StructuredAIResponse


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient Fixture"""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def sample_payload() -> dict:
    """标准的白名单有效载荷"""
    return {
        "promptContext": {
            "user_question": "为什么需求价格弹性掌握度没有提升？",
            "system_facts": {
                "student_id": "S001",
                "student_name": "张小凡",
                "major": "经济学",
                "grade": "大二",
                "learning_goal": "掌握需求弹性分析",
                "current_knowledge_id": "K08",
                "current_knowledge_name": "需求价格弹性",
                "current_chapter": "微观经济学基础",
                "current_path_state": "IN_PROGRESS",
                "current_mastery_percent": 46.0,
                "mastery_target_percent": 80.0,
                "mastery_gap_percent": 34.0,
                "is_mastered": False,
                "prerequisites_met": True,
                "path_priority": "高",
                "is_path_completed": False,
                "next_action": {
                    "type": "PRACTICE",
                    "label": "继续挑战微测验",
                    "target_knowledge_id": "K08",
                    "reason": "通过微测验提高掌握度至80%",
                },
            },
            "grounding_rules": [
                "1. 仅依据客观事实回答。",
                "2. 严禁编造掌握度数值。",
            ],
        },
        "question": "为什么需求价格弹性掌握度没有提升？",
    }


class TimeoutFailureMockProvider(AIProviderAdapter):
    """模拟超时异常的 Provider"""

    @property
    def provider_name(self) -> str:
        return "timeout-mock"

    async def generate(
        self, prompt_context: LearningPromptContext
    ) -> StructuredAIResponse:
        raise ProviderTimeoutError("Upstream model request timed out after 5000ms")


class ExceptionFailureMockProvider(AIProviderAdapter):
    """模拟服务商崩溃异常的 Provider"""

    @property
    def provider_name(self) -> str:
        return "exception-mock"

    async def generate(
        self, prompt_context: LearningPromptContext
    ) -> StructuredAIResponse:
        raise ProviderException(
            "Upstream connection failed: Connection refused to api.openai.com:443"
        )


class SecretLeakingMockProvider(AIProviderAdapter):
    """模拟内部异常包含敏感密钥的 Provider"""

    @property
    def provider_name(self) -> str:
        return "secret-leaking-mock"

    async def generate(
        self, prompt_context: LearningPromptContext
    ) -> StructuredAIResponse:
        raise ProviderException(
            "Authentication failed with key: TEST_SECRET_DO_NOT_USE_998877"
        )


def test_d_backend_01_provider_timeout_returns_504_without_traceback(
    client: TestClient, sample_payload: dict
):
    """D-Backend-01: Provider 超时时返回 504 JSON，错误类型为 GATEWAY_TIMEOUT 且无 Traceback"""
    original_provider = set_provider(TimeoutFailureMockProvider())
    try:
        response = client.post("/api/ai/companion", json=sample_payload)
        assert response.status_code == 504
        data = response.json()
        assert data.get("error") == "GATEWAY_TIMEOUT"
        assert data.get("grounding_status") == "insufficient_context"
        assert "Traceback (most recent call last):" not in response.text
        assert ".py" not in response.text
    finally:
        set_provider(original_provider)


def test_d_backend_02_provider_exception_returns_502_without_traceback(
    client: TestClient, sample_payload: dict
):
    """D-Backend-02: Provider 异常时返回 502 JSON，错误类型为 BAD_GATEWAY 且无 Traceback"""
    original_provider = set_provider(ExceptionFailureMockProvider())
    try:
        response = client.post("/api/ai/companion", json=sample_payload)
        assert response.status_code == 502
        data = response.json()
        assert data.get("error") == "BAD_GATEWAY"
        assert data.get("grounding_status") == "insufficient_context"
        assert "Traceback (most recent call last):" not in response.text
        assert ".py" not in response.text
        # 绝不暴露原始底层连接细节
        assert "api.openai.com:443" not in response.text
    finally:
        set_provider(original_provider)


def test_d_backend_03_unhandled_server_crash_returns_500_without_traceback(
    client: TestClient, sample_payload: dict
):
    """D-Backend-03: 网关未捕获未知异常时返回 500 JSON，错误类型为 GATEWAY_INTERNAL_ERROR 且无 Traceback"""
    with patch(
        "gateway.api.get_provider",
        side_effect=RuntimeError(
            "Fatal unexpected crash in C:\\secret\\production_server.py: Database connection lost"
        ),
    ):
        response = client.post("/api/ai/companion", json=sample_payload)
        assert response.status_code == 500
        data = response.json()
        assert data.get("error") == "GATEWAY_INTERNAL_ERROR"
        assert data.get("grounding_status") == "insufficient_context"
        assert "Traceback (most recent call last):" not in response.text
        assert "production_server.py" not in response.text
        assert "C:\\secret" not in response.text
        assert "Database connection lost" not in response.text


def test_d_backend_04_traceback_and_internal_paths_never_leak(
    client: TestClient, sample_payload: dict
):
    """D-Backend-04: 所有故障状态码 (422, 500, 502, 504) 均严格隔离 Python 堆栈与绝对路径"""
    # 1. 422 验证
    malformed_payload = {"promptContext": "not_an_object"}
    res_422 = client.post("/api/ai/companion", json=malformed_payload)
    assert res_422.status_code == 422
    assert "Traceback (most recent call last):" not in res_422.text
    assert ".py" not in res_422.text

    # 2. 502 验证
    original_provider = set_provider(ExceptionFailureMockProvider())
    try:
        res_502 = client.post("/api/ai/companion", json=sample_payload)
        assert res_502.status_code == 502
        assert "Traceback" not in res_502.text
        assert ".py" not in res_502.text
    finally:
        set_provider(original_provider)

    # 3. 504 验证
    original_provider = set_provider(TimeoutFailureMockProvider())
    try:
        res_504 = client.post("/api/ai/companion", json=sample_payload)
        assert res_504.status_code == 504
        assert "Traceback" not in res_504.text
        assert ".py" not in res_504.text
    finally:
        set_provider(original_provider)


def test_d_backend_05_secret_isolation_under_failure_conditions(
    client: TestClient, sample_payload: dict
):
    """D-Backend-05: 内部异常携带敏感 Secret 时，网关输出绝对不包含该 Secret 字符串"""
    fake_secret = "TEST_SECRET_DO_NOT_USE_998877"
    original_provider = set_provider(SecretLeakingMockProvider())
    try:
        response = client.post("/api/ai/companion", json=sample_payload)
        assert response.status_code == 502
        # 严格验证响应体与 Header 中绝对不包含 Secret
        assert fake_secret not in response.text
        for header_key, header_val in response.headers.items():
            assert fake_secret not in header_key
            assert fake_secret not in header_val
    finally:
        set_provider(original_provider)
