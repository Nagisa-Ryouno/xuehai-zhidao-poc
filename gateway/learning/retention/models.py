# -*- coding: utf-8 -*-
"""
gateway.learning.retention.models
=================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-F
学习保持度验证与间隔复习建议数据模型 (Retention Check Models)

设计规范与安全红线：
1. 确定性 4 档状态机枚举：INSUFFICIENT_DATA, NOT_DUE, DUE_FOR_REVIEW, NEEDS_REINFORCEMENT；
2. 建议动作白名单控制：只能来自 REVIEW_CONCEPT, RETAKE_QUIZ, VIEW_PROGRESS 或 None，禁止自由生成；
3. 事实字段强校验：支持 last_learning_at, days_since_learning, current_mastery 序列化。
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Set
from pydantic import BaseModel, Field, field_validator


class RetentionStatus(str, Enum):
    """保持度判断 4 档确定性状态"""
    NOT_DUE = "NOT_DUE"
    DUE_FOR_REVIEW = "DUE_FOR_REVIEW"
    NEEDS_REINFORCEMENT = "NEEDS_REINFORCEMENT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


ALLOWED_RETENTION_ACTIONS: Set[str] = {
    "REVIEW_CONCEPT",
    "RETAKE_QUIZ",
    "VIEW_PROGRESS",
}


class RetentionProfile(BaseModel):
    """学生针对特定考点的学习保持度档案与复习建议契约"""
    student_id: str = Field(..., description="学生唯一编号")
    knowledge_id: str = Field(..., description="考点唯一编号")
    last_learning_at: Optional[datetime] = Field(None, description="最近一次正式学习完成时间")
    days_since_learning: Optional[int] = Field(None, description="距离最近一次学习经过的天数 (非负整数)")
    current_mastery: Optional[float] = Field(None, description="服务端权威当前 BKT 掌握度 P(L)")
    retention_status: RetentionStatus = Field(..., description="保持度判定状态")
    should_review: bool = Field(False, description="是否建议进行复习/复测")
    suggested_action: Optional[str] = Field(None, description="建议执行的动作（受白名单严格约束）")

    @field_validator("suggested_action")
    @classmethod
    def validate_suggested_action(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_RETENTION_ACTIONS:
            raise ValueError(f"suggested_action 必须来自白名单 {ALLOWED_RETENTION_ACTIONS}，收到: {v}")
        return v
