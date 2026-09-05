# -*- coding: utf-8 -*-
"""
bkt_service.py
学海智导 (Xuehai Zhidao) V2 经典贝叶斯知识追踪 (BKT) 纯数学服务层

职责：
1. 维护标准 BKT 四参数模型 (P(L0), P(T), P(G), P(S))
2. 实现确定性、可解释的贝叶斯先验与后验后验概率更新公式
3. 严格区分「表面正确率 (accuracy)」与「潜在掌握概率 (mastery_probability)」
4. 纯数学计算与内存状态流转，完全解耦外部 IO 与 API 框架
"""

from typing import Optional
from pydantic import BaseModel, Field, model_validator


class BKTParameters(BaseModel):
    """
    经典 BKT 四大参数配置
    - p_l0: 初始先验掌握概率 P(L0)
    - p_t : 知识学习转移概率 P(T) (未掌握 -> 掌握)
    - p_g : 猜测概率 P(G) (未掌握状态下猜对的概率)
    - p_s : 失误概率 P(S) (已掌握状态下失误答错的概率)
    """
    p_l0: float = Field(default=0.20, description="初始先验掌握概率 P(L0)")
    p_t: float = Field(default=0.10, description="学习转移概率 P(T)")
    p_g: float = Field(default=0.20, description="猜测概率 P(G)")
    p_s: float = Field(default=0.10, description="失误概率 P(S)")

    @model_validator(mode="after")
    def validate_bkt_probabilities(self) -> "BKTParameters":
        for name in ["p_l0", "p_t", "p_g", "p_s"]:
            val = getattr(self, name)
            if not (0.0 < val < 1.0):
                raise ValueError(f"BKT 参数 {name}={val} 必须严格处于 (0, 1) 开区间内")

        # BKT 可识别性 (Identifiability) 条件：P(G) + P(S) < 1.0
        # 若 P(G) + P(S) >= 1.0，则说明答对信号与答错信号倒挂或无信息增益
        if self.p_g + self.p_s >= 1.0:
            raise ValueError(
                f"BKT 参数违反可识别性条件: P(G) + P(S) = {self.p_g + self.p_s:.4f} >= 1.0"
            )
        return self


DEFAULT_BKT_PARAMS = BKTParameters()


class BKTState(BaseModel):
    """
    学生单个知识点的当前 BKT 认知状态与学习行为统计
    """
    student_id: str = Field(..., description="学生唯一编号")
    knowledge_id: str = Field(..., description="知识点编号")
    mastery_probability: float = Field(..., description="当前掌握概率 P(L) ∈ [0, 1]")
    attempts: int = Field(default=0, ge=0, description="累计作答次数")
    correct_attempts: int = Field(default=0, ge=0, description="答对次数")
    incorrect_attempts: int = Field(default=0, ge=0, description="答错次数")
    consecutive_correct: int = Field(default=0, ge=0, description="连续答对次数")
    consecutive_incorrect: int = Field(default=0, ge=0, description="连续答错次数")
    last_event_id: Optional[str] = Field(default=None, description="最近触发更新的学习事件 ID")
    last_updated: Optional[str] = Field(default=None, description="最近更新时间戳 ISO 8601")


class BKTUpdateResult(BaseModel):
    """
    一次 BKT 状态演进的明细快照
    """
    student_id: str
    knowledge_id: str
    before_mastery: float
    after_mastery: float
    is_correct: bool
    event_id: str
    state: BKTState


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
