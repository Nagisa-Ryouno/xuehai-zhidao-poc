# -*- coding: utf-8 -*-
"""
gateway.evaluation.judge
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G2: LLM Judge 抽象与多源评估融合架构
"""

from gateway.evaluation.judge.models import (
    JudgeDimension,
    JudgeDecision,
    JudgeFailureClass,
    JudgeScore,
    JudgeResult,
    JudgeCapabilities,
    EvaluationContextProjection,
    FinalEvaluationResult,
)
from gateway.evaluation.judge.interface import LLMJudge
from gateway.evaluation.judge.fake import FakeLLMJudge
from gateway.evaluation.judge.prompt import (
    build_evaluation_context,
    build_judge_prompt,
)
from gateway.evaluation.judge.adapter import CircuitBreaker, CircuitState, JudgeAdapter
from gateway.evaluation.judge.fusion import EvaluationFusionEngine
from gateway.evaluation.judge.real import RealLLMJudge, JUDGE_PROMPT_VERSION
from gateway.evaluation.judge.config import (
    JudgeSettings,
    get_judge_settings,
    build_judge_transport,
)

__all__ = [
    "JudgeDimension",
    "JudgeDecision",
    "JudgeFailureClass",
    "JudgeScore",
    "JudgeResult",
    "JudgeCapabilities",
    "EvaluationContextProjection",
    "FinalEvaluationResult",
    "LLMJudge",
    "FakeLLMJudge",
    "RealLLMJudge",
    "JUDGE_PROMPT_VERSION",
    "build_evaluation_context",
    "build_judge_prompt",
    "CircuitState",
    "CircuitBreaker",
    "JudgeAdapter",
    "EvaluationFusionEngine",
    "JudgeSettings",
    "get_judge_settings",
    "build_judge_transport",
]


