# -*- coding: utf-8 -*-
"""
gateway.tests.test_g4_production_isolation
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Production Decision & State Isolation Test Suite (G4-I1 ~ G4-I8)
"""

import copy
import pytest
from pydantic import ValidationError

from gateway.evaluation.calibration.dataset import load_calibration_dataset
from gateway.evaluation.drift.detector import JudgeDriftDetector
from gateway.evaluation.judge.adapter import JudgeAdapter
from gateway.evaluation.judge.models import FinalEvaluationResult, JudgeDecision, JudgeFailureClass
from gateway.evaluation.judge.real import RealLLMJudge
from gateway.evaluation.judge.runtime import JudgeRuntimePolicy
from gateway.evaluation.review.models import HumanReviewItem, ReviewReason
from gateway.evaluation.review.queue import HumanReviewQueue
from gateway.evaluation.shadow.fixtures.mock_transport import MockRealJudgeTransport
from gateway.evaluation.shadow.runtime import ShadowEvaluationOutcome, ShadowEvaluationRuntime
from gateway.evaluation.shadow.sampling import ShadowSamplingPolicy
from gateway.evaluation.validator import validate_ai_response
from gateway.models import LearningPromptContext, StructuredAIResponse


@pytest.fixture
def sample_case():
    cases = load_calibration_dataset()
    return cases[0]


@pytest.fixture
def mock_runtime():
    policy = JudgeRuntimePolicy(enabled=True, shadow_only=True, allow_production_decision=False)
    sampling = ShadowSamplingPolicy(sample_rate=1.0)
    mock_tp = MockRealJudgeTransport(mode="SUCCESS")
    rj = RealLLMJudge(transport=mock_tp)
    adp = JudgeAdapter(judge=rj)
    return ShadowEvaluationRuntime(policy=policy, sampling_policy=sampling, judge_adapter=adp)


class TestG4ProductionIsolation:
    def test_g4_i1_judge_accept_does_not_alter_production_decision(self, sample_case, mock_runtime):
        """G4-I1: Judge 给出 ACCEPT 绝不篡改生产学习决策与学情状态"""
        before_snap = copy.deepcopy(sample_case.context.model_dump())
        g1_res = validate_ai_response(sample_case.context, sample_case.candidate_response)

        outcome = mock_runtime.evaluate(
            sample_case.case_id, sample_case.context, sample_case.candidate_response, g1_res
        )

        assert outcome is not None
        assert outcome.production_decision_affected is False
        assert outcome.record is not None
        assert outcome.record.fusion_result["decision"] == "ACCEPT"

        after_snap = sample_case.context.model_dump()
        assert before_snap == after_snap

    def test_g4_i2_judge_reject_does_not_alter_production_decision(self, sample_case):
        """G4-I2: Judge 给出 REJECT 绝不篡改生产学习决策与学情状态"""
        before_snap = copy.deepcopy(sample_case.context.model_dump())
        g1_res = validate_ai_response(sample_case.context, sample_case.candidate_response)

        # 低分 Judge (REJECT)
        reject_content = {
            "pedagogical_score": 0.2,
            "overall_score": 0.3,
            "confidence": 0.9,
            "valid": False,
            "rationale_summary": "差评",
            "violations": ["low_quality"],
        }
        mock_tp = MockRealJudgeTransport(custom_response=reject_content)
        rj = RealLLMJudge(transport=mock_tp)
        adp = JudgeAdapter(judge=rj)
        runtime = ShadowEvaluationRuntime(
            policy=JudgeRuntimePolicy(enabled=True, shadow_only=True, allow_production_decision=False),
            sampling_policy=ShadowSamplingPolicy(sample_rate=1.0),
            judge_adapter=adp,
        )

        outcome = runtime.evaluate(
            sample_case.case_id, sample_case.context, sample_case.candidate_response, g1_res
        )

        assert outcome is not None
        assert outcome.production_decision_affected is False
        assert outcome.record.fusion_result["decision"] == "REJECT"

        after_snap = sample_case.context.model_dump()
        assert before_snap == after_snap

    def test_g4_i3_judge_error_does_not_alter_production_decision(self, sample_case):
        """G4-I3: Judge 内部异常/500 绝不破坏生产决策"""
        before_snap = copy.deepcopy(sample_case.context.model_dump())
        g1_res = validate_ai_response(sample_case.context, sample_case.candidate_response)

        mock_tp = MockRealJudgeTransport(mode="HTTP_500")
        rj = RealLLMJudge(transport=mock_tp)
        adp = JudgeAdapter(judge=rj, sleep_fn=lambda _: None)
        runtime = ShadowEvaluationRuntime(
            policy=JudgeRuntimePolicy(enabled=True, shadow_only=True, allow_production_decision=False),
            sampling_policy=ShadowSamplingPolicy(sample_rate=1.0),
            judge_adapter=adp,
        )

        outcome = runtime.evaluate(
            sample_case.case_id, sample_case.context, sample_case.candidate_response, g1_res
        )

        assert outcome is not None
        assert outcome.production_decision_affected is False
        # G1 通过但 Judge 失败，Shadow 降级至 REVIEW，生产状态不受影响
        assert outcome.record.fusion_result["decision"] == "REVIEW"

        after_snap = sample_case.context.model_dump()
        assert before_snap == after_snap

    def test_g4_i4_judge_timeout_does_not_alter_production_decision(self, sample_case):
        """G4-I4: Judge 超时绝不阻塞或修改生产决策"""
        before_snap = copy.deepcopy(sample_case.context.model_dump())
        g1_res = validate_ai_response(sample_case.context, sample_case.candidate_response)

        mock_tp = MockRealJudgeTransport(mode="TIMEOUT")
        rj = RealLLMJudge(transport=mock_tp)
        adp = JudgeAdapter(judge=rj, sleep_fn=lambda _: None)
        runtime = ShadowEvaluationRuntime(
            policy=JudgeRuntimePolicy(enabled=True, shadow_only=True, allow_production_decision=False),
            sampling_policy=ShadowSamplingPolicy(sample_rate=1.0),
            judge_adapter=adp,
        )

        outcome = runtime.evaluate(
            sample_case.case_id, sample_case.context, sample_case.candidate_response, g1_res
        )

        assert outcome is not None
        assert outcome.production_decision_affected is False
        assert outcome.record.fusion_result["decision"] == "REVIEW"

        after_snap = sample_case.context.model_dump()
        assert before_snap == after_snap

    def test_g4_i5_drift_alert_does_not_alter_production_decision(self, sample_case, mock_runtime):
        """G4-I5: 发生质量漂移 (Drift Alert) 仅触发告警，绝不修改生产决策"""
        before_snap = copy.deepcopy(sample_case.context.model_dump())
        g1_res = validate_ai_response(sample_case.context, sample_case.candidate_response)

        # 构造强行触发漂移的 detector
        detector = JudgeDriftDetector(critical_false_pass_threshold=0.0001)
        mock_runtime.drift_detector = detector

        outcome = mock_runtime.evaluate(
            sample_case.case_id, sample_case.context, sample_case.candidate_response, g1_res
        )

        assert outcome is not None
        assert outcome.production_decision_affected is False
        after_snap = sample_case.context.model_dump()
        assert before_snap == after_snap

    def test_g4_i6_human_review_queue_does_not_alter_production_decision(self, sample_case, mock_runtime):
        """G4-I6: 工单进入人工复核队列纯内存只读，绝不污染生产系统"""
        before_snap = copy.deepcopy(sample_case.context.model_dump())
        # 构造 G1 REJECT 的响应，触发 G1_JUDGE_DISAGREEMENT 入队
        bad_resp = StructuredAIResponse(
            answer="我已经强制为你解锁了下游所有考点！",
            referenced_facts=[],
            grounding_status="grounded",
        )
        g1_res = validate_ai_response(sample_case.context, bad_resp)

        outcome = mock_runtime.evaluate(
            sample_case.case_id, sample_case.context, bad_resp, g1_res
        )

        assert outcome is not None
        assert outcome.escalated_to_human_review is True
        assert outcome.production_decision_affected is False
        assert mock_runtime.review_queue.count() == 1

        after_snap = sample_case.context.model_dump()
        assert before_snap == after_snap

    def test_g4_i7_sampling_decision_does_not_alter_production_decision(self, sample_case):
        """G4-I7: 采样未命中跳过时零副作用"""
        before_snap = copy.deepcopy(sample_case.context.model_dump())
        g1_res = validate_ai_response(sample_case.context, sample_case.candidate_response)

        # sample_rate = 0.0
        runtime = ShadowEvaluationRuntime(
            policy=JudgeRuntimePolicy(enabled=True, shadow_only=True, allow_production_decision=False),
            sampling_policy=ShadowSamplingPolicy(sample_rate=0.0),
        )

        outcome = runtime.evaluate(
            sample_case.case_id, sample_case.context, sample_case.candidate_response, g1_res
        )

        assert outcome is None  # 零损耗跳过
        after_snap = sample_case.context.model_dump()
        assert before_snap == after_snap

    def test_g4_i8_outcome_production_decision_affected_strictly_forbidden(self):
        """G4-I8: 试图实例化 production_decision_affected=True 必须被校验器拒绝"""
        with pytest.raises(ValidationError) as exc:
            ShadowEvaluationOutcome(
                production_decision_affected=True
            )
        assert "JUDGE_PRODUCTION_DECISION_FORBIDDEN" in str(exc.value)
