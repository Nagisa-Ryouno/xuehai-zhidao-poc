# -*- coding: utf-8 -*-
"""
gateway.tests.test_judge_transport
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 / Checkpoint 1: Controlled Real LLM Transport & Configuration Layer
测试套件 (JT1 ~ JT15)
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from gateway.adapter import ProviderException, ProviderTimeoutError
from gateway.evaluation.judge.config import (
    JudgeSettings,
    build_judge_transport,
    get_judge_settings,
)
from gateway.transport import (
    DisabledNetworkTransport,
    FakeLLMTransport,
    HttpLLMTransport,
    LLMTransport,
)


# =====================================================================
# JT1 ~ JT7: JudgeSettings 配置与密钥安全契约
# =====================================================================

def test_jt1_default_settings_safely_disabled(monkeypatch):
    """JT1: 无任何环境变量时，默认配置必须安全关闭，禁止初始化真实网络"""
    # 清理所有 AI_JUDGE 相关环境变量
    for key in list(os.environ.keys()):
        if key.startswith("AI_JUDGE_"):
            monkeypatch.delenv(key, raising=False)

    settings = get_judge_settings(reload=True)
    assert settings.enabled is False
    assert settings.api_key is None

    # 工厂函数在 disabled 状态下绝不返回 HttpLLMTransport
    transport = build_judge_transport(settings)
    assert isinstance(transport, DisabledNetworkTransport)
    assert not isinstance(transport, HttpLLMTransport)


def test_jt2_enabled_parsing_case_insensitive(monkeypatch):
    """JT2: AI_JUDGE_ENABLED 正确解析 true/TRUE/True/1"""
    for truthy_val in ["true", "TRUE", "True", "1", "yes", "YES"]:
        monkeypatch.setenv("AI_JUDGE_ENABLED", truthy_val)
        settings = JudgeSettings.from_env()
        assert settings.enabled is True, f"Failed for {truthy_val}"


def test_jt3_false_values_remain_disabled(monkeypatch):
    """JT3: false/FALSE/0 等值严格解析为 False，绝不误开启"""
    for falsy_val in ["false", "FALSE", "False", "0", "no", "NO", "off", ""]:
        monkeypatch.setenv("AI_JUDGE_ENABLED", falsy_val)
        settings = JudgeSettings.from_env()
        assert settings.enabled is False, f"Failed for {falsy_val}"


def test_jt4_reads_all_judge_env_vars(monkeypatch):
    """JT4: 能够完整读取所有 AI_JUDGE_* 环境变量并产出强类型配置对象"""
    monkeypatch.setenv("AI_JUDGE_ENABLED", "true")
    monkeypatch.setenv("AI_JUDGE_PROVIDER", "deepseek")
    monkeypatch.setenv("AI_JUDGE_MODEL", "deepseek-chat")
    monkeypatch.setenv("AI_JUDGE_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("AI_JUDGE_API_KEY", "dummy-test-key-12345678")
    monkeypatch.setenv("AI_JUDGE_TIMEOUT_MS", "3000")
    monkeypatch.setenv("AI_JUDGE_MAX_RETRIES", "1")
    monkeypatch.setenv("AI_JUDGE_TEMPERATURE", "0.2")
    monkeypatch.setenv("AI_JUDGE_CIRCUIT_FAIL_THRESHOLD", "5")

    settings = JudgeSettings.from_env()
    assert settings.enabled is True
    assert settings.provider == "deepseek"
    assert settings.model == "deepseek-chat"
    assert settings.base_url == "https://api.deepseek.com/v1"
    assert settings.api_key == "dummy-test-key-12345678"
    assert settings.timeout_ms == 3000
    assert settings.max_retries == 1
    assert settings.temperature == 0.2
    assert settings.circuit_fail_threshold == 5


def test_jt5_safe_defaults():
    """JT5: 未配置时必须使用绝对安全默认值，绝不私自连接线上生产模型"""
    settings = JudgeSettings()
    assert settings.enabled is False
    assert settings.timeout_ms == 5000
    assert settings.max_retries == 2
    assert settings.temperature == 0.0
    assert settings.circuit_fail_threshold == 3
    assert settings.base_url is None
    assert settings.api_key is None


def test_jt6_api_key_not_in_repr():
    """JT6: 敏感 API Key 绝对禁止出现在 repr(settings) 中"""
    secret = "secret-super-sensitive-token-999"
    settings = JudgeSettings(api_key=secret)
    repr_str = repr(settings)
    assert secret not in repr_str
    assert "..." in repr_str or "***" in repr_str


def test_jt7_masked_api_key():
    """JT7: get_masked_api_key() 永远安全脱敏，稳定输出"""
    # 1. 空 key
    settings_empty = JudgeSettings(api_key=None)
    assert settings_empty.get_masked_api_key() in ["<UNSET>", "(empty)"]

    # 2. 短 key (<= 8 字符)
    settings_short = JudgeSettings(api_key="12345678")
    assert settings_short.get_masked_api_key() == "***"

    # 3. 正常 key
    raw_key = "sk-test-abc123456789xyz"
    settings_normal = JudgeSettings(api_key=raw_key)
    masked = settings_normal.get_masked_api_key()
    assert raw_key not in masked
    assert masked.startswith("sk-")
    assert masked.endswith("xyz")


# =====================================================================
# JT8 ~ JT11: HttpLLMTransport 契约与离线安全
# =====================================================================

def test_jt8_http_transport_inherits_llm_transport():
    """JT8: HttpLLMTransport 必须严格继承已有 LLMTransport 抽象基类"""
    transport = HttpLLMTransport(
        base_url="https://api.example.com/v1",
        api_key="dummy-key",
    )
    assert isinstance(transport, LLMTransport)


@pytest.mark.asyncio
async def test_jt9_http_transport_payload_contract():
    """JT9: HttpLLMTransport 构造标准 OpenAI-compatible 请求体契约 (100% Mock)"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "chatcmpl-test",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"overall_score": 0.85, "confidence": 0.90}',
                }
            }
        ],
    }

    mock_client = MagicMock()
    mock_client.post.return_value = mock_response

    transport = HttpLLMTransport(
        base_url="https://api.example.com/v1",
        api_key="dummy-token",
        model="test-judge-model",
        client=mock_client,
    )

    request_payload = {
        "model": "test-judge-model",
        "system_prompt": "You are an evaluation observer.",
        "user_prompt": "Evaluate this response.",
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }

    result = await transport.send_payload(request_payload, timeout_ms=3000)

    assert result == mock_response.json.return_value
    assert mock_client.post.called

    # 检验调用的 URL 和参数
    call_args = mock_client.post.call_args
    called_url = call_args[0][0] if call_args[0] else call_args[1].get("url")
    assert called_url == "https://api.example.com/v1/chat/completions"

    called_json = call_args[1].get("json")
    assert called_json["model"] == "test-judge-model"
    assert called_json["temperature"] == 0.0
    assert called_json["response_format"] == {"type": "json_object"}
    assert len(called_json["messages"]) == 2
    assert called_json["messages"][0]["role"] == "system"
    assert called_json["messages"][0]["content"] == "You are an evaluation observer."
    assert called_json["messages"][1]["role"] == "user"
    assert called_json["messages"][1]["content"] == "Evaluate this response."


@pytest.mark.asyncio
async def test_jt10_authorization_header_and_secret_isolation():
    """JT10: Authorization: Bearer <API_KEY> 正常传递，但在异常与日志中绝对不泄露"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized access token"
    mock_client.post.return_value = mock_response

    raw_secret_key = "super-secret-key-that-must-not-leak"
    transport = HttpLLMTransport(
        base_url="https://api.example.com/v1",
        api_key=raw_secret_key,
        client=mock_client,
    )

    # 1. 验证发出的请求头携带 Authorization
    with pytest.raises(ProviderException) as exc_info:
        await transport.send_payload({"user_prompt": "hi"}, timeout_ms=1000)

    # 2. 验证抛出的异常消息绝对不包含原始 Key
    assert raw_secret_key not in str(exc_info.value)
    assert "401" in str(exc_info.value)

    # 3. 验证调用传递了 header
    called_headers = mock_client.post.call_args[1].get("headers", {})
    assert called_headers.get("Authorization") == f"Bearer {raw_secret_key}"


def test_jt11_disabled_environment_must_not_initialize_http():
    """JT11: 当 AI_JUDGE_ENABLED=false 时，构建器必须返回 DisabledNetworkTransport"""
    settings = JudgeSettings(
        enabled=False,
        base_url="https://api.deepseek.com/v1",
        api_key="sk-secret-key",
    )

    transport = build_judge_transport(settings)
    assert isinstance(transport, DisabledNetworkTransport)
    assert not isinstance(transport, HttpLLMTransport)


# =====================================================================
# JT12 ~ JT13: 现有 Stage E Transport 契约严格兼容性
# =====================================================================

@pytest.mark.asyncio
async def test_jt12_existing_fake_llm_transport_compatibility():
    """JT12: 现有 FakeLLMTransport 行为严格保持兼容"""
    fake = FakeLLMTransport(mode="success", custom_response_payload={"answer": "ok"})
    res = await fake.send_payload({}, timeout_ms=1000)
    assert res == {"answer": "ok"}

    fake_timeout = FakeLLMTransport(mode="timeout")
    with pytest.raises(ProviderTimeoutError):
        await fake_timeout.send_payload({}, timeout_ms=500)


@pytest.mark.asyncio
async def test_jt13_existing_disabled_transport_compatibility():
    """JT13: 现有 DisabledNetworkTransport 依然坚决阻止网络请求"""
    disabled = DisabledNetworkTransport()
    with pytest.raises(ProviderException) as exc_info:
        await disabled.send_payload({}, timeout_ms=1000)
    assert "Real network calls are disabled" in str(exc_info.value)


# =====================================================================
# JT14 ~ JT15: 参数合法性与 Base URL 校验
# =====================================================================

def test_jt14_invalid_timeout_retries_temperature_circuit_fail():
    """JT14: 非法运行参数被拒绝并抛出 ValueError"""
    with pytest.raises(ValueError, match="timeout_ms"):
        JudgeSettings(timeout_ms=0)

    with pytest.raises(ValueError, match="timeout_ms"):
        JudgeSettings(timeout_ms=-100)

    with pytest.raises(ValueError, match="max_retries"):
        JudgeSettings(max_retries=-1)

    with pytest.raises(ValueError, match="temperature"):
        JudgeSettings(temperature=-0.1)

    with pytest.raises(ValueError, match="temperature"):
        JudgeSettings(temperature=2.1)

    with pytest.raises(ValueError, match="circuit_fail_threshold"):
        JudgeSettings(circuit_fail_threshold=0)


def test_jt15_base_url_validation():
    """JT15: Base URL 校验（拒绝非法非 URL 字符串，允许合法 http/https URL）"""
    # 允许合法的 http / https URL
    s1 = JudgeSettings(base_url="https://api.deepseek.com/v1")
    assert s1.base_url == "https://api.deepseek.com/v1"

    s2 = JudgeSettings(base_url="https://api.openai.com/v1")
    assert s2.base_url == "https://api.openai.com/v1"

    s3 = JudgeSettings(base_url="http://internal-llm.example:8080/v1")
    assert s3.base_url == "http://internal-llm.example:8080/v1"

    s_none = JudgeSettings(base_url=None)
    assert s_none.base_url is None

    # 拒绝明显非 URL 的字符串
    with pytest.raises(ValueError, match="base_url"):
        JudgeSettings(base_url="not-a-url")

    with pytest.raises(ValueError, match="base_url"):
        JudgeSettings(base_url="ftp://invalid-scheme.com")
