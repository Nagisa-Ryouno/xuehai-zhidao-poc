# -*- coding: utf-8 -*-
"""
app.api.routers.students
学生学情、画像、报告与全景看板路由
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from app.api.schemas.student import (
    AllReportsResponse,
    StudentDashboardResponse,
    StudentListItem,
    StudentListResponse,
)
from app.services.student_service import student_service

router = APIRouter(tags=["Students"])


@router.get("/api/students", response_model=StudentListResponse)
def get_students():
    """获取所有学生列表及学情摘要"""
    students_data = student_service.get_all_students()
    items = [
        StudentListItem(
            student_id=s["student_id"],
            student_name=s["student_name"],
            major=s["major"],
            grade=s["grade"],
            learning_goal=s.get("learning_goal", ""),
            average_accuracy=s.get("average_accuracy", 0.0),
            mastery_level=s.get("mastery_level", ""),
            activity_level=s.get("activity_level", ""),
            completion_level=s.get("completion_level", ""),
        )
        for s in students_data
    ]
    return StudentListResponse(
        count=len(items),
        students=items,
    )


@router.get("/api/students/{student_id}/profile")
def get_student_profile(student_id: str) -> Dict[str, Any]:
    """获取指定学生画像档案"""
    profile = student_service.get_student_profile(student_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}",
        )
    return profile


@router.get("/api/students/{student_id}/report")
def get_student_report(student_id: str) -> Dict[str, Any]:
    """获取指定学生综合学情诊断报告"""
    report = student_service.get_student_report(student_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}",
        )
    return report


@router.get("/api/reports", response_model=AllReportsResponse)
def get_all_reports():
    """获取所有学生综合报告"""
    reports = student_service.get_all_reports()
    return AllReportsResponse(
        count=len(reports),
        reports=reports,
    )


@router.get("/api/students/{student_id}/dashboard", response_model=StudentDashboardResponse)
def get_student_dashboard(student_id: str):
    """获取指定学生的完整学情看板（画像 + 推荐路径 + 报告）"""
    dashboard = student_service.get_student_dashboard(student_id)
    if not dashboard:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}",
        )
    return StudentDashboardResponse(**dashboard)
