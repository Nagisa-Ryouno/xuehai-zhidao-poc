# -*- coding: utf-8 -*-
"""
gateway.ai.recommendation.generator
====================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B / Phase 2
DeepSeek AI 候选推荐生成器 (DeepSeekCandidateGenerator)

架构定位与安全红线：
1. 职责单一：仅负责将只读 RecommendationContext 转换为 AI 候选结构，绝无生产决策权；
2. 零副作用：严禁读写业务数据库、严禁更新 BKT、严禁修改 PathState、严禁记录学习事件；
3. 显式任务路由：调用统一 Provider abstraction 时显式传递 task="recommendation"；
4. 严格只读：向大模型发起的请求经过 PII 脱敏（仅限伪匿名标识符）；
5. 结果非权威：生成的候选对象仅代表模型建议，必须经过 Deterministic Validator 校验后方可使用。
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from gateway.adapter import AIProviderAdapter, get_provider
from gateway.ai.deepseek import DeepSeekProvider, MockDeepSeekProvider, ProviderInvalidResponseError
from gateway.ai.models import AIProviderRequest
from gateway.config import gateway_settings
from gateway.ai.recommendation.models import RecommendationContext
from gateway.ai.recommendation.prompt import build_recommendation_prompt

logger = logging.getLogger("xuehai.ai.recommendation.generator")


class DeepSeekCandidateGenerator:
    """
    DeepSeek 候选推荐生成器
    
    职责仅限于：将权威只读上下文转化为模型候选输出，绝不执行任何生产状态写入。
    """

    def __init__(self, provider: Optional[AIProviderAdapter] = None):
        self._provider = provider

    def resolve_provider(self, override_provider: Optional[AIProviderAdapter] = None) -> AIProviderAdapter:
        """解析当前适用的 AI Provider 实例"""
        if override_provider is not None:
            return override_provider
        if self._provider is not None:
            return self._provider

        # 默认离线模式或未启用真实 DeepSeek 时使用 Mock Provider
        if not gateway_settings.deepseek_enabled:
            return MockDeepSeekProvider(model=gateway_settings.deepseek_model)

        return get_provider("deepseek")

    async def generate_raw_candidates(
        self,
        context: RecommendationContext,
        max_candidates: int = 3,
        provider_override: Optional[AIProviderAdapter] = None,
    ) -> Tuple[Any, str]:
        """
        调用 Provider 生成原始候选响应。
        返回 (raw_output, provider_name)。
        raw_output 可能是 parsed_json 字典，或原始未解析文本字符串（供校验器做语法拦截）。
        """
        # 1. 构建提示词对
        sys_prompt, usr_prompt = build_recommendation_prompt(context)

        # 2. 准备候选池元数据（供离线确定性 Mock 使用，避免文本猜测）
        candidate_pool = [
            {"knowledge_id": r.knowledge_id, "resource_id": r.resource_id}
            for r in context.resources
        ]

        # 3. 组装标准统一 AI 请求载荷
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
                "max_candidates": max_candidates,
            },
        )

        # 4. 调用 Provider 执行补全
        provider = self.resolve_provider(provider_override)
        ai_resp = await provider.complete(ai_req)

        # 5. 提取响应载荷
        raw_payload = ai_resp.parsed_json if ai_resp.parsed_json is not None else ai_resp.content
        return raw_payload, provider.provider_name
