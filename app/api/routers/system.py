# -*- coding: utf-8 -*-
"""
app.api.routers.system
系统状态、健康检查与概况路由
"""

from fastapi import APIRouter
from app.api.schemas.system import (
    SystemHealthResponse,
    SystemOverviewResponse,
    SystemRootResponse,
)
from app.services.student_service import student_service

router = APIRouter(tags=["System"])


@router.get("/", response_model=SystemRootResponse)
def root():
    """根路径欢迎信息"""
    return SystemRootResponse(
        message="学海智导 API 正常运行",
        project="学海智导",
        version="0.2.0",
        docs="/docs",
    )


@router.get("/api/health", response_model=SystemHealthResponse)
def health_check():
    """服务健康检查接口"""
    return SystemHealthResponse(
        status="ok",
        message="学海智导后端服务运行正常",
    )


@router.get("/api/overview", response_model=SystemOverviewResponse)
def get_overview():
    """获取系统总体宏观概况数据"""
    overview = student_service.get_system_overview()
    return SystemOverviewResponse(**overview)
