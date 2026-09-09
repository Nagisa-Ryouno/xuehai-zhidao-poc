# -*- coding: utf-8 -*-
"""
gateway.tests.test_calibration_shadow
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Shadow Evaluation Test Suite
"""

import pytest
from pydantic import ValidationError

from gateway.evaluation.shadow.models import ShadowEvaluationRecord
from gateway.evaluation.shadow.recorder import ShadowEvaluationRecorder
from gateway.evaluation.judge.models import JudgeDecision, JudgeFailureClass, FinalEvaluationResult


class TestShadowEvaluation:
    def test_shadow_record_valid(self):
        record = ShadowEvaluationRecord(
            case_id="cal-001",
            g1_result={"valid": True, "policy_compliant": True, "factual_consistency": True},
            judge_result={"overall_score": 0.88, "valid": True},
            fusion_result={"decision": "ACCEPT", "final_valid": True},
            judge_provider="fake_provider",
            judge_model="test-judge-v1",
            prompt_version="g3.0",
            rubric_version="g3.0",
            latency_ms=45.2,
            failure_class="NONE",
            timestamp="2026-09-10T00:00:00Z",
        )
        assert record.case_id == "cal-001"
        assert record.latency_ms == 45.2

    def test_shadow_record_forbids_secret_and_pii(self):
        with pytest.raises(ValueError):
            ShadowEvaluationRecord(
                case_id="cal-002",
                g1_result={"valid": True},
                judge_result={"overall_score": 0.88},
                fusion_result={"decision": "ACCEPT"},
                judge_provider="fake_provider",
                judge_model="test-judge-v1",
                prompt_version="g3.0",
                rubric_version="g3.0",
                latency_ms=12.0,
                failure_class="NONE",
                timestamp="2026-09-10T00:00:00Z",
                # PII or Secret in dict
                extra_secret="sk-live-secret-key-12345",  # forbidden field
            )

    def test_shadow_record_scrubs_pii_in_results(self):
        with pytest.raises(ValueError):
            ShadowEvaluationRecord(
                case_id="cal-003",
                g1_result={"student_phone": "13800138000"},  # PII leak
                judge_result={"overall_score": 0.88},
                fusion_result={"decision": "ACCEPT"},
                judge_provider="fake_provider",
                judge_model="test-judge-v1",
                prompt_version="g3.0",
                rubric_version="g3.0",
                latency_ms=12.0,
                failure_class="NONE",
                timestamp="2026-09-10T00:00:00Z",
            )

    def test_shadow_recorder_in_memory_lifecycle(self):
        recorder = ShadowEvaluationRecorder()
        assert recorder.count() == 0

        rec = recorder.record(
            case_id="cal-010",
            g1_result={"valid": True},
            judge_result={"overall_score": 0.85},
            fusion_result={"decision": "ACCEPT"},
            judge_provider="fake",
            judge_model="model",
            prompt_version="g3.0",
            rubric_version="g3.0",
            latency_ms=30.0,
            failure_class="NONE",
        )
        assert recorder.count() == 1
        assert recorder.get_records()[0].case_id == "cal-010"

        recorder.clear()
        assert recorder.count() == 0

    def test_shadow_mode_does_not_mutate_production_decision(self):
        # Even if shadow judge fails or gives low score, production decision stays intact
        recorder = ShadowEvaluationRecorder()
        prod_decision = FinalEvaluationResult(
            decision=JudgeDecision.ACCEPT,
            final_valid=True,
            deterministic_valid=True,
            policy_compliant=True,
            factual_consistency=True,
            deterministic_scores={"quality": 0.9},
            judge_used=False,
            judge_result=None,
            judge_failure_class=JudgeFailureClass.NONE,
            rationale="G1 passed, shadow mode active",
            violations=[],
        )

        rec = recorder.record(
            case_id="cal-prod-01",
            g1_result={"valid": True},
            judge_result={"overall_score": 0.20, "valid": False}, # Shadow judge says low!
            fusion_result=prod_decision.model_dump(),
            judge_provider="shadow_provider",
            judge_model="shadow_model",
            prompt_version="g3.0",
            rubric_version="g3.0",
            latency_ms=15.0,
            failure_class="NONE",
        )

        # The recorded result is purely an observer; prod_decision is completely unchanged
        assert prod_decision.decision == JudgeDecision.ACCEPT
        assert prod_decision.final_valid is True
        assert rec.case_id == "cal-prod-01"
