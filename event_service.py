# -*- coding: utf-8 -*-
"""
event_service.py
学海智导 (Xuehai Zhidao) V2 统一学习行为日志服务层（向后兼容门面）

本模块委托给 app.infrastructure.persistence.event_repository.EventRepository 实现。
保留原有 API 签名及 DEFAULT_EVENTS_FILE 配置以供向后兼容及单元测试。
"""

from pathlib import Path
from typing import List, Optional, Union

from app.core.config import settings
from app.infrastructure.persistence.event_repository import (
    LearningEventType,
    LearningEventCreate,
    LearningEvent,
    StoredEvent,
    EventSubmissionResponse,
    EventRepository,
    default_event_repository,
)

# ============================================================
# 存储路径与锁配置（向后兼容，支持 tests 动态覆写 DEFAULT_EVENTS_FILE）
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR: Path = settings.DATA_DIR
DEFAULT_EVENTS_FILE: Path = settings.LEARNING_EVENTS_FILE

_file_lock = default_event_repository._lock


# ============================================================
# 核心业务函数（向后兼容门面，委托给 default_event_repository）
# ============================================================

def record_event(
    event_in: LearningEventCreate,
    target_file: Optional[Union[str, Path]] = None,
) -> LearningEvent:
    """
    持久化一条学习行为事件至 JSONL 文件。
    确保服务端权威时间戳、线程安全写入，自动创建目录。
    """
    file_path = target_file or DEFAULT_EVENTS_FILE
    return default_event_repository.record_event(event_in, target_file=file_path)


def get_student_events(
    student_id: str,
    target_file: Optional[Union[str, Path]] = None,
) -> List[LearningEvent]:
    """
    查询指定学生全部历史学习事件（按写入顺序返回）
    供后续教师干预工作台及历史分析使用
    """
    file_path = target_file or DEFAULT_EVENTS_FILE
    return default_event_repository.get_events_by_student(student_id, target_file=file_path)


get_events_by_student = get_student_events


__all__ = [
    "BASE_DIR",
    "DEFAULT_DATA_DIR",
    "DEFAULT_EVENTS_FILE",
    "LearningEventType",
    "LearningEventCreate",
    "LearningEvent",
    "StoredEvent",
    "EventSubmissionResponse",
    "EventRepository",
    "default_event_repository",
    "record_event",
    "get_student_events",
    "get_events_by_student",
]
