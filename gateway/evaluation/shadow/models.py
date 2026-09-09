# -*- coding: utf-8 -*-
"""
gateway.evaluation.shadow.models
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Shadow Evaluation Contracts & Records
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


FORBIDDEN_SHADOW_PATTERNS: List[str] = [
    "sk-",
    "bearer ",
    "13800138000",
    "password",
    "authorization",
    "secret_key",
    "api_key=",
]


class ShadowEvaluationRecord(BaseModel):
    """
    Shadow 旁路评测只读审计记录 (Shadow Evaluation Record)

    安全红线：
    绝对禁止持久化真实密钥、未脱敏 PII 或破坏生产决策与学习状态。
    """
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., description="评测用例唯一编号")
    g1_result: Dict[str, Any] = Field(..., description="G1 确定性底座判定镜像")
    judge_result: Optional[Dict[str, Any]] = Field(default=None, description="Shadow Judge 结构化结果")
    fusion_result: Dict[str, Any] = Field(..., description="生产融合决策镜像（不可变）")
    judge_provider: str = Field(..., description="Judge 提供方名称")
    judge_model: str = Field(..., description="Judge 模型代号")
    prompt_version: str = Field(default="g3.0", description="Prompt 版本")
    rubric_version: str = Field(default="g3.0", description="Rubric 版本")
    latency_ms: float = Field(..., ge=0.0, description="Judge 端到端延迟(毫秒)")
    failure_class: str = Field(default="NONE", description="故障分类")
    timestamp: str = Field(..., description="UTC 时间戳")

    @model_validator(mode="after")
    def verify_no_secrets_or_pii(self) -> "ShadowEvaluationRecord":
        raw_repr = self.model_dump_json().lower()
        for pat in FORBIDDEN_SHADOW_PATTERNS:
            if pat in raw_repr:
                raise ValueError(f"Shadow record contains sensitive pattern: '{pat}'")
        return self
