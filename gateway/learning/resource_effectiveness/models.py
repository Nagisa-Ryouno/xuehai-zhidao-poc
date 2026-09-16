# -*- coding: utf-8 -*-
"""
gateway.learning.resource_effectiveness.models
==============================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-E
资源学习效果档案与自适应分级领域模型 (Resource Effectiveness Profile Models)

设计规范与红线：
1. 确定性分级：根据 usage_count 与 average_delta 确定性划分 5 档效果等级，零随机零模糊；
2. 阈值边界严格断言：
   - usage_count < 2          -> INSUFFICIENT_DATA
   - average_delta >= 0.10     -> VERY_EFFECTIVE
   - 0.02 <= average_delta < 0.10 -> EFFECTIVE
   - -0.02 <= average_delta < 0.02 -> NEUTRAL
   - average_delta < -0.02    -> INEFFECTIVE
3. 零技术黑话：内部等级映射为确定性人本解释文案。
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class HistoricalEffectiveness(str, Enum):
    """历史资源效果等级枚举"""
    VERY_EFFECTIVE = "VERY_EFFECTIVE"
    EFFECTIVE = "EFFECTIVE"
    NEUTRAL = "NEUTRAL"
    INEFFECTIVE = "INEFFECTIVE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


ADJUSTMENT_SCORES: Dict[HistoricalEffectiveness, int] = {
    HistoricalEffectiveness.VERY_EFFECTIVE: 2,
    HistoricalEffectiveness.EFFECTIVE: 1,
    HistoricalEffectiveness.NEUTRAL: 0,
    HistoricalEffectiveness.INEFFECTIVE: -1,
    HistoricalEffectiveness.INSUFFICIENT_DATA: 0,
}


def classify_effectiveness(
    usage_count: int,
    average_delta: float,
) -> HistoricalEffectiveness:
    """
    确定性判定历史资源效果等级 (Pure Logic)
    """
    if usage_count < 2:
        return HistoricalEffectiveness.INSUFFICIENT_DATA

    avg = round(float(average_delta), 4)

    if avg >= 0.10:
        return HistoricalEffectiveness.VERY_EFFECTIVE
    elif avg >= 0.02:
        return HistoricalEffectiveness.EFFECTIVE
    elif avg >= -0.02:
        return HistoricalEffectiveness.NEUTRAL
    else:
        return HistoricalEffectiveness.INEFFECTIVE


class ResourceEffectivenessProfile(BaseModel):
    """学生针对特定考点下特定资源类型的历史效果档案实体"""
    student_id: str
    knowledge_id: str
    resource_type: str
    usage_count: int = Field(default=0, ge=0)
    average_delta: float = Field(default=0.0)
    last_delta: float = Field(default=0.0)
    effectiveness: HistoricalEffectiveness = Field(default=HistoricalEffectiveness.INSUFFICIENT_DATA)


class EffectivenessProfileResponse(BaseModel):
    """学生资源历史效果档案查询接口响应"""
    student_id: str
    knowledge_id: str
    profiles: List[ResourceEffectivenessProfile] = Field(default_factory=list)
