# -*- coding: utf-8 -*-
"""
gateway.learning.companion.events
=================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-B
AI 辅导行为日志仓储扩展 (Companion Auxiliary Events)

支持的辅导事件类型（非生产性正式学习行为）：
- AI_ACTION_VIEW: 呈现引导行动
- AI_ACTION_CLICK: 学生点击引导行动
- AI_GUIDED_SESSION: 伴学完整会话周期
- AI_QUICK_CHECK: 快速思维检查互动

红线原则：
1. 采用 Append-Only 模式持久化
2. 与正式学习行为（CONCEPT_VIEW, QUESTION_ATTEMPT）严格解耦
3. 辅导事件绝对不被当成正式掌握度达标证明（不驱动 BKT）
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings

_companion_event_lock = threading.RLock()

COMPANION_EVENT_TYPES = {
    "AI_ACTION_VIEW",
    "AI_ACTION_CLICK",
    "AI_GUIDED_SESSION",
    "AI_QUICK_CHECK",
}


def record_companion_event(
    event_type: str,
    student_id: str,
    knowledge_id: str,
    payload: Optional[Dict[str, Any]] = None,
    client_timestamp: Optional[str] = None,
    target_file: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    追加记录一条 AI 辅导行为日志（Append-Only，与正式学习事件严格物理隔离）
    """
    dest_path = target_file if target_file is not None else (settings.DATA_DIR / "companion_events.jsonl")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    server_ts = datetime.now(timezone.utc).astimezone().isoformat()
    evt_id = f"evt-ai-{uuid.uuid4().hex[:12]}"
    c_ts = client_timestamp or server_ts

    event_record = {
        "event_id": evt_id,
        "student_id": student_id,
        "knowledge_id": knowledge_id,
        "event_type": event_type,
        "payload": payload or {},
        "client_timestamp": c_ts,
        "server_timestamp": server_ts,
    }

    line = json.dumps(event_record, ensure_ascii=False) + "\n"
    with _companion_event_lock:
        with open(dest_path, "a", encoding="utf-8") as f:
            f.write(line)

    return event_record


def get_all_student_companion_events(
    student_id: str,
    source_file: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    获取指定学生的所有 AI 辅导行为事件记录
    """
    source_path = source_file if source_file is not None else (settings.DATA_DIR / "companion_events.jsonl")
    if not source_path.exists():
        return []

    results = []
    with _companion_event_lock:
        with open(source_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    if data.get("student_id") == student_id and data.get("event_type") in COMPANION_EVENT_TYPES:
                        results.append(data)
                except Exception:
                    continue
    return results
