# -*- coding: utf-8 -*-
"""
gateway.api
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage F: Backend Secure AI Gateway 核心服务入口与生产加固可观测层

特性加固：
1. Request Correlation: 每个请求分配安全无害的 request_id (X-Request-ID Header 贯通)
2. Latency Observation: 毫秒级性能测量，仅作为元数据存在
3. Failure Taxonomy: 内部精细故障分类，面向学生文案彻底隔离
4. Fail-Safe Observability: 旁路审计与指标发生任何异常均被隔离，绝对不影响业务主流程
5. Security Redaction: 所有异常日志与追踪经过安全脱敏，严禁泄露密钥、内部路径与端点
"""

import logging
import time
from typing import Any, Dict
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gateway.adapter import (
    ProviderException,
    ProviderTimeoutError,
    execute_provider_with_timeout,
    get_provider,
)
from gateway.audit import (
    AuditEvent,
    ProviderFailureClass,
    generate_request_id,
    safe_increment_metric,
    safe_record_audit,
    METRIC_REQUESTS_TOTAL,
    METRIC_FAILURES_TOTAL,
    METRIC_FALLBACK_TOTAL,
    METRIC_TIMEOUT_TOTAL,
    METRIC_POLICY_VIOLATIONS_TOTAL,
)
from gateway.config import gateway_settings
from gateway.models import (
    AICompanionRequest,
    StructuredAIResponse,
)
from gateway.redaction import sanitize_exception_message

logger = logging.getLogger("xuehai.gateway")


def classify_provider_exception(exc: Exception) -> ProviderFailureClass:
    """内部故障分类映射函数"""
    msg = str(exc)
    if "forbidden decision field" in msg:
        return ProviderFailureClass.PROVIDER_POLICY_VIOLATION
    if "missing API key" in msg or "not configured" in msg:
        return ProviderFailureClass.PROVIDER_CONFIGURATION_ERROR
    if "client error (HTTP 4" in msg:
        return ProviderFailureClass.PROVIDER_BAD_RESPONSE
    if "server error (HTTP 5" in msg:
        return ProviderFailureClass.PROVIDER_UNAVAILABLE
    if "Connection refused" in msg or "connection" in msg.lower() or "network" in msg.lower():
        return ProviderFailureClass.NETWORK_FAILURE
    if "Invalid response" in msg or "missing required" in msg:
        return ProviderFailureClass.PROVIDER_BAD_RESPONSE
    return ProviderFailureClass.PROVIDER_UNAVAILABLE


def create_gateway_app() -> FastAPI:
    """构建独立 AI Gateway FastAPI 应用实例"""
    application = FastAPI(
        title="学海智导 AI Gateway",
        description="Secure AI Gateway Boundary for Xuehai Zhidao",
        version="0.2.0",
        docs_url=None,  # 关闭内部文档探测
        redoc_url=None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """请求格式/白名单校验失败处理器，杜绝敏感堆栈泄露"""
        req_id = generate_request_id()
        safe_increment_metric(METRIC_FAILURES_TOTAL)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": "SCHEMA_VALIDATION_FAILED",
                "detail": "请求载荷不符合网关安全白名单契约，已拒绝处理。",
                "errors": [
                    {"loc": [str(x) for x in err.get("loc", [])], "msg": err.get("msg", "")}
                    for err in exc.errors()
                ],
            },
            headers={"X-Request-ID": req_id},
        )

    @application.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """全局异常熔断：捕获所有未知异常，杜绝 Python Traceback 泄露给客户端"""
        req_id = generate_request_id()
        clean_name = sanitize_exception_message(exc.__class__.__name__)
        logger.error(f"Gateway internal exception [{req_id}]: {clean_name}")
        safe_increment_metric(METRIC_FAILURES_TOTAL)

        # 记录内部未捕获严重异常事件
        safe_record_audit(
            AuditEvent(
                event_name="GATEWAY_CRASHED",
                request_id=req_id,
                provider="unknown",
                model=gateway_settings.model,
                status="FAILED",
                failure_class=ProviderFailureClass.GATEWAY_INTERNAL_ERROR.value,
                fallback_used=True,
            )
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "GATEWAY_INTERNAL_ERROR",
                "detail": "网关服务异常，已触发安全降级熔断。",
                "grounding_status": "insufficient_context",
                "answer": "抱歉，伴学网关暂时出现内部异常，请稍后重试。",
            },
            headers={"X-Request-ID": req_id},
        )

    @application.get("/api/ai/health")
    def health_check() -> Dict[str, Any]:
        """网关健康检查探针"""
        return {
            "status": "healthy",
            "provider": gateway_settings.provider,
            "masked_key": gateway_settings.get_masked_api_key(),
            "timeout_ms": gateway_settings.timeout_ms,
        }

    @application.post(
        "/api/ai/companion",
        response_model=StructuredAIResponse,
        response_model_exclude_unset=True,
    )
    async def companion_endpoint(
        request: AICompanionRequest,
        response: Response,
    ) -> StructuredAIResponse:
        """
        AI 伴学主入口端点
        
        加固执行边界：
        1. Request Correlation: 注入 X-Request-ID Header 保证链路追踪
        2. Latency & Observability: 旁路收集耗时与状态事件，Fail-safe 熔断保护
        3. Request Validation: Pydantic 严格白名单校验 (extra='forbid')
        4. Provider Selection & Invocation: 委托给 AIProviderAdapter 抽象层
        5. Response Normalization: 仅返回 StructuredAIResponse 契约字段
        6. Secret & Authority Isolation: 密钥绝不暴露，决策权绝对隔离
        """
        request_id = generate_request_id()
        response.headers["X-Request-ID"] = request_id
        start_perf = time.perf_counter()

        prompt_context = request.prompt_context
        if request.question and request.question != prompt_context.user_question:
            prompt_context = prompt_context.model_copy(update={"user_question": request.question})

        provider = get_provider()

        # 1. 记录请求启动审计事件与指标递增
        safe_record_audit(
            AuditEvent(
                event_name="REQUEST_STARTED",
                request_id=request_id,
                provider=provider.provider_name,
                model=gateway_settings.model,
                status="STARTED",
            )
        )
        safe_increment_metric(METRIC_REQUESTS_TOTAL)

        # 2. 执行模型生成
        try:
            result = await execute_provider_with_timeout(
                provider,
                prompt_context,
                timeout_ms=gateway_settings.timeout_ms,
            )
            latency_ms = round((time.perf_counter() - start_perf) * 1000, 2)

            # 3. 正常完成审计事件记录
            safe_record_audit(
                AuditEvent(
                    event_name="PROVIDER_COMPLETED",
                    request_id=request_id,
                    provider=provider.provider_name,
                    model=gateway_settings.model,
                    status="SUCCESS",
                )
            )
            safe_record_audit(
                AuditEvent(
                    event_name="REQUEST_COMPLETED",
                    request_id=request_id,
                    provider=provider.provider_name,
                    model=gateway_settings.model,
                    status="SUCCESS",
                    latency_ms=latency_ms,
                )
            )
            return result

        except ProviderTimeoutError as e:
            latency_ms = round((time.perf_counter() - start_perf) * 1000, 2)
            clean_err = sanitize_exception_message(e)
            logger.warning(f"Gateway timeout [{request_id}]: {clean_err}")

            failure_class = ProviderFailureClass.PROVIDER_TIMEOUT.value
            safe_record_audit(
                AuditEvent(
                    event_name="PROVIDER_FAILED",
                    request_id=request_id,
                    provider=provider.provider_name,
                    model=gateway_settings.model,
                    status="FAILED",
                    failure_class=failure_class,
                    latency_ms=latency_ms,
                )
            )
            safe_record_audit(
                AuditEvent(
                    event_name="FALLBACK_ACTIVATED",
                    request_id=request_id,
                    provider=provider.provider_name,
                    model=gateway_settings.model,
                    status="FALLBACK",
                    failure_class=failure_class,
                    fallback_used=True,
                )
            )
            safe_increment_metric(METRIC_TIMEOUT_TOTAL)
            safe_increment_metric(METRIC_FAILURES_TOTAL)
            safe_increment_metric(METRIC_FALLBACK_TOTAL)

            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "GATEWAY_TIMEOUT",
                    "detail": "AI 伴学服务响应超时，请稍后重试。",
                    "grounding_status": "insufficient_context",
                    "answer": "抱歉，伴学服务响应超时，请稍后重试。",
                },
                headers={"X-Request-ID": request_id},
            )

        except ProviderException as e:
            latency_ms = round((time.perf_counter() - start_perf) * 1000, 2)
            clean_err = sanitize_exception_message(e)
            logger.error(f"Gateway provider error [{request_id}]: {clean_err}")

            fail_enum = classify_provider_exception(e)
            failure_class = fail_enum.value
            if fail_enum == ProviderFailureClass.PROVIDER_POLICY_VIOLATION:
                safe_increment_metric(METRIC_POLICY_VIOLATIONS_TOTAL)

            safe_record_audit(
                AuditEvent(
                    event_name="PROVIDER_FAILED",
                    request_id=request_id,
                    provider=provider.provider_name,
                    model=gateway_settings.model,
                    status="FAILED",
                    failure_class=failure_class,
                    latency_ms=latency_ms,
                )
            )
            safe_record_audit(
                AuditEvent(
                    event_name="FALLBACK_ACTIVATED",
                    request_id=request_id,
                    provider=provider.provider_name,
                    model=gateway_settings.model,
                    status="FALLBACK",
                    failure_class=failure_class,
                    fallback_used=True,
                )
            )
            safe_increment_metric(METRIC_FAILURES_TOTAL)
            safe_increment_metric(METRIC_FALLBACK_TOTAL)

            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={
                    "error": "BAD_GATEWAY",
                    "detail": "AI 服务商暂时不可用，已安全拦截。",
                    "grounding_status": "insufficient_context",
                    "answer": "抱歉，伴学服务商暂时不可用，请稍后重试。",
                },
                headers={"X-Request-ID": request_id},
            )

    return application


app = create_gateway_app()
