# -*- coding: utf-8 -*-
"""
quiz_bank_repository.py
学海智导 (Xuehai Zhidao) V2 测验题库仓储层 (Quiz Bank Repository)

负责从静态种子数据 (settings.QUIZ_BANK_FILE) 中读取、缓存并检索测验题目。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings


class QuizBankRepository:
    """微观经济学分知识点微测验题库仓储"""

    _cached_questions: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def _get_quiz_file(cls) -> Path:
        return settings.QUIZ_BANK_FILE

    @classmethod
    def reload(cls) -> None:
        """清除缓存"""
        cls._cached_questions = None

    @classmethod
    def get_all_questions(cls) -> List[Dict[str, Any]]:
        """获取全部题目列表 (原始完整字段)"""
        if cls._cached_questions is None:
            primary_file = cls._get_quiz_file()
            fallback_file = settings.PROJECT_ROOT / "data" / "quiz_bank.json"
            target_file = primary_file if primary_file.exists() else fallback_file

            if not target_file.exists():
                cls._cached_questions = []
            else:
                try:
                    content = target_file.read_text(encoding="utf-8").strip()
                    cls._cached_questions = json.loads(content) if content else []
                except Exception:
                    cls._cached_questions = []
        return cls._cached_questions

    @classmethod
    def get_questions_by_knowledge_id(cls, knowledge_id: str) -> List[Dict[str, Any]]:
        """按知识点 ID 获取配套自测题列表"""
        questions = cls.get_all_questions()
        return [q for q in questions if q.get("knowledge_id") == knowledge_id]

    @classmethod
    def get_question_by_id(cls, question_id: str) -> Optional[Dict[str, Any]]:
        """按题目 ID 查询单个完整题目"""
        questions = cls.get_all_questions()
        for q in questions:
            if q.get("question_id") == question_id:
                return q
        return None

    @classmethod
    def get_knowledge_ids_with_quizzes(cls) -> List[str]:
        """获取所有包含测验题的知识点 ID 列表 (去重升序)"""
        questions = cls.get_all_questions()
        ids = {q.get("knowledge_id") for q in questions if q.get("knowledge_id")}
        return sorted(list(ids))


# 全局默认单例
quiz_bank_repository = QuizBankRepository()

__all__ = [
    "QuizBankRepository",
    "quiz_bank_repository",
]
