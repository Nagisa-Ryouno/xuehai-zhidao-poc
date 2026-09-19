# -*- coding: utf-8 -*-
"""
gateway.ai.recommendation.models
================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B / Phase 2
AI 个性化推荐引擎数据契约模型

设计规范与架构红线：
1. AI 永远是辅助候选提供者，绝对无生产决策权 (allow_production_decision=False)；
2. RecommendationCandidate 严格仅包含 knowledge_id, resource_id, reason 三项字段，严禁 rank、decision 或 mutation；
3. ValidatedRecommendation 补充权威系统元数据 (title, resource_type, source)；
4. RecommendationRequest 严禁由客户端指定 model (模型完全由服务端配置决定)；
5. 严格 extra='forbid' 白名单拦截非预期参数；
6. 严格定义禁止出现的越权生产决策字段集合 RECOMMENDATION_FORBIDDEN_FIELDS。
"""

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, ConfigDict, Field

# 越权学习决策与数据覆写禁止字段集合
RECOMMENDATION_FORBIDDEN_FIELDS: Set[str] = {
    "decision",
    "allow_production_decision",
    "mutation",
    "event",
    "path_update",
    "mastery_update",
    "action",
    "priority",
    "rank",
    "set_mastery",
    "modify_mastery",
    "mastery",
    "mastery_probability",
    "path_state",
    "unlock",
    "lock",
    "unlock_nodes",
    "state_transition",
    "mutate_path",
    "change_path",
    "next_state",
    "next_path",
    "learning_path_update",
    "next_action_command",
    "bkt",
    "bkt_update",
    "update_bkt",
    "production_decision",
    "learning_event",
}


class RecommendationCandidate(BaseModel):
    """
    AI 推荐候选原始输出契约 (AI 只能生成候选，不能做最终决策)
    
    绝对禁止包含 rank、decision、mutation 等生产控制字段。
    """
    model_config = ConfigDict(extra="forbid")

    knowledge_id: str = Field(..., description="考点唯一标识符 (如 K03)")
    resource_id: str = Field(..., description="学习资源唯一标识符 (如 R031)")
    reason: str = Field(..., description="推荐理由说明文本 (解释性文本，非系统断言)")


class ValidatedRecommendation(BaseModel):
    """
    经过确定性校验并由系统补全权威元数据的最终推荐对象
    """
    model_config = ConfigDict(extra="forbid")

    knowledge_id: str = Field(..., description="考点唯一标识符")
    resource_id: str = Field(..., description="资源唯一标识符")
    reason: str = Field(..., description="经过合规校验的推荐理由")
    title: str = Field(..., description="权威资源标题 (由系统目录注入，非 AI 自行拟定)")
    resource_type: str = Field(..., description="权威资源类型")
    source: str = Field(..., description="权威资源来源 (xuehai_internal / china_mooc)")


class KnowledgeStateSnapshot(BaseModel):
    """只读知识状态事实快照"""
    model_config = ConfigDict(extra="forbid")

    knowledge_id: str = Field(..., description="考点 ID")
    knowledge_name: str = Field(..., description="考点名称")
    mastery: float = Field(..., description="当前掌握度")
    path_state: str = Field(..., description="当前路径状态")


class ResourceCandidateSnapshot(BaseModel):
    """只读候选资源元数据快照"""
    model_config = ConfigDict(extra="forbid")

    resource_id: str = Field(..., description="资源 ID")
    knowledge_id: str = Field(..., description="所属考点 ID")
    resource_type: str = Field(..., description="资源类型")
    title: str = Field(..., description="资源标题")
    description: str = Field(..., description="资源简要描述")
    source: str = Field(..., description="资源来源渠道")


class RecommendationContext(BaseModel):
    """
    确定性只读推荐上下文快照 (严格脱敏，零 PII)
    """
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(..., description="脱敏/伪匿名学生标识符 (如 student_s001)")
    current_focus: str = Field(..., description="当前权威焦点考点 (如 K03)")
    knowledge_states: List[KnowledgeStateSnapshot] = Field(..., description="相关考点状态快照")
    resources: List[ResourceCandidateSnapshot] = Field(..., description="允许推荐的候选资源列表")


class RecommendationRequest(BaseModel):
    """
    推荐生成请求契约
    
    安全原则：严格杜绝客户端指定 model 字段，模型由服务端配置统一裁决。
    """
    model_config = ConfigDict(extra="forbid")

    student_id: Optional[str] = Field(default=None, description="可选显式指定学生标识符")
    knowledge_id: Optional[str] = Field(default=None, description="可选显式焦点考点覆盖 (仅限合法考点)")
    max_recommendations: int = Field(default=3, ge=1, le=3, description="最大推荐候选数量 (上限 3)")


class RecommendationResponse(BaseModel):
    """
    推荐生成统一响应契约
    """
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(..., description="脱敏学生标识符")
    recommendations: List[ValidatedRecommendation] = Field(..., description="已通过确定性校验的推荐项列表")
    source: str = Field(default="deepseek", description="推荐候选提供商")
    validated: bool = Field(default=True, description="确定性校验通过标记")
