# -*- coding: utf-8 -*-
"""
gateway.evaluation.judge.fake
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G2: 确定性 FakeLLMJudge (离线测试专用 Judge)

核心特性：
1. 100% 离线与确定性：零外部网络、零外部模型依赖，50 次调用字节级严格一致
2. 多质量档位模拟：支持通过 forced_mode 显式注入或基于确定性启发式自动评分
3. 契约合规：严格实现 LLMJudge 接口，只读观察，绝不修改输入对象
"""

import re
from typing import Dict, List, Literal, Optional

from gateway.evaluation.judge.interface import LLMJudge
from gateway.evaluation.judge.models import (
    JudgeCapabilities,
    JudgeDimension,
    JudgeResult,
)
from gateway.models import LearningPromptContext, StructuredAIResponse


class FakeLLMJudge(LLMJudge):
    """
    确定性离线模拟 Judge 实现
    """

    def __init__(
        self,
        name: str = "fake-llm-judge",
        version: str = "v1.0",
        forced_mode: Optional[Literal["HIGH", "MEDIUM", "LOW", "UNCERTAIN", "OFF_TOPIC"]] = None,
        forced_confidence: Optional[float] = None,
        should_fail: bool = False,
        failure_reason: str = "Simulated Judge Error",
    ):
        self._name = name
        self._version = version
        self.forced_mode = forced_mode
        self.forced_confidence = forced_confidence
        self.should_fail = should_fail
        self.failure_reason = failure_reason

    def capabilities(self) -> JudgeCapabilities:
        return JudgeCapabilities(
            supported_dimensions=[d for d in JudgeDimension],
            deterministic=True,
            network_required=False,
            provider_name=self._name,
            version=self._version,
        )

    def evaluate(
        self,
        context: LearningPromptContext,
        response: StructuredAIResponse,
    ) -> JudgeResult:
        if self.should_fail:
            raise RuntimeError(self.failure_reason)

        answer = (response.answer or "").strip()
        sf = context.system_facts

        # 1. 显式模式注入支持（用于单元与回归测试针对性验证）
        if self.forced_mode == "HIGH":
            return JudgeResult(
                judge_version=self._version,
                valid=True,
                overall_score=0.92,
                confidence=self.forced_confidence if self.forced_confidence is not None else 0.95,
                dimension_scores={
                    JudgeDimension.EXPLANATION_DEPTH.value: 0.95,
                    JudgeDimension.PEDAGOGICAL_QUALITY.value: 0.92,
                    JudgeDimension.CONTEXTUAL_RELEVANCE.value: 0.95,
                    JudgeDimension.ACTIONABILITY.value: 0.90,
                    JudgeDimension.CLARITY.value: 0.92,
                    JudgeDimension.EMPATHY.value: 0.88,
                },
                rationale_summary="高质量概念阐释与清晰因果逻辑，学习指导建议非常具体且具有建设性。",
                violations=[],
            )
        elif self.forced_mode == "MEDIUM":
            return JudgeResult(
                judge_version=self._version,
                valid=True,
                overall_score=0.72,
                confidence=self.forced_confidence if self.forced_confidence is not None else 0.85,
                dimension_scores={
                    JudgeDimension.EXPLANATION_DEPTH.value: 0.70,
                    JudgeDimension.PEDAGOGICAL_QUALITY.value: 0.72,
                    JudgeDimension.CONTEXTUAL_RELEVANCE.value: 0.80,
                    JudgeDimension.ACTIONABILITY.value: 0.70,
                    JudgeDimension.CLARITY.value: 0.75,
                    JudgeDimension.EMPATHY.value: 0.65,
                },
                rationale_summary="回答中规中矩，涵盖基本学情但解释深度略显不足，建议人工复核。",
                violations=["EXPLANATION_SHALLOW"],
            )
        elif self.forced_mode == "LOW":
            return JudgeResult(
                judge_version=self._version,
                valid=False,
                overall_score=0.45,
                confidence=self.forced_confidence if self.forced_confidence is not None else 0.85,
                dimension_scores={
                    JudgeDimension.EXPLANATION_DEPTH.value: 0.40,
                    JudgeDimension.PEDAGOGICAL_QUALITY.value: 0.45,
                    JudgeDimension.CONTEXTUAL_RELEVANCE.value: 0.50,
                    JudgeDimension.ACTIONABILITY.value: 0.40,
                    JudgeDimension.CLARITY.value: 0.50,
                    JudgeDimension.EMPATHY.value: 0.50,
                },
                rationale_summary="回答较为敷衍空泛，缺乏实质性学情因果归因与具体行动指导。",
                violations=["POOR_EXPLANATION", "INSUFFICIENT_GUIDANCE"],
            )
        elif self.forced_mode == "UNCERTAIN":
            return JudgeResult(
                judge_version=self._version,
                valid=True,
                overall_score=0.85,
                confidence=self.forced_confidence if self.forced_confidence is not None else 0.55,
                dimension_scores={
                    JudgeDimension.EXPLANATION_DEPTH.value: 0.80,
                    JudgeDimension.PEDAGOGICAL_QUALITY.value: 0.85,
                    JudgeDimension.CONTEXTUAL_RELEVANCE.value: 0.85,
                    JudgeDimension.ACTIONABILITY.value: 0.85,
                    JudgeDimension.CLARITY.value: 0.85,
                    JudgeDimension.EMPATHY.value: 0.80,
                },
                rationale_summary="评分较高但置信度较低（0.55 < 0.70），触发人工复核流程。",
                violations=["LOW_CONFIDENCE"],
            )
        elif self.forced_mode == "OFF_TOPIC":
            return JudgeResult(
                judge_version=self._version,
                valid=False,
                overall_score=0.20,
                confidence=0.90,
                dimension_scores={
                    JudgeDimension.EXPLANATION_DEPTH.value: 0.10,
                    JudgeDimension.PEDAGOGICAL_QUALITY.value: 0.20,
                    JudgeDimension.CONTEXTUAL_RELEVANCE.value: 0.0,
                    JudgeDimension.ACTIONABILITY.value: 0.20,
                    JudgeDimension.CLARITY.value: 0.40,
                    JudgeDimension.EMPATHY.value: 0.30,
                },
                rationale_summary="内容与当前考点完全无关，严重脱线。",
                violations=["OFF_TOPIC"],
            )

        # 2. 确定性启发式自动评分模式
        # (a) 概念相关性 (Contextual Relevance)
        has_kp_ref = (sf.current_knowledge_name in answer) or (sf.current_knowledge_id in answer)
        relevance_score = 0.95 if has_kp_ref else 0.40

        # (b) 解释深度 (Explanation Depth)
        # 考察字数、因果词汇、公式/经济学术语提及
        causal_tokens = ["因为", "原因", "差距", "目标", "分析", "由于", "公式", "推导"]
        causal_count = sum(1 for t in causal_tokens if t in answer)
        if len(answer) > 100 and causal_count >= 3:
            depth_score = 0.92
        elif len(answer) > 50 and causal_count >= 1:
            depth_score = 0.82
        elif len(answer) > 25:
            depth_score = 0.68
        else:
            depth_score = 0.40

        # (c) 教学质量 (Pedagogical Quality)
        pedagogical_tokens = ["建议", "首先", "其次", "重点", "理清", "辨析", "结合"]
        ped_count = sum(1 for t in pedagogical_tokens if t in answer)
        pedagogical_score = min(0.95, 0.65 + ped_count * 0.10)

        # (d) 行动指导性 (Actionability)
        action_tokens = ["复习", "练习", "做题", "攻坚", "做测验", "微测验", "回顾"]
        act_count = sum(1 for t in action_tokens if t in answer)
        actionability_score = min(0.95, 0.60 + act_count * 0.12)

        # (e) 清晰度 (Clarity)
        clarity_score = 0.90 if len(answer) >= 30 else 0.60

        # (f) 共情与鼓励 (Empathy)
        empathy_tokens = ["加油", "同学你好", "恭喜", "不要气馁", "继续保持", "太棒了"]
        has_empathy = any(t in answer for t in empathy_tokens)
        empathy_score = 0.88 if has_empathy else 0.70

        # 综合加权平均 (加权计算)
        weights = {
            JudgeDimension.EXPLANATION_DEPTH: 0.25,
            JudgeDimension.PEDAGOGICAL_QUALITY: 0.25,
            JudgeDimension.CONTEXTUAL_RELEVANCE: 0.20,
            JudgeDimension.ACTIONABILITY: 0.15,
            JudgeDimension.CLARITY: 0.10,
            JudgeDimension.EMPATHY: 0.05,
        }
        dim_scores = {
            JudgeDimension.EXPLANATION_DEPTH.value: depth_score,
            JudgeDimension.PEDAGOGICAL_QUALITY.value: pedagogical_score,
            JudgeDimension.CONTEXTUAL_RELEVANCE.value: relevance_score,
            JudgeDimension.ACTIONABILITY.value: actionability_score,
            JudgeDimension.CLARITY.value: clarity_score,
            JudgeDimension.EMPATHY.value: empathy_score,
        }

        overall_score = round(
            sum(dim_scores[dim.value] * w for dim, w in weights.items()),
            2
        )

        confidence = 0.90 if self.forced_confidence is None else self.forced_confidence
        valid = (overall_score >= 0.60)

        violations: List[str] = []
        if overall_score < 0.60:
            violations.append("LOW_JUDGE_SCORE")
        if depth_score < 0.60:
            violations.append("INSUFFICIENT_DEPTH")

        rationale = f"自动综合教学评分 {overall_score:.2f} (深度={depth_score:.2f}, 教学={pedagogical_score:.2f}, 相关={relevance_score:.2f}, 行动={actionability_score:.2f})"

        return JudgeResult(
            judge_version=self._version,
            valid=valid,
            overall_score=overall_score,
            confidence=confidence,
            dimension_scores=dim_scores,
            rationale_summary=rationale,
            violations=violations,
        )
