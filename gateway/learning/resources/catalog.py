# -*- coding: utf-8 -*-
"""
gateway.learning.resources.catalog
==================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-C
学习资源静态全景目录 (Learning Resource Catalog)

红线规范：
1. 100% 覆盖微观经济学全图谱 30 个考点 (K01~K30)
2. 每个考点至少配备 3 项标准学习材料：
   - 考点精要微卡 (CONCEPT_CARD)
   - 典型生活与商业例题精析 (EXAMPLE)
   - 靶向通关微测验 (PRACTICE)
   并针对重点考点配备精讲讲义 (DOCUMENT) 与动画导学 (VIDEO)
3. 内容严格由内部高质量知识库 gateway.content.concept_cards 动态组装，
   绝不制造虚假外链（全部 source="xuehai_internal", is_external=False, source_url=None）
4. 文件位于 gateway/learning/resources/，绝不写入 data/seeds/（遵守架构冻结红线）
"""

from typing import Dict, List, Optional
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.resources.models import LearningResource, ResourceType


def _build_catalog() -> Dict[str, LearningResource]:
    catalog: Dict[str, LearningResource] = {}

    # 包含动画导学的代表性重点考点
    VIDEO_FEATURED_KPS = {"K01", "K02", "K04", "K08", "K11", "K14", "K19", "K24", "K28", "K30"}

    # 遍历全图谱 30 个考点
    for kid in [f"K{i:02d}" for i in range(1, 31)]:
        card = CONCEPT_CARDS.get(kid)
        if not card:
            continue

        kid_lower = kid.lower()

        # 1. 考点精要微卡 (CONCEPT_CARD)
        concept_res = LearningResource(
            resource_id=f"res_{kid_lower}_concept",
            knowledge_id=kid,
            resource_type=ResourceType.CONCEPT_CARD,
            title=f"{card.knowledge_name} 考点精要微卡",
            description=card.one_line_intuition,
            source="xuehai_internal",
            source_url=None,
            estimated_minutes=2,
            difficulty=0.30,
            summary=f"【核心概念】{card.core_concept}\n【学习目标】{card.learning_objective}",
            content_ref=kid,
            is_external=False,
            priority=85,
            metadata={
                "chapter": card.chapter,
                "reading_time_seconds": card.reading_time_seconds,
                "learning_objective": card.learning_objective,
            },
        )
        catalog[concept_res.resource_id] = concept_res

        # 2. 典型生活与商业例题精析 (EXAMPLE)
        example_res = LearningResource(
            resource_id=f"res_{kid_lower}_example",
            knowledge_id=kid,
            resource_type=ResourceType.EXAMPLE,
            title=f"{card.knowledge_name} 典型生活与商业实例精析",
            description=f"围绕【{card.knowledge_name}】的典型生活与商业案例深入拆解，透析解题思路。",
            source="xuehai_internal",
            source_url=None,
            estimated_minutes=3,
            difficulty=0.50,
            summary=f"【典型案例】{card.simple_example}\n【易错陷阱】{card.common_misconceptions}",
            content_ref=f"example_{kid_lower}",
            is_external=False,
            priority=75,
            metadata={
                "chapter": card.chapter,
                "example_detail": card.simple_example,
                "misconceptions": card.common_misconceptions,
            },
        )
        catalog[example_res.resource_id] = example_res

        # 3. 靶向通关微测验 (PRACTICE)
        practice_res = LearningResource(
            resource_id=f"res_{kid_lower}_practice",
            knowledge_id=kid,
            resource_type=ResourceType.PRACTICE,
            title=f"{card.knowledge_name} 靶向通关微测验",
            description=f"针对【{card.knowledge_name}】的微测验，检验概念掌握度并驱动掌握度更新。",
            source="xuehai_internal",
            source_url=None,
            estimated_minutes=4,
            difficulty=0.60,
            summary=f"包含针对【{card.knowledge_name}】的定向单选题测试，测验通过可推动学习路径向前演进。",
            content_ref=f"quiz_{kid}",
            is_external=False,
            priority=70,
            metadata={
                "chapter": card.chapter,
                "quiz_target": kid,
            },
        )
        catalog[practice_res.resource_id] = practice_res

        # 4. 精讲讲义与避坑指南 (DOCUMENT)
        doc_res = LearningResource(
            resource_id=f"res_{kid_lower}_document",
            knowledge_id=kid,
            resource_type=ResourceType.DOCUMENT,
            title=f"{card.knowledge_name} 核心讲义与避坑指南",
            description=f"系统归纳【{card.knowledge_name}】的核心定义、推导脉络与考试常见误区。",
            source="xuehai_internal",
            source_url=None,
            estimated_minutes=5,
            difficulty=0.40,
            summary=f"【讲义精要】{card.core_concept}\n【避坑指南】{card.common_misconceptions}",
            content_ref=f"doc_{kid_lower}",
            is_external=False,
            priority=60,
            metadata={
                "chapter": card.chapter,
                "misconceptions": card.common_misconceptions,
            },
        )
        catalog[doc_res.resource_id] = doc_res

        # 5. 动画导学微视频 (VIDEO) - 针对重点考点
        if kid in VIDEO_FEATURED_KPS:
            video_res = LearningResource(
                resource_id=f"res_{kid_lower}_video",
                knowledge_id=kid,
                resource_type=ResourceType.VIDEO,
                title=f"{card.knowledge_name} 3分钟动画导学",
                description=f"3分钟动态图解【{card.knowledge_name}】的核心直觉与现实应用。",
                source="xuehai_internal",
                source_url=None,
                estimated_minutes=3,
                difficulty=0.35,
                summary=f"【动画导学】通过直观动画生动演示：{card.one_line_intuition}",
                content_ref=f"video_{kid_lower}",
                is_external=False,
                priority=65,
                metadata={
                    "chapter": card.chapter,
                    "video_type": "interactive_animation",
                },
            )
            catalog[video_res.resource_id] = video_res

    return catalog


RESOURCE_CATALOG: Dict[str, LearningResource] = _build_catalog()


def get_resource_by_id(resource_id: str) -> Optional[LearningResource]:
    """根据全局唯一资源ID获取资源"""
    return RESOURCE_CATALOG.get(resource_id)


def get_resources_by_knowledge(
    knowledge_id: str,
    resource_type: Optional[ResourceType] = None,
) -> List[LearningResource]:
    """获取指定考点下的所有学习资源，支持按类型过滤，默认按 priority 降序"""
    items = [
        res for res in RESOURCE_CATALOG.values()
        if res.knowledge_id == knowledge_id
        and (resource_type is None or res.resource_type == resource_type)
    ]
    # 确定性排序：priority DESC, resource_id ASC
    return sorted(items, key=lambda x: (-x.priority, x.resource_id))


def get_all_resources() -> List[LearningResource]:
    """获取全量静态资源列表"""
    return sorted(list(RESOURCE_CATALOG.values()), key=lambda x: (x.knowledge_id, -x.priority, x.resource_id))
