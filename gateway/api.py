# -*- coding: utf-8 -*-
"""
gateway.api
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Backend Secure AI Gateway 核心服务入口
"""

import logging
from typing import Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gateway.config import gateway_settings
from gateway.models import (
    AICompanionRequest,
    StructuredAIResponse,
)

logger = logging.getLogger("xuehai.gateway")


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
        )

    @application.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """全局异常熔断：捕获所有未知异常，杜绝 Python Traceback 泄露给客户端"""
        logger.error(f"Gateway internal exception: {exc.__class__.__name__}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "GATEWAY_INTERNAL_ERROR",
                "detail": "网关服务异常，已触发安全降级熔断。",
                "grounding_status": "insufficient_context",
                "answer": "抱歉，伴学网关暂时出现内部异常，请稍后重试。",
            },
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
    def companion_endpoint(
        request: AICompanionRequest,
    ) -> StructuredAIResponse:
        """
        AI 伴学主入口端点
        
        执行边界：
        1. Request Validation: Pydantic 严格白名单校验 (extra='forbid')
        2. Provider Selection & Invocation: 确定性 Mock Gateway Provider
        3. Response Normalization: 仅返回 StructuredAIResponse 契约字段
        4. Secret Isolation: 杜绝任何密钥外泄
        5. Decision Authority Isolation: 严禁引入任何学习决策字段
        """
        prompt_context = request.prompt_context
        sf = prompt_context.system_facts
        question = request.question or prompt_context.user_question

        # 确定性 Mock Gateway Provider 生成逻辑 (纯确定性，无随机数，无系统修改)
        referenced_facts = [
            f"current_knowledge_point={sf.current_knowledge_id}:{sf.current_knowledge_name}",
            f"current_mastery_percent={sf.current_mastery_percent:.1f}%",
            f"mastery_target_percent={sf.mastery_target_percent:.1f}%",
            f"path_state={sf.current_path_state}",
            f"next_action={sf.next_action.label}",
        ]

        answer = (
            f"同学你好！你当前正在学习【{sf.current_chapter}】中的【{sf.current_knowledge_name}】"
            f"（编号 {sf.current_knowledge_id}）。当前掌握度为 {sf.current_mastery_percent:.1f}%，"
            f"距离达标目标 {sf.mastery_target_percent:.1f}% 还差 {sf.mastery_gap_percent:.1f}%。"
            f"当前路径状态为 {sf.current_path_state}。"
            f"针对你的提问「{question}」，根据系统诊断事实，建议你下一步：{sf.next_action.label}"
            f"（{sf.next_action.reason}）。继续加油！"
        )

        suggested_explanation = (
            f"知识点 {sf.current_knowledge_id} 当前路径状态为 {sf.current_path_state}，"
            f"建议行动为 {sf.next_action.label}。"
        )

        return StructuredAIResponse(
            answer=answer,
            referenced_facts=referenced_facts,
            suggested_explanation=suggested_explanation,
            grounding_status="grounded",
        )

    return application


app = create_gateway_app()
