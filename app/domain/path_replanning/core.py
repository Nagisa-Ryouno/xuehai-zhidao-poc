# -*- coding: utf-8 -*-
"""
app/domain/path_replanning/core.py
学海智导 V2 - Path Replanning Pure Decision Core

纯内存决策流转函数 (Zero IO, Pure Logic).
严格落实单入口原因裁决优先级与 1-hop 决策规则。
"""
from typing import Tuple

from app.core.constants import PathState
from app.domain.path_replanning.models import (
    PathAction,
    ReplanningReasonCode,
    validate_decision_pair,
)


def evaluate_decision_core(
    before_mastery: float,
    after_mastery: float,
    consecutive_incorrect: int = 0,
    previously_mastered: bool = False,
    is_task_context: bool = True,
    current_path_state: PathState = PathState.LOCKED,
    unlocked_successors_count: int = 0,
    has_blocked_prerequisites: bool = False,
    has_successors: bool = True,
) -> Tuple[PathAction, ReplanningReasonCode, PathState]:
    """
    局部动态重规划纯决策核心函数 (Zero IO, Pure Logic).
    严格落实单入口原因裁决优先级:
    - Priority 1: 认知回退检查 (曾掌握 且 after_mastery < 0.70 且 consecutive_incorrect >= 2)
      -> DEMOTE_TO_REVIEW x REVIEW_REQUIRED_DEMOTION
    - Priority 2: 掌握度跃迁检查 (after_mastery >= 0.80)
      - 若 is_task_context 且 current_path_state == IN_PROGRESS，after_path_state = COMPLETED
      - 后继准入情况判断:
        - 若无后继节点 (not has_successors): RETAIN x MASTERY_THRESHOLD_REACHED
        - 若成功解锁 >= 1 个后继 (unlocked_successors_count > 0): UNLOCK_DOWNSTREAM x MASTERY_THRESHOLD_REACHED
        - 若无法解锁且存在受阻前置 (has_blocked_prerequisites): RETAIN x PREREQUISITE_NOT_READY
        - 否则: RETAIN x MASTERY_THRESHOLD_REACHED
    - Priority 3: 默认掌握度未跨越门槛 (after_mastery < 0.80)
      -> RETAIN x MASTERY_STATE_UNCHANGED
    """
    f_before = float(before_mastery)
    f_after = float(after_mastery)
    if isinstance(current_path_state, str) and not isinstance(current_path_state, PathState):
        current_path_state = PathState(current_path_state)
    after_path_state = current_path_state

    # Priority 1: 认知回退
    if previously_mastered and f_after < 0.70 and consecutive_incorrect >= 2:
        action = PathAction.DEMOTE_TO_REVIEW
        reason_code = ReplanningReasonCode.REVIEW_REQUIRED_DEMOTION

    # Priority 2: 掌握度跃迁
    elif f_after >= 0.80:
        if is_task_context and current_path_state == PathState.IN_PROGRESS:
            after_path_state = PathState.COMPLETED

        if not has_successors:
            action = PathAction.RETAIN
            reason_code = ReplanningReasonCode.MASTERY_THRESHOLD_REACHED
        else:
            if unlocked_successors_count > 0:
                action = PathAction.UNLOCK_DOWNSTREAM
                reason_code = ReplanningReasonCode.MASTERY_THRESHOLD_REACHED
            elif has_blocked_prerequisites:
                action = PathAction.RETAIN
                reason_code = ReplanningReasonCode.PREREQUISITE_NOT_READY
            else:
                action = PathAction.RETAIN
                reason_code = ReplanningReasonCode.MASTERY_THRESHOLD_REACHED

    # Priority 3: 未跨越门槛
    else:
        action = PathAction.RETAIN
        reason_code = ReplanningReasonCode.MASTERY_STATE_UNCHANGED

    validate_decision_pair(action, reason_code)
    return action, reason_code, after_path_state
