# -*- coding: utf-8 -*-
"""
gateway.evaluation.judge.runtime
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Judge Runtime Policy (受控运行时配置与安全策略)

设计原则：
1. 默认安全关闭：enabled=False, allow_production_decision=False 强制不可覆写
2. 绝对零业务决策权：任何尝试 allow_production_decision=True 立即抛出异常阻断
3. 严格白名单与有界约束：extra="forbid"，超时时间 [0.1, 30.0] 必须有界
"""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

SHADOW_SCHEMA_VERSION: str = "g4.0"
RUNTIME_POLICY_VERSION: str = "g4.0"
DRIFT_POLICY_VERSION: str = "g4.0"


class JudgeRuntimePolicy(BaseModel):
    """
    Judge 运行时受控策略契约 (严格白名单，默认完全离线静默)
    """
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=False, description="是否启用 Judge 运行时")
    shadow_only: bool = Field(default=True, description="必须为 True，仅作为旁路观测")
    allow_production_decision: bool = Field(
        default=False, description="绝对禁止为 True，严禁参与生产业务决策"
    )
    provider: str = Field(default="mock", description="Judge 提供商标识")
    model: str = Field(default="mock-judge", description="Judge 模型代号")
    timeout_seconds: float = Field(default=5.0, description="单次请求最大超时秒数 [0.1, 30.0]")
    max_requests_per_minute: int = Field(default=60, gt=0, description="每分钟最大请求限额")
    max_daily_requests: int = Field(default=1000, gt=0, description="单日最大请求限额")
    failure_mode: Literal["DEGRADE_TO_REVIEW", "SKIP"] = Field(
        default="DEGRADE_TO_REVIEW", description="故障降级策略"
    )
    version: str = Field(default=RUNTIME_POLICY_VERSION, description="策略规范版本")

    @field_validator("allow_production_decision")
    @classmethod
    def reject_production_decision(cls, v: bool) -> bool:
        if v is True:
            raise ValueError("JUDGE_PRODUCTION_DECISION_FORBIDDEN")
        return v

    @field_validator("shadow_only")
    @classmethod
    def enforce_shadow_only(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("SHADOW_ONLY_MANDATORY: Judge runtime must be shadow-only")
        return v

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout_bounded(cls, v: float) -> float:
        if not (0.1 <= v <= 30.0):
            raise ValueError(f"timeout_seconds must be in [0.1, 30.0], got {v}")
        return v
