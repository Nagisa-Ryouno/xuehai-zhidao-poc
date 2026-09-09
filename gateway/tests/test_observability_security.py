# -*- coding: utf-8 -*-
"""
gateway.tests.test_observability_security
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage F: 可观测性与审计安全红线断言测试 (F-SEC-01 ~ F-SEC-10)

核心安全断言：
F-SEC-01: Audit Event 绝不包含 API Key
F-SEC-02: Audit Event 绝不包含 Authorization Header
F-SEC-03: Audit Event 绝不包含 Prompt 全文
F-SEC-04: Audit Event 绝不包含 Raw Response 全文
F-SEC-05: Exception 净化绝不泄露 Secret 凭据
F-SEC-06: Exception 净化绝不泄露本地源码路径
F-SEC-07: Exception 净化绝不泄露 Provider 内部主机端点
F-SEC-08: 嵌套 Dict / List 结构无法绕过脱敏层
F-SEC-09: Audit Sink 内部故障完全旁路隔离 (Fail-Safe: 不击穿业务请求)
F-SEC-10: Metrics Sink 内部故障完全旁路隔离 (Fail-Safe: 不击穿业务请求)
"""

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from gateway.audit import (
    AuditEvent,
    MemoryAuditSink,
    MemoryMetricsSink,
    safe_record_audit,
    safe_increment_metric,
    set_audit_sink,
    set_metrics_sink,
)
from gateway.redaction import (
    redact_sensitive_string,
    sanitize_audit_payload,
    sanitize_exception_message,
)
from gateway.api import app

TEST_SECRET = "TEST_SECRET_DO_NOT_USE_998877"


@pytest.fixture
def sample_payload() -> dict:
    return {
        "promptContext": {
            "user_question": "需求价格弹性做错了怎么提升？",
            "system_facts": {
                "student_id": "S001",
                "student_name": "张小凡",
                "major": "经济学",
                "grade": "大二",
                "learning_goal": "掌握弹性",
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
            "grounding_rules": ["仅依据事实回答"],
        },
        "question": "需求价格弹性做错了怎么提升？",
    }


def test_f_sec_01_audit_event_contains_no_api_key():
    """F-SEC-01: AuditEvent 契约模型拒绝任何形式的 api_key 字段传入"""
    with pytest.raises(ValidationError):
        AuditEvent(
            event_name="REQUEST_COMPLETED",
            request_id="req_12345",
            provider="mock",
            model="test-model",
            status="SUCCESS",
            api_key=TEST_SECRET,  # 违规注入
        )


def test_f_sec_02_audit_event_contains_no_authorization_header():
    """F-SEC-02: AuditEvent 契约模型拒绝任何 authorization / headers 字段传入"""
    with pytest.raises(ValidationError):
        AuditEvent(
            event_name="REQUEST_COMPLETED",
            request_id="req_12345",
            provider="mock",
            model="test-model",
            status="SUCCESS",
            authorization=f"Bearer {TEST_SECRET}",  # 违规注入
        )


def test_f_sec_03_audit_event_contains_no_prompt():
    """F-SEC-03: AuditEvent 契约模型拒绝 prompt / system_prompt / user_prompt 注入"""
    with pytest.raises(ValidationError):
        AuditEvent(
            event_name="REQUEST_STARTED",
            request_id="req_12345",
            provider="mock",
            model="test-model",
            status="STARTED",
            prompt="You are Xuehai AI...",  # 违规注入
        )


def test_f_sec_04_audit_event_contains_no_raw_response():
    """F-SEC-04: AuditEvent 契约模型拒绝 raw_response / answer 注入"""
    with pytest.raises(ValidationError):
        AuditEvent(
            event_name="REQUEST_COMPLETED",
            request_id="req_12345",
            provider="mock",
            model="test-model",
            status="SUCCESS",
            raw_response={"answer": "全文内容"},  # 违规注入
        )


def test_f_sec_05_exception_sanitization_erases_secrets():
    """F-SEC-05: 异常消息净化严格擦除各类 Secret / Token 凭据"""
    dirty_exception = RuntimeError(
        f"Authorization failed with Bearer {TEST_SECRET} and token sk-proj-1234567890abcdef"
    )
    clean_msg = sanitize_exception_message(dirty_exception)

    assert TEST_SECRET not in clean_msg
    assert "sk-proj-1234567890abcdef" not in clean_msg
    assert "[REDACTED_SECRET]" in clean_msg


def test_f_sec_06_exception_sanitization_erases_source_paths():
    """F-SEC-06: 异常消息净化严格擦除服务端源码文件绝对路径与堆栈"""
    win_err = "Crash at C:\\project\\gateway\\adapter.py, line 175: Null Pointer"
    clean_win = sanitize_exception_message(win_err)
    assert "C:\\project\\gateway\\adapter.py" not in clean_win
    assert "[REDACTED_PATH]" in clean_win

    unix_err = "Crash at /var/www/xuehai/gateway/api.py line 42: Connection refused"
    clean_unix = sanitize_exception_message(unix_err)
    assert "/var/www/xuehai/gateway/api.py" not in clean_unix
    assert "[REDACTED_PATH]" in clean_unix


def test_f_sec_07_exception_sanitization_erases_internal_endpoints():
    """F-SEC-07: 异常消息净化严格擦除 Provider 内部主机端点与完整 URL"""
    url_err = "Connection reset by peer at https://api.deepseek.com:443/v1/chat/completions"
    clean_url = sanitize_exception_message(url_err)
    assert "api.deepseek.com" not in clean_url
    assert "https://" not in clean_url
    assert "[REDACTED_ENDPOINT]" in clean_url


def test_f_sec_08_nested_payload_cannot_bypass_redaction():
    """F-SEC-08: 嵌套 Dict / List 结构无法绕过安全脱敏层"""
    nested_dirty_payload = {
        "metadata": {
            "request_id": "req_001",
            "nested_secrets": {
                "api_key": TEST_SECRET,
                "prompt": "Sensitive prompt content",
                "inner_list": [
                    {"authorization": "Bearer secret-token"},
                    "Safe normal text",
                ],
            },
        },
        "safe_key": "safe_value",
    }

    cleaned = sanitize_audit_payload(nested_dirty_payload)

    # 验证敏感键被彻底剔除
    inner_dict = cleaned["metadata"]["nested_secrets"]
    assert "api_key" not in inner_dict
    assert "prompt" not in inner_dict
    assert "authorization" not in inner_dict["inner_list"][0]
    assert cleaned["safe_key"] == "safe_value"


def test_f_sec_09_audit_sink_failure_is_fail_safe():
    """F-SEC-09: Audit Sink 发生未知内部异常或崩溃时，网关业务流程完全不受影响"""
    class CrashingAuditSink:
        def record(self, event: AuditEvent) -> None:
            raise RuntimeError("CRITICAL DATABASE SINK CRASH")

    # 1. 验证 safe_record_audit 内部完全吸收异常
    dummy_event = AuditEvent(
        event_name="REQUEST_STARTED",
        request_id="req_999",
        provider="mock",
        model="test",
        status="STARTED",
    )
    # 调用绝不抛出 RuntimeError
    safe_record_audit(dummy_event, sink=CrashingAuditSink())


def test_f_sec_10_metrics_sink_failure_is_fail_safe():
    """F-SEC-10: Metrics Sink 发生异常时，网关业务流程完全不受影响"""
    class CrashingMetricsSink:
        def increment(self, metric_name: str, value: int = 1, tags=None) -> None:
            raise ConnectionError("METRICS COLLECTOR CONNECTION DEAD")

    # 调用绝不抛出 ConnectionError
    safe_increment_metric("gateway_requests_total", sink=CrashingMetricsSink())
