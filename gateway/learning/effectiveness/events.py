# -*- coding: utf-8 -*-
"""
gateway.learning.effectiveness.events
=====================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-D
学习会话与效果分析辅助日志持久化层 (Effectiveness Telemetry Isolation)

设计规范与红线：
1. 物理隔离：只写入 `data/resource_effectiveness_events.jsonl`，严禁写入 `data/learning_events.jsonl`；
2. 零副作用：纯旁路辅助遥测，绝对不影响 BKT 计算与正式学习状态更新；
3. 线程安全原子追加写：支持高并发追加，崩溃或网络抖动不丢数据；
4. 隐私防泄露：仅记录最小结构化统计字段，严禁记录长文本、Prompt、密钥或脱敏前个人隐私。
"""

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.config import settings

# 默认效果辅助事件文件路径
DEFAULT_EFFECTIVENESS_EVENTS_FILE = settings.DATA_DIR / "resource_effectiveness_events.jsonl"
_file_lock = threading.Lock()


def record_effectiveness_event(
    student_id: str,
    session_id: str,
    knowledge_id: str,
    event_type: str,
    initial_mastery: Optional[float] = None,
    final_mastery: Optional[float] = None,
    delta: Optional[float] = None,
    quiz_result: Optional[bool] = None,
    metadata: Optional[Dict[str, Any]] = None,
    client_timestamp: Optional[str] = None,
    events_file: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    线程安全地向 data/resource_effectiveness_events.jsonl 追加单条辅助日志
    """
    target_file = events_file or DEFAULT_EFFECTIVENESS_EVENTS_FILE
    target_file.parent.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "event_id": f"evt-eff-{uuid.uuid4().hex[:12]}",
        "student_id": student_id,
        "session_id": session_id,
        "knowledge_id": knowledge_id,
        "event_type": event_type,
        "initial_mastery": initial_mastery,
        "final_mastery": final_mastery,
        "delta": delta,
        "quiz_result": quiz_result,
        "metadata": metadata or {},
        "client_timestamp": client_timestamp or now_iso,
        "server_timestamp": now_iso,
    }

    line = json.dumps(record, ensure_ascii=False) + "\n"

    with _file_lock:
        with open(target_file, "a", encoding="utf-8") as f:
            f.write(line)

    return record


def get_effectiveness_events(
    student_id: Optional[str] = None,
    session_id: Optional[str] = None,
    knowledge_id: Optional[str] = None,
    events_file: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    只读查询辅助效果日志（用于离线分析与聚合）
    """
    target_file = events_file or DEFAULT_EFFECTIVENESS_EVENTS_FILE
    if not target_file.exists():
        return []

    results = []
    with _file_lock:
        with open(target_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    if student_id and data.get("student_id") != student_id:
                        continue
                    if session_id and data.get("session_id") != session_id:
                        continue
                    if knowledge_id and data.get("knowledge_id") != knowledge_id:
                        continue
                    results.append(data)
                except json.JSONDecodeError:
                    continue
    return results

