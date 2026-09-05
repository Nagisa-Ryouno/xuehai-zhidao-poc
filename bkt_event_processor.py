# -*- coding: utf-8 -*-
"""
bkt_event_processor.py
学海智导 (Xuehai Zhidao) V2 学习事件驱动的 BKT 消费处理器 (Backward-compatible Facade)

向后兼容门面，内部委托给 app.services.bkt_event_processor。
"""

from app.services.bkt_event_processor import (
    BKTEventProcessor,
    BKTProcessResult,
    bkt_event_processor,
    find_event_by_id,
    process_event,
    rebuild_student_knowledge_state,
)

__all__ = [
    "BKTProcessResult",
    "BKTEventProcessor",
    "bkt_event_processor",
    "find_event_by_id",
    "process_event",
    "rebuild_student_knowledge_state",
]
