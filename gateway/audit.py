# -*- coding: utf-8 -*-
"""
gateway.audit
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage F: 结构化审计事件契约、故障分类矩阵与安全可观测性接口 (Audit & Observability)

设计原则：
1. 白名单事件契约 (Allowlist Schema)：仅允许记录安全元数据，通过 extra='forbid' 拦截敏感内容
2. 内部故障分类 (Failure Taxonomy)：精细分类（超时、不可用、越权注入等），与面向学生的文案彻底分离
3. 旁路熔断安全 (Fail-Safe Observability)：审计与指标收集发生任何异常均被隔离，绝不破坏业务流
4. 纯净依赖：仅依赖标准库与 Pydantic，不引入外部重型遥测 SDK
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("xuehai.gateway.audit")


class ProviderFailureClass(str, Enum):
    """网关与外部服务商故障分类矩阵（仅供内部诊断，与用户界面文案分离）"""
    NONE = "NONE"
    PROVIDER_CONFIGURATION_ERROR = "PROVIDER_CONFIGURATION_ERROR"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_BAD_RESPONSE = "PROVIDER_BAD_RESPONSE"
    PROVIDER_POLICY_VIOLATION = "PROVIDER_POLICY_VIOLATION"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    FACT_VALIDATION_FAILURE = "FACT_VALIDATION_FAILURE"
    GATEWAY_INTERNAL_ERROR = "GATEWAY_INTERNAL_ERROR"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class AuditEvent(BaseModel):
    """
    网关结构化审计事件模型 (严格白名单，禁止未授权私有/敏感字段注入)
    
    允许字段：
    - event_name, request_id, provider, model, status, failure_class,
      latency_ms, fallback_used, validator_result, timestamp
    
    严禁包含：
    - api_key, authorization, prompt, user_question, raw_response, answer, learning_context, stacktrace
    """
    model_config = ConfigDict(extra="forbid")

    event_name: str
    request_id: str
    provider: str
    model: str
    status: str  # "SUCCESS", "FAILED", "FALLBACK"
    failure_class: Optional[str] = None
    latency_ms: Optional[float] = None
    fallback_used: bool = False
    validator_result: Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )


# ============================================================
# Audit Sink 抽象与实现
# ============================================================

class AuditSink(ABC):
    """审计事件汇聚层抽象基类"""

    @abstractmethod
    def record(self, event: AuditEvent) -> None:
        """记录一条审计事件"""
        pass


class NullAuditSink(AuditSink):
    """默认安全静默实现，不产生任何副作用与开销"""

    def record(self, event: AuditEvent) -> None:
        pass


class MemoryAuditSink(AuditSink):
    """内存审计收集器，用于离线单元测试与契约断言"""

    def __init__(self):
        self.events: List[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)

    def clear(self) -> None:
        self.events.clear()


_active_audit_sink: Optional[AuditSink] = None


def get_audit_sink() -> AuditSink:
    """获取当前激活的 AuditSink"""
    global _active_audit_sink
    if _active_audit_sink is None:
        _active_audit_sink = NullAuditSink()
    return _active_audit_sink


def set_audit_sink(sink: Optional[AuditSink]) -> None:
    """设置或覆盖当前 AuditSink (用于测试与依赖注入)"""
    global _active_audit_sink
    _active_audit_sink = sink


def safe_record_audit(event: AuditEvent, sink: Optional[AuditSink] = None) -> None:
    """
    Fail-Safe 审计事件安全分发函数
    
    红线保证：
    若 Sink.record 发生任何未知崩溃或连接异常，安全捕获并吸收，绝不向外冒泡影响业务。
    """
    target_sink = sink or get_audit_sink()
    try:
        target_sink.record(event)
    except Exception as exc:
        logger.warning(
            f"AuditSink failure suppressed (fail-safe): {exc.__class__.__name__}"
        )


# ============================================================
# Internal Metrics Sink 抽象与实现
# ============================================================

METRIC_REQUESTS_TOTAL = "gateway_requests_total"
METRIC_FAILURES_TOTAL = "gateway_failures_total"
METRIC_FALLBACK_TOTAL = "gateway_fallback_total"
METRIC_FACT_VALIDATION_FAILURES_TOTAL = "gateway_fact_validation_failures_total"
METRIC_POLICY_VIOLATIONS_TOTAL = "gateway_policy_violations_total"
METRIC_TIMEOUT_TOTAL = "gateway_timeout_total"


class MetricsSink(ABC):
    """内部指标收集层抽象基类"""

    @abstractmethod
    def increment(
        self,
        metric_name: str,
        value: int = 1,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """递增指标计数器"""
        pass


class NullMetricsSink(MetricsSink):
    """默认安全静默指标实现"""

    def increment(
        self,
        metric_name: str,
        value: int = 1,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        pass


class MemoryMetricsSink(MetricsSink):
    """内存指标收集器，用于离线单元测试与计数断言"""

    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)

    def increment(
        self,
        metric_name: str,
        value: int = 1,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        self.counters[metric_name] += value

    def get_count(self, metric_name: str) -> int:
        return self.counters.get(metric_name, 0)

    def clear(self) -> None:
        self.counters.clear()


_active_metrics_sink: Optional[MetricsSink] = None


def get_metrics_sink() -> MetricsSink:
    """获取当前激活的 MetricsSink"""
    global _active_metrics_sink
    if _active_metrics_sink is None:
        _active_metrics_sink = NullMetricsSink()
    return _active_metrics_sink


def set_metrics_sink(sink: Optional[MetricsSink]) -> None:
    """设置或覆盖当前 MetricsSink"""
    global _active_metrics_sink
    _active_metrics_sink = sink


def safe_increment_metric(
    metric_name: str,
    value: int = 1,
    tags: Optional[Dict[str, str]] = None,
    sink: Optional[MetricsSink] = None,
) -> None:
    """
    Fail-Safe 指标递增安全函数
    
    红线保证：
    若 Metrics.increment 发生任何异常，安全捕获并吸收，绝不向外冒泡影响业务。
    """
    target_sink = sink or get_metrics_sink()
    try:
        target_sink.increment(metric_name, value=value, tags=tags)
    except Exception as exc:
        logger.warning(
            f"MetricsSink failure suppressed (fail-safe): {exc.__class__.__name__}"
        )


# ============================================================
# Request Correlation ID
# ============================================================

def generate_request_id() -> str:
    """
    生成网关请求唯一关联标识 (Correlation ID)
    
    安全要求：
    - 不包含 user_id、email、phone、API key、prompt、问题文本等敏感信息
    - 格式固定为 req_<12位无害随机十六进制>
    """
    return f"req_{uuid.uuid4().hex[:12]}"
