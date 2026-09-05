# -*- coding: utf-8 -*-
"""
bkt_event_processor.py
学海智导 (Xuehai Zhidao) V2 学习事件驱动的 BKT 消费处理器应用服务 (BKT Event Processor)

职责：
1. 监听并消费来自 EventRepository 的 LearningEvent
2. 过滤事件类型（仅 QUESTION_ATTEMPT 驱动 BKT，其余如 HINT/VIEW 安全忽略）
3. 严格执行事件幂等性校验，防止重复计算与计数漂移
4. 调度 BKT 领域数学引擎演进知识状态并经由 BKTStateRepository 持久化
5. 提供基于权威服务端时间戳的历史学习事件回放重建机制 (rebuild)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

import bkt_state_service
import event_service
from app.core.config import settings
from app.domain.bkt import (
    BKTParameters,
    BKTState,
    DEFAULT_BKT_PARAMS,
    apply_attempt,
    create_initial_state,
)
from app.infrastructure.persistence.bkt_state_repository import (
    BKTStateRepository,
    default_bkt_state_repository,
)
from app.infrastructure.persistence.event_repository import (
    EventRepository,
    LearningEvent,
    default_event_repository,
)


class BKTProcessResult(BaseModel):
    """单条学习事件消费处理结果"""
    status: Literal["updated", "already_processed", "ignored", "error"]
    event_id: str
    student_id: Optional[str] = None
    knowledge_id: Optional[str] = None
    before_mastery: Optional[float] = None
    after_mastery: Optional[float] = None
    changed: bool = False
    reason: Optional[str] = None
    state: Optional[BKTState] = None


class BKTEventProcessor:
    """BKT 事件消费与历史重建应用服务"""

    def __init__(
        self,
        bkt_repo: Optional[BKTStateRepository] = None,
        event_repo: Optional[EventRepository] = None,
    ):
        self.bkt_repo = bkt_repo or default_bkt_state_repository
        self.event_repo = event_repo or default_event_repository

    def find_event_by_id(
        self,
        event_id: str,
        events_file: Optional[Path] = None,
    ) -> Optional[LearningEvent]:
        """根据 event_id 在持久化事件日志中检索单条学习行为事件"""
        target_file = events_file or getattr(event_service, "DEFAULT_EVENTS_FILE", settings.LEARNING_EVENTS_FILE)
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
        self,
        event: Union[LearningEvent, Dict[str, Any]],
        states_file: Optional[Path] = None,
        processed_file: Optional[Path] = None,
        params: Optional[BKTParameters] = None,
    ) -> BKTProcessResult:
        """核心事件消费者"""
        cfg = params or DEFAULT_BKT_PARAMS

        target_states = states_file or getattr(bkt_state_service, "DEFAULT_STATES_FILE", settings.BKT_STATES_FILE)
        target_processed = processed_file or getattr(bkt_state_service, "DEFAULT_PROCESSED_FILE", settings.BKT_PROCESSED_EVENTS_FILE)

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

        # 1. 幂等性校验
        if self.bkt_repo.is_event_processed(event_id, processed_file=target_processed):
            current_state = None
            if student_id and knowledge_id:
                try:
                    current_state = self.bkt_repo.get_state(
                        student_id, knowledge_id, states_file=target_states
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

        # 2. 事件类型过滤
        if event_type != "QUESTION_ATTEMPT":
            self.bkt_repo.mark_event_processed(
                event_id,
                event_info={
                    "student_id": student_id,
                    "knowledge_id": knowledge_id,
                    "event_type": event_type,
                },
                processed_file=target_processed,
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
        current_state = self.bkt_repo.get_state(
            student_id,
            knowledge_id,
            states_file=target_states,
            auto_init=True,
        )

        # 5. 调用纯数学模型更新
        update_res = apply_attempt(
            current_state,
            is_correct=is_correct,
            event_id=event_id,
            timestamp=server_ts,
            params=cfg,
        )

        # 6. 原子持久化新状态并登记已处理索引
        self.bkt_repo.save_state(update_res.state, states_file=target_states)
        self.bkt_repo.mark_event_processed(
            event_id,
            event_info={
                "student_id": student_id,
                "knowledge_id": knowledge_id,
                "event_type": event_type,
                "is_correct": is_correct,
                "before_mastery": update_res.before_mastery,
                "after_mastery": update_res.after_mastery,
            },
            processed_file=target_processed,
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
        self,
        student_id: str,
        knowledge_id: str,
        events: List[Union[LearningEvent, Dict[str, Any]]],
        params: Optional[BKTParameters] = None,
    ) -> BKTState:
        """纯函数式历史事件全量回放与状态重建"""
        cfg = params or DEFAULT_BKT_PARAMS

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

        valid_events.sort(key=lambda item: (item[0], item[1]))

        current_state = create_initial_state(student_id, knowledge_id, cfg)
        for sts, eid, is_corr in valid_events:
            res = apply_attempt(
                current_state,
                is_correct=is_corr,
                event_id=eid,
                timestamp=sts,
                params=cfg,
            )
            current_state = res.state

        return current_state


# 全局默认单例
bkt_event_processor = BKTEventProcessor()

# 模块级兼容函数
find_event_by_id = bkt_event_processor.find_event_by_id
process_event = bkt_event_processor.process_event
rebuild_student_knowledge_state = bkt_event_processor.rebuild_student_knowledge_state

__all__ = [
    "BKTProcessResult",
    "BKTEventProcessor",
    "bkt_event_processor",
    "find_event_by_id",
    "process_event",
    "rebuild_student_knowledge_state",
]
