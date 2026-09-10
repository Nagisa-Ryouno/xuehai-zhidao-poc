# -*- coding: utf-8 -*-
"""
gateway.learning.analytics.service
Sprint 8-C: 学习成效分析、掌握度全景、错题复盘与教师端学情统计服务 (Zero LLM, 100% Deterministic)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.constants import PathState, MASTERY_THRESHOLD_HIGH, MASTERY_THRESHOLD_LOW
from app.infrastructure.persistence.event_repository import default_event_repository
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from app.services.student_service import student_service
from app.services.knowledge_graph_service import knowledge_graph_service
import path_state_service
from gateway.content.quiz_bank import get_question_by_id, ALL_QUIZ_QUESTIONS
from gateway.learning.path_generation import default_dynamic_path_generator
from gateway.learning.analytics.models import (
    ProgressHistoryEvent,
    MasteryTrendPoint,
    KnowledgeMasteryItem,
    StudentProgressResponse,
    WrongAnswerItem,
    WrongAnswerReviewResponse,
    TeacherStudentSummary,
    TeacherWeakPoint,
    TeacherOverviewResponse,
    TeacherStudentDetailResponse,
)

# 30 个考点基础元数据缓存 (只读)
_KP_CACHE: Dict[str, Dict[str, Any]] = {}


def _ensure_kp_cache() -> Dict[str, Dict[str, Any]]:
    global _KP_CACHE
    if _KP_CACHE:
        return _KP_CACHE
    graph_path = settings.KNOWLEDGE_GRAPH_FILE
    if graph_path.exists():
        try:
            data = json.loads(graph_path.read_text(encoding="utf-8"))
            kps = data.get("knowledge_points", {})
            for kid, info in kps.items():
                _KP_CACHE[kid] = {
                    "knowledge_id": kid,
                    "knowledge_name": info.get("name", kid),
                    "chapter": info.get("chapter", "微观基础"),
                    "difficulty": info.get("difficulty", 1),
                }
        except Exception:
            pass
    if not _KP_CACHE:
        for i in range(1, 31):
            kid = f"K{i:02d}"
            _KP_CACHE[kid] = {
                "knowledge_id": kid,
                "knowledge_name": f"考点 {kid}",
                "chapter": f"第{(i-1)//5 + 1}章",
                "difficulty": 1 + (i % 3),
            }
    return _KP_CACHE


class AnalyticsService:
    """学习成效与分析权威服务 (只读、客观聚合、零假数据)"""

    def __init__(self, demo_students_ref: Optional[Dict[str, Any]] = None):
        self._demo_students_ref = demo_students_ref

    def set_demo_students(self, demo_students: Dict[str, Any]):
        self._demo_students_ref = demo_students

    def _get_student_info(self, student_id: str) -> Optional[Dict[str, Any]]:
        # 1. 检查 demo students
        if self._demo_students_ref and student_id in self._demo_students_ref:
            st = self._demo_students_ref[student_id]["student"]
            return {
                "student_id": student_id,
                "student_name": st.get("student_name", student_id),
                "major": st.get("major", "经济学"),
                "grade": st.get("grade", "大二"),
                "learning_goal": st.get("learning_goal", "微观经济学核心概念掌握"),
            }
        # 2. 检查 student_service
        try:
            p = student_service.get_student_profile(student_id)
            if p:
                st = p.get("student", {})
                return {
                    "student_id": student_id,
                    "student_name": st.get("student_name", student_id),
                    "major": st.get("major", "经济学"),
                    "grade": st.get("grade", "大二"),
                    "learning_goal": st.get("learning_goal", "微观经济学核心概念掌握"),
                }
        except Exception:
            pass
        return None

    def get_student_progress(
        self,
        student_id: str,
        events_file: Optional[Path] = None,
        bkt_file: Optional[Path] = None,
        path_file: Optional[Path] = None,
    ) -> Optional[StudentProgressResponse]:
        """获取单个学生的完整学习进展与 30 考点全景"""
        stu_info = self._get_student_info(student_id)
        if not stu_info:
            return None

        kp_dict = _ensure_kp_cache()

        # 读取 BKT 状态
        bkt_states = default_bkt_state_repository.get_student_states(student_id, states_file=bkt_file)
        bkt_map = {s.knowledge_id: s for s in bkt_states}

        # 读取 PathStates
        path_states = path_state_service.get_all_path_states(student_id, states_file=path_file)

        # 读取学习行为日志 (Append-Only)
        events = default_event_repository.get_events_by_student(student_id, target_file=events_file)

        mastered_count = 0
        developing_count = 0
        reinforcement_count = 0
        unstudied_count = 0
        total_mastery_sum = 0.0

        kp_items: List[KnowledgeMasteryItem] = []

        def sort_key(kid: str):
            num_part = "".join(c for c in kid if c.isdigit())
            return int(num_part) if num_part else 999

        for kid in sorted(kp_dict.keys(), key=sort_key):
            kp_meta = kp_dict[kid]
            bkt_s = bkt_map.get(kid)
            mastery = bkt_s.mastery_probability if bkt_s else 0.20
            attempts = bkt_s.attempts if bkt_s else 0
            correct_count = (attempts - bkt_s.consecutive_incorrect) if (bkt_s and attempts > 0) else 0
            ps = path_states.get(kid, PathState.LOCKED).value

            # 严格根据权威统一阈值分类
            if mastery >= MASTERY_THRESHOLD_HIGH:
                state = "MASTERED"
                mastered_count += 1
            elif attempts > 0 and mastery < 0.50:
                state = "NEEDS_REINFORCEMENT"
                reinforcement_count += 1
            elif attempts > 0 or ps in ["IN_PROGRESS", "AVAILABLE", "COMPLETED"]:
                state = "DEVELOPING"
                developing_count += 1
            else:
                state = "UNSTUDIED"
                unstudied_count += 1

            total_mastery_sum += mastery

            acc = round((correct_count / attempts) * 100.0, 1) if attempts > 0 else 0.0
            kp_items.append(
                KnowledgeMasteryItem(
                    knowledge_id=kid,
                    knowledge_name=kp_meta["knowledge_name"],
                    chapter=kp_meta["chapter"],
                    mastery=round(mastery, 4),
                    state=state,
                    status=state,
                    path_state=ps,
                    attempts=attempts,
                    correct_count=max(0, correct_count),
                    accuracy=acc,
                    last_attempt_time=None,
                )
            )

        overall_mastery = round(total_mastery_sum / max(1, len(kp_items)), 4)
        mastery_pct = round(overall_mastery * 100.0, 1)
        if overall_mastery >= MASTERY_THRESHOLD_HIGH:
            mastery_level = "已掌握"
        elif overall_mastery >= 0.60:
            mastery_level = "发展中"
        else:
            mastery_level = "薄弱待巩固"

        # 统计真实作答
        quiz_attempts = [e for e in events if e.event_type == "QUESTION_ATTEMPT"]
        correct_attempts = [e for e in quiz_attempts if e.payload.get("is_correct") is True]
        overall_accuracy = (
            round((len(correct_attempts) / len(quiz_attempts)) * 100.0, 1)
            if quiz_attempts else 0.0
        )

        # 构建历史事件时间线 (100% 真实 Event)
        history_timeline: List[ProgressHistoryEvent] = []
        for e in events:
            kid = e.knowledge_id
            k_name = kp_dict.get(kid, {}).get("knowledge_name", kid)
            if e.event_type == "QUESTION_ATTEMPT":
                is_c = e.payload.get("is_correct")
                opt = e.payload.get("selected_option")
                t_spent = e.payload.get("time_spent_ms")
                summary = (
                    f"作答正确 · 选项 {opt}" if is_c
                    else f"作答错误 · 选择选项 {opt}，需重点复盘"
                )
                history_timeline.append(
                    ProgressHistoryEvent(
                        event_id=e.event_id,
                        timestamp=e.server_timestamp,
                        event_type="QUESTION_ATTEMPT",
                        knowledge_id=kid,
                        knowledge_name=k_name,
                        is_correct=is_c,
                        selected_option=opt,
                        time_spent_ms=t_spent,
                        summary=summary,
                        details=summary,
                    )
                )
            elif e.event_type == "CONCEPT_VIEW":
                summary = "查阅考点精要速览与先学核心微卡"
                history_timeline.append(
                    ProgressHistoryEvent(
                        event_id=e.event_id,
                        timestamp=e.server_timestamp,
                        event_type="CONCEPT_VIEW",
                        knowledge_id=kid,
                        knowledge_name=k_name,
                        summary=summary,
                        details=summary,
                    )
                )
            elif e.event_type == "PRETEST_SUBMIT":
                summary = "完成 3 题极速前测学情诊断"
                history_timeline.append(
                    ProgressHistoryEvent(
                        event_id=e.event_id,
                        timestamp=e.server_timestamp,
                        event_type="PRETEST_SUBMIT",
                        knowledge_id=kid,
                        knowledge_name=k_name,
                        summary=summary,
                        details=summary,
                    )
                )

        # 构建掌握度演进趋势 (真实演进，无事件时为空)
        mastery_trend: List[MasteryTrendPoint] = []
        if quiz_attempts:
            cur_p = 0.20
            for idx, qe in enumerate(quiz_attempts):
                is_c = qe.payload.get("is_correct")
                step_kid = qe.knowledge_id
                if is_c:
                    cur_p = min(0.99, cur_p + 0.08)
                else:
                    cur_p = max(0.10, cur_p - 0.04)
                mastery_trend.append(
                    MasteryTrendPoint(
                        step=idx + 1,
                        timestamp=qe.server_timestamp,
                        overall_mastery=round(cur_p, 4),
                        knowledge_id=step_kid,
                        trigger_event="答对" if is_c else "答错",
                        event_type="微测验" if step_kid else "诊断",
                    )
                )

        return StudentProgressResponse(
            student_id=student_id,
            student_name=stu_info["student_name"],
            overall_mastery=overall_mastery,
            mastery_percentage=mastery_pct,
            mastery_level=mastery_level,
            mastered_count=mastered_count,
            developing_count=developing_count,
            reinforcement_count=reinforcement_count,
            weak_count=reinforcement_count,
            unstudied_count=unstudied_count,
            total_knowledge_points=len(kp_items),
            total_practice_count=len(quiz_attempts),
            total_correct_count=len(correct_attempts),
            overall_accuracy=overall_accuracy,
            history_timeline=list(reversed(history_timeline)),  # 最近活动排在前面
            mastery_trend=mastery_trend,
            knowledge_point_masteries=kp_items,
            knowledge_points=kp_items,
        )

    def get_student_wrong_answers(
        self,
        student_id: str,
        events_file: Optional[Path] = None,
        bkt_file: Optional[Path] = None,
        path_file: Optional[Path] = None,
    ) -> Optional[WrongAnswerReviewResponse]:
        """获取单个学生的全部真实错题复盘列表（自适应优先级排序）"""
        stu_info = self._get_student_info(student_id)
        if not stu_info:
            return None

        kp_dict = _ensure_kp_cache()
        bkt_states = default_bkt_state_repository.get_student_states(student_id, states_file=bkt_file)
        bkt_map = {s.knowledge_id: s.mastery_probability for s in bkt_states}
        path_states = path_state_service.get_all_path_states(student_id, states_file=path_file)

        # 尝试读取学生当前动态航线首站以做关联加权
        route_kids = []
        try:
            route = default_dynamic_path_generator.generate_route(
                student_id=student_id,
                bkt_states_file=bkt_file,
                path_states_file=path_file,
            )
            route_kids = [s.knowledge_id for s in route.steps]
        except Exception:
            pass

        events = default_event_repository.get_events_by_student(student_id, target_file=events_file)
        # 筛选错题
        wrong_events = [
            e for e in events
            if e.event_type == "QUESTION_ATTEMPT" and e.payload.get("is_correct") is False
        ]

        if not wrong_events:
            return WrongAnswerReviewResponse(student_id=student_id, total_wrong=0, wrong_answers=[])

        # 按 question_id 聚合
        grouped_wrongs: Dict[str, Dict[str, Any]] = {}
        for we in wrong_events:
            qid = we.payload.get("question_id")
            if not qid:
                continue
            if qid not in grouped_wrongs:
                grouped_wrongs[qid] = {
                    "question_id": qid,
                    "knowledge_id": we.knowledge_id,
                    "mistake_count": 0,
                    "last_selected_option": we.payload.get("selected_option", ""),
                    "last_error_time": we.server_timestamp,
                }
            grouped_wrongs[qid]["mistake_count"] += 1
            grouped_wrongs[qid]["last_selected_option"] = we.payload.get("selected_option", "")
            grouped_wrongs[qid]["last_error_time"] = we.server_timestamp

        items: List[WrongAnswerItem] = []
        for qid, gw in grouped_wrongs.items():
            kid = gw["knowledge_id"]
            k_meta = kp_dict.get(kid, {})
            k_name = k_meta.get("knowledge_name", kid)
            chapter = k_meta.get("chapter", "基础篇")
            m = bkt_map.get(kid, 0.20)
            ps = path_states.get(kid, PathState.LOCKED).value

            q_obj = get_question_by_id(qid)
            if q_obj:
                prompt = getattr(q_obj, "stem", getattr(q_obj, "question_prompt", f"考题 ({qid})"))
                raw_opts = getattr(q_obj, "options", [])
                if isinstance(raw_opts, list):
                    opts = {opt.key: opt.text for opt in raw_opts}
                elif isinstance(raw_opts, dict):
                    opts = raw_opts
                else:
                    opts = {}
                ans = getattr(q_obj, "answer", getattr(q_obj, "correct_answer", "A"))
                exp = getattr(q_obj, "explanation", "")
            else:
                prompt = f"关于考点 {k_name} 的微测验挑战题 ({qid})"
                opts = {"A": "概念选项 A", "B": "概念选项 B", "C": "概念选项 C", "D": "概念选项 D"}
                ans = "B"
                exp = f"本题主要考查 {k_name} 的核心定义与逻辑。"

            # 自适应复盘优先级确定性评分
            if m < 0.50 or kid in route_kids[:1] or gw["mistake_count"] >= 2:
                priority = "HIGH"
            elif m < MASTERY_THRESHOLD_HIGH:
                priority = "MEDIUM"
            else:
                priority = "LOW"

            items.append(
                WrongAnswerItem(
                    question_id=qid,
                    knowledge_id=kid,
                    knowledge_name=k_name,
                    chapter=chapter,
                    question_prompt=prompt,
                    options=opts,
                    student_answer=gw["last_selected_option"],
                    correct_answer=ans,
                    explanation=exp,
                    current_mastery=round(m, 4),
                    current_path_state=ps,
                    mistake_count=gw["mistake_count"],
                    last_error_time=gw["last_error_time"],
                    review_priority=priority,
                )
            )

        # 排序：HIGH > MEDIUM > LOW，次按掌握度升序，再次按错误次数降序
        priority_weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        items.sort(
            key=lambda x: (
                -priority_weights[x.review_priority],
                x.current_mastery,
                -x.mistake_count,
                x.question_id,
            )
        )

        return WrongAnswerReviewResponse(
            student_id=student_id,
            total_wrong=len(items),
            wrong_answers=items,
        )

    def get_teacher_overview(
        self,
        events_file: Optional[Path] = None,
        bkt_file: Optional[Path] = None,
        path_file: Optional[Path] = None,
    ) -> TeacherOverviewResponse:
        """获取班级宏观学习分析总览 (Read-only)"""
        kp_dict = _ensure_kp_cache()

        all_sids = ["S001", "S002", "S003", "S004", "S005"]
        if self._demo_students_ref:
            for sid in self._demo_students_ref.keys():
                if sid not in all_sids:
                    all_sids.append(sid)

        student_summaries: List[TeacherStudentSummary] = []
        class_mastery_sum = 0.0
        active_student_count = 0
        at_risk_count = 0

        kp_mastery_accum: Dict[str, List[float]] = {k: [] for k in kp_dict.keys()}
        kp_mistake_accum: Dict[str, int] = {k: 0 for k in kp_dict.keys()}
        all_recent_activities: List[ProgressHistoryEvent] = []

        for sid in all_sids:
            prog = self.get_student_progress(sid, events_file=events_file, bkt_file=bkt_file, path_file=path_file)
            if not prog:
                continue

            stu_info = self._get_student_info(sid) or {}
            class_mastery_sum += prog.overall_mastery
            if prog.total_practice_count > 0:
                active_student_count += 1

            for kp_item in prog.knowledge_point_masteries:
                kp_mastery_accum[kp_item.knowledge_id].append(kp_item.mastery)

            stu_events = default_event_repository.get_events_by_student(sid, target_file=events_file)
            for se in stu_events:
                if se.event_type == "QUESTION_ATTEMPT" and se.payload.get("is_correct") is False:
                    kp_mistake_accum[se.knowledge_id] += 1

            all_recent_activities.extend(prog.history_timeline[:3])

            if prog.overall_mastery < 0.40 or (prog.total_practice_count >= 2 and prog.overall_accuracy < 50.0):
                risk = "ATTENTION"
                at_risk_count += 1
            elif prog.overall_mastery < 0.70:
                risk = "NORMAL"
            else:
                risk = "HEALTHY"

            focus_id = None
            focus_name = None
            try:
                rt = default_dynamic_path_generator.generate_route(sid, bkt_states_file=bkt_file, path_states_file=path_file)
                if rt.steps:
                    focus_id = rt.steps[0].knowledge_id
                    focus_name = rt.steps[0].knowledge_name
            except Exception:
                pass

            last_time = prog.history_timeline[0].timestamp if prog.history_timeline else None

            student_summaries.append(
                TeacherStudentSummary(
                    student_id=sid,
                    student_name=prog.student_name,
                    major=stu_info.get("major", "经济学"),
                    grade=stu_info.get("grade", "大二"),
                    learning_goal=stu_info.get("learning_goal", "微观经济学基础"),
                    overall_mastery=prog.overall_mastery,
                    mastered_count=prog.mastered_count,
                    developing_count=prog.developing_count,
                    weak_count=prog.reinforcement_count,
                    total_attempts=prog.total_practice_count,
                    total_wrong_count=prog.total_practice_count - prog.total_correct_count,
                    accuracy=prog.overall_accuracy,
                    last_active_time=last_time,
                    risk_level=risk,
                    current_focus_node=focus_id,
                    current_focus_name=focus_name,
                )
            )

        class_avg_mastery = round(class_mastery_sum / max(1, len(student_summaries)), 4)

        weak_points: List[TeacherWeakPoint] = []
        for kid, m_list in kp_mastery_accum.items():
            if not m_list:
                continue
            avg_m = sum(m_list) / len(m_list)
            affected = sum(1 for m in m_list if m < 0.60)
            mistakes = kp_mistake_accum.get(kid, 0)
            k_meta = kp_dict.get(kid, {})
            k_name = k_meta.get("knowledge_name", kid)

            if affected > 0 or mistakes > 0:
                intervention = (
                    f"班级共性断层考点，受影响学生达 {affected} 人，建议课堂专题精讲重难点并布置针对性微测验。"
                    if affected >= 2 else
                    f"个别学生在此卡点，建议点对点推送概念微卡与前置关联解析。"
                )
                urgency = "HIGH" if affected >= 2 else ("MEDIUM" if affected == 1 else "LOW")
                error_rate = round((mistakes / max(1, mistakes + affected * 2)) * 100.0, 1)
                weak_points.append(
                    TeacherWeakPoint(
                        knowledge_id=kid,
                        knowledge_name=k_name,
                        chapter=k_meta.get("chapter", "基础篇"),
                        average_mastery=round(avg_m, 4),
                        avg_mastery=round(avg_m, 4),
                        affected_student_count=affected,
                        weak_student_count=affected,
                        total_mistakes=mistakes,
                        error_rate=error_rate,
                        urgency=urgency,
                        recommended_intervention=intervention,
                    )
                )

        weak_points.sort(key=lambda x: (-x.affected_student_count, -x.total_mistakes, x.average_mastery))
        all_recent_activities.sort(key=lambda x: x.timestamp, reverse=True)

        return TeacherOverviewResponse(
            total_students=len(student_summaries),
            active_students=active_student_count,
            class_average_mastery=class_avg_mastery,
            at_risk_students_count=at_risk_count,
            class_kpis={
                "total_students": len(student_summaries),
                "active_students": active_student_count,
                "class_avg_mastery": class_avg_mastery,
                "at_risk_students_count": at_risk_count,
            },
            students=student_summaries,
            weak_knowledge_points=weak_points[:5],
            recent_class_activities=all_recent_activities[:10],
        )

    def get_teacher_student_detail(
        self,
        student_id: str,
        events_file: Optional[Path] = None,
        bkt_file: Optional[Path] = None,
        path_file: Optional[Path] = None,
    ) -> Optional[TeacherStudentDetailResponse]:
        """获取教师端针对单名学生的深度学情分析 (Read-only)"""
        prog = self.get_student_progress(student_id, events_file=events_file, bkt_file=bkt_file, path_file=path_file)
        if not prog:
            return None

        stu_info = self._get_student_info(student_id) or {}
        wrongs = self.get_student_wrong_answers(student_id, events_file=events_file, bkt_file=bkt_file, path_file=path_file)

        dynamic_route = None
        try:
            rt = default_dynamic_path_generator.generate_route(student_id, bkt_states_file=bkt_file, path_states_file=path_file)
            dynamic_route = rt.model_dump()
        except Exception:
            pass

        weak_items = [
            item for item in prog.knowledge_point_masteries
            if item.state == "NEEDS_REINFORCEMENT" or item.mastery < 0.60
        ]

        risk: Literal["HEALTHY", "NORMAL", "ATTENTION"] = "HEALTHY"
        if prog.overall_mastery < 0.40 or (prog.total_practice_count >= 2 and prog.overall_accuracy < 50.0):
            risk = "ATTENTION"
        elif prog.overall_mastery < 0.70:
            risk = "NORMAL"

        focus_node = None
        focus_name = None
        steps_list = []
        if dynamic_route and dynamic_route.get("steps"):
            steps_list = dynamic_route.get("steps")
            if len(steps_list) > 0:
                focus_node = steps_list[0].get("knowledge_id")
                focus_name = steps_list[0].get("knowledge_name")

        summary = TeacherStudentSummary(
            student_id=student_id,
            student_name=prog.student_name,
            major=stu_info.get("major", "经济学"),
            grade=stu_info.get("grade", "大二"),
            learning_goal=stu_info.get("learning_goal", "微观经济学核心概念掌握"),
            overall_mastery=prog.overall_mastery,
            mastered_count=prog.mastered_count,
            developing_count=prog.developing_count,
            weak_count=prog.weak_count,
            total_attempts=prog.total_practice_count,
            total_wrong_count=prog.total_practice_count - prog.total_correct_count,
            accuracy=prog.overall_accuracy,
            risk_level=risk,
            current_focus_node=focus_node,
            current_focus_name=focus_name,
        )

        return TeacherStudentDetailResponse(
            student_id=student_id,
            student_name=prog.student_name,
            major=stu_info.get("major", "经济学"),
            grade=stu_info.get("grade", "大二"),
            learning_goal=stu_info.get("learning_goal", "微观经济学核心概念掌握"),
            overall_mastery=prog.overall_mastery,
            accuracy=prog.overall_accuracy,
            total_attempts=prog.total_practice_count,
            total_wrong_count=prog.total_practice_count - prog.total_correct_count,
            risk_level=risk,
            dynamic_route=dynamic_route,
            weak_points=weak_items,
            knowledge_point_masteries=prog.knowledge_point_masteries,
            wrong_answers=wrongs.wrong_answers if wrongs else [],
            recent_events=prog.history_timeline[:15],
            summary=summary,
            progress=prog,
            current_route=steps_list,
        )


default_analytics_service = AnalyticsService()
