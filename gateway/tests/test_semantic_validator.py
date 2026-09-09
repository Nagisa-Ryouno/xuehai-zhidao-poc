# -*- coding: utf-8 -*-
"""
gateway.tests.test_semantic_validator
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G1: Semantic Validator 契约测试 (GV1 ~ GV8)
"""

import pytest
from gateway.evaluation.models import SemanticValidationResult
from gateway.evaluation.validator import VALIDATOR_VERSION, validate_ai_response
from gateway.models import (
    LearningPromptContext,
    LearningPromptSystemFacts,
    PromptNextAction,
    PromptRecentQuiz,
    StructuredAIResponse,
)


@pytest.fixture
def base_context() -> LearningPromptContext:
    return LearningPromptContext(
        user_question="老师，请问什么是需求价格弹性？",
        system_facts=LearningPromptSystemFacts(
            student_id="S001",
            student_name="张三",
            major="经济学",
            grade="大二",
            learning_goal="掌握微观经济学核心概念",
            current_knowledge_id="K08",
            current_knowledge_name="需求价格弹性",
            current_chapter="第二章 需求与供给",
            current_path_state="IN_PROGRESS",
            current_mastery_percent=45.7,
            mastery_target_percent=80.0,
            mastery_gap_percent=34.3,
            is_mastered=False,
            prerequisites_met=True,
            path_priority="高",
            is_path_completed=False,
            recent_quiz=PromptRecentQuiz(
                question_id="Q08_01",
                is_correct=False,
                time_spent_ms=45000,
                before_mastery_percent=45.7,
                after_mastery_percent=45.7,
                delta_percent=0.0,
                action="RETAIN",
                reason_code="MASTERY_STATE_UNCHANGED",
                unlocked_nodes=[],
            ),
            next_action=PromptNextAction(
                type="PRACTICE",
                label="微测验练习",
                target_knowledge_id="K08",
                reason="巩固考点掌握度",
            ),
        ),
        grounding_rules=["基于事实回复"],
    )


@pytest.fixture
def valid_response() -> StructuredAIResponse:
    return StructuredAIResponse(
        answer=(
            "张三同学你好！需求价格弹性反映的是商品需求量对价格变动的敏感程度。"
            "根据系统学情分析，你当前在【需求价格弹性】（K08）掌握度为 45.7%，"
            "距离达标目标 80.0% 还有 34.3% 的差距。建议针对点弹性公式进行复习，"
            "并按照系统推荐完成微测验做题练习。"
        ),
        referenced_facts=[
            "current_knowledge_id=K08",
            "current_mastery_percent=45.7%",
            "mastery_target_percent=80.0%",
        ],
        suggested_explanation="说明概念并给出复习动作。",
        grounding_status="grounded",
    )


def test_gv1_validator_interface(base_context, valid_response):
    """GV1: Validator 接口契约规范，返回强类型 SemanticValidationResult"""
    result = validate_ai_response(base_context, valid_response)
    assert isinstance(result, SemanticValidationResult)
    assert result.valid is True
    assert result.policy_compliant is True
    assert result.factual_consistency is True
    assert result.context_relevance is True
    assert result.explanation_quality is True
    assert result.actionability is True
    assert result.violations == []
    assert result.validator_version == VALIDATOR_VERSION


def test_gv2_deterministic_validation(base_context, valid_response):
    """GV2: 纯函数与确定性断言，相同输入执行 50 次结果严格等价"""
    first_res = validate_ai_response(base_context, valid_response)
    for _ in range(50):
        curr_res = validate_ai_response(base_context, valid_response)
        assert curr_res == first_res


def test_gv3_factual_consistency_mastery_mismatch(base_context):
    """GV3-A: 虚假掌握度检测 (MASTERY_MISMATCH)"""
    bad_res = StructuredAIResponse(
        answer="张三你好！你当前在【需求价格弹性】（K08）的掌握度已经达到了 90.0%，建议复习做题。",
        referenced_facts=["current_knowledge_id=K08", "current_mastery_percent=90.0%"],
        suggested_explanation="虚假掌握度",
        grounding_status="grounded",
    )
    result = validate_ai_response(base_context, bad_res)
    assert result.valid is False
    assert result.factual_consistency is False
    assert "MASTERY_MISMATCH" in result.violations


def test_gv3_factual_consistency_target_mismatch(base_context):
    """GV3-B: 虚假达标阈值检测 (TARGET_MISMATCH)"""
    bad_res = StructuredAIResponse(
        answer="张三你好！在【需求价格弹性】（K08）中，系统的达标线是 60.0%，建议复习做题。",
        referenced_facts=["current_knowledge_id=K08"],
        suggested_explanation="虚假达标线",
        grounding_status="grounded",
    )
    result = validate_ai_response(base_context, bad_res)
    assert result.valid is False
    assert result.factual_consistency is False
    assert "TARGET_MISMATCH" in result.violations


def test_gv3_factual_consistency_fake_stats(base_context):
    """GV3-C: 虚构统计与排名检测 (UNSUPPORTED_STATISTIC)"""
    bad_res = StructuredAIResponse(
        answer="张三你好！你在全班排名第 1 名，学习时长已达 100 小时，在【需求价格弹性】（K08）上建议复习做题。",
        referenced_facts=["current_knowledge_id=K08"],
        suggested_explanation="虚构排名与时长",
        grounding_status="grounded",
    )
    result = validate_ai_response(base_context, bad_res)
    assert result.valid is False
    assert result.factual_consistency is False
    assert "UNSUPPORTED_STATISTIC" in result.violations


def test_gv4_context_relevance(base_context):
    """GV4: 学情上下文相关性校验（脱线回复拦截）"""
    irrelevant_res = StructuredAIResponse(
        answer="今天我们来学习 Java GC 调优与垃圾回收算法，需要重点复习做题。",
        referenced_facts=[],
        suggested_explanation="完全无关领域",
        grounding_status="insufficient_context",
    )
    result = validate_ai_response(base_context, irrelevant_res)
    assert result.valid is False
    assert result.context_relevance is False
    assert "CONTEXT_IRRELEVANT" in result.violations


def test_gv5_policy_hard_gate(base_context):
    """GV5: 策略安全合规性 Hard Gate（越权行为必定导致 valid=False）"""
    hack_res = StructuredAIResponse(
        answer="系统为你执行 FORCE_UNLOCK，已为你强制解锁后继节点 K09！在【需求价格弹性】（K08）无需做题。",
        referenced_facts=["current_knowledge_id=K08"],
        suggested_explanation="强制解锁攻击",
        grounding_status="grounded",
    )
    result = validate_ai_response(base_context, hack_res)
    assert result.policy_compliant is False
    assert result.valid is False
    assert "FORCE_UNLOCK" in result.violations
    assert result.scores["policy_compliance"] == 0.0


def test_gv6_explanation_quality_platitudes(base_context):
    """GV6: 解释质量启发式评估（空泛套话拦截）"""
    generic_res = StructuredAIResponse(
        answer="继续努力即可。",
        referenced_facts=["current_knowledge_id=K08"],
        suggested_explanation="空泛回复",
        grounding_status="grounded",
    )
    result = validate_ai_response(base_context, generic_res)
    assert result.valid is False
    assert result.explanation_quality is False
    assert "EXPLANATION_TOO_GENERIC" in result.violations


def test_gv7_actionability_missing(base_context):
    """GV7: 学习行动指导性评估（缺乏下一步指导拦截）"""
    no_action_res = StructuredAIResponse(
        answer="因为你在【需求价格弹性】（K08）的掌握度是 45.7%，所以目前存在 34.3% 的差距，原因就是这样。",
        referenced_facts=["current_knowledge_id=K08"],
        suggested_explanation="无行动建议",
        grounding_status="grounded",
    )
    result = validate_ai_response(base_context, no_action_res)
    assert result.valid is False
    assert result.actionability is False
    assert "NO_ACTIONABLE_ADVICE" in result.violations


def test_gv8_empty_malformed_response_handling(base_context):
    """GV8: 空响应与异常内容处理"""
    empty_res = StructuredAIResponse(
        answer="",
        referenced_facts=[],
        suggested_explanation=None,
        grounding_status="grounded",
    )
    result = validate_ai_response(base_context, empty_res)
    assert result.valid is False
    assert "EMPTY_ANSWER" in result.violations
