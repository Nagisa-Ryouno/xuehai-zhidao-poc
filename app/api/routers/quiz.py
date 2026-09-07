# -*- coding: utf-8 -*-
"""
app.api.routers.quiz
分知识点微测验与题目提交路由
"""

from fastapi import APIRouter, HTTPException

from app.core.exceptions import EntityNotFoundError, InvalidOptionError
from app.services import quiz_service
from app.api.schemas.quiz import (
    QuizKnowledgeListResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
)

router = APIRouter(tags=["Quiz"])


@router.get("/api/quiz/{knowledge_id}", response_model=QuizKnowledgeListResponse)
def get_quiz_questions(knowledge_id: str):
    """
    按知识点查询测验题目（返回脱敏公开模型，严格剔除正确答案与解析）
    """
    try:
        return quiz_service.get_questions_by_knowledge_id(knowledge_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/quiz/submit", response_model=QuizSubmitResponse)
def submit_quiz_answer(req: QuizSubmitRequest):
    """
    提交题目答案，服务端权威判题并自动记录 QUESTION_ATTEMPT 学习行为事件与触发局部重规划
    """
    try:
        return quiz_service.submit_quiz_answer(req)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidOptionError as e:
        raise HTTPException(status_code=422, detail=str(e))
