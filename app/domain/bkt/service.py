# -*- coding: utf-8 -*-
"""
app/domain/bkt/service.py
学海智导 (Xuehai Zhidao) V2 经典贝叶斯知识追踪 (BKT) 纯数学计算领域服务

职责：
1. 实现确定性、可解释的贝叶斯先验与后验概率更新公式
2. 纯数学计算与内存状态流转，完全解耦外部 IO 与 API 框架
"""

from typing import Optional
from app.domain.bkt.models import (
    BKTParameters,
    DEFAULT_BKT_PARAMS,
    BKTState,
    BKTUpdateResult,
)


def calculate_bkt_update(
    p_l: float,
    is_correct: bool,
    params: Optional[BKTParameters] = None,
) -> float:
    """
    纯函数：计算单次观测（答对 / 答错）后的 BKT 掌握概率更新
    公式：
    1. 观测后验概率 P(L | Obs):
       - 若答对: P(L|corr) = [P(L) * (1-P(S))] / [P(L) * (1-P(S)) + (1-P(L)) * P(G)]
       - 若答错: P(L|inc)  = [P(L) * P(S)]     / [P(L) * P(S)     + (1-P(L)) * (1-P(G))]
    2. 考虑学习转移 P(L_new):
       P(L_new) = P(L | Obs) + (1 - P(L | Obs)) * P(T)
    """
    cfg = params or DEFAULT_BKT_PARAMS
    p_l = max(0.0, min(1.0, float(p_l)))

    p_s = cfg.p_s
    p_g = cfg.p_g
    p_t = cfg.p_t

    if is_correct:
        numerator = p_l * (1.0 - p_s)
        denominator = numerator + (1.0 - p_l) * p_g
    else:
        numerator = p_l * p_s
        denominator = numerator + (1.0 - p_l) * (1.0 - p_g)

    # 极端边界防御
    if denominator <= 0.0:
        p_l_obs = p_l
    else:
        p_l_obs = numerator / denominator

    # 学习转移 (Learning Transition)
    p_l_new = p_l_obs + (1.0 - p_l_obs) * p_t

    # 边界严格钳位
    return max(0.0, min(1.0, p_l_new))


def create_initial_state(
    student_id: str,
    knowledge_id: str,
    params: Optional[BKTParameters] = None,
) -> BKTState:
    """
    工厂函数：创建学生指定知识点的初始状态
    以 P(L0) 作为初试先验，计数器全部归零
    """
    cfg = params or DEFAULT_BKT_PARAMS
    return BKTState(
        student_id=student_id,
        knowledge_id=knowledge_id,
        mastery_probability=cfg.p_l0,
        attempts=0,
        correct_attempts=0,
        incorrect_attempts=0,
        consecutive_correct=0,
        consecutive_incorrect=0,
        last_event_id=None,
        last_updated=None,
    )


def apply_attempt(
    state: BKTState,
    is_correct: bool,
    event_id: str,
    timestamp: str,
    params: Optional[BKTParameters] = None,
) -> BKTUpdateResult:
    """
    应用一次作答观测更新 BKTState，返回演进结果快照与新状态对象
    """
    cfg = params or DEFAULT_BKT_PARAMS
    before_mastery = state.mastery_probability
    after_mastery = calculate_bkt_update(before_mastery, is_correct, cfg)

    new_attempts = state.attempts + 1
    if is_correct:
        new_correct = state.correct_attempts + 1
        new_incorrect = state.incorrect_attempts
        new_consecutive_correct = state.consecutive_correct + 1
        new_consecutive_incorrect = 0
    else:
        new_correct = state.correct_attempts
        new_incorrect = state.incorrect_attempts + 1
        new_consecutive_correct = 0
        new_consecutive_incorrect = state.consecutive_incorrect + 1

    new_state = BKTState(
        student_id=state.student_id,
        knowledge_id=state.knowledge_id,
        mastery_probability=after_mastery,
        attempts=new_attempts,
        correct_attempts=new_correct,
        incorrect_attempts=new_incorrect,
        consecutive_correct=new_consecutive_correct,
        consecutive_incorrect=new_consecutive_incorrect,
        last_event_id=event_id,
        last_updated=timestamp,
    )

    return BKTUpdateResult(
        student_id=state.student_id,
        knowledge_id=state.knowledge_id,
        before_mastery=before_mastery,
        after_mastery=after_mastery,
        is_correct=is_correct,
        event_id=event_id,
        state=new_state,
    )
