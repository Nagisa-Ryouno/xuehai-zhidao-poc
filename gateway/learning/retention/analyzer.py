# -*- coding: utf-8 -*-
"""
gateway.learning.retention.analyzer
===================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-F
学习保持度只读分析器 (Learning Retention Analyzer)

设计规范与安全红线：
1. 绝对只读与零污染：只读解析遥测数据与权威 BKT 掌握度，严禁修改任何数据；
2. 服务端绝对权威：掌握度、上次学习时间、经过天数与判定状态完全由服务端计算，绝不信任前端传入参数；
3. 纯确定性与时间注入：支持通过 `now` 参数注入固定基准时间，确保单元测试 100% 幂等可重复；
4. 依赖注入友好：构造函数支持注入 `effectiveness_file`, `events_file`, `bkt_repo`，实现测试物理隔离。
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from gateway.learning.retention.models import (
    RetentionProfile,
    RetentionStatus,
)

REVIEW_AFTER_DAYS: int = 3
DEFAULT_EFFECTIVENESS_EVENTS_FILE: Path = settings.DATA_DIR / "resource_effectiveness_events.jsonl"
DEFAULT_LEARNING_EVENTS_FILE: Path = settings.LEARNING_EVENTS_FILE


def _parse_iso_datetime(ts_str: Optional[str]) -> Optional[datetime]:
    """安全解析 ISO 8601 时间戳字符串为带时区的 datetime"""
    if not ts_str:
        return None
    try:
        cleaned = str(ts_str).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


class RetentionAnalyzer:
    """学习保持度分析核心服务"""

    def __init__(
        self,
        effectiveness_file: Optional[Path] = None,
        events_file: Optional[Path] = None,
        bkt_repo: Optional[Any] = None,
    ):
        self.effectiveness_file = effectiveness_file or DEFAULT_EFFECTIVENESS_EVENTS_FILE
        self.events_file = events_file or DEFAULT_LEARNING_EVENTS_FILE
        self.bkt_repo = bkt_repo or default_bkt_state_repository

    def analyze(
        self,
        student_id: str,
        knowledge_id: str,
        now: Optional[datetime] = None,
    ) -> RetentionProfile:
        """
        根据真实历史学习记录与当前权威 BKT 状态，确定性评估学生在指定考点的保持度状态。
        """
        # 1. 服务端权威读取当前 BKT 掌握度 (单一事实源)
        current_mastery = 0.20
        try:
            bkt_state = self.bkt_repo.get_state(student_id, knowledge_id, auto_init=False)
            if bkt_state is not None:
                current_mastery = round(float(bkt_state.mastery_probability), 4)
        except Exception:
            current_mastery = 0.20

        # 2. 扫描正式学习效果遥测日志，提取该生该考点的最近学习时间
        latest_learning_at: Optional[datetime] = None
        if self.effectiveness_file.exists():
            try:
                with open(self.effectiveness_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line_str = line.strip()
                        if not line_str:
                            continue
                        try:
                            rec = json.loads(line_str)
                        except Exception:
                            continue

                        # 严格匹配学生和考点
                        if rec.get("student_id") != student_id or rec.get("knowledge_id") != knowledge_id:
                            continue

                        event_type = rec.get("event_type")
                        if event_type in ("RESOURCE_SESSION_COMPLETE", "RESOURCE_SESSION_START"):
                            ts = _parse_iso_datetime(rec.get("server_timestamp") or rec.get("client_timestamp"))
                            if ts:
                                if latest_learning_at is None or ts > latest_learning_at:
                                    latest_learning_at = ts
            except Exception:
                pass

        # 规则 A：若从未进行过正式学习，判定为数据不足
        if latest_learning_at is None:
            return RetentionProfile(
                student_id=student_id,
                knowledge_id=knowledge_id,
                last_learning_at=None,
                days_since_learning=None,
                current_mastery=current_mastery,
                retention_status=RetentionStatus.INSUFFICIENT_DATA,
                should_review=False,
                suggested_action=None,
            )

        # 3. 计算距离上次学习经过的时间
        if now is None:
            ref_now = datetime.now(timezone.utc)
        else:
            ref_now = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
            ref_now = ref_now.astimezone(timezone.utc)

        # 使用自然日历日天数差，确保符合人类直觉与确定性测试
        delta_days = (ref_now.date() - latest_learning_at.date()).days
        days_since_learning = max(0, delta_days)

        # 4. 检查在上次正式学习之后，是否已经进行过快速微测复测
        latest_quiz_after_learning: Optional[Dict[str, Any]] = None
        if self.events_file and self.events_file.exists():
            try:
                with open(self.events_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line_str = line.strip()
                        if not line_str:
                            continue
                        try:
                            rec = json.loads(line_str)
                        except Exception:
                            continue

                        if rec.get("student_id") != student_id or rec.get("knowledge_id") != knowledge_id:
                            continue

                        if rec.get("event_type") == "QUESTION_ATTEMPT":
                            evt_ts = _parse_iso_datetime(rec.get("server_timestamp") or rec.get("client_timestamp"))
                            if evt_ts and evt_ts > latest_learning_at and evt_ts <= ref_now:
                                if latest_quiz_after_learning is None or evt_ts > latest_quiz_after_learning["ts"]:
                                    payload = rec.get("payload") or {}
                                    latest_quiz_after_learning = {
                                        "ts": evt_ts,
                                        "is_correct": payload.get("is_correct"),
                                    }
            except Exception:
                pass

        # 判定逻辑：若最近一次复测表现不佳或掌握度低于 0.60，提示需进一步巩固
        if latest_quiz_after_learning is not None:
            quiz_ts = latest_quiz_after_learning["ts"]
            days_since_quiz = max(0, (ref_now.date() - quiz_ts.date()).days)
            quiz_is_correct = latest_quiz_after_learning.get("is_correct")

            if days_since_quiz < REVIEW_AFTER_DAYS:
                if quiz_is_correct is False or current_mastery < 0.60:
                    return RetentionProfile(
                        student_id=student_id,
                        knowledge_id=knowledge_id,
                        last_learning_at=latest_learning_at,
                        days_since_learning=days_since_quiz,
                        current_mastery=current_mastery,
                        retention_status=RetentionStatus.NEEDS_REINFORCEMENT,
                        should_review=True,
                        suggested_action="REVIEW_CONCEPT",
                    )
                else:
                    # 复测答对且掌握度已稳固，进入已复习未到期状态
                    return RetentionProfile(
                        student_id=student_id,
                        knowledge_id=knowledge_id,
                        last_learning_at=latest_learning_at,
                        days_since_learning=days_since_quiz,
                        current_mastery=current_mastery,
                        retention_status=RetentionStatus.NOT_DUE,
                        should_review=False,
                        suggested_action=None,
                    )
            else:
                # 距最近一次复测已超过 REVIEW_AFTER_DAYS 天，更新参考经过天数后继续走常规复测建议判定
                days_since_learning = days_since_quiz

        # 5. 无后续复测记录时的规则判定 (Rules B, C, D)
        if days_since_learning < REVIEW_AFTER_DAYS:
            # 规则 B: 距上次学习 < 3 天 -> NOT_DUE
            return RetentionProfile(
                student_id=student_id,
                knowledge_id=knowledge_id,
                last_learning_at=latest_learning_at,
                days_since_learning=days_since_learning,
                current_mastery=current_mastery,
                retention_status=RetentionStatus.NOT_DUE,
                should_review=False,
                suggested_action=None,
            )

        # 达到或超过 3 天 -> DUE_FOR_REVIEW
        if current_mastery >= 0.60:
            # 规则 C: >= 3 天 且掌握度良好 -> 快速微测复习
            suggested_action = "RETAKE_QUIZ"
        else:
            # 规则 D: >= 3 天 但掌握度偏低 -> 回顾概念微卡
            suggested_action = "REVIEW_CONCEPT"

        return RetentionProfile(
            student_id=student_id,
            knowledge_id=knowledge_id,
            last_learning_at=latest_learning_at,
            days_since_learning=days_since_learning,
            current_mastery=current_mastery,
            retention_status=RetentionStatus.DUE_FOR_REVIEW,
            should_review=True,
            suggested_action=suggested_action,
        )


default_retention_analyzer = RetentionAnalyzer()
