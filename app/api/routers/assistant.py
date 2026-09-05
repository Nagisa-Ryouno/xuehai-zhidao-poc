# -*- coding: utf-8 -*-
"""
app.api.routers.assistant
AI 智能伴学导师问答与动态问候路由
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from app.api.schemas.assistant import (
    AssistantGreetingResponse,
    AssistantMessageRequest,
)
from app.services.assistant_service import assistant_service
from app.services.student_service import student_service

router = APIRouter(tags=["AIAssistant"])


@router.post("/api/students/{student_id}/assistant")
def chat_with_assistant(
    student_id: str,
    request: AssistantMessageRequest,
) -> Dict[str, Any]:
    """
    AI 学习助手问答接口
    接收学生问题，根据真实多维学情生成上下文相关的智能诊断与指导
    """
    msg = request.message.strip() if request.message else ""
    if not msg:
        raise HTTPException(
            status_code=400,
            detail="消息内容不能为空",
        )

    profile = student_service.get_student_profile(student_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}",
        )

    return assistant_service.generate_assistant_response(
        student_id=student_id,
        message=msg,
    )


@router.get("/api/students/{student_id}/assistant/greeting", response_model=AssistantGreetingResponse)
def get_assistant_greeting(student_id: str):
    """
    获取针对当前学生的 AI 首次专属问候语与动态快捷问题
    """
    profile = student_service.get_student_profile(student_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}",
        )

    greeting_data = assistant_service.get_assistant_greeting(
        student_id=student_id,
    )
    return AssistantGreetingResponse(**greeting_data)
