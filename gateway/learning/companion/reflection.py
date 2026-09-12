# -*- coding: utf-8 -*-
"""
gateway.learning.companion.reflection
=====================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-B
学习结果反思与闭环服务 (Action Reflection Service)

核心原则：
1. 真实客观：所有掌握度数据必须从系统单一真实源（BKT/Analytics/Events）读取，绝不信任客户端传入的伪造掌握度
2. 零生产决策权：AI 仅负责解释最新系统状态，不修改任何 BKT 状态或正式事件
3. 无黑话：文案友好通俗，反映真实认知阶段
4. 闭环引导：反思后即时挂接下一批确定性白名单 Guided Actions
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from app.core.constants import DEMOTION_THRESHOLD, MASTERY_THRESHOLD_HIGH, MASTERY_THRESHOLD_LOW
from app.infrastructure.persistence.event_repository import default_event_repository
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.analytics import default_analytics_service
from gateway.learning.companion.guided_actions import DeterministicActionBuilder
from gateway.learning.companion.models import (
    ActionType,
    CompanionSafetyMetadata,
    CompanionSuggestedAction,
    LearningActionResultRequest,
    LearningActionResultResponse,
)

logger = logging.getLogger("xuehai.companion.reflection")


class ActionReflectionService:
    """学习行动结果反思服务"""

    def __init__(self):
        self.action_builder = DeterministicActionBuilder()

    def reflect_action_result(
        self, request: LearningActionResultRequest
    ) -> LearningActionResultResponse:
        """
        处理学生完成某一学习行动后的反思请求

        流程：
        1. 验证学生与考点
        2. 从权威 Analytics Service 读取真实最新掌握度与错题情况（杜绝客户端造假）
        3. 从历史事件流读取最近一次作答事实
        4. 生成启发式反思讲解
        5. 生成下一组确定性 Guided Actions
        6. 返回强类型响应模型
        """
        student_id = request.student_id.strip()
        kid = request.knowledge_id.strip() if request.knowledge_id else "K01"
        action_type = request.action_type.strip()

        # 读取真实考点信息
        card = CONCEPT_CARDS.get(kid)
        k_name = card.knowledge_name if card else kid

        # 权威单一真实源：读取学生当前整体掌握度情况
        progress = default_analytics_service.get_student_progress(student_id)
        current_mastery = 0.20
        mastery_status = "起步阶段"
        has_unresolved_wrong = False

        if progress:
            for kp in progress.knowledge_point_masteries:
                if kp.knowledge_id == kid:
                    current_mastery = float(kp.mastery)
                    state_map = {
                        "MASTERED": "已掌握",
                        "DEVELOPING": "正在巩固",
                        "NEEDS_REINFORCEMENT": "需要加强",
                        "UNSTUDIED": "起步阶段",
                    }
                    mastery_status = kp.status or state_map.get(kp.state, kp.state)
                    break

        # 检查是否存在近期错题
        wrong_resp = default_analytics_service.get_student_wrong_answers(student_id)
        if wrong_resp:
            for w in wrong_resp.wrong_answers:
                if w.knowledge_id == kid:
                    has_unresolved_wrong = True
                    break

        # 从学习事件流中读取该学生在当前考点上的最新真实事件记录
        events = default_event_repository.get_events_by_student(student_id)
        kp_quiz_events = [
            e for e in events if e.knowledge_id == kid and e.event_type == "QUESTION_ATTEMPT"
        ]

        latest_quiz_correct = None
        if kp_quiz_events:
            last_payload = kp_quiz_events[-1].payload
            latest_quiz_correct = last_payload.get("is_correct")

        # 若请求显式携带了有效结果且与事件流兼容，以事件流和客观结果为准
        is_quiz_correct = (
            latest_quiz_correct
            if latest_quiz_correct is not None
            else (request.result == "correct")
        )

        percent_str = f"{current_mastery * 100.0:.1f}%"

        # 构造客观导师复盘文案 (Zero Jargon)
        if action_type == ActionType.RETRY_QUIZ.value:
            if is_quiz_correct:
                if current_mastery >= MASTERY_THRESHOLD_HIGH:
                    reflection = (
                        f"🎉 太棒了！刚才这次针对【{k_name}】的微测验练习你答对了！\n\n"
                        f"系统当前显示：该考点掌握度已达到 {percent_str}，成功突破 80% 达标标准，达到「已掌握」状态！\n"
                        f"这证明你已经准确掌握了核心概念与推导逻辑。建议前往知识图谱探索下一阶段学习内容，或查看学情档案回顾全景成效。"
                    )
                else:
                    reflection = (
                        f"👏 答得很棒！刚才这次针对【{k_name}】的微测验练习正确。\n\n"
                        f"系统当前显示：该考点掌握度正在稳步提升至 {percent_str}，当前处于「{mastery_status}」阶段。\n"
                        f"你的理解正在变得更加扎实，但尚未达到系统设定的 80% 掌握标准。趁热打铁再做一道题，巩固达标吧！"
                    )
            else:
                reflection = (
                    f"💡 刚才这次针对【{k_name}】的练习未能选对，没关系，错题正是查漏补缺的最好契机！\n\n"
                    f"系统当前记录该考点掌握度为 {percent_str}，处于「{mastery_status}」阶段。\n"
                    f"微观经济学概念往往包含细微的区别与假设条件，建议先重新看一遍考点概念微卡，看清易错误区后再进行练习突破。"
                )
        elif action_type == ActionType.REVIEW_CONCEPT.value:
            reflection = (
                f"📖 你刚刚完成了考点【{k_name}】概念微卡的精要阅读！系统已记录你的微卡学习轨迹。\n\n"
                f"当前该考点掌握度为 {percent_str}。直观理解已基本建立，建议立即进行一次针对性微测验，"
                f"用真实做题来检验概念理解并让系统记录你的掌握度提升！"
            )
        else:
            reflection = (
                f"✓ 系统已记录你的最新学习行为。考点【{k_name}】当前掌握度为 {percent_str}（{mastery_status}）。\n\n"
                f"建议跟随系统推荐路线继续攻坚，保持积极的学习节奏！"
            )

        # 确定性推导下一步 Guided Actions
        guided_actions = self.action_builder.build_actions(
            student_id=student_id,
            knowledge_id=kid,
            mastery=current_mastery,
            has_unresolved_wrong=has_unresolved_wrong,
            question_id=request.question_id,
            knowledge_name=k_name,
        )

        learning_state = {
            "knowledge_id": kid,
            "knowledge_name": k_name,
            "mastery": current_mastery,
            "mastery_percent": percent_str,
            "status": mastery_status,
            "is_mastered": (current_mastery >= MASTERY_THRESHOLD_HIGH),
        }

        safety = CompanionSafetyMetadata(
            allow_production_decision=False,
            sanitized=True,
            offline_mode=True,
            context_source="bkt_single_source_of_truth",
            redactions_applied=["read_only_reflection", "zero_mutation"],
        )

        session_id = request.session_id or f"sess-act-{student_id}-{uuid.uuid4().hex[:8]}"
        action_id = getattr(request, "action_id", None) or f"act-{kid}-{uuid.uuid4().hex[:6]}"
        before_mastery = current_mastery
        after_mastery = current_mastery
        delta = 0.0

        return LearningActionResultResponse(
            session_id=session_id,
            student_id=student_id,
            action_id=action_id,
            action=action_type,
            action_type=action_type,
            knowledge_id=kid,
            knowledge_name=k_name,
            before_mastery=before_mastery,
            after_mastery=after_mastery,
            mastery_delta=delta,
            consecutive_incorrect=0,
            mastery_state_text=mastery_status,
            reflection=reflection,
            reflection_text=reflection,
            guided_actions=guided_actions,
            next_actions=guided_actions,
            learning_state=learning_state,
            safety=safety,
        )


# 全局单例
default_action_reflection_service = ActionReflectionService()
