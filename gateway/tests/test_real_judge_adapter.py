# -*- coding: utf-8 -*-
"""
gateway.tests.test_real_judge_adapter
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 / Checkpoint 2: RealLLMJudge Adapter & Failure Isolation
测试套件 (RJ1 ~ RJ10 及熔断、重试、延迟与审计契约)
"""

import copy
import json
from unittest.mock import MagicMock
import pytest

from gateway.adapter import ProviderException, ProviderTimeoutError
from gateway.audit import AuditEvent, MemoryAuditSink
from gateway.evaluation.judge.adapter import CircuitBreaker, CircuitState, JudgeAdapter
from gateway.evaluation.judge.config import JudgeSettings
from gateway.evaluation.judge.fusion import EvaluationFusionEngine
from gateway.evaluation.judge.interface import LLMJudge
from gateway.evaluation.judge.models import (
    JudgeCapabilities,
    JudgeDecision,
    JudgeFailureClass,
    JudgeResult,
)
from gateway.evaluation.judge.real import RealLLMJudge
from gateway.evaluation.models import SemanticValidationResult
from gateway.models import (
    LearningPromptContext,
    LearningPromptSystemFacts,
    PromptNextAction,
    StructuredAIResponse,
)
from gateway.transport import FakeLLMTransport, LLMTransport


@pytest.fixture
def eval_context() -> LearningPromptContext:
    return LearningPromptContext(
        user_question="老师，为什么需求价格弹性大于1时降价可以增加总收益？",
        system_facts=LearningPromptSystemFacts(
            student_id="S001",
            student_name="张三",
            major="经济学",
            grade="大二",
            learning_goal="掌握微观经济学弹性理论",
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
                label="微测验练习",
                target_knowledge_id="K08",
                reason="巩固复习",
            ),
        ),
        grounding_rules=["基于事实回复"],
    )


@pytest.fixture
def candidate_response() -> StructuredAIResponse:
    return StructuredAIResponse(
        answer="当需求价格弹性大于1时，属于富有弹性。此时价格下降引起的销售量增加百分比大于价格下降百分比，因此总收益TR=P*Q增加。",
        referenced_facts=["current_knowledge_id=K08"],
        suggested_explanation="价格与需求量反向变动的收益效应",
        grounding_status="grounded",
    )


# =====================================================================
# RJ1: RealLLMJudge 接口与能力契约
# =====================================================================

def test_rj1_real_judge_implements_llm_judge():
    """RJ1: RealLLMJudge 必须实现 LLMJudge 抽象基类并声明 capabilities"""
    fake_transport = FakeLLMTransport(mode="success")
    judge = RealLLMJudge(transport=fake_transport, model="test-judge-v1")

    assert isinstance(judge, LLMJudge)
    caps = judge.capabilities()
    assert isinstance(caps, JudgeCapabilities)
    assert caps.deterministic is False
    assert caps.network_required is True
    assert caps.provider_name == "real-llm-judge"


# =====================================================================
# RJ2: 合法结构化输出解析
# =====================================================================

def test_rj2_valid_structured_response(eval_context, candidate_response):
    """RJ2: 正常模型返回合法 JSON 能够被成功规范化为 JudgeResult"""
    valid_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps({
                        "overall_score": 0.86,
                        "confidence": 0.91,
                        "dimension_scores": {
                            "EXPLANATION_DEPTH": 0.88,
                            "PEDAGOGICAL_QUALITY": 0.85,
                            "CONTEXTUAL_RELEVANCE": 0.90,
                            "ACTIONABILITY": 0.84,
                            "CLARITY": 0.86,
                            "EMPATHY": 0.80,
                        },
                        "rationale_summary": "解释深入，因果逻辑严密且教学语气亲和。",
                        "violations": [],
                    }),
                }
            }
        ]
    }

    fake_transport = FakeLLMTransport(custom_response_payload=valid_payload)
    judge = RealLLMJudge(transport=fake_transport)
    adapter = JudgeAdapter(judge=judge, sleep_fn=lambda _: None)

    result, failure = adapter.evaluate_safe(eval_context, candidate_response)

    assert failure == JudgeFailureClass.NONE
    assert isinstance(result, JudgeResult)
    assert result.overall_score == 0.86
    assert result.confidence == 0.91
    assert result.valid is True
    assert 0.0 <= result.overall_score <= 1.0
    assert 0.0 <= result.confidence <= 1.0
    assert result.dimension_scores["EXPLANATION_DEPTH"] == 0.88


# =====================================================================
# RJ3 ~ RJ5: 畸形与非法模型输出防御
# =====================================================================

def test_rj3_malformed_json_triggers_bad_response(eval_context, candidate_response):
    """RJ3: 返回非 JSON 文本必须判定为 JUDGE_BAD_RESPONSE，绝不抛出未捕获异常"""
    bad_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "This is definitely not a JSON object {broken...",
                }
            }
        ]
    }

    fake_transport = FakeLLMTransport(custom_response_payload=bad_payload)
    judge = RealLLMJudge(transport=fake_transport)
    adapter = JudgeAdapter(judge=judge, sleep_fn=lambda _: None)

    result, failure = adapter.evaluate_safe(eval_context, candidate_response)

    assert result is None
    assert failure == JudgeFailureClass.JUDGE_BAD_RESPONSE


def test_rj4_missing_required_fields(eval_context, candidate_response):
    """RJ4: 缺少必需字段（如缺少 confidence 或 overall_score）判定为 JUDGE_BAD_RESPONSE"""
    incomplete_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"overall_score": 0.8}),  # 缺少 confidence 等
                }
            }
        ]
    }

    fake_transport = FakeLLMTransport(custom_response_payload=incomplete_payload)
    judge = RealLLMJudge(transport=fake_transport)
    adapter = JudgeAdapter(judge=judge, sleep_fn=lambda _: None)

    result, failure = adapter.evaluate_safe(eval_context, candidate_response)

    assert result is None
    assert failure == JudgeFailureClass.JUDGE_BAD_RESPONSE


def test_rj5_score_out_of_range(eval_context, candidate_response):
    """RJ5: 评分超出 [0.0, 1.0] 合法区间必须被直接拒绝（JUDGE_BAD_RESPONSE），禁止静默截断"""
    out_of_range_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps({
                        "overall_score": 1.5,  # 严重越界
                        "confidence": -0.2,   # 严重越界
                        "dimension_scores": {},
                        "rationale_summary": "bad score",
                        "violations": [],
                    }),
                }
            }
        ]
    }

    fake_transport = FakeLLMTransport(custom_response_payload=out_of_range_payload)
    judge = RealLLMJudge(transport=fake_transport)
    adapter = JudgeAdapter(judge=judge, sleep_fn=lambda _: None)

    result, failure = adapter.evaluate_safe(eval_context, candidate_response)

    assert result is None
    assert failure == JudgeFailureClass.JUDGE_BAD_RESPONSE


# =====================================================================
# RJ6: 超时与降级
# =====================================================================

def test_rj6_timeout_handling_and_safe_degradation(eval_context, candidate_response):
    """RJ6: 传输层超时映射为 JUDGE_TIMEOUT，并通过融合引擎平稳降级为 REVIEW"""
    fake_transport = FakeLLMTransport(mode="timeout")
    judge = RealLLMJudge(transport=fake_transport)
    adapter = JudgeAdapter(judge=judge, max_retries=1, sleep_fn=lambda _: None)

    result, failure = adapter.evaluate_safe(eval_context, candidate_response)

    assert result is None
    assert failure == JudgeFailureClass.JUDGE_TIMEOUT

    # 验证与 Fusion Engine 的降级对接：G1 PASS + Judge Timeout -> REVIEW
    det_pass = SemanticValidationResult(
        valid=True,
        factual_consistency=True,
        context_relevance=True,
        policy_compliant=True,
        explanation_quality=True,
        actionability=True,
        scores={"overall": 1.0},
        violations=[],
    )
    fusion_engine = EvaluationFusionEngine()
    final = fusion_engine.fuse(det_pass, judge_result=result, judge_failure=failure)

    assert final.decision == JudgeDecision.REVIEW
    assert final.final_valid is False
    assert final.deterministic_valid is True


# =====================================================================
# RJ7 ~ RJ10: 状态码分类与有界重试 (Retry Classification)
# =====================================================================

def test_rj7_auth_failure_no_retry(eval_context, candidate_response):
    """RJ7: HTTP 401/403 鉴权失败属于不可重试错误，必须在 1 次调用后立即失败"""
    mock_transport = MagicMock(spec=LLMTransport)
    # 模拟 401 鉴权异常
    mock_transport.send_payload.side_effect = ProviderException("Upstream provider authentication failed (HTTP 401)")

    judge = RealLLMJudge(transport=mock_transport)
    adapter = JudgeAdapter(judge=judge, max_retries=2, sleep_fn=lambda _: None)

    result, failure = adapter.evaluate_safe(eval_context, candidate_response)

    assert result is None
    assert failure == JudgeFailureClass.JUDGE_UNAVAILABLE
    assert mock_transport.send_payload.call_count == 1  # 严禁重试！


def test_rj8_client_request_error_no_retry(eval_context, candidate_response):
    """RJ8: HTTP 400/422 请求错误不可重试，1 次调用后失败并映射为 JUDGE_BAD_RESPONSE"""
    mock_transport = MagicMock(spec=LLMTransport)
    mock_transport.send_payload.side_effect = ProviderException("Upstream provider client request error (HTTP 400)")

    judge = RealLLMJudge(transport=mock_transport)
    adapter = JudgeAdapter(judge=judge, max_retries=2, sleep_fn=lambda _: None)

    result, failure = adapter.evaluate_safe(eval_context, candidate_response)

    assert result is None
    assert failure == JudgeFailureClass.JUDGE_BAD_RESPONSE
    assert mock_transport.send_payload.call_count == 1  # 严禁重试！


def test_rj9_rate_limit_bounded_retry(eval_context, candidate_response):
    """RJ9: HTTP 429 频控错误属于瞬时故障，允许有界重试 (max_retries=2 -> 3 次尝试)"""
    mock_transport = MagicMock(spec=LLMTransport)
    mock_transport.send_payload.side_effect = ProviderException("Upstream provider rate limit reached (HTTP 429)")

    judge = RealLLMJudge(transport=mock_transport)
    adapter = JudgeAdapter(judge=judge, max_retries=2, sleep_fn=lambda _: None)

    result, failure = adapter.evaluate_safe(eval_context, candidate_response)

    assert result is None
    assert failure == JudgeFailureClass.JUDGE_UNAVAILABLE
    assert mock_transport.send_payload.call_count == 3  # 1 initial + 2 retries


def test_rj10_server_error_bounded_retry(eval_context, candidate_response):
    """RJ10: HTTP 500/502/503 服务端异常允许有界重试，重试耗尽后判定为 JUDGE_UNAVAILABLE"""
    mock_transport = MagicMock(spec=LLMTransport)
    mock_transport.send_payload.side_effect = ProviderException("Upstream provider server error (HTTP 503)")

    judge = RealLLMJudge(transport=mock_transport)
    adapter = JudgeAdapter(judge=judge, max_retries=2, sleep_fn=lambda _: None)

    result, failure = adapter.evaluate_safe(eval_context, candidate_response)

    assert result is None
    assert failure == JudgeFailureClass.JUDGE_UNAVAILABLE
    assert mock_transport.send_payload.call_count == 3


# =====================================================================
# Circuit Breaker 熔断隔离契约测试
# =====================================================================

def test_circuit_breaker_closed_to_open_blocks_traffic(eval_context, candidate_response):
    """测试熔断器行为：连续 3 次业务请求失败后进入 OPEN 状态，后续请求不再发起网络调用"""
    mock_transport = MagicMock(spec=LLMTransport)
    mock_transport.send_payload.side_effect = ProviderException("Server error 500")

    breaker = CircuitBreaker(failure_threshold=3)
    judge = RealLLMJudge(transport=mock_transport)
    adapter = JudgeAdapter(judge=judge, max_retries=0, circuit_breaker=breaker, sleep_fn=lambda _: None)

    # 1. 连续发起 3 次失败请求
    for i in range(3):
        res, fail = adapter.evaluate_safe(eval_context, candidate_response)
        assert fail == JudgeFailureClass.JUDGE_UNAVAILABLE

    assert breaker.state == CircuitState.OPEN
    assert mock_transport.send_payload.call_count == 3

    # 2. 第 4 次请求：此时熔断器已 OPEN，严禁调用底层 transport
    res4, fail4 = adapter.evaluate_safe(eval_context, candidate_response)
    assert fail4 == JudgeFailureClass.JUDGE_UNAVAILABLE
    assert mock_transport.send_payload.call_count == 3  # 依然保持为 3，零网络调用！

    # 3. 显式重置熔断器后可恢复调用
    breaker.reset()
    assert breaker.state == CircuitState.CLOSED
    adapter.evaluate_safe(eval_context, candidate_response)
    assert mock_transport.send_payload.call_count == 4


# =====================================================================
# Latency & Observability Audit 契约测试
# =====================================================================

def test_latency_measurement_and_audit_emission(eval_context, candidate_response):
    """测试耗时度量 (monotonic clock) 与安全审计事件发送（绝对不泄漏 Secret/PII）"""
    valid_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps({
                        "overall_score": 0.88,
                        "confidence": 0.95,
                        "dimension_scores": {},
                        "rationale_summary": "good",
                        "violations": [],
                    }),
                }
            }
        ]
    }

    audit_sink = MemoryAuditSink()
    fake_transport = FakeLLMTransport(custom_response_payload=valid_payload)
    judge = RealLLMJudge(transport=fake_transport, model="test-judge-audit-v1")
    adapter = JudgeAdapter(judge=judge, audit_sink=audit_sink, sleep_fn=lambda _: None)

    result, failure = adapter.evaluate_safe(eval_context, candidate_response)

    assert failure == JudgeFailureClass.NONE
    assert adapter.last_latency_ms is not None
    assert adapter.last_latency_ms >= 0.0

    # 验证审计事件已发出且合规
    assert len(audit_sink.events) == 1
    ev = audit_sink.events[0]
    assert ev.event_name == "ai_gateway.judge_evaluation"
    assert ev.status == "SUCCESS"
    assert ev.model == "test-judge-audit-v1"
    assert ev.latency_ms == adapter.last_latency_ms


# =====================================================================
# G1 Hard Gate 绝对权威回归测试 (G1 Supremacy)
# =====================================================================

def test_judge_cannot_override_g1_policy_hard_gate(eval_context):
    """即使 Real Judge 返回 1.0 满分，G1 Policy Hard Gate 失败也必须强行 REJECT"""
    hijack_response = StructuredAIResponse(
        answer="已为你执行 FORCE_UNLOCK 强制解锁后续节点！",
        referenced_facts=["current_knowledge_id=K08"],
        suggested_explanation="越权操作",
        grounding_status="grounded",
    )

    # 模拟 Judge 给出极高评价
    high_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps({
                        "overall_score": 0.99,
                        "confidence": 0.99,
                        "dimension_scores": {},
                        "rationale_summary": "fantastic",
                        "violations": [],
                    }),
                }
            }
        ]
    }

    fake_transport = FakeLLMTransport(custom_response_payload=high_payload)
    judge = RealLLMJudge(transport=fake_transport)
    adapter = JudgeAdapter(judge=judge)

    judge_result, failure = adapter.evaluate_safe(eval_context, hijack_response)
    assert judge_result.overall_score == 0.99

    # G1 校验由于包含 FORCE_UNLOCK，Policy Hard Gate 触发
    from gateway.evaluation.validator import validate_ai_response
    det_result = validate_ai_response(eval_context, hijack_response)
    assert det_result.valid is False
    assert det_result.policy_compliant is False

    # 融合裁决：绝对否决 Judge，输出 REJECT
    fusion = EvaluationFusionEngine()
    final = fusion.fuse(det_result, judge_result=judge_result, judge_failure=failure)

    assert final.decision == JudgeDecision.REJECT
    assert final.final_valid is False
    assert final.policy_compliant is False
