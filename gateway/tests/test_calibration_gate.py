# -*- coding: utf-8 -*-
"""
gateway.tests.test_calibration_gate
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Calibration Analyzer & Gate Test Suite
"""

import subprocess
import sys
from pathlib import Path
import pytest

from gateway.evaluation.calibration.analyzer import run_calibration
from gateway.evaluation.calibration.models import (
    CALIBRATION_DATASET_VERSION,
    CALIBRATION_RUBRIC_VERSION,
    JUDGE_PROMPT_VERSION,
    CalibrationReport,
)
from gateway.evaluation.judge.adapter import JudgeAdapter
from gateway.evaluation.judge.fake import FakeLLMJudge
from gateway.evaluation.judge.fusion import EvaluationFusionEngine
from gateway.evaluation.judge.models import JudgeDecision
from gateway.evaluation.validator import validate_ai_response
from gateway.evaluation.calibration.dataset import load_sentinel_cases

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestCalibrationGate:
    def test_run_calibration_pipeline(self):
        judge = FakeLLMJudge(forced_mode="HIGH", forced_confidence=0.9)
        adapter = JudgeAdapter(judge=judge)

        report = run_calibration(judge_adapter=adapter)
        assert isinstance(report, CalibrationReport)
        assert report.dataset_version == CALIBRATION_DATASET_VERSION
        assert report.rubric_version == CALIBRATION_RUBRIC_VERSION
        assert report.judge_prompt_version == JUDGE_PROMPT_VERSION
        assert report.dataset_size == 50

        # Decision metrics presence
        assert "accuracy" in report.decision_metrics
        assert "precision" in report.decision_metrics
        assert "recall" in report.decision_metrics
        assert "f1" in report.decision_metrics
        assert "confusion_matrix" in report.decision_metrics

        # Risk metrics presence
        assert "false_accept_rate" in report.risk_metrics
        assert "false_reject_rate" in report.risk_metrics
        assert "critical_false_pass_rate" in report.risk_metrics
        assert "critical_recall" in report.risk_metrics

        # Bias report presence
        assert "verbosity_bias" in report.bias_report
        assert report.bias_report["position_bias"]["status"] == "NOT_APPLICABLE"
        assert report.bias_report["self_preference"]["status"] == "NOT_AVAILABLE"

        # Sentinel report presence
        assert report.sentinel_report["status"] == "PASS"
        assert report.sentinel_report["passed"] >= 9

    def test_sentinel_g1_supremacy_unbreakable(self):
        # Even with an adversarial judge forced to return perfect ACCEPT
        adv_judge = FakeLLMJudge(forced_mode="HIGH", forced_confidence=0.99)
        adapter = JudgeAdapter(judge=adv_judge)
        engine = EvaluationFusionEngine()

        sentinels = load_sentinel_cases()
        for s in sentinels:
            det_res = validate_ai_response(s.context, s.candidate_response)
            j_res, failure = adapter.evaluate_safe(s.context, s.candidate_response)
            fusion_res = engine.fuse(det_res, j_res, failure)

            # Assert G1 rejects and Fusion rejects
            assert det_res.valid is False or det_res.policy_compliant is False or det_res.factual_consistency is False
            assert fusion_res.decision == JudgeDecision.REJECT
            assert fusion_res.final_valid is False

    def test_calibration_gate_script_execution(self):
        gate_script = PROJECT_ROOT / "scripts" / "ai_judge_calibration_gate.py"
        res = subprocess.run(
            [sys.executable, str(gate_script)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res.returncode == 0, f"Gate script failed with output:\n{res.stdout}\n{res.stderr}"
        assert "CALIBRATION INFRASTRUCTURE GATE: PASS" in res.stdout
