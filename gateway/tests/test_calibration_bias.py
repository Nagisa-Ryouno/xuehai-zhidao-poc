# -*- coding: utf-8 -*-
"""
gateway.tests.test_calibration_bias
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Bias Audit Test Suite
"""

import pytest

from gateway.evaluation.calibration.bias import (
    audit_verbosity_bias,
    audit_position_bias,
    audit_style_bias,
    audit_self_preference,
    run_full_bias_audit,
)
from gateway.evaluation.judge.adapter import JudgeAdapter
from gateway.evaluation.judge.fake import FakeLLMJudge


class TestCalibrationBias:
    def test_position_bias_not_applicable(self):
        result = audit_position_bias()
        assert result["status"] == "NOT_APPLICABLE"
        assert "pointwise" in result["reason"].lower()

    def test_self_preference_not_available(self):
        result = audit_self_preference()
        assert result["status"] == "NOT_AVAILABLE"
        assert "generator" in result["reason"].lower()

    def test_verbosity_bias_detection(self):
        # Fake judge returns deterministic high scores
        judge = FakeLLMJudge(forced_mode="HIGH", forced_confidence=0.9)
        adapter = JudgeAdapter(judge=judge)

        result = audit_verbosity_bias(adapter)
        assert "short_score" in result
        assert "long_score" in result
        assert "delta" in result
        assert "bias_detected" in result
        assert 0.0 <= result["short_score"] <= 1.0
        assert 0.0 <= result["long_score"] <= 1.0

    def test_style_bias_detection(self):
        judge = FakeLLMJudge(forced_mode="HIGH", forced_confidence=0.9)
        adapter = JudgeAdapter(judge=judge)

        result = audit_style_bias(adapter)
        assert "style_scores" in result
        assert "formal" in result["style_scores"]
        assert "casual" in result["style_scores"]
        assert "concise" in result["style_scores"]
        assert "verbose" in result["style_scores"]
        assert "max_delta" in result
        assert "bias_detected" in result

    def test_run_full_bias_audit(self):
        judge = FakeLLMJudge(forced_mode="HIGH", forced_confidence=0.9)
        adapter = JudgeAdapter(judge=judge)

        full_audit = run_full_bias_audit(adapter)
        assert "verbosity_bias" in full_audit
        assert "position_bias" in full_audit
        assert "style_bias" in full_audit
        assert "self_preference" in full_audit
        assert full_audit["position_bias"]["status"] == "NOT_APPLICABLE"
        assert full_audit["self_preference"]["status"] == "NOT_AVAILABLE"
