# -*- coding: utf-8 -*-
"""
gateway/learning/path_generation/models.py
学海智导 (Xuehai Zhidao) - 动态学习路线数据模型
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class RouteStep(BaseModel):
    """动态学习路线单步节点"""
    knowledge_id: str = Field(..., description="知识点 ID")
    knowledge_name: str = Field(..., description="知识点名称")
    chapter: str = Field(..., description="所属章节")
    rank: int = Field(..., description="推荐位次: 1, 2, 3")
    role: str = Field(
        ..., description="角色标识: CURRENT (当前焦点) / NEXT (紧接着学习) / UPCOMING (进阶延伸)"
    )
    score: float = Field(..., description="综合优先级打分 (0.00 ~ 1.00)")
    reason_codes: List[str] = Field(
        default_factory=list, description="推荐决策结构化原因编码"
    )
    explanation: str = Field(..., description="面向学生的结构化推荐理由中文阐述")
    mastery: float = Field(..., description="当前 BKT 掌握度 (0.00 ~ 1.00)")
    path_state: str = Field(..., description="当前路径状态: AVAILABLE / IN_PROGRESS / LOCKED")
    prerequisites: List[str] = Field(
        default_factory=list, description="直接前置依赖节点 ID 列表"
    )


class DynamicLearningRoute(BaseModel):
    """动态自适应学习路线模型 (至多 3 站)"""
    student_id: str = Field(..., description="学生 ID")
    goal: str = Field(..., description="设定的学习目标")
    route_length: int = Field(..., description="实际推荐路线长度 (0 <= route_length <= 3)")
    steps: List[RouteStep] = Field(
        default_factory=list, description="有序推荐步骤列表 (严格前置保序)"
    )
    is_fallback: bool = Field(default=False, description="是否触发了安全降级")
    fallback_reason: Optional[str] = Field(default=None, description="降级原因阐明")
    generated_at: str = Field(..., description="路线生成时间戳")
