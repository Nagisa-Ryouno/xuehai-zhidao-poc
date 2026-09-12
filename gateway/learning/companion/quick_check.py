# -*- coding: utf-8 -*-
"""
gateway.learning.companion.quick_check
======================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-B
轻量快速思维检查服务 (Quick Check Service)

核心定位与边界：
1. 启发式教学互动 (Pedagogical Interaction)，非正式生产测验
2. 绝对不调用 BKT，绝对不产生 QUESTION_ATTEMPT 事件，零状态突变 (Zero Mutation)
3. 纯基于权威 30 考点微卡，题目确定、答案唯一且客观
4. 无论对错，均附带正式微测验验证引导 (verified_quiz_action)
"""

from typing import Dict, List, Optional
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.companion.guided_actions import DeterministicActionBuilder
from gateway.learning.companion.models import (
    ActionType,
    CompanionSafetyMetadata,
    CompanionSuggestedAction,
    QuickCheckOption,
    QuickCheckQuestion,
    QuickCheckResponse,
)


class QuickCheckService:
    """轻量快速思维检查服务（零生产状态修改）"""

    def __init__(self):
        # 预置基于 30 考点微卡核心概念与易错点的快速检查题库
        self._check_bank: Dict[str, Dict] = self._init_check_bank()
        self._questions = self._check_bank

    def _init_check_bank(self) -> Dict[str, Dict]:
        bank = {}
        for kid, card in CONCEPT_CARDS.items():
            check_id = f"qc-{kid}-01"
            # 依据概念卡提炼快速检查问题
            bank[kid] = {
                "check_id": check_id,
                "knowledge_id": kid,
                "knowledge_name": card.knowledge_name,
                "prompt": f"【{card.knowledge_name}】思维自测：下列关于该考点的理解，哪项最准确？",
                "options": [
                    QuickCheckOption(
                        key="A",
                        text=card.one_line_intuition,
                    ),
                    QuickCheckOption(
                        key="B",
                        text=f"容易陷入的误区：{card.common_misconceptions.split('。')[0]}",
                    ),
                    QuickCheckOption(
                        key="C",
                        text="该概念在现实经济中仅存在于极端假设情境，不适用于日常经济生活与商业决策。",
                    ),
                    QuickCheckOption(
                        key="D",
                        text="该考点与微观经济学其他考点没有逻辑关联，是完全孤立的概念。",
                    ),
                ],
                "correct_key": "A",
                "hint": f"复习提示：{card.core_concept[:60]}...",
                "explanation": (
                    f"【正确答案：A】\n"
                    f"核心解析：{card.core_concept}\n"
                    f"注意避坑：{card.common_misconceptions}\n"
                    f"（说明：快速思维检查仅用于辅助互动理解，不计入系统正式掌握度，请前往微测验进行正式测评）"
                ),
            }
        return bank

    def get_quick_check(self, knowledge_id: str) -> Optional[QuickCheckQuestion]:
        """获取指定考点的快速思维检查题目（不暴露答案）"""
        kid = knowledge_id or "K01"
        data = self._check_bank.get(kid)
        if not data:
            return None

        return QuickCheckQuestion(
            check_id=data["check_id"],
            question_id=data["check_id"],
            knowledge_id=data["knowledge_id"],
            knowledge_name=data["knowledge_name"],
            prompt=data["prompt"],
            stem=data["prompt"],
            options=data["options"],
            hint=data.get("hint"),
            concept_summary=data.get("hint") or f"掌握【{data['knowledge_name']}】的核心概念",
        )

    def evaluate_quick_check(
        self,
        student_id: str,
        check_id: str,
        knowledge_id: str,
        selected_option: str,
    ) -> QuickCheckResponse:
        """
        评估学生的快速思维检查作答

        硬性约束：
        - 零 BKT 写入
        - 零 QUESTION_ATTEMPT 生成
        - 零 PathState 修改
        """
        kid = knowledge_id or "K01"
        data = self._check_bank.get(kid)
        if not data or data["check_id"] != check_id:
            # 若 check_id 未匹配，尝试按 kid 查找
            if kid in self._check_bank:
                data = self._check_bank[kid]
            else:
                data = self._check_bank.get("K01")

        correct_key = data["correct_key"]
        user_choice = selected_option.strip().upper()
        is_correct = (user_choice == correct_key)

        verified_action = CompanionSuggestedAction(
            action_id=f"act-{kid}-verify-quiz",
            action_type=ActionType.TARGETED_PRACTICE,
            label="✏️ 在正式测验中验证",
            title="✏️ 在正式测验中验证",
            description="快速思维检查完成，通过正式测验检验掌握成效并更新系统掌握度",
            knowledge_id=kid,
            target_knowledge_id=kid,
            route_destination=f"/student/quiz/{kid}",
            reason="快速思维检查完成，通过正式测验检验掌握成效并更新系统掌握度",
            source_reason="快速思维检查完成，通过正式测验检验掌握成效并更新系统掌握度",
            badge="正式测验",
        )

        explanation_prefix = "👏 理解准确！" if is_correct else "💡 思维有些偏差，没关系！"
        full_explanation = f"{explanation_prefix}\n{data['explanation']}"
        key_takeaway = data.get("hint") or f"掌握【{data['knowledge_name']}】的核心概念"

        safety = CompanionSafetyMetadata(
            allow_production_decision=False,
            sanitized=True,
            offline_mode=True,
            context_source="authoritative_concept_cards",
            redactions_applied=["no_bkt_write", "no_production_event"],
        )

        return QuickCheckResponse(
            check_id=check_id,
            knowledge_id=kid,
            is_correct=is_correct,
            correct_option=correct_key,
            explanation=full_explanation,
            key_takeaway=key_takeaway,
            verified_quiz_action=verified_action,
            suggested_actions=[verified_action],
            safety=safety,
        )


# 全局单例
default_quick_check_service = QuickCheckService()
