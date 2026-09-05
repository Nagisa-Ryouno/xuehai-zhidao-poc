# -*- coding: utf-8 -*-
"""
app.api.schemas.path
学习路径与节点执行状态 DTO 模型
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StudentPathStatesResponse(BaseModel):
    """学生路径节点执行状态字典响应"""
    student_id: str
    states: Dict[str, str] = Field(..., description="知识点 ID 到路径状态 (LOCKED/AVAILABLE/IN_PROGRESS/COMPLETED) 映射")


class AllLearningPathsResponse(BaseModel):
    """全量学生学习路径响应"""
    count: int
    paths: Dict[str, Any]
