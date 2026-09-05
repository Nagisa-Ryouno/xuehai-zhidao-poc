# -*- coding: utf-8 -*-
"""
path_state_service.py
学海智导 V2 路径执行状态管理服务
负责维护与独立持久化学生在知识网络中的任务执行状态 (PathState)。
与 BKT 认知状态数据文件严格物理解耦，独立存储于 data/learning_path_states.json。
"""
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Union
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_PATH_STATES_FILE = DATA_DIR / "learning_path_states.json"

_path_state_lock = threading.RLock()


class PathState(str, Enum):
    """
    节点在个性化任务流中的执行状态
    """
    LOCKED = "LOCKED"          # 未满足直接前置要求，锁定不可学
    AVAILABLE = "AVAILABLE"    # 所有直接前置均已掌握，已解锁待学习
    IN_PROGRESS = "IN_PROGRESS"# 当前正在学习/聚焦执行的任务节点
    COMPLETED = "COMPLETED"    # 在任务执行上下文中已成功达到掌握标准


class StudentPathStates(BaseModel):
    """学生路径状态概览模型"""
    student_id: str
    states: Dict[str, PathState] = Field(default_factory=dict)
    last_updated: Optional[str] = None


# 别名兼容
StudentPathProfile = StudentPathStates


def _resolve_file_path(states_file: Optional[Union[Path, str]]) -> Path:
    if states_file is None:
        return DEFAULT_PATH_STATES_FILE
    return Path(states_file)


def _load_all_states(states_file: Optional[Union[Path, str]] = None) -> Dict[str, Dict[str, str]]:
    target_file = _resolve_file_path(states_file)
    if not target_file.exists():
        return {}
    with _path_state_lock:
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                data = json.loads(content)
                if isinstance(data, dict):
                    return data
                return {}
        except Exception:
            return {}


def _save_all_states(data: Dict[str, Dict[str, str]], states_file: Optional[Union[Path, str]] = None) -> None:
    target_file = _resolve_file_path(states_file)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    with _path_state_lock:
        # 原子写入：写入同目录临时文件并关闭，然后 os.replace 替换，避免跨平台锁或崩溃损坏
        tf = tempfile.NamedTemporaryFile("w", dir=str(target_file.parent), delete=False, encoding="utf-8")
        temp_name = tf.name
        try:
            json.dump(data, tf, ensure_ascii=False, indent=2)
            tf.flush()
            tf.close()
            os.replace(temp_name, str(target_file))
        except Exception:
            if os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except Exception:
                    pass
            raise


def get_path_state(
    student_id: str,
    knowledge_id: str,
    states_file: Optional[Union[Path, str]] = None,
    default: PathState = PathState.LOCKED,
) -> PathState:
    """
    获取指定学生指定知识点的当前路径执行状态。未记录时返回 default (默认 LOCKED)。
    """
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
    state: Union[PathState, str],
    states_file: Optional[Union[Path, str]] = None,
) -> None:
    """
    设置并持久化指定学生的单知识点路径状态
    """
    set_path_states_bulk(student_id, {knowledge_id: state}, states_file=states_file)


def set_path_states_bulk(
    student_id: str,
    state_updates: Dict[str, Union[PathState, str]],
    states_file: Optional[Union[Path, str]] = None,
) -> None:
    """
    批量原子更新并持久化指定学生的多个知识点路径状态
    """
    with _path_state_lock:
        data = _load_all_states(states_file)
        if student_id not in data:
            data[student_id] = {}
        for k_id, st in state_updates.items():
            val = st.value if isinstance(st, PathState) else str(st)
            data[student_id][k_id] = val
        _save_all_states(data, states_file=states_file)


def get_all_path_states(
    student_id: str,
    states_file: Optional[Union[Path, str]] = None,
) -> Dict[str, PathState]:
    """
    获取指定学生的全部知识点路径状态字典
    """
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
    initial_states: Optional[Dict[str, Union[PathState, str]]] = None,
    states_file: Optional[Union[Path, str]] = None,
) -> None:
    """
    初始化学生路径状态，可接收初始状态字典
    """
    with _path_state_lock:
        data = _load_all_states(states_file)
        if student_id not in data:
            data[student_id] = {}
        if initial_states:
            for k_id, st in initial_states.items():
                val = st.value if isinstance(st, PathState) else str(st)
                data[student_id][k_id] = val
        _save_all_states(data, states_file=states_file)


def get_student_path_profile(
    student_id: str,
    states_file: Optional[Union[Path, str]] = None,
) -> StudentPathStates:
    """
    获取指定学生的路径状态概览模型
    """
    states = get_all_path_states(student_id, states_file=states_file)
    now_ts = datetime.now(timezone.utc).isoformat()
    return StudentPathStates(student_id=student_id, states=states, last_updated=now_ts)
