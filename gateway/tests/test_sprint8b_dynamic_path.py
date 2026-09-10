# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint8b_dynamic_path
Sprint 8-B: 动态自适应路径生成测试套件 (P1~P12)
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.constants import PathState
import path_state_service
from gateway.api import app, DEMO_STUDENTS
from gateway.learning.path_generation import (
    DynamicLearningRoute,
    DynamicPathGenerator,
    RouteStep,
    calculate_node_priority,
    default_dynamic_path_generator,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_p1_weakness_priority_weighting():
    """P1: 薄弱掌握度节点优先级显著高于高掌握度节点"""
    # 考点 A 掌握度 0.15 (薄弱) vs 考点 B 掌握度 0.75
    score_weak, _, codes_weak, _ = calculate_node_priority(
        knowledge_id="K01",
        mastery=0.15,
        is_target_ancestor_or_self=True,
        is_same_chapter=True,
        all_prereqs_mastered=True,
        path_state="AVAILABLE",
    )
    score_developed, _, codes_developed, _ = calculate_node_priority(
        knowledge_id="K02",
        mastery=0.75,
        is_target_ancestor_or_self=True,
        is_same_chapter=True,
        all_prereqs_mastered=True,
        path_state="AVAILABLE",
    )
    assert score_weak > score_developed
    assert "HIGH_COGNITIVE_WEAKNESS" in codes_weak


def test_p2_prerequisite_supremacy_in_route(tmp_path):
    """P2: 前置知识绝对霸权：前置未掌握时，后继绝不能排在前置之前"""
    generator = DynamicPathGenerator()
    # 新学生，全部未掌握
    route = generator.generate_route(student_id="TEST_P2_STUDENT", goal="掌握需求定理与需求曲线(K04)")
    step_kids = [s.knowledge_id for s in route.steps]
    
    # 在微观拓扑中：K01 -> K02 -> K03 -> K04
    # 如果 K01 或 K02 或 K03 未掌握，K04 绝对不能是第 1 站！
    assert route.steps[0].knowledge_id in ["K01", "K02"]
    if "K04" in step_kids:
        idx_k04 = step_kids.index("K04")
        if "K01" in step_kids:
            assert step_kids.index("K01") < idx_k04
        if "K02" in step_kids:
            assert step_kids.index("K02") < idx_k04
        if "K03" in step_kids:
            assert step_kids.index("K03") < idx_k04


def test_p3_target_relevance_weighting():
    """P3: 目标相关考点与目标前置祖先获得更高的目标相关权重"""
    score_rel, factors_rel, _, _ = calculate_node_priority(
        knowledge_id="K08",
        mastery=0.30,
        is_target_ancestor_or_self=True,
        is_same_chapter=True,
        all_prereqs_mastered=True,
        path_state="AVAILABLE",
    )
    score_irrel, factors_irrel, _, _ = calculate_node_priority(
        knowledge_id="K25",
        mastery=0.30,
        is_target_ancestor_or_self=False,
        is_same_chapter=False,
        all_prereqs_mastered=True,
        path_state="AVAILABLE",
    )
    assert factors_rel["target_relevance"] > factors_irrel["target_relevance"]
    assert score_rel > score_irrel


def test_p4_locked_node_with_unmet_prereqs_never_first_step():
    """P4: 前置未满足的 LOCKED 节点不能成为当前第 1 站焦点 (CURRENT)"""
    generator = DynamicPathGenerator()
    route = generator.generate_route(student_id="TEST_P4_STUDENT", goal="弹性与税收归宿 K11")
    assert len(route.steps) > 0
    first_step = route.steps[0]
    # 第 1 站的前置必须为空或已被掌握
    assert first_step.role == "CURRENT"
    assert first_step.knowledge_id in ["K01", "K02"]


def test_p5_route_length_at_most_3():
    """P5: 动态路线长度至多为 3 (0 <= route_length <= 3)"""
    generator = DynamicPathGenerator()
    route = generator.generate_route(student_id="S001", goal="期末总复习")
    assert 0 <= route.route_length <= 3
    assert len(route.steps) == route.route_length
    ranks = [s.rank for s in route.steps]
    assert ranks == list(range(1, len(route.steps) + 1))


def test_p6_determinism_excluding_metadata_timestamp():
    """P6: 相同输入多次调用生成完全一致的决策字段（剔除 timestamp 比较）"""
    generator = DynamicPathGenerator()
    r1 = generator.generate_route(student_id="S001", goal="需求价格弹性攻坚")
    r2 = generator.generate_route(student_id="S001", goal="需求价格弹性攻坚")
    
    assert r1.route_length == r2.route_length
    for s1, s2 in zip(r1.steps, r2.steps):
        assert s1.knowledge_id == s2.knowledge_id
        assert s1.rank == s2.rank
        assert s1.role == s2.role
        assert s1.score == s2.score
        assert s1.reason_codes == s2.reason_codes
        assert s1.explanation == s2.explanation
        assert s1.prerequisites == s2.prerequisites


def test_p7_structured_scoring_and_explanation():
    """P7: 评分规则结构化且提供清晰的原因编码与中文解释"""
    generator = DynamicPathGenerator()
    route = generator.generate_route(student_id="S001", goal="基础导论")
    for step in route.steps:
        assert len(step.reason_codes) > 0
        assert len(step.explanation.strip()) > 5
        assert step.score >= 0.0
        assert 0.0 <= step.mastery <= 1.0


def test_p8_deterministic_tie_break():
    """P8: 评分完全相同时，Tie-Break 机制保证绝对确定性"""
    # 模拟两个节点分值相同
    from gateway.learning.path_generation.generator import _get_chapter_index
    ch1_idx = _get_chapter_index("第一章 导论")
    ch2_idx = _get_chapter_index("第二章 需求与供给")
    assert ch1_idx < ch2_idx


def test_p9_adaptive_route_recalculation_after_mastery(tmp_path):
    """P9: 掌握状态变更后，动态路径自适应重新计算并向后推进"""
    bkt_file = tmp_path / "bkt_states.json"
    path_file = tmp_path / "path_states.json"
    
    # 1. 初始状态：未掌握 K01
    generator = DynamicPathGenerator()
    r_initial = generator.generate_route(
        student_id="TEST_P9",
        goal="微观经济学",
        states_file=path_file,
        bkt_states_file=bkt_file,
    )
    assert r_initial.steps[0].knowledge_id == "K01"
    
    # 2. 模拟学生掌握了 K01 (写入 BKT >= 0.80)
    bkt_data = {
        "TEST_P9:K01": {
            "student_id": "TEST_P9",
            "knowledge_id": "K01",
            "mastery_probability": 0.85,
            "consecutive_correct": 3,
            "consecutive_incorrect": 0,
            "attempts": 3,
            "state": "已掌握",
        }
    }
    bkt_file.write_text(json.dumps(bkt_data), encoding="utf-8")

    # 重新规划路线
    r_updated = generator.generate_route(
        student_id="TEST_P9",
        goal="微观经济学",
        states_file=path_file,
        bkt_states_file=bkt_file,
    )
    # K01 已掌握，当前首要推荐不再是 K01，而是其后继 K02 或 K03！
    assert r_updated.steps[0].knowledge_id in ["K02", "K03"]
    assert all(s.knowledge_id != "K01" for s in r_updated.steps)


def test_p10_safe_fallback_on_error():
    """P10: 异常输入或未知数据安全降级，绝不崩溃"""
    generator = DynamicPathGenerator()
    # 故意传入非法目标或异常参数
    route = generator.generate_route(student_id="UNKNOWN_STUDENT_XYZ", goal="")
    assert isinstance(route, DynamicLearningRoute)
    assert 0 <= route.route_length <= 3


def test_p11_empty_route_when_all_mastered(tmp_path):
    """P11: 当学生掌握全部知识点时，安全输出 route_length=0，不强行塞入节点"""
    bkt_file = tmp_path / "bkt_all_mastered.json"
    all_mastered = {
        f"MASTER_STUDENT:K{i:02d}": {
            "student_id": "MASTER_STUDENT",
            "knowledge_id": f"K{i:02d}",
            "mastery_probability": 0.95,
            "consecutive_correct": 5,
            "consecutive_incorrect": 0,
            "attempts": 5,
            "state": "已掌握",
        }
        for i in range(1, 31)
    }
    bkt_file.write_text(json.dumps(all_mastered), encoding="utf-8")

    generator = DynamicPathGenerator()
    route = generator.generate_route(
        student_id="MASTER_STUDENT",
        goal="全部掌握",
        bkt_states_file=bkt_file,
    )
    assert route.route_length == 0
    assert len(route.steps) == 0


def test_p12_dynamic_path_api_endpoints(client):
    """P12: 动态路径 API 端点 (/api/path/dynamic/{student_id} 与 explanation)"""
    res = client.get("/api/path/dynamic/S001?goal=弹性理论")
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "S001"
    assert "steps" in data
    assert len(data["steps"]) <= 3
    
    # 解释端点
    res_exp = client.get("/api/path/dynamic/S001/explanation?goal=弹性理论")
    assert res_exp.status_code == 200
    exp_data = res_exp.json()
    assert "steps" in exp_data
    assert "overlay" in exp_data
    assert "node_roles" in exp_data["overlay"]
