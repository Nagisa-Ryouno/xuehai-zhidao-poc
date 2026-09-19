# -*- coding: utf-8 -*-
"""
gateway.learning.today.models
=============================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-G
今日学习行动聚合 Lite 数据模型契约 (Today's Learning Action Models)

设计规范与安全红线：
1. 确定性 5 档行动类型枚举：REVIEW_RETENTION, CONTINUE_LEARNING, PRACTICE, VIEW_PROGRESS, NONE；
2. 单一行动聚合卡片结构：title, description, cta_label, priority_reason, knowledge_id, knowledge_name, suggested_action；
3. 纯只读数据契约，严格遵循 Pydantic V2 规范。
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TodayActionType(str, Enum):
    """今日学习行动 5 档枚举"""
    REVIEW_RETENTION = "REVIEW_RETENTION"
    CONTINUE_LEARNING = "CONTINUE_LEARNING"
    PRACTICE = "PRACTICE"
    VIEW_PROGRESS = "VIEW_PROGRESS"
    NONE = "NONE"


class TodayLearningAction(BaseModel):
    """今日学习行动结构体"""
    action_type: TodayActionType = Field(..., description="行动类型枚举")
    title: str = Field(..., description="行动标题（人类友好无黑话）")
    description: str = Field(..., description="行动描述文案")
    cta_label: str = Field(..., description="行动按钮文案")
    priority_reason: str = Field(..., description="优先级仲裁解释（人本温度无黑话）")

    knowledge_id: Optional[str] = Field(None, description="目标考点编号（若适用）")
    knowledge_name: Optional[str] = Field(None, description="目标考点中文名（若适用）")
    suggested_action: Optional[str] = Field(None, description="建议执行的具体子动作，如 RETAKE_QUIZ / REVIEW_CONCEPT")


class TodayActionResponse(BaseModel):
    """今日学习行动统一接口响应契约"""
    student_id: str = Field(..., description="学生唯一编号")
    action: TodayLearningAction = Field(..., description="仲裁产生的唯一今日学习行动")
