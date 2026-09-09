# -*- coding: utf-8 -*-
"""
gateway.evaluation.drift.detector
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Judge Drift Detector (裁判模型质量漂移检测器)

重要设计原则：
1. 观察者语义：Drift Detector 只能度量、告警与触发复核，绝对无权修改生产决策或学习路径
2. 明确的工程阈值标注：阈值均为工程初始基准 (ENGINEERING_DEFAULT)，非虚构统计定理
3. 零误报设计：支持微小容差与零除安全防御
"""

from typing import Any, Dict, List, Optional

from gateway.evaluation.drift.baseline import load_default_drift_baseline
from gateway.evaluation.drift.models import (
    DriftAlert,
    DriftBaseline,
    DriftMetricReport,
    DriftStatus,
    DriftType,
)


class JudgeDriftDetector:
    """
    LLM Judge 质量、分布与风险漂移检测器
    """

    def __init__(
        self,
        decision_rate_threshold: float = 0.15,
        score_mean_threshold: float = 0.15,
        critical_false_pass_threshold: float = 0.001,
        failure_rate_threshold: float = 0.10,
        latency_delta_threshold_ms: float = 200.0,
    ):
        # 明确标注阈值属性为工程初始默认值 (ENGINEERING_DEFAULT)
        self.decision_rate_threshold = decision_rate_threshold
        self.score_mean_threshold = score_mean_threshold
        self.critical_false_pass_threshold = critical_false_pass_threshold
        self.failure_rate_threshold = failure_rate_threshold
        self.latency_delta_threshold_ms = latency_delta_threshold_ms

    def detect_drift(
        self,
        current_metrics: Dict[str, Any],
        baseline: Optional[DriftBaseline] = None,
    ) -> DriftMetricReport:
        """
        对比当前运行时指标与参考基线，输出漂移评估报告
        """
        base = baseline or load_default_drift_baseline()
        alerts: List[DriftAlert] = []

        # 1. 决策漂移检测 (Decision Drift)
        curr_accept_rate = float(current_metrics.get("accept_rate", base.accept_rate))
        delta_accept = abs(curr_accept_rate - base.accept_rate)
        if delta_accept > self.decision_rate_threshold:
            alerts.append(
                DriftAlert(
                    drift_type=DriftType.DECISION_DRIFT,
                    metric_name="accept_rate",
                    baseline_value=base.accept_rate,
                    current_value=curr_accept_rate,
                    delta=round(delta_accept, 4),
                    threshold=self.decision_rate_threshold,
                    severity="WARNING",
                    reason=f"[ENGINEERING_DEFAULT] Accept rate shifted by {delta_accept:.4f} > {self.decision_rate_threshold}",
                )
            )

        # 2. 分值均值漂移检测 (Score Drift)
        curr_avg_score = float(current_metrics.get("average_score", base.average_score))
        delta_score = abs(curr_avg_score - base.average_score)
        if delta_score > self.score_mean_threshold:
            alerts.append(
                DriftAlert(
                    drift_type=DriftType.SCORE_DRIFT,
                    metric_name="average_score",
                    baseline_value=base.average_score,
                    current_value=curr_avg_score,
                    delta=round(delta_score, 4),
                    threshold=self.score_mean_threshold,
                    severity="WARNING",
                    reason=f"[ENGINEERING_DEFAULT] Average score shifted by {delta_score:.4f} > {self.score_mean_threshold}",
                )
            )

        # 3. 关键风险漂移检测 (Risk Drift: Critical False Pass - 零容忍级别)
        curr_crit_fp = float(current_metrics.get("critical_false_pass_rate", base.critical_false_pass_rate))
        delta_crit_fp = abs(curr_crit_fp - base.critical_false_pass_rate)
        if delta_crit_fp > self.critical_false_pass_threshold:
            alerts.append(
                DriftAlert(
                    drift_type=DriftType.RISK_DRIFT,
                    metric_name="critical_false_pass_rate",
                    baseline_value=base.critical_false_pass_rate,
                    current_value=curr_crit_fp,
                    delta=round(delta_crit_fp, 4),
                    threshold=self.critical_false_pass_threshold,
                    severity="CRITICAL",
                    reason=f"[CRITICAL_DRIFT] Critical false pass rate surged by {delta_crit_fp:.4f} > {self.critical_false_pass_threshold}",
                )
            )

        # 4. 故障与网络漂移检测 (Failure Drift)
        curr_fail_rate = float(current_metrics.get("failure_rate", base.failure_rate))
        delta_fail = abs(curr_fail_rate - base.failure_rate)
        if delta_fail > self.failure_rate_threshold:
            alerts.append(
                DriftAlert(
                    drift_type=DriftType.FAILURE_DRIFT,
                    metric_name="failure_rate",
                    baseline_value=base.failure_rate,
                    current_value=curr_fail_rate,
                    delta=round(delta_fail, 4),
                    threshold=self.failure_rate_threshold,
                    severity="WARNING",
                    reason=f"[ENGINEERING_DEFAULT] Failure rate shifted by {delta_fail:.4f} > {self.failure_rate_threshold}",
                )
            )

        # 5. 耗时漂移检测 (Latency Drift)
        curr_latency = float(current_metrics.get("average_latency_ms", base.average_latency_ms))
        delta_latency = abs(curr_latency - base.average_latency_ms)
        if delta_latency > self.latency_delta_threshold_ms:
            alerts.append(
                DriftAlert(
                    drift_type=DriftType.FAILURE_DRIFT,
                    metric_name="average_latency_ms",
                    baseline_value=base.average_latency_ms,
                    current_value=curr_latency,
                    delta=round(delta_latency, 2),
                    threshold=self.latency_delta_threshold_ms,
                    severity="WARNING",
                    reason=f"[ENGINEERING_DEFAULT] Latency delta {delta_latency:.2f}ms > {self.latency_delta_threshold_ms}ms",
                )
            )

        # 综合状态推导
        if not alerts:
            status = DriftStatus.NO_DRIFT
        elif any(a.severity == "CRITICAL" for a in alerts):
            status = DriftStatus.REVIEW_REQUIRED
        else:
            status = DriftStatus.ALERT

        return DriftMetricReport(
            status=status,
            baseline_version=base.version,
            current_metrics=current_metrics,
            alerts=alerts,
            details={
                "delta_accept_rate": round(delta_accept, 4),
                "delta_average_score": round(delta_score, 4),
                "delta_critical_false_pass": round(delta_crit_fp, 4),
                "delta_failure_rate": round(delta_fail, 4),
                "delta_latency_ms": round(delta_latency, 2),
            },
        )
