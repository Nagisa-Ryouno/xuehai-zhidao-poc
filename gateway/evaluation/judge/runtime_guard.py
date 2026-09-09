# -*- coding: utf-8 -*-
"""
gateway.evaluation.judge.runtime_guard
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Judge Runtime Guard (运行时安全守卫体系)

四层安全防御守卫：
- Guard 1: Configuration Safety (配置有界性与默认关闭验证)
- Guard 2: Shadow-only Enforcement (旁路强制与生产决策绝对隔离)
- Guard 3: PII & Secret Defense (纵深安全脱敏，防止密钥与个人隐私泄漏)
- Guard 4: State Isolation (深度上下文快照比对，零业务状态副作用)
"""

import copy
import re
from typing import Any, Dict, Optional

from gateway.evaluation.judge.models import EvaluationContextProjection
from gateway.evaluation.judge.runtime import JudgeRuntimePolicy
from gateway.models import LearningPromptContext

# 敏感模式正则匹配
RE_PHONE = re.compile(r"1[3-9]\d{9}")
RE_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
RE_BEARER = re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]+")
RE_API_KEY = re.compile(r"(?i)(sk-[a-zA-Z0-9]{10,}|api_key=[a-zA-Z0-9_-]+)")
RE_PASSWORD = re.compile(r"(?i)(password|passwd)[:=]\s*\S+")


class JudgeRuntimeGuard:
    """
    Judge 运行时安全守卫管理器
    """

    def __init__(self, policy: Optional[JudgeRuntimePolicy] = None):
        self.policy = policy or JudgeRuntimePolicy()

    def check_configuration_safety(self, policy: Optional[JudgeRuntimePolicy] = None) -> bool:
        """
        Guard 1: 验证运行时配置安全性
        """
        pol = policy or self.policy

        if not (0.1 <= pol.timeout_seconds <= 30.0):
            raise ValueError(f"Configuration safety failed: timeout_seconds out of bounds: {pol.timeout_seconds}")
        if pol.max_requests_per_minute <= 0:
            raise ValueError("Configuration safety failed: max_requests_per_minute must be > 0")
        if pol.max_daily_requests <= 0:
            raise ValueError("Configuration safety failed: max_daily_requests must be > 0")
        if not pol.provider or not pol.model:
            raise ValueError("Configuration safety failed: provider and model must be specified")

        return True

    def check_shadow_only_enforcement(self, policy: Optional[JudgeRuntimePolicy] = None) -> bool:
        """
        Guard 2: 强制 Shadow-only 且禁止接管生产决策
        """
        pol = policy or self.policy
        if pol.allow_production_decision is not False:
            raise ValueError("JUDGE_PRODUCTION_DECISION_FORBIDDEN")
        if pol.shadow_only is not True:
            raise RuntimeError("SHADOW_ONLY_MANDATORY: Production decision taking by Judge is strictly forbidden")
        return True

    def scrub_context_for_pii_and_secrets(
        self,
        context: LearningPromptContext,
    ) -> EvaluationContextProjection:
        """
        Guard 3: 纵深脱敏防御，构造零 PII、零 Secret 的 EvaluationContextProjection
        """
        user_q = context.user_question
        # 1. 深度清洗敏感模式
        user_q = RE_PHONE.sub("[REDACTED_PHONE]", user_q)
        user_q = RE_EMAIL.sub("[REDACTED_EMAIL]", user_q)
        user_q = RE_BEARER.sub("[REDACTED_BEARER]", user_q)
        user_q = RE_API_KEY.sub("[REDACTED_KEY]", user_q)
        user_q = RE_PASSWORD.sub("[REDACTED_PASS]", user_q)

        facts = context.system_facts

        # 2. 构造 EvaluationContextProjection，隔离 student_id, student_name, major, grade
        projection = EvaluationContextProjection(
            knowledge_node_id=facts.current_knowledge_id,
            knowledge_node_title=facts.current_knowledge_name,
            current_mastery_percent=facts.current_mastery_percent,
            mastery_target_percent=facts.mastery_target_percent,
            is_mastered=facts.is_mastered,
            decision=facts.next_action.type,
            current_question=user_q,
        )

        return projection

    def verify_state_isolation(self, before_snapshot: Dict[str, Any], after_snapshot: Dict[str, Any]) -> None:
        """
        Guard 4: 验证学习上下文状态绝对隔离，禁止任何突变
        """
        if before_snapshot != after_snapshot:
            raise RuntimeError("SHADOW_STATE_MUTATION: LearningContext state mutation detected during shadow evaluation")
