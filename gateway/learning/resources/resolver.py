# -*- coding: utf-8 -*-
"""
gateway.learning.resources.resolver
===================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-C
资源感知自适应学习推荐引擎 (Deterministic Resource Resolver)

设计规范与红线约束：
1. 绝对确定性：资源推荐、时序、分类完全由规则矩阵决定，严禁使用任何 LLM 生成或随机扰动。
2. 5 种自适应学习场景（Cases A ~ E）：
   - Case E (CASE_E_ROADBLOCK_REPAIR): 连续错误 (consecutive_incorrect >= 2) -> 优先概念微卡与例题排查阻碍
   - Case A (CASE_A_WEAK_FOUNDATION): 薄弱起步 (mastery < 0.60) -> 概念微卡 -> 典型例题 -> 讲义/导学 -> 靶向练习
   - Case B (CASE_B_DEVELOPING): 进阶巩固 (0.60 <= mastery < 0.80) -> 典型例题 -> 靶向练习 -> 概念微卡 -> 讲义
   - Case C (CASE_C_MASTERED_ADVANCE): 掌握跃迁 (mastery >= 0.80 且有后继) -> 进阶练习 -> 后继考点预习微卡 -> 典型例题
   - Case D (CASE_D_TERMINAL_CONSOLIDATE): 终点巩固 (mastery >= 0.80 且图谱终点) -> 综合练习 -> 典型例题 -> 精讲讲义
3. 纯函数稳定性 (Deterministic Tie-Breaker)：
   相同输入在任意时间执行均返回完全一致的资源列表与字节级一致的排序。
4. 语言零黑话 (No Jargon)：
   推荐理由一律采用通俗自然中文，严禁暴露技术指标、类名或内部变量名。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from app.services.knowledge_graph_service import knowledge_graph_service
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.resource_effectiveness import (
    ResourceEffectivenessAggregator,
    default_adaptation_strategy,
    default_resource_effectiveness_aggregator,
)
from gateway.learning.resources.catalog import (
    get_resource_by_id,
    get_resources_by_knowledge,
)
from gateway.learning.resources.models import (
    LearningResource,
    RecommendedResourcesResponse,
    ResourceRecommendation,
    ResourceType,
)


class ResourceResolver:
    """资源感知确定性推荐解析器"""

    @classmethod
    def resolve(
        cls,
        student_id: str,
        knowledge_id: Optional[str] = None,
        mastery_override: Optional[float] = None,
        consecutive_incorrect_override: Optional[int] = None,
        events_file: Optional[Path] = None,
    ) -> RecommendedResourcesResponse:
        """
        根据学生的真实掌握度与做题状态，确定性输出自适应资源推荐序列
        """
        target_kid = knowledge_id or cls._infer_target_knowledge(student_id)

        # 读取真实 BKT 状态
        bkt_state = default_bkt_state_repository.get_state(student_id, target_kid)
        
        mastery = (
            float(mastery_override)
            if mastery_override is not None
            else (float(bkt_state.mastery_probability) if bkt_state else 0.20)
        )
        
        consecutive_incorrect = (
            int(consecutive_incorrect_override)
            if consecutive_incorrect_override is not None
            else (int(bkt_state.consecutive_incorrect) if bkt_state else 0)
        )

        # 获取后继依赖节点
        successors = knowledge_graph_service.get_successors(target_kid)
        unmastered_successors = []
        for succ in successors:
            succ_state = default_bkt_state_repository.get_state(student_id, succ)
            if not succ_state or succ_state.mastery_probability < 0.80:
                unmastered_successors.append(succ)

        # 匹配推荐场景规则
        case_code, reason_summary, raw_recommendations = cls._match_case_strategy(
            student_id=student_id,
            knowledge_id=target_kid,
            mastery=mastery,
            consecutive_incorrect=consecutive_incorrect,
            successors=successors,
            unmastered_successors=unmastered_successors,
        )

        # Sprint 9-E: 读取真实历史资源效果，对合法候选资源进行确定性二次微调排序
        aggregator = (
            ResourceEffectivenessAggregator(events_file=events_file)
            if events_file
            else default_resource_effectiveness_aggregator
        )
        profiles = aggregator.get_resource_effectiveness(
            student_id=student_id,
            knowledge_id=target_kid,
        )
        adapted_recommendations = default_adaptation_strategy.apply_adaptation(
            candidates=raw_recommendations,
            profiles=profiles,
        )

        # 赋予 rank 与 suggested_order (1-indexed)
        final_recommendations: List[ResourceRecommendation] = []
        for idx, item in enumerate(adapted_recommendations, start=1):
            eff = item.get("historical_effectiveness", "INSUFFICIENT_DATA")
            eff_val = eff.value if hasattr(eff, "value") else str(eff)
            final_recommendations.append(
                ResourceRecommendation(
                    resource=item["resource"],
                    rank=idx,
                    recommended_reason=item["recommended_reason"],
                    reason_category=item["reason_category"],
                    suggested_order=item.get("suggested_order", idx),
                    historical_effectiveness=eff_val,
                    why_recommended=item.get("why_recommended"),
                    score_adjustment=int(item.get("score_adjustment", 0)),
                )
            )

        return RecommendedResourcesResponse(
            student_id=student_id,
            knowledge_id=target_kid,
            mastery=round(mastery, 4),
            case_code=case_code,
            recommendations=final_recommendations,
            reason_summary=reason_summary,
        )

    @classmethod
    def _infer_target_knowledge(cls, student_id: str) -> str:
        """
        若未显式指定考点，自动推导学生当前最需要攻坚的学习考点（优先薄弱或未达标节点，默认 K01）
        """
        for i in range(1, 31):
            kid = f"K{i:02d}"
            state = default_bkt_state_repository.get_state(student_id, kid)
            if not state or state.mastery_probability < 0.80:
                return kid
        return "K01"

    @classmethod
    def _match_case_strategy(
        cls,
        student_id: str,
        knowledge_id: str,
        mastery: float,
        consecutive_incorrect: int,
        successors: List[str],
        unmastered_successors: List[str],
    ) -> Tuple[str, str, List[Dict[str, Any]]]:
        """
        根据输入状态确定性匹配 Cases A ~ E
        """
        kid = knowledge_id
        kid_lower = kid.lower()
        all_kp_resources = get_resources_by_knowledge(kid)
        res_by_type: Dict[ResourceType, List[LearningResource]] = {}
        for r in all_kp_resources:
            res_by_type.setdefault(r.resource_type, []).append(r)

        concept_res = res_by_type.get(ResourceType.CONCEPT_CARD, [None])[0]
        example_res = res_by_type.get(ResourceType.EXAMPLE, [None])[0]
        practice_res = res_by_type.get(ResourceType.PRACTICE, [None])[0]
        document_res = res_by_type.get(ResourceType.DOCUMENT, [None])[0]
        video_res = res_by_type.get(ResourceType.VIDEO, [None])[0]

        recs: List[Dict[str, Any]] = []

        # =====================================================================
        # Case E: 连续答错 >= 2 次 (认知受阻保护)
        # =====================================================================
        if consecutive_incorrect >= 2:
            case_code = "CASE_E_ROADBLOCK_REPAIR"
            reason_summary = "近期该考点连续作答受阻（≥2次），建议暂缓直接刷题，先回归概念卡片梳理核心要点与生活例题，排查思维误区。"

            if concept_res:
                recs.append({
                    "resource": concept_res,
                    "recommended_reason": "连续答错达到2次，先重温考点微卡夯实概念核心要义，避免盲目尝试",
                    "reason_category": "REPAIR",
                    "suggested_order": 1,
                })
            if example_res:
                recs.append({
                    "resource": example_res,
                    "recommended_reason": "研读典型生活与商业实例精析，深入拆解典型解题思路与常见避坑要点",
                    "reason_category": "APPLICATION",
                    "suggested_order": 2,
                })
            if practice_res:
                recs.append({
                    "resource": practice_res,
                    "recommended_reason": "在理清概念与例题之后，进行针对性微测验检验理解并消除认知障碍",
                    "reason_category": "CONSOLIDATION",
                    "suggested_order": 3,
                })
            return case_code, reason_summary, recs

        # =====================================================================
        # Case A: 薄弱起步阶段 (掌握度 < 0.60)
        # =====================================================================
        if mastery < 0.60:
            case_code = "CASE_A_WEAK_FOUNDATION"
            reason_summary = "当前考点掌握度较低（<60%），建议先通过概念微卡与生活例题建立直观认知，打牢基础后再进行测验巩固。"

            if concept_res:
                recs.append({
                    "resource": concept_res,
                    "recommended_reason": "掌握度处于起步阶段，建议先通读考点微卡，掌握核心概念与基本原理",
                    "reason_category": "FOUNDATION",
                    "suggested_order": 1,
                })
            if example_res:
                recs.append({
                    "resource": example_res,
                    "recommended_reason": "研读典型生活与商业实例，通过通俗实际案例建立对理论概念的感性认知",
                    "reason_category": "APPLICATION",
                    "suggested_order": 2,
                })
            if video_res:
                recs.append({
                    "resource": video_res,
                    "recommended_reason": "观看直观动画导学，动态理解考点演化逻辑",
                    "reason_category": "FOUNDATION",
                    "suggested_order": 3,
                })
            elif document_res:
                recs.append({
                    "resource": document_res,
                    "recommended_reason": "精读核心讲义与避坑指南，全面梳理考试常见误区",
                    "reason_category": "FOUNDATION",
                    "suggested_order": 3,
                })
            if practice_res:
                order_num = 4 if (video_res or document_res) else 3
                recs.append({
                    "resource": practice_res,
                    "recommended_reason": "完成靶向通关微测验，检验概念掌握度并驱动后续知识节点解锁",
                    "reason_category": "CONSOLIDATION",
                    "suggested_order": order_num,
                })
            return case_code, reason_summary, recs

        # =====================================================================
        # Case B: 巩固提升阶段 (0.60 <= 掌握度 < 0.80)
        # =====================================================================
        if mastery < 0.80:
            case_code = "CASE_B_DEVELOPING"
            reason_summary = "当前考点掌握度处于提升期（60%~80%），建议通过例题精析和定向微练巩固强化，冲刺80%达标线。"

            if example_res:
                recs.append({
                    "resource": example_res,
                    "recommended_reason": "掌握度处于巩固提升阶段，优先精读实例解析透析出题套路与推导技巧",
                    "reason_category": "APPLICATION",
                    "suggested_order": 1,
                })
            if practice_res:
                recs.append({
                    "resource": practice_res,
                    "recommended_reason": "进行靶向通关微测验，一鼓作气冲刺80%达标门槛",
                    "reason_category": "CONSOLIDATION",
                    "suggested_order": 2,
                })
            if concept_res:
                recs.append({
                    "resource": concept_res,
                    "recommended_reason": "随时对照考点微卡查漏补缺，加深关键结论记忆",
                    "reason_category": "FOUNDATION",
                    "suggested_order": 3,
                })
            if document_res:
                recs.append({
                    "resource": document_res,
                    "recommended_reason": "查阅讲义深化知识网络，防范考试易错失分点",
                    "reason_category": "CONSOLIDATION",
                    "suggested_order": 4,
                })
            return case_code, reason_summary, recs

        # =====================================================================
        # Case C: 掌握达标且有后继节点 (掌握度 >= 0.80 且 successors)
        # =====================================================================
        if successors:
            case_code = "CASE_C_MASTERED_ADVANCE"
            next_target = unmastered_successors[0] if unmastered_successors else successors[0]
            next_card = CONCEPT_CARDS.get(next_target)
            next_name = next_card.knowledge_name if next_card else next_target
            reason_summary = f"当前考点已达标掌握（≥80%），建议开启后继考点【{next_name}】的进阶预习与攻坚。"

            if practice_res:
                recs.append({
                    "resource": practice_res,
                    "recommended_reason": "当前考点已达到掌握标准，可进行进阶微练保持手感与熟练度",
                    "reason_category": "ADVANCEMENT",
                    "suggested_order": 1,
                })

            # 跨节点推荐：后继考点的概念微卡
            next_concept = get_resource_by_id(f"res_{next_target.lower()}_concept")
            if next_concept:
                recs.append({
                    "resource": next_concept,
                    "recommended_reason": f"当前考点已通关，建议开启下游依赖考点【{next_name}】的概念预习",
                    "reason_category": "ADVANCEMENT",
                    "suggested_order": 2,
                })

            if example_res:
                recs.append({
                    "resource": example_res,
                    "recommended_reason": "研读生活与商业实例，融会贯通微观经济学应用分析能力",
                    "reason_category": "APPLICATION",
                    "suggested_order": 3,
                })
            return case_code, reason_summary, recs

        # =====================================================================
        # Case D: 图谱终点考点已达标 (掌握度 >= 0.80 且无 successors)
        # =====================================================================
        case_code = "CASE_D_TERMINAL_CONSOLIDATE"
        reason_summary = "图谱终点考点已达标掌握（≥80%），建议进行综合模拟演练与全景复盘，巩固全阶段学习成果。"

        if practice_res:
            recs.append({
                "resource": practice_res,
                "recommended_reason": "图谱终点考点已达标，进行综合通关演练保持熟练度",
                "reason_category": "CONSOLIDATION",
                "suggested_order": 1,
            })
        if example_res:
            recs.append({
                "resource": example_res,
                "recommended_reason": "研读典型应用实例精析，回顾全章综合经济模型应用",
                "reason_category": "APPLICATION",
                "suggested_order": 2,
            })
        if document_res:
            recs.append({
                "resource": document_res,
                "recommended_reason": "研读核心讲义系统复盘，梳理全书知识脉络",
                "reason_category": "FOUNDATION",
                "suggested_order": 3,
            })

        return case_code, reason_summary, recs


default_resource_resolver = ResourceResolver()
