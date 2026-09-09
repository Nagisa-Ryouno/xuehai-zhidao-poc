# -*- coding: utf-8 -*-
"""
gateway.evaluation.drift.baseline
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Default Drift Baseline (默认质量漂移基线)
"""

from gateway.evaluation.drift.models import DriftBaseline

# 默认工程参考基线 (基于 G3 黄金校准集沉淀)
DEFAULT_DRIFT_BASELINE = DriftBaseline(
    version="g4.0",
    accept_rate=0.52,
    review_rate=0.00,
    reject_rate=0.48,
    average_score=0.70,
    score_variance=0.05,
    critical_false_pass_rate=0.00,
    failure_rate=0.00,
    average_latency_ms=50.0,
)


def load_default_drift_baseline() -> DriftBaseline:
    """获取默认漂移评测基线"""
    return DEFAULT_DRIFT_BASELINE.model_copy()
