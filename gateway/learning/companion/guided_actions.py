# -*- coding: utf-8 -*-
"""
gateway.learning.companion.guided_actions
=========================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-B
确定性推荐行动构建器 (Deterministic Action Builder)

核心原则：
1. AI 不自由生成 Action；Action 严格由系统事实驱动与白名单控制
2. 纯函数、无随机、无副作用 (Zero Mutation)
3. 遵循 Case A ~ E 确定性规则矩阵
4. 杜绝技术黑话，理由 (reason) 仅陈述客观系统事实
"""

from typing import List, Optional, Set
from gateway.learning.companion.models import ActionType, CompanionSuggestedAction

VALID_ACTION_TYPES: Set[ActionType] = set(ActionType)


class DeterministicActionBuilder:
    """确定性学习行动生成器"""

    @staticmethod
    def validate_action(action: CompanionSuggestedAction) -> bool:
        """校验行动是否严格属于白名单，若不合法抛出 ValueError"""
        if action.action_type not in VALID_ACTION_TYPES:
            raise ValueError(f"Action type {action.action_type} 不在法定白名单内")
        return True

    @staticmethod
    def validate_action_whitelist(action: CompanionSuggestedAction) -> bool:
        """校验行动是否严格属于白名单（布尔接口）"""
        return action.action_type in VALID_ACTION_TYPES

    @staticmethod
    def build_actions(
        student_id: str,
        knowledge_id: str,
        mastery: Optional[float] = None,
        has_unresolved_wrong: bool = False,
        consecutive_incorrect: int = 0,
        successors: Optional[List[str]] = None,
        unmastered_successors: Optional[List[str]] = None,
        question_id: Optional[str] = None,
        knowledge_name: Optional[str] = None,
    ) -> List[CompanionSuggestedAction]:
        """
        根据客观学情事实确定性推导白名单学习行动

        规则矩阵 (Cases A ~ E)：
        - Case E: consecutive_incorrect >= 2 -> 连续做错认知受阻 -> 重温概念微卡 + 错题归因复盘
        - Case A: mastery < 0.60 (或初始起步) -> 掌握度薄弱 -> 重新看概念 + 靶向再练一道
        - Case B: 0.60 <= mastery < 0.80 -> 巩固阶段 -> 靶向再练一道 + 重新看概念
        - Case C: mastery >= 0.80 且有未掌握后继 -> 掌握度已达标 -> 攻坚后继考点微测验 + 查看学情进展
        - Case D: mastery >= 0.80 且无后继/图谱终点 -> 查看学情进展 + 拓展进阶探讨
        """
        kid = knowledge_id or "K01"
        succ_list = successors or []
        unmastered_succ = unmastered_successors or []

        # Priority 1 (Case E): 连续做错 >= 2 次，触发认知受阻保护
        if consecutive_incorrect >= 2:
            return [
                CompanionSuggestedAction(
                    action_id=f"act-{kid}-review-remedial",
                    action_type=ActionType.READ_CONCEPT,
                    label="📖 重温概念微卡",
                    title="📖 重温概念微卡",
                    description="该考点已连续受阻，建议重温概念微卡夯实直观理解",
                    knowledge_id=kid,
                    target_knowledge_id=kid,
                    question_id=question_id,
                    target_question_id=question_id,
                    route_destination=f"/student/concept/{kid}",
                    reason="该考点连续答错达到 2 次，先夯实核心要义以防盲目刷题",
                    source_reason="该考点连续答错达到 2 次，先夯实核心要义以防盲目刷题",
                    badge="认知巩固",
                ),
                CompanionSuggestedAction(
                    action_id=f"act-{kid}-wrong-review",
                    action_type=ActionType.REVIEW_WRONG_ANSWERS,
                    label="🔍 错题归因复盘",
                    title="🔍 错题归因复盘",
                    description="查阅近期错因归纳与易混淆概念陷阱",
                    knowledge_id=kid,
                    target_knowledge_id=kid,
                    question_id=question_id,
                    target_question_id=question_id,
                    route_destination="/student/profile/wrong-answers",
                    reason="针对近期高频易错题型进行专项复盘与反思",
                    source_reason="针对近期高频易错题型进行专项复盘与反思",
                    badge="错题查漏",
                ),
            ]

        # 若未提供掌握度，视作初始起步
        f_mastery = float(mastery) if mastery is not None else 0.20

        # Priority 2 (Case A): 掌握度薄弱 (< 0.60)
        if f_mastery < 0.60:
            return [
                CompanionSuggestedAction(
                    action_id=f"act-{kid}-concept-weak",
                    action_type=ActionType.READ_CONCEPT,
                    label="📖 重新看概念",
                    title="📖 重新看概念",
                    description="当前考点处于起步阶段，建议精读微卡核心要点",
                    knowledge_id=kid,
                    target_knowledge_id=kid,
                    route_destination=f"/student/concept/{kid}",
                    reason="当前掌握度处于起步阶段，建议精读微卡核心要点",
                    source_reason="当前掌握度处于起步阶段，建议精读微卡核心要点",
                    badge="重温基础",
                ),
                CompanionSuggestedAction(
                    action_id=f"act-{kid}-quiz-weak",
                    action_type=ActionType.TARGETED_PRACTICE,
                    label="✏️ 靶向再练一道",
                    title="✏️ 靶向再练一道",
                    description="通过微测验检验直观理解，建立第一阶段认知基础",
                    knowledge_id=kid,
                    target_knowledge_id=kid,
                    route_destination=f"/student/quiz/{kid}",
                    reason="通过微测验建立第一阶段认知基础",
                    source_reason="通过微测验建立第一阶段认知基础",
                    badge="基础演练",
                ),
            ]

        # Priority 3 (Case B): 巩固阶段 (0.60 <= mastery < 0.80)
        elif f_mastery < 0.80:
            return [
                CompanionSuggestedAction(
                    action_id=f"act-{kid}-quiz-developing",
                    action_type=ActionType.TARGETED_PRACTICE,
                    label="✏️ 靶向再练一道",
                    title="✏️ 靶向再练一道",
                    description="当前掌握度正在稳步提升，趁热打铁冲刺 80% 达标门槛",
                    knowledge_id=kid,
                    target_knowledge_id=kid,
                    route_destination=f"/student/quiz/{kid}",
                    reason="当前掌握度正在稳步提升，冲刺达标门槛",
                    source_reason="当前掌握度正在稳步提升，冲刺达标门槛",
                    badge="达标攻坚",
                ),
                CompanionSuggestedAction(
                    action_id=f"act-{kid}-concept-developing",
                    action_type=ActionType.READ_CONCEPT,
                    label="📖 重新看概念",
                    title="📖 重新看概念",
                    description="扫除推导逻辑细节盲区，确保掌握度稳定达标",
                    knowledge_id=kid,
                    target_knowledge_id=kid,
                    route_destination=f"/student/concept/{kid}",
                    reason="扫除推导逻辑细节盲区，确保掌握度稳定达标",
                    source_reason="扫除推导逻辑细节盲区，确保掌握度稳定达标",
                    badge="查漏补缺",
                ),
            ]

        # Priority 4 (Case C & D): 掌握度已达标 (mastery >= 0.80)
        else:
            # Case C: 存在未掌握后继考点
            if unmastered_succ:
                next_target = unmastered_succ[0]
                return [
                    CompanionSuggestedAction(
                        action_id=f"act-{next_target}-quiz-successor",
                        action_type=ActionType.TARGETED_PRACTICE,
                        label="✏️ 进阶突破下一考点",
                        title="✏️ 进阶突破下一考点",
                        description=f"当前考点已达标掌握，趁热打铁攻坚进阶考点【{next_target}】",
                        knowledge_id=next_target,
                        target_knowledge_id=next_target,
                        route_destination=f"/student/quiz/{next_target}",
                        reason="当前考点已达标掌握，系统建议向后继考点延伸突破",
                        source_reason="当前考点已达标掌握，系统建议向后继考点延伸突破",
                        badge="进阶挑战",
                    ),
                    CompanionSuggestedAction(
                        action_id=f"act-{kid}-progress-view",
                        action_type=ActionType.VIEW_PROGRESS,
                        label="📊 查看学情进展",
                        title="📊 查看学情进展",
                        description="回顾 30 考点认知全景与当前学习航线",
                        knowledge_id=kid,
                        target_knowledge_id=kid,
                        route_destination="/student/profile/progress",
                        reason="当前考点已达标，查看整体学习进度",
                        source_reason="当前考点已达标，查看整体学习进度",
                        badge="阶段纵览",
                    ),
                ]
            else:
                # Case D: 无后继或全已达标 (终点)
                return [
                    CompanionSuggestedAction(
                        action_id=f"act-{kid}-progress-terminal",
                        action_type=ActionType.VIEW_PROGRESS,
                        label="📊 查看学情进展",
                        title="📊 查看学情进展",
                        description="恭喜达成达标标准！查阅当前图谱全景掌握成效",
                        knowledge_id=kid,
                        target_knowledge_id=kid,
                        route_destination="/student/profile/progress",
                        reason="当前考点已达标掌握，回顾全景学习成效",
                        source_reason="当前考点已达标掌握，回顾全景学习成效",
                        badge="达标达成",
                    ),
                    CompanionSuggestedAction(
                        action_id=f"act-{kid}-discussion-terminal",
                        action_type=ActionType.CONTINUE_DISCUSSION,
                        label="💬 拓展进阶思考",
                        title="💬 拓展进阶思考",
                        description="探讨该考点在宏观经济或现实商业决策中的深度应用",
                        knowledge_id=kid,
                        target_knowledge_id=kid,
                        route_destination="/student/assistant",
                        reason="探讨该考点在后续章节与现实生活中的深层联系",
                        source_reason="探讨该考点在后续章节与现实生活中的深层联系",
                        badge="启发探讨",
                    ),
                ]
