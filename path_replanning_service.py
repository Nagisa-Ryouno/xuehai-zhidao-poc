# -*- coding: utf-8 -*-
"""
path_replanning_service.py
学海智导 V2 - Path Replanning Decision Core 局部动态重规划核心决策引擎

实现 Architecture Freeze Final v6 规范：
1. 定义路径决策 Action 与 ReasonCode 强类型枚举 (委托给 app.domain.path_replanning)
2. 固化 5 组合法决策矩阵与合法性校验器 (委托给 app.domain.path_replanning)
3. 提供基于 Decimal + ROUND_HALF_UP 的四位定点掌握度规范化函数 (委托给 app.domain.path_replanning)
4. 提供纯函数式、字节级确定性、与时序解耦的 Canonical 业务载荷模型及序列化器 (委托给 app.domain.path_replanning)
5. 提供独立的审计元数据 (AuditMetadata) 与完整审计信封 (DecisionAuditEnvelope) (委托给 app.domain.path_replanning)
6. DAG 只读探针与 1-hop MutationDomain 隔离决策核心 (evaluate_and_replan 委托给 evaluate_decision_core)
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import bkt_state_service
import knowledge_graph_service
import path_state_service
from app.core.constants import PathState
from app.domain.path_replanning import (
    PathAction,
    ReplanningReasonCode,
    LEGAL_DECISION_PAIRS,
    validate_decision_pair,
    format_canonical_mastery,
    CanonicalBusinessPayload,
    AuditMetadata,
    DecisionAuditEnvelope,
    evaluate_decision_core,
)

__all__ = [
    "PathAction",
    "ReplanningReasonCode",
    "LEGAL_DECISION_PAIRS",
    "validate_decision_pair",
    "format_canonical_mastery",
    "CanonicalBusinessPayload",
    "AuditMetadata",
    "DecisionAuditEnvelope",
    "PathState",
    "evaluate_decision_core",
    "evaluate_and_replan",
    "get_prerequisites",
    "get_successors",
    "is_knowledge_mastered",
    "can_unlock_successor",
]


# ============================================================
# DAG 只读探针与后继准入评估函数 (Read-Only Probes)
# ============================================================

def get_prerequisites(knowledge_id: str) -> List[str]:
    """从权威知识图谱中读取知识点的直接前置依赖列表 (Read-Only)"""
    kp_dict = knowledge_graph_service.knowledge_graph_service._raw_knowledge_points.get(knowledge_id, {})
    return list(kp_dict.get("prerequisite", []))


def get_successors(knowledge_id: str) -> List[str]:
    """从权威知识图谱中读取知识点的直接后继知识点列表 (Read-Only)"""
    kp_dict = knowledge_graph_service.knowledge_graph_service._raw_knowledge_points.get(knowledge_id, {})
    return list(kp_dict.get("next_knowledge", []))


def is_knowledge_mastered(
    student_id: str,
    knowledge_id: str,
    bkt_states_file: Optional[Union[Path, str]] = None,
) -> bool:
    """
    检查知识点是否已达到 MASTERED 门槛 (P(L) >= 0.80)。
    若无记录或未掌握，返回 False。
    内部阈值使用原生 IEEE-754 浮点数比较。
    """
    target_file = Path(bkt_states_file) if bkt_states_file is not None else None
    try:
        state = bkt_state_service.get_state(
            student_id, knowledge_id, states_file=target_file, auto_init=False
        )
        if state is None:
            return False
        return float(state.mastery_probability) >= 0.80
    except (KeyError, Exception):
        return False


def can_unlock_successor(
    student_id: str,
    successor_id: str,
    current_just_mastered: str,
    bkt_states_file: Optional[Union[Path, str]] = None,
) -> bool:
    """
    后继准入评估：
    检查 successor_id 的所有直接前置是否全部达到 MASTERED。
    若某个前置即为 current_just_mastered，其在本次决策中已达成 MASTERED，视为满足。
    """
    prereqs = get_prerequisites(successor_id)
    if not prereqs:
        return True
    for p in prereqs:
        if p == current_just_mastered:
            continue
        if not is_knowledge_mastered(student_id, p, bkt_states_file=bkt_states_file):
            return False
    return True


# ============================================================
# 局部动态重规划唯一权威裁决引擎 (Core Replanning Engine)
# ============================================================

def evaluate_and_replan(
    student_id: str,
    knowledge_id: str,
    before_mastery: float,
    after_mastery: float,
    consecutive_incorrect: int = 0,
    previously_mastered: bool = False,
    is_task_context: bool = True,
    trace_id: Optional[str] = None,
    states_file: Optional[Union[Path, str]] = None,
    bkt_states_file: Optional[Union[Path, str]] = None,
) -> DecisionAuditEnvelope:
    """
    局部动态重规划唯一权威裁决入口。
    严格落实单入口原因裁决优先级 (Reason Resolution Priority):
    - Priority 1: 认知回退检查 (曾掌握 且 after_mastery < 0.70 且 consecutive_incorrect >= 2)
      -> DEMOTE_TO_REVIEW × REVIEW_REQUIRED_DEMOTION
    - Priority 2: 掌握度跃迁检查 (after_mastery >= 0.80)
      - 若 is_task_context 且 before_path == IN_PROGRESS，才更新为 COMPLETED；
      - 下游后继准入评估：
        - 若无后继或全已是 AVAILABLE/COMPLETED -> RETAIN × MASTERY_THRESHOLD_REACHED
        - 若成功解锁 >= 1 个后继 (LOCKED -> AVAILABLE) -> UNLOCK_DOWNSTREAM × MASTERY_THRESHOLD_REACHED
        - 若无法解锁任何后继且存在未满足同辈前置 -> RETAIN × PREREQUISITE_NOT_READY
    - Priority 3: 默认区间内状态未跨越门槛 (after_mastery < 0.80)
      -> RETAIN × MASTERY_STATE_UNCHANGED
    """
    target_states_file = Path(states_file) if states_file is not None else None
    target_bkt_file = Path(bkt_states_file) if bkt_states_file is not None else None

    before_path = path_state_service.get_path_state(
        student_id, knowledge_id, states_file=target_states_file
    )
    if isinstance(before_path, str) and not isinstance(before_path, PathState):
        before_path = PathState(before_path)

    affected_nodes: List[str] = []
    path_updates: Dict[str, PathState] = {}

    f_before = float(before_mastery)
    f_after = float(after_mastery)

    successors = get_successors(knowledge_id)
    has_successors = bool(successors)
    unlocked_successors_count = 0
    has_blocked_prerequisites = False

    if f_after >= 0.80 and successors:
        for succ in successors:
            succ_state = path_state_service.get_path_state(
                student_id, succ, states_file=target_states_file
            )
            can_unlock = can_unlock_successor(
                student_id, succ, current_just_mastered=knowledge_id, bkt_states_file=target_bkt_file
            )
            if can_unlock:
                if succ_state == PathState.LOCKED:
                    # 下游解锁仅能将状态更新为 AVAILABLE，严禁直接自动晋升为 IN_PROGRESS！
                    path_updates[succ] = PathState.AVAILABLE
                    affected_nodes.append(succ)
                    unlocked_successors_count += 1
            else:
                # 检查是否有未满足的直接前置 p != knowledge_id
                succ_prereqs = get_prerequisites(succ)
                for p in succ_prereqs:
                    if p != knowledge_id and not is_knowledge_mastered(student_id, p, bkt_states_file=target_bkt_file):
                        has_blocked_prerequisites = True
                        break

    # 委托给纯领域决策核心
    action, reason_code, after_path = evaluate_decision_core(
        before_mastery=f_before,
        after_mastery=f_after,
        consecutive_incorrect=consecutive_incorrect,
        previously_mastered=previously_mastered,
        is_task_context=is_task_context,
        current_path_state=before_path,
        unlocked_successors_count=unlocked_successors_count,
        has_blocked_prerequisites=has_blocked_prerequisites,
        has_successors=has_successors,
    )

    if action == PathAction.DEMOTE_TO_REVIEW:
        affected_nodes.append(knowledge_id)
    elif f_after >= 0.80:
        if after_path != before_path:
            path_updates[knowledge_id] = after_path
            affected_nodes.append(knowledge_id)
        elif f_before < 0.80:
            affected_nodes.append(knowledge_id)
    else:
        affected_nodes.append(knowledge_id)

    # 批量持久化发生状态变化的路径节点
    if path_updates:
        path_state_service.set_path_states_bulk(
            student_id,
            {k: (v.value if hasattr(v, "value") else str(v)) for k, v in path_updates.items()},
            states_file=target_states_file,
        )

    # 规范化定点掌握度与规范载荷构建
    payload = CanonicalBusinessPayload(
        rule_version="v1.0",
        student_id=student_id,
        knowledge_id=knowledge_id,
        before_mastery=format_canonical_mastery(before_mastery),
        after_mastery=format_canonical_mastery(after_mastery),
        before_path_state=before_path,
        after_path_state=after_path,
        action=action,
        reason_code=reason_code,
        affected_nodes=sorted(list(set(affected_nodes))),
    )

    metadata = AuditMetadata(trace_id=trace_id)
    return DecisionAuditEnvelope(audit_metadata=metadata, canonical_payload=payload)
