# -*- coding: utf-8 -*-
"""
gateway.learning.resources.mooc_catalog
=======================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-A / Handoff Freeze Correction
中国大学MOOC外部资源独立精选目录 (China University MOOC External Resource Catalog)

设计规范与安全红线：
1. 物理隔离：独立维护 MOOC_RESOURCE_CATALOG，绝不写入原有 RESOURCE_CATALOG，
   严防破坏 Sprint 9-C 内部 130 项资源纯净性与历史测试契约；
2. 权威模型复用：严格复用已有 LearningResource 领域模型与 ResourceType 枚举 (VIDEO, DOCUMENT)；
3. 严格数据契约：
   - source == "china_mooc"
   - is_external == True
   - 稳定唯一 ID：mooc_{knowledge_id_lower}_{short_slug}，严禁使用随机 UUID 或时间戳；
   - 绝不编造虚假资源、虚构章节序号或伪造 30/30 覆盖率；如实保持精选示范目录（共 12 项）；
4. 官方核验课程源与官方十讲规范：
   - 北京大学《微观经济学之供给与需求》（官方课程代码：PKU-1003090003）
   - 武汉大学《微观经济学》（主讲：文建东 教授，官方课程代码：whu-23003，官方全课明确为十讲结构）
   - 杜绝一切超出十讲范围的虚假讲次（禁止出现第十一讲、十四讲、十九讲等虚构编号）；
5. 纯确定性与时间无关：排序规则统一为 (-priority, resource_id)，多次调用返回稳定有序列表。
"""

from typing import Dict, List, Optional
from gateway.learning.resources.models import LearningResource, ResourceType
from gateway.learning.resources.security import validate_external_mooc_url

PKU_MOOC_COURSE_ID = "PKU-1003090003"
WHU_MOOC_COURSE_ID = "whu-23003"

PKU_MOOC_URL = f"https://www.icourse163.org/course/{PKU_MOOC_COURSE_ID}"
WHU_MOOC_URL = f"https://www.icourse163.org/course/{WHU_MOOC_COURSE_ID}"


def _build_mooc_catalog() -> Dict[str, LearningResource]:
    """
    静态构建中国大学MOOC国家级一流公开课优质拓展学习资源精选目录。
    严格对齐北京大学与武汉大学官方开课大纲与真实十讲结构（共 12 项精选）。
    """
    raw_resources: List[LearningResource] = [
        # K01: 稀缺性与经济学基本问题 (WHU 第一讲)
        LearningResource(
            resource_id="mooc_k01_scarcity",
            knowledge_id="K01",
            resource_type=ResourceType.VIDEO,
            title="中国大学MOOC·名校微课：稀缺性与经济学导论",
            description="来自国家级一流本科公开课，系统阐述稀缺性、选择与资源配置等经济学核心命题。",
            source="china_mooc",
            source_url=WHU_MOOC_URL,
            estimated_minutes=15,
            difficulty=0.35,
            summary="【名校慕课精选】武汉大学文建东教授微观经济学公开课，剖析经济学独特思维方式。",
            content_ref=None,
            is_external=True,
            priority=65,
            metadata={
                "provider": "中国大学MOOC",
                "university": "武汉大学",
                "instructor": "文建东 教授",
                "course": "微观经济学",
                "course_id": WHU_MOOC_COURSE_ID,
                "chapter": "第一讲 导论与基本概念",
            },
        ),
        # K02: 机会成本与生产可能性边界 (WHU 第一讲)
        LearningResource(
            resource_id="mooc_k02_opportunity_cost",
            knowledge_id="K02",
            resource_type=ResourceType.VIDEO,
            title="中国大学MOOC·名校微课：机会成本与生产可能性边界",
            description="通过生产可能性边界模型透析机会成本与资源配置效率，解析理性决策的边际权衡法则。",
            source="china_mooc",
            source_url=WHU_MOOC_URL,
            estimated_minutes=18,
            difficulty=0.40,
            summary="【名校慕课精选】武汉大学文建东教授讲授，从机会成本视角审视一切经济选择。",
            content_ref=None,
            is_external=True,
            priority=65,
            metadata={
                "provider": "中国大学MOOC",
                "university": "武汉大学",
                "instructor": "文建东 教授",
                "course": "微观经济学",
                "course_id": WHU_MOOC_COURSE_ID,
                "chapter": "第一讲 导论与基本概念",
            },
        ),
        # K03: 理性人假设与需求原理 (PKU 需求与供给分析)
        LearningResource(
            resource_id="mooc_k03_demand_shifts",
            knowledge_id="K03",
            resource_type=ResourceType.DOCUMENT,
            title="中国大学MOOC·名校讲义：理性选择与需求原理",
            description="深入剖析经济人理性选择假定，结合替代品与互补品变动区分‘需求量变动’与‘需求变动’。",
            source="china_mooc",
            source_url=PKU_MOOC_URL,
            estimated_minutes=12,
            difficulty=0.45,
            summary="【慕课精讲讲义】北京大学微观经济学之供给与需求讲义，系统梳理需求曲线与理性决策。",
            content_ref=None,
            is_external=True,
            priority=60,
            metadata={
                "provider": "中国大学MOOC",
                "university": "北京大学",
                "instructor": "徐高 教授",
                "course": "微观经济学之供给与需求",
                "course_id": PKU_MOOC_COURSE_ID,
                "chapter": "需求与供给分析",
            },
        ),
        # K04: 供求变动与市场均衡机制 (WHU 第二讲)
        LearningResource(
            resource_id="mooc_k04_equilibrium",
            knowledge_id="K04",
            resource_type=ResourceType.VIDEO,
            title="中国大学MOOC·名校微课：供求与市场均衡机制",
            description="分析供给曲线与需求曲线的相互作用，阐释超额供求驱动下的均衡价格形成与市场出清动力。",
            source="china_mooc",
            source_url=WHU_MOOC_URL,
            estimated_minutes=20,
            difficulty=0.45,
            summary="【名校慕课精选】武汉大学文建东教授讲授，动态推导‘看不见的手’的微观动力机制。",
            content_ref=None,
            is_external=True,
            priority=65,
            metadata={
                "provider": "中国大学MOOC",
                "university": "武汉大学",
                "instructor": "文建东 教授",
                "course": "微观经济学",
                "course_id": WHU_MOOC_COURSE_ID,
                "chapter": "第二讲 供求与市场均衡",
            },
        ),
        # K05: 需求价格弹性及其应用 (WHU 第三讲)
        LearningResource(
            resource_id="mooc_k05_elasticity",
            knowledge_id="K05",
            resource_type=ResourceType.VIDEO,
            title="中国大学MOOC·名校微课：弹性理论及其应用",
            description="定量测度价格变动引起的反应程度，结合中点公式证明价格弹性与厂商总收益的数理关系。",
            source="china_mooc",
            source_url=WHU_MOOC_URL,
            estimated_minutes=25,
            difficulty=0.50,
            summary="【名校慕课精选】弹性理论综合专题，解析富有弹性与缺乏弹性情境下的收益决策。",
            content_ref=None,
            is_external=True,
            priority=65,
            metadata={
                "provider": "中国大学MOOC",
                "university": "武汉大学",
                "instructor": "文建东 教授",
                "course": "微观经济学",
                "course_id": WHU_MOOC_COURSE_ID,
                "chapter": "第三讲 弹性理论及其应用",
            },
        ),
        # K08: 消费者行为理论与效用分析 (WHU 第四讲)
        LearningResource(
            resource_id="mooc_k08_consumer_equilibrium",
            knowledge_id="K08",
            resource_type=ResourceType.VIDEO,
            title="中国大学MOOC·名校微课：消费者行为理论与效用分析",
            description="边际替代率递减规律（MRS）、预算约束线与无差异曲线相切条件，推导效用最大化消费束。",
            source="china_mooc",
            source_url=WHU_MOOC_URL,
            estimated_minutes=22,
            difficulty=0.55,
            summary="【名校慕课精选】序数效用论精讲，系统建立消费者最优选择的几何与经济学直觉。",
            content_ref=None,
            is_external=True,
            priority=65,
            metadata={
                "provider": "中国大学MOOC",
                "university": "武汉大学",
                "instructor": "文建东 教授",
                "course": "微观经济学",
                "course_id": WHU_MOOC_COURSE_ID,
                "chapter": "第四讲 消费者行为理论",
            },
        ),
        # K11: 生产理论与生产函数 (WHU 第五讲)
        LearningResource(
            resource_id="mooc_k11_production_function",
            knowledge_id="K11",
            resource_type=ResourceType.VIDEO,
            title="中国大学MOOC·名校微课：生产理论与边际报酬递减",
            description="短期生产函数中总产量、平均产量与边际产量的几何对应关系与要素合理投入区域划分。",
            source="china_mooc",
            source_url=WHU_MOOC_URL,
            estimated_minutes=20,
            difficulty=0.55,
            summary="【名校慕课精选】生产三阶段分析与柯布-道格拉斯生产函数理论解析。",
            content_ref=None,
            is_external=True,
            priority=65,
            metadata={
                "provider": "中国大学MOOC",
                "university": "武汉大学",
                "instructor": "文建东 教授",
                "course": "微观经济学",
                "course_id": WHU_MOOC_COURSE_ID,
                "chapter": "第五讲 生产理论",
            },
        ),
        # K14: 成本理论与成本曲线 (WHU 第六讲)
        LearningResource(
            resource_id="mooc_k14_cost_curves",
            knowledge_id="K14",
            resource_type=ResourceType.DOCUMENT,
            title="中国大学MOOC·名校讲义：短期与长期成本理论",
            description="固定成本、可变成本、边际成本与平均成本等曲线族之间的最低点穿刺与几何约束关系。",
            source="china_mooc",
            source_url=WHU_MOOC_URL,
            estimated_minutes=15,
            difficulty=0.55,
            summary="【慕课精讲讲义】成本曲线族综合坐标图解，理清短期成本向长期成本的包络推导。",
            content_ref=None,
            is_external=True,
            priority=60,
            metadata={
                "provider": "中国大学MOOC",
                "university": "武汉大学",
                "instructor": "文建东 教授",
                "course": "微观经济学",
                "course_id": WHU_MOOC_COURSE_ID,
                "chapter": "第六讲 成本理论",
            },
        ),
        # K19: 完全竞争市场与厂商均衡 (WHU 第七讲)
        LearningResource(
            resource_id="mooc_k19_perfect_competition",
            knowledge_id="K19",
            resource_type=ResourceType.VIDEO,
            title="中国大学MOOC·名校微课：完全竞争市场与厂商决策",
            description="价格接受者假定、P=MC 利润最大化原则与短期停业临界点（P=AVC最低点）的经济含义推导。",
            source="china_mooc",
            source_url=WHU_MOOC_URL,
            estimated_minutes=22,
            difficulty=0.65,
            summary="【名校慕课精选】完全竞争市场结构核心，零经济利润与资源配置效率剖析。",
            content_ref=None,
            is_external=True,
            priority=65,
            metadata={
                "provider": "中国大学MOOC",
                "university": "武汉大学",
                "instructor": "文建东 教授",
                "course": "微观经济学",
                "course_id": WHU_MOOC_COURSE_ID,
                "chapter": "第七讲 完全竞争市场",
            },
        ),
        # K24: 不完全竞争市场与垄断定价 (WHU 第八讲)
        LearningResource(
            resource_id="mooc_k24_monopoly",
            knowledge_id="K24",
            resource_type=ResourceType.VIDEO,
            title="中国大学MOOC·名校微课：不完全竞争与垄断定价",
            description="垄断势力的成因、边际收益与价格的关系、价格歧视机制以及社会福利无谓损失（Deadweight Loss）。",
            source="china_mooc",
            source_url=WHU_MOOC_URL,
            estimated_minutes=25,
            difficulty=0.70,
            summary="【名校慕课精选】不完全竞争市场结构，透析完全垄断与垄断竞争厂商的最优决策。",
            content_ref=None,
            is_external=True,
            priority=65,
            metadata={
                "provider": "中国大学MOOC",
                "university": "武汉大学",
                "instructor": "文建东 教授",
                "course": "微观经济学",
                "course_id": WHU_MOOC_COURSE_ID,
                "chapter": "第八讲 不完全竞争市场",
            },
        ),
        # K28: 市场失灵与外部性 (WHU 第九讲)
        LearningResource(
            resource_id="mooc_k28_externalities",
            knowledge_id="K28",
            resource_type=ResourceType.VIDEO,
            title="中国大学MOOC·名校微课：市场失灵与外部性治理",
            description="正负外部性对市场效率的破坏机理，庇古税/补贴与科斯产权界定解决外部性的理论对比。",
            source="china_mooc",
            source_url=WHU_MOOC_URL,
            estimated_minutes=20,
            difficulty=0.60,
            summary="【名校慕课精选】市场失灵经典专题，清晰梳理私人成本与社会成本脱节的成因及政策工具。",
            content_ref=None,
            is_external=True,
            priority=65,
            metadata={
                "provider": "中国大学MOOC",
                "university": "武汉大学",
                "instructor": "文建东 教授",
                "course": "微观经济学",
                "course_id": WHU_MOOC_COURSE_ID,
                "chapter": "第九讲 市场失灵与公共政策",
            },
        ),
        # K30: 公共物品、信息不对称与市场失灵 (WHU 第九讲)
        LearningResource(
            resource_id="mooc_k30_public_goods",
            knowledge_id="K30",
            resource_type=ResourceType.VIDEO,
            title="中国大学MOOC·名校微课：公共物品与信息不对称",
            description="非排他性与非竞用性界定、公共物品搭便车难题，以及逆向选择与道德风险等信息不对称问题。",
            source="china_mooc",
            source_url=WHU_MOOC_URL,
            estimated_minutes=18,
            difficulty=0.60,
            summary="【名校慕课精选】公共经济与信息经济核心问题，解析市场无法有效配置公共资源的原因。",
            content_ref=None,
            is_external=True,
            priority=65,
            metadata={
                "provider": "中国大学MOOC",
                "university": "武汉大学",
                "instructor": "文建东 教授",
                "course": "微观经济学",
                "course_id": WHU_MOOC_COURSE_ID,
                "chapter": "第九讲 市场失灵与公共政策",
            },
        ),
    ]

    catalog: Dict[str, LearningResource] = {}
    for res in raw_resources:
        # 严格执行入库安全前置断言
        if res.source_url and not validate_external_mooc_url(res.source_url):
            raise ValueError(f"MOOC 资源外链不合法或未在官方白名单中: {res.source_url}")
        catalog[res.resource_id] = res

    return catalog


# 全局独立 MOOC 资源目录字典（与内部 RESOURCE_CATALOG 物理隔离）
MOOC_RESOURCE_CATALOG: Dict[str, LearningResource] = _build_mooc_catalog()


def get_mooc_resource_by_id(resource_id: str) -> Optional[LearningResource]:
    """根据唯一 MOOC 资源 ID 查询外部资源实体"""
    return MOOC_RESOURCE_CATALOG.get(resource_id)


def get_mooc_resources_by_knowledge(
    knowledge_id: str,
    resource_type: Optional[ResourceType] = None,
) -> List[LearningResource]:
    """
    获取指定考点下的所有 MOOC 学习资源，支持类型过滤。
    确定性排序：(-priority, resource_id ASC)
    """
    items = [
        res for res in MOOC_RESOURCE_CATALOG.values()
        if res.knowledge_id == knowledge_id
        and (resource_type is None or res.resource_type == resource_type)
    ]
    return sorted(items, key=lambda x: (-x.priority, x.resource_id))


def get_all_mooc_resources() -> List[LearningResource]:
    """获取所有中国大学MOOC外部资源，确定性按 (knowledge_id, -priority, resource_id) 排序"""
    items = list(MOOC_RESOURCE_CATALOG.values())
    return sorted(items, key=lambda x: (x.knowledge_id, -x.priority, x.resource_id))
