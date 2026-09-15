# -*- coding: utf-8 -*-
"""
gateway.learning.effectiveness.analyzer
=======================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-D
学习效果只读分析器 (Resource Effectiveness Analyzer)

设计规范与红线约束：
1. 纯只读计算：严禁修改 `bkt_states.json`、`learning_path_states.json` 或 `learning_events.jsonl`；
2. 权威 master delta：必须基于服务端读取的客观 BKT 状态，严禁信任客户端传递的任何假掌握度；
3. 不做虚假因果与伪统计：单次会话如实展示客观变化，历史汇总严格施加最小样本约束 (MIN_SAMPLE_SIZE >= 3)；
4. 语言零黑话 (No Jargon)：面向学生文案绝不泄露算法变量。
"""

from typing import List, Optional
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.effectiveness.feedback import default_feedback_service
from gateway.learning.effectiveness.models import (
    EffectivenessStatus,
    LearningEffectiveness,
    LearningSession,
    ResourceEffectivenessSignal,
    SessionStatus,
)

MIN_SAMPLE_SIZE = 3


class ResourceEffectivenessAnalyzer:
    """资源学习效果只读分析引擎"""

    @classmethod
    def analyze_session(
        cls,
        session: LearningSession,
    ) -> LearningEffectiveness:
        """
        根据给定的学习会话进行效果分析与人本评价生成
        """
        # 若 final_mastery 尚未填充，从权威 BKT 库重读
        if session.final_mastery is not None:
            final_mastery = session.final_mastery
        else:
            bkt_state = default_bkt_state_repository.get_state(session.student_id, session.knowledge_id)
            raw_final = float(bkt_state.mastery_probability) if bkt_state else session.initial_mastery
            final_mastery = round(raw_final, 4)

        if session.mastery_delta is not None:
            delta = session.mastery_delta
        else:
            delta = round(final_mastery - session.initial_mastery, 4)

        kp_card = CONCEPT_CARDS.get(session.knowledge_id)
        kp_name = kp_card.knowledge_name if kp_card else session.knowledge_id

        # 调用反馈服务生成人本说明
        eff_status, title, msg, next_action = default_feedback_service.evaluate(
            initial_mastery=session.initial_mastery,
            final_mastery=final_mastery,
            delta=delta,
            quiz_result=session.quiz_result,
            knowledge_name=kp_name,
        )

        return LearningEffectiveness(
            session_id=session.session_id,
            student_id=session.student_id,
            knowledge_id=session.knowledge_id,
            initial_mastery=session.initial_mastery,
            final_mastery=final_mastery,
            mastery_delta=delta,
            effectiveness_status=eff_status,
            feedback_title=title,
            feedback_message=msg,
            completed_resources_count=len(session.completed_resource_ids),
            quiz_attempted=(session.quiz_question_id is not None),
            quiz_correct=session.quiz_result,
            suggested_next_action=next_action,
        )

    @classmethod
    def aggregate_historical_signal(
        cls,
        knowledge_id: str,
        sessions: List[LearningSession],
        student_id: Optional[str] = None,
    ) -> ResourceEffectivenessSignal:
        """
        基于历史会话集合聚合效果信号（严格遵循 MIN_SAMPLE_SIZE 最小样本门槛）
        """
        completed = [
            s for s in sessions
            if s.knowledge_id == knowledge_id
            and s.status == SessionStatus.COMPLETED
            and s.mastery_delta is not None
        ]
        if student_id:
            completed = [s for s in completed if s.student_id == student_id]

        count = len(completed)
        if count == 0:
            return ResourceEffectivenessSignal(
                knowledge_id=knowledge_id,
                sample_count=0,
                positive_count=0,
                stable_count=0,
                negative_count=0,
                average_delta=None,
                is_statistically_significant=False,
                observation_signal="暂无历史学习记录，本次学习将作为起点",
            )

        pos_count = sum(1 for s in completed if s.mastery_delta and s.mastery_delta >= 0.05)
        stable_count = sum(1 for s in completed if s.mastery_delta and -0.05 < s.mastery_delta < 0.05)
        neg_count = sum(1 for s in completed if s.mastery_delta and s.mastery_delta <= -0.05)
        avg_delta = round(sum(s.mastery_delta for s in completed if s.mastery_delta is not None) / count, 4)

        if count < MIN_SAMPLE_SIZE:
            return ResourceEffectivenessSignal(
                knowledge_id=knowledge_id,
                sample_count=count,
                positive_count=pos_count,
                stable_count=stable_count,
                negative_count=neg_count,
                average_delta=avg_delta,
                is_statistically_significant=False,
                observation_signal=f"当前历史样本较少（{count}次），仅以本次单次学习会话为准",
            )

        # 满足最小样本时的宏观观察信号
        if avg_delta >= 0.08:
            signal_text = "该考点学习材料在近期学习中表现优秀，学习后掌握情况显著提升"
        elif avg_delta >= 0:
            signal_text = "该考点学习材料在近期学习中表现稳健，有助于概念巩固"
        else:
            signal_text = "该考点近期作答可能存在认知障碍，建议重点精读例题与微卡"

        return ResourceEffectivenessSignal(
            knowledge_id=knowledge_id,
            sample_count=count,
            positive_count=pos_count,
            stable_count=stable_count,
            negative_count=neg_count,
            average_delta=avg_delta,
            is_statistically_significant=True,
            observation_signal=signal_text,
        )


default_effectiveness_analyzer = ResourceEffectivenessAnalyzer()

