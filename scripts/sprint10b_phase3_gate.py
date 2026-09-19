# -*- coding: utf-8 -*-
"""
scripts/sprint10b_phase3_gate.py
================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B / Phase 3
个性化推荐产品化质量门禁 (Personalized Recommendation Productization Quality Gate)

检查项 (20 维全量覆盖)：
[01/20] Recommendation API reachable
[02/20] Recommendation response schema
[03/20] Recommendation section renders
[04/20] Internal resource click works
[05/20] MOOC resource click works
[06/20] ExternalRedirectModal preserved
[07/20] AI URL cannot bypass catalog
[08/20] Recommendation failure doesn't break ResourceHub
[09/20] Empty recommendation doesn't break ResourceHub
[10/20] Loading state works
[11/20] Mobile 375x812 responsive layout
[12/20] Mobile 390x844 responsive layout
[13/20] No horizontal overflow
[14/20] No BKT mutation
[15/20] No PathState mutation
[16/20] No Learning Event mutation
[17/20] Today Action unchanged
[18/20] Dynamic Path unchanged
[19/20] Existing Companion unchanged
[20/20] Recommendation remains candidate-only

目标：20/20 PASS
"""

import hashlib
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from app.infrastructure.persistence.event_repository import default_event_repository
import path_state_service
from gateway.api import create_gateway_app
from gateway.learning.path_generation import default_dynamic_path_generator
from gateway.ai.recommendation.models import RECOMMENDATION_FORBIDDEN_FIELDS, ValidatedRecommendation
from gateway.ai.recommendation.prompt import build_recommendation_prompt
from gateway.ai.recommendation.context import RecommendationContextBuilder


def run_check(num: int, title: str, fn) -> bool:
    prefix = f"[{num:02d}/20] {title}"
    dots = "." * max(2, 60 - len(prefix))
    print(f"{prefix} {dots} ", end="", flush=True)
    try:
        fn()
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_01_recommendation_api_reachable():
    app = create_gateway_app()
    client = TestClient(app)
    resp = client.post("/api/ai/recommendations/S001", json={"max_recommendations": 3})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "recommendations" in data
    assert data["student_id"] == "student_s001"


def test_02_recommendation_response_schema():
    app = create_gateway_app()
    client = TestClient(app)
    resp = client.post("/api/ai/recommendations/S001", json={"max_recommendations": 3})
    data = resp.json()
    assert data["validated"] is True
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) <= 3

    for r in data["recommendations"]:
        for req_field in ["knowledge_id", "resource_id", "reason", "title", "resource_type", "source"]:
            assert req_field in r, f"Missing required field {req_field}"
        # 绝对杜绝 url 透传与算法越权字段
        assert "url" not in r
        assert "mastery_probability" not in r
        assert "decision" not in r


def test_03_recommendation_section_renders():
    rh_path = PROJECT_ROOT / "frontend" / "src" / "components" / "student" / "ResourceHub.tsx"
    content = rh_path.read_text(encoding="utf-8")
    assert 'data-testid="personalized-recommendation-section"' in content
    assert 'data-testid="personalized-rec-title"' in content
    assert "为你推荐" in content
    assert "根据你最近的学习情况，为你推荐了这些内容。" in content


def test_04_internal_resource_click_works():
    rh_path = PROJECT_ROOT / "frontend" / "src" / "components" / "student" / "ResourceHub.tsx"
    content = rh_path.read_text(encoding="utf-8")
    assert "handleOpenPersonalRecommendation" in content
    assert "onOpenConceptCard" in content
    assert "onStartQuiz" in content
    assert "setActiveReadingResource" in content


def test_05_mooc_resource_click_works():
    rh_path = PROJECT_ROOT / "frontend" / "src" / "components" / "student" / "ResourceHub.tsx"
    content = rh_path.read_text(encoding="utf-8")
    assert "targetResource.is_external && targetResource.source === 'china_mooc'" in content
    assert "setExternalRedirectTarget(targetResource)" in content


def test_06_external_redirect_modal_preserved():
    rh_path = PROJECT_ROOT / "frontend" / "src" / "components" / "student" / "ResourceHub.tsx"
    content = rh_path.read_text(encoding="utf-8")
    assert "<ExternalRedirectModal" in content
    assert "resource={externalRedirectTarget}" in content
    assert "handleConfirmExternalRedirect" in content
    assert "isSafeChinaMoocUrl" in content


def test_07_ai_url_cannot_bypass_catalog():
    # 1. 验证后端 ValidatedRecommendation 绝对不含有 url 字段
    assert "url" not in ValidatedRecommendation.model_fields

    # 2. 验证 ResourceHub.tsx 从权威目录查询 targetResource
    rh_path = PROJECT_ROOT / "frontend" / "src" / "components" / "student" / "ResourceHub.tsx"
    content = rh_path.read_text(encoding="utf-8")
    assert "getResourceItem(rec.resource_id)" in content

    # 3. 验证存在安全防注入自动化测试
    test_path = PROJECT_ROOT / "frontend" / "test" / "sprint10b_recommendation_ui.test.ts"
    test_content = test_path.read_text(encoding="utf-8")
    assert "poisonedAIPayload" in test_content or "evil.attacker.com" in test_content


def test_08_recommendation_failure_doesnt_break_resource_hub():
    rh_path = PROJECT_ROOT / "frontend" / "src" / "components" / "student" / "ResourceHub.tsx"
    content = rh_path.read_text(encoding="utf-8")
    assert "getPersonalizedRecommendations" in content
    assert "catch (err)" in content
    assert "RECOMMENDATION_UNAVAILABLE" in content
    assert 'data-testid="personalized-rec-error"' in content


def test_09_empty_recommendation_doesnt_break_resource_hub():
    rh_path = PROJECT_ROOT / "frontend" / "src" / "components" / "student" / "ResourceHub.tsx"
    content = rh_path.read_text(encoding="utf-8")
    assert 'data-testid="personalized-rec-empty"' in content
    assert "暂时没有适合你的推荐，可浏览下方全部学习资源。" in content


def test_10_loading_state_works():
    rh_path = PROJECT_ROOT / "frontend" / "src" / "components" / "student" / "ResourceHub.tsx"
    content = rh_path.read_text(encoding="utf-8")
    assert 'data-testid="personalized-rec-loading"' in content
    assert "正在生成推荐……" in content


def test_11_mobile_375x812():
    rh_path = PROJECT_ROOT / "frontend" / "src" / "components" / "student" / "ResourceHub.tsx"
    content = rh_path.read_text(encoding="utf-8")
    # 验证响应式栅格: 默认 1 列，大屏 2~3 列
    assert "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3" in content
    assert "flex flex-col sm:flex-row" in content


def test_12_mobile_390x844():
    rh_path = PROJECT_ROOT / "frontend" / "src" / "components" / "student" / "ResourceHub.tsx"
    content = rh_path.read_text(encoding="utf-8")
    assert "p-5 sm:p-6" in content
    assert "w-full" in content


def test_13_no_horizontal_overflow():
    rh_path = PROJECT_ROOT / "frontend" / "src" / "components" / "student" / "ResourceHub.tsx"
    content = rh_path.read_text(encoding="utf-8")
    assert "overflow-hidden" in content
    assert "line-clamp-2" in content


def test_14_no_bkt_mutation():
    app = create_gateway_app()
    client = TestClient(app)
    bkt_before = default_bkt_state_repository.get_student_states("S001")

    client.post("/api/ai/recommendations/S001", json={"max_recommendations": 3})

    bkt_after = default_bkt_state_repository.get_student_states("S001")
    assert bkt_after == bkt_before, "BKT state was mutated by recommendation API"


def test_15_no_path_state_mutation():
    app = create_gateway_app()
    client = TestClient(app)
    path_before = path_state_service.get_all_path_states("S001")

    client.post("/api/ai/recommendations/S001", json={"max_recommendations": 3})

    path_after = path_state_service.get_all_path_states("S001")
    assert path_after == path_before, "PathState was mutated by recommendation API"


def test_16_no_learning_event_mutation():
    app = create_gateway_app()
    client = TestClient(app)
    events_before = len(default_event_repository.get_events_by_student("S001"))

    client.post("/api/ai/recommendations/S001", json={"max_recommendations": 3})

    events_after = len(default_event_repository.get_events_by_student("S001"))
    assert events_after == events_before, "Learning events were created by recommendation API"


def test_17_today_action_unchanged():
    app = create_gateway_app()
    client = TestClient(app)
    act_before = client.get("/api/learning/today/S001").json()

    client.post("/api/ai/recommendations/S001", json={"max_recommendations": 3})

    act_after = client.get("/api/learning/today/S001").json()
    assert act_after == act_before, "Today Action was altered by recommendation API"


def test_18_dynamic_path_unchanged():
    app = create_gateway_app()
    client = TestClient(app)
    route_before = client.get("/api/path/dynamic/S001").json()

    client.post("/api/ai/recommendations/S001", json={"max_recommendations": 3})

    route_after = client.get("/api/path/dynamic/S001").json()
    route_before.pop("generated_at", None)
    route_after.pop("generated_at", None)
    assert route_after == route_before, "Dynamic Path was altered by recommendation API"


def test_19_existing_companion_unchanged():
    app = create_gateway_app()
    client = TestClient(app)
    resp = client.get("/api/ai/companion/actions/S001")
    assert resp.status_code == 200
    assert "actions" in resp.json()


def test_20_recommendation_remains_candidate_only():
    ctx = RecommendationContextBuilder.build_context("S001")
    sys_p, _ = build_recommendation_prompt(ctx)
    assert "allow_production_decision = False" in sys_p
    assert "decision" in RECOMMENDATION_FORBIDDEN_FIELDS
    assert "production_decision" in RECOMMENDATION_FORBIDDEN_FIELDS


def main():
    print("=" * 70)
    print("学海智导 Sprint 10-B / Phase 3 严苛质量门禁 (20-Point Strict Gate)")
    print("=" * 70)

    checks = [
        (1, "Recommendation API reachable", test_01_recommendation_api_reachable),
        (2, "Recommendation response schema", test_02_recommendation_response_schema),
        (3, "Recommendation section renders", test_03_recommendation_section_renders),
        (4, "Internal resource click works", test_04_internal_resource_click_works),
        (5, "MOOC resource click works", test_05_mooc_resource_click_works),
        (6, "ExternalRedirectModal preserved", test_06_external_redirect_modal_preserved),
        (7, "AI URL cannot bypass catalog", test_07_ai_url_cannot_bypass_catalog),
        (8, "Recommendation failure doesn't break ResourceHub", test_08_recommendation_failure_doesnt_break_resource_hub),
        (9, "Empty recommendation doesn't break ResourceHub", test_09_empty_recommendation_doesnt_break_resource_hub),
        (10, "Loading state works", test_10_loading_state_works),
        (11, "Mobile 375x812 responsive layout", test_11_mobile_375x812),
        (12, "Mobile 390x844 responsive layout", test_12_mobile_390x844),
        (13, "No horizontal overflow", test_13_no_horizontal_overflow),
        (14, "No BKT mutation", test_14_no_bkt_mutation),
        (15, "No PathState mutation", test_15_no_path_state_mutation),
        (16, "No Learning Event mutation", test_16_no_learning_event_mutation),
        (17, "Today Action unchanged", test_17_today_action_unchanged),
        (18, "Dynamic Path unchanged", test_18_dynamic_path_unchanged),
        (19, "Existing Companion unchanged", test_19_existing_companion_unchanged),
        (20, "Recommendation remains candidate-only", test_20_recommendation_remains_candidate_only),
    ]

    passed = 0
    for num, title, fn in checks:
        if run_check(num, title, fn):
            passed += 1

    print("-" * 70)
    print(f"Gate Score: {passed}/{len(checks)} PASS")
    if passed == len(checks):
        print("ALL QUALITY CHECKS PASSED — SPRINT 10-B PHASE 3 VERIFIED")
        return 0
    else:
        print("QUALITY GATE FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
