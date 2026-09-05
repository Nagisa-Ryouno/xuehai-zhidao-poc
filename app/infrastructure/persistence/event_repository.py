# -*- coding: utf-8 -*-
"""
event_repository.py
学海智导 (Xuehai Zhidao) V2 统一学习行为日志仓储层 (Event Repository)

职责：
1. 学习行为事件流持久化 (JSONL Append-Only)
2. 线程安全（RLock 保护追加写入与顺序读取）
3. 服务端权威 ISO 8601 时间戳生成
4. 绝不参与任何 BKT、DAG 决策或 LLM 调用
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal, Union

from pydantic import BaseModel, Field

from app.core.config import settings


# ============================================================
# 事件数据模型契约 (严格对照 api_contract.md)
# ============================================================

LearningEventType = Literal[
    "QUESTION_ATTEMPT",
    "HINT_REQUEST",
    "CONCEPT_VIEW",
    "PATH_STEP_COMPLETE",
]


class LearningEventCreate(BaseModel):
    """客户端上报的事件模型（允许忽略或重写客户端伪造的 server_timestamp）"""
    event_id: str = Field(..., min_length=1, description="事件唯一业务标识符")
    student_id: str = Field(..., min_length=1, description="学生ID")
    knowledge_id: str = Field(..., min_length=1, description="知识点ID")
    event_type: LearningEventType = Field(..., description="学习事件类型枚举")
    payload: Dict[str, Any] = Field(default_factory=dict, description="事件明细有效负载")
    client_timestamp: str = Field(..., min_length=1, description="客户端发生时间戳 ISO 8601")

    model_config = {
        "extra": "ignore",  # 忽略客户端私自传入的额外字段（如伪造的 server_timestamp）
    }


class LearningEvent(LearningEventCreate):
    """服务端持久化落盘的标准事件模型"""
    server_timestamp: str = Field(..., description="服务端生成的权威入库时间戳")


# 别名供通用仓储接口规范使用
StoredEvent = LearningEvent


class EventSubmissionResponse(BaseModel):
    """API 成功返回数据模型"""
    status: str = "success"
    event_id: str
    server_timestamp: str


# ============================================================
# EventRepository 仓储类实现
# ============================================================

class EventRepository:
    """学习行为事件流持久化仓储 (JSONL Append-Only)"""

    def __init__(self, file_path: Optional[Union[str, Path]] = None):
        self.file_path: Path = Path(file_path) if file_path is not None else settings.LEARNING_EVENTS_FILE
        self._lock = threading.RLock()

    def record_event(
        self,
        event_in: LearningEventCreate,
        target_file: Optional[Union[str, Path]] = None,
    ) -> LearningEvent:
        """
        持久化一条学习行为事件至 JSONL 文件。
        使用 target_file or self.file_path；
        自动创建 parent 目录；
        生成服务端本地 ISO8601 时间戳 (datetime.now(timezone.utc).astimezone().isoformat())；
        在 self._lock 保护下，以 'a' 模式追加写入 model_dump_json() + '\n'；
        返回 LearningEvent。
        """
        dest_path = Path(target_file) if target_file is not None else self.file_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # 由服务端权威生成本地时区 ISO 8601 时间戳
        server_ts = datetime.now(timezone.utc).astimezone().isoformat()

        event_dict = event_in.model_dump()
        event_dict["server_timestamp"] = server_ts
        stored_event = LearningEvent(**event_dict)

        with self._lock:
            with open(dest_path, "a", encoding="utf-8") as f:
                f.write(stored_event.model_dump_json() + "\n")

        return stored_event

    def get_events_by_student(
        self,
        student_id: str,
        target_file: Optional[Union[str, Path]] = None,
    ) -> List[LearningEvent]:
        """
        查询指定学生全部历史学习事件（按写入顺序返回）。
        使用 target_file or self.file_path；
        若文件不存在返回 []；
        在 self._lock 保护下逐行读取并过滤 student_id，解析为 LearningEvent 列表并返回。
        """
        src_path = Path(target_file) if target_file is not None else self.file_path
        if not src_path.exists():
            return []

        events: List[LearningEvent] = []
        with self._lock:
            with open(src_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                        if data.get("student_id") == student_id:
                            events.append(LearningEvent(**data))
                    except Exception:
                        continue

        return events

    # 便捷方法别名
    get_student_events = get_events_by_student


# 全局默认单例
default_event_repository = EventRepository()

__all__ = [
    "LearningEventType",
    "LearningEventCreate",
    "LearningEvent",
    "StoredEvent",
    "EventSubmissionResponse",
    "EventRepository",
    "default_event_repository",
]
