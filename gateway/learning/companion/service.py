# -*- coding: utf-8 -*-
"""
gateway.learning.companion.service
==================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-A
AI 学习伙伴应用服务 (Companion Service)

核心架构不变量：
1. 只读解释边界：AI 永远不修改生产状态 (allow_production_decision = False)
2. 零副作用 (Zero Mutation)：不写入 BKT 状态，不追加生产事件，不篡改路径
3. 严格学生会话隔离：内存会话以 student_id 为主控，绝不跨生串味
4. 离线确定性保障：即使无外部 LLM API，仍能依托权威微卡与题库输出高质量辅导
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from gateway.adapter import get_provider
from gateway.learning.analytics import default_analytics_service
from gateway.learning.companion.context import (
    CompanionContextBuilder,
    default_companion_context_builder,
)
from gateway.learning.companion.events import record_companion_event
from gateway.learning.companion.guided_actions import DeterministicActionBuilder
from gateway.learning.companion.models import (
    CompanionChatMessage,
    CompanionContextMetadata,
    CompanionMode,
    CompanionSafetyMetadata,
    CompanionSession,
    CompanionStudyRequest,
    CompanionStudyResponse,
    CompanionSuggestedAction,
    LearningActionResultRequest,
    LearningActionResultResponse,
    QuickCheckQuestion,
    QuickCheckResponse,
)
from gateway.learning.companion.prompt import (
    build_system_prompt,
    format_concept_explain_offline,
    format_conversation_reply_offline,
    format_learning_summary_offline,
    format_wrong_answer_review_offline,
    is_potential_injection,
)
from gateway.learning.companion.quick_check import default_quick_check_service
from gateway.learning.companion.reflection import default_action_reflection_service

logger = logging.getLogger("xuehai.companion")


class CompanionService:
    """AI 学习伙伴全周期服务"""

    def __init__(
        self,
        context_builder: Optional[CompanionContextBuilder] = None,
    ):
        self.context_builder = context_builder or default_companion_context_builder
        self.action_builder = DeterministicActionBuilder()
        self.quick_check_service = default_quick_check_service
        self.reflection_service = default_action_reflection_service
        # 内存态会话管理，以 session_id 为主键
        self._sessions: Dict[str, CompanionSession] = {}
        # 学生最新活跃会话映射：student_id -> session_id
        self._student_latest_session: Dict[str, str] = {}

    def get_or_create_session(
        self, student_id: str, session_id: Optional[str] = None
    ) -> CompanionSession:
        """获取或创建学生专属会话（保障学生隔离）"""
        now_str = datetime.now(timezone.utc).isoformat()

        if session_id and session_id in self._sessions:
            existing = self._sessions[session_id]
            # 安全防线：若会话绑定的学生与当前请求学生不符，强制创建新会话防串味
            if existing.student_id == student_id:
                return existing

        # 若请求未指定 session_id，检查学生最近的会话
        if not session_id and student_id in self._student_latest_session:
            latest_id = self._student_latest_session[student_id]
            if latest_id in self._sessions:
                return self._sessions[latest_id]

        new_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        new_session = CompanionSession(
            session_id=new_id,
            student_id=student_id,
            messages=[],
            last_knowledge_id=None,
            created_at=now_str,
        )
        self._sessions[new_id] = new_session
        self._student_latest_session[student_id] = new_id
        return new_session

    def reset_student_session(self, student_id: str) -> bool:
        """重置指定学生的伴学会话（清空上下文防脏数据）"""
        if student_id in self._student_latest_session:
            sid = self._student_latest_session.pop(student_id)
            if sid in self._sessions:
                del self._sessions[sid]
        # 清理所有属于该学生的会话
        to_del = [sid for sid, s in self._sessions.items() if s.student_id == student_id]
        for sid in to_del:
            del self._sessions[sid]
        return True

    def get_session(self, session_id: str) -> Optional[CompanionSession]:
        """查询指定会话状态"""
        return self._sessions.get(session_id)

    async def handle_companion_request(
        self, request: CompanionStudyRequest
    ) -> CompanionStudyResponse:
        """
        处理学生发起的 AI 伴学辅导请求
        
        执行边界：
        1. 验证学生身份与参数
        2. 构建只读权威上下文（根据 mode 调度）
        3. 生成结构化回答（离线确定性生成或接入云端适配器）
        4. 更新会话轮次（限制 5 轮 / 10 条消息）
        5. 返回强契约响应模型，严格附加 allow_production_decision = False
        """
        student_id = request.student_id.strip()
        mode = request.mode
        session = self.get_or_create_session(student_id, request.session_id)
        now_str = datetime.now(timezone.utc).isoformat()

        # 根据辅导模式抽取权威客观上下文
        if mode == CompanionMode.CONCEPT_EXPLAIN:
            target_kid = request.knowledge_id or session.last_knowledge_id or "K01"
            meta, facts, referenced = self.context_builder.build_concept_context(
                student_id, target_kid
            )
            session.last_knowledge_id = target_kid
            answer = format_concept_explain_offline(facts)
            suggested_actions = [
                f"巩固练习：完成【{target_kid}】微测验",
                f"思维延展：查看【{target_kid}】前置依赖",
                "向导师追问：我不理解生活案例的对应关系",
            ]
            user_msg_content = request.message or f"请讲解考点：{target_kid}"

        elif mode == CompanionMode.WRONG_ANSWER_REVIEW:
            target_qid = request.question_id
            if not target_qid:
                # 自动寻找学生最近的一道错题
                wrong_resp = default_analytics_service.get_student_wrong_answers(student_id)
                if wrong_resp and wrong_resp.wrong_answers:
                    target_qid = wrong_resp.wrong_answers[0].question_id
                else:
                    target_qid = "Q-K01-01"  # 兜底试题

            meta, facts, referenced = self.context_builder.build_wrong_answer_context(
                student_id, target_qid, request.knowledge_id
            )
            session.last_knowledge_id = meta.knowledge_id
            answer = format_wrong_answer_review_offline(facts)
            suggested_actions = [
                f"靶向重练：重新作答【{target_qid}】",
                f"回溯微卡：复习【{meta.knowledge_id}】概念卡",
                "向导师追问：为什么这个错误选项容易混淆？",
            ]
            user_msg_content = request.message or f"请帮我剖析错题：{target_qid}"

        elif mode == CompanionMode.LEARNING_SUMMARY:
            meta, facts, referenced = self.context_builder.build_learning_summary_context(
                student_id
            )
            answer = format_learning_summary_offline(facts)
            suggested_actions = [
                "攻坚薄弱考点：按推荐顺序开始练习",
                "查阅错题本：复盘历史易错题",
                "向导师追问：如何制定冲刺复习规划？",
            ]
            user_msg_content = request.message or "请为我生成当前学习成效全景总结"

        elif mode == CompanionMode.CONVERSATION:
            user_msg_content = request.message or "老师好，我想深入请教微观经济学的核心思维。"
            meta, facts, referenced = self.context_builder.build_conversation_context(
                student_id, session, user_msg_content, request.knowledge_id
            )
            if request.knowledge_id:
                session.last_knowledge_id = request.knowledge_id

            answer = format_conversation_reply_offline(user_msg_content, facts)
            suggested_actions = [
                "继续追问底层假设",
                "查看相关考点概念微卡",
                "返回当前学习路径",
            ]
        else:
            raise ValueError(f"未知的伴学辅导模式：{mode}")

        # 若请求包含学习材料上下文，进行真实材料联结增强
        if request.resource_context:
            res_title = request.resource_context.get("resource_title") or request.resource_context.get("title", "")
            res_type = request.resource_context.get("resource_type") or request.resource_context.get("type", "")
            if res_title:
                answer += f"\n\n📚 **结合研读材料**：针对【{res_title}】（{res_type}），建议结合上述逻辑关注其核心推演与实际应用。"
                if referenced is not None:
                    referenced.append(f"学习材料：{res_title}")

        # 维护内存会话历史（最多保存 5 轮，即 10 条消息）
        session.messages.append(
            CompanionChatMessage(
                role="user",
                content=user_msg_content,
                timestamp=now_str,
            )
        )
        session.messages.append(
            CompanionChatMessage(
                role="assistant",
                content=answer,
                timestamp=now_str,
            )
        )
        if len(session.messages) > 10:
            session.messages = session.messages[-10:]

        # 构建确定性 Guided Actions
        wrong_resp = default_analytics_service.get_student_wrong_answers(student_id)
        has_unresolved_wrong = False
        if wrong_resp:
            has_unresolved_wrong = any(
                w.knowledge_id == meta.knowledge_id for w in wrong_resp.wrong_answers
            )

        guided_actions = self.action_builder.build_actions(
            student_id=student_id,
            knowledge_id=meta.knowledge_id or "K01",
            mastery=meta.mastery,
            has_unresolved_wrong=has_unresolved_wrong,
            question_id=meta.question_id,
            knowledge_name=meta.knowledge_name,
        )

        # 概念精讲模式下自动挂接轻量快速思维检查
        quick_check = None
        if mode == CompanionMode.CONCEPT_EXPLAIN and meta.knowledge_id:
            quick_check = self.quick_check_service.get_quick_check(meta.knowledge_id)

        learning_state = {
            "knowledge_id": meta.knowledge_id,
            "knowledge_name": meta.knowledge_name,
            "mastery": meta.mastery,
            "status": meta.mastery_status,
            "is_mastered": (meta.mastery is not None and meta.mastery >= 0.80),
        }

        safety = CompanionSafetyMetadata(
            allow_production_decision=False,
            sanitized=True,
            offline_mode=True,
            context_source="authoritative_knowledge_engine",
            redactions_applied=["pii_filter", "prompt_injection_guard"],
        )

        return CompanionStudyResponse(
            session_id=session.session_id,
            mode=mode,
            answer=answer,
            context=meta,
            safety=safety,
            suggested_actions=suggested_actions,
            guided_actions=guided_actions,
            learning_state=learning_state,
            quick_check=quick_check,
            provider="offline",
            referenced_facts=referenced,
        )

    def get_quick_check(self, knowledge_id: str) -> Optional[QuickCheckQuestion]:
        """获取指定考点的快速思维检查试题"""
        return self.quick_check_service.get_quick_check(knowledge_id)

    def evaluate_quick_check(
        self, student_id: str, check_id: str, knowledge_id: str, selected_option: str
    ) -> QuickCheckResponse:
        """评估学生快速思维检查，记录辅导日志，绝不更新 BKT"""
        res = self.quick_check_service.evaluate_quick_check(
            student_id, check_id, knowledge_id, selected_option
        )
        try:
            record_companion_event(
                "AI_QUICK_CHECK",
                student_id,
                knowledge_id,
                {
                    "check_id": check_id,
                    "selected": selected_option,
                    "is_correct": res.is_correct,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record AI_QUICK_CHECK: {e}")
        return res

    def reflect_action_result(
        self, request: LearningActionResultRequest
    ) -> LearningActionResultResponse:
        """反思学生完成的真实学习行动结果"""
        return self.reflection_service.reflect_action_result(request)

    def get_student_guided_actions(
        self, student_id: str, knowledge_id: Optional[str] = None
    ) -> List[CompanionSuggestedAction]:
        """按需获取学生当前考点的确定性 Guided Actions"""
        kid = knowledge_id or "K01"
        progress = default_analytics_service.get_student_progress(student_id)
        mastery = None
        if progress:
            for kp in progress.knowledge_point_masteries:
                if kp.knowledge_id == kid:
                    mastery = float(kp.mastery)
                    break
        wrong_resp = default_analytics_service.get_student_wrong_answers(student_id)
        has_wrong = False
        if wrong_resp:
            has_wrong = any(w.knowledge_id == kid for w in wrong_resp.wrong_answers)
        return self.action_builder.build_actions(
            student_id=student_id,
            knowledge_id=kid,
            mastery=mastery,
            has_unresolved_wrong=has_wrong,
        )


# 全局单例
default_companion_service = CompanionService()
