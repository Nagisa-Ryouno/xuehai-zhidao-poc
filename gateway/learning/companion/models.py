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
    guided_actions: List["CompanionSuggestedAction"] = Field(default_factory=list, description="确定性结构化学习行动列表")
    learning_state: Optional[Dict[str, Any]] = Field(default=None, description="当前客观掌握度状态快照")
    quick_check: Optional["QuickCheckQuestion"] = Field(default=None, description="内嵌的轻量快速思维检查题目")
    provider: str = Field(default="offline", description="实际响应提供商（offline / mock / real）")
    referenced_facts: List[str] = Field(default_factory=list, description="本次回答所引用的客观系统事实列表")


class ActionType(str, Enum):
    """确定性学习行动白名单类型"""
    REVIEW_CONCEPT = "review_concept"
    RETRY_QUIZ = "retry_quiz"
    CONTINUE_CONVERSATION = "continue_conversation"
    VIEW_PROGRESS = "view_progress"
    REVIEW_WRONG_ANSWERS = "review_wrong_answers"

    # 别名兼容
    READ_CONCEPT = "READ_CONCEPT"
    TARGETED_PRACTICE = "TARGETED_PRACTICE"
    CONTINUE_DISCUSSION = "CONTINUE_DISCUSSION"


class CompanionSuggestedAction(BaseModel):
    """确定性推荐行动模型"""
    model_config = ConfigDict(extra="ignore")

    action_id: str = Field(..., description="行动唯一标识")
    action_type: ActionType = Field(..., description="行动类型（白名单）")
    label: str = Field(default="", description="行动按钮展示文本")
    title: Optional[str] = Field(default=None, description="行动标题（别名）")
    description: Optional[str] = Field(default=None, description="行动说明")
    knowledge_id: Optional[str] = Field(default=None, description="目标知识点ID")
    target_knowledge_id: Optional[str] = Field(default=None, description="目标知识点ID（别名）")
    question_id: Optional[str] = Field(default=None, description="目标试题ID")
    target_question_id: Optional[str] = Field(default=None, description="目标试题ID（别名）")
    route_destination: Optional[str] = Field(default=None, description="跳转目标路径")
    reason: str = Field(default="", description="客观事实依据（禁止主观AI宣称）")
    source_reason: Optional[str] = Field(default=None, description="事实依据（别名）")
    badge: Optional[str] = Field(default=None, description="状态徽章")

    def model_post_init(self, __context: Any) -> None:
        if self.title is None:
            self.title = self.label
        if not self.label and self.title:
            self.label = self.title
        if self.description is None:
            self.description = self.reason
        if not self.reason and self.description:
            self.reason = self.description
        if self.target_knowledge_id is None:
            self.target_knowledge_id = self.knowledge_id
        if self.knowledge_id is None and self.target_knowledge_id:
            self.knowledge_id = self.target_knowledge_id
        if self.target_question_id is None:
            self.target_question_id = self.question_id
        if self.source_reason is None:
            self.source_reason = self.reason
        if self.route_destination is None:
            if self.action_type in {ActionType.REVIEW_CONCEPT, ActionType.READ_CONCEPT}:
                self.route_destination = f"/student/concept/{self.knowledge_id or 'K01'}"
            elif self.action_type in {ActionType.RETRY_QUIZ, ActionType.TARGETED_PRACTICE}:
                self.route_destination = f"/student/quiz/{self.knowledge_id or 'K01'}"
            elif self.action_type == ActionType.VIEW_PROGRESS:
                self.route_destination = "/student/profile/progress"
            elif self.action_type == ActionType.REVIEW_WRONG_ANSWERS:
                self.route_destination = "/student/profile/wrong-answers"
            else:
                self.route_destination = "/student/assistant"


class QuickCheckOption(BaseModel):
    """快速思维检查选项"""
    model_config = ConfigDict(extra="ignore")

    key: str = Field(..., description="选项标识符，如 A/B/C")
    id: Optional[str] = Field(default=None, description="选项标识符（别名）")
    text: str = Field(..., description="选项正文")

    def model_post_init(self, __context: Any) -> None:
        if self.id is None:
            self.id = self.key


class QuickCheckQuestion(BaseModel):
    """快速思维检查题目实体（轻量互动，非正式测验）"""
    model_config = ConfigDict(extra="ignore")

    check_id: str = Field(..., description="快速检查唯一ID")
    question_id: Optional[str] = Field(default=None, description="题目ID（别名）")
    knowledge_id: str = Field(..., description="关联考点ID")
    knowledge_name: str = Field(..., description="关联考点名称")
    prompt: str = Field(..., description="问题描述")
    stem: Optional[str] = Field(default=None, description="题干（别名）")
    options: List[QuickCheckOption] = Field(..., description="选项列表")
    hint: Optional[str] = Field(default=None, description="启发式思考提示")
    concept_summary: Optional[str] = Field(default=None, description="考点要点总结")

    def model_post_init(self, __context: Any) -> None:
        if self.question_id is None:
            self.question_id = self.check_id
        if self.stem is None:
            self.stem = self.prompt


class QuickCheckSubmitRequest(BaseModel):
    """学生提交快速思维检查作答"""
    model_config = ConfigDict(extra="ignore")

    student_id: str = Field(..., description="学生ID")
    check_id: Optional[str] = Field(default=None, description="快速检查题目ID")
    question_id: Optional[str] = Field(default=None, description="题目ID（别名）")
    knowledge_id: str = Field(..., description="考点ID")
    selected_option: str = Field(..., description="选中选项键")

    def model_post_init(self, __context: Any) -> None:
        if not self.check_id and self.question_id:
            self.check_id = self.question_id
        elif not self.question_id and self.check_id:
            self.question_id = self.check_id


class QuickCheckResponse(BaseModel):
    """快速检查判定反馈（零BKT副作用）"""
    model_config = ConfigDict(extra="ignore")

    check_id: str = Field(..., description="快速检查题目ID")
    knowledge_id: str = Field(..., description="考点ID")
    is_correct: bool = Field(..., description="是否正确")
    correct_option: Optional[str] = Field(default="A", description="正确选项键")
    explanation: str = Field(..., description="启发式反馈解析")
    key_takeaway: Optional[str] = Field(default=None, description="核心要点总结")
    verified_quiz_action: Optional[CompanionSuggestedAction] = Field(
        default=None, description="引导前往正式测验验证的推荐行动"
    )
    suggested_actions: List[CompanionSuggestedAction] = Field(
        default_factory=list, description="跟进建议行动列表"
    )
    safety: CompanionSafetyMetadata = Field(
        default_factory=CompanionSafetyMetadata, description="安全元数据"
    )

    def model_post_init(self, __context: Any) -> None:
        if not self.suggested_actions and self.verified_quiz_action:
            self.suggested_actions = [self.verified_quiz_action]


class LearningActionResultRequest(BaseModel):
    """学习行动完成后向伴学导师上报真实闭环请求"""
    model_config = ConfigDict(extra="ignore")

    student_id: str = Field(..., description="学生ID")
    action_type: str = Field(..., description="完成的行动类型，如 retry_quiz / review_concept")
    knowledge_id: str = Field(..., description="知识点ID")
    question_id: Optional[str] = Field(default=None, description="相关题目ID（若有）")
    result: Optional[str] = Field(default=None, description="客观作答结果，如 correct / incorrect / completed")
    is_correct: Optional[bool] = Field(default=None, description="作答是否正确")
    score: Optional[float] = Field(default=None, description="测验得分")
    session_id: Optional[str] = Field(default=None, description="当前伴学会话ID")


class LearningActionResultResponse(BaseModel):
    """伴学导师对学习行动结果的客观反思与下一步引导响应"""
    model_config = ConfigDict(extra="ignore")

    session_id: Optional[str] = Field(default=None, description="会话ID")
    student_id: Optional[str] = Field(default=None, description="学生ID")
    action_id: Optional[str] = Field(default=None, description="行动ID")
    action: str = Field(default="", description="本次反思针对的行动")
    action_type: Optional[str] = Field(default=None, description="行动类型")
    knowledge_id: Optional[str] = Field(default=None, description="考点ID")
    knowledge_name: Optional[str] = Field(default=None, description="考点名称")
    before_mastery: Optional[float] = Field(default=0.20, description="行动前掌握度")
    after_mastery: Optional[float] = Field(default=0.20, description="行动后掌握度")
    mastery_delta: Optional[float] = Field(default=0.0, description="掌握度净增量")
    consecutive_incorrect: Optional[int] = Field(default=0, description="连续答错次数")
    mastery_state_text: Optional[str] = Field(default="起步阶段", description="掌握度状态文本")
    reflection: str = Field(default="", description="导师专业复盘与学情反思内容")
    reflection_text: Optional[str] = Field(default=None, description="反思文案（别名）")
    guided_actions: List[CompanionSuggestedAction] = Field(
        default_factory=list, description="下一步确定性学习行动列表"
    )
    next_actions: List[CompanionSuggestedAction] = Field(
        default_factory=list, description="下一步行动列表（别名）"
    )
    learning_state: Dict[str, Any] = Field(default_factory=dict, description="系统当前客观掌握度真实状态")
    safety: CompanionSafetyMetadata = Field(
        default_factory=CompanionSafetyMetadata, description="安全元数据"
    )

    def model_post_init(self, __context: Any) -> None:
        if self.reflection_text is None:
            self.reflection_text = self.reflection
        if not self.next_actions and self.guided_actions:
            self.next_actions = self.guided_actions


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
