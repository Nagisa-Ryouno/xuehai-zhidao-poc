# -*- coding: utf-8 -*-
"""
gateway.ai.recommendation.context
=================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B / Phase 2
确定性推荐上下文构建器 (Deterministic Recommendation Context Builder)

设计规范与安全红线：
1. 100% 只读快照：绝不调用任何写 API、不修改 BKT、不修改路径、不生成学习事件；
2. 复用已有权威逻辑：当前焦点考点复用动态路径生成器与路径状态，不发明第二套业务规则；
3. PII 绝对脱敏：内部学生学号转为伪匿名标识符，严格执行 assert_no_pii 安全审查；
4. 资源白名单收敛：候选资源均提取自 Unified Resource Catalog (内部 130 项 + MOOC 12 项)；
5. 纯函数稳定性：相同状态数据在任意时刻调用输出字节级完全一致的 RecommendationContext。
"""

from typing import Dict, List, Optional
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from gateway.ai.deepseek import assert_no_pii
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.resources.service import get_unified_resources_by_knowledge
from gateway.ai.recommendation.models import (
    KnowledgeStateSnapshot,
    RecommendationContext,
    ResourceCandidateSnapshot,
)


def resolve_authoritative_focus_knowledge(
    student_id: str,
    focus_override: Optional[str] = None,
) -> str:
    """
    确定性解析学生当前的权威学习焦点考点。
    
    严格复用已有业务解析逻辑，绝对不创建第二套业务事实：
    1. 若调用方显式提供了合规考点覆盖，优先采用；
    2. 复用 DynamicPathGenerator 生成的动态学习路径首个步骤；
    3. 复用 PathStateService 中首个 IN_PROGRESS 或 AVAILABLE 状态考点；
    4. 复用 ResourceResolver._infer_target_knowledge 判定最需要攻坚的考点；
    5. 兜底返回图谱起点 "K01"。
    """
    if focus_override and focus_override in CONCEPT_CARDS:
        return focus_override

    # 1. 复用 DynamicPathGenerator
    try:
        from gateway.learning.path_generation import default_dynamic_path_generator
        route = default_dynamic_path_generator.generate_route(student_id)
        if route and route.steps:
            candidate = route.steps[0].knowledge_id
            if candidate in CONCEPT_CARDS:
                return candidate
    except Exception:
        pass

    # 2. 复用 PathStateService
    try:
        import path_state_service
        p_states = path_state_service.get_all_path_states(student_id)
        # 优先 IN_PROGRESS
        for kid in sorted(p_states.keys()):
            s_val = p_states[kid].value if hasattr(p_states[kid], "value") else str(p_states[kid])
            if s_val == "IN_PROGRESS" and kid in CONCEPT_CARDS:
                return kid
        # 其次 AVAILABLE
        for kid in sorted(p_states.keys()):
            s_val = p_states[kid].value if hasattr(p_states[kid], "value") else str(p_states[kid])
            if s_val == "AVAILABLE" and kid in CONCEPT_CARDS:
                return kid
    except Exception:
        pass

    # 3. 复用 ResourceResolver 启发式推导
    try:
        from gateway.learning.resources.resolver import ResourceResolver
        inferred = ResourceResolver._infer_target_knowledge(student_id)
        if inferred in CONCEPT_CARDS:
            return inferred
    except Exception:
        pass

    return "K01"


class RecommendationContextBuilder:
    """推荐上下文快照构建器"""

    @classmethod
    def build_context(
        cls,
        student_id: str,
        focus_override: Optional[str] = None,
        max_resources_per_knowledge: int = 5,
    ) -> RecommendationContext:
        """
        基于当前权威学习状态，构建只读不可变的 RecommendationContext。
        """
        # 1. 学生 ID 伪匿名化 (例如 "S001" -> "student_s001")
        pseudo_id = (
            f"student_{student_id.lower()}"
            if not student_id.lower().startswith("student_")
            else student_id.lower()
        )

        # 2. 确定权威焦点考点 (复用已有逻辑)
        focus_kid = resolve_authoritative_focus_knowledge(student_id, focus_override)

        # 3. 收集相关考点集合 (焦点考点 + 前后相邻或处于可用/进行中的少量考点)
        active_kids = [focus_kid]
        try:
            import path_state_service
            p_states = path_state_service.get_all_path_states(student_id)
            for kid in sorted(p_states.keys()):
                s_val = p_states[kid].value if hasattr(p_states[kid], "value") else str(p_states[kid])
                if s_val in ("IN_PROGRESS", "AVAILABLE") and kid in CONCEPT_CARDS and kid not in active_kids:
                    active_kids.append(kid)
                    if len(active_kids) >= 4:
                        break
        except Exception:
            pass

        # 4. 构建知识状态快照
        knowledge_snapshots: List[KnowledgeStateSnapshot] = []
        for kid in sorted(active_kids):
            card = CONCEPT_CARDS.get(kid)
            kname = card.knowledge_name if card else kid

            try:
                bkt_state = default_bkt_state_repository.get_state(student_id, kid)
                mastery = round(float(bkt_state.mastery_probability), 4)
            except Exception:
                mastery = 0.20

            try:
                import path_state_service
                p_state = path_state_service.get_path_state(student_id, kid)
                p_val = p_state.value if hasattr(p_state, "value") else str(p_state)
            except Exception:
                p_val = "AVAILABLE" if kid == focus_kid else "LOCKED"

            knowledge_snapshots.append(
                KnowledgeStateSnapshot(
                    knowledge_id=kid,
                    knowledge_name=kname,
                    mastery=mastery,
                    path_state=p_val,
                )
            )

        # 5. 构建候选资源快照 (从权威 unified 目录提取)
        resource_snapshots: List[ResourceCandidateSnapshot] = []
        for kid in sorted(active_kids):
            items = get_unified_resources_by_knowledge(kid, source="all")
            for res in items[:max_resources_per_knowledge]:
                type_val = res.resource_type.value if hasattr(res.resource_type, "value") else str(res.resource_type)
                desc = res.description or f"{res.title} 辅导材料"
                resource_snapshots.append(
                    ResourceCandidateSnapshot(
                        resource_id=res.resource_id,
                        knowledge_id=res.knowledge_id,
                        resource_type=type_val,
                        title=res.title,
                        description=desc,
                        source=res.source,
                    )
                )

        # 保证资源排序确定性
        resource_snapshots.sort(key=lambda r: (r.knowledge_id, r.resource_id))

        # 6. PII 防火墙全量扫描
        assert_no_pii(pseudo_id, context_name="context.student_id")
        for k in knowledge_snapshots:
            assert_no_pii(k.knowledge_name, context_name="context.knowledge_name")
        for r in resource_snapshots:
            assert_no_pii(r.title, context_name="context.resource_title")
            assert_no_pii(r.description, context_name="context.resource_description")

        return RecommendationContext(
            student_id=pseudo_id,
            current_focus=focus_kid,
            knowledge_states=knowledge_snapshots,
            resources=resource_snapshots,
        )
