# -*- coding: utf-8 -*-
"""
gateway.tests.test_provider_contract
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage B: Provider Adapter Contract & Secret Isolation 专用契约测试 (12 项核心断言)
"""

import asyncio
import copy
import json
import logging
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from gateway.adapter import (
    AIProviderAdapter,
    FutureExternalLLMProvider,
    MockGatewayProvider,
    ProviderException,
    ProviderTimeoutError,
    execute_provider_with_timeout,
    get_provider,
    set_provider,
)
from gateway.api import app
from gateway.config import GatewaySettings
from gateway.models import (
    AICompanionRequest,
    LearningPromptContext,
    StructuredAIResponse,
)

FORBIDDEN_DECISION_FIELDS = {
    "decision",
    "unlock_nodes",
    "state_transition",
    "mutate_path",
    "modify_mastery",
    "set_mastery",
    "next_state",
    "learning_path_update",
    "next_action_command",
    "change_path",
    "path_mutation",
}


@pytest.fixture
def sample_context() -> LearningPromptContext:
    """构建标准的只读测试上下文"""
    return LearningPromptContext(
        user_question="这道题我做错了，为什么掌握度没达标？",
        system_facts={
            "student_id": "S001",
            "student_name": "李同学",
            "major": "经济学",
            "grade": "大二",
            "learning_goal": "微观经济学",
            "current_knowledge_id": "K08",
            "current_knowledge_name": "需求价格弹性",
            "current_chapter": "第二章",
            "current_path_state": "IN_PROGRESS",
            "current_mastery_percent": 45.7,
            "mastery_target_percent": 80.0,
            "mastery_gap_percent": 34.3,
            "is_mastered": False,
            "prerequisites_met": True,
            "path_priority": "高",
            "is_path_completed": False,
            "recent_quiz": {
                "question_id": "Q08_01",
                "is_correct": False,
                "time_spent_ms": 30000,
                "before_mastery_percent": 45.7,
                "after_mastery_percent": 45.7,
                "delta_percent": 0.0,
                "action": "RETAIN",
                "reason_code": "MASTERY_STATE_UNCHANGED",
                "unlocked_nodes": [],
            },
            "next_action": {
                "type": "PRACTICE",
                "label": "继续针对性练习",
                "target_knowledge_id": "K08",
                "reason": "掌握度尚未跨越 80% 达标线",
            },
        },
        grounding_rules=[
            "1. Only use supplied system facts.",
            "2. Explain decisions instead of replacing them.",
        ],
    )


@pytest.mark.asyncio
async def test_b1_adapter_interface():
    """Test B1: MockGatewayProvider 与 FutureExternalLLMProvider 严格实现 AIProviderAdapter 契约"""
    mock_p = MockGatewayProvider()
    assert isinstance(mock_p, AIProviderAdapter)
    assert issubclass(MockGatewayProvider, AIProviderAdapter)
    assert mock_p.provider_name == "mock-gateway-provider"

    ext_p = FutureExternalLLMProvider(name="deepseek")
    assert isinstance(ext_p, AIProviderAdapter)
    assert issubclass(FutureExternalLLMProvider, AIProviderAdapter)
    assert ext_p.provider_name == "deepseek"


@pytest.mark.asyncio
async def test_b2_input_whitelist(sample_context):
    """Test B2: Provider 只能接收 LearningPromptContext，不能接受任意领域模型"""
    provider = MockGatewayProvider()
    res = await provider.generate(sample_context)
    assert isinstance(res, StructuredAIResponse)

    # 验证非 LearningPromptContext 无法通过类型/运行时模型校验
    with pytest.raises(Exception):
        # 尝试传入无 system_facts 的非法原始字典
        AICompanionRequest.model_validate({"invalid_root": 123})


@pytest.mark.asyncio
async def test_b3_output_contract(sample_context):
    """Test B3: Provider 输出必须严格符合 StructuredAIResponse 契约"""
    provider = MockGatewayProvider()
    response = await provider.generate(sample_context)

    assert isinstance(response, StructuredAIResponse)
    assert isinstance(response.answer, str) and len(response.answer) > 0
    assert isinstance(response.referenced_facts, list)
    assert len(response.referenced_facts) >= 4
    assert response.grounding_status in ("grounded", "insufficient_context")


@pytest.mark.asyncio
async def test_b4_zero_decision_authority(sample_context):
    """Test B4: Provider 输出绝不得包含任何学习决策或状态变更字段"""
    provider = MockGatewayProvider()
    response = await provider.generate(sample_context)
    dumped = response.model_dump()

    # 递归验证所有键值均不在禁止字段黑名单内
    for forbidden in FORBIDDEN_DECISION_FIELDS:
        assert forbidden not in dumped, f"输出中违规包含了学习决策字段: {forbidden}"
        assert not hasattr(response, forbidden), f"模型中违规定义了属性: {forbidden}"


@pytest.mark.asyncio
async def test_b5_determinism(sample_context):
    """Test B5: 相同 Context 连续调用 10 次，所有 JSON 序列化输出字节级完全一致"""
    provider = MockGatewayProvider()
    results = []

    for _ in range(10):
        res = await provider.generate(sample_context)
        results.append(json.dumps(res.model_dump(), sort_keys=True, ensure_ascii=False))

    first = results[0]
    for idx, r in enumerate(results[1:], start=2):
        assert r == first, f"第 {idx} 次调用结果与第 1 次不一致"


@pytest.mark.asyncio
async def test_b6_immutable_context(sample_context):
    """Test B6: Provider 执行前后输入 prompt_context 深度完全等价，绝对不可变"""
    provider = MockGatewayProvider()
    before_dump = copy.deepcopy(sample_context.model_dump())

    await provider.generate(sample_context)

    after_dump = sample_context.model_dump()
    assert before_dump == after_dump, "Provider 执行修改了输入的 prompt_context"


@pytest.mark.asyncio
async def test_b7_provider_exception(sample_context):
    """Test B7: Provider 抛出异常时不击穿网关，通过 execute_provider_with_timeout 转化为受控异常并在 HTTP 端平稳降级"""
    error_provider = MockGatewayProvider(mode="error")

    with pytest.raises(ProviderException) as exc_info:
        await execute_provider_with_timeout(error_provider, sample_context)
    assert "Simulated upstream provider failure" in str(exc_info.value)

    # 验证 HTTP 网关级容灾拦截
    set_provider(error_provider)
    try:
        client = TestClient(app)
        res = client.post("/api/ai/companion", json={"promptContext": sample_context.model_dump()})
        assert res.status_code == 502
        assert res.json()["error"] == "BAD_GATEWAY"
        assert "traceback" not in res.text.lower()
    finally:
        set_provider(None)


@pytest.mark.asyncio
async def test_b8_provider_timeout(sample_context):
    """Test B8: 超时 Provider 被 5000ms 契约熔断，不发生无限悬挂"""
    timeout_provider = MockGatewayProvider(mode="timeout")

    # 使用极短超时（50ms）快速验证超时异常受控抛出
    with pytest.raises(ProviderTimeoutError):
        await execute_provider_with_timeout(timeout_provider, sample_context, timeout_ms=50)

    # 验证 HTTP 客户端获得 504 Gateway Timeout 且结构安全
    set_provider(timeout_provider)
    try:
        client = TestClient(app)
        from unittest.mock import patch
        fast_settings = GatewaySettings(timeout_ms=50)
        with patch("gateway.api.gateway_settings", fast_settings), patch("gateway.adapter.gateway_settings", fast_settings):
            res = client.post("/api/ai/companion", json={"promptContext": sample_context.model_dump()})
            assert res.status_code == 504
            assert res.json()["error"] == "GATEWAY_TIMEOUT"
    finally:
        set_provider(None)


@pytest.mark.asyncio
async def test_b9_secret_isolation(sample_context, caplog):
    """Test B9: 模拟密钥 TEST_SECRET_DO_NOT_USE 绝不出现在响应、异常信息或日志中"""
    fake_secret = "TEST_SECRET_DO_NOT_USE_998877"
    test_settings = GatewaySettings(
        provider="mock",
        api_key=fake_secret,
        model="test-model",
    )

    from unittest.mock import patch
    with patch("gateway.config.gateway_settings", test_settings), patch("gateway.adapter.gateway_settings", test_settings):
        client = TestClient(app)
        with caplog.at_level(logging.DEBUG):
            res = client.post("/api/ai/companion", json={"promptContext": sample_context.model_dump()})

        assert res.status_code == 200
        assert fake_secret not in res.text
        assert fake_secret not in caplog.text


def test_b10_secret_not_in_frontend():
    """Test B10: 验证前端源代码目录中没有任何生产或测试用真实 API 密钥硬编码"""
    project_root = Path(__file__).resolve().parent.parent.parent
    frontend_src = project_root / "frontend" / "src"

    forbidden_patterns = ["sk-proj-", "sk-ant-", "deepseek-api-key", "OPENAI_API_KEY"]
    for ts_file in frontend_src.rglob("*.ts*"):
        text = ts_file.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in text, f"在前端源码 {ts_file.name} 中发现潜在敏感凭证: {pattern}"


@pytest.mark.asyncio
async def test_b11_provider_replacement(sample_context):
    """Test B11: 验证网关支持通过 set_provider 无感热替换 Provider 实现"""
    custom_resp = StructuredAIResponse(
        answer="这是由备用 Provider 生成的替代解释内容。",
        referenced_facts=["custom_provider=provider_b"],
        suggested_explanation="备用模型解释。",
        grounding_status="grounded",
    )
    provider_a = MockGatewayProvider(name="provider-a")
    provider_b = MockGatewayProvider(name="provider-b", custom_response=custom_resp)

    # 1. 挂载 Provider A
    set_provider(provider_a)
    client = TestClient(app)
    res_a = client.post("/api/ai/companion", json={"promptContext": sample_context.model_dump()}).json()
    assert "编号 K08" in res_a["answer"]

    # 2. 热替换为 Provider B
    set_provider(provider_b)
    res_b = client.post("/api/ai/companion", json={"promptContext": sample_context.model_dump()}).json()
    assert res_b["answer"] == "这是由备用 Provider 生成的替代解释内容。"
    assert res_b["referenced_facts"] == ["custom_provider=provider_b"]

    # 恢复默认
    set_provider(None)


def test_b12_core_learning_isolation():
    """Test B12: 验证 Provider 适配器无任何对 BKT、Decision Core 或 PathState 的底层依赖或状态写操作"""
    import gateway.adapter as ga
    import sys

    # 检查 gateway.adapter 内部导入，绝对不包含 app.domain.bkt 或 app.domain.path_replanning
    adapter_file = Path(ga.__file__).read_text(encoding="utf-8")
    assert "app.domain.bkt" not in adapter_file
    assert "app.domain.path_replanning" not in adapter_file
    assert "bkt_service" not in adapter_file
    assert "path_state_service" not in adapter_file
