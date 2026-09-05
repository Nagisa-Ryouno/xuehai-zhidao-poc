# -*- coding: utf-8 -*-
"""
bkt_state_repository.py
学海智导 (Xuehai Zhidao) V2 BKT 认知状态与已处理事件索引仓储层 (BKT State Repository)

职责：
1. 管理 student_id x knowledge_id 维度的 BKT 状态落盘 (settings.BKT_STATES_FILE)
2. 维护已处理事件索引 (settings.BKT_PROCESSED_EVENTS_FILE) 实现消费幂等性
3. 线程安全（threading.RLock）与文件原子性写入（同目录临时文件写入后 replace）
4. 支持测试路径注入，严防测试执行污染生产环境
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from app.core.config import settings
from app.domain.bkt import BKTState, create_initial_state


# ============================================================
# 底层文件原子读写帮助函数
# ============================================================

def _atomic_write_json(file_path: Union[Path, str], data: Any) -> None:
    """原子性持久化 JSON 数据（写入同目录临时文件后重命名替换）"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _read_json_file(file_path: Union[Path, str]) -> Dict[str, Any]:
    """读取 JSON 文件字典，文件不存在时返回空字典"""
    path = Path(file_path)
    if not path.exists():
        return {}
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return {}
        return json.loads(content)
    except Exception:
        return {}


# ============================================================
# BKT 状态仓储实现
# ============================================================

class BKTStateRepository:
    """BKT 认知状态与已处理事件索引持久化仓储"""

    def __init__(
        self,
        states_file: Optional[Union[Path, str]] = None,
        processed_file: Optional[Union[Path, str]] = None,
    ):
        self.states_file: Path = Path(states_file) if states_file else settings.BKT_STATES_FILE
        self.processed_file: Path = Path(processed_file) if processed_file else settings.BKT_PROCESSED_EVENTS_FILE
        self._lock = threading.RLock()

    def get_state(
        self,
        student_id: str,
        knowledge_id: str,
        states_file: Optional[Union[Path, str]] = None,
        auto_init: bool = True,
    ) -> BKTState:
        """
        获取指定学生指定知识点的当前 BKT 认知状态
        若记录不存在且 auto_init=True，则返回以 P(L0) 初始化的默认状态
        """
        target_file = Path(states_file) if states_file is not None else self.states_file
        key = f"{student_id}:{knowledge_id}"

        with self._lock:
            all_states = _read_json_file(target_file)
            if key in all_states:
                return BKTState(**all_states[key])

        if auto_init:
            return create_initial_state(student_id, knowledge_id)

        raise KeyError(f"未找到状态记录: {key}")

    def save_state(
        self,
        state: BKTState,
        states_file: Optional[Union[Path, str]] = None,
    ) -> None:
        """
        原子持久化单个知识点 BKTState
        """
        target_file = Path(states_file) if states_file is not None else self.states_file
        key = f"{state.student_id}:{state.knowledge_id}"

        with self._lock:
            all_states = _read_json_file(target_file)
            all_states[key] = state.model_dump()
            _atomic_write_json(target_file, all_states)

    def get_student_states(
        self,
        student_id: str,
        states_file: Optional[Union[Path, str]] = None,
    ) -> List[BKTState]:
        """
        查询指定学生名下的全部知识点状态记录列表
        """
        target_file = Path(states_file) if states_file is not None else self.states_file
        prefix = f"{student_id}:"
        result: List[BKTState] = []

        with self._lock:
            all_states = _read_json_file(target_file)
            for key, val in all_states.items():
                if key.startswith(prefix):
                    result.append(BKTState(**val))

        return result

    def is_event_processed(
        self,
        event_id: str,
        processed_file: Optional[Union[Path, str]] = None,
    ) -> bool:
        """
        判断指定的 event_id 是否已被 BKT 引擎消费过
        """
        target_file = Path(processed_file) if processed_file is not None else self.processed_file
        with self._lock:
            events = _read_json_file(target_file)
            return event_id in events

    def mark_event_processed(
        self,
        event_id: str,
        event_info: Optional[Dict[str, Any]] = None,
        processed_file: Optional[Union[Path, str]] = None,
    ) -> None:
        """
        记录已处理事件元数据，供后续幂等拦截
        """
        target_file = Path(processed_file) if processed_file is not None else self.processed_file
        now_ts = datetime.now(timezone.utc).astimezone().isoformat()

        with self._lock:
            events = _read_json_file(target_file)
            info = event_info.copy() if event_info else {}
            info.setdefault("processed_at", now_ts)
            events[event_id] = info
            _atomic_write_json(target_file, events)


# ============================================================
# 全局默认单例与导出
# ============================================================

default_bkt_state_repository = BKTStateRepository()

__all__ = [
    "_atomic_write_json",
    "_read_json_file",
    "BKTStateRepository",
    "default_bkt_state_repository",
]
