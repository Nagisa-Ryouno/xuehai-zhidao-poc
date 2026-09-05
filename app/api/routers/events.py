# -*- coding: utf-8 -*-
"""
app.api.routers.events
学习行为事件采集上报路由
"""

from fastapi import APIRouter

import event_service
from app.api.schemas.event import (
    EventSubmissionResponse,
    LearningEventCreate,
)

router = APIRouter(tags=["LearningEvents"])


@router.post("/api/events", response_model=EventSubmissionResponse)
def submit_learning_event(event: LearningEventCreate):
    """
    统一接收并持久化来自前端、测验系统或伴学模块的学习行为事件 (Append-Only JSONL)
    """
    stored = event_service.record_event(event)
    return EventSubmissionResponse(
        status="success",
        event_id=stored.event_id,
        server_timestamp=stored.server_timestamp,
    )
