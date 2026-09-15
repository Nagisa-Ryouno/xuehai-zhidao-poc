# -*- coding: utf-8 -*-
"""
gateway.learning.effectiveness.feedback
=======================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-D
学习效果反馈与下一步建议生成服务 (Resource Feedback Service)

设计规范与红线：
1. 时间关联而非虚假因果：绝不说“因为你看了材料所以提升了”，使用“完成本次学习后，你的掌握情况从 A% 变为 B%”；
2. 答对不等于完全掌握：即使 quiz_result=True，只要最终掌握度 < 0.80，严禁宣称“已彻底掌握”；
3. 杜绝工程底层黑话 (No Jargon)：面向学生使用通俗鼓舞人本表述，严禁暴露算法细节；
4. 绝对确定性：相同数值输入保证产生一致的文案与下一步动作映射。
"""

from typing import Dict, Tuple
from gateway.learning.effectiveness.models import EffectivenessStatus


class ResourceFeedbackService:
    """资源学习效果与人本反馈生成服务"""

    @classmethod
    def evaluate(
        cls,
        initial_mastery: float,
        final_mastery: float,
        delta: float,
        quiz_result: bool | None = None,
        knowledge_name: str | None = None,
    ) -> Tuple[EffectivenessStatus, str, str, str]:
        """
        根据前后掌握度与作答事实生成反馈
        返回：(effectiveness_status, feedback_title, feedback_message, suggested_next_action)
        """
        f_init = round(float(initial_mastery), 4)
        f_final = round(float(final_mastery), 4)
        f_delta = round(float(delta), 4)

        init_pct = f"{round(f_init * 100, 1)}%"
        final_pct = f"{round(f_final * 100, 1)}%"
        kp_label = f"「{knowledge_name}」" if knowledge_name else "该考点"

        # ---------------------------------------------------------------------
        # 1. 效果等级划分 (4 阶确定性阈值)
        # ---------------------------------------------------------------------
        if f_delta >= 0.15:
            status = EffectivenessStatus.STRONG_PROGRESS
            title = "这次学习很有收获"
            if f_final >= 0.80:
                msg = f"完成本次学习后，你在{kp_label}的掌握情况从 {init_pct} 跃升到了 {final_pct}，已成功达成掌握标准！"
                next_action = "NEXT_KNOWLEDGE"
            else:
                msg = f"完成本次学习后，你在{kp_label}的掌握情况从 {init_pct} 提升到了 {final_pct}，理解更加深入透彻。建议再练一道巩固优势。"
                next_action = "PRACTICE_AGAIN"

        elif f_delta >= 0.05:
            status = EffectivenessStatus.MEANINGFUL_PROGRESS
            title = "正在稳步巩固"
            if f_final >= 0.80:
                msg = f"完成本次学习后，你在{kp_label}的掌握情况稳步上升到了 {final_pct}，顺利达标！"
                next_action = "NEXT_KNOWLEDGE"
            else:
                msg = f"完成本次学习后，你在{kp_label}的掌握情况从 {init_pct} 稳步上升到了 {final_pct}，核心概念基础已经更扎实了。"
                next_action = "PRACTICE_AGAIN"

        elif f_delta > -0.05:
            status = EffectivenessStatus.STABLE
            title = "这次主要完成了巩固"
            if f_final >= 0.80:
                msg = f"完成本次学习后，你在{kp_label}的高掌握状态稳定保持在 {final_pct}，发挥很平稳。"
                next_action = "NEXT_KNOWLEDGE"
            else:
                msg = f"完成本次学习后，你在{kp_label}的掌握情况平稳保持在 {final_pct}。知识状态很稳定，建议继续做针对性练习进一步攻坚。"
                next_action = "PRACTICE_AGAIN"

        else:
            status = EffectivenessStatus.NEEDS_MORE_SUPPORT
            title = "这一部分还需要继续梳理"
            msg = f"完成本次学习后，你在{kp_label}的掌握情况出现小幅波动（当前为 {final_pct}）。别灰心，建议重新温习考点微卡，排查易错陷阱后再试一次。"
            next_action = "REVIEW_CONCEPT"

        return status, title, msg, next_action


default_feedback_service = ResourceFeedbackService()

