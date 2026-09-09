# -*- coding: utf-8 -*-
"""
gateway.evaluation.calibration.models
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Calibration Domain & Dataset Models
"""

from enum import Enum
import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from gateway.evaluation.judge.models import JudgeDecision
from gateway.models import LearningPromptContext, StructuredAIResponse

CALIBRATION_DATASET_VERSION: str = "g3-cp3.0"
CALIBRATION_RUBRIC_VERSION: str = "g3.0"
JUDGE_PROMPT_VERSION: str = "g3.0"


class CalibrationCategory(str, Enum):
    """校准用例分类"""
    NORMAL = "NORMAL"
    LOW_MASTERY = "LOW_MASTERY"
    HIGH_MASTERY = "HIGH_MASTERY"
    BOUNDARY = "BOUNDARY"
    SAFETY = "SAFETY"
    FACT_CRITICAL = "FACT_CRITICAL"
    ADVERSARIAL = "ADVERSARIAL"
    OFF_TOPIC = "OFF_TOPIC"


class CalibrationRiskLevel(str, Enum):
    """风险等级"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CalibrationExpectedDecision(str, Enum):
    """期望决策倾向"""
    CLEAR_ACCEPT = "CLEAR_ACCEPT"
    GOOD_BUT_IMPERFECT = "GOOD_BUT_IMPERFECT"
    BORDERLINE = "BORDERLINE"
    CLEAR_REJECT = "CLEAR_REJECT"
    SAFETY_CRITICAL = "SAFETY_CRITICAL"
    FACT_CRITICAL = "FACT_CRITICAL"
    OFF_TOPIC = "OFF_TOPIC"


class ConfidenceLevel(str, Enum):
    """人工标注置信度"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CalibrationCase(BaseModel):
    """校准用例强类型定义"""
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., description="全局唯一用例标识符")
    category: CalibrationCategory = Field(..., description="校准类别")
    risk_level: CalibrationRiskLevel = Field(..., description="风险等级")
    context: LearningPromptContext = Field(..., description="学情上下文")
    candidate_response: StructuredAIResponse = Field(..., description="待评估 AI 候选回答")
    expected_decision: CalibrationExpectedDecision = Field(..., description="期望决策倾向")
    critical_failure: bool = Field(default=False, description="是否属于关键安全/事实阻断项")
    expected_violations: List[str] = Field(default_factory=list, description="预期应捕获的违规标记")
    notes: Optional[str] = Field(default=None, description="用例备注说明")


class HumanLabel(BaseModel):
    """人工黄金标注契约"""
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., description="关联校准用例 ID")
    annotator_id: str = Field(..., description="标注人员代号")
    pedagogical_value: float = Field(..., ge=0.0, le=1.0, description="教学价值打分 [0.0, 1.0]")
    explanation_depth: float = Field(..., ge=0.0, le=1.0, description="解释深度打分 [0.0, 1.0]")
    tone_appropriateness: float = Field(..., ge=0.0, le=1.0, description="语气得体打分 [0.0, 1.0]")
    guidance_clarity: float = Field(..., ge=0.0, le=1.0, description="引导清晰打分 [0.0, 1.0]")
    overall_quality: float = Field(..., ge=0.0, le=1.0, description="综合质量打分 [0.0, 1.0]")
    decision: JudgeDecision = Field(..., description="人工判定裁决: ACCEPT / REVIEW / REJECT")
    confidence: ConfidenceLevel = Field(..., description="人工置信度")
    critical_failure: bool = Field(default=False, description="是否包含不可容忍的关键缺陷")
    notes: Optional[str] = Field(default=None, description="人工复核备注")

    @field_validator(
        "pedagogical_value",
        "explanation_depth",
        "tone_appropriateness",
        "guidance_clarity",
        "overall_quality",
    )
    @classmethod
    def check_finite_score(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"Score cannot be NaN or Inf, got {v}")
        return v


class ComparisonResult(BaseModel):
    """单个用例的人机比对分析信封"""
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., description="用例编号")
    human_decision: JudgeDecision = Field(..., description="人工黄金判定")
    judge_decision: JudgeDecision = Field(..., description="Judge 判定")
    decision_match: bool = Field(..., description="裁决是否一致")
    human_scores: Dict[str, float] = Field(default_factory=dict, description="人工维度得分")
    judge_scores: Dict[str, float] = Field(default_factory=dict, description="Judge 维度得分")
    score_errors: Dict[str, float] = Field(default_factory=dict, description="各维度得分绝对误差")
    critical_failure_match: bool = Field(..., description="关键缺陷标记是否一致")
    is_critical_false_pass: bool = Field(default=False, description="是否发生关键缺陷错误放行")


class CalibrationReport(BaseModel):
    """校准总报告信封"""
    model_config = ConfigDict(extra="forbid")

    dataset_version: str = Field(default=CALIBRATION_DATASET_VERSION)
    rubric_version: str = Field(default=CALIBRATION_RUBRIC_VERSION)
    judge_prompt_version: str = Field(default=JUDGE_PROMPT_VERSION)
    dataset_size: int = Field(..., description="评测用例总数")
    decision_metrics: Dict[str, Any] = Field(default_factory=dict, description="裁决一致性指标")
    risk_metrics: Dict[str, Any] = Field(default_factory=dict, description="风险控制指标 (FAR, FRR, Critical False-Pass)")
    score_metrics: Dict[str, Any] = Field(default_factory=dict, description="分值 MAE 及相关性")
    category_breakdown: Dict[str, Any] = Field(default_factory=dict, description="分类别细分指标")
    human_human_agreement: str = Field(default="NOT_AVAILABLE", description="人人一致性说明")
    bias_report: Dict[str, Any] = Field(default_factory=dict, description="偏见审计报告")
    sentinel_report: Dict[str, Any] = Field(default_factory=dict, description="底线 Sentinel 检验报告")
    offline_status: str = Field(default="OFFLINE", description="网络隔离状态")
    privacy_status: str = Field(default="SECURE", description="脱敏合规状态")
