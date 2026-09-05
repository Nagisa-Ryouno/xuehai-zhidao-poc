# -*- coding: utf-8 -*-
"""
bkt_event_processor.py
学海智导 (Xuehai Zhidao) V2 学习事件驱动的 BKT 消费处理器

职责：
1. 监听并消费来自 event_service 的 LearningEvent
2. 过滤事件类型（仅 QUESTION_ATTEMPT 驱动 BKT，其余如 HINT/VIEW 安全忽略）
3. 严格执行事件幂等性校验，防止重复计算与计数漂移
4. 调度 bkt_service 数学引擎演进知识状态并经由 bkt_state_service 持久化
5. 提供基于权威服务端时间戳的历史学习事件回放重建机制 (rebuild)
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Literal
from pydantic import BaseModel, Field

import bkt_service
import bkt_state_service
import event_service
from bkt_service import BKTState, BKTParameters, DEFAULT_BKT_PARAMS
from event_service import LearningEvent


class BKTProcessResult(BaseModel):
    """
    单条学习事件消费处理结果
    """
    status: Literal["updated", "already_processed", "ignored", "error"]
    event_id: str
    student_id: Optional[str] = None
    knowledge_id: Optional[str] = None
    before_mastery: Optional[float] = None
    after_mastery: Optional[float] = None
    changed: bool = False
    reason: Optional[str] = None
    state: Optional[BKTState] = None


def find_event_by_id(
    event_id: str,
    events_file: Optional[Path] = None,
) -> Optional[LearningEvent]:
    """
    根据 event_id 在持久化事件日志中检索单条学习行为事件
    """
    target_file = events_file or event_service.DEFAULT_EVENTS_FILE
    if not target_file.exists():
        return None

    with open(target_file, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                if data.get("event_id") == event_id:
                    return LearningEvent(**data)
            except Exception:
                continue
    return None


def process_event(
    event: Union[LearningEvent, Dict[str, Any]],
    states_file: Optional[Path] = None,
    processed_file: Optional[Path] = None,
    params: Optional[BKTParameters] = None,
) -> BKTProcessResult:
    """
    核心事件消费者：
    1. 校验 event 基本格式与 event_id
    2. 幂等检查：若 event_id 已处理过，返回 already_processed
    3. 类型检查：若非 QUESTION_ATTEMPT，返回 ignored（暂不影响 BKT）
    4. 载荷检查：必须包含合法的 is_correct 布尔值
    5. 读取当前 BKTState，调用数学公式更新
    6. 保存状态并记录已处理事件索引
    """
    cfg = params or DEFAULT_BKT_PARAMS

    if isinstance(event, dict):
        event_id = event.get("event_id")
        student_id = event.get("student_id")
        knowledge_id = event.get("knowledge_id")
        event_type = event.get("event_type")
        payload = event.get("payload", {})
        server_ts = event.get("server_timestamp") or event.get("client_timestamp") or ""
    else:
        event_id = event.event_id
        student_id = event.student_id
        knowledge_id = event.knowledge_id
        event_type = event.event_type
        payload = event.payload
        server_ts = event.server_timestamp or event.client_timestamp

    if not event_id:
        return BKTProcessResult(
            status="error",
            event_id="",
            changed=False,
            reason="事件缺失唯一标识 event_id",
        )

    # 1. 幂等性校验：同一个 event_id 不得重复改变 BKT 状态
    if bkt_state_service.is_event_processed(event_id, processed_file=processed_file):
        # 尝试读取当前状态返回，以便调用方感知
        current_state = None
        if student_id and knowledge_id:
            try:
                current_state = bkt_state_service.get_state(
                    student_id, knowledge_id, states_file=states_file
                )
            except Exception:
                pass
        return BKTProcessResult(
            status="already_processed",
            event_id=event_id,
            student_id=student_id,
            knowledge_id=knowledge_id,
            changed=False,
            state=current_state,
            reason=f"事件 {event_id} 之前已完成消费，拒绝重复计算",
        )

    # 2. 事件类型过滤：当前阶段仅 QUESTION_ATTEMPT 驱动认知状态演进
    if event_type != "QUESTION_ATTEMPT":
        # 标记为已消费，防止重复查询
        bkt_state_service.mark_event_processed(
            event_id,
            event_info={
                "student_id": student_id,
                "knowledge_id": knowledge_id,
                "event_type": event_type,
            },
            processed_file=processed_file,
        )
        return BKTProcessResult(
            status="ignored",
            event_id=event_id,
            student_id=student_id,
            knowledge_id=knowledge_id,
            changed=False,
            reason=f"事件类型 {event_type} 不参与 BKT 掌握度数学更新",
        )

    # 3. 校验有效载荷中的 is_correct 判题结果
    if not isinstance(payload, dict) or "is_correct" not in payload:
        return BKTProcessResult(
            status="error",
            event_id=event_id,
            student_id=student_id,
            knowledge_id=knowledge_id,
            changed=False,
            reason="QUESTION_ATTEMPT 事件载荷中缺少 'is_correct' 判题结果",
        )

    is_correct = payload["is_correct"]
    if not isinstance(is_correct, bool):
        return BKTProcessResult(
            status="error",
            event_id=event_id,
            student_id=student_id,
            knowledge_id=knowledge_id,
            changed=False,
            reason="'is_correct' 字段必须为布尔值 (True/False)",
        )

    if not student_id or not knowledge_id:
        return BKTProcessResult(
            status="error",
            event_id=event_id,
            student_id=student_id,
            knowledge_id=knowledge_id,
            changed=False,
            reason="缺少学生编号或知识点编号",
        )

    # 4. 加载当前状态
    current_state = bkt_state_service.get_state(
        student_id,
        knowledge_id,
        states_file=states_file,
        auto_init=True,
    )

    # 5. 调用纯数学模型更新
    update_res = bkt_service.apply_attempt(
        current_state,
        is_correct=is_correct,
        event_id=event_id,
        timestamp=server_ts,
        params=cfg,
    )

    # 6. 原子持久化新状态并登记已处理索引
    bkt_state_service.save_state(update_res.state, states_file=states_file)
    bkt_state_service.mark_event_processed(
        event_id,
        event_info={
            "student_id": student_id,
            "knowledge_id": knowledge_id,
            "event_type": event_type,
            "is_correct": is_correct,
            "before_mastery": update_res.before_mastery,
            "after_mastery": update_res.after_mastery,
        },
        processed_file=processed_file,
    )

    return BKTProcessResult(
        status="updated",
        event_id=event_id,
        student_id=student_id,
        knowledge_id=knowledge_id,
        before_mastery=update_res.before_mastery,
        after_mastery=update_res.after_mastery,
        changed=True,
        state=update_res.state,
    )


def rebuild_student_knowledge_state(
    student_id: str,
    knowledge_id: str,
    events: List[Union[LearningEvent, Dict[str, Any]]],
    params: Optional[BKTParameters] = None,
) -> BKTState:
    """
    纯函数式历史事件全量回放与状态重建：
    1. 过滤匹配 student_id 与 knowledge_id 的 QUESTION_ATTEMPT 事件
    2. 按 event_id 去重（确保输入数据内部幂等）
    3. 严格按照 server_timestamp 升序（时间相同时按 event_id）排序
    4. 从 P(L0) 初始状态开始，依次按序应用 BKT 更新公式
    5. 返回最终计算得出的 BKTState
    """
    cfg = params or DEFAULT_BKT_PARAMS

    # 1. 过滤匹配目标学生与知识点的答题事件
    valid_events = []
    seen_ids = set()

    for e in events:
        if isinstance(e, dict):
            eid = e.get("event_id")
            sid = e.get("student_id")
            kid = e.get("knowledge_id")
            etype = e.get("event_type")
            sts = e.get("server_timestamp") or e.get("client_timestamp") or ""
            payload = e.get("payload", {})
        else:
            eid = e.event_id
            sid = e.student_id
            kid = e.knowledge_id
            etype = e.event_type
            sts = e.server_timestamp or e.client_timestamp
            payload = e.payload

        if sid == student_id and kid == knowledge_id and etype == "QUESTION_ATTEMPT":
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                is_corr = payload.get("is_correct")
                if isinstance(is_corr, bool):
                    valid_events.append((sts, eid, is_corr))

    # 2. 严格按 server_timestamp 排序，时间相同则按 eid 稳定 tie-break
    valid_events.sort(key=lambda item: (item[0], item[1]))

    # 3. 顺序回放演进
    current_state = bkt_service.create_initial_state(student_id, knowledge_id, cfg)
    for sts, eid, is_corr in valid_events:
        res = bkt_service.apply_attempt(
            current_state,
            is_correct=is_corr,
            event_id=eid,
            timestamp=sts,
            params=cfg,
        )
        current_state = res.state

    return current_state
