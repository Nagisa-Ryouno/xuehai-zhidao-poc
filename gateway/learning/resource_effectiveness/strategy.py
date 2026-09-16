# -*- coding: utf-8 -*-
"""
gateway.learning.resource_effectiveness.strategy
================================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-E
确定性候选资源自适应二次排序策略 (Deterministic Adaptation Strategy)

设计规范与红线约束：
1. 绝对确定性：排序分值计算与平局仲裁严格确定性，严禁使用 random、hash 或时间戳；
2. 候选池边界防线：历史效果仅在现有规则产出的候选资源池内部进行微调，绝不引入未准入资源；
3. 优雅降级：无历史数据或样本不足 (usage_count < 2) 时，微调量为 0，原有候选排序 100% 保持不变；
4. 纯模板文案：推荐理由严格采用确定性模板生成，杜绝使用 LLM 生成推荐理由；
5. 人本叙事克制：不暴露内部算法分值，文案语气温和客观，不作出个人特征绝对化断言。
"""

from typing import Any, Dict, List, Optional
from gateway.learning.resource_effectiveness.models import (
    ADJUSTMENT_SCORES,
    HistoricalEffectiveness,
    ResourceEffectivenessProfile,
)

# 确定性推荐解释文案模板库（严格遵循 Section 10 契约）
WHY_RECOMMENDED_TEMPLATES: Dict[HistoricalEffectiveness, str] = {
    HistoricalEffectiveness.VERY_EFFECTIVE: "你之前用这种学习方式时，掌握情况有过比较明显的提升。",
    HistoricalEffectiveness.EFFECTIVE: "你之前用这种学习方式时，掌握情况有过稳定提升。",
    HistoricalEffectiveness.NEUTRAL: "这是当前学习阶段适合你的学习方式。",
    HistoricalEffectiveness.INEFFECTIVE: "你之前用这种学习方式时，提升比较有限，这次换一种方式试试。",
    HistoricalEffectiveness.INSUFFICIENT_DATA: "这是当前学习阶段适合你的学习方式。",
}


class DeterministicAdaptationStrategy:
    """确定性资源自适应排序策略器"""

    @classmethod
    def apply_adaptation(
        cls,
        candidates: List[Dict[str, Any]],
        profiles: Optional[Dict[str, ResourceEffectivenessProfile]] = None,
    ) -> List[Dict[str, Any]]:
        """
        对已由底层掌握度与规则矩阵确定的候选资源列表进行二次微调排序与解释注入。
        
        分值模型：
        - 每个候选资源按其原有推荐顺序赋予基准分：base_score = 100.0 - (original_order - 1) * 5.0
        - 历史效果微调量：score_adjustment = ADJUSTMENT_SCORES[eff] (+2, +1, 0, -1, 0)
        - 最终排序分：final_score = base_score + score_adjustment * 10.0
        - 稳定排序：按 (final_score DESC, original_order ASC) 排序
        - 重新编排 suggested_order 与 rank (1-indexed)
        """
        if not candidates:
            return []

        profiles = profiles or {}

        scored_candidates: List[Dict[str, Any]] = []

        for idx, item in enumerate(candidates, start=1):
            resource = item.get("resource")
            r_type = resource.resource_type.value if hasattr(resource, "resource_type") else str(item.get("resource_type", ""))

            # 查询该资源类型的历史效果档案
            profile = profiles.get(r_type) or profiles.get(r_type.lower()) or profiles.get(r_type.upper())
            if profile and profile.effectiveness:
                eff = profile.effectiveness
            else:
                eff = HistoricalEffectiveness.INSUFFICIENT_DATA

            adj = ADJUSTMENT_SCORES.get(eff, 0)

            # 阶梯式基准分：确保在微调量存在差异时，高成效资源可合理跃迁，同分时严格保持原始顺序
            base_score = 100.0 - (idx - 1) * 5.0
            final_score = base_score + float(adj) * 10.0

            why_text = WHY_RECOMMENDED_TEMPLATES.get(eff, WHY_RECOMMENDED_TEMPLATES[HistoricalEffectiveness.INSUFFICIENT_DATA])

            # 浅拷贝字典，附加自适应特征
            new_item = dict(item)
            new_item["original_order"] = idx
            new_item["historical_effectiveness"] = eff
            new_item["why_recommended"] = why_text
            new_item["score_adjustment"] = adj
            new_item["_final_score"] = final_score

            scored_candidates.append(new_item)

        # 稳定排序：第一主键 final_score 降序，第二主键 original_order 升序
        scored_candidates.sort(key=lambda x: (-x["_final_score"], x["original_order"]))

        # 重新赋予 rank 与 suggested_order
        adapted_results: List[Dict[str, Any]] = []
        for new_idx, candidate in enumerate(scored_candidates, start=1):
            candidate["rank"] = new_idx
            candidate["suggested_order"] = new_idx
            adapted_results.append(candidate)

        return adapted_results


default_adaptation_strategy = DeterministicAdaptationStrategy()
