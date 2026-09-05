# -*- coding: utf-8 -*-
"""
app.api.schemas.assistant
AI 伴学助手问答与问候 DTO 模型
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AssistantMessageRequest(BaseModel):
    """助手聊天请求体"""
    message: str = Field(..., min_length=1, description="学生提问内容")


class AssistantRelatedKnowledge(BaseModel):
    """关联知识点结构"""
    knowledge_id: str
    knowledge_name: str
    accuracy: Optional[float] = None
    priority: Optional[str] = None
    reason: Optional[str] = None


class AssistantChatResponse(BaseModel):
    """助手聊天结构化响应"""
    answer: str
    related_knowledge_points: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)


class AssistantGreetingResponse(BaseModel):
    """助手首次专属问候响应"""
    student_id: str
    student_name: str
    greeting: str
    quick_prompts: List[str] = Field(default_factory=list)
