# -*- coding: utf-8 -*-
"""
gateway.learning.resources.service
==================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-A
学习资源统一查询适配层 (Unified Learning Resource Service)

设计规范与安全红线：
1. 目录物理分离，查询统一收敛：
   - 内部 130 项标准资源维护于 RESOURCE_CATALOG；
   - 外部中国大学MOOC资源维护于 MOOC_RESOURCE_CATALOG；
   - 本服务提供只读统一查询，保持两套底层目录的物理隔离；
2. 推荐体系严格隔离：
   - 本统一查询层仅面向普通资源展示 API (ResourceHub)；
   - 严禁让外部 MOOC 资源进入 ResourceResolver 候选池；
3. 来源过滤确定性：
   - 支持 source="xuehai_internal" (或 internal) 只查内部；
   - 支持 source="china_mooc" (或 mooc) 只查 MOOC；
   - 支持 source="all" (或 None) 统一组合（内部在前，MOOC在后）；
4. 严格 Fail-Closed 安全防线：
   - 外部 MOOC 资源若 source_url 未通过 security 白名单校验，坚决拦截不予输出；
5. 确定性排序稳定输出：
   - 内部资源保持现有 (-priority, resource_id ASC)；
   - MOOC 资源保持 (-priority, resource_id ASC)；
   - 组合输出保证内部在前、外部在后，零随机数，零时间戳扰动。
"""

from typing import List, Optional
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.resources.models import LearningResource, ResourceType
from gateway.learning.resources.catalog import (
    get_resource_by_id as get_internal_resource_by_id,
    get_resources_by_knowledge as get_internal_resources_by_knowledge,
    get_all_resources as get_all_internal_resources,
)
from gateway.learning.resources.mooc_catalog import (
    get_mooc_resource_by_id,
    get_mooc_resources_by_knowledge,
    get_all_mooc_resources,
)
from gateway.learning.resources.security import validate_external_mooc_url


def get_unified_resource_by_id(resource_id: str) -> Optional[LearningResource]:
    """
    根据全局唯一资源 ID 检索资源（优先内部资源，次查 MOOC 外部资源）。
    若为 MOOC 资源，严格执行 fail-closed 安全外链校验。
    """
    if not resource_id:
        return None

    # 1. 优先在内部 130 项资源目录中查找
    internal_res = get_internal_resource_by_id(resource_id)
    if internal_res:
        return internal_res

    # 2. 次在 MOOC 外部资源目录中查找
    mooc_res = get_mooc_resource_by_id(resource_id)
    if mooc_res:
        # Fail-closed 安全断言：若存在 source_url 必须通过安全校验
        if mooc_res.source_url and not validate_external_mooc_url(mooc_res.source_url):
            return None
        return mooc_res

    return None


def get_unified_resources_by_knowledge(
    knowledge_id: str,
    resource_type: Optional[ResourceType] = None,
    source: Optional[str] = "all",
) -> List[LearningResource]:
    """
    获取指定考点下的学习材料列表，支持来源过滤与类型过滤。
    
    :param knowledge_id: 目标考点 ID (如 "K01")
    :param resource_type: 可选资源类型过滤 (CONCEPT_CARD, EXAMPLE, PRACTICE, DOCUMENT, VIDEO)
    :param source: 来源过滤，支持 "all" (默认), "xuehai_internal" (或 internal), "china_mooc" (或 mooc)
    :return: 确定性排序的资源列表（内部在前，MOOC在后）
    """
    if knowledge_id not in CONCEPT_CARDS:
        return []

    norm_source = (source or "all").strip().lower()

    # 1. 内部资源查询
    internal_items: List[LearningResource] = []
    if norm_source in ("all", "xuehai_internal", "internal"):
        internal_items = get_internal_resources_by_knowledge(
            knowledge_id=knowledge_id,
            resource_type=resource_type,
        )

    # 2. MOOC 外部资源查询（带 fail-closed 安全防线）
    mooc_items: List[LearningResource] = []
    if norm_source in ("all", "china_mooc", "mooc"):
        raw_mooc_items = get_mooc_resources_by_knowledge(
            knowledge_id=knowledge_id,
            resource_type=resource_type,
        )
        for item in raw_mooc_items:
            # 严格防范非法外链与伪造来源
            if not item.is_external or item.source != "china_mooc":
                continue
            if item.source_url and not validate_external_mooc_url(item.source_url):
                continue
            mooc_items.append(item)

    # 3. 确定性合并输出：内部资源保持在前，MOOC 资源置后
    return internal_items + mooc_items


def get_all_unified_resources(
    source: Optional[str] = "all",
) -> List[LearningResource]:
    """
    获取全量学习资源列表（内部 + MOOC）。
    """
    norm_source = (source or "all").strip().lower()

    internal_items: List[LearningResource] = []
    if norm_source in ("all", "xuehai_internal", "internal"):
        internal_items = get_all_internal_resources()

    mooc_items: List[LearningResource] = []
    if norm_source in ("all", "china_mooc", "mooc"):
        for item in get_all_mooc_resources():
            if item.is_external and item.source == "china_mooc":
                if not item.source_url or validate_external_mooc_url(item.source_url):
                    mooc_items.append(item)

    return internal_items + mooc_items
