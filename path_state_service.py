# -*- coding: utf-8 -*-
"""
path_state_service.py
学海智导 V2 路径执行状态管理服务 (Backward-compatible Facade)

向后兼容门面，内部委托给 app.infrastructure.persistence.path_state_repository.default_path_state_repository。
"""
from pathlib import Path
from typing import Dict, Optional, Union

from app.core.config import settings
from app.infrastructure.persistence.path_state_repository import (
    PathState,
    StudentPathStates,
    StudentPathProfile,
    PathStateRepository,
    default_path_state_repository,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_PATH_STATES_FILE = settings.LEARNING_PATH_STATES_FILE

_path_state_lock = default_path_state_repository._lock


def get_path_state(
    student_id: str,
    knowledge_id: str,
    states_file: Optional[Union[Path, str]] = None,
    default: PathState = PathState.LOCKED,
) -> PathState:
    """获取指定学生指定知识点的当前路径执行状态。未记录时返回 default (默认 LOCKED)。"""
    target_file = states_file or DEFAULT_PATH_STATES_FILE
    return default_path_state_repository.get_path_state(
        student_id=student_id,
        knowledge_id=knowledge_id,
        states_file=target_file,
        default=default,
    )


def set_path_state(
    student_id: str,
    knowledge_id: str,
    state: Union[PathState, str],
    states_file: Optional[Union[Path, str]] = None,
) -> None:
    """设置并持久化指定学生的单知识点路径状态"""
    target_file = states_file or DEFAULT_PATH_STATES_FILE
    default_path_state_repository.set_path_state(
        student_id=student_id,
        knowledge_id=knowledge_id,
        state=state,
        states_file=target_file,
    )


def set_path_states_bulk(
    student_id: str,
    state_updates: Dict[str, Union[PathState, str]],
    states_file: Optional[Union[Path, str]] = None,
) -> None:
    """批量原子更新并持久化指定学生的多个知识点路径状态"""
    target_file = states_file or DEFAULT_PATH_STATES_FILE
    default_path_state_repository.set_path_states_bulk(
        student_id=student_id,
        state_updates=state_updates,
        states_file=target_file,
    )


def get_all_path_states(
    student_id: str,
    states_file: Optional[Union[Path, str]] = None,
) -> Dict[str, PathState]:
    """获取指定学生的全部知识点路径状态字典"""
    target_file = states_file or DEFAULT_PATH_STATES_FILE
    return default_path_state_repository.get_all_path_states(
        student_id=student_id,
        states_file=target_file,
    )


def init_student_path(
    student_id: str,
    initial_states: Optional[Dict[str, Union[PathState, str]]] = None,
    states_file: Optional[Union[Path, str]] = None,
) -> None:
    """初始化学生路径状态，可接收初始状态字典"""
    target_file = states_file or DEFAULT_PATH_STATES_FILE
    default_path_state_repository.init_student_path(
        student_id=student_id,
        initial_states=initial_states,
        states_file=target_file,
    )


def get_student_path_profile(
    student_id: str,
    states_file: Optional[Union[Path, str]] = None,
) -> StudentPathStates:
    """获取指定学生的路径状态概览模型"""
    target_file = states_file or DEFAULT_PATH_STATES_FILE
    return default_path_state_repository.get_student_path_profile(
        student_id=student_id,
        states_file=target_file,
    )


__all__ = [
    "PathState",
    "StudentPathStates",
    "StudentPathProfile",
    "PathStateRepository",
    "default_path_state_repository",
    "DEFAULT_PATH_STATES_FILE",
    "_path_state_lock",
    "get_path_state",
    "set_path_state",
    "set_path_states_bulk",
    "get_all_path_states",
    "init_student_path",
    "get_student_path_profile",
]
