# -*- coding: utf-8 -*-
"""
app.domain.event.models
学海智导 (Xuehai Zhidao) V2 学习行为事件实体模型 (Domain Models)
"""

from typing import Any, Dict, Literal
from pydantic import BaseModel, Field

LearningEventType = Literal[
    "QUESTION_ATTEMPT",
    "HINT_REQUEST",
    "CONCEPT_VIEW",
    "PATH_STEP_COMPLETE",
]


class LearningEventCreate(BaseModel):
    """客户端上报的事件模型（允许忽略或重写客户端伪造的 server_timestamp）"""
    event_id: str = Field(..., min_length=1, description="事件唯一业务标识符")
    student_id: str = Field(..., min_length=1, description="学生ID")
    knowledge_id: str = Field(..., min_length=1, description="知识点ID")
    event_type: LearningEventType = Field(..., description="学习事件类型枚举")
    payload: Dict[str, Any] = Field(default_factory=dict, description="事件明细有效负载")
    client_timestamp: str = Field(..., min_length=1, description="客户端发生时间戳 ISO 8601")

    model_config = {
        "extra": "ignore",  # 忽略客户端私自传入的额外字段（如伪造的 server_timestamp）
    }


class LearningEvent(LearningEventCreate):
    """服务端持久化落盘的标准事件模型"""
    server_timestamp: str = Field(..., description="服务端生成的权威入库时间戳")


# 别名供通用仓储接口规范使用
StoredEvent = LearningEvent


class EventSubmissionResponse(BaseModel):
    """API 成功返回数据模型"""
    status: str = "success"
    event_id: str
    server_timestamp: str
