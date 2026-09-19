# -*- coding: utf-8 -*-
"""
gateway.ai.recommendation.service
=================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B / Phase 2
推荐服务编排层 (Recommendation Service Orchestrator)

设计规范与架构红线：
1. 绝对只读架构：严禁引入任何写持久化操作、严禁调用 BKT/Path/Events 写 API；
2. 完整流水线编排：
   Context 快照构建 -> Prompt 生成 -> Provider 异步调用 -> JSON 解析 -> 确定性三层校验 -> 组装返回；
3. 离线 Mock 与生产路由解耦：
   - 默认环境 (DEEPSEEK_ENABLED=false) 安全路由至 MockDeepSeekProvider；
   - 线上联调环境通过配置化启用真实 DeepSeekProvider；
4. 绝不伪造降级：校验失败时坚决抛出异常阻断，严禁降级返回未经校验的原始 AI 响应。
"""

import logging
from typing import Any, Dict, List, Optional

from gateway.adapter import AIProviderAdapter, get_provider
from gateway.ai.deepseek import DeepSeekProvider, MockDeepSeekProvider
from gateway.ai.models import AIProviderRequest
from gateway.config import gateway_settings
from gateway.ai.recommendation.context import RecommendationContextBuilder
from gateway.ai.recommendation.models import (
    RecommendationCandidate,
    RecommendationContext,
    RecommendationRequest,
    RecommendationResponse,
    ValidatedRecommendation,
)
from gateway.ai.recommendation.prompt import build_recommendation_prompt
from gateway.ai.recommendation.validator import (
    RecommendationValidator,
    ValidationRejectedError,
)

logger = logging.getLogger("xuehai.ai.recommendation")


class RecommendationService:
    """推荐服务编排器 (只读、安全、确定性)"""

    def __init__(
        self,
        provider: Optional[AIProviderAdapter] = None,
        validator: Optional[Any] = None,
        context_builder: Optional[Any] = None,
    ):
        self._provider = provider
        self._validator = validator or RecommendationValidator
        self._context_builder = context_builder or RecommendationContextBuilder

    def _resolve_provider(self, override_provider: Optional[AIProviderAdapter] = None) -> AIProviderAdapter:
        """解析获取适用的 AI Provider 实例"""
        if override_provider is not None:
            return override_provider
        if self._provider is not None:
            return self._provider

        # 若处于离线模式或未开启真实 DeepSeek，默认路由至确定性 Mock Provider
        if not gateway_settings.deepseek_enabled:
            return MockDeepSeekProvider(model=gateway_settings.deepseek_model)

        # 线上启用模式
        return get_provider("deepseek")

    async def get_recommendations(
        self,
        student_id: str,
        request: Optional[RecommendationRequest] = None,
        provider_override: Optional[AIProviderAdapter] = None,
    ) -> RecommendationResponse:
        """
        根据学生当前权威学习状态，生成并校验个性化学习资源推荐。
        """
        req = request or RecommendationRequest()
        focus_override = req.knowledge_id
        max_recs = req.max_recommendations

        # 1. 构建权威不可变只读上下文快照
        context: RecommendationContext = self._context_builder.build_context(
            student_id=student_id,
            focus_override=focus_override,
        )

        # 2. 构建提示词对 (system_prompt, user_prompt)
        sys_prompt, usr_prompt = build_recommendation_prompt(context)

        # 3. 准备候选池元数据（供离线确定性 Mock Provider 使用，严格避免文本字符串猜词）
        candidate_pool = [
            {"knowledge_id": r.knowledge_id, "resource_id": r.resource_id}
            for r in context.resources
        ]

        # 4. 组装标准统一 AI 请求契约
        ai_req = AIProviderRequest(
            system_prompt=sys_prompt,
            user_prompt=usr_prompt,
            response_format="json_object",
            max_tokens=1024,
            temperature=0.0,
            user_id=context.student_id,
            task="recommendation",  # 显式任务契约声明
            metadata={
                "task": "recommendation",
                "candidate_pool": candidate_pool,
            },
        )

        # 5. 调用 Provider 获取模型响应
        provider = self._resolve_provider(provider_override)
        ai_resp = await provider.complete(ai_req)

        # 6. 提取原始响应输出 (优先 parsed_json，次之 content)
        raw_payload = ai_resp.parsed_json if ai_resp.parsed_json is not None else ai_resp.content

        # 7. 执行确定性三层校验与权威元数据补全
        validated_list: List[ValidatedRecommendation] = self._validator.validate(
            raw_output=raw_payload,
            context=context,
            max_allowed=max_recs,
        )

        # 8. 组装标准响应契约并返回
        return RecommendationResponse(
            student_id=context.student_id,
            recommendations=validated_list,
            source=provider.provider_name,
            validated=True,
        )


# 全局单例
default_recommendation_service = RecommendationService()
