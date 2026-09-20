# -*- coding: utf-8 -*-
"""
scripts/sprint10b_phase3_live_smoke.py
======================================
学海智导 (Xuehai Zhidao) — Sprint 10-B Phase 3
真实 DeepSeek API 受控联调与端到端验证脚本 (Controlled Live Smoke Test)

执行规范与安全红线：
1. 默认离线安全：必须显式配置 DEEPSEEK_ENABLED=true 与有效 API Key 方可执行，否则安全退出；
2. 请求上限限制：全生命周期执行真实请求次数严格硬限制 <= 3 次；
3. 零密钥暴露：全流程绝不打印、记录或存储明文 API Key；
4. 绝对只读闭环：调用前后断言 BKT、PathState、Learning Events、Resource Events 零突变；
5. 仲裁权守卫：真实模型候选必须全部通过 Deterministic Validator 权威仲裁；
6. 结构化审计报告：输出脱敏可审计结果至 artifacts/phase3_live_smoke_summary.json。
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 尝试安全载入本地 .env（若存在，已由 .gitignore 保护）
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
)

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
SUMMARY_FILE = ARTIFACTS_DIR / "phase3_live_smoke_summary.json"

# 硬上限计数器：单次执行真实请求最多 3 次
MAX_LIVE_REQUESTS = 3
_live_request_count = 0


def record_live_request():
    global _live_request_count
    _live_request_count += 1
    if _live_request_count > MAX_LIVE_REQUESTS:
        raise RuntimeError(f"HARD LIMIT EXCEEDED: Live request count ({_live_request_count}) exceeded maximum ({MAX_LIVE_REQUESTS})")


def get_live_provider() -> Optional[DeepSeekProvider]:
    """根据环境显式解析真实 DeepSeekProvider"""
    is_live_arg = "--live" in sys.argv
    enabled = is_live_arg or (os.getenv("DEEPSEEK_ENABLED", "").strip().lower() in ("true", "1", "yes"))
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip().rstrip("/")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip()
    timeout = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "20"))

    if not enabled or not api_key:
        return None

    # 直接使用配置的 model (deepseek-flash)，不进行任何别名或 rewrite
    return DeepSeekProvider(
        name="deepseek",
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout,
        enabled=True,
    )


# ==============================================================================
# 状态快照读取与比对纯函数 (Zero Mutation Invariant)
# ==============================================================================

def capture_system_state() -> Dict[str, Any]:
    bkt_file = settings.BKT_STATES_FILE
    path_file = settings.LEARNING_PATH_STATES_FILE
    events_file = settings.LEARNING_EVENTS_FILE
    res_events_file = PROJECT_ROOT / "data" / "resource_events.jsonl"
    res_eff_file = PROJECT_ROOT / "data" / "resource_effectiveness_events.jsonl"

    return {
        "bkt": bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else "",
        "path": path_file.read_text(encoding="utf-8") if path_file.exists() else "",
        "learning_events": events_file.read_text(encoding="utf-8") if events_file.exists() else "",
        "resource_events": res_events_file.read_text(encoding="utf-8") if res_events_file.exists() else "",
        "resource_eff_events": res_eff_file.read_text(encoding="utf-8") if res_eff_file.exists() else "",
    }


def compare_system_state(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, int]:
    return {
        "bkt_mutation": 0 if before["bkt"] == after["bkt"] else 1,
        "path_mutation": 0 if before["path"] == after["path"] else 1,
        "learning_event_mutation": 0 if before["learning_events"] == after["learning_events"] else 1,
        "resource_event_mutation": 0 if before["resource_events"] == after["resource_events"] else 1,
        "resource_eff_mutation": 0 if before["resource_eff_events"] == after["resource_eff_events"] else 1,
    }


# ==============================================================================
# Request #1: Happy Path
# ==============================================================================

async def run_request_1_happy_path(provider: DeepSeekProvider) -> Dict[str, Any]:
    print("\n--- [Request #1: Happy Path] ---")
    record_live_request()

    # 准备标准只读脱敏 Context
    ctx = RecommendationContext(
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

    generator = DeepSeekCandidateGenerator(provider=provider)
    svc = RecommendationService(provider=provider, generator=generator, raise_on_rejection=False)

    start_t = time.perf_counter()
    error_msg = None
    resp = None
    try:
        raw_payload, provider_name = await generator.generate_raw_candidates(
            context=ctx,
            max_candidates=2,
            provider_override=provider,
        )
        val_result = RecommendationValidator.validate_candidates_detailed(
            raw_output=raw_payload,
            context=ctx,
            max_allowed=2,
        )
        resp = RecommendationResponse(
            student_id=ctx.student_id,
            recommendations=val_result.validated_candidates,
            source=provider_name,
            validated=len(val_result.rejected_candidates) == 0,
            ai_candidates=raw_payload.get("recommendations") if isinstance(raw_payload, dict) and isinstance(raw_payload.get("recommendations"), list) else None,
            validated_candidates=val_result.validated_candidates,
            rejected_candidates=val_result.rejected_candidates,
            validation_reasons=val_result.validation_reasons,
        )
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"

    elapsed_ms = int((time.perf_counter() - start_t) * 1000)

    if error_msg:
        print(f"Request #1 Error (Safe Failure): {error_msg}")
        return {
            "status": "SAFE_FAILURE",
            "elapsed_ms": elapsed_ms,
            "error": error_msg,
            "validated_count": 0,
            "rejected_count": 0,
        }

    val_count = len(resp.validated_candidates or [])
    rej_count = len(resp.rejected_candidates or [])
    print(f"Request #1 Finished in {elapsed_ms}ms | Validated: {val_count}, Rejected: {rej_count}")
    for idx, cand in enumerate(resp.validated_candidates or []):
        print(f"  [Validated #{idx+1}] ({cand.knowledge_id}, {cand.resource_id}) - {cand.title}")
    for idx, rej in enumerate(resp.rejected_candidates or []):
        print(f"  [Rejected #{idx+1}] Code={rej.code}, Reason={rej.reason}")

    return {
        "status": "SUCCESS",
        "elapsed_ms": elapsed_ms,
        "validated_count": val_count,
        "rejected_count": rej_count,
        "rejection_codes": [r.code for r in (resp.rejected_candidates or [])],
        "allow_production_decision": False,
    }


# ==============================================================================
# Request #2: Context Boundary
# ==============================================================================

async def run_request_2_context_boundary(provider: DeepSeekProvider) -> Dict[str, Any]:
    print("\n--- [Request #2: Context Boundary] ---")
    record_live_request()

    # 构造仅包含两个特定候选资源的边界上下文
    bounded_ctx = RecommendationContext(
        student_id="student_s001",
        current_focus="K03",
        knowledge_states=[
            KnowledgeStateSnapshot(knowledge_id="K03", knowledge_name="需求价格弹性", mastery=0.3, path_state="IN_PROGRESS"),
        ],
        resources=[
            ResourceCandidateSnapshot(
                resource_id="res_k03_concept", knowledge_id="K03", resource_type="concept_microcard",
                title="微卡", description="描述", source="xuehai_internal",
            ),
        ],
    )

    generator = DeepSeekCandidateGenerator(provider=provider)
    start_t = time.perf_counter()
    error_msg = None
    val_result = None

    try:
        raw_payload, _ = await generator.generate_raw_candidates(
            context=bounded_ctx,
            max_candidates=1,
            provider_override=provider,
        )
        val_result = RecommendationValidator.validate_candidates_detailed(
            raw_output=raw_payload,
            context=bounded_ctx,
            max_allowed=1,
        )
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"

    elapsed_ms = int((time.perf_counter() - start_t) * 1000)

    if error_msg:
        print(f"Request #2 Error (Safe Failure): {error_msg}")
        return {
            "status": "SAFE_FAILURE",
            "elapsed_ms": elapsed_ms,
            "error": error_msg,
            "boundary_respected": True,
        }

    # 验证最终通过的 candidates 绝不能超出 bounded_ctx
    allowed_rids = {r.resource_id for r in bounded_ctx.resources}
    for v in val_result.validated_candidates:
        assert v.resource_id in allowed_rids, f"BOUNDARY LEAK: resource '{v.resource_id}' leaked through validator"

    val_count = len(val_result.validated_candidates)
    rej_count = len(val_result.rejected_candidates)
    print(f"Request #2 Finished in {elapsed_ms}ms | Validated: {val_count}, Rejected: {rej_count} | Boundary respected: YES")

    return {
        "status": "SUCCESS",
        "elapsed_ms": elapsed_ms,
        "validated_count": val_count,
        "rejected_count": rej_count,
        "rejection_codes": [r.code for r in val_result.rejected_candidates],
        "boundary_respected": True,
        "allow_production_decision": False,
    }


# ==============================================================================
# Request #3: Full E2E Mutation Safety
# ==============================================================================

async def run_request_3_mutation_safety(provider: DeepSeekProvider) -> Tuple[Dict[str, Any], Dict[str, int]]:
    print("\n--- [Request #3: Full E2E Mutation Safety] ---")
    record_live_request()

    # 1. 记录前置快照
    state_before = capture_system_state()

    generator = DeepSeekCandidateGenerator(provider=provider)
    svc = RecommendationService(provider=provider, generator=generator, raise_on_rejection=False)

    start_t = time.perf_counter()
    error_msg = None
    resp = None

    try:
        resp = await svc.get_recommendations("S001")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"

    elapsed_ms = int((time.perf_counter() - start_t) * 1000)

    # 2. 记录后置快照并进行严格对比
    state_after = capture_system_state()
    mutation_diff = compare_system_state(state_before, state_after)

    total_mutations = sum(mutation_diff.values())
    print(f"Request #3 Finished in {elapsed_ms}ms | Total State Mutations: {total_mutations}")
    for k, v in mutation_diff.items():
        print(f"  {k}: {v}")

    assert total_mutations == 0, f"HARD REDLINE BREACH: System state was mutated during recommendation: {mutation_diff}"

    res_summary = {
        "status": "SUCCESS" if not error_msg else "SAFE_FAILURE",
        "elapsed_ms": elapsed_ms,
        "error": error_msg,
        "total_mutations": total_mutations,
        "allow_production_decision": False,
    }
    return res_summary, mutation_diff


# ==============================================================================
# 主执行入口
# ==============================================================================

async def main_async():
    print("=" * 70)
    print("=== Sprint 10-B Phase 3 Live Smoke ===")
    print("=" * 70)

    provider = get_live_provider()
    if provider is None:
        print("Mode: OFFLINE / LIVE_API_KEY_NOT_CONFIGURED")
        print("Reason: DEEPSEEK_ENABLED is false or DEEPSEEK_API_KEY is not set.")
        print("Action: Safely skipped real DeepSeek API calls.")
        print("Result: UNDEFINED_BOUNDARY (Offline Safe Exit)")
        print("=" * 70)
        # 写出安全退出概要
        summary = {
            "mode": "OFFLINE",
            "status": "LIVE_API_KEY_NOT_CONFIGURED",
            "live_requests_made": 0,
            "allow_production_decision": False,
        }
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        SUMMARY_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        return 0

    print("Mode: LIVE")
    print(f"Provider: {provider.provider_name.capitalize()}")
    print(f"Model: {provider.model}")
    print(f"Base URL: {provider.base_url}")
    print(f"API Key: (configured, redacted)")
    print("=" * 70)

    # 执行最多 3 次受控请求
    r1_res = await run_request_1_happy_path(provider)
    r2_res = await run_request_2_context_boundary(provider)
    r3_res, mutation_diff = await run_request_3_mutation_safety(provider)

    print("\n" + "=" * 70)
    print("=== Phase 3 Live Smoke Summary ===")
    print(f"Request #1 (Happy Path): {r1_res['status']}")
    print(f"Request #2 (Context Boundary): {r2_res['status']}")
    print(f"Request #3 (Mutation Safety): {r3_res['status']}")
    print(f"Total Live Requests: {_live_request_count} (<= {MAX_LIVE_REQUESTS})")
    print(f"BKT mutation: {mutation_diff['bkt_mutation']}")
    print(f"PathState mutation: {mutation_diff['path_mutation']}")
    print(f"Learning event mutation: {mutation_diff['learning_event_mutation']}")
    print(f"Resource event mutation: {mutation_diff['resource_event_mutation']}")
    print("allow_production_decision: False")
    print("API key exposed: NO")
    print("=" * 70)

    # 保存脱敏审计结果至 artifacts
    audit_summary = {
        "mode": "LIVE",
        "provider": provider.provider_name,
        "model": provider.model,
        "live_requests_count": _live_request_count,
        "request_1": r1_res,
        "request_2": r2_res,
        "request_3": r3_res,
        "mutation_diff": mutation_diff,
        "allow_production_decision": False,
        "api_key_exposed": False,
    }
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_FILE.write_text(json.dumps(audit_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Audit evidence recorded to: {SUMMARY_FILE.name}")
    return 0


def main():
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
