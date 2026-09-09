# -*- coding: utf-8 -*-
"""
gateway.tests.test_g4_drift
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Judge Drift Detection Test Suite (G4-D1 ~ G4-D8)
"""

import copy
import pytest

from gateway.evaluation.calibration.dataset import load_calibration_dataset
from gateway.evaluation.drift.baseline import load_default_drift_baseline
from gateway.evaluation.drift.detector import JudgeDriftDetector
from gateway.evaluation.drift.models import DriftBaseline, DriftStatus, DriftType


@pytest.fixture
def detector():
    return JudgeDriftDetector(
        decision_rate_threshold=0.15,
        score_mean_threshold=0.15,
        critical_false_pass_threshold=0.001,
        failure_rate_threshold=0.10,
        latency_delta_threshold_ms=200.0,
    )


@pytest.fixture
def baseline():
    return load_default_drift_baseline()


class TestG4Drift:
    def test_g4_d1_baseline_creation(self, baseline):
        """G4-D1: 验证默认漂移基线模型与版本契约"""
        assert isinstance(baseline, DriftBaseline)
        assert baseline.version == "g4.0"
        assert 0.0 <= baseline.accept_rate <= 1.0
        assert baseline.critical_false_pass_rate == 0.0

    def test_g4_d2_decision_drift(self, detector, baseline):
        """G4-D2: 决策采纳率显著偏离时触发 DECISION_DRIFT 告警"""
        report = detector.detect_drift(
            {"accept_rate": baseline.accept_rate + 0.25}, baseline
        )
        assert report.status != DriftStatus.NO_DRIFT
        alerts = [a for a in report.alerts if a.drift_type == DriftType.DECISION_DRIFT]
        assert len(alerts) == 1
        assert alerts[0].metric_name == "accept_rate"

    def test_g4_d3_score_drift(self, detector, baseline):
        """G4-D3: 平均分偏离基线超过阈值触发 SCORE_DRIFT 告警"""
        report = detector.detect_drift(
            {"average_score": baseline.average_score - 0.20}, baseline
        )
        alerts = [a for a in report.alerts if a.drift_type == DriftType.SCORE_DRIFT]
        assert len(alerts) == 1
        assert alerts[0].metric_name == "average_score"

    def test_g4_d4_critical_false_pass_drift(self, detector, baseline):
        """G4-D4: 关键缺陷漏放率微量上涌直接触发 REVIEW_REQUIRED (CRITICAL) 告警"""
        report = detector.detect_drift(
            {"critical_false_pass_rate": 0.02}, baseline
        )
        assert report.status == DriftStatus.REVIEW_REQUIRED
        alerts = [a for a in report.alerts if a.drift_type == DriftType.RISK_DRIFT]
        assert len(alerts) == 1
        assert alerts[0].severity == "CRITICAL"

    def test_g4_d5_latency_drift(self, detector, baseline):
        """G4-D5: 耗时异常暴涨触发耗时漂移告警"""
        report = detector.detect_drift(
            {"average_latency_ms": baseline.average_latency_ms + 350.0}, baseline
        )
        alerts = [a for a in report.alerts if a.metric_name == "average_latency_ms"]
        assert len(alerts) == 1

    def test_g4_d6_failure_rate_drift(self, detector, baseline):
        """G4-D6: 接口错误率上涨触发 FAILURE_DRIFT 告警"""
        report = detector.detect_drift(
            {"failure_rate": 0.15}, baseline
        )
        alerts = [a for a in report.alerts if a.drift_type == DriftType.FAILURE_DRIFT and a.metric_name == "failure_rate"]
        assert len(alerts) == 1

    def test_g4_d7_no_false_alert_on_normal_variation(self, detector, baseline):
        """G4-D7: 在正常阈值容差范围内波动不产生误告警"""
        report = detector.detect_drift(
            {
                "accept_rate": baseline.accept_rate + 0.03,  # < 0.15
                "average_score": baseline.average_score - 0.04,  # < 0.15
                "critical_false_pass_rate": 0.0,
                "failure_rate": 0.02,  # < 0.10
                "average_latency_ms": baseline.average_latency_ms + 30.0,  # < 200ms
            },
            baseline,
        )
        assert report.status == DriftStatus.NO_DRIFT
        assert len(report.alerts) == 0

    def test_g4_d8_drift_does_not_mutate_production_state(self, detector, baseline):
        """G4-D8: 漂移计算过程完全只读，不修改基线对象或任何外部环境"""
        base_dump_before = copy.deepcopy(baseline.model_dump())
        _ = detector.detect_drift({"accept_rate": 0.99, "critical_false_pass_rate": 0.5}, baseline)
        base_dump_after = baseline.model_dump()
        assert base_dump_before == base_dump_after
