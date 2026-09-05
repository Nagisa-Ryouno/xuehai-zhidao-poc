# -*- coding: utf-8 -*-
"""
path_replanning_service.py
学海智导 V2 - Path Replanning Decision Core 契约层与规范化序列化器

职责与范围限制 (Task 2 契约层)：
1. 定义路径决策 Action 与 ReasonCode 强类型枚举
2. 固化 5 组合法决策矩阵与合法性校验器
3. 提供基于 Decimal + ROUND_HALF_UP 的四位定点掌握度规范化函数
4. 提供纯函数式、字节级确定性、与时序解耦的 Canonical 业务载荷模型及序列化器
5. 提供独立的审计元数据 (AuditMetadata) 与完整审计信封 (DecisionAuditEnvelope)

【红线提示】：本文件严禁实现 DAG 拓扑遍历、前置读取/判断与下游解锁逻辑（交由 Task 3 实现）。
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import json
from typing import Any, List, Optional, Set, Tuple, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
