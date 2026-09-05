# -*- coding: utf-8 -*-
"""
app.api.schemas.system
系统基础信息、健康检查与全览 DTO 模型
"""

from typing import Dict, List
from pydantic import BaseModel, Field


class SystemRootResponse(BaseModel):
    """根路径响应"""
    message: str = Field(default="学海智导 API 正常运行")
    project: str = Field(default="学海智导")
    version: str = Field(default="0.2.0")
    docs: str = Field(default="/docs")


class SystemHealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(default="ok")
    message: str = Field(default="学海智导后端服务运行正常")


class OverviewStudentSummary(BaseModel):
    """概况中的精简学生信息"""
    student_id: str
    student_name: str


class SystemOverviewResponse(BaseModel):
    """系统宏观概况响应"""
    student_count: int = Field(..., description="学生总数")
    profile_count: int = Field(..., description="画像档案总数")
    learning_path_count: int = Field(..., description="规划路径总数")
    report_count: int = Field(..., description="综合学情报告总数")
    students: List[OverviewStudentSummary] = Field(default_factory=list, description="学生简明列表")
