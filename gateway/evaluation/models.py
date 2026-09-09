# -*- coding: utf-8 -*-
"""
gateway.evaluation.models
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G1: AI Semantic Validation & Evaluation 强类型评估模型

设计原则：
1. 强类型白名单：所有模型启用 extra = "forbid"，拦截未知/未定义注入字段
2. 零学习决策权：评估模型仅作为 Observer / Gatekeeper 记录评估结果，绝不包含控制指令
3. 严格对齐：复用已有 LearningPromptContext 与 StructuredAIResponse
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from gateway.models import LearningPromptContext, StructuredAIResponse


class EvaluationCategory(str, Enum):
    """评估用例类别枚举"""
    NORMAL = "NORMAL"
    LOW_MASTERY = "LOW_MASTERY"
    HIGH_MASTERY = "HIGH_MASTERY"
    BOUNDARY = "BOUNDARY"
    SAFETY = "SAFETY"
    ADVERSARIAL = "ADVERSARIAL"


class EvaluationCase(BaseModel):
    """强类型离线评测用例定义"""
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., description="唯一用例标识符，例如 CASE_NORMAL_01")
    category: EvaluationCategory = Field(..., description="评估类别")
    description: str = Field(..., description="用例意图与学情场景描述")
    learning_context: LearningPromptContext = Field(..., description="标准只读学情提示词上下文")
    candidate_response: StructuredAIResponse = Field(..., description="待评估候选 AI 响应")
    expected_behavior: List[str] = Field(default_factory=list, description="预期行为约束标签列表")
    forbidden_behavior: List[str] = Field(default_factory=list, description="显式禁止行为标签列表")
    expected_valid: bool = Field(default=True, description="预期该响应是否合法通过语义校验")
    expected_violations: List[str] = Field(default_factory=list, description="若预期不合法，预期的违规标签列表")


class SemanticValidationResult(BaseModel):
    """语义校验结果模型（5 维细粒度判决与安全硬门禁）"""
    model_config = ConfigDict(extra="forbid")

    valid: bool = Field(..., description="综合有效性判定（所有维度必须均为 True）")
    factual_consistency: bool = Field(..., description="事实一致性判定")
    context_relevance: bool = Field(..., description="上下文相关性判定")
    policy_compliant: bool = Field(..., description="策略合规性硬门禁（False 则 valid 必为 False）")
    explanation_quality: bool = Field(..., description="解释质量启发式判定")
    actionability: bool = Field(..., description="学习行动指导性判定")
    violations: List[str] = Field(default_factory=list, description="违规项标签列表")
    scores: Dict[str, float] = Field(default_factory=dict, description="各维度定量得分 (0.0 ~ 1.0)")
    validator_version: str = Field(default="v1.0", description="校验器版本号")


class CaseEvaluationResult(BaseModel):
    """单个用例评估执行明细"""
    model_config = ConfigDict(extra="forbid")

    case_id: str
    category: EvaluationCategory
    validation_result: SemanticValidationResult
    passed: bool = Field(..., description="用例执行结果是否与预期完全一致")
    expected_valid: bool
    expected_violations: List[str] = Field(default_factory=list)
    actual_violations: List[str] = Field(default_factory=list)
    state_unchanged: bool = Field(default=True, description="上下文状态是否严格未变")
    duration_ms: float = Field(default=0.0, description="评估耗时毫秒数")


class EvaluationReport(BaseModel):
    """评估套件全量聚合报告"""
    model_config = ConfigDict(extra="forbid")

    dataset_version: str
    validator_version: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    category_statistics: Dict[str, Dict[str, Any]]
    duration_ms: float = 0.0
    all_safety_cases_passed: bool = True
    core_state_unchanged: bool = True
    violations_summary: List[Dict[str, Any]] = Field(default_factory=list)
