# -*- coding: utf-8 -*-
"""
gateway.learning.analytics.models
Sprint 8-C: 学习成效沉淀、掌握度历史、错题复盘与教师学习分析数据契约
"""

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class ProgressHistoryEvent(BaseModel):
    """单条真实学习行为时序事件模型 (100% 来源于 EventRepository)"""
    event_id: str
    timestamp: str
    event_type: str
    knowledge_id: Optional[str] = None
    knowledge_name: Optional[str] = None
    is_correct: Optional[bool] = None
    selected_option: Optional[str] = None
    mastery_after: Optional[float] = None
    time_spent_ms: Optional[int] = None
    summary: str
    details: Optional[str] = None


class MasteryTrendPoint(BaseModel):
    """掌握度演进阶梯采样点"""
    step: int
    timestamp: str
    overall_mastery: float
    knowledge_id: str
    trigger_event: str
    event_type: Optional[str] = None


class KnowledgeMasteryItem(BaseModel):
    """30 个考点各自的权威掌握度与路径状态详情"""
    knowledge_id: str
    knowledge_name: str
    chapter: str
    mastery: float
    state: Literal["MASTERED", "DEVELOPING", "NEEDS_REINFORCEMENT", "UNSTUDIED"]
    status: Optional[str] = None
    path_state: str
    attempts: int = 0
    correct_count: int = 0
    accuracy: float = 0.0
    last_attempt_time: Optional[str] = None


class StudentProgressResponse(BaseModel):
    """学生学习进展与成效历史完整响应模型"""
    student_id: str
    student_name: str
    overall_mastery: float
    mastery_percentage: float
    mastery_level: Optional[str] = None
    mastered_count: int
    developing_count: int
    reinforcement_count: int
    weak_count: int = 0
    unstudied_count: int
    total_knowledge_points: int = 30
    total_practice_count: int
    total_correct_count: int
    overall_accuracy: float
    history_timeline: List[ProgressHistoryEvent]
    mastery_trend: List[MasteryTrendPoint]
    knowledge_point_masteries: List[KnowledgeMasteryItem]
    knowledge_points: List[KnowledgeMasteryItem] = Field(default_factory=list)


class WrongAnswerItem(BaseModel):
    """错题复盘卡片模型 (源于真实 QUESTION_ATTEMPT 且 is_correct=False)"""
    question_id: str
    knowledge_id: str
    knowledge_name: str
    chapter: str
    question_prompt: str
    options: Dict[str, str]
    student_answer: str
    correct_answer: str
    explanation: str
    current_mastery: float
    current_path_state: str
    mistake_count: int
    last_error_time: str
    review_priority: Literal["HIGH", "MEDIUM", "LOW"]


class WrongAnswerReviewResponse(BaseModel):
    """错题复盘列表响应模型"""
    student_id: str
    total_wrong: int
    wrong_answers: List[WrongAnswerItem]


class TeacherStudentSummary(BaseModel):
    """教师端学生列表中单名学生的学情聚合概览"""
    student_id: str
    student_name: str
    major: str
    grade: str
    learning_goal: str
    overall_mastery: float
    mastered_count: int
    developing_count: int
    weak_count: int
    total_attempts: int
    total_wrong_count: int
    accuracy: float
    last_active_time: Optional[str] = None
    risk_level: Literal["HEALTHY", "NORMAL", "ATTENTION"]
    current_focus_node: Optional[str] = None
    current_focus_name: Optional[str] = None


class TeacherWeakPoint(BaseModel):
    """班级共性薄弱卡点分析项"""
    knowledge_id: str
    knowledge_name: str
    chapter: str
    average_mastery: float
    avg_mastery: Optional[float] = None
    affected_student_count: int
    weak_student_count: Optional[int] = None
    total_mistakes: int
    error_rate: Optional[float] = None
    urgency: Optional[str] = "MEDIUM"
    recommended_intervention: str


class TeacherOverviewResponse(BaseModel):
    """教师学习分析总览看板响应模型 (Read-only)"""
    total_students: int
    active_students: int
    class_average_mastery: float
    at_risk_students_count: int
    class_kpis: Optional[Dict[str, Any]] = None
    students: List[TeacherStudentSummary]
    weak_knowledge_points: List[TeacherWeakPoint]
    recent_class_activities: List[ProgressHistoryEvent]


class TeacherStudentDetailResponse(BaseModel):
    """教师端单生下钻深潜学情响应模型 (Read-only)"""
    student_id: str
    student_name: str
    major: str
    grade: str
    learning_goal: str
    overall_mastery: float
    accuracy: float
    total_attempts: int
    total_wrong_count: int
    risk_level: Literal["HEALTHY", "NORMAL", "ATTENTION"]
    dynamic_route: Optional[Dict[str, Any]] = None
    weak_points: List[KnowledgeMasteryItem]
    knowledge_point_masteries: List[KnowledgeMasteryItem]
    wrong_answers: List[WrongAnswerItem]
    recent_events: List[ProgressHistoryEvent]
