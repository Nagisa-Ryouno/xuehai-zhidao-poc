# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint9c_learning_resources
==============================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-C
学习资源中心与资源感知自适应学习严苛测试套件 (Learning Resource Hub Test Suite)

覆盖：
1. 资源模型验证与枚举校验
2. 全图谱 30 考点 (K01~K30) 100% 静态目录覆盖
3. 资源类型完备性（每个考点必须拥有 CONCEPT_CARD, EXAMPLE, PRACTICE，总数 >= 90）
4. 零失效外链：全部为内部资源，is_external=False，无恶意/虚假 URL
5. 目录按考点与类型筛选
6. 单资源精准检索
7. Case A (薄弱起步 < 0.60): 优先概念微卡与例题
8. Case B (进阶提升 0.60~0.80): 优先例题与微测验
9. Case C (达标进阶 >= 0.80 且有后继): 进阶练习与后继考点预习
10. Case D (终点巩固 >= 0.80 且无后继): 综合演练与讲义复盘
11. Case E (认知受阻 consecutive_incorrect >= 2): 概念微卡排查与例题剖析
12. 掌握度临界边界判定 (0.59 vs 0.60)
13. 掌握度临界边界判定 (0.79 vs 0.80)
14. 100 次重复调用输出完全确定性（纯函数断言）
15. 推荐理由白名单审核（零技术黑话）
16. 缺省考点推导逻辑
17. 多学生独立隔离性
18. 资源事件 Append-Only 写入与读取
19. 遥测隔离红线：资源交互对 data/learning_events.jsonl 零写入
20. 掌握度事实红线：资源交互对 data/bkt_states.json 零变更（零生产副作用）
21. HTTP API: 考点资源列表获取 (GET /api/learning/resources/{kid})
22. HTTP API: 考点资源类型过滤 (GET /api/learning/resources/{kid}?resource_type=...)
23. HTTP API: 自适应推荐接口 (GET /api/learning/resources/recommended/{student_id})
24. HTTP API: 单个资源详情 (GET /api/learning/resources/item/{resource_id})
25. HTTP API: 资源事件独立端点 (POST /api/learning/resources/events)
26. HTTP API: 统一学习事件端点对资源事件的路由转发 (POST /api/learning/events)
27. HTTP API: 404 防御（未知学生、未知考点、未知资源）
28. HTTP API: 400 防御（非法资源类型过滤）
"""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.core.config import settings
from gateway.api import create_gateway_app
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.resources import (
    ResourceType,
    LearningResource,
    ResourceRecommendation,
    RecommendedResourcesResponse,
    ResourceListResponse,
    ResourceEventPayload,
    RESOURCE_CATALOG,
    get_resource_by_id,
    get_resources_by_knowledge,
    get_all_resources,
    ResourceResolver,
    default_resource_resolver,
    record_resource_event,
    get_student_resource_events,
    VALID_RESOURCE_EVENT_TYPES,
)


@pytest.fixture(scope="module")
def api_client():
    app = create_gateway_app()
    return TestClient(app)


# -----------------------------------------------------------------------------
# 1. 领域模型与枚举校验
# -----------------------------------------------------------------------------
def test_01_models_validation_and_invalid_type_rejection():
    # 合法资源实体
    res = LearningResource(
        resource_id="res_test_01",
        knowledge_id="K01",
        resource_type=ResourceType.CONCEPT_CARD,
        title="测试概念微卡",
        description="描述信息",
        estimated_minutes=3,
        difficulty=0.25,
    )
    assert res.resource_id == "res_test_01"
    assert res.source == "xuehai_internal"
    assert res.is_external is False
    assert res.source_url is None

    # 非法事件类型校验抛错
    with pytest.raises(ValueError):
        ResourceEventPayload(
            student_id="S001",
            resource_id="res_test_01",
            knowledge_id="K01",
            event_type="INVALID_EVENT_TYPE",
        )


# -----------------------------------------------------------------------------
# 2. 全图谱 30 考点静态目录覆盖与资源完备性
# -----------------------------------------------------------------------------
def test_02_catalog_coverage_all_30_kps():
    all_kids = [f"K{i:02d}" for i in range(1, 31)]
    for kid in all_kids:
        items = get_resources_by_knowledge(kid)
        assert len(items) >= 3, f"考点 {kid} 学习资源少于 3 项"


def test_03_catalog_minimum_3_resources_per_kp():
    all_kids = [f"K{i:02d}" for i in range(1, 31)]
    total_resources = get_all_resources()
    assert len(total_resources) >= 90, f"资源总数 {len(total_resources)} 小于 90 项"

    for kid in all_kids:
        types = {r.resource_type for r in get_resources_by_knowledge(kid)}
        assert ResourceType.CONCEPT_CARD in types, f"考点 {kid} 缺少 CONCEPT_CARD"
        assert ResourceType.EXAMPLE in types, f"考点 {kid} 缺少 EXAMPLE"
        assert ResourceType.PRACTICE in types, f"考点 {kid} 缺少 PRACTICE"


def test_04_no_external_links_all_internal():
    for r in RESOURCE_CATALOG.values():
        assert r.is_external is False, f"资源 {r.resource_id} 标为外部资源"
        assert r.source == "xuehai_internal", f"资源 {r.resource_id} 来源非内部"
        assert r.source_url is None, f"资源 {r.resource_id} 包含了外部URL"


def test_05_catalog_queries_by_knowledge_and_type():
    k01_all = get_resources_by_knowledge("K01")
    assert len(k01_all) >= 4

    k01_concepts = get_resources_by_knowledge("K01", resource_type=ResourceType.CONCEPT_CARD)
    assert len(k01_concepts) == 1
    assert k01_concepts[0].resource_type == ResourceType.CONCEPT_CARD

    k01_practices = get_resources_by_knowledge("K01", resource_type=ResourceType.PRACTICE)
    assert len(k01_practices) == 1
    assert k01_practices[0].resource_type == ResourceType.PRACTICE


def test_06_catalog_single_item_query():
    item = get_resource_by_id("res_k01_concept")
    assert item is not None
    assert item.knowledge_id == "K01"
    assert "稀缺性" in item.title

    missing = get_resource_by_id("res_non_existent_999")
    assert missing is None


# -----------------------------------------------------------------------------
# 3. 确定性推荐引擎 Cases A ~ E 规则与时序断言
# -----------------------------------------------------------------------------
def test_07_case_a_weak_foundation_ordering():
    # Case A: mastery < 0.60
    resp = ResourceResolver.resolve(
        student_id="S001",
        knowledge_id="K01",
        mastery_override=0.35,
        consecutive_incorrect_override=0,
    )
    assert resp.case_code == "CASE_A_WEAK_FOUNDATION"
    assert resp.mastery == 0.35
    assert len(resp.recommendations) >= 3

    # 时序断言：CONCEPT_CARD 必须为首选推荐 (rank 1)
    types_in_order = [r.resource.resource_type for r in resp.recommendations]
    assert types_in_order[0] == ResourceType.CONCEPT_CARD
    assert types_in_order[1] == ResourceType.EXAMPLE
    # PRACTICE 必须在概念微卡与例题之后
    assert types_in_order[-1] == ResourceType.PRACTICE
    assert resp.recommendations[0].reason_category == "FOUNDATION"


def test_08_case_b_developing_ordering():
    # Case B: 0.60 <= mastery < 0.80
    resp = ResourceResolver.resolve(
        student_id="S001",
        knowledge_id="K01",
        mastery_override=0.72,
        consecutive_incorrect_override=0,
    )
    assert resp.case_code == "CASE_B_DEVELOPING"
    assert resp.mastery == 0.72

    types_in_order = [r.resource.resource_type for r in resp.recommendations]
    # 时序断言：优先 EXAMPLE 精析和 PRACTICE 微练
    assert types_in_order[0] == ResourceType.EXAMPLE
    assert types_in_order[1] == ResourceType.PRACTICE
    assert resp.recommendations[0].reason_category == "APPLICATION"


def test_09_case_c_mastered_with_successors():
    # Case C: mastery >= 0.80 且有后继考点 (K01 后继为 K02, K03 等)
    resp = ResourceResolver.resolve(
        student_id="S001",
        knowledge_id="K01",
        mastery_override=0.88,
        consecutive_incorrect_override=0,
    )
    assert resp.case_code == "CASE_C_MASTERED_ADVANCE"
    assert resp.mastery == 0.88

    types_in_order = [r.resource.resource_type for r in resp.recommendations]
    # 首个推荐为进阶 PRACTICE
    assert types_in_order[0] == ResourceType.PRACTICE
    # 推荐列表中包含后继考点预习微卡
    rec_kids = [r.resource.knowledge_id for r in resp.recommendations]
    assert any(k != "K01" for k in rec_kids), "Case C 应跨节点推荐后继考点的预习微卡"


def test_10_case_d_terminal_node_consolidate():
    # Case D: mastery >= 0.80 且为图谱终点考点 (K30 无后继)
    resp = ResourceResolver.resolve(
        student_id="S001",
        knowledge_id="K30",
        mastery_override=0.92,
        consecutive_incorrect_override=0,
    )
    assert resp.case_code == "CASE_D_TERMINAL_CONSOLIDATE"
    types_in_order = [r.resource.resource_type for r in resp.recommendations]
    assert types_in_order[0] == ResourceType.PRACTICE
    assert types_in_order[1] == ResourceType.EXAMPLE
    assert "终点" in resp.reason_summary


def test_11_case_e_consecutive_incorrect_override():
    # Case E: consecutive_incorrect >= 2，即便掌握度为 0.75，也必须优先触发认知受阻修复
    resp = ResourceResolver.resolve(
        student_id="S001",
        knowledge_id="K01",
        mastery_override=0.75,
        consecutive_incorrect_override=2,
    )
    assert resp.case_code == "CASE_E_ROADBLOCK_REPAIR"
    types_in_order = [r.resource.resource_type for r in resp.recommendations]
    assert types_in_order[0] == ResourceType.CONCEPT_CARD
    assert types_in_order[1] == ResourceType.EXAMPLE
    assert resp.recommendations[0].reason_category == "REPAIR"


# -----------------------------------------------------------------------------
# 4. 临界边界与纯函数确定性断言
# -----------------------------------------------------------------------------
def test_12_mastery_boundary_case_059_vs_060():
    resp_059 = ResourceResolver.resolve(student_id="S001", knowledge_id="K01", mastery_override=0.59)
    resp_060 = ResourceResolver.resolve(student_id="S001", knowledge_id="K01", mastery_override=0.60)
    assert resp_059.case_code == "CASE_A_WEAK_FOUNDATION"
    assert resp_060.case_code == "CASE_B_DEVELOPING"


def test_13_mastery_boundary_case_079_vs_080():
    resp_079 = ResourceResolver.resolve(student_id="S001", knowledge_id="K01", mastery_override=0.79)
    resp_080 = ResourceResolver.resolve(student_id="S001", knowledge_id="K01", mastery_override=0.80)
    assert resp_079.case_code == "CASE_B_DEVELOPING"
    assert resp_080.case_code == "CASE_C_MASTERED_ADVANCE"


def test_14_deterministic_ranking_100_runs_identical():
    # 纯函数验证：连续调用 100 次，返回结构字节级一致
    baseline_json = ResourceResolver.resolve(
        student_id="S001", knowledge_id="K01", mastery_override=0.45
    ).model_dump_json()

    for _ in range(100):
        current_json = ResourceResolver.resolve(
            student_id="S001", knowledge_id="K01", mastery_override=0.45
        ).model_dump_json()
        assert current_json == baseline_json


def test_15_no_jargon_in_recommended_reasons():
    FORBIDDEN_JARGON = [
        "bkt", "p_transit", "p_init", "dag", "enum", "mutationdomain",
        "float", "round_half_up", "backend", "endpoint", "jsonl", "sql"
    ]
    for case_args in [
        (0.30, 0), (0.70, 0), (0.85, 0), (0.70, 2)
    ]:
        resp = ResourceResolver.resolve(
            student_id="S001",
            knowledge_id="K01",
            mastery_override=case_args[0],
            consecutive_incorrect_override=case_args[1],
        )
        assert resp.reason_summary
        for word in FORBIDDEN_JARGON:
            assert word not in resp.reason_summary.lower(), f"推荐摘要暴露黑话: {word}"

        for rec in resp.recommendations:
            for word in FORBIDDEN_JARGON:
                assert word not in rec.recommended_reason.lower(), f"推荐理由暴露黑话: {word}"


def test_16_target_kp_inference_when_omitted():
    resp = ResourceResolver.resolve(student_id="S001", knowledge_id=None)
    assert resp.knowledge_id in CONCEPT_CARDS
    assert len(resp.recommendations) > 0


def test_17_multi_student_isolation():
    resp_s1 = ResourceResolver.resolve(student_id="S001", knowledge_id="K01")
    resp_s2 = ResourceResolver.resolve(student_id="S002", knowledge_id="K01")
    assert resp_s1.student_id == "S001"
    assert resp_s2.student_id == "S002"


# -----------------------------------------------------------------------------
# 5. 独立行为日志与零副作用不变式
# -----------------------------------------------------------------------------
def test_18_resource_events_append_only_to_resource_events_file(tmp_path):
    test_file = tmp_path / "test_resource_events.jsonl"
    record_resource_event(
        student_id="S001",
        resource_id="res_k01_concept",
        knowledge_id="K01",
        event_type="RESOURCE_VIEW",
        duration_seconds=5,
        target_file=test_file,
    )
    record_resource_event(
        student_id="S001",
        resource_id="res_k01_example",
        knowledge_id="K01",
        event_type="RESOURCE_OPEN",
        duration_seconds=30,
        target_file=test_file,
    )

    evts = get_student_resource_events("S001", source_file=test_file)
    assert len(evts) == 2
    assert evts[0]["event_type"] == "RESOURCE_VIEW"
    assert evts[1]["event_type"] == "RESOURCE_OPEN"


def test_19_telemetry_isolation_zero_learning_events_written(api_client):
    # 记录 resource 事件前，获取 learning_events.jsonl 的大小/行数
    learning_events_path = settings.DATA_DIR / "learning_events.jsonl"
    initial_learning_lines = 0
    if learning_events_path.exists():
        initial_learning_lines = len(learning_events_path.read_text(encoding="utf-8").strip().splitlines())

    # 调用资源事件端点
    resp = api_client.post(
        "/api/learning/resources/events",
        json={
            "student_id": "TEST_ISO_STU",
            "resource_id": "res_k01_concept",
            "knowledge_id": "K01",
            "event_type": "RESOURCE_COMPLETE",
            "duration_seconds": 45,
        },
    )
    assert resp.status_code == 200

    # 再次检查 learning_events.jsonl，必须严格 0 增长
    current_learning_lines = 0
    if learning_events_path.exists():
        current_learning_lines = len(learning_events_path.read_text(encoding="utf-8").strip().splitlines())

    assert current_learning_lines == initial_learning_lines, "资源事件违规写入了 learning_events.jsonl！"


def test_20_zero_bkt_mutation_invariant(api_client):
    bkt_path = settings.DATA_DIR / "bkt_states.json"
    initial_bkt_bytes = bkt_path.read_bytes() if bkt_path.exists() else b""

    # 请求自适应推荐接口
    resp = api_client.get("/api/learning/resources/recommended/S001?knowledge_id=K01")
    assert resp.status_code == 200

    # 发送资源研读行为
    resp2 = api_client.post(
        "/api/learning/resources/events",
        json={
            "student_id": "S001",
            "resource_id": "res_k01_concept",
            "knowledge_id": "K01",
            "event_type": "RESOURCE_OPEN",
            "duration_seconds": 120,
        },
    )
    assert resp2.status_code == 200

    current_bkt_bytes = bkt_path.read_bytes() if bkt_path.exists() else b""
    assert current_bkt_bytes == initial_bkt_bytes, "资源浏览违规篡改了 BKT 掌握度状态文件！"


# -----------------------------------------------------------------------------
# 6. HTTP API 接口集成与防御断言
# -----------------------------------------------------------------------------
def test_21_api_get_knowledge_resources_endpoint_200(api_client):
    resp = api_client.get("/api/learning/resources/K01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["knowledge_id"] == "K01"
    assert data["total"] >= 4
    assert len(data["resources"]) == data["total"]


def test_22_api_get_knowledge_resources_filter_by_type(api_client):
    resp = api_client.get("/api/learning/resources/K01?resource_type=CONCEPT_CARD")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["resources"][0]["resource_type"] == "CONCEPT_CARD"


def test_23_api_get_recommended_resources_endpoint_200(api_client):
    resp = api_client.get("/api/learning/resources/recommended/S001?knowledge_id=K01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["student_id"] == "S001"
    assert data["knowledge_id"] == "K01"
    assert "recommendations" in data
    assert len(data["recommendations"]) >= 3


def test_24_api_get_resource_item_endpoint_200(api_client):
    resp = api_client.get("/api/learning/resources/item/res_k01_concept")
    assert resp.status_code == 200
    data = resp.json()
    assert data["resource_id"] == "res_k01_concept"
    assert data["resource_type"] == "CONCEPT_CARD"
    assert data["is_external"] is False


def test_25_api_post_resource_events_endpoint_200(api_client):
    resp = api_client.post(
        "/api/learning/resources/events",
        json={
            "student_id": "S001",
            "resource_id": "res_k01_practice",
            "knowledge_id": "K01",
            "event_type": "RESOURCE_COMPLETE",
            "duration_seconds": 60,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "recorded"
    assert data["event_id"].startswith("evt-res-")


def test_26_api_post_learning_events_routed_to_resource_events(api_client):
    # 通过统一 /api/learning/events 传入 RESOURCE_VIEW
    resp = api_client.post(
        "/api/learning/events",
        json={
            "student_id": "S001",
            "knowledge_id": "K01",
            "event_type": "RESOURCE_VIEW",
            "payload": {
                "resource_id": "res_k01_concept",
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "recorded"
    assert data["event_id"].startswith("evt-res-")


def test_27_api_404_error_handling(api_client):
    # 未知学生
    r1 = api_client.get("/api/learning/resources/recommended/UNKNOWN_STU_999")
    assert r1.status_code == 404

    # 未知考点
    r2 = api_client.get("/api/learning/resources/K99")
    assert r2.status_code == 404

    # 未知资源
    r3 = api_client.get("/api/learning/resources/item/res_non_existent")
    assert r3.status_code == 404


def test_28_api_400_invalid_resource_type(api_client):
    # 非法资源类型过滤
    resp = api_client.get("/api/learning/resources/K01?resource_type=INVALID_TYPE")
    assert resp.status_code == 400
    assert "不支持的资源类型" in resp.json()["detail"]
