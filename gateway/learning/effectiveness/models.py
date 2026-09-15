# -*- coding: utf-8 -*-
"""
gateway.learning.effectiveness.models
=====================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-D
学习会话生命周期与学习效果评估领域模型 (Learning Session & Effectiveness Models)

设计规范与安全红线：
1. BKT 唯一事实源：`initial_mastery` 在 Session 创建时权威读取快照，`final_mastery` 在 Session 完成时重新从服务端读取；
2. 零客户端造假：客户端绝对不能上传或篡改 `final_mastery` 与 `mastery_delta`；
3. 零生产状态突变：模型与评估过程为纯分析模型，绝对不反向修改 `bkt_states.json`；
4. 语言零黑话 (No Jargon)：面向学生的反馈文案使用温和鼓舞人本表述，严禁暴露底层算法术语与虚假因果承诺。
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class SessionStatus(str, Enum):
    """学习会话生命周期状态"""
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class EffectivenessStatus(str, Enum):
    """学习效果分类标识 (确定性分类，非因果判定)"""
    STRONG_PROGRESS = "STRONG_PROGRESS"          # 掌握度净增 >= +0.15 (+15%)
    MEANINGFUL_PROGRESS = "MEANINGFUL_PROGRESS"  # +0.05 <= 掌握度净增 < +0.15 (+5% ~ +15%)
    STABLE = "STABLE"                            # -0.05 < 掌握度净增 < +0.05 (平稳巩固)
    NEEDS_MORE_SUPPORT = "NEEDS_MORE_SUPPORT"    # 掌握度净增 <= -0.05 (答错或认知受阻)


class LearningSession(BaseModel):
    """学生单次完整学习过程会话实体"""
    session_id: str = Field(default_factory=lambda: f"sess-{uuid.uuid4().hex[:12]}")
    student_id: str
    knowledge_id: str
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None

    # 掌握度状态快照 (必须服务端权威读取与计算，四位小数精度)
    initial_mastery: float = Field(..., description="会话创建时服务端权威快照的掌握度")
    final_mastery: Optional[float] = Field(default=None, description="会话完成时服务端权威读取的掌握度")
    mastery_delta: Optional[float] = Field(default=None, description="服务端计算的掌握度净增量 (final - initial)")

    # 资源流转与完成跟踪
    resource_ids: List[str] = Field(default_factory=list, description="本次推荐或计划研读的学习资源清单")
    completed_resource_ids: List[str] = Field(default_factory=list, description="本次实际标记完成的学习资源清单")

    # 微测验关联
    quiz_question_id: Optional[str] = Field(default=None, description="本次参与的官方微测验题目ID")
    quiz_result: Optional[bool] = Field(default=None, description="微测验作答结果是否正确")

    status: SessionStatus = Field(default=SessionStatus.IN_PROGRESS, description="会话当前流转状态")
    notes: Optional[str] = Field(default=None, description="会话辅助备注")

    @field_validator("initial_mastery")
    @classmethod
    def validate_initial_mastery(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"初始掌握度必须在 [0.0, 1.0] 区间，当前值: {v}")
        return round(float(v), 4)

    @field_validator("final_mastery")
    @classmethod
    def validate_final_mastery(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v < 0.0 or v > 1.0:
                raise ValueError(f"最终掌握度必须在 [0.0, 1.0] 区间，当前值: {v}")
            return round(float(v), 4)
        return None

    @field_validator("mastery_delta")
    @classmethod
    def validate_mastery_delta(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            return round(float(v), 4)
        return None


class LearningSessionCreateRequest(BaseModel):
    """创建学习会话请求载荷"""
    student_id: str
    knowledge_id: str
    resource_ids: Optional[List[str]] = Field(default_factory=list)


class LearningSessionCompleteRequest(BaseModel):
    """完成学习会话请求载荷 (客户端禁止提供 final_mastery，任何客户端伪造字段均被无视)"""
    student_id: str
    completed_resource_ids: Optional[List[str]] = Field(default_factory=list)
    quiz_question_id: Optional[str] = None
    quiz_result: Optional[bool] = None


class LearningEffectiveness(BaseModel):
    """单次学习会话效果客观评价实体 (只读分析)"""
    session_id: str
    student_id: str
    knowledge_id: str
    initial_mastery: float
    final_mastery: float
    mastery_delta: float
    effectiveness_status: EffectivenessStatus
    feedback_title: str
    feedback_message: str
    completed_resources_count: int
    quiz_attempted: bool
    quiz_correct: Optional[bool] = None
    suggested_next_action: str


class ResourceEffectivenessSignal(BaseModel):
    """考点/资源历史学习表现信号 (需满足最小样本约束 MIN_SAMPLE_SIZE)"""
    knowledge_id: str
    sample_count: int
    positive_count: int
    stable_count: int
    negative_count: int
    average_delta: Optional[float] = None
    is_statistically_significant: bool = False
    observation_signal: str = "暂无足够历史样本，仅以单次会话为准"


class KnowledgeEffectivenessResponse(BaseModel):
    """考点学习效果综合查询响应"""
    student_id: str
    knowledge_id: str
    latest_session: Optional[LearningSession] = None
    effectiveness: Optional[LearningEffectiveness] = None
    historical_signal: Optional[ResourceEffectivenessSignal] = None


class SessionCompleteResponse(BaseModel):
    """完成会话响应载荷，聚合会话信息与效果分析"""
    session: LearningSession
    effectiveness: LearningEffectiveness


