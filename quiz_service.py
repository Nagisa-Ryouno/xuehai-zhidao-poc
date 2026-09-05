# -*- coding: utf-8 -*-
"""
quiz_service.py
学海智导 (Xuehai Zhidao) V2 分知识点微测验服务层 (Backward-compatible Facade)

向后兼容门面，内部委托给 app.services.quiz_service。
"""

from app.services.quiz_service import (
    DEFAULT_QUIZ_FILE,
    LearningStateSnapshot,
    QuizKnowledgeListResponse,
    QuizOption,
    QuizQuestionInternal,
    QuizQuestionPublic,
    QuizSubmitRequest,
    QuizSubmitResponse,
    get_all_questions,
    get_mastery_state,
    get_question_by_id,
    get_questions_by_knowledge_id,
    is_valid_knowledge_id,
    load_quiz_bank,
    submit_quiz_answer,
)

__all__ = [
    "DEFAULT_QUIZ_FILE",
    "QuizOption",
    "QuizQuestionPublic",
    "QuizQuestionInternal",
    "QuizKnowledgeListResponse",
    "QuizSubmitRequest",
    "get_mastery_state",
    "LearningStateSnapshot",
    "QuizSubmitResponse",
    "load_quiz_bank",
    "get_all_questions",
    "is_valid_knowledge_id",
    "get_question_by_id",
    "get_questions_by_knowledge_id",
    "submit_quiz_answer",
]
