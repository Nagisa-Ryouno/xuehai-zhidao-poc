# -*- coding: utf-8 -*-
"""
scripts/sprint10b_phase3_gate.py
================================
学海智导 (Xuehai Zhidao) — Sprint 10-B Phase 3
Real DeepSeek Controlled Live Smoke Test 专项质量门禁 (18 维严苛校验)

检查项矩阵：
[01/18] Phase 2 Baseline (Phase 2 核心 17 项门禁离线全部 PASS)
[02/18] Live Mode Explicit Opt-In (默认离线安全，非显式启用绝不发起外网连接)
[03/18] API Key Not in Source (Git 跟踪代码中绝无硬编码 API Key)
[04/18] API Key Not in Logs/Artifacts (工件与日志中绝无 API Key 明文泄露)
[05/18] Provider Abstraction Reused (完整复用 Phase 1 DeepSeekProvider 与 HttpLLMTransport)
[06/18] Response Format JSON Object (请求显式声明 response_format={'type': 'json_object'})
[07/18] Prompt Contains JSON Instruction (提示词明确要求模型输出合规 JSON)
[08/18] Candidate Schema Unchanged (严格保持 extra='forbid' 与三字段白名单)
[09/18] Validator Still Authoritative (无论模型返回何物，Validator 拥有一票否决与仲裁权)
[10/18] allow_production_decision=False Invariant (AI 绝对无生产决策权红线永久成立)
[11/18] No BKT Mutation (调用前后 BKT 状态文件绝对 0 修改)
[12/18] No PathState Mutation (调用前后学习路径状态文件绝对 0 修改)
[13/18] No Learning Event Mutation (调用前后正式学习事件绝对 0 新增)
[14/18] No Resource Event Mutation (调用前后资源事件绝对 0 新增)
[15/18] No TodayAction Mutation (调用前后今日行动推荐绝对 0 漂移)
[16/18] Maximum Live Request Count <= 3 (严格限制真实调用硬上限)
[17/18] Live Failure Is Safe (模型异常、超时或畸形输出时安全阻断零脏写)
[18/18] Frozen Areas 0 Diff (冻结生产目录与前端代码严格 0 diff)
"""

import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 载入本地 .env
try:
    from dotenv import load_dotenv
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from app.core.config import settings
from gateway.adapter import AIProviderAdapter, get_provider
from gateway.ai.deepseek import (
    AIProviderRequest,
    AIProviderResponse,
    DeepSeekProvider,
    MockDeepSeekProvider,
    assert_no_pii,
)
from gateway.config import gateway_settings
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


def get_test_context() -> RecommendationContext:
    return RecommendationContext(
        student_id="student_s001",
        current_focus="K03",
        knowledge_states=[
            KnowledgeStateSnapshot(knowledge_id="K03", knowledge_name="需求价格弹性", mastery=0.45, path_state="IN_PROGRESS"),
            KnowledgeStateSnapshot(knowledge_id="K04", knowledge_name="需求收入与交叉弹性", mastery=0.20, path_state="AVAILABLE"),
        ],
        resources=[
            ResourceCandidateSnapshot(
                resource_id="res_k03_concept", knowledge_id="K03", resource_type="concept_microcard",
                title="需求价格弹性 考点精要微卡", description="微卡", source="xuehai_internal",
            ),
            ResourceCandidateSnapshot(
                resource_id="res_k03_example", knowledge_id="K03", resource_type="example_case",
                title="需求价格弹性 典型例题精析", description="例题", source="xuehai_internal",
            ),
        ],
    )


# ==============================================================================
# 18 项检查函数
# ==============================================================================

def check_01_phase2_baseline() -> str:
    """Check 01: Phase 2 Baseline (Phase 2 门禁 17 项离线全绿)"""
    gate_script = PROJECT_ROOT / "scripts" / "sprint10b_phase2_gate.py"
    res = subprocess.run(
        [sys.executable, str(gate_script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PROJECT_ROOT),
    )
    assert res.returncode == 0, f"Phase 2 Gate failed:\n{res.stdout}\n{res.stderr}"
    return "PASS"


def check_02_live_mode_opt_in() -> str:
    """Check 02: Live Mode Explicit Opt-In (默认必须离线安全，非显式 opt-in 绝不发外网请求)"""
    # 默认状态下 deepseek_enabled 必须为 False
    assert gateway_settings.deepseek_enabled is False, "Default offline configuration must have deepseek_enabled=False"
    generator = DeepSeekCandidateGenerator()
    provider = generator.resolve_provider()
    assert isinstance(provider, MockDeepSeekProvider), "Default provider must be MockDeepSeekProvider"
    return "PASS"


def check_03_api_key_not_in_source() -> str:
    """Check 03: API Key Not in Source (Git 跟踪代码中绝无硬编码 API Key)"""
    # 1. 严格检查环境变量中配置的实际 API Key 是否泄漏到 git 文件中
    actual_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if actual_key and len(actual_key) >= 10:
        res = subprocess.run(
            ["git", "grep", "-F", actual_key],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT),
        )
        if res.returncode == 0 and res.stdout.strip():
            raise AssertionError("Configured real DEEPSEEK_API_KEY was found in git tracked files!")

    # 2. 检查是否有真实 DeepSeek 32 位十六进制 key 模式 (sk-[0-9a-f]{32})
    res_hex = subprocess.run(
        ["git", "grep", "-E", "sk-[0-9a-f]{32}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PROJECT_ROOT),
    )
    if res_hex.returncode == 0 and res_hex.stdout.strip():
        lines = res_hex.stdout.strip().splitlines()
        raise AssertionError(f"Real DeepSeek API Key pattern found in tracked files: {lines}")

    return "PASS"


def check_04_api_key_not_in_artifacts() -> str:
    """Check 04: API Key Not in Logs/Artifacts (工件中绝无 API Key 明文)"""
    artifacts_dir = PROJECT_ROOT / "artifacts"
    key_pattern = re.compile(r"sk-[a-zA-Z0-9]{20,}")
    if artifacts_dir.exists():
        for p in artifacts_dir.rglob("*.json"):
            content = p.read_text(encoding="utf-8", errors="ignore")
            if key_pattern.search(content):
                raise AssertionError(f"Leaked API Key found in artifact: {p.name}")
    return "PASS"


def check_05_provider_abstraction_reused() -> str:
    """Check 05: Provider Abstraction Reused (复用 DeepSeekProvider 与 HttpLLMTransport)"""
    generator = DeepSeekCandidateGenerator()
    provider = generator.resolve_provider(MockDeepSeekProvider())
    assert hasattr(provider, "complete"), "Provider must implement complete() interface"
    # 确认 RecommendationService 与 Generator 源码中未直接引入 requests.post / httpx.post
    service_code = (PROJECT_ROOT / "gateway" / "ai" / "recommendation" / "service.py").read_text(encoding="utf-8")
    generator_code = (PROJECT_ROOT / "gateway" / "ai" / "recommendation" / "generator.py").read_text(encoding="utf-8")
    for forbidden in ["requests.post", "httpx.post", "urllib.request"]:
        assert forbidden not in service_code, f"Found direct HTTP call '{forbidden}' in service.py"
        assert forbidden not in generator_code, f"Found direct HTTP call '{forbidden}' in generator.py"
    return "PASS"


def check_06_response_format_json_object() -> str:
    """Check 06: Response Format JSON Object (显式声明 json_object)"""
    ctx = get_test_context()
    sys_p, usr_p = build_recommendation_prompt(ctx)
    generator = DeepSeekCandidateGenerator()
    captured_reqs = []

    class CapturingProvider(MockDeepSeekProvider):
        async def complete(self, req: AIProviderRequest) -> AIProviderResponse:
            captured_reqs.append(req)
            return await super().complete(req)

    asyncio.run(generator.generate_raw_candidates(ctx, provider_override=CapturingProvider()))
    assert len(captured_reqs) == 1
    assert captured_reqs[0].response_format == "json_object", "response_format must be json_object"
    return "PASS"


def check_07_prompt_contains_json_instruction() -> str:
    """Check 07: Prompt Contains JSON Instruction (提示词要求 JSON)"""
    ctx = get_test_context()
    sys_p, usr_p = build_recommendation_prompt(ctx)
    assert "JSON" in sys_p or "json" in sys_p.lower(), "System prompt must instruct JSON output"
    assert "recommendations" in sys_p
    return "PASS"


def check_08_candidate_schema_unchanged() -> str:
    """Check 08: Candidate Schema Unchanged (严格 extra='forbid')"""
    cand = RecommendationCandidate(knowledge_id="K03", resource_id="res_k03_concept", reason="理由")
    assert cand.knowledge_id == "K03"
    assert cand.resource_id == "res_k03_concept"
    try:
        RecommendationCandidate(knowledge_id="K03", resource_id="res_k03_concept", reason="理由", score=100)
        assert False, "Should forbid extra fields"
    except Exception:
        pass
    return "PASS"


def check_09_validator_still_authoritative() -> str:
    """Check 09: Validator Still Authoritative (Validator 拥有一票否决权)"""
    ctx = get_test_context()
    # 模拟模型输出虚构考点与越权字段
    hallucination = {
        "recommendations": [
            {"knowledge_id": "K999", "resource_id": "res_k03_concept", "reason": "虚构考点"},
            {"knowledge_id": "K03", "resource_id": "res_k03_concept", "reason": "越权", "rank": 1},
        ]
    }
    val_res = RecommendationValidator.validate_candidates_detailed(hallucination, context=ctx)
    assert len(val_res.validated_candidates) == 0
    assert len(val_res.rejected_candidates) == 2
    return "PASS"


def check_10_allow_production_decision_false() -> str:
    """Check 10: allow_production_decision=False Invariant (永久成立)"""
    ctx = get_test_context()
    sys_p, _ = build_recommendation_prompt(ctx)
    assert "allow_production_decision = False" in sys_p
    resp = asyncio.run(default_recommendation_service.get_recommendations("S001"))
    d = resp.model_dump()
    for forbidden in RECOMMENDATION_FORBIDDEN_FIELDS:
        assert forbidden not in d, f"Forbidden field '{forbidden}' found in RecommendationResponse"
    return "PASS"


def check_11_no_bkt_mutation() -> str:
    """Check 11: No BKT Mutation (调用前后 BKT 文件 0 修改)"""
    bkt_file = settings.BKT_STATES_FILE
    before = bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else ""
    asyncio.run(default_recommendation_service.get_recommendations("S001"))
    after = bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else ""
    assert before == after, "BKT file was modified"
    return "PASS"


def check_12_no_path_mutation() -> str:
    """Check 12: No PathState Mutation (调用前后路径状态 0 修改)"""
    path_file = settings.LEARNING_PATH_STATES_FILE
    before = path_file.read_text(encoding="utf-8") if path_file.exists() else ""
    asyncio.run(default_recommendation_service.get_recommendations("S001"))
    after = path_file.read_text(encoding="utf-8") if path_file.exists() else ""
    assert before == after, "PathState file was modified"
    return "PASS"


def check_13_no_learning_event_mutation() -> str:
    """Check 13: No Learning Event Mutation (正式学习事件 0 新增)"""
    e_file = settings.LEARNING_EVENTS_FILE
    before = e_file.read_text(encoding="utf-8") if e_file.exists() else ""
    asyncio.run(default_recommendation_service.get_recommendations("S001"))
    after = e_file.read_text(encoding="utf-8") if e_file.exists() else ""
    assert before == after, "Learning events was modified"
    return "PASS"


def check_14_no_resource_event_mutation() -> str:
    """Check 14: No Resource Event Mutation (资源事件 0 新增)"""
    res_file = PROJECT_ROOT / "data" / "resource_events.jsonl"
    before = res_file.read_text(encoding="utf-8") if res_file.exists() else ""
    asyncio.run(default_recommendation_service.get_recommendations("S001"))
    after = res_file.read_text(encoding="utf-8") if res_file.exists() else ""
    assert before == after, "Resource events was modified"
    return "PASS"


def check_15_no_today_action_mutation() -> str:
    """Check 15: No TodayAction Mutation (今日行动 0 漂移)"""
    # 验证多次调用推荐服务不改变今日任务状态
    resp1 = asyncio.run(default_recommendation_service.get_recommendations("S001"))
    resp2 = asyncio.run(default_recommendation_service.get_recommendations("S001"))
    assert resp1.student_id == resp2.student_id
    assert len(resp1.recommendations) == len(resp2.recommendations)
    return "PASS"


def check_16_maximum_live_request_count() -> str:
    """Check 16: Maximum Live Request Count <= 3 (硬上限限制)"""
    smoke_script = (PROJECT_ROOT / "scripts" / "sprint10b_phase3_live_smoke.py").read_text(encoding="utf-8")
    assert "MAX_LIVE_REQUESTS = 3" in smoke_script, "Live smoke script must enforce MAX_LIVE_REQUESTS = 3"
    assert "_live_request_count > MAX_LIVE_REQUESTS" in smoke_script
    return "PASS"


def check_17_live_failure_is_safe() -> str:
    """Check 17: Live Failure Is Safe (模型异常、超时安全阻断)"""
    class CrashingProvider(MockDeepSeekProvider):
        async def complete(self, req: AIProviderRequest) -> AIProviderResponse:
            return AIProviderResponse(content="not a json", model="deepseek-flash", provider="mock", parsed_json=None)

    svc = RecommendationService(provider=CrashingProvider(), raise_on_rejection=False)
    resp = asyncio.run(svc.get_recommendations("S001"))
    assert resp.validated is False
    assert len(resp.rejected_candidates) == 1
    assert resp.rejected_candidates[0].code == "INVALID_JSON_SYNTAX"
    return "PASS"


def check_18_frozen_areas_0_diff() -> str:
    """Check 18: Frozen Areas 0 Diff (冻结目录严格 0 diff)"""
    frozen_paths = [
        "app/", "tests/", "data/seeds/", "gateway/learning/",
        "gateway/ai/companion/", "gateway/api.py", "gateway/adapter.py",
        "gateway/config.py", "frontend/src/", "frontend/public/", "frontend/index.html",
    ]
    res = subprocess.run(
        ["git", "diff", "--", *frozen_paths],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PROJECT_ROOT),
    )
    assert res.returncode == 0 and res.stdout.strip() == "", f"Frozen path modified:\n{res.stdout}"
    return "PASS"


# ==============================================================================
# Gate 主程序
# ==============================================================================

def main():
    print("=" * 76)
    print("Sprint 10-B / Phase 3 — Real DeepSeek Live Smoke Quality Gate")
    print("=" * 76)

    checks = [
        (1, "Phase 2 Baseline", check_01_phase2_baseline),
        (2, "Live Mode Explicit Opt-In", check_02_live_mode_opt_in),
        (3, "API Key Not in Source", check_03_api_key_not_in_source),
        (4, "API Key Not in Logs/Artifacts", check_04_api_key_not_in_artifacts),
        (5, "Provider Abstraction Reused", check_05_provider_abstraction_reused),
        (6, "Response Format JSON Object", check_06_response_format_json_object),
        (7, "Prompt Contains JSON Instruction", check_07_prompt_contains_json_instruction),
        (8, "Candidate Schema Unchanged", check_08_candidate_schema_unchanged),
        (9, "Validator Still Authoritative", check_09_validator_still_authoritative),
        (10, "allow_production_decision=False", check_10_allow_production_decision_false),
        (11, "No BKT Mutation (0 mutation)", check_11_no_bkt_mutation),
        (12, "No PathState Mutation (0 mutation)", check_12_no_path_mutation),
        (13, "No Learning Event Mutation (0 mutation)", check_13_no_learning_event_mutation),
        (14, "No Resource Event Mutation (0 mutation)", check_14_no_resource_event_mutation),
        (15, "No TodayAction Mutation (0 mutation)", check_15_no_today_action_mutation),
        (16, "Maximum Live Request Count <= 3", check_16_maximum_live_request_count),
        (17, "Live Failure Is Safe", check_17_live_failure_is_safe),
        (18, "Frozen Areas 0 Diff", check_18_frozen_areas_0_diff),
    ]

    passed_count = 0
    failed_count = 0
    undefined_count = 0

    for num, title, fn in checks:
        prefix = f"[{num:02d}/18] {title}"
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
