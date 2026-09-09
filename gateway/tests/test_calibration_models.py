# -*- coding: utf-8 -*-
"""
gateway.tests.test_calibration_models
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Calibration Domain Models & Contracts Test Suite
"""

import math
import pytest
from pydantic import ValidationError

from gateway.evaluation.calibration.models import (
    CALIBRATION_DATASET_VERSION,
    CALIBRATION_RUBRIC_VERSION,
    JUDGE_PROMPT_VERSION,
    CalibrationCategory,
    CalibrationExpectedDecision,
    CalibrationRiskLevel,
    ConfidenceLevel,
    CalibrationCase,
    HumanLabel,
    ComparisonResult,
    CalibrationReport,
)
from gateway.evaluation.judge.models import JudgeDecision
from gateway.models import (
    LearningPromptContext,
    LearningPromptSystemFacts,
    PromptNextAction,
    StructuredAIResponse,
)


def _make_dummy_context() -> LearningPromptContext:
    return LearningPromptContext(
        user_question="什么是需求价格弹性？",
        system_facts=LearningPromptSystemFacts(
            student_id="S001",
            student_name="测试同学",
            major="经济学",
            grade="大一",
            learning_goal="掌握微观经济学",
            current_knowledge_id="K08",
            current_knowledge_name="需求价格弹性",
            current_chapter="第二章 需求与供给",
            current_path_state="IN_PROGRESS",
            current_mastery_percent=75.0,
            mastery_target_percent=80.0,
            mastery_gap_percent=5.0,
            is_mastered=False,
            prerequisites_met=True,
            path_priority="NORMAL",
            is_path_completed=False,
            recent_quiz=None,
            next_action=PromptNextAction(
                type="PRACTICE",
                label="练习强化",
                target_knowledge_id="K08",
                reason="巩固弹性概念",
            ),
        ),
        grounding_rules=["根据客观事实作答"],
    )


def _make_dummy_response() -> StructuredAIResponse:
    return StructuredAIResponse(
        answer="需求价格弹性衡量价格变化引起的需求量变动程度。",
        referenced_facts=["当前掌握度75%"],
        suggested_explanation="可以理解为需求敏感度",
        grounding_status="grounded",
    )


class TestCalibrationModels:
    def test_version_constants(self):
        assert CALIBRATION_DATASET_VERSION == "g3-cp3.0"
        assert CALIBRATION_RUBRIC_VERSION == "g3.0"
        assert JUDGE_PROMPT_VERSION == "g3.0"

    def test_calibration_category_values(self):
        expected = {
            "NORMAL",
            "LOW_MASTERY",
            "HIGH_MASTERY",
            "BOUNDARY",
            "SAFETY",
            "FACT_CRITICAL",
            "ADVERSARIAL",
            "OFF_TOPIC",
        }
        actual = {c.value for c in CalibrationCategory}
        assert actual == expected

    def test_calibration_case_valid(self):
        case = CalibrationCase(
            case_id="cal-001",
            category=CalibrationCategory.NORMAL,
            risk_level=CalibrationRiskLevel.LOW,
            context=_make_dummy_context(),
            candidate_response=_make_dummy_response(),
            expected_decision=CalibrationExpectedDecision.CLEAR_ACCEPT,
            critical_failure=False,
            expected_violations=[],
            notes="标准合规用例",
        )
        assert case.case_id == "cal-001"
        assert case.critical_failure is False

    def test_calibration_case_extra_forbid(self):
        raw = {
            "case_id": "cal-002",
            "category": "NORMAL",
            "risk_level": "LOW",
            "context": _make_dummy_context().model_dump(),
            "candidate_response": _make_dummy_response().model_dump(),
            "expected_decision": "CLEAR_ACCEPT",
            "unauthorized_field": "injected",
        }
        with pytest.raises(ValidationError):
            CalibrationCase.model_validate(raw)

    def test_human_label_valid(self):
        label = HumanLabel(
            case_id="cal-001",
            annotator_id="annotator-A",
            pedagogical_value=0.9,
            explanation_depth=0.85,
            tone_appropriateness=0.95,
            guidance_clarity=0.88,
            overall_quality=0.89,
            decision=JudgeDecision.ACCEPT,
            confidence=ConfidenceLevel.HIGH,
            critical_failure=False,
            notes="优秀解答",
        )
        assert label.case_id == "cal-001"
        assert label.pedagogical_value == 0.9

    def test_human_label_score_out_of_bounds(self):
        with pytest.raises(ValidationError):
            HumanLabel(
                case_id="cal-001",
                annotator_id="annotator-A",
                pedagogical_value=1.5,  # > 1.0
                explanation_depth=0.8,
                tone_appropriateness=0.8,
                guidance_clarity=0.8,
                overall_quality=0.8,
                decision=JudgeDecision.ACCEPT,
                confidence=ConfidenceLevel.HIGH,
                critical_failure=False,
            )

        with pytest.raises(ValidationError):
            HumanLabel(
                case_id="cal-001",
                annotator_id="annotator-A",
                pedagogical_value=-0.1,  # < 0.0
                explanation_depth=0.8,
                tone_appropriateness=0.8,
                guidance_clarity=0.8,
                overall_quality=0.8,
                decision=JudgeDecision.ACCEPT,
                confidence=ConfidenceLevel.HIGH,
                critical_failure=False,
            )

    def test_human_label_nan_or_inf_rejected(self):
        with pytest.raises(ValidationError):
            HumanLabel(
                case_id="cal-001",
                annotator_id="annotator-A",
                pedagogical_value=float("nan"),
                explanation_depth=0.8,
                tone_appropriateness=0.8,
                guidance_clarity=0.8,
                overall_quality=0.8,
                decision=JudgeDecision.ACCEPT,
                confidence=ConfidenceLevel.HIGH,
                critical_failure=False,
            )

        with pytest.raises(ValidationError):
            HumanLabel(
                case_id="cal-001",
                annotator_id="annotator-A",
                pedagogical_value=float("inf"),
                explanation_depth=0.8,
                tone_appropriateness=0.8,
                guidance_clarity=0.8,
                overall_quality=0.8,
                decision=JudgeDecision.ACCEPT,
                confidence=ConfidenceLevel.HIGH,
                critical_failure=False,
            )

    def test_human_label_extra_forbid(self):
        with pytest.raises(ValidationError):
            HumanLabel(
                case_id="cal-001",
                annotator_id="annotator-A",
                pedagogical_value=0.8,
                explanation_depth=0.8,
                tone_appropriateness=0.8,
                guidance_clarity=0.8,
                overall_quality=0.8,
                decision=JudgeDecision.ACCEPT,
                confidence=ConfidenceLevel.HIGH,
                critical_failure=False,
                leaked_token="secret-123",
            )

    def test_comparison_result_valid(self):
        comp = ComparisonResult(
            case_id="cal-001",
            human_decision=JudgeDecision.ACCEPT,
            judge_decision=JudgeDecision.ACCEPT,
            decision_match=True,
            human_scores={"overall_quality": 0.85},
            judge_scores={"overall_score": 0.86},
            score_errors={"overall_error": 0.01},
            critical_failure_match=True,
            is_critical_false_pass=False,
        )
        assert comp.decision_match is True
        assert comp.is_critical_false_pass is False

    def test_calibration_report_valid(self):
        report = CalibrationReport(
            dataset_version=CALIBRATION_DATASET_VERSION,
            rubric_version=CALIBRATION_RUBRIC_VERSION,
            judge_prompt_version=JUDGE_PROMPT_VERSION,
            dataset_size=50,
            decision_metrics={"accuracy": 0.92},
            risk_metrics={"false_accept_rate": 0.04, "critical_false_pass_rate": 0.0},
            score_metrics={"mae": 0.08},
            category_breakdown={"NORMAL": {"count": 10, "accuracy": 1.0}},
            human_human_agreement="NOT_AVAILABLE",
            bias_report={"verbosity": "PASS", "position": "NOT_APPLICABLE"},
            sentinel_report={"total": 9, "passed": 9, "status": "PASS"},
            offline_status="OFFLINE",
            privacy_status="SECURE",
        )
        assert report.dataset_size == 50
        assert report.human_human_agreement == "NOT_AVAILABLE"
