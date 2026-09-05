# -*- coding: utf-8 -*-
"""
path_replanning_service.py
学海智导 V2 - Path Replanning Decision Core 局部动态重规划核心决策引擎

实现 Architecture Freeze Final v6 规范：
1. 定义路径决策 Action 与 ReasonCode 强类型枚举
2. 固化 5 组合法决策矩阵与合法性校验器
3. 提供基于 Decimal + ROUND_HALF_UP 的四位定点掌握度规范化函数
4. 提供纯函数式、字节级确定性、与时序解耦的 Canonical 业务载荷模型及序列化器
5. 提供独立的审计元数据 (AuditMetadata) 与完整审计信封 (DecisionAuditEnvelope)
6. DAG 只读探针与 1-hop MutationDomain 隔离决策核心 (evaluate_and_replan)
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

import bkt_state_service
import knowledge_graph_service
import path_state_service
from path_state_service import PathState


class PathAction(str, Enum):
    """路径重规划执行动作枚举"""
    UNLOCK_DOWNSTREAM = "UNLOCK_DOWNSTREAM"
    RETAIN = "RETAIN"
    DEMOTE_TO_REVIEW = "DEMOTE_TO_REVIEW"


class ReplanningReasonCode(str, Enum):
    """路径重规划决策原因代码枚举"""
    MASTERY_THRESHOLD_REACHED = "MASTERY_THRESHOLD_REACHED"
    MASTERY_STATE_UNCHANGED = "MASTERY_STATE_UNCHANGED"
    PREREQUISITE_NOT_READY = "PREREQUISITE_NOT_READY"
    REVIEW_REQUIRED_DEMOTION = "REVIEW_REQUIRED_DEMOTION"


# 5 组合法决策矩阵（严格穷举，不可扩充）
LEGAL_DECISION_PAIRS: Set[Tuple[PathAction, ReplanningReasonCode]] = {
    (PathAction.UNLOCK_DOWNSTREAM, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED),
    (PathAction.RETAIN, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED),
    (PathAction.RETAIN, ReplanningReasonCode.MASTERY_STATE_UNCHANGED),
    (PathAction.RETAIN, ReplanningReasonCode.PREREQUISITE_NOT_READY),
    (PathAction.DEMOTE_TO_REVIEW, ReplanningReasonCode.REVIEW_REQUIRED_DEMOTION),
}


def validate_decision_pair(
    action: Union[PathAction, str],
    reason_code: Union[ReplanningReasonCode, str],
) -> None:
    """
    校验决策动作与原因代码配对是否合法。
    若不在 LEGAL_DECISION_PAIRS 矩阵中，显式抛出 ValueError。
    """
    try:
        act = PathAction(action) if not isinstance(action, PathAction) else action
        code = (
            ReplanningReasonCode(reason_code)
            if not isinstance(reason_code, ReplanningReasonCode)
            else reason_code
        )
    except ValueError:
        raise ValueError(f"Invalid action '{action}' or reason_code '{reason_code}'")

    if (act, code) not in LEGAL_DECISION_PAIRS:
        raise ValueError(
            f"Illegal decision pair: ({act.value}, {code.value}). "
            f"Allowed pairs: {[(a.value, r.value) for a, r in LEGAL_DECISION_PAIRS]}"
        )


def format_canonical_mastery(raw_float: Union[float, int, str, Decimal]) -> str:
    """
    法定唯一舍入步骤：Decimal(str(raw_float)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    返回严格 4 位定点字符串（例如 f"{rounded:.4f}"）。
    严禁使用 Python 内置 round()，严禁输出裸 float。
    """
    rounded = Decimal(str(raw_float)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return f"{rounded:.4f}"


class CanonicalBusinessPayload(BaseModel):
    """
    路径重规划核心规范业务载荷模型。
    仅包含参与确定性业务断言的核心字段，严禁包含 decision_id, timestamp, duration_ms, trace_id 等时序/审计字段。
    """
    model_config = ConfigDict(extra="forbid")

    rule_version: str = Field(default="v1.0", description="规则引擎版本号，当前固定为 v1.0")
    student_id: str = Field(..., description="学生唯一编号")
    knowledge_id: str = Field(..., description="触发重规划决策的目标知识点编号")
    before_mastery: str = Field(..., description="决策前规范化掌握度字符串 (4位定点)")
    after_mastery: str = Field(..., description="决策后规范化掌握度字符串 (4位定点)")
    before_path_state: PathState = Field(..., description="决策前路径执行状态")
    after_path_state: PathState = Field(..., description="决策后路径执行状态")
    action: PathAction = Field(..., description="重规划决策执行动作")
    reason_code: ReplanningReasonCode = Field(..., description="决策依据原因代码")
    affected_nodes: List[str] = Field(default_factory=list, description="本次决策波及/更新的节点编号列表")

    @field_validator("before_mastery", "after_mastery", mode="before")
    @classmethod
    def validate_mastery_is_str(cls, v: Any) -> str:
        if isinstance(v, (float, int)):
            raise TypeError(
                f"Mastery must be a canonical 4-decimal string, not float/int ({v}). "
                f"Use format_canonical_mastery()."
            )
        if not isinstance(v, str):
            raise TypeError(f"Mastery must be a str, got {type(v).__name__}")
        return v

    @field_validator("rule_version", mode="after")
    @classmethod
    def validate_rule_version_fixed(cls, v: str) -> str:
        if v != "v1.0":
            raise ValueError(f"rule_version must be 'v1.0', got '{v}'")
        return v

    @field_validator("affected_nodes", mode="after")
    @classmethod
    def normalize_affected_nodes(cls, v: List[str]) -> List[str]:
        if not v:
            return []
        return sorted(list(set(v)))

    @model_validator(mode="after")
    def validate_decision_consistency(self) -> "CanonicalBusinessPayload":
        validate_decision_pair(self.action, self.reason_code)
        return self

    def to_canonical_json(self) -> str:
        """
        生成字节级完全确定性的 JSON 规范化字符串。
        保证：
        - affected_nodes 严格以 ASCII 升序排列：sorted(list(set(self.affected_nodes)))，空时为 []
        - 字典序稳定排序：sort_keys=True
        - 紧凑无空格分隔符：separators=(',', ':')
        - 原生 UTF-8：ensure_ascii=False
        - 纯函数，相同输入多次调用生成的 JSON 字符串与 SHA-256 哈希字节级严格一致。
        """
        nodes = sorted(list(set(self.affected_nodes))) if self.affected_nodes else []
        payload_data = {
            "action": self.action.value if isinstance(self.action, PathAction) else str(self.action),
            "affected_nodes": nodes,
            "after_mastery": self.after_mastery,
            "after_path_state": (
                self.after_path_state.value
                if isinstance(self.after_path_state, PathState)
                else str(self.after_path_state)
            ),
            "before_mastery": self.before_mastery,
            "before_path_state": (
                self.before_path_state.value
                if isinstance(self.before_path_state, PathState)
                else str(self.before_path_state)
            ),
            "knowledge_id": self.knowledge_id,
            "reason_code": (
                self.reason_code.value
                if isinstance(self.reason_code, ReplanningReasonCode)
                else str(self.reason_code)
            ),
            "rule_version": self.rule_version,
            "student_id": self.student_id,
        }
        return json.dumps(payload_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class AuditMetadata(BaseModel):
    """
    独立审计元数据模型。
    维护与业务 payload 完全正交的非确定性与可观测性元数据。
    """
    decision_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="决策事件全局唯一 UUID",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="决策生成 ISO8601 UTC 时间戳 (以 Z 结尾)",
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="全链路追踪 ID",
    )


class DecisionAuditEnvelope(BaseModel):
    """
    完整决策审计信封模型。
    外层包含审计元数据与内层确定性规范业务载荷。
    """
    audit_metadata: AuditMetadata = Field(
        default_factory=AuditMetadata,
        description="独立审计元数据",
    )
    canonical_payload: CanonicalBusinessPayload = Field(
        ...,
        description="内层纯粹业务确定性载荷",
    )


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
    after_path = before_path

    affected_nodes: List[str] = []
    path_updates: Dict[str, PathState] = {}

    action: PathAction
    reason_code: ReplanningReasonCode

    # 内部阈值使用原生 IEEE-754 浮点数，严禁使用格式化字符串比较
    f_before = float(before_mastery)
    f_after = float(after_mastery)

    # Priority 1: 认知回退检查 (曾掌握 且 after_mastery < 0.70 且 consecutive_incorrect >= 2)
    if previously_mastered and f_after < 0.70 and consecutive_incorrect >= 2:
        action = PathAction.DEMOTE_TO_REVIEW
        reason_code = ReplanningReasonCode.REVIEW_REQUIRED_DEMOTION
        affected_nodes.append(knowledge_id)

    # Priority 2: 掌握度跃迁检查 (after_mastery >= 0.80)
    elif f_after >= 0.80:
        # MASTERED != COMPLETED：若 is_task_context 且 before_path == IN_PROGRESS，才更新为 COMPLETED
        if is_task_context and before_path == PathState.IN_PROGRESS:
            after_path = PathState.COMPLETED
            path_updates[knowledge_id] = PathState.COMPLETED
            affected_nodes.append(knowledge_id)
        else:
            # 即使 PathState 未变，若认知状态首次跨越 0.80 门槛也计入 affected_nodes
            if f_before < 0.80:
                affected_nodes.append(knowledge_id)

        successors = get_successors(knowledge_id)
        if not successors:
            # 图谱终点节点或无后继节点
            action = PathAction.RETAIN
            reason_code = ReplanningReasonCode.MASTERY_THRESHOLD_REACHED
        else:
            unlocked_any = False
            has_blocked_by_coprereq = False

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
                        unlocked_any = True
                else:
                    # 检查是否有未满足的直接前置 p != knowledge_id
                    succ_prereqs = get_prerequisites(succ)
                    for p in succ_prereqs:
                        if p != knowledge_id and not is_knowledge_mastered(student_id, p, bkt_states_file=target_bkt_file):
                            has_blocked_by_coprereq = True
                            break

            if unlocked_any:
                action = PathAction.UNLOCK_DOWNSTREAM
                reason_code = ReplanningReasonCode.MASTERY_THRESHOLD_REACHED
            elif has_blocked_by_coprereq:
                action = PathAction.RETAIN
                reason_code = ReplanningReasonCode.PREREQUISITE_NOT_READY
            else:
                action = PathAction.RETAIN
                reason_code = ReplanningReasonCode.MASTERY_THRESHOLD_REACHED

    # Priority 3: 默认区间内状态未跨越门槛 (after_mastery < 0.80)
    else:
        action = PathAction.RETAIN
        reason_code = ReplanningReasonCode.MASTERY_STATE_UNCHANGED
        affected_nodes.append(knowledge_id)

    # 校验合法配对
    validate_decision_pair(action, reason_code)

    # 批量持久化发生状态变化的路径节点
    if path_updates:
        path_state_service.set_path_states_bulk(
            student_id, path_updates, states_file=target_states_file
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
