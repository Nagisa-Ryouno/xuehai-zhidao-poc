# -*- coding: utf-8 -*-
"""
gateway.learning.resources.events
=================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-C
学习资源行为日志仓储 (Resource Auxiliary Events)

包含：
- record_resource_event: 记录资源交互事件 (RESOURCE_VIEW, RESOURCE_OPEN, RESOURCE_COMPLETE, RESOURCE_EXTERNAL_OPEN)
- get_student_resource_events: 查询学生资源交互记录

红线规范：
1. 采用 Append-Only 模式持久化至 data/resource_events.jsonl
2. 与正式学习事件 (data/learning_events.jsonl) 严格物理隔离，绝不混合存储
3. 资源行为仅用于学习行为追踪与体验优化，绝不直接驱动 BKT 掌握度变更（零生产副作用）
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from gateway.learning.resources.models import VALID_RESOURCE_EVENT_TYPES

_resource_event_lock = threading.RLock()


def record_resource_event(
    student_id: str,
    resource_id: str,
    knowledge_id: str,
    event_type: str,
    duration_seconds: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    client_timestamp: Optional[str] = None,
    target_file: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    追加记录一条学习资源交互行为日志（Append-Only，与正式学习事件严格物理隔离）
    """
    if event_type not in VALID_RESOURCE_EVENT_TYPES:
        raise ValueError(f"非法资源事件类型: {event_type}，合法集合为: {VALID_RESOURCE_EVENT_TYPES}")

    dest_path = target_file if target_file is not None else (settings.DATA_DIR / "resource_events.jsonl")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    server_ts = datetime.now(timezone.utc).astimezone().isoformat()
    evt_id = f"evt-res-{uuid.uuid4().hex[:12]}"
    c_ts = client_timestamp or server_ts

    event_record = {
        "event_id": evt_id,
        "student_id": student_id,
        "resource_id": resource_id,
        "knowledge_id": knowledge_id,
        "event_type": event_type,
        "duration_seconds": duration_seconds,
        "metadata": metadata or {},
        "client_timestamp": c_ts,
        "server_timestamp": server_ts,
    }

    line = json.dumps(event_record, ensure_ascii=False) + "\n"
    with _resource_event_lock:
        with open(dest_path, "a", encoding="utf-8") as f:
            f.write(line)

    return event_record


def get_student_resource_events(
    student_id: str,
    source_file: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    获取指定学生的所有学习资源交互事件记录
    """
    source_path = source_file if source_file is not None else (settings.DATA_DIR / "resource_events.jsonl")
    if not source_path.exists():
        return []

    results = []
    with _resource_event_lock:
        with open(source_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    if data.get("student_id") == student_id and data.get("event_type") in VALID_RESOURCE_EVENT_TYPES:
                        results.append(data)
                except Exception:
                    continue
    return results
