# -*- coding: utf-8 -*-
"""
gateway.learning.today.resolver
===============================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-G
今日学习行动确定性仲裁解析器 (Today's Learning Action Resolver)

设计规范与安全红线：
1. 确定性单一仲裁阶梯：
   NEEDS_REINFORCEMENT > DUE_FOR_REVIEW > IN_PROGRESS > PRACTICE > VIEW_PROGRESS > NONE
2. 保持度复查平局裁决：若多个考点同时满足某一保持度状态，严格按 knowledge_id 升序选择首个；
3. 绝对只读与零副作用：严禁写入 BKT、学习事件、遥测或路径状态；
4. 时间一致性与确定性幂等：相同数据快照 + 固定 now 50 次重复执行返回完全一致的结果；
5. 依赖注入友好：支持构造函数注入 Mock/自定义组件以实现纯粹单元测试隔离。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.retention.models import RetentionProfile, RetentionStatus
from gateway.learning.today.models import (
    TodayActionResponse,
    TodayActionType,
    TodayLearningAction,
)


class TodayActionResolver:
    """今日学习行动确定性仲裁解析器"""

    def __init__(
        self,
        retention_analyzer: Optional[Any] = None,
        path_state_service: Optional[Any] = None,
        resource_resolver: Optional[Any] = None,
        student_service: Optional[Any] = None,
    ):
        self._retention_analyzer = retention_analyzer
        self._path_state_service = path_state_service
        self._resource_resolver = resource_resolver
        self._student_service = student_service

    @property
    def retention_analyzer(self) -> Any:
        if self._retention_analyzer is not None:
            return self._retention_analyzer
        from gateway.learning.retention import default_retention_analyzer
        return default_retention_analyzer

    @property
    def path_state_service(self) -> Any:
        if self._path_state_service is not None:
            return self._path_state_service
        import path_state_service
        return path_state_service

    @property
    def resource_resolver(self) -> Any:
        if self._resource_resolver is not None:
            return self._resource_resolver
        from gateway.learning.resources import default_resource_resolver
        return default_resource_resolver

    @property
    def student_service(self) -> Any:
        if self._student_service is not None:
            return self._student_service
        from app.services.student_service import student_service
        return student_service

    def _get_knowledge_name(self, knowledge_id: Optional[str]) -> str:
        if not knowledge_id:
            return ""
        if knowledge_id in CONCEPT_CARDS:
            return CONCEPT_CARDS[knowledge_id].knowledge_name
        return knowledge_id

    def _validate_student(self, student_id: str) -> None:
        if not student_id:
            raise KeyError(f"Invalid student ID: {student_id}")
        try:
            profile = self.student_service.get_student_profile(student_id)
            if profile:
                return
        except Exception:
            pass
        if student_id in ("S001", "S002") or student_id.startswith("DEMO_"):
            return
        raise KeyError(f"Student not found: {student_id}")

    def _get_candidate_knowledge_ids(self, student_id: str) -> List[str]:
        analyzer = self.retention_analyzer
        learned_kids = set()
        eff_file = getattr(analyzer, "effectiveness_file", None)
        if eff_file and Path(eff_file).exists():
            try:
                with open(eff_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line_str = line.strip()
                        if not line_str:
                            continue
                        try:
                            rec = json.loads(line_str)
                            if rec.get("student_id") == student_id and rec.get("knowledge_id"):
                                learned_kids.add(rec["knowledge_id"])
                        except Exception:
                            continue
            except Exception:
                pass

        if learned_kids:
            return sorted(list(learned_kids))

        # 若真实 effectiveness 文件存在但该生无记录（如从未学习的 S002），保持度判定无候选考点
        if eff_file and Path(eff_file).exists():
            return []

        # 在无文件或 mock 测试环境下，回退遍历标准考点
        return sorted(list(CONCEPT_CARDS.keys()))

    def resolve(
        self,
        student_id: str,
        now: Optional[datetime] = None,
        candidate_knowledge_ids: Optional[List[str]] = None,
    ) -> TodayActionResponse:
        """
        确定性裁决学生今日唯一的最佳学习行动
        """
        self._validate_student(student_id)

        # -------------------------------------------------------------
        # Step 1 & Step 2: 保持度判断 (NEEDS_REINFORCEMENT & DUE_FOR_REVIEW)
        # -------------------------------------------------------------
        candidates = (
            candidate_knowledge_ids
            if candidate_knowledge_ids is not None
            else self._get_candidate_knowledge_ids(student_id)
        )

        needs_reinforcement_profiles: List[RetentionProfile] = []
        due_for_review_profiles: List[RetentionProfile] = []

        for kid in candidates:
            try:
                profile = self.retention_analyzer.analyze(student_id, kid, now=now)
                if profile.retention_status == RetentionStatus.NEEDS_REINFORCEMENT:
                    needs_reinforcement_profiles.append(profile)
                elif profile.retention_status == RetentionStatus.DUE_FOR_REVIEW:
                    due_for_review_profiles.append(profile)
            except Exception:
                continue

        # 优先级 1: NEEDS_REINFORCEMENT 优先
        if needs_reinforcement_profiles:
            needs_reinforcement_profiles.sort(key=lambda p: p.knowledge_id)
            chosen = needs_reinforcement_profiles[0]
            kname = self._get_knowledge_name(chosen.knowledge_id)
            return TodayActionResponse(
                student_id=student_id,
                action=TodayLearningAction(
                    action_type=TodayActionType.REVIEW_RETENTION,
                    title="建议再巩固一下",
                    description=f"{kname}最近一次复习还不够稳定，先重新看看概念，再试一次。",
                    cta_label="重新学习",
                    priority_reason="已有考点复习未稳固，需针对性巩固",
                    knowledge_id=chosen.knowledge_id,
                    knowledge_name=kname,
                    suggested_action=chosen.suggested_action or "REVIEW_CONCEPT",
                ),
            )

        # 优先级 2: DUE_FOR_REVIEW
        if due_for_review_profiles:
            due_for_review_profiles.sort(key=lambda p: p.knowledge_id)
            chosen = due_for_review_profiles[0]
            kname = self._get_knowledge_name(chosen.knowledge_id)
            return TodayActionResponse(
                student_id=student_id,
                action=TodayLearningAction(
                    action_type=TodayActionType.REVIEW_RETENTION,
                    title="该复习一下了",
                    description=f"{kname}已经有一段时间没有复习，现在花 1～2 分钟快速测一下，可以帮助你确认是否还记得。",
                    cta_label="开始快速复测",
                    priority_reason="已有考点达到复习间隔时间",
                    knowledge_id=chosen.knowledge_id,
                    knowledge_name=kname,
                    suggested_action=chosen.suggested_action or "RETAKE_QUIZ",
                ),
            )

        # -------------------------------------------------------------
        # Step 3: 学习路径检查 (IN_PROGRESS / 首个 AVAILABLE)
        # -------------------------------------------------------------
        in_progress_kid: Optional[str] = None
        available_kid: Optional[str] = None
        all_completed: bool = False

        try:
            path_states = self.path_state_service.get_all_path_states(student_id)
        except Exception:
            path_states = {}

        in_prog_candidates = [
            k for k, s in path_states.items()
            if (s.value if hasattr(s, "value") else str(s)) == "IN_PROGRESS"
        ]
        if in_prog_candidates:
            in_prog_candidates.sort()
            in_progress_kid = in_prog_candidates[0]

        dashboard_steps = []
        try:
            dashboard = self.student_service.get_student_dashboard(student_id)
            dashboard_steps = dashboard.get("learning_path", {}).get("learning_path", [])
        except Exception:
            dashboard_steps = []

        if not in_progress_kid and dashboard_steps:
            for step in dashboard_steps:
                skid = step.get("knowledge_id")
                if not skid:
                    continue
                s_state = path_states.get(skid)
                s_state_val = s_state.value if hasattr(s_state, "value") else str(s_state)
                if s_state_val == "IN_PROGRESS":
                    in_progress_kid = skid
                    break
                elif s_state_val == "AVAILABLE" and available_kid is None:
                    available_kid = skid

        continue_kid = in_progress_kid or available_kid
        if continue_kid:
            kname = self._get_knowledge_name(continue_kid)
            is_new_demo = student_id.startswith("DEMO_")
            title = f"开始你的第一次学习：{kname}" if is_new_demo else f"继续学习：{kname}"
            description = (
                "从微观经济学第一站开始，跟随自适应导学建立你的个人学情档案。"
                if is_new_demo
                else "这是你当前学习路径中的下一步内容。"
            )
            priority_reason = (
                "开启微观经济学自适应学习之旅"
                if is_new_demo
                else "当前学习路径中的首要未完成任务"
            )
            return TodayActionResponse(
                student_id=student_id,
                action=TodayLearningAction(
                    action_type=TodayActionType.CONTINUE_LEARNING,
                    title=title,
                    description=description,
                    cta_label="开始学习",
                    priority_reason=priority_reason,
                    knowledge_id=continue_kid,
                    knowledge_name=kname,
                    suggested_action="REVIEW_CONCEPT",
                ),
            )

        # -------------------------------------------------------------
        # Step 4: PRACTICE 检查 (调用已有 resource_resolver)
        # -------------------------------------------------------------
        practice_kid: Optional[str] = None
        try:
            res_rec = self.resource_resolver.resolve(student_id=student_id)
            for rec in res_rec.recommendations:
                rtype = getattr(rec.resource, "resource_type", None)
                rtype_val = rtype.value if hasattr(rtype, "value") else str(rtype)
                if rtype_val == "PRACTICE":
                    practice_kid = rec.resource.knowledge_id
                    break
        except Exception:
            practice_kid = None

        if practice_kid:
            kname = self._get_knowledge_name(practice_kid)
            return TodayActionResponse(
                student_id=student_id,
                action=TodayLearningAction(
                    action_type=TodayActionType.PRACTICE,
                    title="做一道小练习",
                    description="现在没有需要复习的内容，可以用一个小练习保持学习节奏。",
                    cta_label="开始练习",
                    priority_reason="推荐靶向微练保持学习节奏",
                    knowledge_id=practice_kid,
                    knowledge_name=kname,
                    suggested_action="RETAKE_QUIZ",
                ),
            )

        # -------------------------------------------------------------
        # Step 5: VIEW_PROGRESS (所有考点均已达标)
        # -------------------------------------------------------------
        if dashboard_steps:
            all_steps_completed = all(
                (path_states.get(step.get("knowledge_id")) and 
                 (path_states.get(step.get("knowledge_id")).value if hasattr(path_states.get(step.get("knowledge_id")), "value") else str(path_states.get(step.get("knowledge_id")))) == "COMPLETED")
                for step in dashboard_steps if step.get("knowledge_id")
            )
            if all_steps_completed:
                all_completed = True

        if all_completed:
            return TodayActionResponse(
                student_id=student_id,
                action=TodayLearningAction(
                    action_type=TodayActionType.VIEW_PROGRESS,
                    title="看看最近的学习进展",
                    description="目前没有需要立即完成的任务，可以先看看自己的学习进度。",
                    cta_label="查看学情",
                    priority_reason="当前所有阶段任务已全部达标",
                    knowledge_id=None,
                    knowledge_name=None,
                    suggested_action="VIEW_PROGRESS",
                ),
            )

        # -------------------------------------------------------------
        # Step 6: NONE (兜底)
        # -------------------------------------------------------------
        return TodayActionResponse(
            student_id=student_id,
            action=TodayLearningAction(
                action_type=TodayActionType.NONE,
                title="",
                description="",
                cta_label="",
                priority_reason="当前无待办学习任务",
                knowledge_id=None,
                knowledge_name=None,
                suggested_action=None,
            ),
        )


default_today_action_resolver = TodayActionResolver()
