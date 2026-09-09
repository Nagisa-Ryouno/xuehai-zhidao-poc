# -*- coding: utf-8 -*-
"""
gateway.evaluation.calibration
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: AI Judge Calibration Domain
"""

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
from gateway.evaluation.calibration.dataset import (
    load_calibration_dataset,
    load_human_labels,
    load_sentinel_cases,
    DEFAULT_CALIBRATION_FIXTURES_DIR,
)
from gateway.evaluation.calibration.metrics import (
    calculate_decision_metrics,
    calculate_risk_metrics,
    calculate_score_metrics,
    calculate_category_breakdown,
    calculate_human_agreement,
)
from gateway.evaluation.calibration.bias import (
    audit_verbosity_bias,
    audit_position_bias,
    audit_style_bias,
    audit_self_preference,
    run_full_bias_audit,
)
from gateway.evaluation.calibration.analyzer import run_calibration

__all__ = [
    "CALIBRATION_DATASET_VERSION",
    "CALIBRATION_RUBRIC_VERSION",
    "JUDGE_PROMPT_VERSION",
    "CalibrationCategory",
    "CalibrationExpectedDecision",
    "CalibrationRiskLevel",
    "ConfidenceLevel",
    "CalibrationCase",
    "HumanLabel",
    "ComparisonResult",
    "CalibrationReport",
    "load_calibration_dataset",
    "load_human_labels",
    "load_sentinel_cases",
    "DEFAULT_CALIBRATION_FIXTURES_DIR",
    "calculate_decision_metrics",
    "calculate_risk_metrics",
    "calculate_score_metrics",
    "calculate_category_breakdown",
    "calculate_human_agreement",
    "audit_verbosity_bias",
    "audit_position_bias",
    "audit_style_bias",
    "audit_self_preference",
    "run_full_bias_audit",
    "run_calibration",
]
