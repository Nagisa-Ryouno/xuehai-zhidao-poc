# -*- coding: utf-8 -*-
"""
gateway.evaluation.judge.adapter
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 / Checkpoint 2: JudgeAdapter 生产级加固、有界重试、异常分类与熔断隔离

核心原则：
1. 故障绝对隔离：LLM Judge 作为可插拔观察器，其执行异常、超时、限流或熔断绝不可中断主学习链路
2. 熔断器 (Circuit Breaker)：连续失败达到阈值进入 OPEN 状态，阻断网络调用保护上游
3. 区分性有界重试：严格区分瞬时可重试故障 (429/5xx/Timeout) 与不可重试故障 (401/403/400/SchemaError)
4. 耗时度量与安全审计：使用 monotonic clock 度量延迟，安全发送审计事件，绝不泄露 API Key 与 PII
5. 依赖注入友好：支持注入 sleep_fn 与 audit_sink，确保离线测试 100% 快速、无等待
"""

import asyncio
from enum import Enum
import logging
import time
from typing import Callable, Optional, Tuple
import uuid

from gateway.audit import AuditEvent, AuditSink, NullAuditSink
from gateway.evaluation.judge.fake import FakeLLMJudge
from gateway.evaluation.judge.interface import LLMJudge
from gateway.evaluation.judge.models import JudgeFailureClass, JudgeResult
from gateway.models import LearningPromptContext, StructuredAIResponse

logger = logging.getLogger("xuehai.gateway.evaluation.judge")


class CircuitState(str, Enum):
    """熔断器状态枚举"""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    通用熔断器状态机
    """

    def __init__(self, failure_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.state = CircuitState.CLOSED
        self.failure_count = 0

    def record_success(self) -> None:
        """成功调用重置失败计数与熔断状态"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """记录一次最终业务请求失败，达到阈值触发 OPEN 熔断"""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def allow_request(self) -> bool:
        """判断是否允许放行网络请求"""
        return self.state != CircuitState.OPEN

    def reset(self) -> None:
        """手动重置熔断器状态为 CLOSED"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED


class JudgeAdapter:
    """
    通用 Judge 生产级适配容器
    """

    def __init__(
        self,
        judge: Optional[LLMJudge] = None,
        max_retries: int = 2,
        circuit_breaker: Optional[CircuitBreaker] = None,
        audit_sink: Optional[AuditSink] = None,
        sleep_fn: Optional[Callable[[float], None]] = None,
    ):
        self.judge = judge if judge is not None else FakeLLMJudge()
        self.max_retries = max_retries
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.audit_sink = audit_sink or NullAuditSink()
        self._sleep_fn = sleep_fn if sleep_fn is not None else time.sleep
        self.last_latency_ms: Optional[float] = None

    def _is_retriable_error(self, exc: Exception) -> bool:
        """
        判断异常是否属于可重试的瞬时网络或服务端故障
        """
        # 1. 超时异常属于典型可重试故障
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
            return True
        from gateway.adapter import ProviderTimeoutError, ProviderException
        if isinstance(exc, ProviderTimeoutError):
            return True

        # 2. ProviderException 需分析内部状态码或语义
        if isinstance(exc, ProviderException):
            msg = str(exc).lower()
            # 明确不可重试的客户端/鉴权/参数错误（401/403/400/422）
            if any(term in msg for term in ["401", "403", "400", "422", "authentication failed", "client request error", "unauthorized"]):
                return False
            # 明确可重试的频控或服务端错误（429/500/502/503）
            if any(term in msg for term in ["429", "500", "502", "503", "rate limit", "server error"]):
                return True

        # 3. 底层网络连接错误可重试
        if isinstance(exc, ConnectionError):
            return True

        # 4. 数据解析/值越界属于不可重试的坏响应
        if isinstance(exc, (ValueError, TypeError)):
            return False

        return False

    def _map_exception_to_failure(self, exc: Exception) -> JudgeFailureClass:
        """
        将捕获的底层异常精细映射为规范的 JudgeFailureClass
        """
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
            return JudgeFailureClass.JUDGE_TIMEOUT
        from gateway.adapter import ProviderTimeoutError, ProviderException
        if isinstance(exc, ProviderTimeoutError):
            return JudgeFailureClass.JUDGE_TIMEOUT

        if isinstance(exc, (ValueError, TypeError)):
            return JudgeFailureClass.JUDGE_BAD_RESPONSE

        if isinstance(exc, ConnectionError):
            return JudgeFailureClass.JUDGE_UNAVAILABLE

        if isinstance(exc, ProviderException):
            msg = str(exc).lower()
            if any(term in msg for term in ["400", "422", "client request error", "malformed"]):
                return JudgeFailureClass.JUDGE_BAD_RESPONSE
            if any(term in msg for term in ["401", "403", "429", "500", "502", "503", "authentication failed", "rate limit", "server error"]):
                return JudgeFailureClass.JUDGE_UNAVAILABLE

        return JudgeFailureClass.JUDGE_INTERNAL_ERROR

    def _emit_audit_event(
        self,
        status: str,
        failure_class: JudgeFailureClass,
        latency_ms: float,
        overall_score: Optional[float] = None,
    ) -> None:
        """安全发出审计事件，杜绝泄露敏感凭证与 PII"""
        try:
            model_name = getattr(self.judge, "model", getattr(self.judge, "_name", "unknown"))
            caps_method = getattr(self.judge, "capabilities", None)
            provider_name = caps_method().provider_name if callable(caps_method) else "unknown"

            event = AuditEvent(
                event_name="ai_gateway.judge_evaluation",
                request_id=f"judge-{uuid.uuid4().hex[:8]}",
                provider=provider_name,
                model=model_name,
                status=status,
                failure_class=failure_class.value if failure_class != JudgeFailureClass.NONE else None,
                latency_ms=round(latency_ms, 2),
                fallback_used=(status != "SUCCESS"),
                validator_result=f"score={overall_score:.2f}" if overall_score is not None else None,
            )
            self.audit_sink.record(event)
        except Exception as audit_err:
            logger.debug(f"Audit sink failed safely: {audit_err}")

    def evaluate_safe(
        self,
        context: LearningPromptContext,
        response: StructuredAIResponse,
    ) -> Tuple[Optional[JudgeResult], JudgeFailureClass]:
        """
        在安全容错、熔断保护与有界重试机制下调用底层 Judge
        """
        # 1. 熔断器拦截
        if not self.circuit_breaker.allow_request():
            logger.warning("Judge circuit breaker is OPEN, blocking request")
            self.last_latency_ms = 0.0
            return None, JudgeFailureClass.JUDGE_UNAVAILABLE

        # 2. 计时器启动 (monotonic clock)
        start_time = time.perf_counter()
        max_attempts = self.max_retries + 1
        attempt = 0
        last_exception: Optional[Exception] = None

        while attempt < max_attempts:
            attempt += 1
            try:
                result = self.judge.evaluate(context, response)

                # 校验结构合法性
                if not isinstance(result, JudgeResult):
                    logger.warning("Judge returned non-JudgeResult instance")
                    raise ValueError("Judge returned non-JudgeResult instance")

                if not (0.0 <= result.overall_score <= 1.0) or not (0.0 <= result.confidence <= 1.0):
                    logger.warning("Judge scores out of valid [0.0, 1.0] range")
                    raise ValueError("Judge scores out of valid [0.0, 1.0] range")

                # 成功：记录熔断器成功并统计耗时
                self.circuit_breaker.record_success()
                latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                self.last_latency_ms = latency_ms

                # 发送结构化审计事件
                self._emit_audit_event(
                    status="SUCCESS",
                    failure_class=JudgeFailureClass.NONE,
                    latency_ms=latency_ms,
                    overall_score=result.overall_score,
                )

                return result, JudgeFailureClass.NONE

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Judge evaluation attempt {attempt}/{max_attempts} failed: "
                    f"{type(e).__name__}: {str(e)}"
                )

                is_retriable = self._is_retriable_error(e)
                if not is_retriable or attempt >= max_attempts:
                    break

                # 有界指数退避等待
                backoff = 0.05 * (2 ** (attempt - 1))
                if self._sleep_fn:
                    self._sleep_fn(backoff)

        # 业务请求彻底失败：熔断器失败计数递增 1 次
        self.circuit_breaker.record_failure()
        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        self.last_latency_ms = latency_ms

        failure_class = (
            self._map_exception_to_failure(last_exception)
            if last_exception
            else JudgeFailureClass.JUDGE_UNKNOWN_ERROR
        )

        # 发送结构化失败审计事件
        self._emit_audit_event(
            status="FAILED",
            failure_class=failure_class,
            latency_ms=latency_ms,
        )

        return None, failure_class
