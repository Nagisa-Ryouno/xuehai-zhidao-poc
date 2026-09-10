# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint8b_graph_route
Sprint 8-B: 知识图谱航线高亮与覆盖测试套件 (G1~G5)
"""

import pytest
from fastapi.testclient import TestClient

from app.services.knowledge_graph_service import knowledge_graph_service
from gateway.api import app
from gateway.learning.graph import (
    apply_route_overlay_to_graph,
    get_route_graph_overlay,
)
from gateway.learning.path_generation import default_dynamic_path_generator


@pytest.fixture
def client():
    return TestClient(app)


def test_g1_route_overlay_node_badges_and_roles():
    """G1: 航线节点徽章与角色标签准确映射 (CURRENT, NEXT, UPCOMING)"""
    route = default_dynamic_path_generator.generate_route("S001", goal="导论与需求")
    assert route.route_length >= 1
    
    overlay = get_route_graph_overlay("S001", route)
    assert overlay["student_id"] == "S001"
    assert overlay["route_length"] == route.route_length
    
    for step in route.steps:
        kid = step.knowledge_id
        assert kid in overlay["node_roles"]
        assert overlay["node_roles"][kid] == step.role
        assert overlay["node_ranks"][kid] == step.rank
        assert f"第{step.rank}站" in overlay["node_badges"][kid]


def test_g2_highlighted_flow_edges_between_route_steps():
    """G2: 航线时序流动边连接相邻步骤，具有动态动画与高亮属性"""
    route = default_dynamic_path_generator.generate_route("S001", goal="导论与需求")
    overlay = get_route_graph_overlay("S001", route)
    
    edges = overlay["highlighted_edges"]
    expected_edges_count = max(0, route.route_length - 1)
    assert len(edges) == expected_edges_count
    
    for i in range(len(edges)):
        e = edges[i]
        assert e["type"] == "routeEdge"
        assert e["animated"] is True
        assert e["source"] == route.steps[i].knowledge_id
        assert e["target"] == route.steps[i + 1].knowledge_id
        assert e["data"]["is_active_route"] is True


def test_g3_base_graph_integrity_preserved():
    """G3: 图谱原有 30 节点拓扑与属性完好无损"""
    base = knowledge_graph_service.get_student_knowledge_graph("S001")
    assert len(base["nodes"]) == 30
    assert len(base["edges"]) >= 42
    
    route = default_dynamic_path_generator.generate_route("S001", goal="导论与需求")
    applied = apply_route_overlay_to_graph(base, route)
    
    assert len(applied["nodes"]) == 30
    # 原有基础属性依然完好保留
    for n in applied["nodes"]:
        assert "id" in n
        assert "data" in n
        assert "knowledge_id" in n["data"]
        assert "accuracy" in n["data"]


def test_g4_apply_route_overlay_decorates_nodes():
    """G4: apply_route_overlay_to_graph 正确为航线节点打上高亮标记"""
    base = knowledge_graph_service.get_student_knowledge_graph("S001")
    route = default_dynamic_path_generator.generate_route("S001", goal="导论与需求")
    applied = apply_route_overlay_to_graph(base, route)
    
    route_kids = {s.knowledge_id for s in route.steps}
    for n in applied["nodes"]:
        kid = n["id"]
        data = n["data"]
        if kid in route_kids:
            assert data["is_on_route"] is True
            assert data["route_role"] in ["CURRENT", "NEXT", "UPCOMING"]
            assert data["route_rank"] in [1, 2, 3]
            assert "第" in data["route_badge"]
        else:
            assert data["is_on_route"] is False
            assert data["route_role"] is None


def test_g5_dynamic_knowledge_graph_endpoint(client):
    """G5: 动态图谱 API 端点 (/api/students/{student_id}/knowledge-graph/dynamic)"""
    res = client.get("/api/students/S001/knowledge-graph/dynamic?goal=需求弹性")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert "dynamic_route" in data
    assert "route_overlay" in data
    assert len(data["nodes"]) == 30
    # 航线存在
    assert len(data["dynamic_route"]["steps"]) <= 3
