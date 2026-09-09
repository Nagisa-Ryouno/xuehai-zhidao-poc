# -*- coding: utf-8 -*-
"""
gateway.evaluation.review.models
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Human Review Escalation Models & Contracts
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewReason(str, Enum):
    """人工复核触发原因枚举"""
    CRITICAL_DISAGREEMENT = "CRITICAL_DISAGREEMENT"
    HIGH_UNCERTAINTY = "HIGH_UNCERTAINTY"
    JUDGE_FAILURE = "JUDGE_FAILURE"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    G1_JUDGE_DISAGREEMENT = "G1_JUDGE_DISAGREEMENT"


FORBIDDEN_REVIEW_PATTERNS: List[str] = [
    "sk-",
    "bearer ",
    "13800138000",
    "password",
    "authorization",
    "secret_key",
    "api_key=",
]


class HumanReviewItem(BaseModel):
    """
    人工复核升级工单契约
    安全红线：严格禁止包含任何 API Key、Authorization Header、原始未脱敏学生身份与密码凭证。
    """
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(..., description="复核工单全局唯一 ID")
    case_id: str = Field(..., description="关联评测用例标识")
    reason: ReviewReason = Field(..., description="升级复核触发原因")
    risk_level: str = Field(default="MEDIUM", description="风险等级 (LOW / MEDIUM / HIGH / CRITICAL)")
    g1_decision: str = Field(..., description="G1 确定性底座裁决 (ACCEPT / REJECT)")
    judge_decision: str = Field(..., description="Judge 建议裁决 (ACCEPT / REVIEW / REJECT)")
    judge_scores: Dict[str, float] = Field(default_factory=dict, description="Judge 维度打分快照")
    sanitized_context_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="脱敏学情上下文元数据 (仅含考点代号、名称等客观事实)"
    )
    prompt_version: str = Field(default="g3.0", description="Prompt 规范版本")
    rubric_version: str = Field(default="g3.0", description="评分细则规范版本")
    timestamp: str = Field(..., description="触发 UTC 时间戳")

    @model_validator(mode="after")
    def verify_no_secrets_or_pii(self) -> "HumanReviewItem":
        raw_repr = self.model_dump_json().lower()
        for pat in FORBIDDEN_REVIEW_PATTERNS:
            if pat in raw_repr:
                raise ValueError(f"Human review item contains forbidden sensitive pattern: '{pat}'")
        return self
