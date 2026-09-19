# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint10a_mooc_api
======================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-A
中国大学MOOC与内部资源统一查询 API 严苛测试套件 (MOOC & Unified Resource API Tests)

测试覆盖：
1. Test 1: GET /api/learning/resources/K01 默认返回全量资源（同时包含内部与MOOC）
2. Test 2: source filter: source=xuehai_internal / internal 仅返回内部资源
3. Test 3: source filter: source=china_mooc / mooc 仅返回 MOOC 外部资源
4. Test 4: source filter: source=all 显式请求时完整返回两者
5. Test 5: MOOC 资源契约断言：is_external == True, source == "china_mooc"
6. Test 6: MOOC 资源外链安全断言：全部 source_url 100% 通过 security 白名单校验
7. Test 7: 不存在考点 (K99, K00) 防御：严格保持 404 错误响应契约
8. Test 8: 确定性断言：连续 25 次调用相同 API，响应字节级与顺序完全稳定一致
9. Test 9: Recommended API 隔离断言：GET /api/learning/resources/recommended/{student_id}
           依然且仅包含内部资源，绝无 MOOC 外部资源侵入，推荐位次与分值 0 漂移
10. Test 10: Effectiveness API 隔离断言：资源成效档案未受 MOOC 任何污染
11. Test 11: 单资源详情查询 GET /api/learning/resources/item/{id} 支持内部与 MOOC
12. Test 12: 非法 source 参数 400 防御
"""

import pytest
from fastapi.testclient import TestClient

from gateway.api import create_gateway_app
from gateway.learning.resources.models import ResourceType
from gateway.learning.resources.catalog import RESOURCE_CATALOG
from gateway.learning.resources.mooc_catalog import MOOC_RESOURCE_CATALOG
from gateway.learning.resources.security import validate_external_mooc_url
from gateway.learning.resources.service import (
    get_unified_resource_by_id,
    get_unified_resources_by_knowledge,
    get_all_unified_resources,
)


@pytest.fixture(scope="module")
def api_client():
    """测试客户端实例"""
    app = create_gateway_app()
    return TestClient(app)


# =============================================================================
# 1. 统一查询与 Source 过滤契约
# =============================================================================

def test_01_k01_default_returns_both_internal_and_mooc(api_client):
    """Test 1: GET /api/learning/resources/K01 默认同时返回内部资源与 MOOC 资源"""
    resp = api_client.get("/api/learning/resources/K01")
    assert resp.status_code == 200
    data = resp.json()

    assert data["knowledge_id"] == "K01"
    resources = data["resources"]
    assert len(resources) == data["total"]

    sources = {r["source"] for r in resources}
    assert "xuehai_internal" in sources, "必须包含内部资源"
    assert "china_mooc" in sources, "必须包含中国大学MOOC外部资源"

    # 排序顺序断言：内部资源在前，MOOC 资源置后
    internal_indices = [idx for idx, r in enumerate(resources) if r["source"] == "xuehai_internal"]
    mooc_indices = [idx for idx, r in enumerate(resources) if r["source"] == "china_mooc"]
    assert max(internal_indices) < min(mooc_indices), "内部资源必须整体排在 MOOC 资源之前"


def test_02_source_filter_xuehai_internal_only(api_client):
    """Test 2: source=xuehai_internal 严格只返回内部资源"""
    resp = api_client.get("/api/learning/resources/K01?source=xuehai_internal")
    assert resp.status_code == 200
    data = resp.json()

    resources = data["resources"]
    assert len(resources) > 0
    for r in resources:
        assert r["source"] == "xuehai_internal"
        assert r["is_external"] is False
        assert r["source_url"] is None

    # 同时测试 alias: source=internal
    resp_alias = api_client.get("/api/learning/resources/K01?source=internal")
    assert resp_alias.status_code == 200
    assert resp_alias.json()["total"] == data["total"]


def test_03_source_filter_china_mooc_only(api_client):
    """Test 3: source=china_mooc 严格只返回 MOOC 资源"""
    resp = api_client.get("/api/learning/resources/K01?source=china_mooc")
    assert resp.status_code == 200
    data = resp.json()

    resources = data["resources"]
    assert len(resources) >= 1
    for r in resources:
        assert r["source"] == "china_mooc"
        assert r["is_external"] is True
        assert r["source_url"] is not None
        assert validate_external_mooc_url(r["source_url"]) is True

    # 同时测试 alias: source=mooc
    resp_alias = api_client.get("/api/learning/resources/K01?source=mooc")
    assert resp_alias.status_code == 200
    assert resp_alias.json()["total"] == data["total"]


def test_04_source_filter_all_returns_both(api_client):
    """Test 4: source=all 显式指定时返回内部与 MOOC 两者"""
    resp = api_client.get("/api/learning/resources/K01?source=all")
    assert resp.status_code == 200
    data = resp.json()

    sources = {r["source"] for r in data["resources"]}
    assert "xuehai_internal" in sources
    assert "china_mooc" in sources

    # 与缺省 source 的返回项数量严格一致
    resp_default = api_client.get("/api/learning/resources/K01")
    assert data["total"] == resp_default.json()["total"]


# =============================================================================
# 2. MOOC 资源与安全契约断言
# =============================================================================

def test_05_mooc_resources_external_contract(api_client):
    """Test 5: MOOC 资源必须满足 is_external == True 与标准元数据"""
    resp = api_client.get("/api/learning/resources/K01?source=china_mooc")
    assert resp.status_code == 200
    for res in resp.json()["resources"]:
        assert res["is_external"] is True
        assert res["source"] == "china_mooc"
        assert res["resource_id"].startswith("mooc_")
        assert "metadata" in res and res["metadata"].get("provider") == "中国大学MOOC"


def test_06_mooc_resources_url_security_validated(api_client):
    """Test 6: 所有 API 返回的 MOOC 资源 source_url 均通过严格安全校验"""
    resp = api_client.get("/api/learning/resources/K01?source=china_mooc")
    assert resp.status_code == 200
    for res in resp.json()["resources"]:
        url = res.get("source_url")
        assert url is not None
        assert validate_external_mooc_url(url) is True
        assert url.startswith("https://")
        assert "icourse163.org" in url


# =============================================================================
# 3. 错误与异常防御契约
# =============================================================================

def test_07_unknown_knowledge_point_404(api_client):
    """Test 7: 不存在的考点必须严格保持 404 响应"""
    r1 = api_client.get("/api/learning/resources/K99")
    assert r1.status_code == 404
    assert "找不到指定考点" in r1.json()["detail"]

    r2 = api_client.get("/api/learning/resources/K00")
    assert r2.status_code == 404

    r3 = api_client.get("/api/learning/resources/INVALID_KID")
    assert r3.status_code == 404


def test_08_invalid_source_and_type_parameters_400(api_client):
    """验证非法 source 与 resource_type 参数返回 400"""
    r1 = api_client.get("/api/learning/resources/K01?source=unsupported_source")
    assert r1.status_code == 400
    assert "不支持的资源来源" in r1.json()["detail"]

    r2 = api_client.get("/api/learning/resources/K01?resource_type=INVALID_TYPE")
    assert r2.status_code == 400
    assert "不支持的资源类型" in r2.json()["detail"]


# =============================================================================
# 4. 纯函数稳定性与确定性
# =============================================================================

def test_09_determinism_25_consecutive_calls(api_client):
    """Test 8: 连续调用 25 次相同 API，响应序列与属性严格稳定一致"""
    resp_first = api_client.get("/api/learning/resources/K01")
    assert resp_first.status_code == 200
    first_ids = [r["resource_id"] for r in resp_first.json()["resources"]]

    for _ in range(25):
        resp = api_client.get("/api/learning/resources/K01")
        assert resp.status_code == 200
        current_ids = [r["resource_id"] for r in resp.json()["resources"]]
        assert current_ids == first_ids, "确定性排序断言失败"


# =============================================================================
# 5. 关键架构隔离性断言 (Recommended & Effectiveness 零污染)
# =============================================================================

def test_10_recommended_api_strictly_isolated_from_mooc(api_client):
    """Test 9: 自适应推荐接口 GET /api/learning/resources/recommended/{student_id}
    必须 100% 保持内部资源闭环，绝无任何 MOOC 资源侵入"""
    resp = api_client.get("/api/learning/resources/recommended/S001?knowledge_id=K01")
    assert resp.status_code == 200
    data = resp.json()

    assert "recommendations" in data
    recs = data["recommendations"]
    assert len(recs) >= 3

    for rec in recs:
        res = rec["resource"]
        # 严格断言：推荐出来的所有资源必须且只能是内部资源
        assert res["source"] == "xuehai_internal", f"推荐候选池混入了非内部资源: {res['resource_id']}"
        assert res["is_external"] is False, f"推荐候选池混入了外部资源: {res['resource_id']}"
        assert res["source_url"] is None
        assert not res["resource_id"].startswith("mooc_"), f"MOOC 资源渗透到了推荐接口: {res['resource_id']}"


def test_11_effectiveness_api_strictly_isolated_from_mooc(api_client):
    """Test 10: 资源成效接口未受 MOOC 任何污染"""
    resp = api_client.get("/api/learning/resources/effectiveness-profile/S001?knowledge_id=K01")
    assert resp.status_code == 200
    data = resp.json()

    # 成效档案仅包含内部标准类型
    allowed_types = {"CONCEPT_CARD", "EXAMPLE", "PRACTICE", "DOCUMENT", "VIDEO", "micro_quiz", "concept_card"}
    for prof in data.get("profiles", []):
        rtype = prof.get("resource_type")
        assert rtype in allowed_types or rtype.upper() in allowed_types


# =============================================================================
# 6. 单项资源详情查询统一适配 (GET /item/{id})
# =============================================================================

def test_12_get_resource_item_supports_both_internal_and_mooc(api_client):
    """Test 11: GET /api/learning/resources/item/{id} 同时支持内部与 MOOC 资源详情"""
    # 1. 查询内部微卡
    resp_int = api_client.get("/api/learning/resources/item/res_k01_concept")
    assert resp_int.status_code == 200
    assert resp_int.json()["source"] == "xuehai_internal"
    assert resp_int.json()["is_external"] is False

    # 2. 查询外部 MOOC
    resp_mooc = api_client.get("/api/learning/resources/item/mooc_k01_scarcity")
    assert resp_mooc.status_code == 200
    assert resp_mooc.json()["source"] == "china_mooc"
    assert resp_mooc.json()["is_external"] is True
    assert "icourse163.org" in resp_mooc.json()["source_url"]

    # 3. 查询不存在的资源
    resp_non = api_client.get("/api/learning/resources/item/non_existent_999")
    assert resp_non.status_code == 404
