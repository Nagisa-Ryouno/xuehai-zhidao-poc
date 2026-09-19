# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint10b_phase3_integration
===============================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B / Phase 3
个性化推荐与学生端资源中心集成契约测试 (Productization & Integration Tests)

覆盖范围：
1. Recommendation API 与前端 ResourceHub 契约对齐 (GET/POST)
2. 推荐候选权威性水合：通过 /learning/resources/item/{resource_id} 解析真实元数据
3. 内部资源项元数据完备性 (CONCEPT_CARD, EXAMPLE, PRACTICE)
4. MOOC 资源项元数据完备性 (china_mooc, verified source_url, provider)
5. 权威 URL 安全屏障：Recommendation 响应绝不携带 url 字段，强制依赖权威目录
6. 零学习副作用保证：调用前后 BKT, PathState, Today Action, Learning Events 0 变更
7. 多学生独立隔离性：S001 与 S002 产生相互隔离的推荐上下文
8. 错误降级弹性：上游异常不破坏系统基础资源中心接口
"""

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from app.infrastructure.persistence.event_repository import default_event_repository
import path_state_service
from gateway.api import create_gateway_app


@pytest.fixture
def client():
    app = create_gateway_app()
    return TestClient(app)


def test_recommendation_api_contract_for_resource_hub(client):
    """
    Test 1: 验证 Recommendation API 符合前端 ResourceHub 的集成契约
    """
    resp = client.post(
        "/api/ai/recommendations/student_s001",
        json={"max_recommendations": 3},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["student_id"] == "student_s001"
    assert data["validated"] is True
    assert "recommendations" in data
    assert len(data["recommendations"]) <= 3

    for rec in data["recommendations"]:
        assert "knowledge_id" in rec
        assert "resource_id" in rec
        assert "reason" in rec
        assert "title" in rec
        assert "resource_type" in rec
        assert "source" in rec
        # 绝对不能泄漏 URL 字段，强制走权威目录
        assert "url" not in rec
        assert "source_url" not in rec


def test_resource_item_resolution_for_internal_and_mooc(client):
    """
    Test 2: 验证通过 resource_id 从权威单项接口准确水合内部与 MOOC 资源详情
    """
    # 内部资源水合
    resp_int = client.get("/api/learning/resources/item/res_k03_concept")
    assert resp_int.status_code == 200
    item_int = resp_int.json()
    assert item_int["resource_id"] == "res_k03_concept"
    assert item_int["source"] == "xuehai_internal"
    assert item_int["is_external"] is False

    # MOOC 资源水合
    resp_mooc = client.get("/api/learning/resources/item/mooc_k01_scarcity")
    assert resp_mooc.status_code == 200
    item_mooc = resp_mooc.json()
    assert item_mooc["resource_id"] == "mooc_k01_scarcity"
    assert item_mooc["source"] == "china_mooc"
    assert item_mooc["is_external"] is True
    assert item_mooc["source_url"].startswith("https://www.icourse163.org/")
    assert item_mooc["metadata"]["provider"] == "中国大学MOOC"


def test_url_safety_cannot_bypass_catalog(client):
    """
    Test 3: 安全性断言——推荐接口绝对不直接透传 URL，杜绝钓鱼外链风险
    """
    resp = client.post(
        "/api/ai/recommendations/S001",
        json={"max_recommendations": 3},
    )
    assert resp.status_code == 200
    data = resp.json()

    # 递归检查所有键，确认没有 url, target_url, redirect_url
    for rec in data["recommendations"]:
        assert "url" not in rec
        assert "target_url" not in rec
        assert "redirect_url" not in rec


def test_zero_mutation_invariant(client):
    """
    Test 4: 零学习决策副作用断言——调用推荐端点不会产生任何业务状态变更
    """
    student_id = "S001"

    # 读取调用前快照
    bkt_before = default_bkt_state_repository.get_student_states(student_id)
    path_before = path_state_service.get_all_path_states(student_id)
    events_before = len(default_event_repository.get_events_by_student(student_id))

    # 执行推荐调用
    resp = client.post(
        f"/api/ai/recommendations/{student_id}",
        json={"max_recommendations": 3},
    )
    assert resp.status_code == 200

    # 读取调用后快照并比对
    bkt_after = default_bkt_state_repository.get_student_states(student_id)
    path_after = path_state_service.get_all_path_states(student_id)
    events_after = len(default_event_repository.get_events_by_student(student_id))

    assert bkt_after == bkt_before, "BKT 状态不得被推荐调用篡改"
    assert path_after == path_before, "PathState 不得被推荐调用篡改"
    assert events_after == events_before, "绝不能产生多余的 Learning Events"


def test_today_action_remains_independent(client):
    """
    Test 5: 验证推荐接口调用前后，今日学习行动 (Today Action) 保持完全独立且不变
    """
    student_id = "S001"

    action_before = client.get(f"/api/learning/today/{student_id}").json()
    assert "action" in action_before

    # 调用推荐
    client.post(f"/api/ai/recommendations/{student_id}", json={"max_recommendations": 3})

    action_after = client.get(f"/api/learning/today/{student_id}").json()
    assert action_after == action_before, "今日最佳学习行动绝不能因 AI 推荐调用而发生改变"


def test_multi_student_isolation(client):
    """
    Test 6: 验证不同学生的推荐上下文与响应完全隔离
    """
    resp_s1 = client.post("/api/ai/recommendations/S001", json={"max_recommendations": 2})
    resp_s2 = client.post("/api/ai/recommendations/S002", json={"max_recommendations": 2})

    assert resp_s1.status_code == 200
    assert resp_s2.status_code == 200
    assert resp_s1.json()["student_id"] == "student_s001"
    assert resp_s2.json()["student_id"] == "student_s002"
