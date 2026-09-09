# -*- coding: utf-8 -*-
"""
gateway.models
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
AI Gateway 强类型输入/输出契约模型

设计原则：
1. 严格白名单：所有模型开启 extra = "forbid"，拦截未知/恶意/私有注入字段
2. 契约对齐：与 frontend/src/components/student/ 现有契约严格一致
3. 权限隔离：绝不包含决策、解锁、状态跃迁等学习引擎内部控制字段
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class PromptRecentQuiz(BaseModel):
    """微测验作答客观历史事实（只读）"""
    model_config = ConfigDict(extra="forbid")

    question_id: str
    is_correct: bool
    time_spent_ms: int
    before_mastery_percent: float
    after_mastery_percent: float
    delta_percent: float
    action: str
    reason_code: str
    unlocked_nodes: List[str] = Field(default_factory=list)


class PromptNextAction(BaseModel):
    """确定性学习引擎给出的建议下一步行动（只读事实，不可被 AI 篡改）"""
    model_config = ConfigDict(extra="forbid")

    type: str
    label: str
    target_knowledge_id: str
    reason: str


class LearningPromptSystemFacts(BaseModel):
    """前端白名单投影后的系统客观事实集"""
    model_config = ConfigDict(extra="forbid")

    student_id: str
    student_name: str
    major: str
    grade: str
    learning_goal: str

    current_knowledge_id: str
    current_knowledge_name: str
    current_chapter: str
    current_path_state: Literal["LOCKED", "AVAILABLE", "IN_PROGRESS", "COMPLETED"]

    current_mastery_percent: float
    mastery_target_percent: float
    mastery_gap_percent: float
    is_mastered: bool

    prerequisites_met: bool
    path_priority: str
    is_path_completed: bool

    recent_quiz: Optional[PromptRecentQuiz] = None
    next_action: PromptNextAction


class LearningPromptContext(BaseModel):
    """安全投影后的学习提示词上下文"""
    model_config = ConfigDict(extra="forbid")

    user_question: str
    system_facts: LearningPromptSystemFacts
    grounding_rules: List[str] = Field(default_factory=list)


class AICompanionRequest(BaseModel):
    """AI 伴学网关统一请求载荷"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    prompt_context: LearningPromptContext = Field(..., alias="promptContext")
    question: Optional[str] = None


class StructuredAIResponse(BaseModel):
    """AI 伴学网关统一结构化输出契约（对齐前端 StructuredAIResponse）"""
    model_config = ConfigDict(extra="forbid")

    answer: str
    referenced_facts: List[str] = Field(default_factory=list)
    suggested_explanation: Optional[str] = None
    grounding_status: Literal["grounded", "insufficient_context"] = "grounded"


class GatewayErrorResponse(BaseModel):
    """网关统一安全降级响应模型（无内部敏感信息）"""
    model_config = ConfigDict(extra="forbid")

    error: str
    detail: str
    grounding_status: Literal["insufficient_context"] = "insufficient_context"
    answer: str
