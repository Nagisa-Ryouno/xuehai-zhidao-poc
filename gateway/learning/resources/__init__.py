# -*- coding: utf-8 -*-
"""
gateway.learning.resources
==========================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-C
学习资源中心与资源感知自适应学习模块 (Learning Resource Hub & Adaptive Learning)

对外导出：
- 领域模型: ResourceType, LearningResource, ResourceRecommendation, RecommendedResourcesResponse, ResourceListResponse, ResourceEventPayload
- 静态全景目录: RESOURCE_CATALOG, get_resource_by_id, get_resources_by_knowledge, get_all_resources
- 确定性推荐引擎: ResourceResolver, default_resource_resolver
- 独立事件持久化: record_resource_event, get_student_resource_events, VALID_RESOURCE_EVENT_TYPES
"""

from gateway.learning.resources.models import (
    ResourceType,
    LearningResource,
    ResourceRecommendation,
    RecommendedResourcesResponse,
    ResourceListResponse,
    ResourceEventPayload,
    RESOURCE_TYPE_LABELS,
    VALID_RESOURCE_EVENT_TYPES,
)
from gateway.learning.resources.catalog import (
    RESOURCE_CATALOG,
    get_resource_by_id,
    get_resources_by_knowledge,
    get_all_resources,
)
from gateway.learning.resources.resolver import (
    ResourceResolver,
    default_resource_resolver,
)
from gateway.learning.resources.events import (
    record_resource_event,
    get_student_resource_events,
)

__all__ = [
    "ResourceType",
    "LearningResource",
    "ResourceRecommendation",
    "RecommendedResourcesResponse",
    "ResourceListResponse",
    "ResourceEventPayload",
    "RESOURCE_TYPE_LABELS",
    "VALID_RESOURCE_EVENT_TYPES",
    "RESOURCE_CATALOG",
    "get_resource_by_id",
    "get_resources_by_knowledge",
    "get_all_resources",
    "ResourceResolver",
    "default_resource_resolver",
    "record_resource_event",
    "get_student_resource_events",
]
