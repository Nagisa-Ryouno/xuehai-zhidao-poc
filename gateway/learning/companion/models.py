# -*- coding: utf-8 -*-
"""
gateway.learning.companion.models
=================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-A
AI 学习伙伴 (AI Learning Companion) 强类型契约模型

设计原则与红线约束：
1. 只读解释边界：AI 是 Tutor / Companion / Explanation Layer，绝非生产决策层
2. 权限硬隔离：永远包含 allow_production_decision = False
3. 严格白名单与字符长度硬限制：单条消息不超过 2000 字符，超出直接 422 报错
4. 杜绝技术黑话与虚假宣称：输出纯净教学语言，明确标注离线/真实提供商
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompanionMode(str, Enum):
    CONCEPT_EXPLAIN = "concept_explain"
    WRONG_ANSWER_REVIEW = "wrong_answer_review"
    CONVERSATION = "conversation"
    LEARNING_SUMMARY = "learning_summary"


class CompanionSafetyMetadata(BaseModel):
    """安全与权限隔离元数据（硬约束）"""
    model_config = ConfigDict(extra="forbid")

    allow_production_decision: bool = Field(
        default=False,
        description="硬性安全边界：AI 永远不具备修改生产状态的权限",
    )
    sanitized: bool = Field(
        default=True,
        description="输入与上下文是否经过白名单清洗脱敏",
    )
    offline_mode: bool = Field(
        default=True,
        description="是否处于离线安全确定性辅导模式",
    )
    context_source: str = Field(
        default="authoritative_knowledge_engine",
        description="上下文事实来源声明",
    )
    redactions_applied: List[str] = Field(
        default_factory=list,
        description="已应用的脱敏规则标签",
    )

    @field_validator("allow_production_decision")
    @classmethod
    def validate_production_decision_frozen(cls, v: bool) -> bool:
        if v is True:
            raise ValueError("CRITICAL: allow_production_decision must strictly be False for AI Companion!")
        return False


class CompanionContextMetadata(BaseModel):
    """当前学习上下文白名单元数据（只读、无敏感信息）"""
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(..., description="学生业务标识符")
    knowledge_id: Optional[str] = Field(default=None, description="知识点ID，如 K01")
    knowledge_name: Optional[str] = Field(default=None, description="知识点名称")
    chapter: Optional[str] = Field(default=None, description="所属章节")
    mastery: Optional[float] = Field(default=None, description="当前掌握度数值 (0.0~1.0)")
    mastery_status: Optional[str] = Field(default=None, description="认知阶段，如 薄弱/发展中/已掌握")
    prerequisites: List[str] = Field(default_factory=list, description="前置考点列表")
    question_id: Optional[str] = Field(default=None, description="关联的错题ID，如 Q-K01-01")
    learning_goal: Optional[str] = Field(default=None, description="设定的阶段学习目标")


class CompanionStudyRequest(BaseModel):
    """学生端发起的 AI 伴学辅导请求"""
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(..., min_length=1, description="学生ID")
    mode: CompanionMode = Field(default=CompanionMode.CONCEPT_EXPLAIN, description="伴学辅导模式")
    knowledge_id: Optional[str] = Field(default=None, description="目标考点ID")
    question_id: Optional[str] = Field(default=None, description="目标题目ID（错题辅导模式）")
    message: Optional[str] = Field(default=None, description="学生提问或输入文本（限制 2000 字符内）")
    session_id: Optional[str] = Field(default=None, description="连续对话会话标识")

    @field_validator("message")
    @classmethod
    def validate_message_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 2000:
            raise ValueError("提问内容超过最大允许长度 (2000 字符)，请精简后重试。")
        return v


class CompanionStudyResponse(BaseModel):
    """AI 伴学辅导统一响应契约"""
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="当前会话标识")
    mode: CompanionMode = Field(..., description="本次响应对应的模式")
    answer: str = Field(..., description="面向大学生的专业、温和、启发式辅导内容")
    context: CompanionContextMetadata = Field(..., description="本次辅导绑定的客观上下文")
    safety: CompanionSafetyMetadata = Field(default_factory=CompanionSafetyMetadata, description="安全与权限元数据")
    suggested_actions: List[str] = Field(default_factory=list, description="建议的下一步学习行动（仅供参考，不修改正式路线）")
    provider: str = Field(default="offline", description="实际响应提供商（offline / mock / real）")
    referenced_facts: List[str] = Field(default_factory=list, description="本次回答所引用的客观系统事实列表")


class CompanionChatMessage(BaseModel):
    """单条会话消息实体"""
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"] = Field(..., description="消息角色")
    content: str = Field(..., description="消息文本")
    timestamp: str = Field(..., description="ISO 8601 时间戳")


class CompanionSession(BaseModel):
    """学生专属的伴学会话状态（内存管理）"""
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="会话唯一ID")
    student_id: str = Field(..., description="绑定的学生ID")
    messages: List[CompanionChatMessage] = Field(default_factory=list, description="最近轮次的对话记录（至多 5 轮）")
    last_knowledge_id: Optional[str] = Field(default=None, description="最近聚焦的知识点ID")
    created_at: str = Field(..., description="会话创建时间")
