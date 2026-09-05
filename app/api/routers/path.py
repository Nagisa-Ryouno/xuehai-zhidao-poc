# -*- coding: utf-8 -*-
"""
app.api.routers.path
推荐学习路径与动态路径执行状态路由
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException

import path_state_service
from app.api.schemas.path import (
    AllLearningPathsResponse,
    StudentPathStatesResponse,
)
from app.services.path_service import path_service
from app.services.student_service import student_service

router = APIRouter(tags=["LearningPath"])


@router.get("/api/students/{student_id}/learning-path")
def get_learning_path(student_id: str) -> Dict[str, Any]:
    """获取单个学生的推荐学习路径"""
    path_data = path_service.get_student_learning_path(student_id)
    if not path_data:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}",
        )
    return path_data


@router.get("/api/learning-paths", response_model=AllLearningPathsResponse)
def get_all_learning_paths():
    """获取所有学生推荐学习路径字典"""
    paths = path_service.get_all_learning_paths()
    return AllLearningPathsResponse(
        count=len(paths),
        paths=paths,
    )


@router.get("/api/students/{student_id}/path-states", response_model=StudentPathStatesResponse)
def get_student_path_states(student_id: str):
    """
    查询指定学生在知识网络中的路径执行状态字典 (LOCKED, AVAILABLE, IN_PROGRESS, COMPLETED)
    """
    profile = student_service.get_student_profile(student_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}",
        )
    states = path_state_service.get_all_path_states(student_id)
    return StudentPathStatesResponse(
        student_id=student_id,
        states={k: v.value for k, v in states.items()},
    )
