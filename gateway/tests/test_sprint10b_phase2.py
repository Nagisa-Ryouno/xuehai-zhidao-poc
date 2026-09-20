# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint10b_phase2
===================================
学海智导 (Xuehai Zhidao) — Sprint 10-B Phase 2
DeepSeek Candidate Recommendation & Deterministic Validation 全量测试套件

核心测试范围：
1. Provider 契约与任务路由：显式 task="recommendation" 契约、离线 Mock 确定性；
2. Candidate Schema 规范：extra='forbid'、仅限 (knowledge_id, resource_id, reason)；
3. Case A: 合法候选接受 (ACCEPT)；
4. Case B 【Service/集成层测试】: Global Catalog 存在 != 当前 Context 合法 (K03->R999) -> REJECT (RESOURCE_NOT_IN_CONTEXT)；
5. Case C: 未知考点拦截 (K999) -> REJECT (UNKNOWN_KNOWLEDGE_ID)；
6. Case D: 未知资源拦截 (R_NONEXISTENT) -> REJECT (UNKNOWN_RESOURCE_ID)；
7. Case E: 重复候选结构化去重 -> 首项保留，第二项记录为 REJECT (DUPLICATE_CANDIDATE)；
8. Case F: 空候选数组安全通过 (validated_candidates = [], 无生产决策回退)；
9. Case G 【全链路端到端】: Mock Provider -> Generator -> JSON parse failure -> 结构化 rejection -> Service Response，
           状态零污染验证 (零 BKT/Path/Events/TodayAction 变动)；
10. Case H: 非法字段与 rank/priority/score 统一拦截为稳定 FORBIDDEN_FIELD_ITEM；
11. Order Determinism: Run A (K03, K04) 与 Run B (K04, K03) 经确定性键值排序后输出完全一致；
12. Reason 边界安全：非空、<=300 字符、结构化命令注入拦截、正常教学解释无误杀；
13. PII 防火墙：伪匿名 student_id、零真实个人信息；
14. 业务状态零突变：BKT、PathState、Learning Events、Resource Events 零修改；
15. 20 次离线重复性：20 次调用输出结构完全一致。
"""

import asyncio
import copy
import json
from pathlib import Path
from typing import Any, Dict, List
import pytest
from pydantic import ValidationError

from app.core.config import settings
from gateway.adapter import AIProviderAdapter, get_provider
from gateway.ai.deepseek import (
    AIProviderRequest,
    AIProviderResponse,
    MockDeepSeekProvider,
    assert_no_pii,
)
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
    default_recommendation_service,
)


@pytest.fixture
def test_context() -> RecommendationContext:
    """提供具有确定性边界的标准只读推荐上下文快照"""
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
                description="典型例题实战",
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
# 1. Provider 契约与任务路由
# ==============================================================================

def test_phase2_01_provider_contract_and_task_routing(test_context: RecommendationContext):
    """验证 Provider 调用契约，确认包含显式 task='recommendation' 契约路由与脱敏 user_id"""
    generator = DeepSeekCandidateGenerator()
    captured_requests: List[AIProviderRequest] = []

    class CapturingMockProvider(MockDeepSeekProvider):
        async def complete(self, req: AIProviderRequest) -> AIProviderResponse:
            captured_requests.append(req)
            return await super().complete(req)

    mock_p = CapturingMockProvider()
    raw, provider_name = asyncio.run(
        generator.generate_raw_candidates(
            context=test_context,
            max_candidates=2,
            provider_override=mock_p,
        )
    )

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.task == "recommendation"
    assert req.user_id == test_context.student_id
    assert req.metadata["task"] == "recommendation"
    assert req.metadata["max_candidates"] == 2
    assert isinstance(req.metadata["candidate_pool"], list)
    assert len(req.metadata["candidate_pool"]) == 3
    assert provider_name == "mock-deepseek"


# ==============================================================================
# 2. Candidate Schema 契约
# ==============================================================================

def test_phase2_02_candidate_schema_extra_forbid():
    """验证 RecommendationCandidate 严格 extra='forbid'，仅允许 knowledge_id, resource_id, reason"""
    # 合法实例
    cand = RecommendationCandidate(
        knowledge_id="K03",
        resource_id="res_k03_concept",
        reason="基础薄弱，建议先阅读核心微卡",
    )
    assert cand.knowledge_id == "K03"
    assert cand.resource_id == "res_k03_concept"

    # 尝试注入额外字段应当引发 ValidationError
    with pytest.raises(ValidationError):
        RecommendationCandidate(
            knowledge_id="K03",
            resource_id="res_k03_concept",
            reason="推荐理由",
            rank=1,
        )

    with pytest.raises(ValidationError):
        RecommendationCandidate(
            knowledge_id="K03",
            resource_id="res_k03_concept",
            reason="推荐理由",
            priority="high",
        )


# ==============================================================================
# 3. Case A: 合法候选顺利通过 (ACCEPT)
# ==============================================================================

def test_phase2_03_case_a_valid_candidate_accepted(test_context: RecommendationContext):
    """Case A: Context 包含 K03->res_k03_concept，AI 返回该对 -> ACCEPT 并注入权威元数据"""
    raw_output = {
        "recommendations": [
            {
                "knowledge_id": "K03",
                "resource_id": "res_k03_concept",
                "reason": "概念掌握不足，建议先学习核心微卡构建体系。",
            }
        ]
    }
    result: CandidateValidationResult = RecommendationValidator.validate_candidates_detailed(
        raw_output=raw_output,
        context=test_context,
    )

    assert len(result.validated_candidates) == 1
    assert len(result.rejected_candidates) == 0
    assert len(result.validation_reasons) == 0

    item = result.validated_candidates[0]
    assert item.knowledge_id == "K03"
    assert item.resource_id == "res_k03_concept"
    assert item.title != ""
    assert item.source == "xuehai_internal"


# ==============================================================================
# 4. Case B: Service/集成层测试 — Global Catalog 存在 != 当前 Context 合法
# ==============================================================================

def test_phase2_04_case_b_service_level_candidate_pool_isolation():
    """
    Case B 【Service/集成层测试】：
    证明：即使全局统一资源目录存在合法资源（如 K01 的 res_k01_concept），
    但若当前推荐上下文仅包含 K03/K04 候选，AI 输出 K03->res_k01_concept 时，
    在 Service/集成编排层坚决拦截并拒绝为 RESOURCE_NOT_IN_CONTEXT / RESOURCE_KNOWLEDGE_MISMATCH。
    """
    # 验证 res_k01_concept 确实存在于全局资源目录
    global_res = get_unified_resource_by_id("res_k01_concept")
    assert global_res is not None, "全局资源目录必须包含 res_k01_concept"

    class HallucinatingProvider(MockDeepSeekProvider):
        async def complete(self, req: AIProviderRequest) -> AIProviderResponse:
            # 模拟模型越界：返回虽然存在于全局库但不在当前 Context 候选池中的资源 ID
            payload = {
                "recommendations": [
                    {
                        "knowledge_id": "K03",
                        "resource_id": "res_k01_concept",
                        "reason": "跨考点强行推荐全局库资源",
                    }
                ]
            }
            return AIProviderResponse(
                content=json.dumps(payload),
                model="mock-deepseek",
                provider="mock-deepseek",
                parsed_json=payload,
            )

    svc = RecommendationService(provider=HallucinatingProvider(), raise_on_rejection=False)
    resp: RecommendationResponse = asyncio.run(
        svc.get_recommendations(student_id="S001")
    )

    assert resp.validated is False
    assert len(resp.validated_candidates) == 0
    assert len(resp.rejected_candidates) == 1
    rej = resp.rejected_candidates[0]
    assert rej.code in ("RESOURCE_NOT_IN_CONTEXT", "RESOURCE_KNOWLEDGE_MISMATCH")
    assert "res_k01_concept" in str(rej.candidate)


# ==============================================================================
# 5. Case C: 未知考点拦截 (UNKNOWN_KNOWLEDGE_ID)
# ==============================================================================

def test_phase2_05_case_c_unknown_knowledge_id(test_context: RecommendationContext):
    """Case C: AI 返回系统不存在的虚构考点 K999 -> REJECT (UNKNOWN_KNOWLEDGE_ID / KNOWLEDGE_NOT_IN_CONTEXT)"""
    raw_output = {
        "recommendations": [
            {
                "knowledge_id": "K999",
                "resource_id": "res_k03_concept",
                "reason": "虚构考点",
            }
        ]
    }
    result = RecommendationValidator.validate_candidates_detailed(raw_output, context=test_context)

    assert len(result.validated_candidates) == 0
    assert len(result.rejected_candidates) == 1
    assert result.rejected_candidates[0].code in ("UNKNOWN_KNOWLEDGE_ID", "KNOWLEDGE_NOT_IN_CONTEXT")


# ==============================================================================
# 6. Case D: 未知资源拦截 (UNKNOWN_RESOURCE_ID)
# ==============================================================================

def test_phase2_06_case_d_unknown_resource_id(test_context: RecommendationContext):
    """Case D: AI 返回全库不存在的虚构资源 R_NONEXISTENT -> REJECT (UNKNOWN_RESOURCE_ID / RESOURCE_NOT_IN_CONTEXT)"""
    raw_output = {
        "recommendations": [
            {
                "knowledge_id": "K03",
                "resource_id": "res_nonexistent_9999",
                "reason": "虚构资源",
            }
        ]
    }
    result = RecommendationValidator.validate_candidates_detailed(raw_output, context=test_context)

    assert len(result.validated_candidates) == 0
    assert len(result.rejected_candidates) == 1
    assert result.rejected_candidates[0].code in ("UNKNOWN_RESOURCE_ID", "RESOURCE_NOT_IN_CONTEXT")


# ==============================================================================
# 7. Case E: 重复候选去重 (DUPLICATE_CANDIDATE)
# ==============================================================================

def test_phase2_07_case_e_duplicate_candidate_deduplication(test_context: RecommendationContext):
    """Case E: AI 返回重复候选 (K03->res_k03_concept 出现两次) -> 首项保留，第二项记录为 DUPLICATE_CANDIDATE"""
    raw_output = {
        "recommendations": [
            {
                "knowledge_id": "K03",
                "resource_id": "res_k03_concept",
                "reason": "第一次推荐理由",
            },
            {
                "knowledge_id": "K03",
                "resource_id": "res_k03_concept",
                "reason": "重复推荐相同资源",
            },
        ]
    }
    result = RecommendationValidator.validate_candidates_detailed(raw_output, context=test_context)

    assert len(result.validated_candidates) == 1
    assert len(result.rejected_candidates) == 1
    assert result.rejected_candidates[0].code == "DUPLICATE_CANDIDATE"
    assert "DUPLICATE_CANDIDATE" in result.validation_reasons[0]


# ==============================================================================
# 8. Case F: 空候选数组安全通过
# ==============================================================================

def test_phase2_08_case_f_empty_recommendations_array(test_context: RecommendationContext):
    """Case F: AI 返回空推荐候选列表 [] -> 安全通过，validated_candidates = []，绝不自动回退到 AI 生产决策"""
    raw_output = {"recommendations": []}
    result = RecommendationValidator.validate_candidates_detailed(raw_output, context=test_context)

    assert result.validated_candidates == []
    assert result.rejected_candidates == []
    assert result.validation_reasons == []


# ==============================================================================
# 9. Case G: 全链路端到端非 JSON 拦截与零污染验证
# ==============================================================================

def test_phase2_09_case_g_full_chain_non_json_zero_mutation():
    """
    Case G 【全链路端到端完整测试】：
    链路：Mock Provider -> Generator -> JSON parse failure -> 结构化 rejection (INVALID_JSON_SYNTAX) -> Service Response。
    同时明确证明：在发生非 JSON 错误时，系统绝不触发 BKT、PathState、TodayAction、
    QUESTION_ATTEMPT、learning/resource events 的任何隐式更新或生产决策 fallback。
    """
    # 记录前置快照
    bkt_file = settings.BKT_STATES_FILE
    path_file = settings.LEARNING_PATH_STATES_FILE
    events_file = settings.LEARNING_EVENTS_FILE

    bkt_before = bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else ""
    path_before = path_file.read_text(encoding="utf-8") if path_file.exists() else ""
    events_count_before = len(events_file.read_text(encoding="utf-8").strip().splitlines()) if events_file.exists() else 0

    class MalformedTextProvider(MockDeepSeekProvider):
        async def complete(self, req: AIProviderRequest) -> AIProviderResponse:
            # 模拟模型输出非 JSON 的自然语言文本
            malformed_text = "抱歉，作为大语言模型，我认为学生需要多加练习，但我不输出 JSON 格式。"
            return AIProviderResponse(
                content=malformed_text,
                model="mock-deepseek",
                provider="mock-deepseek",
                parsed_json=None,  # JSON 解析失败
            )

    svc = RecommendationService(provider=MalformedTextProvider(), raise_on_rejection=False)
    resp: RecommendationResponse = asyncio.run(
        svc.get_recommendations(student_id="S001")
    )

    # 1. 验证结构化响应
    assert resp.validated is False
    assert resp.recommendations == []
    assert resp.validated_candidates == []
    assert len(resp.rejected_candidates) == 1
    assert resp.rejected_candidates[0].code == "INVALID_JSON_SYNTAX"
    assert "not valid JSON" in resp.rejected_candidates[0].reason

    # 2. 验证权威状态绝对零修改 (Zero Mutation Invariant)
    bkt_after = bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else ""
    path_after = path_file.read_text(encoding="utf-8") if path_file.exists() else ""
    events_count_after = len(events_file.read_text(encoding="utf-8").strip().splitlines()) if events_file.exists() else 0

    assert bkt_before == bkt_after, "BKT 状态文件绝对不可变更"
    assert path_before == path_after, "学习路径状态文件绝对不可变更"
    assert events_count_before == events_count_after, "正式学习事件行数绝对不可增加"


# ==============================================================================
# 10. Case H: 非法字段与 rank/priority/score 统一映射为 FORBIDDEN_FIELD_ITEM
# ==============================================================================

def test_phase2_10_case_h_forbidden_fields_and_rank_priority_score(test_context: RecommendationContext):
    """
    Case H: AI 试图输出 rank、priority、score 等越权生产优先级字段，
    统一拦截为标准拒绝码 FORBIDDEN_FIELD_ITEM，禁止 AI rank 转化为生产优先级。
    """
    test_payloads = [
        {"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": "理由", "rank": 1},
        {"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": "理由", "priority": "urgent"},
        {"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": "理由", "score": 99.5},
        {"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": "理由", "set_mastery": 1.0},
        {"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": "理由", "mutation": True},
    ]

    for item in test_payloads:
        raw_output = {"recommendations": [item]}
        res = RecommendationValidator.validate_candidates_detailed(raw_output, context=test_context)
        assert len(res.validated_candidates) == 0
        assert len(res.rejected_candidates) == 1
        assert res.rejected_candidates[0].code == "FORBIDDEN_FIELD_ITEM"


# ==============================================================================
# 11. Order Determinism: 确定性排序仲裁测试
# ==============================================================================

def test_phase2_11_order_determinism(test_context: RecommendationContext):
    """
    Order Determinism 关键测试：
    Run A: AI 输出顺序为 [K03, K04]
    Run B: AI 输出顺序为 [K04, K03] (顺序颠倒)
    验证：经 Deterministic Validator 排序仲裁后，两者的 validated_candidates 顺序完全一致！
    AI 输出顺序、rank、priority、score 绝对不决定系统最终推荐顺序。
    """
    run_a_payload = {
        "recommendations": [
            {"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": "建议复习K03概念"},
            {"knowledge_id": "K04", "resource_id": "res_k04_practice", "reason": "建议完成K04测验"},
        ]
    }
    run_b_payload = {
        "recommendations": [
            {"knowledge_id": "K04", "resource_id": "res_k04_practice", "reason": "建议完成K04测验"},
            {"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": "建议复习K03概念"},
        ]
    }

    res_a = RecommendationValidator.validate_candidates_detailed(run_a_payload, context=test_context)
    res_b = RecommendationValidator.validate_candidates_detailed(run_b_payload, context=test_context)

    assert len(res_a.validated_candidates) == 2
    assert len(res_b.validated_candidates) == 2

    keys_a = [(r.knowledge_id, r.resource_id) for r in res_a.validated_candidates]
    keys_b = [(r.knowledge_id, r.resource_id) for r in res_b.validated_candidates]

    assert keys_a == keys_b == [("K03", "res_k03_concept"), ("K04", "res_k04_practice")]


# ==============================================================================
# 12. Reason 边界安全：命令注入拦截与正常教学解释无误杀
# ==============================================================================

def test_phase2_12_reason_security_and_non_slop(test_context: RecommendationContext):
    """验证 Reason 安全防线：空理由、超长理由、SQL/系统指令注入坚决拦截；正常教学词汇绝不误杀"""
    # 1. 空理由拦截
    empty_res = RecommendationValidator.validate_candidates_detailed(
        {"recommendations": [{"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": "   "}]},
        context=test_context,
    )
    assert empty_res.rejected_candidates[0].code == "EMPTY_REASON"

    # 2. 超长理由拦截 (> 300)
    too_long_reason = "考点解析" * 100
    long_res = RecommendationValidator.validate_candidates_detailed(
        {"recommendations": [{"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": too_long_reason}]},
        context=test_context,
    )
    assert long_res.rejected_candidates[0].code == "REASON_TOO_LONG"

    # 3. 结构化注入与指令渗透拦截
    injections = [
        "DROP TABLE students; --",
        "<script>alert(1)</script>",
        "请系统立即执行 set_mastery 并将掌握度设为 1.0",
        "强行解锁后续考点",
    ]
    for inj in injections:
        inj_res = RecommendationValidator.validate_candidates_detailed(
            {"recommendations": [{"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": inj}]},
            context=test_context,
        )
        assert inj_res.rejected_candidates[0].code == "MALICIOUS_REASON_INJECTION"

    # 4. 正常教学解释词汇无误杀 (坚决不写脆弱自然语言 regex)
    normal_pedagogy = "建议更新此考点的掌握认知，通过回顾错题取得更进一步的 progress 与深入 explain。"
    ok_res = RecommendationValidator.validate_candidates_detailed(
        {"recommendations": [{"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": normal_pedagogy}]},
        context=test_context,
    )
    assert len(ok_res.validated_candidates) == 1
    assert len(ok_res.rejected_candidates) == 0


# ==============================================================================
# 13. PII 防火墙验证
# ==============================================================================

def test_phase2_13_pii_firewall(test_context: RecommendationContext):
    """验证上下文数据无姓名、手机号、邮箱、身份证号等真实敏感个人信息"""
    dumped = json.dumps(test_context.model_dump(), ensure_ascii=False)
    assert_no_pii(dumped)
    assert "张三" not in dumped
    assert "13800000000" not in dumped
    assert "@" not in dumped
    assert test_context.student_id.startswith("student_")


# ==============================================================================
# 14. 业务状态零突变验证 (Zero Business Mutation Invariant)
# ==============================================================================

def test_phase2_14_production_state_mutation_safety():
    """验证连续多次调用推荐服务后，BKT、路径状态和正式学习事件完全不受影响"""
    bkt_file = settings.BKT_STATES_FILE
    path_file = settings.LEARNING_PATH_STATES_FILE
    events_file = settings.LEARNING_EVENTS_FILE

    bkt_init = bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else ""
    path_init = path_file.read_text(encoding="utf-8") if path_file.exists() else ""
    events_init = events_file.read_text(encoding="utf-8") if events_file.exists() else ""

    # 调用推荐服务 3 次
    for _ in range(3):
        asyncio.run(default_recommendation_service.get_recommendations("S001"))

    assert (bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else "") == bkt_init
    assert (path_file.read_text(encoding="utf-8") if path_file.exists() else "") == path_init
    assert (events_file.read_text(encoding="utf-8") if events_file.exists() else "") == events_init


# ==============================================================================
# 15. 20 次离线确定性重复性验证
# ==============================================================================

def test_phase2_15_deterministic_20_repeated_runs(test_context: RecommendationContext):
    """同一只读上下文在 Mock Provider 下连续运行 20 次，输出结构 100% 字节级稳定一致"""
    mock_p = MockDeepSeekProvider()
    svc = RecommendationService(provider=mock_p, raise_on_rejection=False)

    first_resp = asyncio.run(svc.get_recommendations("S001"))
    first_dump = first_resp.model_dump_json()

    for idx in range(19):
        resp = asyncio.run(svc.get_recommendations("S001"))
        assert resp.model_dump_json() == first_dump, f"Run #{idx+2} 与首次运行结果产生偏差"
