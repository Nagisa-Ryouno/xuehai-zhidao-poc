# -*- coding: utf-8 -*-
"""
event_service.py
学海智导 (Xuehai Zhidao) V2 统一学习行为日志服务层

职责：
1. 接收与校验前端/测验等模块上报的学习行为事件
2. 服务端权威生成 ISO 8601 时间戳 (server_timestamp)
3. 线程安全地追加落盘至本地 data/learning_events.jsonl
4. 绝不参与任何 BKT、DAG 决策或 LLM 调用（坚守确定性日志采集器职责）
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field

# ============================================================
# 存储路径与锁配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / "data"
DEFAULT_EVENTS_FILE = DEFAULT_DATA_DIR / "learning_events.jsonl"

_file_lock = threading.Lock()

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


class EventSubmissionResponse(BaseModel):
    """API 成功返回数据模型"""
    status: str = "success"
    event_id: str
    server_timestamp: str


# ============================================================
# 核心业务函数
# ============================================================

def record_event(
    event_in: LearningEventCreate,
    target_file: Optional[Path] = None,
) -> LearningEvent:
    """
    持久化一条学习行为事件至 JSONL 文件。
    确保服务端权威时间戳、线程安全写入，自动创建目录。
    """
    file_path = target_file or DEFAULT_EVENTS_FILE
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # 由服务端权威生成本地时区 ISO 8601 时间戳
    server_ts = datetime.now(timezone.utc).astimezone().isoformat()

    event_dict = event_in.model_dump()
    event_dict["server_timestamp"] = server_ts

    stored_event = LearningEvent(**event_dict)

    # 线程安全地追加写入（一行一个标准 JSON）
    with _file_lock:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(stored_event.model_dump_json() + "\n")

    return stored_event


def get_student_events(
    student_id: str,
    target_file: Optional[Path] = None,
) -> List[LearningEvent]:
    """
    查询指定学生全部历史学习事件（按写入顺序返回）
    供后续教师干预工作台及历史分析使用
    """
    file_path = target_file or DEFAULT_EVENTS_FILE
    if not file_path.exists():
        return []

    events: List[LearningEvent] = []
    with _file_lock:
        with open(file_path, "r", encoding="utf-8") as f:
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
