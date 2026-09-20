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
from typing import Any, Dict, List, Optional, Tuple

from gateway.adapter import AIProviderAdapter, get_provider
from gateway.ai.deepseek import DeepSeekProvider, MockDeepSeekProvider
from gateway.ai.models import AIProviderRequest
from gateway.config import gateway_settings
from gateway.ai.recommendation.context import RecommendationContextBuilder
from gateway.ai.recommendation.generator import DeepSeekCandidateGenerator
from gateway.ai.recommendation.models import (
    CandidateValidationResult,
    RecommendationCandidate,
    RecommendationContext,
    RecommendationRequest,
    RecommendationResponse,
    RejectedCandidate,
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
        generator: Optional[Any] = None,
        raise_on_rejection: bool = True,
    ):
        self._provider = provider
        self._validator = validator or RecommendationValidator
        self._context_builder = context_builder or RecommendationContextBuilder
        self._generator = generator or DeepSeekCandidateGenerator(provider=provider)
        self._raise_on_rejection = raise_on_rejection

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
        raise_on_rejection: Optional[bool] = None,
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

        # 2. 调用生成器生成原始候选响应
        active_provider = provider_override or self._provider
        raw_payload, provider_name = await self._generator.generate_raw_candidates(
            context=context,
            max_candidates=max_recs,
            provider_override=active_provider,
        )

        # 3. 执行确定性三层校验与权威元数据补全
        validation_result: CandidateValidationResult = self._validator.validate_candidates_detailed(
            raw_output=raw_payload,
            context=context,
            max_allowed=max_recs,
        )

        # 4. 判断是否需要抛出校验异常 (网关端点默认阻断模式)
        should_raise = self._raise_on_rejection if raise_on_rejection is None else raise_on_rejection
        if should_raise and validation_result.rejected_candidates:
            first_rej = validation_result.rejected_candidates[0]
            raise ValidationRejectedError(first_rej.reason, first_rej.code)

        # 5. 提取 AI 生成的原始候选对象列表 (若是标准结构)
        ai_cands: Optional[List[Dict[str, Any]]] = None
        if isinstance(raw_payload, dict) and isinstance(raw_payload.get("recommendations"), list):
            ai_cands = [item for item in raw_payload["recommendations"] if isinstance(item, dict)]
        elif isinstance(raw_payload, list):
            ai_cands = [item for item in raw_payload if isinstance(item, dict)]

        # 6. 组装标准响应契约并返回 (包含结构化拒绝与确定性排序推荐)
        return RecommendationResponse(
            student_id=context.student_id,
            recommendations=validation_result.validated_candidates,
            source=provider_name,
            validated=len(validation_result.rejected_candidates) == 0,
            ai_candidates=ai_cands,
            validated_candidates=validation_result.validated_candidates,
            rejected_candidates=validation_result.rejected_candidates,
            validation_reasons=validation_result.validation_reasons,
        )


# 全局单例
default_recommendation_service = RecommendationService()
