# -*- coding: utf-8 -*-
"""
gateway.tests.test_observability_contract
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage F: 可观测性与生产加固契约测试 (F1 ~ F14)

覆盖维度：
F1: AuditEvent 契约与必须字段
F2: 严格白名单 (extra='forbid')
F3: Request Correlation ID 规范性与无害性
F4: Failure Taxonomy 故障分类矩阵
F5: 内部故障分类与用户界面文案彻底隔离
F6: Safe Audit Sink (Null & Memory)
F7: Redaction 净化层
F8: 异常净化层
F9: 耗时观测 (Latency Observation)
F10: 内部指标契约 (Outcome Metrics)
F11: Audit Lifecycle 事件生命周期时序
F12: 学习引擎确定性上下文绝对不可变性 (Invariant F12)
F13: 网关端点对 Audit/Metrics 崩溃的旁路容灾 (Fail-Safe)
F14: 敏感内容默认不可观测性 (Metadata observable, Content protected)
"""

import copy
import time
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from gateway.audit import (
    AuditEvent,
    MemoryAuditSink,
    MemoryMetricsSink,
    NullAuditSink,
    NullMetricsSink,
    ProviderFailureClass,
    generate_request_id,
    get_audit_sink,
    get_metrics_sink,
    set_audit_sink,
    set_metrics_sink,
    METRIC_REQUESTS_TOTAL,
    METRIC_FAILURES_TOTAL,
    METRIC_FALLBACK_TOTAL,
    METRIC_TIMEOUT_TOTAL,
    METRIC_POLICY_VIOLATIONS_TOTAL,
)
from gateway.adapter import (
    MockGatewayProvider,
    ExternalLLMProvider,
    ProviderException,
    ProviderTimeoutError,
    set_provider,
)
from gateway.api import app
from gateway.models import LearningPromptContext, StructuredAIResponse
from gateway.transport import FakeLLMTransport

TEST_SECRET = "TEST_SECRET_DO_NOT_USE_998877"


@pytest.fixture
def sample_payload() -> dict:
    """标准测试请求载荷"""
    return {
        "promptContext": {
            "user_question": "为什么我需求价格弹性的掌握度只有46%？",
            "system_facts": {
                "student_id": "S001",
                "student_name": "张小凡",
                "major": "经济学",
                "grade": "大二",
                "learning_goal": "微观分析",
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
                    "label": "继续微测验",
                    "target_knowledge_id": "K08",
                    "reason": "巩固基础",
                },
            },
            "grounding_rules": ["严格基于客观事实"],
        },
        "question": "为什么我需求价格弹性的掌握度只有46%？",
    }


# ============================================================
# F1, F2: AuditEvent Schema & Allowlist
# ============================================================

def test_f01_audit_event_schema_contract():
    """F1: AuditEvent 模型具备规范的必须字段与默认时间戳"""
    event = AuditEvent(
        event_name="REQUEST_STARTED",
        request_id="req_abc123456789",
        provider="mock",
        model="mock-companion-v1",
        status="SUCCESS",
        latency_ms=12.5,
    )
    assert event.event_name == "REQUEST_STARTED"
    assert event.request_id == "req_abc123456789"
    assert event.latency_ms == 12.5
    assert event.timestamp.endswith("Z") or "+00:00" in event.timestamp


def test_f02_audit_event_strict_allowlist():
    """F2: 严格白名单防御，非法未授权字段传入时抛出 ValidationError"""
    with pytest.raises(ValidationError):
        AuditEvent(
            event_name="REQUEST_COMPLETED",
            request_id="req_001",
            provider="mock",
            model="mock",
            status="SUCCESS",
            unauthorized_field="malicious_payload",
        )


# ============================================================
# F3: Request Correlation ID
# ============================================================

def test_f03_request_id_format_and_safety():
    """F3: Request Correlation ID 格式规范且不包含敏感信息"""
    req_ids = [generate_request_id() for _ in range(50)]
    assert len(set(req_ids)) == 50  # 保证唯一性
    for r_id in req_ids:
        assert r_id.startswith("req_")
        assert len(r_id) == 16
        # 绝不包含用户标识、邮箱或密钥模式
        assert "@" not in r_id
        assert "sk-" not in r_id


# ============================================================
# F4, F5: Failure Taxonomy & Separation from User-Facing Text
# ============================================================

def test_f04_failure_taxonomy_matrix():
    """F4: Failure Taxonomy 覆盖所有预定义的受控错误分类"""
    expected_classes = {
        "NONE",
        "PROVIDER_CONFIGURATION_ERROR",
        "PROVIDER_TIMEOUT",
        "PROVIDER_UNAVAILABLE",
        "PROVIDER_BAD_RESPONSE",
        "PROVIDER_POLICY_VIOLATION",
        "NETWORK_FAILURE",
        "FACT_VALIDATION_FAILURE",
        "GATEWAY_INTERNAL_ERROR",
        "UNKNOWN_FAILURE",
    }
    actual_classes = {item.value for item in ProviderFailureClass}
    assert expected_classes.issubset(actual_classes)


def test_f05_internal_failure_separated_from_user_facing_error(sample_payload):
    """F5: 内部故障分类标签绝不泄露给学生端，学生端只看到温和安全文本"""
    # 模拟 Provider 超时
    fake_transport = FakeLLMTransport(mode="timeout")
    provider = ExternalLLMProvider(api_key=TEST_SECRET, transport=fake_transport)
    original = set_provider(provider)
    audit_sink = MemoryAuditSink()
    set_audit_sink(audit_sink)

    try:
        client = TestClient(app)
        response = client.post("/api/ai/companion", json=sample_payload)
        assert response.status_code == 504
        data = response.json()

        # 学生端看到的 answer 必须是温和静态文案
        assert "抱歉，伴学服务响应超时，请稍后重试。" in data["answer"]
        assert "PROVIDER_TIMEOUT" not in data["answer"]
        assert "gateway/adapter.py" not in data["answer"]

        # 内部审计事件准确记录了分类
        failed_events = [e for e in audit_sink.events if e.failure_class == "PROVIDER_TIMEOUT"]
        assert len(failed_events) >= 1
    finally:
        set_provider(original)
        set_audit_sink(None)


# ============================================================
# F6: Safe Audit Sink
# ============================================================

def test_f06_audit_sink_mechanisms():
    """F6: NullAuditSink 默认静默与 MemoryAuditSink 准确捕获事件"""
    null_sink = NullAuditSink()
    dummy = AuditEvent(
        event_name="TEST",
        request_id="req_001",
        provider="mock",
        model="test",
        status="SUCCESS",
    )
    null_sink.record(dummy)  # 无报错

    mem_sink = MemoryAuditSink()
    mem_sink.record(dummy)
    assert len(mem_sink.events) == 1
    assert mem_sink.events[0].request_id == "req_001"
    mem_sink.clear()
    assert len(mem_sink.events) == 0


# ============================================================
# F7, F8: Redaction Layer & Exception Sanitization
# ============================================================

def test_f07_redaction_layer_sanitization():
    """F7: sanitize_audit_payload 深度净化敏感键与敏感字符串"""
    from gateway.redaction import sanitize_audit_payload
    payload = {
        "safe_field": "ok",
        "api_key": "sk-proj-secret123",
        "nested": {
            "prompt": "secret prompt text",
            "token": "secret token",
            "normal": "user message",
        },
    }
    cleaned = sanitize_audit_payload(payload)
    assert "api_key" not in cleaned
    assert "prompt" not in cleaned["nested"]
    assert "token" not in cleaned["nested"]
    assert cleaned["nested"]["normal"] == "user message"


def test_f08_exception_sanitization_contract():
    """F8: sanitize_exception_message 净化异常消息，消除 Secret 与路径"""
    from gateway.redaction import sanitize_exception_message
    exc = Exception(f"Failed with key {TEST_SECRET} in C:\\xuehai\\gateway\\adapter.py")
    cleaned = sanitize_exception_message(exc)
    assert TEST_SECRET not in cleaned
    assert "C:\\xuehai" not in cleaned
    assert "[REDACTED_SECRET]" in cleaned
    assert "[REDACTED_PATH]" in cleaned


# ============================================================
# F9: Latency Observation
# ============================================================

def test_f09_latency_observation(sample_payload):
    """F9: 请求耗时以毫秒精准记录在审计元数据中，不影响回答内容"""
    mem_sink = MemoryAuditSink()
    set_audit_sink(mem_sink)
    try:
        client = TestClient(app)
        res = client.post("/api/ai/companion", json=sample_payload)
        assert res.status_code == 200

        completed = [e for e in mem_sink.events if e.event_name == "REQUEST_COMPLETED"]
        assert len(completed) >= 1
        latency = completed[0].latency_ms
        assert latency is not None
        assert latency >= 0.0
        assert isinstance(latency, float)
    finally:
        set_audit_sink(None)


# ============================================================
# F10: Outcome Metrics
# ============================================================

def test_f10_outcome_metrics_collection(sample_payload):
    """F10: 网关各请求场景正确累加内部指标计数器"""
    metrics_sink = MemoryMetricsSink()
    set_metrics_sink(metrics_sink)

    try:
        client = TestClient(app)
        # 1. 成功请求
        res_ok = client.post("/api/ai/companion", json=sample_payload)
        assert res_ok.status_code == 200
        assert metrics_sink.get_count(METRIC_REQUESTS_TOTAL) >= 1

        # 2. 超时请求
        fake_timeout = FakeLLMTransport(mode="timeout")
        set_provider(ExternalLLMProvider(api_key=TEST_SECRET, transport=fake_timeout))
        res_timeout = client.post("/api/ai/companion", json=sample_payload)
        assert res_timeout.status_code == 504
        assert metrics_sink.get_count(METRIC_TIMEOUT_TOTAL) >= 1
        assert metrics_sink.get_count(METRIC_FAILURES_TOTAL) >= 1

        # 3. 越权字段请求
        fake_policy = FakeLLMTransport(mode="forbidden_decision")
        set_provider(ExternalLLMProvider(api_key=TEST_SECRET, transport=fake_policy))
        res_policy = client.post("/api/ai/companion", json=sample_payload)
        assert res_policy.status_code == 502
        assert metrics_sink.get_count(METRIC_POLICY_VIOLATIONS_TOTAL) >= 1

        set_provider(None)
    finally:
        set_metrics_sink(None)
        set_provider(None)


# ============================================================
# F11: Audit Lifecycle
# ============================================================

def test_f11_audit_lifecycle_events(sample_payload):
    """F11: 正常请求产生完整的启动、完成时序事件"""
    mem_sink = MemoryAuditSink()
    set_audit_sink(mem_sink)

    try:
        client = TestClient(app)
        res = client.post("/api/ai/companion", json=sample_payload)
        assert res.status_code == 200

        event_names = [e.event_name for e in mem_sink.events]
        assert "REQUEST_STARTED" in event_names
        assert "PROVIDER_COMPLETED" in event_names
        assert "REQUEST_COMPLETED" in event_names
    finally:
        set_audit_sink(None)


# ============================================================
# F12: Deterministic Core Immutability
# ============================================================

def test_f12_deterministic_core_immutability(sample_payload):
    """F12: Invariant F12 — 所有审计与可观测性链路绝不篡改客观学情上下文"""
    context_dict = sample_payload["promptContext"]
    context_before = copy.deepcopy(context_dict)

    client = TestClient(app)
    res = client.post("/api/ai/companion", json=sample_payload)
    assert res.status_code == 200

    # 断言 payload 未被内存就地修改
    assert sample_payload["promptContext"] == context_before


# ============================================================
# F13: Observability Must Be Fail-Safe
# ============================================================

def test_f13_observability_failure_does_not_break_request(sample_payload):
    """F13: AuditSink 与 MetricsSink 同时抛出致命异常时，网关业务依然正常响应"""
    class CrashingSink(MemoryAuditSink, MemoryMetricsSink):
        def record(self, event):
            raise RuntimeError("CRITICAL AUDIT SINK FAILURE")
        def increment(self, metric_name, value=1, tags=None):
            raise RuntimeError("CRITICAL METRICS SINK FAILURE")

    bad_sink = CrashingSink()
    set_audit_sink(bad_sink)
    set_metrics_sink(bad_sink)

    try:
        client = TestClient(app)
        response = client.post("/api/ai/companion", json=sample_payload)
        # 业务绝不崩溃，依然返回 200 成功响应
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
    finally:
        set_audit_sink(None)
        set_metrics_sink(None)


# ============================================================
# F14: Sensitive Content Non-Observability
# ============================================================

def test_f14_sensitive_content_non_observability(sample_payload):
    """F14: 审计事件严格只记录元数据，Prompt 与学情上下文绝不进入审计事件"""
    mem_sink = MemoryAuditSink()
    set_audit_sink(mem_sink)

    try:
        client = TestClient(app)
        res = client.post("/api/ai/companion", json=sample_payload)
        assert res.status_code == 200

        for event in mem_sink.events:
            ev_dict = event.model_dump()
            assert "prompt" not in ev_dict
            assert "user_prompt" not in ev_dict
            assert "system_prompt" not in ev_dict
            assert "raw_response" not in ev_dict
            assert "user_question" not in ev_dict
            assert "learning_context" not in ev_dict
    finally:
        set_audit_sink(None)
