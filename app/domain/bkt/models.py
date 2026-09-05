# -*- coding: utf-8 -*-
"""
app/domain/bkt/models.py
学海智导 (Xuehai Zhidao) V2 经典贝叶斯知识追踪 (BKT) 纯领域模型

纯领域模型实体与值对象：
- BKTParameters: BKT 四大参数配置与先验边界校验
- DEFAULT_BKT_PARAMS: 默认参数全局单例
- BKTState: 单学生单知识点认知状态实体
- BKTUpdateResult: 单次作答更新结果值对象
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
