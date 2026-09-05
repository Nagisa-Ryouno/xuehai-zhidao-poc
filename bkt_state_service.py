# -*- coding: utf-8 -*-
"""
bkt_state_service.py
学海智导 (Xuehai Zhidao) V2 BKT 认知状态持久化与并发管理服务层（向后兼容门面）

本模块委托给 app.infrastructure.persistence.bkt_state_repository.BKTStateRepository 实现。
保留原有 API 签名及 DEFAULT_STATES_FILE, DEFAULT_PROCESSED_FILE 配置以供向后兼容及单元测试。
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import bkt_service
from app.core.config import settings
from app.domain.bkt import BKTState, create_initial_state
from app.infrastructure.persistence.bkt_state_repository import (
    BKTStateRepository,
    default_bkt_state_repository,
    _atomic_write_json,
    _read_json_file,
)

# ============================================================
# 默认存储路径与锁配置（向后兼容，支持 tests 动态覆写）
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR: Path = settings.DATA_DIR
DEFAULT_STATES_FILE: Path = settings.BKT_STATES_FILE
DEFAULT_PROCESSED_FILE: Path = settings.BKT_PROCESSED_EVENTS_FILE

_state_lock = default_bkt_state_repository._lock


# ============================================================
# 核心业务函数（向后兼容门面，委托给 default_bkt_state_repository）
# ============================================================

def get_state(
    student_id: str,
    knowledge_id: str,
    states_file: Optional[Union[Path, str]] = None,
    auto_init: bool = True,
) -> BKTState:
    """
    获取指定学生指定知识点的当前 BKT 认知状态
    若记录不存在且 auto_init=True，则返回以 P(L0) 初始化的默认状态
    """
    target_file = states_file if states_file is not None else DEFAULT_STATES_FILE
    return default_bkt_state_repository.get_state(
        student_id=student_id,
        knowledge_id=knowledge_id,
        states_file=target_file,
        auto_init=auto_init,
    )


def save_state(
    state: BKTState,
    states_file: Optional[Union[Path, str]] = None,
) -> None:
    """
    原子持久化单个知识点 BKTState
    """
    target_file = states_file if states_file is not None else DEFAULT_STATES_FILE
    default_bkt_state_repository.save_state(state, states_file=target_file)


def get_student_states(
    student_id: str,
    states_file: Optional[Union[Path, str]] = None,
) -> List[BKTState]:
    """
    查询指定学生名下的全部知识点状态记录列表
    """
    target_file = states_file if states_file is not None else DEFAULT_STATES_FILE
    return default_bkt_state_repository.get_student_states(student_id, states_file=target_file)


def is_event_processed(
    event_id: str,
    processed_file: Optional[Union[Path, str]] = None,
) -> bool:
    """
    判断指定的 event_id 是否已被 BKT 引擎消费过
    """
    target_file = processed_file if processed_file is not None else DEFAULT_PROCESSED_FILE
    return default_bkt_state_repository.is_event_processed(event_id, processed_file=target_file)


def mark_event_processed(
    event_id: str,
    event_info: Optional[Dict[str, Any]] = None,
    processed_file: Optional[Union[Path, str]] = None,
) -> None:
    """
    记录已处理事件元数据，供后续幂等拦截
    """
    target_file = processed_file if processed_file is not None else DEFAULT_PROCESSED_FILE
    default_bkt_state_repository.mark_event_processed(
        event_id=event_id,
        event_info=event_info,
        processed_file=target_file,
    )


__all__ = [
    "BASE_DIR",
    "DEFAULT_DATA_DIR",
    "DEFAULT_STATES_FILE",
    "DEFAULT_PROCESSED_FILE",
    "_state_lock",
    "_atomic_write_json",
    "_read_json_file",
    "BKTState",
    "bkt_service",
    "BKTStateRepository",
    "default_bkt_state_repository",
    "get_state",
    "save_state",
    "get_student_states",
    "is_event_processed",
    "mark_event_processed",
]
