# -*- coding: utf-8 -*-
"""
bkt_state_service.py
学海智导 (Xuehai Zhidao) V2 BKT 认知状态持久化与并发管理服务层

职责：
1. 管理 student_id x knowledge_id 维度的 BKT 状态落盘 (data/bkt_states.json)
2. 维护已处理事件索引 (data/bkt_processed_events.json) 实现消费幂等性
3. 线程安全（threading.Lock）与文件原子性写入（tempfile 替换）
4. 支持测试路径注入，严防测试执行污染生产环境
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import bkt_service
from bkt_service import BKTState

# ============================================================
# 默认存储路径与锁
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / "data"
DEFAULT_STATES_FILE = DEFAULT_DATA_DIR / "bkt_states.json"
DEFAULT_PROCESSED_FILE = DEFAULT_DATA_DIR / "bkt_processed_events.json"

_state_lock = threading.Lock()


# ============================================================
# 底层文件原子读写帮助函数
# ============================================================

def _atomic_write_json(file_path: Path, data: Any) -> None:
    """原子性持久化 JSON 数据（写入同目录临时文件后重命名替换）"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = file_path.with_name(f"{file_path.name}.{os.getpid()}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(file_path)


def _read_json_file(file_path: Path) -> Dict[str, Any]:
    """读取 JSON 文件字典，文件不存在时返回空字典"""
    if not file_path.exists():
        return {}
    try:
        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            return {}
        return json.loads(content)
    except Exception:
        return {}


# ============================================================
# 状态查询与持久化核心接口
# ============================================================

def get_state(
    student_id: str,
    knowledge_id: str,
    states_file: Optional[Path] = None,
    auto_init: bool = True,
) -> BKTState:
    """
    获取指定学生指定知识点的当前 BKT 认知状态
    若记录不存在且 auto_init=True，则返回以 P(L0) 初始化的默认状态
    """
    target_file = states_file or DEFAULT_STATES_FILE
    key = f"{student_id}:{knowledge_id}"

    with _state_lock:
        all_states = _read_json_file(target_file)
        if key in all_states:
            return BKTState(**all_states[key])

    if auto_init:
        return bkt_service.create_initial_state(student_id, knowledge_id)

    raise KeyError(f"未找到状态记录: {key}")


def save_state(
    state: BKTState,
    states_file: Optional[Path] = None,
) -> None:
    """
    原子持久化单个知识点 BKTState
    """
    target_file = states_file or DEFAULT_STATES_FILE
    key = f"{state.student_id}:{state.knowledge_id}"

    with _state_lock:
        all_states = _read_json_file(target_file)
        all_states[key] = state.model_dump()
        _atomic_write_json(target_file, all_states)


def get_student_states(
    student_id: str,
    states_file: Optional[Path] = None,
) -> List[BKTState]:
    """
    查询指定学生名下的全部知识点状态记录列表
    """
    target_file = states_file or DEFAULT_STATES_FILE
    prefix = f"{student_id}:"
    result: List[BKTState] = []

    with _state_lock:
        all_states = _read_json_file(target_file)
        for key, val in all_states.items():
            if key.startswith(prefix):
                result.append(BKTState(**val))

    return result


# ============================================================
# 幂等处理事件追踪接口
# ============================================================

def is_event_processed(
    event_id: str,
    processed_file: Optional[Path] = None,
) -> bool:
    """
    判断指定的 event_id 是否已被 BKT 引擎消费过
    """
    target_file = processed_file or DEFAULT_PROCESSED_FILE
    with _state_lock:
        events = _read_json_file(target_file)
        return event_id in events


def mark_event_processed(
    event_id: str,
    event_info: Optional[Dict[str, Any]] = None,
    processed_file: Optional[Path] = None,
) -> None:
    """
    记录已处理事件元数据，供后续幂等拦截
    """
    target_file = processed_file or DEFAULT_PROCESSED_FILE
    now_ts = datetime.now(timezone.utc).astimezone().isoformat()

    with _state_lock:
        events = _read_json_file(target_file)
        info = event_info.copy() if event_info else {}
        info.setdefault("processed_at", now_ts)
        events[event_id] = info
        _atomic_write_json(target_file, events)
