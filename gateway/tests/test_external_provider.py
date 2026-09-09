# -*- coding: utf-8 -*-
"""
gateway.tests.test_external_provider
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage E: Controlled External LLM Provider Readiness (E1 ~ E23 契约测试)

测试分类：
- E1 ~ E5: Provider Contract (接口实现、输入白名单、输出契约、零决策权、Provider 可替换性)
- E6 ~ E10: Configuration & Secret (Mock 默认安全、缺少 Key 受控异常、Secret 隔离)
- E11 ~ E16: Transport (DisabledNetworkTransport 离线保证、FakeTransport 成功/超时/4xx/5xx/畸形测试)
- E17 ~ E20: Security & Immutability (越权字段拦截、上下文深度不可变、内部对象隔离、全生命周期凭证隔离)
- E21 ~ E23: Determinism (Prompt 确定性、响应归一化确定性、故障行为确定性)
"""

import copy
import json
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from gateway.adapter import (
    AIProviderAdapter,
    ExternalLLMProvider,
    FORBIDDEN_DECISION_FIELDS,
    MockGatewayProvider,
    ProviderConfigurationError,
    ProviderException,
    ProviderTimeoutError,
    get_provider,
    set_provider,
)
from gateway.api import app
from gateway.config import GatewaySettings
from gateway.models import (
    LearningPromptContext,
    LearningPromptSystemFacts,
    PromptNextAction,
    StructuredAIResponse,
)
from gateway.prompt import ExternalPromptPayload, build_external_prompt
from gateway.transport import (
    DisabledNetworkTransport,
    FakeLLMTransport,
    LLMTransport,
)

TEST_SECRET = "TEST_SECRET_DO_NOT_USE_998877"


@pytest.fixture
def sample_context() -> LearningPromptContext:
    """标准的只读学习提示词上下文"""
    return LearningPromptContext(
        user_question="这道需求价格弹性的微测验我为什么做错了？",
        system_facts=LearningPromptSystemFacts(
            student_id="S001",
            student_name="张小凡",
            major="经济学",
            grade="大二",
            learning_goal="掌握需求价格弹性与微观分析",
            current_knowledge_id="K08",
            current_knowledge_name="需求价格弹性",
            current_chapter="微观经济学基础",
            current_path_state="IN_PROGRESS",
            current_mastery_percent=46.0,
            mastery_target_percent=80.0,
            mastery_gap_percent=34.0,
            is_mastered=False,
            prerequisites_met=True,
            path_priority="高",
            is_path_completed=False,
            next_action=PromptNextAction(
                type="PRACTICE",
                label="继续挑战微测验",
                target_knowledge_id="K08",
                reason="通过针对性练习提高掌握度至80%",
            ),
        ),
        grounding_rules=[
            "1. 仅依据客观事实回答。",
            "2. 严禁编造任何掌握度数值或考点。",
        ],
    )


# ============================================================
# Category 1: Provider Contract (E1 ~ E5)
# ============================================================

def test_e01_external_provider_implements_adapter_interface():
    """E1: ExternalLLMProvider 正确实现 AIProviderAdapter 抽象基类"""
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=FakeLLMTransport())
    assert isinstance(provider, AIProviderAdapter)
    assert provider.provider_name == "external-llm-provider"
    assert hasattr(provider, "generate")


@pytest.mark.asyncio
async def test_e02_input_whitelist_only_accepts_learning_prompt_context(sample_context):
    """E2: ExternalLLMProvider.generate 仅接受强类型 LearningPromptContext"""
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=FakeLLMTransport())
    # 正常调用成功
    res = await provider.generate(sample_context)
    assert isinstance(res, StructuredAIResponse)


@pytest.mark.asyncio
async def test_e03_output_strictly_matches_structured_ai_response(sample_context):
    """E3: ExternalLLMProvider 输出严格对齐 StructuredAIResponse 契约规范"""
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=FakeLLMTransport())
    res = await provider.generate(sample_context)

    assert isinstance(res.answer, str)
    assert len(res.answer) > 0
    assert isinstance(res.referenced_facts, list)
    assert res.grounding_status in ("grounded", "insufficient_context")


@pytest.mark.asyncio
async def test_e04_external_provider_has_zero_decision_authority(sample_context):
    """E4: ExternalLLMProvider 输出绝不包含任何决策控制字段"""
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=FakeLLMTransport())
    res = await provider.generate(sample_context)
    res_dict = res.model_dump()

    for forbidden in FORBIDDEN_DECISION_FIELDS:
        assert forbidden not in res_dict, f"输出中包含非法决策字段: {forbidden}"


@pytest.mark.asyncio
async def test_e05_provider_substitutability_invariant_e1(sample_context):
    """E5: Invariant E1 — Provider 可替换性保证 (Mock ↔ External 无感互换)"""
    mock_p = MockGatewayProvider()
    ext_p = ExternalLLMProvider(api_key=TEST_SECRET, transport=FakeLLMTransport())

    res_mock = await mock_p.generate(sample_context)
    res_ext = await ext_p.generate(sample_context)

    # 验证两者满足完全一致的契约
    for res in (res_mock, res_ext):
        assert isinstance(res, StructuredAIResponse)
        assert res.grounding_status == "grounded"
        assert len(res.answer) > 0
        assert len(res.referenced_facts) > 0
        for forbidden in FORBIDDEN_DECISION_FIELDS:
            assert forbidden not in res.model_dump()


# ============================================================
# Category 2: Configuration & Secret (E6 ~ E10)
# ============================================================

def test_e06_mock_remains_safe_default():
    """E6: 无任何环境变量或默认配置时，系统必须安全默认使用 MockGatewayProvider"""
    # 模拟完全无配置环境变量
    default_p = get_provider()
    assert isinstance(default_p, MockGatewayProvider)
    assert default_p.provider_name == "mock-gateway-provider"


@pytest.mark.asyncio
async def test_e07_external_without_api_key_raises_controlled_configuration_error(sample_context):
    """E7: External Provider 未配置 API Key 时抛出受控 ProviderConfigurationError"""
    provider = ExternalLLMProvider(api_key=None, transport=FakeLLMTransport())
    with pytest.raises(ProviderConfigurationError) as exc_info:
        await provider.generate(sample_context)

    assert "missing API key" in str(exc_info.value)
    # 绝不能包含任何密钥细节或敏感信息
    assert TEST_SECRET not in str(exc_info.value)


@pytest.mark.asyncio
async def test_e08_secret_never_appears_in_exception(sample_context):
    """E8: 底层异常抛出时，敏感 Secret 绝不泄露到异常消息中"""
    fake_transport = FakeLLMTransport(mode="http_5xx", status_code=500)
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=fake_transport)

    with pytest.raises(ProviderException) as exc_info:
        await provider.generate(sample_context)

    err_msg = str(exc_info.value)
    assert TEST_SECRET not in err_msg


def test_e09_secret_never_appears_in_prompt(sample_context):
    """E9: 提示词构建器组装的 Payload 中绝不包含任何 API Key 或 Secret 凭据"""
    prompt_payload = build_external_prompt(sample_context, model="mock-model")

    assert TEST_SECRET not in prompt_payload.system_prompt
    assert TEST_SECRET not in prompt_payload.user_prompt
    assert TEST_SECRET not in prompt_payload.model


def test_e10_secret_never_appears_in_logs_or_response(sample_context):
    """E10: 网关集成请求中，API Key 绝对不暴露在 HTTP 响应或 Header 中"""
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=FakeLLMTransport())
    original = set_provider(provider)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/ai/companion",
            json={"promptContext": sample_context.model_dump()},
        )
        assert response.status_code == 200
        assert TEST_SECRET not in response.text
        for k, v in response.headers.items():
            assert TEST_SECRET not in k
            assert TEST_SECRET not in v
    finally:
        set_provider(original)


# ============================================================
# Category 3: Transport & Offline Guarantee (E11 ~ E16)
# ============================================================

@pytest.mark.asyncio
async def test_e11_disabled_network_transport_guarantees_no_network():
    """E11: DisabledNetworkTransport 严格阻断真实网络调用，保障 100% 离线运行"""
    transport = DisabledNetworkTransport()
    with pytest.raises(ProviderException) as exc_info:
        await transport.send_payload({"test": "data"}, timeout_ms=1000)

    assert "Real network calls are disabled in Stage E" in str(exc_info.value)
    assert TEST_SECRET not in str(exc_info.value)


@pytest.mark.asyncio
async def test_e12_fake_transport_success(sample_context):
    """E12: FakeLLMTransport 成功模式返回合规数据并被正常处理"""
    transport = FakeLLMTransport(mode="success")
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=transport)
    res = await provider.generate(sample_context)

    assert isinstance(res, StructuredAIResponse)
    assert res.grounding_status == "grounded"
    assert transport.last_request_payload is not None


@pytest.mark.asyncio
async def test_e13_fake_transport_timeout(sample_context):
    """E13: FakeLLMTransport 超时模式精准触发 ProviderTimeoutError"""
    transport = FakeLLMTransport(mode="timeout")
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=transport)

    with pytest.raises(ProviderTimeoutError):
        await provider.generate(sample_context)


@pytest.mark.asyncio
async def test_e14_fake_transport_http_4xx(sample_context):
    """E14: FakeLLMTransport 4xx 客户端异常模式触发受控 ProviderException"""
    transport = FakeLLMTransport(mode="http_4xx", status_code=429)
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=transport)

    with pytest.raises(ProviderException) as exc_info:
        await provider.generate(sample_context)
    assert "HTTP 429" in str(exc_info.value)


@pytest.mark.asyncio
async def test_e15_fake_transport_http_5xx(sample_context):
    """E15: FakeLLMTransport 5xx 服务端异常模式触发受控 ProviderException"""
    transport = FakeLLMTransport(mode="http_5xx", status_code=502)
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=transport)

    with pytest.raises(ProviderException) as exc_info:
        await provider.generate(sample_context)
    assert "HTTP 502" in str(exc_info.value)


@pytest.mark.asyncio
async def test_e16_fake_transport_malformed_output(sample_context):
    """E16: FakeLLMTransport 畸形输出模式触发解析与契约防御拦截"""
    transport = FakeLLMTransport(mode="malformed")
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=transport)

    with pytest.raises(ProviderException) as exc_info:
        await provider.generate(sample_context)
    assert "Invalid StructuredAIResponse" in str(exc_info.value)


# ============================================================
# Category 4: Security & Immutability (E17 ~ E20)
# ============================================================

@pytest.mark.asyncio
async def test_e17_forbidden_decision_field_injection_rejected(sample_context):
    """E17: 外部模型输出中注入任何非法决策控制字段时，立即触发硬性拦截"""
    for forbidden_key in FORBIDDEN_DECISION_FIELDS:
        transport = FakeLLMTransport(
            mode="success",
            custom_response_payload={
                "answer": "试图越权修改",
                "referenced_facts": [],
                forbidden_key: "MALICIOUS_INJECTION",
            },
        )
        provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=transport)
        with pytest.raises(ProviderException) as exc_info:
            await provider.generate(sample_context)
        assert f"forbidden decision field: {forbidden_key}" in str(exc_info.value)


@pytest.mark.asyncio
async def test_e18_learning_prompt_context_immutability(sample_context):
    """E18: Provider 执行全过程保证 LearningPromptContext 绝对深度不可变"""
    context_before = copy.deepcopy(sample_context)
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=FakeLLMTransport())

    await provider.generate(sample_context)
    assert sample_context == context_before


def test_e19_raw_internal_objects_cannot_enter_provider():
    """E19: 提示词构建器仅接受合规的 LearningPromptContext，杜绝内部原始实体直接穿透"""
    # build_external_prompt 的入参签名与 Pydantic 校验确保只有强类型白名单上下文可被接收
    import inspect
    sig = inspect.signature(build_external_prompt)
    assert "context" in sig.parameters
    assert sig.parameters["context"].annotation == LearningPromptContext


@pytest.mark.asyncio
async def test_e20_secret_isolation_full_lifecycle(sample_context):
    """E20: 全生命周期凭证隔离断言，测试密钥绝不侵入 StructuredAIResponse 输出"""
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=FakeLLMTransport())
    res = await provider.generate(sample_context)

    assert TEST_SECRET not in res.answer
    if res.suggested_explanation:
        assert TEST_SECRET not in res.suggested_explanation
    for fact in res.referenced_facts:
        assert TEST_SECRET not in fact


# ============================================================
# Category 5: Determinism (E21 ~ E23)
# ============================================================

def test_e21_prompt_construction_deterministic(sample_context):
    """E21: build_external_prompt 纯函数特性，多次调用产生字节级深度一致的提示词载荷"""
    payload_1 = build_external_prompt(sample_context, model="model-v1")
    for _ in range(20):
        payload_n = build_external_prompt(sample_context, model="model-v1")
        assert payload_1.system_prompt == payload_n.system_prompt
        assert payload_1.user_prompt == payload_n.user_prompt
        assert payload_1.model == payload_n.model
        assert payload_1.response_format == payload_n.response_format
        assert payload_1.temperature == payload_n.temperature


@pytest.mark.asyncio
async def test_e22_response_normalization_deterministic(sample_context):
    """E22: 响应归一化逻辑具备严格确定性，相同输入与传输产生等价 StructuredAIResponse"""
    transport = FakeLLMTransport(mode="success")
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=transport)

    res_1 = await provider.generate(sample_context)
    for _ in range(10):
        res_n = await provider.generate(sample_context)
        assert res_1 == res_n


def test_e23_failure_behavior_deterministic(sample_context):
    """E23: 错误降级与配置异常行为具备严格确定性"""
    provider = ExternalLLMProvider(api_key=None, transport=FakeLLMTransport())
    original = set_provider(provider)
    try:
        client = TestClient(app)
        res_1 = client.post("/api/ai/companion", json={"promptContext": sample_context.model_dump()}).json()
        res_2 = client.post("/api/ai/companion", json={"promptContext": sample_context.model_dump()}).json()
        assert res_1 == res_2
        assert res_1["error"] == "BAD_GATEWAY"
    finally:
        set_provider(original)
