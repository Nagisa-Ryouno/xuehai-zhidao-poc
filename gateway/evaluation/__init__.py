# -*- coding: utf-8 -*-
"""
gateway.evaluation
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G1: AI Semantic Validation & Evaluation — Offline Evaluation Foundation
"""

from gateway.evaluation.models import (
    EvaluationCategory,
    EvaluationCase,
    SemanticValidationResult,
    CaseEvaluationResult,
    EvaluationReport,
)
from gateway.evaluation.validator import (
    VALIDATOR_VERSION,
    FORBIDDEN_BEHAVIOR,
    validate_ai_response,
)
from gateway.evaluation.dataset import (
    DATASET_VERSION,
    load_evaluation_dataset,
    get_dataset_summary,
)
from gateway.evaluation.evaluator import (
    evaluate_case,
    run_evaluation_suite,
)

__all__ = [
    "EvaluationCategory",
    "EvaluationCase",
    "SemanticValidationResult",
    "CaseEvaluationResult",
    "EvaluationReport",
    "VALIDATOR_VERSION",
    "FORBIDDEN_BEHAVIOR",
    "validate_ai_response",
    "DATASET_VERSION",
    "load_evaluation_dataset",
    "get_dataset_summary",
    "evaluate_case",
    "run_evaluation_suite",
]
