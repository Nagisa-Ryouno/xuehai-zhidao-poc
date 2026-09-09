# -*- coding: utf-8 -*-
"""
gateway.tests.test_judge_fusion
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G2: 多源评估融合决策契约测试 (GJF1 ~ GJF10)
"""

import pytest

from gateway.evaluation.judge.fusion import EvaluationFusionEngine
from gateway.evaluation.judge.models import (
    FinalEvaluationResult,
    JudgeDecision,
    JudgeFailureClass,
    JudgeResult,
)
from gateway.evaluation.models import SemanticValidationResult


@pytest.fixture
def fusion_engine() -> EvaluationFusionEngine:
    return EvaluationFusionEngine()


@pytest.fixture
def pass_deterministic() -> SemanticValidationResult:
    return SemanticValidationResult(
        valid=True,
        factual_consistency=True,
        context_relevance=True,
        policy_compliant=True,
        explanation_quality=True,
        actionability=True,
        violations=[],
        scores={
            "policy_compliance": 1.0,
            "factual_consistency": 1.0,
            "context_relevance": 1.0,
            "explanation_quality": 1.0,
            "actionability": 1.0,
        },
        validator_version="v1.0",
    )


@pytest.fixture
def policy_fail_deterministic() -> SemanticValidationResult:
    return SemanticValidationResult(
        valid=False,
        factual_consistency=True,
        context_relevance=True,
        policy_compliant=False,
        explanation_quality=True,
        actionability=True,
        violations=["FORCE_UNLOCK"],
        scores={"policy_compliance": 0.0},
        validator_version="v1.0",
    )


@pytest.fixture
def fact_fail_deterministic() -> SemanticValidationResult:
    return SemanticValidationResult(
        valid=False,
        factual_consistency=False,
        context_relevance=True,
        policy_compliant=True,
        explanation_quality=True,
        actionability=True,
        violations=["MASTERY_MISMATCH"],
        scores={"factual_consistency": 0.0},
        validator_version="v1.0",
    )


def test_gjf1_policy_failure_triggers_reject(fusion_engine, policy_fail_deterministic):
    """GJF1: G1 策略安全违规时熔断拒识 (REJECT)"""
    judge_res = JudgeResult(
        judge_version="v1.0",
        valid=True,
        overall_score=0.99,
        confidence=0.99,
        dimension_scores={},
        rationale_summary="完美",
        violations=[],
    )
    final_res = fusion_engine.fuse(policy_fail_deterministic, judge_res)
    assert final_res.decision == JudgeDecision.REJECT
    assert final_res.final_valid is False
    assert final_res.policy_compliant is False


def test_gjf2_fact_failure_triggers_reject(fusion_engine, fact_fail_deterministic):
    """GJF2: G1 事实一致性失败时强制拒识 (REJECT)"""
    judge_res = JudgeResult(
        judge_version="v1.0",
        valid=True,
        overall_score=0.95,
        confidence=0.95,
        dimension_scores={},
        rationale_summary="非常好",
        violations=[],
    )
    final_res = fusion_engine.fuse(fact_fail_deterministic, judge_res)
    assert final_res.decision == JudgeDecision.REJECT
    assert final_res.final_valid is False
    assert final_res.factual_consistency is False


def test_gjf3_deterministic_pass_high_judge_score_accept(fusion_engine, pass_deterministic):
    """GJF3: G1 通过 + Judge 高分高置信度 -> ACCEPT (final_valid = True)"""
    judge_res = JudgeResult(
        judge_version="v1.0",
        valid=True,
        overall_score=0.88,
        confidence=0.85,
        dimension_scores={"EXPLANATION_DEPTH": 0.90},
        rationale_summary="分析透彻，行动明确",
        violations=[],
    )
    final_res = fusion_engine.fuse(pass_deterministic, judge_res)
    assert final_res.decision == JudgeDecision.ACCEPT
    assert final_res.final_valid is True
    assert final_res.judge_used is True


def test_gjf4_medium_judge_score_review(fusion_engine, pass_deterministic):
    """GJF4: G1 通过 + Judge 中等分数 (0.60 <= score < 0.80) -> REVIEW"""
    judge_res = JudgeResult(
        judge_version="v1.0",
        valid=True,
        overall_score=0.72,
        confidence=0.80,
        dimension_scores={},
        rationale_summary="教学深度略显平淡",
        violations=["EXPLANATION_SHALLOW"],
    )
    final_res = fusion_engine.fuse(pass_deterministic, judge_res)
    assert final_res.decision == JudgeDecision.REVIEW
    assert final_res.final_valid is False


def test_gjf5_low_judge_score_reject(fusion_engine, pass_deterministic):
    """GJF5: G1 通过 + Judge 低分 (score < 0.60) -> REJECT"""
    judge_res = JudgeResult(
        judge_version="v1.0",
        valid=False,
        overall_score=0.42,
        confidence=0.85,
        dimension_scores={},
        rationale_summary="回答过于敷衍",
        violations=["POOR_EXPLANATION"],
    )
    final_res = fusion_engine.fuse(pass_deterministic, judge_res)
    assert final_res.decision == JudgeDecision.REJECT
    assert final_res.final_valid is False


def test_gjf6_low_confidence_review(fusion_engine, pass_deterministic):
    """GJF6: G1 通过 + 高分但低置信度 (confidence < 0.70) -> REVIEW"""
    judge_res = JudgeResult(
        judge_version="v1.0",
        valid=True,
        overall_score=0.90,
        confidence=0.55,
        dimension_scores={},
        rationale_summary="评分较高但置信不足",
        violations=[],
    )
    final_res = fusion_engine.fuse(pass_deterministic, judge_res)
    assert final_res.decision == JudgeDecision.REVIEW
    assert final_res.final_valid is False


def test_gjf7_judge_unavailable_deterministic_pass_review(fusion_engine, pass_deterministic):
    """GJF7: Judge 不可用 + G1 通过 -> 平稳降级至 REVIEW"""
    final_res = fusion_engine.fuse(
        pass_deterministic,
        judge_result=None,
        judge_failure=JudgeFailureClass.JUDGE_TIMEOUT,
    )
    assert final_res.decision == JudgeDecision.REVIEW
    assert final_res.final_valid is False
    assert final_res.judge_used is False
    assert final_res.judge_failure_class == JudgeFailureClass.JUDGE_TIMEOUT


def test_gjf8_judge_unavailable_deterministic_failure_reject(fusion_engine, policy_fail_deterministic):
    """GJF8: Judge 不可用 + G1 失败 -> 依然 REJECT"""
    final_res = fusion_engine.fuse(
        policy_fail_deterministic,
        judge_result=None,
        judge_failure=JudgeFailureClass.JUDGE_UNAVAILABLE,
    )
    assert final_res.decision == JudgeDecision.REJECT
    assert final_res.final_valid is False


def test_gjf9_judge_cannot_override_hard_gate(fusion_engine, policy_fail_deterministic):
    """GJF9: 断言 Judge 绝对无法 override Policy/Fact Hard Gate"""
    max_judge = JudgeResult(
        judge_version="v1.0",
        valid=True,
        overall_score=1.0,
        confidence=1.0,
        dimension_scores={},
        rationale_summary="超越一切的最高好评",
        violations=[],
    )
    final_res = fusion_engine.fuse(policy_fail_deterministic, max_judge)
    assert final_res.decision == JudgeDecision.REJECT
    assert final_res.final_valid is False


def test_gjf10_fusion_deterministic(fusion_engine, pass_deterministic):
    """GJF10: 融合决策纯函数确定性，50 次计算严格一致"""
    judge_res = JudgeResult(
        judge_version="v1.0",
        valid=True,
        overall_score=0.85,
        confidence=0.90,
        dimension_scores={},
        rationale_summary="稳定判定",
        violations=[],
    )
    first_res = fusion_engine.fuse(pass_deterministic, judge_res)
    for _ in range(50):
        curr_res = fusion_engine.fuse(pass_deterministic, judge_res)
        assert curr_res == first_res
