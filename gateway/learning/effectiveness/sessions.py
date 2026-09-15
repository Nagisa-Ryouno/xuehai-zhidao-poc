# -*- coding: utf-8 -*-
"""
gateway.learning.effectiveness.sessions
=======================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-D
学习会话生命周期管理服务 (Learning Session Management Service)

设计规范与安全红线：
1. 权威快照：Session 创建时严格 snapshot `initial_mastery`，完成时严格重新读取 `final_mastery`；
2. 零伪造防御：客户端传入的任何掌握度数值一律忽略或拒绝，以服务端真实 BKT 状态为准；
3. 幂等性：重复调用 complete_session 返回既有完成结果，不产生二次事件或重复状态突变；
4. 学生上下文隔离：跨学生查询或操作必须强校验 `student_id`，禁止未授权跨生越权；
5. 原子持久化：写入同目录下的临时文件后 os.replace 替换，保证高并发与断电安全性。
"""

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.effectiveness.events import record_effectiveness_event
from gateway.learning.effectiveness.models import (
    LearningSession,
    SessionStatus,
)
from gateway.learning.resources.resolver import ResourceResolver

DEFAULT_SESSIONS_FILE = settings.DATA_DIR / "learning_sessions.json"
_session_lock = threading.Lock()


class LearningSessionService:
    """学习会话服务与独立持久化存储"""

    def __init__(self, sessions_file: Optional[Path] = None):
        self.sessions_file = sessions_file or DEFAULT_SESSIONS_FILE
        self._sessions: Dict[str, LearningSession] = {}
        self._load_sessions()

    def _load_sessions(self) -> None:
        """从磁盘原子加载所有会话"""
        if not self.sessions_file.exists():
            self._sessions.clear()
            return
        try:
            with open(self.sessions_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                new_sessions = {}
                if isinstance(raw_data, dict):
                    for sid, sdata in raw_data.items():
                        try:
                            new_sessions[sid] = LearningSession(**sdata)
                        except Exception:
                            continue
                self._sessions = new_sessions
        except Exception:
            pass

    def _save_sessions(self) -> None:
        """原子写入磁盘持久化"""
        self.sessions_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.sessions_file.parent / f"{self.sessions_file.name}.tmp.{uuid.uuid4().hex[:8]}"
        serialized = {sid: sess.model_dump() for sid, sess in self._sessions.items()}
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(serialized, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, self.sessions_file)
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

    def create_session(
        self,
        student_id: str,
        knowledge_id: str,
        resource_ids: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> LearningSession:
        """
        创建新的学习会话，并权威快照 initial_mastery
        """
        # 1. 考点合法性校验
        if knowledge_id not in CONCEPT_CARDS:
            raise KeyError(f"考点不存在：{knowledge_id}")

        # 2. 从权威 BKT 状态库读取当前掌握度快照
        bkt_state = default_bkt_state_repository.get_state(student_id, knowledge_id)
        raw_mastery = float(bkt_state.mastery_probability) if bkt_state else 0.20
        initial_mastery = round(raw_mastery, 4)

        # 3. 若未提供待学资源列表，调用推荐引擎确定性获取推荐序列
        if not resource_ids:
            rec_res = ResourceResolver.resolve(student_id=student_id, knowledge_id=knowledge_id)
            resource_ids = [r.resource.resource_id for r in rec_res.recommendations]

        session = LearningSession(
            session_id=f"sess-{uuid.uuid4().hex[:12]}",
            student_id=student_id,
            knowledge_id=knowledge_id,
            initial_mastery=initial_mastery,
            resource_ids=resource_ids or [],
            completed_resource_ids=[],
            status=SessionStatus.IN_PROGRESS,
            notes=notes,
        )

        with _session_lock:
            self._sessions[session.session_id] = session
            self._save_sessions()

        # 记录会话开启遥测事件
        record_effectiveness_event(
            student_id=student_id,
            session_id=session.session_id,
            knowledge_id=knowledge_id,
            event_type="RESOURCE_SESSION_START",
            initial_mastery=initial_mastery,
            metadata={"resource_ids": resource_ids},
        )

        return session

    def get_session(
        self,
        session_id: str,
        request_student_id: Optional[str] = None,
    ) -> LearningSession:
        """
        查询会话实体，支持多生上下文隔离检查
        """
        with _session_lock:
            if session_id not in self._sessions:
                self._load_sessions()
            session = self._sessions.get(session_id)

        if not session:
            raise KeyError(f"找不到指定的学习会话：{session_id}")

        if request_student_id and session.student_id != request_student_id:
            raise PermissionError(f"学生上下文隔离校验失败：无权访问学生 {session.student_id} 的学习会话")

        return session

    def mark_resource_completed(
        self,
        session_id: str,
        student_id: str,
        resource_id: str,
    ) -> LearningSession:
        """
        在会话中标记研读完成某项资源
        """
        session = self.get_session(session_id, request_student_id=student_id)

        if session.status != SessionStatus.IN_PROGRESS:
            return session

        with _session_lock:
            if resource_id not in session.completed_resource_ids:
                session.completed_resource_ids.append(resource_id)
                self._sessions[session_id] = session
                self._save_sessions()

        return session

    def link_quiz_attempt(
        self,
        session_id: str,
        student_id: str,
        question_id: str,
        is_correct: bool,
    ) -> LearningSession:
        """
        将会话与正式测验作答关联
        """
        session = self.get_session(session_id, request_student_id=student_id)

        with _session_lock:
            session.quiz_question_id = question_id
            session.quiz_result = is_correct
            self._sessions[session_id] = session
            self._save_sessions()

        return session

    def complete_session(
        self,
        session_id: str,
        student_id: str,
        completed_resource_ids: Optional[List[str]] = None,
        quiz_question_id: Optional[str] = None,
        quiz_result: Optional[bool] = None,
    ) -> LearningSession:
        """
        完成学习会话：
        1. 幂等性防护：若已是 COMPLETED，直接返回已有会话结果；
        2. 权威重读：从权威 BKT 库重新读取 final_mastery，计算真实的 mastery_delta；
        3. 记录效果遥测。
        """
        session = self.get_session(session_id, request_student_id=student_id)

        # 幂等性防护
        if session.status == SessionStatus.COMPLETED:
            return session

        # 权威重读最新 BKT 状态
        bkt_state = default_bkt_state_repository.get_state(session.student_id, session.knowledge_id)
        raw_final = float(bkt_state.mastery_probability) if bkt_state else session.initial_mastery
        final_mastery = round(raw_final, 4)
        mastery_delta = round(final_mastery - session.initial_mastery, 4)

        now_iso = datetime.now(timezone.utc).isoformat()

        with _session_lock:
            session.final_mastery = final_mastery
            session.mastery_delta = mastery_delta
            session.completed_at = now_iso
            session.status = SessionStatus.COMPLETED

            if completed_resource_ids:
                for rid in completed_resource_ids:
                    if rid not in session.completed_resource_ids:
                        session.completed_resource_ids.append(rid)

            if quiz_question_id:
                session.quiz_question_id = quiz_question_id
            if quiz_result is not None:
                session.quiz_result = quiz_result

            self._sessions[session_id] = session
            self._save_sessions()

        # 记录会话完成与效果评估遥测
        record_effectiveness_event(
            student_id=session.student_id,
            session_id=session.session_id,
            knowledge_id=session.knowledge_id,
            event_type="RESOURCE_SESSION_COMPLETE",
            initial_mastery=session.initial_mastery,
            final_mastery=final_mastery,
            delta=mastery_delta,
            quiz_result=session.quiz_result,
            metadata={
                "completed_resources_count": len(session.completed_resource_ids),
                "quiz_question_id": session.quiz_question_id,
            },
        )

        return session

    def get_latest_session(
        self,
        student_id: str,
        knowledge_id: str,
    ) -> Optional[LearningSession]:
        """获取学生针对特定考点的最新一个会话"""
        with _session_lock:
            self._load_sessions()
            matched = [
                s for s in self._sessions.values()
                if s.student_id == student_id and s.knowledge_id == knowledge_id
            ]
        if not matched:
            return None
        # 按 started_at 逆序排列
        matched.sort(key=lambda x: x.started_at, reverse=True)
        return matched[0]

    def get_student_sessions(
        self,
        student_id: str,
        knowledge_id: Optional[str] = None,
    ) -> List[LearningSession]:
        """获取指定学生的所有会话"""
        with _session_lock:
            matched = [s for s in self._sessions.values() if s.student_id == student_id]
            if knowledge_id:
                matched = [s for s in matched if s.knowledge_id == knowledge_id]
        matched.sort(key=lambda x: x.started_at, reverse=True)
        return matched


default_session_service = LearningSessionService()

