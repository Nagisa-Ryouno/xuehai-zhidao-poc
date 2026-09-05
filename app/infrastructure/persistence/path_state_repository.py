# -*- coding: utf-8 -*-
"""
path_state_repository.py
学海智导 (Xuehai Zhidao) V2 路径执行状态仓储层 (Path State Repository)

职责：
1. 维护与独立持久化学生在知识网络中的任务执行状态 (PathState)
2. 与 BKT 认知状态数据文件严格物理解耦 (settings.LEARNING_PATH_STATES_FILE)
3. 线程安全 (threading.RLock) 与跨平台原子写入 (tempfile + os.replace)
4. 支持测试路径依赖注入，严防测试执行污染生产环境
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Dict, Optional, Union

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.constants import PathState


class StudentPathStates(BaseModel):
    """学生路径状态概览模型"""
    student_id: str
    states: Dict[str, PathState] = Field(default_factory=dict)
    last_updated: Optional[str] = None


# 别名兼容
StudentPathProfile = StudentPathStates


class PathStateRepository:
    """路径执行状态持久化仓储"""

    def __init__(self, states_file: Optional[Union[Path, str]] = None):
        self.states_file: Path = (
            Path(states_file) if states_file is not None else settings.LEARNING_PATH_STATES_FILE
        )
        self._lock = threading.RLock()

    def _resolve_file_path(self, states_file: Optional[Union[Path, str]] = None) -> Path:
        if states_file is None:
            return self.states_file
        return Path(states_file)

    def _load_all_states(
        self, states_file: Optional[Union[Path, str]] = None
    ) -> Dict[str, Dict[str, str]]:
        target_file = self._resolve_file_path(states_file)
        if not target_file.exists():
            return {}
        with self._lock:
            try:
                content = target_file.read_text(encoding="utf-8").strip()
                if not content:
                    return {}
                data = json.loads(content)
                if isinstance(data, dict):
                    return data
                return {}
            except Exception:
                return {}

    def _save_all_states(
        self, data: Dict[str, Dict[str, str]], states_file: Optional[Union[Path, str]] = None
    ) -> None:
        target_file = self._resolve_file_path(states_file)
        target_file.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            # 原子写入：写入同目录临时文件并关闭，然后 os.replace 替换，避免跨平台锁或崩溃损坏
            tf = tempfile.NamedTemporaryFile(
                "w", dir=str(target_file.parent), delete=False, encoding="utf-8"
            )
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
        self,
        student_id: str,
        knowledge_id: str,
        states_file: Optional[Union[Path, str]] = None,
        default: PathState = PathState.LOCKED,
    ) -> PathState:
        """
        获取指定学生指定知识点的当前路径执行状态。未记录时返回 default (默认 LOCKED)。
        """
        data = self._load_all_states(states_file)
        stu_dict = data.get(student_id, {})
        val = stu_dict.get(knowledge_id)
        if val:
            try:
                return PathState(val)
            except ValueError:
                return default
        return default

    def set_path_state(
        self,
        student_id: str,
        knowledge_id: str,
        state: Union[PathState, str],
        states_file: Optional[Union[Path, str]] = None,
    ) -> None:
        """
        设置并持久化指定学生的单知识点路径状态
        """
        self.set_path_states_bulk(student_id, {knowledge_id: state}, states_file=states_file)

    def set_path_states_bulk(
        self,
        student_id: str,
        state_updates: Dict[str, Union[PathState, str]],
        states_file: Optional[Union[Path, str]] = None,
    ) -> None:
        """
        批量原子更新并持久化指定学生的多个知识点路径状态
        """
        with self._lock:
            data = self._load_all_states(states_file)
            if student_id not in data:
                data[student_id] = {}
            for k_id, st in state_updates.items():
                val = st.value if isinstance(st, PathState) else str(st)
                data[student_id][k_id] = val
            self._save_all_states(data, states_file=states_file)

    def get_all_path_states(
        self,
        student_id: str,
        states_file: Optional[Union[Path, str]] = None,
    ) -> Dict[str, PathState]:
        """
        获取指定学生的全部知识点路径状态字典
        """
        data = self._load_all_states(states_file)
        stu_dict = data.get(student_id, {})
        res: Dict[str, PathState] = {}
        for k_id, val in stu_dict.items():
            try:
                res[k_id] = PathState(val)
            except ValueError:
                res[k_id] = PathState.LOCKED
        return res

    def init_student_path(
        self,
        student_id: str,
        initial_states: Optional[Dict[str, Union[PathState, str]]] = None,
        states_file: Optional[Union[Path, str]] = None,
    ) -> None:
        """
        初始化学生路径状态，可接收初始状态字典
        """
        with self._lock:
            data = self._load_all_states(states_file)
            if student_id not in data:
                data[student_id] = {}
            if initial_states:
                for k_id, st in initial_states.items():
                    val = st.value if isinstance(st, PathState) else str(st)
                    data[student_id][k_id] = val
            self._save_all_states(data, states_file=states_file)

    def get_student_path_profile(
        self,
        student_id: str,
        states_file: Optional[Union[Path, str]] = None,
    ) -> StudentPathStates:
        """
        获取指定学生的路径状态概览模型
        """
        states = self.get_all_path_states(student_id, states_file=states_file)
        now_ts = datetime.now(timezone.utc).isoformat()
        return StudentPathStates(student_id=student_id, states=states, last_updated=now_ts)


# 全局默认单例
default_path_state_repository = PathStateRepository()

__all__ = [
    "PathState",
    "StudentPathStates",
    "StudentPathProfile",
    "PathStateRepository",
    "default_path_state_repository",
]
