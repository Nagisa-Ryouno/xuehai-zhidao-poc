# -*- coding: utf-8 -*-
"""
gateway.learning.companion.context
==================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-A
AI 学习伙伴只读上下文构建器与安全清洗层 (Companion Context Builder)

核心安全不变量：
1. 只读探针：仅从权威微卡库、题库、进展服务与路线服务读取客观事实
2. 白名单清洗：严格剔除一切凭据、Token、内部系统路径与未授权信息
3. 杜绝幻觉：以权威题库与概念微卡为唯一基准事实 (Ground Truth)
"""

import copy
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.services.knowledge_graph_service import knowledge_graph_service
from app.services.student_service import student_service
from gateway.content.concept_cards import CONCEPT_CARDS, ConceptMicroCard
from gateway.content.quiz_bank import get_question_by_id, QuizQuestionInternal
from gateway.learning.analytics import default_analytics_service
from gateway.learning.path_generation import default_dynamic_path_generator
from gateway.learning.companion.models import (
    CompanionContextMetadata,
    CompanionMode,
    CompanionSession,
)


class CompanionContextBuilder:
    """学习伙伴只读上下文构建器"""

    # 允许透传给 Prompt 的客观事实白名单键
    ALLOWED_FACT_KEYS = {
        "student_id",
        "student_name",
        "learning_goal",
        "major",
        "grade",
        "knowledge_id",
        "knowledge_name",
        "chapter",
        "mastery",
        "mastery_status",
        "prerequisites",
        "one_line_intuition",
        "core_concept",
        "simple_example",
        "common_misconceptions",
        "learning_objective",
        "question_id",
        "stem",
        "options",
        "student_choice",
        "correct_answer",
        "explanation",
        "mastery_count",
        "developing_count",
        "weak_count",
        "wrong_count",
        "recommendations",
    }

    # 严格禁止泄露的敏感关键词
    SENSITIVE_PATTERNS = [
        "api_key",
        "token",
        "secret",
        "password",
        "credential",
        "bkt_states_file",
        "learning_events_file",
        "system_prompt",
        "private_key",
    ]

    def resolve_student(self, student_id: str) -> Optional[Dict[str, Any]]:
        """安全解析学生基本学籍与目标信息"""
        if not student_id:
            return None
        info = default_analytics_service._get_student_info(student_id)
        if info:
            return info
        try:
            profile = student_service.get_student_profile(student_id)
            if profile:
                st = profile.get("student", {})
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

    def get_knowledge_prerequisites(self, knowledge_id: str) -> List[str]:
        """获取指定考点的前置依赖考点"""
        try:
            nodes = knowledge_graph_service.get_nodes()
            for node in nodes:
                if node.get("id") == knowledge_id or node.get("knowledge_id") == knowledge_id:
                    prereqs = node.get("prerequisites", [])
                    if isinstance(prereqs, list):
                        return prereqs
        except Exception:
            pass
        return []

    def get_student_knowledge_mastery(self, student_id: str, knowledge_id: str) -> Tuple[float, str]:
        """获取学生在指定考点的客观掌握度与状态"""
        try:
            prog = default_analytics_service.get_student_progress(student_id)
            if prog and prog.knowledge_point_masteries:
                for item in prog.knowledge_point_masteries:
                    if item.knowledge_id == knowledge_id:
                        status_str = item.status or ("已掌握" if item.state == "MASTERED" else "发展中" if item.state == "DEVELOPING" else "薄弱")
                        return (item.mastery, status_str)
        except Exception:
            pass
        return (0.20, "薄弱")

    def build_concept_context(
        self, student_id: str, knowledge_id: str
    ) -> Tuple[CompanionContextMetadata, Dict[str, Any], List[str]]:
        """构建『概念精讲』模式只读上下文"""
        student_info = self.resolve_student(student_id)
        if not student_info:
            raise ValueError(f"找不到学生档案：{student_id}")

        if knowledge_id not in CONCEPT_CARDS:
            raise ValueError(f"找不到指定考点微卡：{knowledge_id}")

        card: ConceptMicroCard = CONCEPT_CARDS[knowledge_id]
        mastery_prob, mastery_status = self.get_student_knowledge_mastery(student_id, knowledge_id)
        prereqs = self.get_knowledge_prerequisites(knowledge_id)

        meta = CompanionContextMetadata(
            student_id=student_id,
            knowledge_id=knowledge_id,
            knowledge_name=card.knowledge_name,
            chapter=card.chapter,
            mastery=mastery_prob,
            mastery_status=mastery_status,
            prerequisites=prereqs,
            learning_goal=student_info.get("learning_goal"),
        )

        facts = {
            "student_id": student_id,
            "student_name": student_info.get("student_name", student_id),
            "learning_goal": student_info.get("learning_goal"),
            "knowledge_id": knowledge_id,
            "knowledge_name": card.knowledge_name,
            "chapter": card.chapter,
            "mastery": mastery_prob,
            "mastery_status": mastery_status,
            "prerequisites": prereqs,
            "one_line_intuition": card.one_line_intuition,
            "core_concept": card.core_concept,
            "simple_example": card.simple_example,
            "common_misconceptions": card.common_misconceptions,
            "learning_objective": card.learning_objective,
        }

        referenced_facts = [
            f"考点归属：{knowledge_id} {card.knowledge_name}（所属章节：{card.chapter}）",
            f"直观理解：{card.one_line_intuition}",
            f"核心要义：{card.core_concept}",
            f"典型生活案例：{card.simple_example}",
            f"考试高频易错：{card.common_misconceptions}",
            f"当前学生认知阶段：{mastery_status} (掌握度指数: {mastery_prob:.2f})",
        ]

        return meta, self.sanitize_facts(facts), referenced_facts

    def build_wrong_answer_context(
        self, student_id: str, question_id: str, knowledge_id: Optional[str] = None
    ) -> Tuple[CompanionContextMetadata, Dict[str, Any], List[str]]:
        """构建『错题剖析』模式只读上下文"""
        student_info = self.resolve_student(student_id)
        if not student_info:
            raise ValueError(f"找不到学生档案：{student_id}")

        question: Optional[QuizQuestionInternal] = get_question_by_id(question_id)
        if not question:
            raise ValueError(f"找不到指定题目：{question_id}")

        k_id = knowledge_id or question.knowledge_id
        card = CONCEPT_CARDS.get(k_id)
        card_name = card.knowledge_name if card else k_id
        chapter = card.chapter if card else "微观经济学基础"

        # 查找学生的真实作答记录
        student_choice = "未作答"
        try:
            wrong_resp = default_analytics_service.get_student_wrong_answers(student_id)
            if wrong_resp and wrong_resp.wrong_answers:
                for w in wrong_resp.wrong_answers:
                    if w.question_id == question_id:
                        student_choice = w.student_answer
                        break
        except Exception:
            pass

        mastery_prob, mastery_status = self.get_student_knowledge_mastery(student_id, k_id)

        meta = CompanionContextMetadata(
            student_id=student_id,
            knowledge_id=k_id,
            knowledge_name=card_name,
            chapter=chapter,
            mastery=mastery_prob,
            mastery_status=mastery_status,
            question_id=question_id,
            learning_goal=student_info.get("learning_goal"),
        )

        options_map = {opt.key: opt.text for opt in question.options}
        facts = {
            "student_id": student_id,
            "student_name": student_info.get("student_name", student_id),
            "knowledge_id": k_id,
            "knowledge_name": card_name,
            "chapter": chapter,
            "question_id": question_id,
            "stem": question.stem,
            "options": options_map,
            "student_choice": student_choice,
            "correct_answer": question.answer,
            "explanation": question.explanation,
            "common_misconceptions": card.common_misconceptions if card else "",
            "mastery_status": mastery_status,
        }

        referenced_facts = [
            f"错题题号：{question_id}（考点：{k_id} {card_name}）",
            f"题干：{question.stem}",
            f"选项：{'; '.join([f'{k}. {v}' for k, v in options_map.items()])}",
            f"学生作答选项：{student_choice}",
            f"官方标准答案：{question.answer}",
            f"官方解析核心逻辑：{question.explanation}",
        ]

        return meta, self.sanitize_facts(facts), referenced_facts

    def build_learning_summary_context(
        self, student_id: str
    ) -> Tuple[CompanionContextMetadata, Dict[str, Any], List[str]]:
        """构建『阶段总结』模式只读上下文"""
        student_info = self.resolve_student(student_id)
        if not student_info:
            raise ValueError(f"找不到学生档案：{student_id}")

        prog = default_analytics_service.get_student_progress(student_id)
        wrong_resp = default_analytics_service.get_student_wrong_answers(student_id)
        goal = student_info.get("learning_goal") or "微观经济学期末冲刺"
        try:
            dynamic_route = default_dynamic_path_generator.generate_route(student_id, goal=goal)
        except Exception:
            dynamic_route = None

        if prog:
            mastery_count = prog.mastered_count
            developing_count = prog.developing_count
            weak_count = prog.reinforcement_count + prog.unstudied_count
        else:
            mastery_count = 0
            developing_count = 0
            weak_count = 30

        wrong_count = wrong_resp.total_wrong if wrong_resp else 0

        recommendations = []
        if dynamic_route and dynamic_route.steps:
            for step in dynamic_route.steps[:3]:
                recommendations.append(f"{step.knowledge_id} {step.knowledge_name}")

        meta = CompanionContextMetadata(
            student_id=student_id,
            learning_goal=student_info.get("learning_goal"),
            mastery_status=f"已掌握 {mastery_count} / 待巩固 {weak_count}",
        )

        facts = {
            "student_id": student_id,
            "student_name": student_info.get("student_name", student_id),
            "learning_goal": student_info.get("learning_goal"),
            "mastery_count": mastery_count,
            "developing_count": developing_count,
            "weak_count": weak_count,
            "wrong_count": wrong_count,
            "recommendations": recommendations,
        }

        referenced_facts = [
            f"学生阶段学习目标：{student_info.get('learning_goal', '微观经济学期末冲刺')}",
            f"30 考点全景掌握分布：已掌握 {mastery_count} 个，发展中 {developing_count} 个，薄弱待突破 {weak_count} 个",
            f"累计待攻克错题：共 {wrong_count} 道错题记录",
            f"自适应引擎推荐下一步攻坚考点：{', '.join(recommendations) if recommendations else '依据知识图谱主线自主学习'}",
        ]

        return meta, self.sanitize_facts(facts), referenced_facts

    def build_conversation_context(
        self,
        student_id: str,
        session: CompanionSession,
        message: Optional[str] = None,
        knowledge_id: Optional[str] = None,
    ) -> Tuple[CompanionContextMetadata, Dict[str, Any], List[str]]:
        """构建『自由讨论』与连续多轮对话只读上下文"""
        student_info = self.resolve_student(student_id)
        if not student_info:
            raise ValueError(f"找不到学生档案：{student_id}")

        target_kid = knowledge_id or session.last_knowledge_id or "K01"
        card = CONCEPT_CARDS.get(target_kid)
        card_name = card.knowledge_name if card else target_kid
        chapter = card.chapter if card else "微观经济学基础"
        mastery_prob, mastery_status = self.get_student_knowledge_mastery(student_id, target_kid)

        meta = CompanionContextMetadata(
            student_id=student_id,
            knowledge_id=target_kid,
            knowledge_name=card_name,
            chapter=chapter,
            mastery=mastery_prob,
            mastery_status=mastery_status,
            learning_goal=student_info.get("learning_goal"),
        )

        # 提取最近最多 5 轮 (10 条消息) 对话历史
        history_msgs = [
            {"role": m.role, "content": m.content}
            for m in session.messages[-10:]
        ]

        facts = {
            "student_id": student_id,
            "student_name": student_info.get("student_name", student_id),
            "knowledge_id": target_kid,
            "knowledge_name": card_name,
            "chapter": chapter,
            "mastery": mastery_prob,
            "mastery_status": mastery_status,
            "one_line_intuition": card.one_line_intuition if card else "",
            "core_concept": card.core_concept if card else "",
            "common_misconceptions": card.common_misconceptions if card else "",
            "dialogue_history": history_msgs,
        }

        referenced_facts = [
            f"当前聚焦考点：{target_kid} {card_name}",
            f"所属章节：{chapter}",
            f"当前认知阶段：{mastery_status} (掌握度指数: {mastery_prob:.2f})",
        ]

        return meta, self.sanitize_facts(facts), referenced_facts

    def sanitize_facts(self, raw_facts: Dict[str, Any]) -> Dict[str, Any]:
        """严格白名单清洗与脱敏：绝不泄露敏感工程凭据与内部属性"""
        sanitized: Dict[str, Any] = {}
        for k, v in raw_facts.items():
            # 1. 键名必须在白名单内或属于合法的上下文辅助键
            if k not in self.ALLOWED_FACT_KEYS and k != "dialogue_history":
                continue

            # 2. 检查键名与值是否含有敏感 pattern
            k_lower = str(k).lower()
            if any(pattern in k_lower for pattern in self.SENSITIVE_PATTERNS):
                continue

            if isinstance(v, str):
                v_lower = v.lower()
                if any(pattern in v_lower for pattern in self.SENSITIVE_PATTERNS):
                    sanitized[k] = "[REDACTED_CONFIDENTIAL]"
                    continue

            sanitized[k] = copy.deepcopy(v)

        return sanitized


# 全局单例
default_companion_context_builder = CompanionContextBuilder()
