# -*- coding: utf-8 -*-
"""
gateway.evaluation.shadow.runtime
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Shadow Evaluation Runtime (旁路评估运行时总控)

核心原则：
1. 观察者语义：Fusion 结果与 Judge 评分仅作为 Shadow Observation 暂存，绝不回写或干预生产决策
2. 绝对生产隔离：production_decision_affected 强制为 False，任何尝试设为 True 立即拒绝
3. 严格全生命周期防御：采样过滤 -> 安全守卫 -> 投影脱敏 -> 隔离调用 -> 漂移审计 -> 复核升级 -> 审计发射
"""

import copy
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from gateway.audit import AuditEvent, AuditSink, NullAuditSink
from gateway.evaluation.drift.detector import JudgeDriftDetector
from gateway.evaluation.drift.models import DriftStatus
from gateway.evaluation.judge.adapter import JudgeAdapter
from gateway.evaluation.judge.fake import FakeLLMJudge
from gateway.evaluation.judge.fusion import EvaluationFusionEngine
from gateway.evaluation.judge.models import (
    JudgeDecision,
    JudgeFailureClass,
)
from gateway.evaluation.judge.runtime import (
    JudgeRuntimePolicy,
    RUNTIME_POLICY_VERSION,
    SHADOW_SCHEMA_VERSION,
)
from gateway.evaluation.judge.runtime_guard import JudgeRuntimeGuard
from gateway.evaluation.models import SemanticValidationResult
from gateway.evaluation.review.models import HumanReviewItem, ReviewReason
from gateway.evaluation.review.queue import HumanReviewQueue
from gateway.evaluation.shadow.models import ShadowEvaluationRecord
from gateway.evaluation.shadow.recorder import ShadowEvaluationRecorder
from gateway.evaluation.shadow.sampling import ShadowSamplingPolicy
from gateway.models import LearningPromptContext, StructuredAIResponse


class ShadowEvaluationOutcome(BaseModel):
    """
    Shadow 运行时最终产出信封 (只读，绝无生产决策副作用)
    """
    model_config = ConfigDict(extra="forbid")

    record: Optional[ShadowEvaluationRecord] = Field(default=None, description="旁路评估持久化记录")
    production_decision_affected: bool = Field(
        default=False, description="生产业务决策是否受影响 (强制为 False)"
    )
    drift_detected: bool = Field(default=False, description="是否触发质量漂移")
    escalated_to_human_review: bool = Field(default=False, description="是否升级进入人工复核工单")
    review_item: Optional[HumanReviewItem] = Field(default=None, description="生成的复核工单实体")

    @field_validator("production_decision_affected")
    @classmethod
    def enforce_zero_production_effect(cls, v: bool) -> bool:
        if v is True:
            raise ValueError("JUDGE_PRODUCTION_DECISION_FORBIDDEN: Shadow outcome cannot affect production decision")
        return v


class ShadowEvaluationRuntime:
    """
    Shadow Evaluation 旁路评估主控引擎
    """

    def __init__(
        self,
        policy: Optional[JudgeRuntimePolicy] = None,
        sampling_policy: Optional[ShadowSamplingPolicy] = None,
        judge_adapter: Optional[JudgeAdapter] = None,
        guard: Optional[JudgeRuntimeGuard] = None,
        fusion_engine: Optional[EvaluationFusionEngine] = None,
        drift_detector: Optional[JudgeDriftDetector] = None,
        review_queue: Optional[HumanReviewQueue] = None,
        recorder: Optional[ShadowEvaluationRecorder] = None,
        audit_sink: Optional[AuditSink] = None,
    ):
        self.policy = policy or JudgeRuntimePolicy()
        self.sampling_policy = sampling_policy or ShadowSamplingPolicy()
        self.guard = guard or JudgeRuntimeGuard(policy=self.policy)
        self.judge_adapter = judge_adapter or JudgeAdapter(judge=FakeLLMJudge(forced_mode="HIGH"))
        self.fusion_engine = fusion_engine or EvaluationFusionEngine()
        self.drift_detector = drift_detector or JudgeDriftDetector()
        self.review_queue = review_queue or HumanReviewQueue()
        self.recorder = recorder or ShadowEvaluationRecorder()
        self.audit_sink = audit_sink or NullAuditSink()

    def evaluate(
        self,
        case_id: str,
        context: LearningPromptContext,
        response: StructuredAIResponse,
        g1_result: SemanticValidationResult,
        risk_level: str = "MEDIUM",
        category: Optional[str] = None,
    ) -> Optional[ShadowEvaluationOutcome]:
        """
        执行受控 Shadow 评估全流程

        @param case_id 用例或请求唯一 ID
        @param context 原始学情上下文
        @param response 待评估 AI 候选回答
        @param g1_result G1 确定性校验结果
        @param risk_level 风险级别
        @param category 考点或用例分类
        @return Optional[ShadowEvaluationOutcome] 若未启用或未命中采样返回 None，否则返回只读旁路报告
        """
        # 1. 默认安全关闭：若策略未启用，直接安全旁路跳过
        if not self.policy.enabled:
            return None

        # 2. 采样判定：未命中采样直接跳过，零资源消耗
        if not self.sampling_policy.should_sample(case_id=case_id, category=category, risk_level=risk_level):
            return None

        # 3. 前置安全守卫检查 (Guard 1 & Guard 2)
        self.guard.check_configuration_safety(self.policy)
        self.guard.check_shadow_only_enforcement(self.policy)

        # 4. 深度快照记录 (Guard 4 前置)
        before_snapshot = copy.deepcopy(context.model_dump())

        # 5. 纵深安全脱敏处理 (Guard 3)
        projection = self.guard.scrub_context_for_pii_and_secrets(context)

        # 6. 发射 Shadow 启动审计事件
        self.audit_sink.record(
            AuditEvent(
                event_name="ai_gateway.judge.shadow_started",
                request_id=case_id,
                provider=self.policy.provider,
                model=self.policy.model,
                status="SUCCESS",
            )
        )

        # 7. 调用 JudgeAdapter 进行受控评测
        judge_res, failure_class = self.judge_adapter.evaluate_safe(context, response)

        # 8. 状态隔离验证 (Guard 4 后置)：断言无任何突变
        after_snapshot = context.model_dump()
        self.guard.verify_state_isolation(before_snapshot, after_snapshot)

        # 9. 融合裁决 (作为 Observation Only)
        fusion_res = self.fusion_engine.fuse(g1_result, judge_res, failure_class)

        latency_ms = getattr(self.judge_adapter, "last_latency_ms", 0.0)

        # 10. 记录至 Shadow 专有观测器
        record = self.recorder.record(
            case_id=case_id,
            g1_result=g1_result.model_dump(),
            judge_result=judge_res.model_dump() if judge_res else None,
            fusion_result=fusion_res.model_dump(),
            judge_provider=self.policy.provider,
            judge_model=self.policy.model,
            prompt_version="g3.0",
            rubric_version="g3.0",
            latency_ms=latency_ms,
            failure_class=failure_class.value,
        )

        # 11. 漂移检测 (Drift Detection)
        j_score = judge_res.overall_score if judge_res else 0.0
        drift_report = self.drift_detector.detect_drift({
            "accept_rate": 1.0 if (judge_res and judge_res.overall_score >= 0.8) else 0.0,
            "average_score": j_score,
            "failure_rate": 1.0 if failure_class != JudgeFailureClass.NONE else 0.0,
            "average_latency_ms": latency_ms,
        })
        is_drift = (drift_report.status != DriftStatus.NO_DRIFT)
        if is_drift:
            self.audit_sink.record(
                AuditEvent(
                    event_name="ai_gateway.judge.drift_detected",
                    request_id=case_id,
                    provider=self.policy.provider,
                    model=self.policy.model,
                    status="SUCCESS",
                    failure_class=failure_class.value,
                    latency_ms=latency_ms,
                )
            )

        # 12. 人工复核升级检查 (Human Review Escalation Rules)
        review_item: Optional[HumanReviewItem] = None
        review_reason: Optional[ReviewReason] = None

        g1_pass = (g1_result.valid and g1_result.policy_compliant and g1_result.factual_consistency)
        judge_accept = (judge_res is not None and judge_res.overall_score >= 0.80 and judge_res.confidence >= 0.70)

        if not g1_pass and judge_accept:
            review_reason = ReviewReason.G1_JUDGE_DISAGREEMENT
        elif not g1_result.policy_compliant or not g1_result.factual_consistency:
            review_reason = ReviewReason.CRITICAL_DISAGREEMENT
        elif failure_class != JudgeFailureClass.NONE:
            review_reason = ReviewReason.JUDGE_FAILURE
        elif judge_res and judge_res.confidence < 0.70:
            review_reason = ReviewReason.HIGH_UNCERTAINTY
        elif is_drift:
            review_reason = ReviewReason.DRIFT_DETECTED

        if review_reason is not None:
            review_item = HumanReviewItem(
                review_id=str(uuid.uuid4()),
                case_id=case_id,
                reason=review_reason,
                risk_level=risk_level,
                g1_decision="ACCEPT" if g1_pass else "REJECT",
                judge_decision="ACCEPT" if judge_accept else ("REVIEW" if judge_res else "FAILURE"),
                judge_scores=judge_res.dimension_scores if judge_res else {},
                sanitized_context_metadata={
                    "knowledge_id": context.system_facts.current_knowledge_id,
                    "knowledge_name": context.system_facts.current_knowledge_name,
                },
                prompt_version="g3.0",
                rubric_version="g3.0",
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            )
            self.review_queue.enqueue(review_item)
            self.audit_sink.record(
                AuditEvent(
                    event_name="ai_gateway.judge.human_review_required",
                    request_id=case_id,
                    provider=self.policy.provider,
                    model=self.policy.model,
                    status="SUCCESS",
                )
            )

        # 13. 发射完成/失败审计事件
        comp_event_name = (
            "ai_gateway.judge.shadow_completed"
            if failure_class == JudgeFailureClass.NONE
            else "ai_gateway.judge.shadow_failed"
        )
        self.audit_sink.record(
            AuditEvent(
                event_name=comp_event_name,
                request_id=case_id,
                provider=self.policy.provider,
                model=self.policy.model,
                status="SUCCESS" if failure_class == JudgeFailureClass.NONE else "FAILED",
                failure_class=failure_class.value,
                latency_ms=latency_ms,
            )
        )

        return ShadowEvaluationOutcome(
            record=record,
            production_decision_affected=False,
            drift_detected=is_drift,
            escalated_to_human_review=(review_item is not None),
            review_item=review_item,
        )
