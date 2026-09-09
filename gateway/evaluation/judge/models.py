# -*- coding: utf-8 -*-
"""
gateway.evaluation.judge.models
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G2: LLM Judge 抽象与融合评估数据模型

设计原则：
1. 强类型与严格白名单：所有模型启用 extra = "forbid"，拦截任何未定义或外溢字段
2. 绝对数据隔离：严禁出现 prompt, system_prompt, learning_context, raw_response, secret, api_key, authorization 等敏感字段
3. 零学习决策权：仅作为 Evaluation Observer 与质量指标容器，不包含任何 BKT / PathState 控制指令
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class JudgeDimension(str, Enum):
    """Judge 高阶教学质量评价维度枚举"""
    EXPLANATION_DEPTH = "EXPLANATION_DEPTH"
    PEDAGOGICAL_QUALITY = "PEDAGOGICAL_QUALITY"
    CONTEXTUAL_RELEVANCE = "CONTEXTUAL_RELEVANCE"
    ACTIONABILITY = "ACTIONABILITY"
    CLARITY = "CLARITY"
    EMPATHY = "EMPATHY"


class JudgeDecision(str, Enum):
    """最终评估融合裁决枚举"""
    ACCEPT = "ACCEPT"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class JudgeFailureClass(str, Enum):
    """Judge 执行故障与异常分类枚举"""
    NONE = "NONE"
    JUDGE_TIMEOUT = "JUDGE_TIMEOUT"
    JUDGE_UNAVAILABLE = "JUDGE_UNAVAILABLE"
    JUDGE_BAD_RESPONSE = "JUDGE_BAD_RESPONSE"
    JUDGE_POLICY_VIOLATION = "JUDGE_POLICY_VIOLATION"
    JUDGE_INTERNAL_ERROR = "JUDGE_INTERNAL_ERROR"
    JUDGE_UNKNOWN_ERROR = "JUDGE_UNKNOWN_ERROR"


class JudgeScore(BaseModel):
    """单维度评分契约"""
    model_config = ConfigDict(extra="forbid")

    dimension: JudgeDimension = Field(..., description="评价维度")
    score: float = Field(..., ge=0.0, le=1.0, description="评分 [0.0, 1.0]")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度 [0.0, 1.0]")
    rationale: str = Field(..., description="评分依据简述")


class JudgeResult(BaseModel):
    """结构化 Judge 产出契约"""
    model_config = ConfigDict(extra="forbid")

    judge_version: str = Field(default="judge-v1.0", description="Judge 版本号")
    valid: bool = Field(..., description="Judge 质量初判是否合格")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="高阶综合得分")
    confidence: float = Field(..., ge=0.0, le=1.0, description="综合评估置信度")
    dimension_scores: Dict[str, float] = Field(default_factory=dict, description="各维度得分映射")
    rationale_summary: str = Field(..., description="综合评语摘要")
    violations: List[str] = Field(default_factory=list, description="Judge 发现的非致命质量瑕疵标签")


class JudgeCapabilities(BaseModel):
    """Judge 能力与元数据声明契约"""
    model_config = ConfigDict(extra="forbid")

    supported_dimensions: List[JudgeDimension] = Field(..., description="支持的评价维度列表")
    deterministic: bool = Field(default=True, description="是否完全确定性")
    network_required: bool = Field(default=False, description="是否依赖外部网络")
    provider_name: str = Field(..., description="Judge 提供方名称")
    version: str = Field(default="v1.0", description="Judge 规格版本")


class EvaluationContextProjection(BaseModel):
    """
    最小必要学情上下文投影 (Evaluation Context Projection)
    
    安全红线：
    绝对禁止 user_id, email, phone, token, secret, authorization 等敏感字段进入！
    """
    model_config = ConfigDict(extra="forbid")

    knowledge_node_id: str = Field(..., description="当前知识点代号（如 K08）")
    knowledge_node_title: str = Field(..., description="当前知识点名称")
    current_mastery_percent: float = Field(..., description="当前掌握度百分比")
    mastery_target_percent: float = Field(..., description="达标阈值百分比")
    is_mastered: bool = Field(..., description="是否已达标")
    decision: str = Field(..., description="系统当前建议行动标识（只读事实）")
    current_question: str = Field(..., description="经过脱敏的学生提问内容")


class FinalEvaluationResult(BaseModel):
    """融合引擎综合判定信封"""
    model_config = ConfigDict(extra="forbid")

    decision: JudgeDecision = Field(..., description="最终三态裁决: ACCEPT / REVIEW / REJECT")
    final_valid: bool = Field(..., description="最终回答是否采纳发布")
    deterministic_valid: bool = Field(..., description="G1 确定性底座是否通过")
    policy_compliant: bool = Field(..., description="G1 策略合规性硬门禁是否通过")
    factual_consistency: bool = Field(..., description="G1 事实一致性是否通过")
    deterministic_scores: Dict[str, float] = Field(default_factory=dict, description="G1 基础 5 维评分")
    judge_used: bool = Field(default=False, description="是否实际调用了 Judge 进行辅助评估")
    judge_result: Optional[JudgeResult] = Field(default=None, description="Judge 结构化结果")
    judge_failure_class: JudgeFailureClass = Field(default=JudgeFailureClass.NONE, description="Judge 故障分类")
    rationale: str = Field(..., description="融合决策原因阐述")
    violations: List[str] = Field(default_factory=list, description="所有违规与质量风险标签汇总")
