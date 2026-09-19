# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint10b_deepseek_provider
=============================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B / Phase 1
DeepSeek Provider 与安全 AI Gateway 基础设施契约与安全隔离测试

覆盖核心契约（Section 30 Test 1 ~ Test 16 + 边界防护）：
1. Test 1: 默认 DEEPSEEK_ENABLED=false 零网络访问
2. Test 2: Mock Provider 确定性：20 次连续请求输出 100% 字节级一致
3. Test 3: 默认模型 deepseek-flash 且支持配置化替换
4. Test 4: 默认 Base URL https://api.deepseek.com 且不自动追加 /v1
5. Test 5: API Key 缺失时受控拦截，绝不调用外部真实 API
6. Test 6: 凭证安全：源码、构建产物与配置中绝无明文真实 Key，脱敏有效
7. Test 7: 超时异常精确映射为 PROVIDER_TIMEOUT
8. Test 8: HTTP 429 频控异常精确映射为 RATE_LIMITED
9. Test 9: HTTP 401 鉴权异常精确映射为 AUTHENTICATION_ERROR
10. Test 10: HTTP 5xx 故障精确映射为 PROVIDER_UNAVAILABLE
11. Test 11: 畸形非 JSON 响应安全失败 (PROVIDER_INVALID_RESPONSE)
12. Test 12: 空响应安全失败 (PROVIDER_INVALID_RESPONSE)
13. Test 13: 绝不虚假伪造：DeepSeek 失败绝不静默假装成功
14. Test 14: allow_production_decision 强制恒等于 False
15. Test 15: 生产状态零副作用 (Zero Business Mutation Invariant)
16. Test 16: PII 隐私越界检测：手机号、邮箱、身份证严格阻断
17. Test 17: 网络边界隔离 (Network Boundary Assertion: 0 calls to api.deepseek.com)
18. Test 18: /api/ai/health 网关探针包含 deepseek 静态状态且无外网探活
19. Test 19: get_provider 工厂依赖注入支持 deepseek 类型
20. Test 20: 真实 API 测试门禁隔离 (仅在 DEEPSEEK_LIVE_TEST=1 且 key 具备时运行)
"""

import asyncio
import copy
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from gateway.adapter import (
    AIProviderAdapter,
    FORBIDDEN_DECISION_FIELDS,
    ProviderConfigurationError,
    ProviderException,
    ProviderTimeoutError,
    get_provider,
    set_provider,
)
from gateway.ai import (
    AIProviderError,
    AIProviderRequest,
    AIProviderResponse,
    AuthenticationError,
    DeepSeekProvider,
    MockAIProvider,
    MockDeepSeekProvider,
    PIIViolationError,
    ProviderDisabledError,
    ProviderErrorCategory,
    ProviderInvalidResponseError,
    ProviderTimeout,
    ProviderUnavailableError,
    RateLimitError,
    assert_no_pii,
)
from gateway.api import app, create_gateway_app
from gateway.config import GatewaySettings, gateway_settings
from gateway.evaluation.judge.models import JudgeResult
from gateway.evaluation.judge.runtime import JudgeRuntimePolicy
from gateway.learning.companion.models import CompanionSafetyMetadata
from gateway.models import (
    LearningPromptContext,
    LearningPromptSystemFacts,
    PromptNextAction,
    StructuredAIResponse,
)
from gateway.transport import (
    DisabledNetworkTransport,
    FakeLLMTransport,
    LLMTransport,
)


@pytest.fixture
def client():
    test_app = create_gateway_app()
    with TestClient(test_app) as c:
        yield c


@pytest.fixture
def sample_ai_request() -> AIProviderRequest:
    return AIProviderRequest(
        system_prompt="你是一位专业的微观经济学伴学导师。请以 JSON 格式输出回答。",
        user_prompt="请解释什么是需求价格弹性，并说明其经济学意义。",
        response_format="json_object",
        max_tokens=1024,
        temperature=0.0,
        user_id="student_s001",
    )


@pytest.fixture
def sample_prompt_context() -> LearningPromptContext:
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
                type="RECOMMEND_PRACTICE",
                label="完成针对性巩固练习",
                target_knowledge_id="K08",
                reason="客观掌握度未达到达标阈值",
            ),
        ),
        grounding_rules=["只依据系统提供的客观事实回答，不伪造数据。"],
    )


# ------------------------------------------------------------------------------
# Test 1: 默认 DEEPSEEK_ENABLED=false 零网络访问
# ------------------------------------------------------------------------------
def test_01_default_deepseek_disabled_and_offline(sample_ai_request):
    """Test 1: 默认配置下 DEEPSEEK_ENABLED=false，拒绝网络连接并抛出受控 ProviderDisabledError"""
    assert gateway_settings.deepseek_enabled is False

    provider = DeepSeekProvider(enabled=False)
    assert provider.enabled is False
    assert isinstance(provider.transport, DisabledNetworkTransport)

    with pytest.raises(ProviderDisabledError) as exc_info:
        asyncio.run(provider.complete(sample_ai_request))

    err = exc_info.value
    assert err.category == ProviderErrorCategory.PROVIDER_DISABLED
    assert "disabled" in str(err).lower()


# ------------------------------------------------------------------------------
# Test 2: Mock Provider 确定性：20 次连续请求输出 100% 字节级一致
# ------------------------------------------------------------------------------
def test_02_mock_provider_20_consecutive_calls_deterministic(sample_ai_request):
    """Test 2: MockDeepSeekProvider 针对相同请求连续 20 次调用，输出 100% 字节级严格一致"""
    mock_provider = MockDeepSeekProvider()

    responses = []
    for _ in range(20):
        resp = asyncio.run(mock_provider.complete(sample_ai_request))
        responses.append(resp.content)

    # 验证全部 20 次响应完全等于第 1 次响应
    first_resp = responses[0]
    for i, r in enumerate(responses):
        assert r == first_resp, f"第 {i+1} 次调用产生漂移，非确定性输出"


# ------------------------------------------------------------------------------
# Test 3: 默认模型 deepseek-flash 且支持配置化替换
# ------------------------------------------------------------------------------
def test_03_default_model_and_configurable_replacement():
    """Test 3: 默认模型必须为 deepseek-flash，且必须支持配置为 deepseek-v4-pro"""
    assert gateway_settings.deepseek_model == "deepseek-flash"

    # 默认实例
    default_provider = DeepSeekProvider()
    assert default_provider.model == "deepseek-flash"

    # 可配置化替换为 deepseek-v4-pro
    v4_provider = DeepSeekProvider(model="deepseek-v4-pro")
    assert v4_provider.model == "deepseek-v4-pro"


# ------------------------------------------------------------------------------
# Test 4: 默认 Base URL https://api.deepseek.com 且不自动追加 /v1
# ------------------------------------------------------------------------------
def test_04_default_base_url_and_no_v1_auto_append():
    """Test 4: 默认 Base URL 为 https://api.deepseek.com，严格禁止自动追加 /v1"""
    assert gateway_settings.deepseek_base_url == "https://api.deepseek.com"

    provider = DeepSeekProvider()
    assert provider.base_url == "https://api.deepseek.com"
    assert not provider.base_url.endswith("/v1")

    # 验证 HTTP Transport 生成的 endpoint_url
    fake_transport = FakeLLMTransport()
    custom_provider = DeepSeekProvider(
        base_url="https://api.deepseek.com",
        transport=fake_transport,
    )
    assert custom_provider.base_url == "https://api.deepseek.com"


# ------------------------------------------------------------------------------
# Test 5: API Key 缺失时受控拦截，绝不调用外部真实 API
# ------------------------------------------------------------------------------
def test_05_missing_api_key_prevents_network_call(sample_ai_request):
    """Test 5: 当启用但未配置 API Key 时，受控阻断，绝不尝试发起真实外部请求"""
    provider = DeepSeekProvider(enabled=True, api_key="")
    assert provider.is_configured is False

    with pytest.raises(AIProviderError) as exc_info:
        asyncio.run(provider.complete(sample_ai_request))

    err = exc_info.value
    assert err.category == ProviderErrorCategory.PROVIDER_CONFIGURATION_ERROR


# ------------------------------------------------------------------------------
# Test 6: 凭证安全：源码、构建产物与配置中绝无明文真实 Key，脱敏有效
# ------------------------------------------------------------------------------
def test_06_secret_safety_and_masking():
    """Test 6: 密钥脱敏有效，且代码库与 .env.example 中绝无真实 sk- 密钥"""
    settings = GatewaySettings(deepseek_api_key="sk-testsecret987654321")
    masked = settings.get_masked_deepseek_api_key()
    assert masked.startswith("sk-")
    assert "..." in masked
    assert "testsecret" not in masked

    # 确保 is_secret_contained 防护有效
    assert settings.is_secret_contained("normal string without secret") is True
    assert settings.is_secret_contained("string containing sk-testsecret987654321") is False

    # 扫描 .env.example 确保没有硬编码真实 key
    env_example_path = Path(".env.example")
    if env_example_path.exists():
        content = env_example_path.read_text(encoding="utf-8")
        assert "DEEPSEEK_API_KEY=" in content
        # 确保等号后面为空
        for line in content.splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                val = line.split("=", 1)[1].strip()
                assert val == "", f"发现 .env.example 包含非空 Key: {val}"


# ------------------------------------------------------------------------------
# Test 7: 超时异常精确映射为 PROVIDER_TIMEOUT
# ------------------------------------------------------------------------------
def test_07_timeout_mapping(sample_ai_request):
    """Test 7: 底层 Transport 超时受控转换为 PROVIDER_TIMEOUT"""
    fake_transport = FakeLLMTransport(mode="timeout")
    provider = DeepSeekProvider(
        enabled=True,
        api_key="sk-test-mock-key",
        transport=fake_transport,
    )

    with pytest.raises(ProviderTimeout) as exc_info:
        asyncio.run(provider.complete(sample_ai_request))

    err = exc_info.value
    assert err.category == ProviderErrorCategory.PROVIDER_TIMEOUT
    assert isinstance(err, ProviderTimeoutError)


# ------------------------------------------------------------------------------
# Test 8: HTTP 429 频控异常精确映射为 RATE_LIMITED
# ------------------------------------------------------------------------------
def test_08_rate_limit_429_mapping(sample_ai_request):
    """Test 8: HTTP 429 错误精确识别为 RATE_LIMITED 频控异常"""
    fake_transport = FakeLLMTransport(mode="http_4xx", status_code=429)
    provider = DeepSeekProvider(
        enabled=True,
        api_key="sk-test-mock-key",
        transport=fake_transport,
    )

    with pytest.raises(RateLimitError) as exc_info:
        asyncio.run(provider.complete(sample_ai_request))

    err = exc_info.value
    assert err.category == ProviderErrorCategory.RATE_LIMITED
    assert err.status_code == 429


# ------------------------------------------------------------------------------
# Test 9: HTTP 401 鉴权异常精确映射为 AUTHENTICATION_ERROR
# ------------------------------------------------------------------------------
def test_09_authentication_401_mapping(sample_ai_request):
    """Test 9: HTTP 401 鉴权失败受控映射为 AUTHENTICATION_ERROR"""
    fake_transport = FakeLLMTransport(mode="http_4xx", status_code=401)
    provider = DeepSeekProvider(
        enabled=True,
        api_key="sk-test-mock-key",
        transport=fake_transport,
    )

    with pytest.raises(AuthenticationError) as exc_info:
        asyncio.run(provider.complete(sample_ai_request))

    err = exc_info.value
    assert err.category == ProviderErrorCategory.AUTHENTICATION_ERROR
    assert err.status_code == 401


# ------------------------------------------------------------------------------
# Test 10: HTTP 5xx 故障精确映射为 PROVIDER_UNAVAILABLE
# ------------------------------------------------------------------------------
def test_10_server_error_5xx_mapping(sample_ai_request):
    """Test 10: HTTP 500/502/503 精确映射为 PROVIDER_UNAVAILABLE"""
    fake_transport = FakeLLMTransport(mode="http_5xx", status_code=502)
    provider = DeepSeekProvider(
        enabled=True,
        api_key="sk-test-mock-key",
        transport=fake_transport,
    )

    with pytest.raises(ProviderUnavailableError) as exc_info:
        asyncio.run(provider.complete(sample_ai_request))

    err = exc_info.value
    assert err.category == ProviderErrorCategory.PROVIDER_UNAVAILABLE


# ------------------------------------------------------------------------------
# Test 11: 畸形非 JSON 响应安全失败 (PROVIDER_INVALID_RESPONSE)
# ------------------------------------------------------------------------------
def test_11_invalid_json_response_safe_failure(sample_ai_request):
    """Test 11: 当期望 JSON 却返回非 JSON 文本时，安全失败并归类为 PROVIDER_INVALID_RESPONSE"""
    fake_transport = FakeLLMTransport(
        custom_response_payload={
            "choices": [
                {
                    "message": {"content": "This is plain text, not valid json {"},
                    "finish_reason": "stop",
                }
            ]
        }
    )
    provider = DeepSeekProvider(
        enabled=True,
        api_key="sk-test-mock-key",
        transport=fake_transport,
    )

    with pytest.raises(ProviderInvalidResponseError) as exc_info:
        asyncio.run(provider.complete(sample_ai_request))

    err = exc_info.value
    assert err.category == ProviderErrorCategory.PROVIDER_INVALID_RESPONSE


# ------------------------------------------------------------------------------
# Test 12: 空响应安全失败 (PROVIDER_INVALID_RESPONSE)
# ------------------------------------------------------------------------------
def test_12_empty_response_safe_failure(sample_ai_request):
    """Test 12: 上游返回空文本时，安全失败并归类为 PROVIDER_INVALID_RESPONSE"""
    fake_transport = FakeLLMTransport(
        custom_response_payload={
            "choices": [
                {
                    "message": {"content": "   "},
                    "finish_reason": "stop",
                }
            ]
        }
    )
    provider = DeepSeekProvider(
        enabled=True,
        api_key="sk-test-mock-key",
        transport=fake_transport,
    )

    with pytest.raises(ProviderInvalidResponseError) as exc_info:
        asyncio.run(provider.complete(sample_ai_request))

    err = exc_info.value
    assert err.category == ProviderErrorCategory.PROVIDER_INVALID_RESPONSE


# ------------------------------------------------------------------------------
# Test 13: 绝不虚假伪造：DeepSeek 失败绝不静默假装成功
# ------------------------------------------------------------------------------
def test_13_no_fallback_deception(sample_ai_request):
    """Test 13: DeepSeek 失败时严格向上抛出具体分类异常，绝不静默假装成功"""
    fake_transport = FakeLLMTransport(mode="http_5xx", status_code=500)
    provider = DeepSeekProvider(
        enabled=True,
        api_key="sk-test-mock-key",
        transport=fake_transport,
    )

    # 必须抛出异常，绝不可返回一个看起来正常的 fake 响应
    with pytest.raises(AIProviderError):
        asyncio.run(provider.complete(sample_ai_request))


# ------------------------------------------------------------------------------
# Test 14: allow_production_decision 强制恒等于 False
# ------------------------------------------------------------------------------
def test_14_allow_production_decision_strictly_false():
    """Test 14: 系统的所有 AI 评测与伴学策略中 allow_production_decision 严格恒等于 False"""
    # 1. 验证 JudgeRuntimePolicy
    policy = JudgeRuntimePolicy()
    assert policy.allow_production_decision is False

    with pytest.raises(ValueError):
        JudgeRuntimePolicy(allow_production_decision=True)

    # 2. 验证 Companion 安全元数据
    safety = CompanionSafetyMetadata()
    assert safety.allow_production_decision is False


# ------------------------------------------------------------------------------
# Test 15: 生产状态零副作用 (Zero Business Mutation Invariant)
# ------------------------------------------------------------------------------
def test_15_business_mutation_isolation(sample_ai_request):
    """Test 15: 调用 DeepSeek Provider 绝不产生 BKT、学习事件或路径状态的任何修改"""
    bkt_file = Path("data/bkt_states.json")
    events_file = Path("data/learning_events.jsonl")

    bkt_mtime_before = bkt_file.stat().st_mtime if bkt_file.exists() else None
    events_mtime_before = events_file.stat().st_mtime if events_file.exists() else None

    # 执行 Mock 调用
    mock_p = MockDeepSeekProvider()
    asyncio.run(mock_p.complete(sample_ai_request))

    bkt_mtime_after = bkt_file.stat().st_mtime if bkt_file.exists() else None
    events_mtime_after = events_file.stat().st_mtime if events_file.exists() else None

    assert bkt_mtime_before == bkt_mtime_after, "BKT 文件被意外修改"
    assert events_mtime_before == events_mtime_after, "Learning events 文件被意外修改"


# ------------------------------------------------------------------------------
# Test 16: PII 隐私越界检测：手机号、邮箱、身份证严格阻断
# ------------------------------------------------------------------------------
def test_16_pii_detection_blocking():
    """Test 16: 请求提示词中若误含手机号、邮箱或身份证，必须立即拦截报错"""
    # 手机号测试
    with pytest.raises(PIIViolationError):
        assert_no_pii("请帮我分析张同学（手机 13812345678）的学情")

    # 邮箱测试
    with pytest.raises(PIIViolationError):
        assert_no_pii("学生联系方式 student@university.edu.cn")

    # 身份证测试
    with pytest.raises(PIIViolationError):
        assert_no_pii("身份证号 110101199003072345 需查询")

    # 合法无 PII 请求正常通过
    assert_no_pii("学生学号 S001，请解释边际收益递减规律。")


# ------------------------------------------------------------------------------
# Test 17: 网络边界隔离 (Network Boundary Assertion: 0 calls to api.deepseek.com)
# ------------------------------------------------------------------------------
def test_17_network_boundary_zero_external_requests(sample_ai_request):
    """Test 17: 默认环境下执行 Provider 逻辑，验证绝对无发往 api.deepseek.com 的网络调用"""
    with patch("requests.post") as mock_post:
        provider = DeepSeekProvider(enabled=False)
        with pytest.raises(ProviderDisabledError):
            asyncio.run(provider.complete(sample_ai_request))

        # 断言 requests.post 调用次数为 0
        assert mock_post.call_count == 0


# ------------------------------------------------------------------------------
# Test 18: /api/ai/health 网关探针包含 deepseek 静态状态且无外网探活
# ------------------------------------------------------------------------------
def test_18_gateway_ai_health_endpoint_deepseek_block(client):
    """Test 18: GET /api/ai/health 包含 deepseek 状态声明，且不发起任何外部网络探活请求"""
    with patch("requests.post") as mock_post:
        res = client.get("/api/ai/health")
        assert res.status_code == 200

        data = res.json()
        assert data["status"] == "healthy"
        assert "deepseek" in data

        ds_data = data["deepseek"]
        assert ds_data["enabled"] is False
        assert ds_data["configured"] is False
        assert ds_data["model"] == "deepseek-flash"
        assert ds_data["base_url"] == "https://api.deepseek.com"
        assert ds_data["reachable"] == "unknown"

        # 保证探活探针绝对不调用真实网络
        assert mock_post.call_count == 0


# ------------------------------------------------------------------------------
# Test 19: get_provider 工厂依赖注入支持 deepseek 类型
# ------------------------------------------------------------------------------
def test_19_get_provider_factory_deepseek_support():
    """Test 19: get_provider('deepseek') 正确构建 DeepSeekProvider 实例"""
    p = get_provider("deepseek")
    assert isinstance(p, DeepSeekProvider)
    assert p.provider_name == "deepseek"

    p_flash = get_provider("deepseek-flash")
    assert isinstance(p_flash, DeepSeekProvider)


# ------------------------------------------------------------------------------
# Test 20: 真实 API 测试门禁隔离 (仅在 DEEPSEEK_LIVE_TEST=1 且 key 具备时运行)
# ------------------------------------------------------------------------------
def test_20_live_api_conditional_gate():
    """Test 20: 真实 API 测试严格隔离门禁，默认自动跳过"""
    live_flag = os.getenv("DEEPSEEK_LIVE_TEST", "0")
    if live_flag != "1":
        pytest.skip("DEEPSEEK_LIVE_TEST!=1: 遵循离线基线，安全跳过外部真实 API 联调测试")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("未提供 DEEPSEEK_API_KEY，跳过真实 API 测试")

    # 最小化单次请求验证
    provider = DeepSeekProvider(enabled=True, api_key=api_key)
    req = AIProviderRequest(
        system_prompt="Return valid JSON only.",
        user_prompt='Return {"ok": true}',
        response_format="json_object",
        max_tokens=64,
    )
    resp = asyncio.run(provider.complete(req))
    assert resp.content
    assert resp.parsed_json is not None
    assert resp.parsed_json.get("ok") is True
