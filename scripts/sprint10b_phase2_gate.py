# -*- coding: utf-8 -*-
"""
scripts/sprint10b_phase2_gate.py
================================
学海智导 (Xuehai Zhidao) — Sprint 10-B Phase 2
DeepSeek Candidate Recommendation & Deterministic Validation 核心质量门禁

聚焦于 Phase 2 自身不变量（17 项核心质量与架构红线校验）：
[01/17] Provider Contract (显式 task='recommendation' 契约与脱敏 user_id)
[02/17] Candidate Schema (严格 extra='forbid' 白名单字段校验)
[03/17] Valid Candidate [Case A] (合法候选顺利通过并注入权威元数据)
[04/17] Invalid Knowledge [Case C] (未知考点 K999 坚决拦截)
[05/17] Invalid Resource [Case D] (未知资源坚决拦截)
[06/17] Invalid Relation (考点与资源归属不匹配坚决拦截)
[07/17] Duplicate Candidate [Case E] (重复项去重，首项保留，次项标记 DUPLICATE_CANDIDATE)
[08/17] Empty Response [Case F] (空数组安全通过，validated_candidates=[], 零决策回退)
[09/17] Malformed Response [Case G] (全链路非 JSON 语法解析失败 -> 结构化拦截)
[10/17] PII Firewall (严格脱敏检查，零真实姓名、手机、邮箱、身份证)
[11/17] allow_production_decision=False (AI 绝对无生产决策权红线保持)
[12/17] BKT Unchanged (推荐调用前后 BKT 状态绝对零修改)
[13/17] PathState Unchanged (推荐调用前后路径状态绝对零修改)
[14/17] Learning Events Unchanged (推荐调用前后正式学习事件绝对零新增)
[15/17] Resource Events Unchanged (推荐调用前后资源事件绝对零新增)
[16/17] Deterministic 20x (同一上下文与 Mock 连续 20 次调用输出 100% 稳定一致)
[17/17] Mock Offline Guarantee (DEEPSEEK_ENABLED=false 离线默认保证，零外部网络请求)
"""

import asyncio
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pydantic import ValidationError
from app.core.config import settings
from gateway.adapter import AIProviderAdapter, get_provider
from gateway.ai.deepseek import (
    AIProviderRequest,
    AIProviderResponse,
    MockDeepSeekProvider,
    assert_no_pii,
)
from gateway.config import gateway_settings
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.resources.service import get_unified_resource_by_id
from gateway.ai.recommendation import (
    RECOMMENDATION_FORBIDDEN_FIELDS,
    CandidateValidationResult,
    DeepSeekCandidateGenerator,
    KnowledgeStateSnapshot,
    RecommendationCandidate,
    RecommendationContext,
    RecommendationContextBuilder,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationService,
    RecommendationValidator,
    RejectedCandidate,
    ResourceCandidateSnapshot,
    ValidatedRecommendation,
    ValidationRejectedError,
    build_recommendation_prompt,
    default_recommendation_service,
)


def get_sample_context() -> RecommendationContext:
    return RecommendationContext(
        student_id="student_s001",
        current_focus="K03",
        knowledge_states=[
            KnowledgeStateSnapshot(
                knowledge_id="K03",
                knowledge_name="需求价格弹性",
                mastery=0.45,
                path_state="IN_PROGRESS",
            ),
            KnowledgeStateSnapshot(
                knowledge_id="K04",
                knowledge_name="需求收入与交叉弹性",
                mastery=0.20,
                path_state="AVAILABLE",
            ),
        ],
        resources=[
            ResourceCandidateSnapshot(
                resource_id="res_k03_concept",
                knowledge_id="K03",
                resource_type="concept_microcard",
                title="需求价格弹性 考点精要微卡",
                description="核心概念精析",
                source="xuehai_internal",
            ),
            ResourceCandidateSnapshot(
                resource_id="res_k03_example",
                knowledge_id="K03",
                resource_type="example_case",
                title="需求价格弹性 典型例题精析",
                description="典型例题精解",
                source="xuehai_internal",
            ),
            ResourceCandidateSnapshot(
                resource_id="res_k04_practice",
                knowledge_id="K04",
                resource_type="micro_practice",
                title="需求收入与交叉弹性 靶向通关微测验",
                description="靶向微练习",
                source="xuehai_internal",
            ),
        ],
    )


# ==============================================================================
# 17 项核心检查逻辑
# ==============================================================================

def check_01_provider_contract():
    """Check 01: Provider Contract (显式 task='recommendation' 契约路由)"""
    ctx = get_sample_context()
    generator = DeepSeekCandidateGenerator()
    captured = []

    class CapturingMock(MockDeepSeekProvider):
        async def complete(self, req: AIProviderRequest) -> AIProviderResponse:
            captured.append(req)
            return await super().complete(req)

    asyncio.run(generator.generate_raw_candidates(context=ctx, provider_override=CapturingMock()))
    assert len(captured) == 1
    req = captured[0]
    assert req.task == "recommendation", f"task must be recommendation, got {req.task}"
    assert req.user_id == ctx.student_id
    assert req.response_format == "json_object"


def check_02_candidate_schema():
    """Check 02: Candidate Schema (严格 extra='forbid' 白名单字段校验)"""
    cand = RecommendationCandidate(
        knowledge_id="K03",
        resource_id="res_k03_concept",
        reason="基础薄弱，先看微卡",
    )
    assert cand.knowledge_id == "K03"
    assert cand.resource_id == "res_k03_concept"

    try:
        RecommendationCandidate(
            knowledge_id="K03",
            resource_id="res_k03_concept",
            reason="理由",
            rank=1,
        )
        assert False, "extra='forbid' failed to reject rank"
    except ValidationError:
        pass


def check_03_valid_candidate():
    """Check 03: Valid Candidate [Case A] (合法候选顺利通过并注入权威元数据)"""
    ctx = get_sample_context()
    raw = {
        "recommendations": [
            {
                "knowledge_id": "K03",
                "resource_id": "res_k03_concept",
                "reason": "概念掌握不足，建议先学习核心微卡构建体系。",
            }
        ]
    }
    res = RecommendationValidator.validate_candidates_detailed(raw, context=ctx)
    assert len(res.validated_candidates) == 1
    assert len(res.rejected_candidates) == 0
    item = res.validated_candidates[0]
    assert item.knowledge_id == "K03"
    assert item.resource_id == "res_k03_concept"
    assert item.title != ""


def check_04_invalid_knowledge():
    """Check 04: Invalid Knowledge [Case C] (未知考点 K999 坚决拦截)"""
    ctx = get_sample_context()
    raw = {"recommendations": [{"knowledge_id": "K999", "resource_id": "res_k03_concept", "reason": "虚构"}]}
    res = RecommendationValidator.validate_candidates_detailed(raw, context=ctx)
    assert len(res.validated_candidates) == 0
    assert len(res.rejected_candidates) == 1
    assert res.rejected_candidates[0].code in ("UNKNOWN_KNOWLEDGE_ID", "KNOWLEDGE_NOT_IN_CONTEXT")


def check_05_invalid_resource():
    """Check 05: Invalid Resource [Case D] (未知资源坚决拦截)"""
    ctx = get_sample_context()
    raw = {"recommendations": [{"knowledge_id": "K03", "resource_id": "res_not_exist_99", "reason": "虚构"}]}
    res = RecommendationValidator.validate_candidates_detailed(raw, context=ctx)
    assert len(res.validated_candidates) == 0
    assert len(res.rejected_candidates) == 1
    assert res.rejected_candidates[0].code in ("UNKNOWN_RESOURCE_ID", "RESOURCE_NOT_IN_CONTEXT")


def check_06_invalid_relation():
    """Check 06: Invalid Relation (考点与资源归属不匹配坚决拦截)"""
    raw = {"recommendations": [{"knowledge_id": "K02", "resource_id": "res_k01_concept", "reason": "张冠李戴"}]}
    res = RecommendationValidator.validate_candidates_detailed(raw, context=None)
    assert len(res.validated_candidates) == 0
    assert len(res.rejected_candidates) == 1
    assert res.rejected_candidates[0].code == "RESOURCE_KNOWLEDGE_MISMATCH"


def check_07_duplicate_candidate():
    """Check 07: Duplicate Candidate [Case E] (重复项去重，首项保留，次项标记 DUPLICATE_CANDIDATE)"""
    ctx = get_sample_context()
    raw = {
        "recommendations": [
            {"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": "第一次"},
            {"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": "第二次"},
        ]
    }
    res = RecommendationValidator.validate_candidates_detailed(raw, context=ctx)
    assert len(res.validated_candidates) == 1
    assert len(res.rejected_candidates) == 1
    assert res.rejected_candidates[0].code == "DUPLICATE_CANDIDATE"


def check_08_empty_response():
    """Check 08: Empty Response [Case F] (空数组安全通过，validated_candidates=[], 零决策回退)"""
    ctx = get_sample_context()
    raw = {"recommendations": []}
    res = RecommendationValidator.validate_candidates_detailed(raw, context=ctx)
    assert res.validated_candidates == []
    assert res.rejected_candidates == []
    assert res.validation_reasons == []


def check_09_malformed_response():
    """Check 09: Malformed Response [Case G] (全链路非 JSON 语法解析失败 -> 结构化拦截)"""
    class MalformedProvider(MockDeepSeekProvider):
        async def complete(self, req: AIProviderRequest) -> AIProviderResponse:
            return AIProviderResponse(
                content="Not valid JSON response at all",
                model="mock-deepseek",
                provider="mock-deepseek",
                parsed_json=None,
            )

    svc = RecommendationService(provider=MalformedProvider(), raise_on_rejection=False)
    resp = asyncio.run(svc.get_recommendations("S001"))
    assert resp.validated is False
    assert len(resp.rejected_candidates) == 1
    assert resp.rejected_candidates[0].code == "INVALID_JSON_SYNTAX"


def check_10_pii_firewall():
    """Check 10: PII Firewall (严格脱敏检查，零真实姓名、手机、邮箱、身份证)"""
    ctx = RecommendationContextBuilder.build_context("S001")
    raw = json.dumps(ctx.model_dump(), ensure_ascii=False)
    assert_no_pii(raw)
    assert ctx.student_id == "student_s001"
    assert "张三" not in raw
    assert "138" not in raw


def check_11_allow_production_decision_invariant():
    """Check 11: allow_production_decision=False (AI 绝对无生产决策权红线保持)"""
    # 验证模型契约与系统提示词
    ctx = get_sample_context()
    sys_p, _ = build_recommendation_prompt(ctx)
    assert "allow_production_decision = False" in sys_p
    assert "Candidate-only" in sys_p

    # 验证响应不暴露生产决策字段
    res = asyncio.run(default_recommendation_service.get_recommendations("S001"))
    d = res.model_dump()
    for f in RECOMMENDATION_FORBIDDEN_FIELDS:
        assert f not in d, f"Forbidden field '{f}' found in recommendation response"


def check_12_bkt_unchanged():
    """Check 12: BKT Unchanged (推荐调用前后 BKT 状态绝对零修改)"""
    bkt_file = settings.BKT_STATES_FILE
    before = bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else ""
    asyncio.run(default_recommendation_service.get_recommendations("S001"))
    after = bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else ""
    assert before == after, "BKT state was unexpectedly mutated"


def check_13_path_state_unchanged():
    """Check 13: PathState Unchanged (推荐调用前后路径状态绝对零修改)"""
    p_file = settings.LEARNING_PATH_STATES_FILE
    before = p_file.read_text(encoding="utf-8") if p_file.exists() else ""
    asyncio.run(default_recommendation_service.get_recommendations("S001"))
    after = p_file.read_text(encoding="utf-8") if p_file.exists() else ""
    assert before == after, "Learning path state was unexpectedly mutated"


def check_14_learning_events_unchanged():
    """Check 14: Learning Events Unchanged (推荐调用前后正式学习事件绝对零新增)"""
    e_file = settings.LEARNING_EVENTS_FILE
    before = e_file.read_text(encoding="utf-8") if e_file.exists() else ""
    asyncio.run(default_recommendation_service.get_recommendations("S001"))
    after = e_file.read_text(encoding="utf-8") if e_file.exists() else ""
    assert before == after, "Learning events log was unexpectedly mutated"


def check_15_resource_events_unchanged():
    """Check 15: Resource Events Unchanged (推荐调用前后资源事件绝对零新增)"""
    res_events_file = Path("data/resource_events.jsonl")
    before = res_events_file.read_text(encoding="utf-8") if res_events_file.exists() else ""
    asyncio.run(default_recommendation_service.get_recommendations("S001"))
    after = res_events_file.read_text(encoding="utf-8") if res_events_file.exists() else ""
    assert before == after, "Resource events log was unexpectedly mutated"


def check_16_deterministic_20x():
    """Check 16: Deterministic 20x (同一上下文与 Mock 连续 20 次调用输出 100% 稳定一致)"""
    mock = MockDeepSeekProvider()
    svc = RecommendationService(provider=mock, raise_on_rejection=False)
    first_resp = asyncio.run(svc.get_recommendations("S001")).model_dump_json()

    for idx in range(19):
        resp = asyncio.run(svc.get_recommendations("S001")).model_dump_json()
        assert resp == first_resp, f"Run #{idx+2} differed from baseline"


def check_17_mock_offline_guarantee():
    """Check 17: Mock Offline Guarantee (DEEPSEEK_ENABLED=false 离线默认保证，零外部网络请求)"""
    assert gateway_settings.deepseek_enabled is False, "DEEPSEEK_ENABLED must default to False"
    svc = RecommendationService()
    provider = svc._resolve_provider()
    assert isinstance(provider, MockDeepSeekProvider), "Must resolve to MockDeepSeekProvider in offline mode"


# ==============================================================================
# Gate 主程序
# ==============================================================================

def main():
    print("=" * 76)
    print("Sprint 10-B / Phase 2 — DeepSeek Recommendation & Validation Quality Gate")
    print("=" * 76)

    checks = [
        (1, "Provider Contract", check_01_provider_contract),
        (2, "Candidate Schema", check_02_candidate_schema),
        (3, "Valid Candidate [Case A]", check_03_valid_candidate),
        (4, "Invalid Knowledge [Case C]", check_04_invalid_knowledge),
        (5, "Invalid Resource [Case D]", check_05_invalid_resource),
        (6, "Invalid Relation", check_06_invalid_relation),
        (7, "Duplicate Candidate [Case E]", check_07_duplicate_candidate),
        (8, "Empty Response [Case F]", check_08_empty_response),
        (9, "Malformed Response [Case G]", check_09_malformed_response),
        (10, "PII Firewall", check_10_pii_firewall),
        (11, "allow_production_decision=False", check_11_allow_production_decision_invariant),
        (12, "BKT Unchanged (0 mutation)", check_12_bkt_unchanged),
        (13, "PathState Unchanged (0 mutation)", check_13_path_state_unchanged),
        (14, "Learning Events Unchanged (0 mutation)", check_14_learning_events_unchanged),
        (15, "Resource Events Unchanged (0 mutation)", check_15_resource_events_unchanged),
        (16, "Deterministic 20x Repeated Runs", check_16_deterministic_20x),
        (17, "Mock Offline Guarantee", check_17_mock_offline_guarantee),
    ]

    passed_count = 0
    failed_count = 0
    undefined_count = 0

    for num, title, fn in checks:
        prefix = f"[{num:02d}/17] {title}"
        dots = "." * max(2, 64 - len(prefix))
        print(f"{prefix} {dots} ", end="", flush=True)
        try:
            status = fn()
            if status == "UNDEFINED_BOUNDARY":
                print("UNDEFINED_BOUNDARY")
                undefined_count += 1
            else:
                print("PASS")
                passed_count += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed_count += 1

    print("=" * 76)
    print(f"Gate Summary: {passed_count} PASSED, {undefined_count} UNDEFINED_BOUNDARY, {failed_count} FAILED")
    print("=" * 76)

    if failed_count == 0:
        print("RESULT: PASS (All invariants held with FAIL == 0)")
        sys.exit(0)
    else:
        print("RESULT: FAIL (Quality Gate blocked due to invariant violation)")
        sys.exit(1)


if __name__ == "__main__":
    main()
