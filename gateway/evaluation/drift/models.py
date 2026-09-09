# -*- coding: utf-8 -*-
"""
gateway.evaluation.drift.models
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Judge Drift Detection Contracts & Models
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DriftType(str, Enum):
    """漂移类型枚举"""
    DECISION_DRIFT = "DECISION_DRIFT"
    SCORE_DRIFT = "SCORE_DRIFT"
    RISK_DRIFT = "RISK_DRIFT"
    FAILURE_DRIFT = "FAILURE_DRIFT"


class DriftStatus(str, Enum):
    """漂移状态结论"""
    NO_DRIFT = "NO_DRIFT"
    ALERT = "ALERT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class DriftAlert(BaseModel):
    """单项漂移告警信封"""
    model_config = ConfigDict(extra="forbid")

    drift_type: DriftType = Field(..., description="漂移类型")
    metric_name: str = Field(..., description="触发漂移的指标名称")
    baseline_value: float = Field(..., description="基线值")
    current_value: float = Field(..., description="当前值")
    delta: float = Field(..., description="偏离差值绝对值")
    threshold: float = Field(..., description="工程告警阈值")
    severity: str = Field(default="WARNING", description="严重级别 (WARNING / CRITICAL)")
    reason: str = Field(..., description="告警原因与说明")


class DriftBaseline(BaseModel):
    """
    Judge 质量与指标基线契约 (基于 G3 评测沉淀)
    """
    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="g4.0", description="基线版本代号")
    accept_rate: float = Field(default=0.52, ge=0.0, le=1.0, description="基线采纳率")
    review_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="基线复核率")
    reject_rate: float = Field(default=0.48, ge=0.0, le=1.0, description="基线拒绝率")
    average_score: float = Field(default=0.70, ge=0.0, le=1.0, description="基线平均分")
    score_variance: float = Field(default=0.05, ge=0.0, description="基线分值方差")
    critical_false_pass_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="基线关键缺陷误放行率")
    failure_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="基线执行失败率")
    average_latency_ms: float = Field(default=50.0, ge=0.0, description="基线平均耗时(ms)")


class DriftMetricReport(BaseModel):
    """
    漂移检测综合评估报告
    """
    model_config = ConfigDict(extra="forbid")

    status: DriftStatus = Field(..., description="综合漂移判定状态")
    baseline_version: str = Field(default="g4.0")
    current_metrics: Dict[str, Any] = Field(default_factory=dict, description="当前批次运行时指标")
    alerts: List[DriftAlert] = Field(default_factory=list, description="触发的漂移告警列表")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细差异比对数据")
