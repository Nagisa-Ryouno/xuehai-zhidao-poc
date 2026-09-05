# P0-8 局部动态路径重规划引擎 (Local Adaptive Path Replanning Core) 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于已验收的 P0-7 测验-事件-BKT 闭环，实现“BKT 认知状态更新 → 局部 DAG 路径状态确定性重规划”引擎，完成从掌握度跃迁到前置依赖解锁的权威决策闭环。

**Architecture:** 采用严格契约化的“单跳确定性重规划模型 (DAG-Constrained Local Deterministic Replanning)”。决策核心采用只读探针读取 DAG 依赖与同辈前置（DecisionReadDomain），严格将状态变更域限制在 1-hop 邻域（MutationDomain = {Kc} ∪ Succ(Kc)）；通过单一合法优先级裁决生成冻结的 5 组合法决策之一；将确定性业务载荷（Canonical Business Payload）与非确定性审计元数据（Audit Metadata）物理分离，实现字节级等价断言。

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, openpyxl, pytest, unittest, Decimal (ROUND_HALF_UP).

---

## Global Constraints

- **BKT 数学模型零篡改**：严格消费 P0-6/P0-7 输出的潜变量掌握度浮点数，零修改 `bkt_service.py`、公式与参数 ($P(L_0)=0.20, P(T)=0.10, P(G)=0.20, P(S)=0.10$)。
- **架构极简与算法主权**：禁止引入 MQ/Celery/Redis/Kafka/LLM/Agent，完全基于纯 Python 函数式确定性算法驱动。
- **职责严格隔离**：
  - 不在 P0-8 Core 中实现 Focus Scheduling（焦点选择调度）；
  - 不在 P0-8 Core 中实现 `INSERT_PREREQ`、`INSERT_REMEDIAL`、冷却重置等补救调度行为；
  - 严禁 2-hop / 3-hop 级联解锁，单次决策仅评估直接后继 $\text{Succ}(K_c)$；
  - P0-8 仅能将下游节点状态置为 `AVAILABLE`，严禁直接自动晋升为 `IN_PROGRESS`。
- **状态正交解耦**：认知状态（`MasteryState`: `WEAK`, `DEVELOPING`, `MASTERED`, `NEEDS_REVIEW`）与路径状态（`PathState`: `LOCKED`, `AVAILABLE`, `IN_PROGRESS`, `COMPLETED`）正交。`MASTERED != COMPLETED`。只有在有效路径任务上下文且该节点处于 `IN_PROGRESS` 时，达成 `MASTERED` 才允许迁移为 `COMPLETED`。
- **定点数值与舍入标准**：
  - 内部状态机判断一律使用原生 IEEE-754 64-bit 浮点数比较 ($<0.60, \ge 0.80, <0.70$)，严禁使用格式化字符串参与逻辑判断；
  - `quantize(Decimal("0.0001"), ROUND_HALF_UP)` 是唯一法定舍入步骤；fixed-point string formatting 仅负责最终 4 位定点字符串表现（如 `"0.4566"`, `"0.8118"`），避免掌握度裸浮点值在 JSON 序列化与解析过程中产生表示差异，统一使用固定 4 位定点字符串表达。
- **Canonical 序列化准则**：
  - 当前 Canonical Business Payload 的对象键均限定为 ASCII 字符，因此按稳定字典序排序；Python 实现使用 `sort_keys=True`；
  - 数组字段 `affected_nodes` 严格按 ASCII 升序排列；
  - 紧凑分隔符 `separators=(',', ':')`，`ensure_ascii=False`，版本号固定 `rule_version="v1.0"`；
  - `decision_id` (UUIDv4)、`timestamp`、`trace_id` 物理剥离至 Audit Metadata，严禁进入 Canonical Business Payload，不参与确定性等价断言。
- **决策合法性矩阵（严格 5 组，单入口优先级裁决）**：
  1. `(UNLOCK_DOWNSTREAM, MASTERY_THRESHOLD_REACHED)`
  2. `(RETAIN, MASTERY_THRESHOLD_REACHED)`
  3. `(RETAIN, MASTERY_STATE_UNCHANGED)`
  4. `(RETAIN, PREREQUISITE_NOT_READY)`
  5. `(DEMOTE_TO_REVIEW, REVIEW_REQUIRED_DEMOTION)`
  - `PREREQUISITE_NOT_READY` 只有在 $K_c$ 达到 $P \ge 0.80$ 且存在后继但全受阻于未掌握同辈前置时才能产生；$P < 0.80$ 时绝对严禁产生 `PREREQUISITE_NOT_READY`。
- **开发方法论**：严格 TDD（测试先行，红灯失败 → 最小实现 → 绿灯通过 → 重构）。

---

## File Structure

```
xuehai-zhidao-poc/
├── path_state_service.py              # [NEW] 路径执行状态存储服务与持久化层 (LOCKED, AVAILABLE, IN_PROGRESS, COMPLETED)
├── path_replanning_service.py         # [NEW] 局部动态重规划核心决策引擎、数据契约、Decimal 格式化与规范化序列化器
├── quiz_service.py                    # [MODIFY] 在微测验答题闭环中触发重规划引擎，组装返回载荷
├── 04_api.py                          # [MODIFY] 增加学生路径状态查询端点，更新微测验返回模型
├── data/
│   ├── learning_path_states.json      # [RUNTIME] 独立持久化的学生路径状态快照文件
├── tests/
│   ├── test_path_state.py             # [NEW] 路径状态管理与原子持久化单测
│   ├── test_path_replanning_core.py   # [NEW] 决策核心、5组配对校验、定点舍入与规范序列化单测
│   ├── test_path_replanning_dag.py    # [NEW] DAG 只读探针、1-hop MutationDomain 隔离与负向测试
│   ├── test_path_replanning_golden_e2e.py # [NEW] Golden E2E 3步时序闭环与确定性等价字节级断言
│   └── test_quiz_replanning_integration.py # [NEW] 测验-事件-BKT-重规划完整 API 集成测试
```

---

## Task Breakdown

### Task 1: 路径状态服务与独立持久化层 (`path_state_service.py`)

**Files:**
- Create: `path_state_service.py`
- Test: `tests/test_path_state.py`

**Interfaces:**
- Consumes: None (独立系统层)
- Produces:
  - `class PathState(str, Enum)`: `LOCKED = "LOCKED"`, `AVAILABLE = "AVAILABLE"`, `IN_PROGRESS = "IN_PROGRESS"`, `COMPLETED = "COMPLETED"`
  - `class StudentPathStates(BaseModel)`: `student_id: str`, `states: Dict[str, PathState]`, `last_updated: Optional[str]`
  - `get_path_state(student_id: str, knowledge_id: str, states_file: Optional[Path] = None, default: PathState = PathState.LOCKED) -> PathState`
  - `set_path_state(student_id: str, knowledge_id: str, state: PathState, states_file: Optional[Path] = None) -> None`
  - `set_path_states_bulk(student_id: str, state_updates: Dict[str, PathState], states_file: Optional[Path] = None) -> None`
  - `get_all_path_states(student_id: str, states_file: Optional[Path] = None) -> Dict[str, PathState]`
  - `init_student_path(student_id: str, initial_states: Optional[Dict[str, PathState]] = None, states_file: Optional[Path] = None) -> None`

- [ ] **Step 1: 编写路径状态服务失败测试 (`tests/test_path_state.py`)**

```python
# -*- coding: utf-8 -*-
"""
tests/test_path_state.py
测试路径执行状态模型、默认初始化、状态迁移与原子持久化
"""
import tempfile
import unittest
from pathlib import Path

import path_state_service
from path_state_service import PathState


class TestPathStateService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.states_file = Path(self.temp_dir.name) / "test_path_states.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_default_state_is_locked(self):
        """未初始化的节点默认状态为 LOCKED"""
        state = path_state_service.get_path_state(
            "stu_001", "K08", states_file=self.states_file
        )
        self.assertEqual(state, PathState.LOCKED)

    def test_02_set_and_get_path_state(self):
        """单节点状态读写与持久化验证"""
        path_state_service.set_path_state(
            "stu_001", "K08", PathState.IN_PROGRESS, states_file=self.states_file
        )
        state = path_state_service.get_path_state(
            "stu_001", "K08", states_file=self.states_file
        )
        self.assertEqual(state, PathState.IN_PROGRESS)

    def test_03_bulk_update_path_states(self):
        """批量原子更新多节点状态"""
        updates = {
            "K08": PathState.COMPLETED,
            "K09": PathState.AVAILABLE,
            "K11": PathState.LOCKED,
        }
        path_state_service.set_path_states_bulk(
            "stu_001", updates, states_file=self.states_file
        )
        all_states = path_state_service.get_all_path_states(
            "stu_001", states_file=self.states_file
        )
        self.assertEqual(all_states["K08"], PathState.COMPLETED)
        self.assertEqual(all_states["K09"], PathState.AVAILABLE)
        self.assertEqual(all_states["K11"], PathState.LOCKED)

    def test_04_student_isolation(self):
        """不同学生之间的路径状态物理隔离"""
        path_state_service.set_path_state(
            "stu_001", "K08", PathState.COMPLETED, states_file=self.states_file
        )
        path_state_service.set_path_state(
            "stu_002", "K08", PathState.LOCKED, states_file=self.states_file
        )
        self.assertEqual(
            path_state_service.get_path_state("stu_001", "K08", states_file=self.states_file),
            PathState.COMPLETED,
        )
        self.assertEqual(
            path_state_service.get_path_state("stu_002", "K08", states_file=self.states_file),
            PathState.LOCKED,
        )
```

- [ ] **Step 2: 运行测试验证红灯 (FAIL)**

运行：`pytest tests/test_path_state.py -v`
预期：FAIL，提示 `ModuleNotFoundError: No module named 'path_state_service'`。

- [ ] **Step 3: 实现路径状态存储服务 (`path_state_service.py`)**

```python
# -*- coding: utf-8 -*-
"""
path_state_service.py
学海智导 V2 路径执行状态管理服务
负责维护与独立持久化学生在知识网络中的任务执行状态 (PathState)。
与 BKT 认知状态数据文件严格物理解耦，存储于 data/learning_path_states.json。
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_PATH_STATES_FILE = DATA_DIR / "learning_path_states.json"


class PathState(str, Enum):
    """
    节点在个性化任务流中的执行状态
    """
    LOCKED = "LOCKED"          # 未满足直接前置要求，锁定不可学
    AVAILABLE = "AVAILABLE"    # 所有直接前置均已掌握，已解锁待学习
    IN_PROGRESS = "IN_PROGRESS"# 当前正在学习/聚焦执行的任务节点
    COMPLETED = "COMPLETED"    # 在任务执行上下文中已成功达到掌握标准


class StudentPathProfile(BaseModel):
    student_id: str
    states: Dict[str, PathState] = Field(default_factory=dict)
    last_updated: Optional[str] = None


def _load_all_states(states_file: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    target_file = states_file or DEFAULT_PATH_STATES_FILE
    if not target_file.exists():
        return {}
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_all_states(data: Dict[str, Dict[str, str]], states_file: Optional[Path] = None) -> None:
    target_file = states_file or DEFAULT_PATH_STATES_FILE
    target_file.parent.mkdir(parents=True, exist_ok=True)

    # 原子写入：写入临时文件后重命名，防止进程并发/崩溃导致文件损坏
    with tempfile.NamedTemporaryFile("w", dir=str(target_file.parent), delete=False, encoding="utf-8") as tf:
        json.dump(data, tf, ensure_ascii=False, indent=2)
        temp_name = tf.name

    os.replace(temp_name, str(target_file))


def get_path_state(
    student_id: str,
    knowledge_id: str,
    states_file: Optional[Path] = None,
    default: PathState = PathState.LOCKED,
) -> PathState:
    data = _load_all_states(states_file)
    stu_dict = data.get(student_id, {})
    val = stu_dict.get(knowledge_id)
    if val:
        try:
            return PathState(val)
        except ValueError:
            return default
    return default


def set_path_state(
    student_id: str,
    knowledge_id: str,
    state: PathState,
    states_file: Optional[Path] = None,
) -> None:
    set_path_states_bulk(student_id, {knowledge_id: state}, states_file=states_file)


def set_path_states_bulk(
    student_id: str,
    state_updates: Dict[str, PathState],
    states_file: Optional[Path] = None,
) -> None:
    data = _load_all_states(states_file)
    if student_id not in data:
        data[student_id] = {}
    for k_id, st in state_updates.items():
        data[student_id][k_id] = st.value if isinstance(st, PathState) else str(st)
    _save_all_states(data, states_file=states_file)


def get_all_path_states(
    student_id: str,
    states_file: Optional[Path] = None,
) -> Dict[str, PathState]:
    data = _load_all_states(states_file)
    stu_dict = data.get(student_id, {})
    res: Dict[str, PathState] = {}
    for k_id, val in stu_dict.items():
        try:
            res[k_id] = PathState(val)
        except ValueError:
            res[k_id] = PathState.LOCKED
    return res


def init_student_path(
    student_id: str,
    initial_states: Optional[Dict[str, PathState]] = None,
    states_file: Optional[Path] = None,
) -> None:
    data = _load_all_states(states_file)
    if student_id not in data:
        data[student_id] = {}
    if initial_states:
        for k_id, st in initial_states.items():
            data[student_id][k_id] = st.value if isinstance(st, PathState) else str(st)
    _save_all_states(data, states_file=states_file)
```

- [ ] **Step 4: 运行测试验证绿灯 (PASS)**

运行：`pytest tests/test_path_state.py -v`
预期：4 passed in <0.2s。

- [ ] **Step 5: 提交代码**

```bash
git add path_state_service.py tests/test_path_state.py
git commit -m "feat(p0-8): implement path state management and persistence service"
```

---

### Task 2: 决策核心契约、定点格式化与规范序列化器 (`path_replanning_service.py` Part 1)

**Files:**
- Create: `path_replanning_service.py`
- Test: `tests/test_path_replanning_core.py`

**Interfaces:**
- Consumes: `path_state_service.PathState`
- Produces:
  - `class PathAction(str, Enum)`: `UNLOCK_DOWNSTREAM = "UNLOCK_DOWNSTREAM"`, `RETAIN = "RETAIN"`, `DEMOTE_TO_REVIEW = "DEMOTE_TO_REVIEW"`
  - `class ReplanningReasonCode(str, Enum)`: `MASTERY_THRESHOLD_REACHED = "MASTERY_THRESHOLD_REACHED"`, `MASTERY_STATE_UNCHANGED = "MASTERY_STATE_UNCHANGED"`, `PREREQUISITE_NOT_READY = "PREREQUISITE_NOT_READY"`, `REVIEW_REQUIRED_DEMOTION = "REVIEW_REQUIRED_DEMOTION"`
  - `LEGAL_DECISION_PAIRS = Set[Tuple[PathAction, ReplanningReasonCode]]`
  - `format_canonical_mastery(raw_float: float) -> str`: 严格执行 `Decimal(str(raw_float)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)` 格式化为 4 位小数字符串
  - `class CanonicalBusinessPayload(BaseModel)`:
    - 字段：`rule_version="v1.0"`, `student_id`, `knowledge_id`, `before_mastery`, `after_mastery`, `before_path_state`, `after_path_state`, `action`, `reason_code`, `affected_nodes: List[str]`
    - 方法：`to_canonical_json() -> str`（`sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`）
  - `class AuditMetadata(BaseModel)`:
    - 字段：`decision_id: str`, `timestamp: str`, `trace_id: Optional[str] = None`
  - `class DecisionAuditEnvelope(BaseModel)`:
    - 字段：`audit_metadata: AuditMetadata`, `canonical_payload: CanonicalBusinessPayload`

- [ ] **Step 1: 编写数据契约与规范序列化失败测试 (`tests/test_path_replanning_core.py`)**

```python
# -*- coding: utf-8 -*-
"""
tests/test_path_replanning_core.py
测试定点数舍入、5组决策矩阵合法性校验、载荷与元数据物理分离、规范化 JSON 序列化
"""
import json
import unittest
from decimal import Decimal

import path_replanning_service
from path_replanning_service import (
    PathAction,
    ReplanningReasonCode,
    LEGAL_DECISION_PAIRS,
    validate_decision_pair,
    format_canonical_mastery,
    CanonicalBusinessPayload,
    AuditMetadata,
    DecisionAuditEnvelope,
)
from path_state_service import PathState


class TestPathReplanningCore(unittest.TestCase):
    def test_01_canonical_mastery_rounding_and_formatting(self):
        """验证 Decimal + ROUND_HALF_UP 4位定点小数字符串生成"""
        self.assertEqual(format_canonical_mastery(0.2), "0.2000")
        self.assertEqual(format_canonical_mastery(0.1273499), "0.1273")
        self.assertEqual(format_canonical_mastery(0.45661), "0.4566")
        self.assertEqual(format_canonical_mastery(0.81180), "0.8118")
        self.assertEqual(format_canonical_mastery(0.81185), "0.8119")  # HALF_UP
        self.assertEqual(format_canonical_mastery(0.12725), "0.1273")  # HALF_UP

    def test_02_legal_decision_pairs_membership(self):
        """严格闭合 5 组合法决策矩阵验证"""
        self.assertEqual(len(LEGAL_DECISION_PAIRS), 5)
        self.assertIn((PathAction.UNLOCK_DOWNSTREAM, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED), LEGAL_DECISION_PAIRS)
        self.assertIn((PathAction.RETAIN, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED), LEGAL_DECISION_PAIRS)
        self.assertIn((PathAction.RETAIN, ReplanningReasonCode.MASTERY_STATE_UNCHANGED), LEGAL_DECISION_PAIRS)
        self.assertIn((PathAction.RETAIN, ReplanningReasonCode.PREREQUISITE_NOT_READY), LEGAL_DECISION_PAIRS)
        self.assertIn((PathAction.DEMOTE_TO_REVIEW, ReplanningReasonCode.REVIEW_REQUIRED_DEMOTION), LEGAL_DECISION_PAIRS)

    def test_03_invalid_decision_pairs_rejected(self):
        """非法配对直接抛出 ValueError"""
        with self.assertRaises(ValueError):
            validate_decision_pair(PathAction.UNLOCK_DOWNSTREAM, ReplanningReasonCode.MASTERY_STATE_UNCHANGED)

        with self.assertRaises(ValueError):
            validate_decision_pair(PathAction.DEMOTE_TO_REVIEW, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED)

    def test_04_canonical_business_payload_json_determinism(self):
        """验证 Canonical Business Payload 规范 JSON Profile (ASCII字典序、紧凑无空白、定点数表达)"""
        payload = CanonicalBusinessPayload(
            rule_version="v1.0",
            student_id="stu_dev_001",
            knowledge_id="K08",
            before_mastery="0.4566",
            after_mastery="0.8118",
            before_path_state=PathState.IN_PROGRESS,
            after_path_state=PathState.COMPLETED,
            action=PathAction.UNLOCK_DOWNSTREAM,
            reason_code=ReplanningReasonCode.MASTERY_THRESHOLD_REACHED,
            affected_nodes=["K09", "K08"],  # 乱序传入
        )

        canonical_json = payload.to_canonical_json()
        expected = (
            '{"action":"UNLOCK_DOWNSTREAM",'
            '"affected_nodes":["K08","K09"],'
            '"after_mastery":"0.8118",'
            '"after_path_state":"COMPLETED",'
            '"before_mastery":"0.4566",'
            '"before_path_state":"IN_PROGRESS",'
            '"knowledge_id":"K08",'
            '"reason_code":"MASTERY_THRESHOLD_REACHED",'
            '"rule_version":"v1.0",'
            '"student_id":"stu_dev_001"}'
        )
        self.assertEqual(canonical_json, expected)

    def test_05_payload_and_metadata_physical_separation(self):
        """验证 decision_id 和 timestamp 改变绝不改变 Canonical Business Payload"""
        meta1 = AuditMetadata(
            decision_id="11111111-1111-4111-8111-111111111111",
            timestamp="2026-09-05T12:00:00.000Z",
        )
        meta2 = AuditMetadata(
            decision_id="22222222-2222-4222-8222-222222222222",
            timestamp="2026-09-05T13:00:00.000Z",
        )
        payload = CanonicalBusinessPayload(
            rule_version="v1.0",
            student_id="stu_dev_001",
            knowledge_id="K08",
            before_mastery="0.1273",
            after_mastery="0.4566",
            before_path_state=PathState.IN_PROGRESS,
            after_path_state=PathState.IN_PROGRESS,
            action=PathAction.RETAIN,
            reason_code=ReplanningReasonCode.MASTERY_STATE_UNCHANGED,
            affected_nodes=["K08"],
        )
        env1 = DecisionAuditEnvelope(audit_metadata=meta1, canonical_payload=payload)
        env2 = DecisionAuditEnvelope(audit_metadata=meta2, canonical_payload=payload)

        self.assertNotEqual(env1.audit_metadata.decision_id, env2.audit_metadata.decision_id)
        self.assertEqual(
            env1.canonical_payload.to_canonical_json(),
            env2.canonical_payload.to_canonical_json(),
        )
```

- [ ] **Step 2: 运行测试验证红灯 (FAIL)**

运行：`pytest tests/test_path_replanning_core.py -v`
预期：FAIL，提示 `ModuleNotFoundError: No module named 'path_replanning_service'`。

- [ ] **Step 3: 编写数据契约与规范序列化实现 (`path_replanning_service.py` 基础骨架)**

```python
# -*- coding: utf-8 -*-
"""
path_replanning_service.py
学海智导 V2 局部动态路径重规划核心决策引擎
实现架构冻结 Architecture Freeze Final v6 规范：
- 严格闭合 5 组决策合法性矩阵
- Decimal + ROUND_HALF_UP 四位定点字符串规范化
- Canonical Business Payload 与 Audit Metadata 物理分离
- 稳定 ASCII 字典序排序与紧凑 JSON 序列化
"""
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from path_state_service import PathState
import knowledge_graph_service
import bkt_state_service


class PathAction(str, Enum):
    UNLOCK_DOWNSTREAM = "UNLOCK_DOWNSTREAM"
    RETAIN = "RETAIN"
    DEMOTE_TO_REVIEW = "DEMOTE_TO_REVIEW"


class ReplanningReasonCode(str, Enum):
    MASTERY_THRESHOLD_REACHED = "MASTERY_THRESHOLD_REACHED"
    MASTERY_STATE_UNCHANGED = "MASTERY_STATE_UNCHANGED"
    PREREQUISITE_NOT_READY = "PREREQUISITE_NOT_READY"
    REVIEW_REQUIRED_DEMOTION = "REVIEW_REQUIRED_DEMOTION"


# 严格闭合的 5 组合法决策矩阵
LEGAL_DECISION_PAIRS: Set[Tuple[PathAction, ReplanningReasonCode]] = {
    (PathAction.UNLOCK_DOWNSTREAM, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED),
    (PathAction.RETAIN, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED),
    (PathAction.RETAIN, ReplanningReasonCode.MASTERY_STATE_UNCHANGED),
    (PathAction.RETAIN, ReplanningReasonCode.PREREQUISITE_NOT_READY),
    (PathAction.DEMOTE_TO_REVIEW, ReplanningReasonCode.REVIEW_REQUIRED_DEMOTION),
}


def validate_decision_pair(action: PathAction, reason_code: ReplanningReasonCode) -> None:
    """校验决策动作与原因代码配对是否合法"""
    pair = (action, reason_code)
    if pair not in LEGAL_DECISION_PAIRS:
        raise ValueError(f"非法决策动作与原因组合: action={action.value}, reason_code={reason_code.value}")


def format_canonical_mastery(raw_float: float) -> str:
    """
    quantize(Decimal("0.0001"), ROUND_HALF_UP) 是唯一法定舍入步骤；
    fixed-point string formatting 仅负责最终 4 位字符串表现，避免掌握度裸浮点值在 JSON 序列化与解析过程中产生表示差异。
    """
    d = Decimal(str(raw_float))
    rounded = d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return f"{rounded:.4f}"


class CanonicalBusinessPayload(BaseModel):
    """
    参与业务决策等价性与确定性断言的核心载荷
    当前对象键均限定为 ASCII 字符，因此按稳定字典序排序；Python 实现使用 sort_keys=True。
    """
    rule_version: str = "v1.0"
    student_id: str
    knowledge_id: str
    before_mastery: str
    after_mastery: str
    before_path_state: PathState
    after_path_state: PathState
    action: PathAction
    reason_code: ReplanningReasonCode
    affected_nodes: List[str]

    def to_canonical_json(self) -> str:
        # 保证 affected_nodes 严格以 ASCII 字典序排序
        sorted_nodes = sorted(list(set(self.affected_nodes)))
        data_dict = {
            "rule_version": self.rule_version,
            "student_id": self.student_id,
            "knowledge_id": self.knowledge_id,
            "before_mastery": self.before_mastery,
            "after_mastery": self.after_mastery,
            "before_path_state": self.before_path_state.value if isinstance(self.before_path_state, PathState) else str(self.before_path_state),
            "after_path_state": self.after_path_state.value if isinstance(self.after_path_state, PathState) else str(self.after_path_state),
            "action": self.action.value if isinstance(self.action, PathAction) else str(self.action),
            "reason_code": self.reason_code.value if isinstance(self.reason_code, ReplanningReasonCode) else str(self.reason_code),
            "affected_nodes": sorted_nodes,
        }
        return json.dumps(data_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class AuditMetadata(BaseModel):
    """非确定性审计追踪元数据，严禁参与确定性断言"""
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    trace_id: Optional[str] = None


class DecisionAuditEnvelope(BaseModel):
    """完整的决策审计外层包装模型"""
    audit_metadata: AuditMetadata
    canonical_payload: CanonicalBusinessPayload
```

- [ ] **Step 4: 运行测试验证绿灯 (PASS)**

运行：`pytest tests/test_path_replanning_core.py -v`
预期：5 passed in <0.2s。

- [ ] **Step 5: 提交代码**

```bash
git add path_replanning_service.py tests/test_path_replanning_core.py
git commit -m "feat(p0-8): add decision core data contracts, decimal formatter and canonical serializer"
```

---

### Task 3: DAG 只读探针、1-hop MutationDomain 与核心裁决引擎 (`path_replanning_service.py` Part 2)

**Files:**
- Modify: `path_replanning_service.py`
- Test: `tests/test_path_replanning_dag.py`

**Interfaces:**
- Consumes:
  - `knowledge_graph_service.knowledge_graph_service._raw_knowledge_points`
  - `bkt_state_service.get_state(student_id, k_id)`
  - `path_state_service.get_path_state`, `set_path_states_bulk`
- Produces:
  - `evaluate_and_replan(student_id: str, knowledge_id: str, before_mastery: float, after_mastery: float, consecutive_incorrect: int = 0, previously_mastered: bool = False, is_task_context: bool = True, trace_id: Optional[str] = None, states_file: Optional[Path] = None, bkt_states_file: Optional[Path] = None) -> DecisionAuditEnvelope`
  - 核心只读辅助方法：
    - `get_prerequisites(knowledge_id: str) -> List[str]`
    - `get_successors(knowledge_id: str) -> List[str]`
    - `can_unlock_successor(student_id: str, successor_id: str, current_just_mastered: str, bkt_states_file: Optional[Path] = None) -> bool`

- [ ] **Step 1: 编写 DAG 只读探针、1-hop 隔离与负向测试 (`tests/test_path_replanning_dag.py`)**

```python
# -*- coding: utf-8 -*-
"""
tests/test_path_replanning_dag.py
测试 DAG 只读探针、1-hop MutationDomain 物理隔离与全套负向测试用例：
1. P < 0.80 时绝不能产生 PREREQUISITE_NOT_READY
2. 非直接后继绝对不得进入 affected_nodes
3. K11 拥有双前置 (K08, K10)，在 K10 未掌握时，不得因 K08 达标而级联解锁，必须保持 LOCKED 且不得进入 affected_nodes
4. AVAILABLE 绝不得自动转为 IN_PROGRESS
5. 非任务上下文下的 MASTERED 绝不得自动将 PathState 置为 COMPLETED
6. 孤立/终点节点达成 MASTERED 时返回 RETAIN × MASTERY_THRESHOLD_REACHED
"""
import tempfile
import unittest
from pathlib import Path

import bkt_state_service
import path_state_service
import path_replanning_service
from path_state_service import PathState
from path_replanning_service import PathAction, ReplanningReasonCode


class TestPathReplanningDAG(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path_states_file = Path(self.temp_dir.name) / "test_path_states.json"
        self.bkt_states_file = Path(self.temp_dir.name) / "test_bkt_states.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_negative_p_below_080_never_prerequisite_not_ready(self):
        """负向测试 1: 当 P(L) < 0.80 时，无论下游前置情况如何，绝对严禁生成 PREREQUISITE_NOT_READY"""
        # 设定 K08 此时仅 0.4566 (< 0.80)，且下游 K11 确有未满足前置
        envelope = path_replanning_service.evaluate_and_replan(
            student_id="stu_001",
            knowledge_id="K08",
            before_mastery=0.1273,
            after_mastery=0.4566,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        payload = envelope.canonical_payload
        self.assertEqual(payload.action, PathAction.RETAIN)
        self.assertEqual(payload.reason_code, ReplanningReasonCode.MASTERY_STATE_UNCHANGED)
        self.assertNotEqual(payload.reason_code, ReplanningReasonCode.PREREQUISITE_NOT_READY)

    def test_02_mutation_domain_1hop_isolation_and_k11_locked(self):
        """负向测试 2 & 3: K11 保持 LOCKED，严禁进入 affected_nodes，严禁 2-hop 级联"""
        # 初始化：K08 IN_PROGRESS, K09 LOCKED, K11 LOCKED, K10 未掌握
        path_state_service.set_path_states_bulk(
            "stu_001",
            {
                "K08": PathState.IN_PROGRESS,
                "K09": PathState.LOCKED,
                "K11": PathState.LOCKED,
            },
            states_file=self.path_states_file,
        )

        envelope = path_replanning_service.evaluate_and_replan(
            student_id="stu_001",
            knowledge_id="K08",
            before_mastery=0.4566,
            after_mastery=0.8118,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        payload = envelope.canonical_payload
        # K08 完结，K09 解锁为 AVAILABLE
        self.assertEqual(payload.action, PathAction.UNLOCK_DOWNSTREAM)
        self.assertEqual(payload.reason_code, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED)
        self.assertEqual(payload.affected_nodes, ["K08", "K09"])
        self.assertNotIn("K11", payload.affected_nodes)

        # 检查持久化状态：K11 必须依然是 LOCKED
        k11_state = path_state_service.get_path_state("stu_001", "K11", states_file=self.path_states_file)
        self.assertEqual(k11_state, PathState.LOCKED)

        # 检查 K09 必须是 AVAILABLE，绝不可自动变为 IN_PROGRESS
        k09_state = path_state_service.get_path_state("stu_001", "K09", states_file=self.path_states_file)
        self.assertEqual(k09_state, PathState.AVAILABLE)

    def test_03_prerequisite_not_ready_fired_only_when_mastered_and_all_succ_blocked(self):
        """当且仅当 Kc 达标 (P>=0.80) 且所有后继均因联合前置未满足而受阻时，产生 PREREQUISITE_NOT_READY"""
        # 设定虚拟测试场景：K09 已先被置为 AVAILABLE，只剩下 K11 作为需要解锁的后继，但 K10 未掌握
        path_state_service.set_path_states_bulk(
            "stu_001",
            {
                "K08": PathState.IN_PROGRESS,
                "K09": PathState.AVAILABLE,  # 已是 AVAILABLE，不需要再次解锁
                "K11": PathState.LOCKED,     # 依赖 K08, K09, K10，但 K10 未掌握
            },
            states_file=self.path_states_file,
        )

        envelope = path_replanning_service.evaluate_and_replan(
            student_id="stu_001",
            knowledge_id="K08",
            before_mastery=0.7500,
            after_mastery=0.8500,  # 达标
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        payload = envelope.canonical_payload
        # K09 状态未变，K11 无法解锁，因此所有后继均无法解锁，且 K11 受到未掌握前置阻塞
        self.assertEqual(payload.action, PathAction.RETAIN)
        self.assertEqual(payload.reason_code, ReplanningReasonCode.PREREQUISITE_NOT_READY)
        self.assertEqual(payload.affected_nodes, ["K08"])

    def test_04_negative_non_task_context_does_not_complete_path_state(self):
        """负向测试 5: 非任务上下文（如自主测验），MASTERED 不得修改 PathState 为 COMPLETED"""
        path_state_service.set_path_state(
            "stu_001", "K08", PathState.AVAILABLE, states_file=self.path_states_file
        )
        envelope = path_replanning_service.evaluate_and_replan(
            student_id="stu_001",
            knowledge_id="K08",
            before_mastery=0.75,
            after_mastery=0.85,
            is_task_context=False,  # 非任务上下文
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        payload = envelope.canonical_payload
        # 路径状态保持原样 AVAILABLE
        self.assertEqual(payload.before_path_state, PathState.AVAILABLE)
        self.assertEqual(payload.after_path_state, PathState.AVAILABLE)
        # K08 不应该作为 PathState 改变进入 affected_nodes（除非后继节点解锁）
        k08_state = path_state_service.get_path_state("stu_001", "K08", states_file=self.path_states_file)
        self.assertEqual(k08_state, PathState.AVAILABLE)

    def test_05_regression_demotion_trigger(self):
        """认知退化检查：曾掌握且跌破 0.70 且连错 >= 2 触发 DEMOTE_TO_REVIEW"""
        envelope = path_replanning_service.evaluate_and_replan(
            student_id="stu_001",
            knowledge_id="K08",
            before_mastery=0.72,
            after_mastery=0.65,
            consecutive_incorrect=2,
            previously_mastered=True,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        payload = envelope.canonical_payload
        self.assertEqual(payload.action, PathAction.DEMOTE_TO_REVIEW)
        self.assertEqual(payload.reason_code, ReplanningReasonCode.REVIEW_REQUIRED_DEMOTION)
```

- [ ] **Step 2: 运行测试验证红灯 (FAIL)**

运行：`pytest tests/test_path_replanning_dag.py -v`
预期：FAIL，提示 `AttributeError: module 'path_replanning_service' has no attribute 'evaluate_and_replan'`。

- [ ] **Step 3: 实现核心裁决引擎与 DAG 只读探针 (`path_replanning_service.py` 完整实现)**

在 `path_replanning_service.py` 中追加实现：

```python
def get_prerequisites(knowledge_id: str) -> List[str]:
    """从权威知识图谱中读取知识点的直接前置依赖列表 (Read-Only)"""
    kp_dict = knowledge_graph_service.knowledge_graph_service._raw_knowledge_points.get(knowledge_id, {})
    return list(kp_dict.get("prerequisite", []))


def get_successors(knowledge_id: str) -> List[str]:
    """从权威知识图谱中读取知识点的直接后继知识点列表 (Read-Only)"""
    kp_dict = knowledge_graph_service.knowledge_graph_service._raw_knowledge_points.get(knowledge_id, {})
    return list(kp_dict.get("next_knowledge", []))


def is_knowledge_mastered(student_id: str, knowledge_id: str, bkt_states_file: Optional[Path] = None) -> bool:
    """检查知识点是否已达到 MASTERED 门槛 (P(L) >= 0.80)"""
    state = bkt_state_service.get_state(student_id, knowledge_id, states_file=bkt_states_file, auto_init=False)
    if state is None:
        return False
    return state.mastery_probability >= 0.80


def can_unlock_successor(
    student_id: str,
    successor_id: str,
    current_just_mastered: str,
    bkt_states_file: Optional[Path] = None,
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


def evaluate_and_replan(
    student_id: str,
    knowledge_id: str,
    before_mastery: float,
    after_mastery: float,
    consecutive_incorrect: int = 0,
    previously_mastered: bool = False,
    is_task_context: bool = True,
    trace_id: Optional[str] = None,
    states_file: Optional[Path] = None,
    bkt_states_file: Optional[Path] = None,
) -> DecisionAuditEnvelope:
    """
    局部动态重规划唯一权威裁决入口。
    严格执行单入口优先级裁决 (Reason Resolution Priority):
    1. 认知退化判定 (REVIEW_REQUIRED_DEMOTION)
    2. 掌握度达标判定 (after_mastery >= 0.80)
       2.1 成功解锁至少 1 个后继 -> UNLOCK_DOWNSTREAM × MASTERY_THRESHOLD_REACHED
       2.2 所有后继因同辈前置未满足而受阻 -> RETAIN × PREREQUISITE_NOT_READY
       2.3 无后继 (终点/孤立节点) 或所有后继本已是 AVAILABLE/COMPLETED -> RETAIN × MASTERY_THRESHOLD_REACHED
    3. 状态未变更判定 -> RETAIN × MASTERY_STATE_UNCHANGED
    """
    before_path = path_state_service.get_path_state(student_id, knowledge_id, states_file=states_file)
    after_path = before_path

    affected_nodes: List[str] = []
    path_updates: Dict[str, PathState] = {}

    action: PathAction
    reason_code: ReplanningReasonCode

    # -------------------------------------------------------------
    # 状态机内部阈值判断使用原生浮点数 IEEE-754，严禁使用格式化字符串比较
    # -------------------------------------------------------------

    # Priority 1: 认知回退检查 (曾掌握且 P<0.70 且连错 >= 2)
    if previously_mastered and after_mastery < 0.70 and consecutive_incorrect >= 2:
        action = PathAction.DEMOTE_TO_REVIEW
        reason_code = ReplanningReasonCode.REVIEW_REQUIRED_DEMOTION
        # 回退不撤销 COMPLETED 路径状态，但记录本节点变化
        affected_nodes.append(knowledge_id)

    # Priority 2: 掌握度跃迁检查 (after_mastery >= 0.80)
    elif after_mastery >= 0.80:
        # MASTERED != COMPLETED：只有处于任务上下文且当前状态为 IN_PROGRESS，才更新为 COMPLETED
        if is_task_context and before_path == PathState.IN_PROGRESS:
            after_path = PathState.COMPLETED
            path_updates[knowledge_id] = PathState.COMPLETED
            affected_nodes.append(knowledge_id)
        else:
            # 即使 PathState 未变，若认知状态首次达标也计入 affected_nodes
            if before_mastery < 0.80:
                affected_nodes.append(knowledge_id)

        successors = get_successors(knowledge_id)
        if not successors:
            # 终点节点或无后继节点
            action = PathAction.RETAIN
            reason_code = ReplanningReasonCode.MASTERY_THRESHOLD_REACHED
        else:
            unlocked_any = False
            has_blocked_by_coprereq = False

            for succ in successors:
                succ_state = path_state_service.get_path_state(student_id, succ, states_file=states_file)
                can_unlock = can_unlock_successor(
                    student_id, succ, current_just_mastered=knowledge_id, bkt_states_file=bkt_states_file
                )
                if can_unlock:
                    if succ_state == PathState.LOCKED:
                        # 严格更新为 AVAILABLE，绝不得直接设置为 IN_PROGRESS
                        path_updates[succ] = PathState.AVAILABLE
                        affected_nodes.append(succ)
                        unlocked_any = True
                else:
                    # 检查是否有未满足的前置 p != knowledge_id
                    succ_prereqs = get_prerequisites(succ)
                    for p in succ_prereqs:
                        if p != knowledge_id and not is_knowledge_mastered(student_id, p, bkt_states_file=bkt_states_file):
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

    # Priority 3: 默认区间内状态未跨越门槛
    else:
        action = PathAction.RETAIN
        reason_code = ReplanningReasonCode.MASTERY_STATE_UNCHANGED
        # BKT 状态有更新，当前节点计入 affected_nodes
        affected_nodes.append(knowledge_id)

    # 校验合法配对
    validate_decision_pair(action, reason_code)

    # 持久化实际发生状态改变的节点
    if path_updates:
        path_state_service.set_path_states_bulk(student_id, path_updates, states_file=states_file)

    # 组装 Canonical Business Payload 与 Audit Metadata
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
```

- [ ] **Step 4: 运行测试验证绿灯 (PASS)**

运行：`pytest tests/test_path_replanning_dag.py -v`
预期：5 passed in <0.3s。

- [ ] **Step 5: 提交代码**

```bash
git add path_replanning_service.py tests/test_path_replanning_dag.py
git commit -m "feat(p0-8): implement local replanning core with DAG probe and 1-hop isolation"
```

---

### Task 4: Golden E2E 3 步时序闭环与确定性等价字节级断言 (`tests/test_path_replanning_golden_e2e.py`)

**Files:**
- Create: `tests/test_path_replanning_golden_e2e.py`

**Interfaces:**
- Consumes:
  - `path_replanning_service.evaluate_and_replan`
  - `bkt_service.apply_attempt`, `bkt_state_service`
  - `path_state_service`
- Produces:
  - 覆盖 Golden E2E Step 1 (Wrong, 0.1273), Step 2 (Correct, 0.4566), Step 3 (Correct, 0.8118) 严格数值与状态断言
  - 覆盖确定性断言：重复执行字节级一致性（`hash(payload1.to_canonical_json()) == hash(payload2.to_canonical_json())`）
  - 覆盖负向断言：修改 `decision_id` 与 `timestamp` 不改变 Canonical Payload JSON

- [ ] **Step 1: 编写 Golden E2E 与确定性等价断言测试 (`tests/test_path_replanning_golden_e2e.py`)**

```python
# -*- coding: utf-8 -*-
"""
tests/test_path_replanning_golden_e2e.py
P0-8 黄金端到端 (Golden E2E) 3步时序流转与确定性等价测试
拓扑背景：
- K08 需求价格弹性 (初始 0.2000, IN_PROGRESS)
- K09 收入与交叉弹性 (直接后继，前置仅 K08，初始 0.2000, LOCKED)
- K10 供给弹性 (前置 K05/K07，初始 0.2000, 未掌握)
- K11 弹性与税收归宿 (双前置 K08, K09, K10，初始 0.2000, LOCKED)
"""
import hashlib
import tempfile
import unittest
from pathlib import Path

import bkt_service
import bkt_state_service
import path_state_service
import path_replanning_service
from path_state_service import PathState
from path_replanning_service import PathAction, ReplanningReasonCode


class TestGoldenE2EAndDeterminism(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path_states_file = Path(self.temp_dir.name) / "test_path_states.json"
        self.bkt_states_file = Path(self.temp_dir.name) / "test_bkt_states.json"
        self.student_id = "stu_dev_001"

        # 初始化学生节点状态
        path_state_service.set_path_states_bulk(
            self.student_id,
            {
                "K08": PathState.IN_PROGRESS,
                "K09": PathState.LOCKED,
                "K11": PathState.LOCKED,
            },
            states_file=self.path_states_file,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_golden_e2e_three_steps(self):
        """执行黄金端到端 3 步闭环测试"""
        # -------------------------------------------------------------
        # Step 1: 答错 (Wrong)
        # BKT: 0.2000 -> 0.1273499...
        # -------------------------------------------------------------
        bkt_state_0 = bkt_service.create_initial_state(self.student_id, "K08")
        step1_res = bkt_service.apply_attempt(bkt_state_0, is_correct=False)
        bkt_state_service.save_state(step1_res.state, states_file=self.bkt_states_file)

        env_step1 = path_replanning_service.evaluate_and_replan(
            student_id=self.student_id,
            knowledge_id="K08",
            before_mastery=bkt_state_0.mastery_probability,
            after_mastery=step1_res.state.mastery_probability,
            consecutive_incorrect=step1_res.state.consecutive_incorrect,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        p1 = env_step1.canonical_payload
        self.assertEqual(p1.before_mastery, "0.2000")
        self.assertEqual(p1.after_mastery, "0.1273")
        self.assertEqual(p1.before_path_state, PathState.IN_PROGRESS)
        self.assertEqual(p1.after_path_state, PathState.IN_PROGRESS)
        self.assertEqual(p1.action, PathAction.RETAIN)
        self.assertEqual(p1.reason_code, ReplanningReasonCode.MASTERY_STATE_UNCHANGED)
        self.assertEqual(p1.affected_nodes, ["K08"])
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K09", states_file=self.path_states_file),
            PathState.LOCKED,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K11", states_file=self.path_states_file),
            PathState.LOCKED,
        )

        # -------------------------------------------------------------
        # Step 2: 答对 (Correct)
        # BKT: 0.1273499... -> 0.45661...
        # 掌握度 0.4566 严格属于 WEAK (< 0.60)，绝非 DEVELOPING
        # -------------------------------------------------------------
        step2_res = bkt_service.apply_attempt(step1_res.state, is_correct=True)
        bkt_state_service.save_state(step2_res.state, states_file=self.bkt_states_file)

        env_step2 = path_replanning_service.evaluate_and_replan(
            student_id=self.student_id,
            knowledge_id="K08",
            before_mastery=step1_res.state.mastery_probability,
            after_mastery=step2_res.state.mastery_probability,
            consecutive_incorrect=step2_res.state.consecutive_incorrect,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        p2 = env_step2.canonical_payload
        self.assertEqual(p2.before_mastery, "0.1273")
        self.assertEqual(p2.after_mastery, "0.4566")
        self.assertEqual(p2.before_path_state, PathState.IN_PROGRESS)
        self.assertEqual(p2.after_path_state, PathState.IN_PROGRESS)
        self.assertEqual(p2.action, PathAction.RETAIN)
        self.assertEqual(p2.reason_code, ReplanningReasonCode.MASTERY_STATE_UNCHANGED)
        self.assertEqual(p2.affected_nodes, ["K08"])
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K09", states_file=self.path_states_file),
            PathState.LOCKED,
        )

        # -------------------------------------------------------------
        # Step 3: 答对 (Correct)
        # BKT: 0.45661... -> 0.81180...
        # 掌握度 0.8118 达到 MASTERED (>= 0.80)
        # K08 -> COMPLETED
        # K09 -> AVAILABLE (解锁!)
        # K11 -> 仍为 LOCKED (因为 K10 未掌握)，绝对不得进入 affected_nodes
        # -------------------------------------------------------------
        step3_res = bkt_service.apply_attempt(step2_res.state, is_correct=True)
        bkt_state_service.save_state(step3_res.state, states_file=self.bkt_states_file)

        env_step3 = path_replanning_service.evaluate_and_replan(
            student_id=self.student_id,
            knowledge_id="K08",
            before_mastery=step2_res.state.mastery_probability,
            after_mastery=step3_res.state.mastery_probability,
            consecutive_incorrect=step3_res.state.consecutive_incorrect,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        p3 = env_step3.canonical_payload
        self.assertEqual(p3.before_mastery, "0.4566")
        self.assertEqual(p3.after_mastery, "0.8118")
        self.assertEqual(p3.before_path_state, PathState.IN_PROGRESS)
        self.assertEqual(p3.after_path_state, PathState.COMPLETED)
        self.assertEqual(p3.action, PathAction.UNLOCK_DOWNSTREAM)
        self.assertEqual(p3.reason_code, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED)
        self.assertEqual(p3.affected_nodes, ["K08", "K09"])
        self.assertNotIn("K11", p3.affected_nodes)

        # 验证物理状态
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K08", states_file=self.path_states_file),
            PathState.COMPLETED,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K09", states_file=self.path_states_file),
            PathState.AVAILABLE,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K11", states_file=self.path_states_file),
            PathState.LOCKED,
        )

    def test_02_canonical_payload_determinism_byte_for_byte(self):
        """确定性测试：完全相同的输入多次执行，生成的 Canonical Payload 必须字节级一致"""
        json_outputs = []
        for _ in range(5):
            env = path_replanning_service.evaluate_and_replan(
                student_id="stu_det_001",
                knowledge_id="K08",
                before_mastery=0.45661,
                after_mastery=0.81180,
                states_file=self.path_states_file,
                bkt_states_file=self.bkt_states_file,
            )
            json_outputs.append(env.canonical_payload.to_canonical_json())

        first_json = json_outputs[0]
        first_hash = hashlib.sha256(first_json.encode("utf-8")).hexdigest()
        for idx, item in enumerate(json_outputs[1:], start=2):
            item_hash = hashlib.sha256(item.encode("utf-8")).hexdigest()
            self.assertEqual(
                item_hash,
                first_hash,
                f"第 {idx} 次运行与第 1 次运行的 Canonical Payload 哈希不一致",
            )
            self.assertEqual(item, first_json)
```

- [ ] **Step 2: 运行测试验证绿灯 (PASS)**

运行：`pytest tests/test_path_replanning_golden_e2e.py -v`
预期：2 passed in <0.3s。

- [ ] **Step 3: 提交代码**

```bash
git add tests/test_path_replanning_golden_e2e.py
git commit -m "test(p0-8): add golden e2e 3-step sequence and byte-for-byte determinism tests"
```

---

### Task 5: 测验答题闭环集成与 API 端点 (`quiz_service.py` & `04_api.py`)

**Files:**
- Modify: `quiz_service.py`
- Modify: `04_api.py`
- Test: `tests/test_quiz_replanning_integration.py`

**Interfaces:**
- Consumes: `path_replanning_service.evaluate_and_replan`, `DecisionAuditEnvelope`
- Produces:
  - `QuizSubmitResponse` 增加可选字段 `replanning: Optional[DecisionAuditEnvelope] = None`
  - 新增 API: `GET /api/students/{student_id}/path-states`，返回 `{ "student_id": str, "states": Dict[str, PathState] }`

- [ ] **Step 1: 编写 API 闭环集成失败测试 (`tests/test_quiz_replanning_integration.py`)**

```python
# -*- coding: utf-8 -*-
"""
tests/test_quiz_replanning_integration.py
P0-8 全闭环集成测试：
POST /api/quiz/submit 提交作答
-> 权威判题
-> 自动记录 QUESTION_ATTEMPT 学习事件
-> BKT 认知状态流式演进
-> 触发局部动态路径重规划
-> 返回完整 replanning 审计包装与状态响应
"""
import importlib
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

import bkt_state_service
import event_service
import path_state_service
from path_state_service import PathState

_api_module = importlib.import_module("04_api")
app = _api_module.app


class TestQuizReplanningIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.events_file = Path(self.temp_dir.name) / "test_events.jsonl"
        self.bkt_states_file = Path(self.temp_dir.name) / "test_bkt_states.json"
        self.processed_file = Path(self.temp_dir.name) / "test_processed.json"
        self.path_states_file = Path(self.temp_dir.name) / "test_path_states.json"

        self.orig_events = event_service.DEFAULT_EVENTS_FILE
        self.orig_bkt = bkt_state_service.DEFAULT_STATES_FILE
        self.orig_proc = bkt_state_service.DEFAULT_PROCESSED_FILE
        self.orig_path = path_state_service.DEFAULT_PATH_STATES_FILE

        event_service.DEFAULT_EVENTS_FILE = self.events_file
        bkt_state_service.DEFAULT_STATES_FILE = self.bkt_states_file
        bkt_state_service.DEFAULT_PROCESSED_FILE = self.processed_file
        path_state_service.DEFAULT_PATH_STATES_FILE = self.path_states_file

        self.client = TestClient(app)

    def tearDown(self):
        event_service.DEFAULT_EVENTS_FILE = self.orig_events
        bkt_state_service.DEFAULT_STATES_FILE = self.orig_bkt
        bkt_state_service.DEFAULT_PROCESSED_FILE = self.orig_proc
        path_state_service.DEFAULT_PATH_STATES_FILE = self.orig_path
        self.temp_dir.cleanup()

    def test_01_submit_quiz_triggers_replanning_in_response(self):
        """做题提交响应中包含完整的 replanning 决策信封"""
        # 初始化学生状态
        path_state_service.set_path_state(
            "stu_dev_001", "K08", PathState.IN_PROGRESS, states_file=self.path_states_file
        )

        res = self.client.post(
            "/api/quiz/submit",
            json={
                "student_id": "stu_dev_001",
                "question_id": "quiz-k08-01",
                "selected_option": "B",  # 正确答案
                "time_spent_ms": 5000,
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_correct"])
        self.assertIn("replanning", data)
        replanning = data["replanning"]
        self.assertIsNotNone(replanning)

        payload = replanning["canonical_payload"]
        metadata = replanning["audit_metadata"]
        self.assertIn("decision_id", metadata)
        self.assertIn("timestamp", metadata)
        self.assertEqual(payload["knowledge_id"], "K08")
        self.assertEqual(payload["action"], "RETAIN")
        self.assertEqual(payload["reason_code"], "MASTERY_STATE_UNCHANGED")

    def test_02_get_student_path_states_endpoint(self):
        """GET /api/students/{student_id}/path-states 查询路径状态快照"""
        path_state_service.set_path_states_bulk(
            "stu_dev_001",
            {"K08": PathState.COMPLETED, "K09": PathState.AVAILABLE},
            states_file=self.path_states_file,
        )
        res = self.client.get("/api/students/stu_dev_001/path-states")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["student_id"], "stu_dev_001")
        self.assertEqual(data["states"]["K08"], "COMPLETED")
        self.assertEqual(data["states"]["K09"], "AVAILABLE")
```

- [ ] **Step 2: 运行测试验证红灯 (FAIL)**

运行：`pytest tests/test_quiz_replanning_integration.py -v`
预期：FAIL，提示响应中无 `replanning` 字段或 404 未定义端点。

- [ ] **Step 3: 修改 `quiz_service.py` 联动重规划引擎**

在 `quiz_service.py` 中：
1. 导入 `import path_replanning_service` 与 `from path_replanning_service import DecisionAuditEnvelope`
2. 在 `QuizSubmitResponse` 模型中增加 `replanning: Optional[DecisionAuditEnvelope] = None`
3. 在 `submit_quiz_answer` 函数中，当 `bkt_res.status == "updated"` 时调用：
   ```python
   replanning_envelope: Optional[path_replanning_service.DecisionAuditEnvelope] = None
   if bkt_res.status == "updated" and bkt_res.state is not None:
       try:
           prev_mastered = (bkt_res.before_mastery is not None and bkt_res.before_mastery >= 0.80)
           replanning_envelope = path_replanning_service.evaluate_and_replan(
               student_id=req.student_id,
               knowledge_id=question.knowledge_id,
               before_mastery=bkt_res.before_mastery or 0.20,
               after_mastery=bkt_res.after_mastery or bkt_res.state.mastery_probability,
               consecutive_incorrect=bkt_res.state.consecutive_incorrect,
               previously_mastered=prev_mastered,
               is_task_context=True,
               trace_id=stored_event.event_id,
               states_file=None, # 使用默认
               bkt_states_file=states_file,
           )
       except Exception as replan_err:
           # 降级保护：重规划引擎异常不影响基础判题结果
           pass
   ```
4. 在 `QuizSubmitResponse(...)` 返回对象中装配 `replanning=replanning_envelope`。

- [ ] **Step 4: 修改 `04_api.py` 暴露学生路径状态接口**

在 `04_api.py` 中：
```python
import path_state_service


class StudentPathStatesResponse(BaseModel):
    student_id: str
    states: Dict[str, str]


@app.get("/api/students/{student_id}/path-states", response_model=StudentPathStatesResponse)
def get_student_path_states(student_id: str):
    """
    查询指定学生的知识网络路径状态快照
    """
    profiles = load_json(PROFILE_FILE)
    if student_id not in profiles:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}",
        )
    states = path_state_service.get_all_path_states(student_id)
    return StudentPathStatesResponse(
        student_id=student_id,
        states={k: v.value for k, v in states.items()},
    )
```

- [ ] **Step 5: 运行测试验证绿灯 (PASS)**

运行：`pytest tests/test_quiz_replanning_integration.py -v`
预期：2 passed in <0.5s。

- [ ] **Step 6: 提交代码**

```bash
git add quiz_service.py 04_api.py tests/test_quiz_replanning_integration.py
git commit -m "feat(p0-8): integrate path replanning into quiz submit pipeline and expose path-states api"
```

---

### Task 6: 全量回归测试与 BKT 零修改验证 (`tests/`)

**Files:**
- Test: 全量现有测试（`tests/test_bkt_*.py`, `tests/test_quiz_*.py`, `tests/test_event_*.py`）及全部新建测试

**Interfaces:**
- 验证所有既有功能不受任何影响，特别是 BKT 数学公式和状态引擎零污染。

- [ ] **Step 1: 运行全量单元与集成测试**

运行：`pytest tests/ -v`
预期：所有 60 个历史测试 + 18 个 P0-8 新增测试全部 PASS（共计 78 个测试通过）。

- [ ] **Step 2: 验证 BKT 服务代码零修改与纯净性**

运行：`git diff HEAD~5 bkt_service.py`
预期：无输出（`bkt_service.py` 没有任何改动）。

- [ ] **Step 3: 运行 git status 确认工作区整洁**

运行：`git status`
预期：`nothing to commit, working tree clean`。

---

## 最终验证命令清单 (Verification Commands)

1. **P0-8 路径状态服务验证**：
   `pytest tests/test_path_state.py -v`
2. **P0-8 决策契约、定点舍入与规范序列化验证**：
   `pytest tests/test_path_replanning_core.py -v`
3. **P0-8 DAG 探针、1-hop 隔离与全套负向测试验证**：
   `pytest tests/test_path_replanning_dag.py -v`
4. **P0-8 Golden E2E 3步时序闭环与确定性等价验证**：
   `pytest tests/test_path_replanning_golden_e2e.py -v`
5. **P0-8 微测验-事件-BKT-重规划完整 API 闭环验证**：
   `pytest tests/test_quiz_replanning_integration.py -v`
6. **全量系统回归测试**：
   `pytest tests/ -v`
7. **BKT 纯度校验（严禁改动）**：
   `git diff master bkt_service.py`
