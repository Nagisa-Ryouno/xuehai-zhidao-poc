# -*- coding: utf-8 -*-
"""
app.api.routers.learning_state
动态 BKT 掌握度认知状态查询与事件驱动演进路由
"""

from fastapi import APIRouter, HTTPException

import bkt_event_processor
import bkt_state_service
import quiz_service
from app.api.schemas.learning_state import (
    BKTStateResponse,
    LearningStateUpdateRequest,
    LearningStateUpdateResponse,
)
from app.services.student_service import student_service

router = APIRouter(tags=["LearningState"])


@router.get(
    "/api/students/{student_id}/knowledge-state/{knowledge_id}",
    response_model=BKTStateResponse,
)
def get_student_knowledge_state(student_id: str, knowledge_id: str):
    """
    查询指定学生指定知识点的动态 BKT 掌握度认知状态
    若尚无作答记录，返回 P(L0)=0.20 的合法初始状态
    """
    profile = student_service.get_student_profile(student_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}",
        )

    if not quiz_service.is_valid_knowledge_id(knowledge_id):
        raise HTTPException(
            status_code=404,
            detail=f"未找到对应知识点：{knowledge_id}",
        )

    state = bkt_state_service.get_state(student_id, knowledge_id, auto_init=True)
    mastery_pct = round(state.mastery_probability * 100.0, 2)

    return BKTStateResponse(
        student_id=state.student_id,
        knowledge_id=state.knowledge_id,
        mastery_probability=round(state.mastery_probability, 6),
        mastery_percent=mastery_pct,
        attempts=state.attempts,
        correct_attempts=state.correct_attempts,
        incorrect_attempts=state.incorrect_attempts,
        consecutive_correct=state.consecutive_correct,
        consecutive_incorrect=state.consecutive_incorrect,
        last_updated=state.last_updated,
        last_event_id=state.last_event_id,
    )


@router.post(
    "/api/learning-state/update",
    response_model=LearningStateUpdateResponse,
)
def update_learning_state_from_event(req: LearningStateUpdateRequest):
    """
    根据已落盘的学习事件触发 BKT 认知状态演进（消费已有事件，幂等保证）
    """
    event = bkt_event_processor.find_event_by_id(req.event_id)
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"未找到对应学习事件：{req.event_id}",
        )

    result = bkt_event_processor.process_event(event)

    return LearningStateUpdateResponse(
        status=result.status,
        event_id=result.event_id,
        student_id=result.student_id,
        knowledge_id=result.knowledge_id,
        before=round(result.before_mastery, 6) if result.before_mastery is not None else None,
        after=round(result.after_mastery, 6) if result.after_mastery is not None else None,
        changed=result.changed,
        reason=result.reason,
    )
