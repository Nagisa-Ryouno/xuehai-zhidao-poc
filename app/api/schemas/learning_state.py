# -*- coding: utf-8 -*-
"""
app.api.schemas.learning_state
动态 BKT 学情认知状态与事件演进 DTO 模型
"""

from typing import Optional
from pydantic import BaseModel, Field


class BKTStateResponse(BaseModel):
    """单知识点 BKT 动态认知掌握度响应"""
    student_id: str
    knowledge_id: str
    mastery_probability: float = Field(..., description="掌握概率 P(L), 范围 [0.0, 1.0]")
    mastery_percent: float = Field(..., description="掌握概率百分比 (0~100)")
    attempts: int = Field(default=0, description="累计作答次数")
    correct_attempts: int = Field(default=0, description="正确作答次数")
    incorrect_attempts: int = Field(default=0, description="错误作答次数")
    consecutive_correct: int = Field(default=0, description="连续正确次数")
    consecutive_incorrect: int = Field(default=0, description="连续错误次数")
    last_updated: Optional[str] = Field(default=None, description="最近更新时间 (ISO-8601)")
    last_event_id: Optional[str] = Field(default=None, description="最近关联事件 ID")


class LearningStateUpdateRequest(BaseModel):
    """基于事件驱动状态更新请求"""
    event_id: str = Field(..., min_length=1, description="待消费的学习行为事件 ID")


class LearningStateUpdateResponse(BaseModel):
    """状态更新演进响应"""
    status: str = Field(..., description="处理状态 (updated / duplicate / error / skipped)")
    event_id: str
    student_id: Optional[str] = None
    knowledge_id: Optional[str] = None
    before: Optional[float] = None
    after: Optional[float] = None
    changed: bool = False
    reason: Optional[str] = None
