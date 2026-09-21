# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint10c_recommendation_session
===================================================
学海智导 (Xuehai Zhidao) — Sprint 10-C Phase 3
AI 个性化推荐在学生学习会话中的集成验证测试套件

测试目标：
1. 学习会话上下文考点绑定 (knowledge_id 显式锚定)；
2. 考点资源池物理隔离性 (K01 vs K02)；
3. 学习决策权与数据零副作用不变性 (Zero Business Mutation Invariant)；
4. 容错与非阻塞退避契约 (422 / 504 / 429 映射)；
5. 请求参数白名单与安全防御 (禁止客户端指定 model / extra 字段)；
6. 人本化推荐解释与零指令/零决策词断言。
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from gateway.ai.deepseek import (
    AIProviderResponse,
    MockDeepSeekProvider,
    ProviderTimeout,
    RateLimitError,
)
from gateway.ai.recommendation import (
    RECOMMENDATION_FORBIDDEN_FIELDS,
    RecommendationCandidate,
    RecommendationContext,
    RecommendationContextBuilder,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationService,
    ValidationRejectedError,
    default_recommendation_service,
)
from gateway.api import create_gateway_app


@pytest.fixture
def client():
    test_app = create_gateway_app()
    with TestClient(test_app) as c:
        yield c


# ==============================================================================
# Group 1: 学习会话上下文锚定与知识点绑定
# ==============================================================================

def test_01_session_anchored_recommendation_k02(client):
    """Test 01: 会话指定 knowledge_id='K02'，返回推荐必须严格锚定于 K02"""
    res = client.post(
        "/api/ai/recommendations/S001",
        json={"knowledge_id": "K02", "max_recommendations": 3},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "student_s001"
    assert data["validated"] is True
    assert "recommendations" in data

    for rec in data["recommendations"]:
        assert rec["knowledge_id"] == "K02"
        assert rec["title"] != ""
        assert rec["resource_type"] in ["CONCEPT_CARD", "EXAMPLE", "PRACTICE", "DOCUMENT", "VIDEO"]
        assert rec["source"] in ["xuehai_internal", "china_mooc"]


def test_02_context_isolation_between_different_kps(client):
    """Test 02: K01 与 K02 上下文所获候选必须物理隔离，不会混淆考点资源"""
    res_k01 = client.post(
        "/api/ai/recommendations/S001",
        json={"knowledge_id": "K01", "max_recommendations": 3},
    )
    assert res_k01.status_code == 200
    recs_k01 = res_k01.json()["recommendations"]

    res_k02 = client.post(
        "/api/ai/recommendations/S001",
        json={"knowledge_id": "K02", "max_recommendations": 3},
    )
    assert res_k02.status_code == 200
    recs_k02 = res_k02.json()["recommendations"]

    k01_resource_ids = {r["resource_id"] for r in recs_k01}
    k02_resource_ids = {r["resource_id"] for r in recs_k02}

    for r in recs_k01:
        assert r["knowledge_id"] == "K01"
    for r in recs_k02:
        assert r["knowledge_id"] == "K02"

    # 两者资源集合交集必须为空
    assert k01_resource_ids.isdisjoint(k02_resource_ids)


def test_03_unknown_knowledge_id_fallback(client):
    """Test 03: 传入未知考点 ID 时安全回退至当前权威焦点考点，系统不崩溃"""
    res = client.post(
        "/api/ai/recommendations/S001",
        json={"knowledge_id": "K999", "max_recommendations": 2},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["validated"] is True
    # 返回的考点必须是知识图谱中真实存在的考点
    for rec in data["recommendations"]:
        assert rec["knowledge_id"].startswith("K")
        assert rec["knowledge_id"] != "K999"


# ==============================================================================
# Group 2: 零业务状态变更与零决策权 (Zero Mutation Invariant)
# ==============================================================================

def test_04_session_recommendation_zero_bkt_mutation(client):
    """Test 04: 会话内调用推荐接口，BKT 状态文件绝对零修改"""
    bkt_file = settings.BKT_STATES_FILE
    before_content = bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else ""

    res = client.post("/api/ai/recommendations/S001", json={"knowledge_id": "K02"})
    assert res.status_code == 200

    after_content = bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else ""
    assert before_content == after_content


def test_05_session_recommendation_zero_path_state_mutation(client):
    """Test 05: 会话内调用推荐接口，路径状态文件绝对零修改"""
    path_file = settings.LEARNING_PATH_STATES_FILE
    before_content = path_file.read_text(encoding="utf-8") if path_file.exists() else ""

    res = client.post("/api/ai/recommendations/S001", json={"knowledge_id": "K02"})
    assert res.status_code == 200

    after_content = path_file.read_text(encoding="utf-8") if path_file.exists() else ""
    assert before_content == after_content


def test_06_session_recommendation_zero_learning_events(client):
    """Test 06: 会话内调用推荐接口，正式学习事件绝对零记录"""
    events_file = settings.LEARNING_EVENTS_FILE
    before_lines = events_file.read_text(encoding="utf-8").strip().splitlines() if events_file.exists() else []

    res = client.post("/api/ai/recommendations/S001", json={"knowledge_id": "K02"})
    assert res.status_code == 200

    after_lines = events_file.read_text(encoding="utf-8").strip().splitlines() if events_file.exists() else []
    assert len(before_lines) == len(after_lines)


def test_07_recommendation_response_zero_decision_fields(client):
    """Test 07: 推荐响应中绝对禁止包含任何决策字段与指令字段"""
    res = client.post("/api/ai/recommendations/S001", json={"knowledge_id": "K02"})
    assert res.status_code == 200
    raw_dict = res.json()

    for forbidden in RECOMMENDATION_FORBIDDEN_FIELDS:
        assert forbidden not in raw_dict

    for item in raw_dict["recommendations"]:
        for forbidden in RECOMMENDATION_FORBIDDEN_FIELDS:
            assert forbidden not in item


# ==============================================================================
# Group 3: 容错与非阻塞退避映射 (Fault Resilience)
# ==============================================================================

def test_08_client_model_injection_rejected_422(client):
    """Test 08: 客户端企图传递 model 字段篡改模型，被严格 422 拒绝"""
    res = client.post(
        "/api/ai/recommendations/S001",
        json={"knowledge_id": "K02", "model": "deepseek-chat-override"},
    )
    assert res.status_code == 422
    assert "SCHEMA_VALIDATION_FAILED" in res.text or "extra" in res.text.lower()


def test_09_extra_parameters_rejected_422(client):
    """Test 09: 客户端企图传递额外越权参数，被 extra='forbid' 拦截"""
    res = client.post(
        "/api/ai/recommendations/S001",
        json={"knowledge_id": "K02", "skip_quiz": True},
    )
    assert res.status_code == 422


def test_10_ai_timeout_maps_to_504(client):
    """Test 10: Provider 异步调用超时，网关受控映射为 HTTP 504 供前端回退基线"""
    mock_timeout = MockDeepSeekProvider()

    async def _raise_timeout(*args, **kwargs):
        raise ProviderTimeout("Simulated AI timeout", timeout_seconds=15.0)

    mock_timeout.complete = _raise_timeout
    svc = RecommendationService(provider=mock_timeout)

    with patch("gateway.api.default_recommendation_service", svc):
        res = client.post("/api/ai/recommendations/S001", json={"knowledge_id": "K02"})
        assert res.status_code == 504
        assert "响应超时" in res.json()["detail"]


def test_11_ai_validation_rejection_maps_to_422(client):
    """Test 11: AI 返回幻觉或非法候选时，确定性校验器拦截并映射为 HTTP 422"""
    mock_bad = MockDeepSeekProvider()
    bad_resp = AIProviderResponse(
        content=json.dumps({"recommendations": [{"knowledge_id": "K02", "resource_id": "R_NONEXISTENT", "reason": "bad"}]}),
        model="deepseek-flash",
        provider="mock-deepseek",
        parsed_json={"recommendations": [{"knowledge_id": "K02", "resource_id": "R_NONEXISTENT", "reason": "bad"}]},
    )

    async def _mock_complete(*args, **kwargs):
        return bad_resp

    mock_bad.complete = _mock_complete
    svc = RecommendationService(provider=mock_bad)

    with patch("gateway.api.default_recommendation_service", svc):
        res = client.post("/api/ai/recommendations/S001", json={"knowledge_id": "K02"})
        assert res.status_code == 422
        assert "AI 推荐候选未通过确定性安全校验" in res.json()["detail"]


# ==============================================================================
# Group 4: 人本化推荐解释文本规范
# ==============================================================================

def test_12_recommendation_reasons_humanistic_and_zero_imperatives(client):
    """Test 12: 推荐理由必须为友好解释，严禁包含强制指令词 (如“你必须”、“系统要求”)"""
    res = client.post("/api/ai/recommendations/S001", json={"knowledge_id": "K02"})
    assert res.status_code == 200
    recs = res.json()["recommendations"]

    forbidden_imperatives = ["你必须", "强制", "系统命令", "系统断言", "无可争议", "禁止跳过"]
    for rec in recs:
        reason = rec["reason"]
        assert len(reason) > 0
        for imp in forbidden_imperatives:
            assert imp not in reason, f"推荐理由包含禁止指令词 '{imp}': {reason}"
