# -*- coding: utf-8 -*-
"""
gateway/learning/path_generation/scoring.py
学海智导 (Xuehai Zhidao) - 动态路线节点优先级评分器

评分模型公式：
PriorityScore = 0.35 * WeaknessScore
              + 0.25 * TargetRelevance
              + 0.20 * PrerequisiteReadiness
              + 0.10 * PathAvailability
              + 0.10 * DiagnosticPriority

Tie-Break 策略：
(-score, chapter_index, difficulty, knowledge_id)
"""

from typing import Dict, List, Optional, Tuple

# 集中评分权重配置
WEIGHT_WEAKNESS: float = 0.35
WEIGHT_TARGET_RELEVANCE: float = 0.25
WEIGHT_PREREQUISITE_READINESS: float = 0.20
WEIGHT_PATH_AVAILABILITY: float = 0.10
WEIGHT_DIAGNOSTIC_PRIORITY: float = 0.10

# 校验权重总和为 1.00
assert abs((WEIGHT_WEAKNESS + WEIGHT_TARGET_RELEVANCE + WEIGHT_PREREQUISITE_READINESS + WEIGHT_PATH_AVAILABILITY + WEIGHT_DIAGNOSTIC_PRIORITY) - 1.0) < 1e-6


def calculate_node_priority(
    knowledge_id: str,
    mastery: float,
    is_target_ancestor_or_self: bool,
    is_same_chapter: bool,
    all_prereqs_mastered: bool,
    path_state: str,
    diagnostic_status: Optional[str] = None,
) -> Tuple[float, Dict[str, float], List[str], str]:
    """
    计算单个知识节点的综合攻坚优先级打分与原因说明。
    
    返回：
    (total_score, factors, reason_codes, explanation)
    """
    # 1. 掌握度薄弱分：掌握度越低，攻坚优先级越高 (1.0 - mastery)
    clamped_mastery = max(0.0, min(1.0, mastery))
    weakness_score = 1.0 - clamped_mastery
    
    # 2. 目标相关性打分
    if is_target_ancestor_or_self:
        target_relevance = 1.0
    elif is_same_chapter:
        target_relevance = 0.5
    else:
        target_relevance = 0.1
        
    # 3. 前置就绪分：前置全部掌握才能顺畅学习
    prereq_readiness = 1.0 if all_prereqs_mastered else 0.0
    
    # 4. 路径执行就绪分
    if path_state == "IN_PROGRESS":
        path_availability = 1.0
    elif path_state == "AVAILABLE":
        path_availability = 0.8
    else:
        path_availability = 0.0  # LOCKED
        
    # 5. 前测诊断优先级
    if diagnostic_status == "WEAK":
        diagnostic_priority = 1.0
    elif diagnostic_status == "DEVELOPING":
        diagnostic_priority = 0.3
    else:
        diagnostic_priority = 0.5  # 未测验节点中性赋分
        
    total_score = (
        WEIGHT_WEAKNESS * weakness_score
        + WEIGHT_TARGET_RELEVANCE * target_relevance
        + WEIGHT_PREREQUISITE_READINESS * prereq_readiness
        + WEIGHT_PATH_AVAILABILITY * path_availability
        + WEIGHT_DIAGNOSTIC_PRIORITY * diagnostic_priority
    )
    total_score = round(total_score, 4)
    
    factors = {
        "weakness_score": round(weakness_score, 4),
        "target_relevance": round(target_relevance, 4),
        "prereq_readiness": round(prereq_readiness, 4),
        "path_availability": round(path_availability, 4),
        "diagnostic_priority": round(diagnostic_priority, 4),
    }
    
    reason_codes: List[str] = []
    explanation_parts: List[str] = []
    
    if path_state == "IN_PROGRESS":
        reason_codes.append("CURRENTLY_IN_PROGRESS")
        explanation_parts.append("当前已在进行中")
    elif path_state == "AVAILABLE":
        reason_codes.append("PATH_AVAILABLE")
        
    if all_prereqs_mastered:
        reason_codes.append("PREREQUISITES_SATISFIED")
        explanation_parts.append("前置依赖已全部掌握")
    else:
        reason_codes.append("PREREQUISITE_PENDING")
        
    if is_target_ancestor_or_self:
        reason_codes.append("GOAL_DIRECT_PATH")
        explanation_parts.append("处于当前学习目标直接推进路径上")
        
    if clamped_mastery < 0.60:
        reason_codes.append("HIGH_COGNITIVE_WEAKNESS")
        explanation_parts.append(f"掌握度较弱({clamped_mastery:.2f})")
    elif clamped_mastery < 0.80:
        reason_codes.append("DEVELOPING_MASTERY")
        explanation_parts.append(f"尚在发展中({clamped_mastery:.2f})")
        
    if diagnostic_status == "WEAK":
        reason_codes.append("DIAGNOSTIC_WEAK_POINT")
        explanation_parts.append("前测诊断发现盲区")
        
    if not explanation_parts:
        explanation = "知识图谱自适应推进节点。"
    else:
        explanation = "，".join(explanation_parts) + "，综合优先级最优。"
        
    return total_score, factors, reason_codes, explanation
