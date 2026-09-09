# -*- coding: utf-8 -*-
"""
gateway.tests.test_calibration_metrics
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Calibration Metrics & Agreement Calculations Test Suite
"""

import pytest

from gateway.evaluation.calibration.metrics import (
    calculate_decision_metrics,
    calculate_risk_metrics,
    calculate_score_metrics,
    calculate_human_agreement,
    calculate_category_breakdown,
)
from gateway.evaluation.calibration.models import (
    CalibrationCategory,
    CalibrationExpectedDecision,
    CalibrationRiskLevel,
    ConfidenceLevel,
    CalibrationCase,
    HumanLabel,
    ComparisonResult,
)
from gateway.evaluation.judge.models import JudgeDecision


def _create_comp(case_id, h_dec, j_dec, h_score, j_score, crit=False, is_crit_fp=False):
    return ComparisonResult(
        case_id=case_id,
        human_decision=h_dec,
        judge_decision=j_dec,
        decision_match=(h_dec == j_dec),
        human_scores={"overall_quality": h_score},
        judge_scores={"overall_score": j_score},
        score_errors={"overall_error": round(abs(h_score - j_score), 4)},
        critical_failure_match=True,
        is_critical_false_pass=is_crit_fp,
    )


class TestCalibrationMetrics:
    def test_decision_metrics_calculation(self):
        # 4 items:
        # Case 1: H=ACCEPT, J=ACCEPT (TP)
        # Case 2: H=ACCEPT, J=REVIEW (FN)
        # Case 3: H=REJECT, J=REJECT (TN)
        # Case 4: H=REJECT, J=ACCEPT (FP)
        comps = [
            _create_comp("c1", JudgeDecision.ACCEPT, JudgeDecision.ACCEPT, 0.9, 0.9),
            _create_comp("c2", JudgeDecision.ACCEPT, JudgeDecision.REVIEW, 0.8, 0.7),
            _create_comp("c3", JudgeDecision.REJECT, JudgeDecision.REJECT, 0.1, 0.1),
            _create_comp("c4", JudgeDecision.REJECT, JudgeDecision.ACCEPT, 0.1, 0.8),
        ]

        metrics = calculate_decision_metrics(comps)
        assert metrics["total"] == 4
        assert metrics["accuracy"] == 0.5  # 2 out of 4 match
        assert metrics["precision"] == 0.5  # TP / (TP + FP) = 1 / 2
        assert metrics["recall"] == 0.5     # TP / (TP + FN) = 1 / 2
        assert metrics["f1"] == 0.5

        cm = metrics["confusion_matrix"]
        assert cm["ACCEPT"]["ACCEPT"] == 1
        assert cm["ACCEPT"]["REVIEW"] == 1
        assert cm["REJECT"]["ACCEPT"] == 1
        assert cm["REJECT"]["REJECT"] == 1

    def test_risk_metrics_far_and_critical_false_pass(self):
        # c1: Non-critical, H=REJECT, J=ACCEPT (FAR event)
        # c2: Critical, H=REJECT, J=ACCEPT (Critical False Pass!)
        # c3: Critical, H=REJECT, J=REJECT (Critical caught)
        # c4: H=ACCEPT, J=REJECT (FRR event)
        comps = [
            _create_comp("c1", JudgeDecision.REJECT, JudgeDecision.ACCEPT, 0.2, 0.85, crit=False, is_crit_fp=False),
            _create_comp("c2", JudgeDecision.REJECT, JudgeDecision.ACCEPT, 0.1, 0.90, crit=True, is_crit_fp=True),
            _create_comp("c3", JudgeDecision.REJECT, JudgeDecision.REJECT, 0.1, 0.10, crit=True, is_crit_fp=False),
            _create_comp("c4", JudgeDecision.ACCEPT, JudgeDecision.REJECT, 0.9, 0.20, crit=False, is_crit_fp=False),
        ]
        critical_case_ids = {"c2", "c3"}

        risk = calculate_risk_metrics(comps, critical_case_ids)
        # Total human != ACCEPT: c1, c2, c3 (3 items). J=ACCEPT on c1, c2 -> FAR = 2/3
        assert pytest.approx(risk["false_accept_rate"], 0.01) == 0.67
        # Total human == ACCEPT: c4 (1 item). J=REJECT on c4 -> FRR = 1/1 = 1.0
        assert risk["false_reject_rate"] == 1.0
        # Critical cases: c2, c3 (2 items). J=ACCEPT on c2 -> Critical False Pass = 1/2 = 0.5
        assert risk["critical_false_pass_rate"] == 0.5
        # Critical recall: c3 rejected out of 2 -> 0.5
        assert risk["critical_recall"] == 0.5

    def test_score_metrics_mae_and_correlation(self):
        comps = [
            _create_comp("c1", JudgeDecision.ACCEPT, JudgeDecision.ACCEPT, 0.9, 0.8), # err 0.1
            _create_comp("c2", JudgeDecision.ACCEPT, JudgeDecision.ACCEPT, 0.8, 0.7), # err 0.1
            _create_comp("c3", JudgeDecision.REJECT, JudgeDecision.REJECT, 0.2, 0.3), # err 0.1
        ]
        score_metrics = calculate_score_metrics(comps)
        assert pytest.approx(score_metrics["overall_mae"], 0.01) == 0.10
        assert "dimensions" in score_metrics
        assert "overall_quality" in score_metrics["dimensions"]
        assert score_metrics["dimensions"]["overall_quality"]["mae"] == pytest.approx(0.10, 0.01)

    def test_human_agreement_single_annotator_not_available(self):
        # Only one annotator
        labels = {
            "c1": [HumanLabel(
                case_id="c1", annotator_id="A1",
                pedagogical_value=0.9, explanation_depth=0.9, tone_appropriateness=0.9,
                guidance_clarity=0.9, overall_quality=0.9, decision=JudgeDecision.ACCEPT,
                confidence=ConfidenceLevel.HIGH, critical_failure=False
            )]
        }
        res = calculate_human_agreement(labels)
        assert res["status"] == "NOT_AVAILABLE"
        assert res["cohen_kappa"] is None
        assert "Only one annotator" in res["reason"]

    def test_category_breakdown_metrics(self):
        comps = [
            _create_comp("c1", JudgeDecision.ACCEPT, JudgeDecision.ACCEPT, 0.9, 0.9),
            _create_comp("c2", JudgeDecision.ACCEPT, JudgeDecision.REVIEW, 0.9, 0.7),
        ]
        case_categories = {"c1": CalibrationCategory.NORMAL, "c2": CalibrationCategory.NORMAL}
        breakdown = calculate_category_breakdown(comps, case_categories)

        assert "NORMAL" in breakdown
        assert breakdown["NORMAL"]["total"] == 2
        assert breakdown["NORMAL"]["matched"] == 1
        assert breakdown["NORMAL"]["accuracy"] == 0.5
