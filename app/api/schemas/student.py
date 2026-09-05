# -*- coding: utf-8 -*-
"""
app.api.schemas.student
学生画像、列表、学情看板及报告 DTO 模型
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StudentListItem(BaseModel):
    """学生列表条目模型"""
    student_id: str
    student_name: str
    major: str
    grade: str
    learning_goal: str
    average_accuracy: float
    mastery_level: str
    activity_level: str
    completion_level: str


class StudentListResponse(BaseModel):
    """学生列表汇总响应"""
    count: int
    students: List[StudentListItem]


class StudentDashboardResponse(BaseModel):
    """学生完整学习看板响应"""
    student_id: str
    profile: Optional[Dict[str, Any]] = None
    learning_path: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None


class AllReportsResponse(BaseModel):
    """全量学生报告响应"""
    count: int
    reports: Dict[str, Any]
