# -*- coding: utf-8 -*-
"""
gateway.tests.test_judge_contract
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G2: LLM Judge 接口与数据模型契约测试 (GJ1 ~ GJ10)
"""

import pytest
from pydantic import ValidationError

from gateway.evaluation.judge.adapter import JudgeAdapter
from gateway.evaluation.judge.fake import FakeLLMJudge
from gateway.evaluation.judge.interface import LLMJudge
from gateway.evaluation.judge.models import (
    EvaluationContextProjection,
    JudgeCapabilities,
    JudgeDimension,
    JudgeFailureClass,
    JudgeResult,
    JudgeScore,
)
from gateway.evaluation.judge.prompt import (
    build_evaluation_context,
    build_judge_prompt,
)
from gateway.models import (
    LearningPromptContext,
    LearningPromptSystemFacts,
    PromptNextAction,
    StructuredAIResponse,
)


@pytest.fixture
def sample_context() -> LearningPromptContext:
    return LearningPromptContext(
        user_question="什么是需求价格弹性？为什么目前未达标？",
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
            recent_quiz=None,
            next_action=PromptNextAction(
                type="PRACTICE",
                label="微测验做题练习",
                target_knowledge_id="K08",
                reason="巩固概念",
            ),
        ),
        grounding_rules=["基于事实回复"],
    )


@pytest.fixture
def sample_response() -> StructuredAIResponse:
    return StructuredAIResponse(
        answer=(
            "张三同学你好！需求价格弹性反映的是商品需求量对价格变动的敏感程度。"
            "根据系统学情分析，你当前在【需求价格弹性】（K08）掌握度为 45.7%，"
            "距离达标目标 80.0% 还有 34.3% 的差距。建议复习点弹性公式并进行微测验做题练习。"
        ),
        referenced_facts=["current_knowledge_id=K08", "current_mastery_percent=45.7%"],
        suggested_explanation="说明概念并建议练习。",
        grounding_status="grounded",
    )


def test_gj1_judge_interface_contract(sample_context, sample_response):
    """GJ1: Judge 抽象接口实现与类型合规性"""
    judge = FakeLLMJudge()
    assert isinstance(judge, LLMJudge)

    result = judge.evaluate(sample_context, sample_response)
    assert isinstance(result, JudgeResult)
    assert result.judge_version == "v1.0"
    assert isinstance(result.overall_score, float)
    assert isinstance(result.confidence, float)


def test_gj2_judge_result_schema():
    """GJ2: JudgeResult 严格白名单与未知字段拦截 (extra='forbid')"""
    valid_data = {
        "judge_version": "v1.0",
        "valid": True,
        "overall_score": 0.85,
        "confidence": 0.90,
        "dimension_scores": {"EXPLANATION_DEPTH": 0.85},
        "rationale_summary": "解释深入，逻辑严谨。",
        "violations": [],
    }
    jr = JudgeResult.model_validate(valid_data)
    assert jr.overall_score == 0.85

    # 尝试注入非法外溢字段（如 prompt, secret, authorization 等）
    with pytest.raises(ValidationError):
        JudgeResult.model_validate({**valid_data, "prompt": "malicious injection"})

    with pytest.raises(ValidationError):
        JudgeResult.model_validate({**valid_data, "secret": "leaked_secret"})


def test_gj3_score_range_validation():
    """GJ3: JudgeScore 与 JudgeResult 评分边界校验 (0.0 <= score <= 1.0)"""
    JudgeScore(dimension=JudgeDimension.CLARITY, score=0.0, confidence=0.5, rationale="底线")
    JudgeScore(dimension=JudgeDimension.CLARITY, score=1.0, confidence=0.5, rationale="顶线")

    with pytest.raises(ValidationError):
        JudgeScore(dimension=JudgeDimension.CLARITY, score=-0.1, confidence=0.5, rationale="越界负值")

    with pytest.raises(ValidationError):
        JudgeScore(dimension=JudgeDimension.CLARITY, score=1.1, confidence=0.5, rationale="越界高值")


def test_gj4_confidence_range_validation():
    """GJ4: 置信度边界校验 (0.0 <= confidence <= 1.0)"""
    JudgeScore(dimension=JudgeDimension.EMPATHY, score=0.8, confidence=0.0, rationale="零置信")
    JudgeScore(dimension=JudgeDimension.EMPATHY, score=0.8, confidence=1.0, rationale="满置信")

    with pytest.raises(ValidationError):
        JudgeScore(dimension=JudgeDimension.EMPATHY, score=0.8, confidence=-0.01, rationale="负置信越界")

    with pytest.raises(ValidationError):
        JudgeScore(dimension=JudgeDimension.EMPATHY, score=0.8, confidence=1.05, rationale="超额置信越界")


def test_gj5_deterministic_fake_judge(sample_context, sample_response):
    """GJ5: Fake Judge 纯内存确定性断言 (50 次调用结果字节级一致)"""
    judge = FakeLLMJudge()
    first_dump = judge.evaluate(sample_context, sample_response).model_dump()

    for _ in range(50):
        curr_dump = judge.evaluate(sample_context, sample_response).model_dump()
        assert curr_dump == first_dump


def test_gj6_judge_capability_declaration():
    """GJ6: Judge 能力与元数据声明规范"""
    judge = FakeLLMJudge()
    caps = judge.capabilities()
    assert isinstance(caps, JudgeCapabilities)
    assert caps.deterministic is True
    assert caps.network_required is False
    assert len(caps.supported_dimensions) == 6
    assert JudgeDimension.EXPLANATION_DEPTH in caps.supported_dimensions


def test_gj7_malformed_judge_response_rejection(sample_context, sample_response):
    """GJ7: 结构畸形或损坏的 Judge 响应拦截"""
    class BadJudge(LLMJudge):
        def capabilities(self):
            return FakeLLMJudge().capabilities()
        def evaluate(self, ctx, resp):
            return "not_a_judge_result"  # type: ignore

    adapter = JudgeAdapter(judge=BadJudge())
    res, failure = adapter.evaluate_safe(sample_context, sample_response)
    assert res is None
    assert failure == JudgeFailureClass.JUDGE_BAD_RESPONSE


def test_gj8_judge_exception_isolation(sample_context, sample_response):
    """GJ8: Judge 异常故障隔离，绝不崩溃评估流程"""
    failing_judge = FakeLLMJudge(should_fail=True, failure_reason="Upstream model crash")
    adapter = JudgeAdapter(judge=failing_judge)

    res, failure = adapter.evaluate_safe(sample_context, sample_response)
    assert res is None
    assert failure == JudgeFailureClass.JUDGE_INTERNAL_ERROR


def test_gj9_context_projection(sample_context):
    """GJ9: Evaluation Context Projection 仅保留最小必要字段并剔除敏感个人数据"""
    proj = build_evaluation_context(sample_context)
    assert isinstance(proj, EvaluationContextProjection)
    assert proj.knowledge_node_id == "K08"
    assert proj.knowledge_node_title == "需求价格弹性"
    assert proj.current_mastery_percent == 45.7
    assert proj.mastery_target_percent == 80.0
    assert proj.is_mastered is False
    assert proj.decision == "微测验做题练习"

    # 验证私有信息被隔离
    proj_dict = proj.model_dump()
    assert "student_id" not in proj_dict
    assert "student_name" not in proj_dict
    assert "major" not in proj_dict
    assert "grade" not in proj_dict


def test_gj10_prompt_contract(sample_context, sample_response):
    """GJ10: Judge Prompt 契约结构与防越权声明检验"""
    prompt = build_judge_prompt(sample_context, sample_response)
    assert "You have ZERO learning decision authority." in prompt
    assert "CANNOT and MUST NOT modify student mastery" in prompt
    assert "EXPLANATION_DEPTH" in prompt
    assert "PEDAGOGICAL_QUALITY" in prompt
    assert "Required Output JSON Format" in prompt
    # 保证 Prompt 中不出现密钥关键词
    assert "AI_API_KEY" not in prompt
    assert "Bearer" not in prompt
