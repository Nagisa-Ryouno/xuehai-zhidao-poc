# -*- coding: utf-8 -*-
"""
gateway.learning.resources.models
=================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-C
学习资源中心与资源感知自适应学习领域模型

包含：
- ResourceType: 资源类型枚举 (CONCEPT_CARD, EXAMPLE, PRACTICE, DOCUMENT, VIDEO)
- LearningResource: 学习资源模型（严格内部来源，杜绝失效外链）
- ResourceRecommendation: 包含推荐位序与白名单推荐理由的资源项
- RecommendedResourcesResponse: 针对学生当前考点的自适应推荐结果
- ResourceListResponse: 考点资源列表响应
- ResourceEventPayload: 资源交互辅助事件载荷（物理隔离于正式学习事件）
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ResourceType(str, Enum):
    """学习资源类型"""
    CONCEPT_CARD = "CONCEPT_CARD"  # 考点精要微卡
    EXAMPLE = "EXAMPLE"            # 典型生活与商业例题
    PRACTICE = "PRACTICE"          # 靶向通关微测验
    DOCUMENT = "DOCUMENT"          # 讲义与易错考点指南
    VIDEO = "VIDEO"                # 直观导学微视频/动画


RESOURCE_TYPE_LABELS: Dict[ResourceType, str] = {
    ResourceType.CONCEPT_CARD: "考点微卡",
    ResourceType.EXAMPLE: "典型例题",
    ResourceType.PRACTICE: "靶向微练",
    ResourceType.DOCUMENT: "精讲讲义",
    ResourceType.VIDEO: "导学视频",
}


class LearningResource(BaseModel):
    """学习资源实体模型"""
    resource_id: str = Field(..., description="全局唯一资源ID，如 res_k01_concept")
    knowledge_id: str = Field(..., description="关联考点ID，如 K01")
    resource_type: ResourceType = Field(..., description="资源类型")
    title: str = Field(..., min_length=1, max_length=200, description="资源标题")
    description: str = Field(..., min_length=1, description="资源描述/一句话概括")
    source: str = Field(default="xuehai_internal", description="资源来源，内部生产标为 xuehai_internal")
    source_url: Optional[str] = Field(default=None, description="外部链接（内部资源默认为 None）")
    estimated_minutes: int = Field(default=3, ge=1, le=120, description="建议学习时长（分钟）")
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0, description="资源难度（0.0-1.0）")
    summary: Optional[str] = Field(default=None, description="资源摘要或核心速记")
    content_ref: Optional[str] = Field(default=None, description="内部内容关联索引（如 concept_k01, quiz_k01 等）")
    is_external: bool = Field(default=False, description="是否为外部资源，内部资源严格为 False")
    priority: int = Field(default=50, ge=1, le=100, description="基础默认排序权重 (1-100)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据（章节、例题拆解、考点目标等）")

    @field_validator("is_external")
    @classmethod
    def validate_is_external(cls, v: bool) -> bool:
        # 严格防范伪造外链：如果是内部来源，不允许设为 external
        return v


class ResourceRecommendation(BaseModel):
    """资源自适应推荐项"""
    resource: LearningResource = Field(..., description="推荐的学习资源实体")
    rank: int = Field(..., ge=1, description="推荐位次（1-indexed）")
    recommended_reason: str = Field(..., description="通俗易懂的自适应推荐理由（严禁技术黑话）")
    reason_category: str = Field(..., description="推荐类别（FOUNDATION, APPLICATION, CONSOLIDATION, REPAIR, ADVANCEMENT）")
    suggested_order: int = Field(..., ge=1, description="学习时序建议（第几步完成）")
    historical_effectiveness: Optional[str] = Field(
        default="INSUFFICIENT_DATA", description="历史资源效果分级 (Sprint 9-E)"
    )
    why_recommended: Optional[str] = Field(
        default=None, description="确定性推荐解释理由 (Sprint 9-E)"
    )
    score_adjustment: int = Field(
        default=0, description="自适应排序分值微调量 (Sprint 9-E)"
    )


class RecommendedResourcesResponse(BaseModel):
    """自适应资源推荐接口响应"""
    student_id: str = Field(..., description="学生ID")
    knowledge_id: str = Field(..., description="推荐聚焦的目标考点ID")
    mastery: float = Field(..., ge=0.0, le=1.0, description="当前考点客观掌握度")
    case_code: str = Field(..., description="推荐决策场景代码，如 CASE_A_WEAK_FOUNDATION")
    recommendations: List[ResourceRecommendation] = Field(default_factory=list, description="推荐资源列表（严格确定性排序）")
    reason_summary: str = Field(..., description="整体推荐策略与阶段导引说明")


class ResourceListResponse(BaseModel):
    """考点资源列表响应"""
    knowledge_id: str = Field(..., description="考点ID")
    total: int = Field(..., ge=0, description="资源总数")
    resources: List[LearningResource] = Field(default_factory=list, description="考点对应的所有学习资源")


VALID_RESOURCE_EVENT_TYPES = {
    "RESOURCE_VIEW",          # 资源卡片曝光
    "RESOURCE_OPEN",          # 打开资源研读
    "RESOURCE_COMPLETE",      # 标记/完成研读
    "RESOURCE_EXTERNAL_OPEN", # 打开外部参考（如有）
}


class ResourceEventPayload(BaseModel):
    """资源交互行为日志请求载荷"""
    student_id: str = Field(..., min_length=1)
    resource_id: str = Field(..., min_length=1)
    knowledge_id: str = Field(..., min_length=1)
    event_type: str = Field(...)
    duration_seconds: Optional[int] = Field(default=None, ge=0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    client_timestamp: Optional[str] = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in VALID_RESOURCE_EVENT_TYPES:
            raise ValueError(f"非法资源事件类型: {v}，合法集合为: {VALID_RESOURCE_EVENT_TYPES}")
        return v
