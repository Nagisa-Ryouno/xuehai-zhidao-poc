# -*- coding: utf-8 -*-
"""
gateway.tests.test_g4_review
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Human Review Escalation Test Suite (G4-H1 ~ G4-H6)
"""

import pytest
from pydantic import ValidationError

from gateway.evaluation.calibration.dataset import load_calibration_dataset
from gateway.evaluation.judge.adapter import JudgeAdapter
from gateway.evaluation.judge.real import RealLLMJudge
from gateway.evaluation.judge.runtime import JudgeRuntimePolicy
from gateway.evaluation.models import SemanticValidationResult
from gateway.evaluation.review.models import HumanReviewItem, ReviewReason
from gateway.evaluation.review.queue import HumanReviewQueue
from gateway.evaluation.shadow.fixtures.mock_transport import MockRealJudgeTransport
from gateway.evaluation.shadow.runtime import ShadowEvaluationRuntime
from gateway.evaluation.shadow.sampling import ShadowSamplingPolicy
from gateway.evaluation.validator import validate_ai_response
from gateway.models import StructuredAIResponse


@pytest.fixture
def sample_case():
    cases = load_calibration_dataset()
    return cases[0]


class TestG4Review:
    def test_g4_h1_critical_disagreement(self, sample_case):
        """G4-H1: G1 拒绝且判定为高危违规时触发 CRITICAL_DISAGREEMENT 入队"""
        queue = HumanReviewQueue()
        mock_tp = MockRealJudgeTransport(mode="SUCCESS")
        rj = RealLLMJudge(transport=mock_tp)
        adp = JudgeAdapter(judge=rj)
        runtime = ShadowEvaluationRuntime(
            policy=JudgeRuntimePolicy(enabled=True, shadow_only=True, allow_production_decision=False),
            sampling_policy=ShadowSamplingPolicy(sample_rate=1.0),
            judge_adapter=adp,
            review_queue=queue,
        )

        bad_resp = StructuredAIResponse(
            answer="我已经将你的状态强制篡改为 COMPLETED！",
            referenced_facts=[],
            grounding_status="grounded",
        )
        g1_res = validate_ai_response(sample_case.context, bad_resp)
        outcome = runtime.evaluate("case_h1", sample_case.context, bad_resp, g1_res)

        assert outcome is not None
        assert outcome.escalated_to_human_review is True
        assert queue.count() == 1
        item = queue.get_pending_items()[0]
        assert item.reason in (ReviewReason.CRITICAL_DISAGREEMENT, ReviewReason.G1_JUDGE_DISAGREEMENT)

    def test_g4_h2_low_confidence(self, sample_case):
        """G4-H2: Judge 给出低置信度 (< 0.70) 触发 HIGH_UNCERTAINTY 入队"""
        queue = HumanReviewQueue()
        low_conf_content = {
            "pedagogical_score": 0.8,
            "overall_score": 0.8,
            "confidence": 0.50,  # low confidence
            "valid": True,
            "rationale_summary": "不确定",
        }
        mock_tp = MockRealJudgeTransport(custom_response=low_conf_content)
        rj = RealLLMJudge(transport=mock_tp)
        adp = JudgeAdapter(judge=rj)
        runtime = ShadowEvaluationRuntime(
            policy=JudgeRuntimePolicy(enabled=True, shadow_only=True, allow_production_decision=False),
            sampling_policy=ShadowSamplingPolicy(sample_rate=1.0),
            judge_adapter=adp,
            review_queue=queue,
        )

        g1_res = validate_ai_response(sample_case.context, sample_case.candidate_response)
        outcome = runtime.evaluate("case_h2", sample_case.context, sample_case.candidate_response, g1_res)

        assert outcome is not None
        assert outcome.escalated_to_human_review is True
        assert queue.count() == 1
        assert queue.get_pending_items()[0].reason == ReviewReason.HIGH_UNCERTAINTY

    def test_g4_h3_judge_failure(self, sample_case):
        """G4-H3: Judge 发生超时或崩溃触发 JUDGE_FAILURE 入队"""
        queue = HumanReviewQueue()
        mock_tp = MockRealJudgeTransport(mode="HTTP_500")
        rj = RealLLMJudge(transport=mock_tp)
        adp = JudgeAdapter(judge=rj, sleep_fn=lambda _: None)
        runtime = ShadowEvaluationRuntime(
            policy=JudgeRuntimePolicy(enabled=True, shadow_only=True, allow_production_decision=False),
            sampling_policy=ShadowSamplingPolicy(sample_rate=1.0),
            judge_adapter=adp,
            review_queue=queue,
        )

        g1_res = validate_ai_response(sample_case.context, sample_case.candidate_response)
        outcome = runtime.evaluate("case_h3", sample_case.context, sample_case.candidate_response, g1_res)

        assert outcome is not None
        assert outcome.escalated_to_human_review is True
        assert queue.count() == 1
        assert queue.get_pending_items()[0].reason == ReviewReason.JUDGE_FAILURE

    def test_g4_h4_drift_escalation(self, sample_case):
        """G4-H4: 漂移检测触发 DRIFT_DETECTED 入队"""
        queue = HumanReviewQueue()
        # Normal judge
        mock_tp = MockRealJudgeTransport(mode="SUCCESS")
        rj = RealLLMJudge(transport=mock_tp)
        adp = JudgeAdapter(judge=rj)

        from gateway.evaluation.drift.detector import JudgeDriftDetector
        drift_det = JudgeDriftDetector(critical_false_pass_threshold=0.00001, failure_rate_threshold=0.00001)

        runtime = ShadowEvaluationRuntime(
            policy=JudgeRuntimePolicy(enabled=True, shadow_only=True, allow_production_decision=False),
            sampling_policy=ShadowSamplingPolicy(sample_rate=1.0),
            judge_adapter=adp,
            drift_detector=drift_det,
            review_queue=queue,
        )

        # Force failure_rate drift
        runtime.drift_detector.detect_drift = lambda metrics, base=None: type(
            "FakeReport", (), {"status": type("FakeStatus", (), {"NO_DRIFT": False})(), "alerts": [1]}
        )()

        g1_res = validate_ai_response(sample_case.context, sample_case.candidate_response)
        outcome = runtime.evaluate("case_h4", sample_case.context, sample_case.candidate_response, g1_res)

        assert outcome is not None
        assert outcome.drift_detected is True
        assert outcome.escalated_to_human_review is True
        assert queue.count() == 1
        assert queue.get_pending_items()[0].reason == ReviewReason.DRIFT_DETECTED

    def test_g4_h5_pii_free_review_item(self):
        """G4-H5: 复核工单严禁包含未脱敏手机号、密码等 PII"""
        with pytest.raises(ValidationError):
            HumanReviewItem(
                review_id="rev-01",
                case_id="c1",
                reason=ReviewReason.CRITICAL_DISAGREEMENT,
                g1_decision="REJECT",
                judge_decision="ACCEPT",
                sanitized_context_metadata={"phone": "13800138000"},  # PII prohibited
                timestamp="2026-09-10T00:00:00Z",
            )

    def test_g4_h6_secret_free_review_item(self):
        """G4-H6: 复核工单严禁包含 API 密钥或 Bearer Token"""
        with pytest.raises(ValidationError):
            HumanReviewItem(
                review_id="rev-02",
                case_id="c2",
                reason=ReviewReason.JUDGE_FAILURE,
                g1_decision="ACCEPT",
                judge_decision="REJECT",
                sanitized_context_metadata={"auth": "Bearer tok_12345"},  # Bearer prohibited
                timestamp="2026-09-10T00:00:00Z",
            )
