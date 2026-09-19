# -*- coding: utf-8 -*-
"""
gateway/tests/test_sprint10c_teacher.py
========================================
学海智导 (Xuehai Zhidao) — Sprint 10-C / Phase 2: Teacher Web Productization
教师端学情中台只读聚合契约测试与零侵入断言
"""

import json
from fastapi.testclient import TestClient
from gateway.api import create_gateway_app
from app.infrastructure.persistence.event_repository import default_event_repository
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from path_state_service import get_all_path_states


client = TestClient(create_gateway_app())


def test_01_teacher_overview_endpoint():
    """GET /api/teacher/overview 返回完整的班级宏观数据"""
    res = client.get("/api/teacher/overview")
    assert res.status_code == 200
    data = res.json()
    assert "class_kpis" in data
    assert "total_students" in data
    assert "active_students" in data
    assert "class_average_mastery" in data
    assert "students" in data
    assert "weak_knowledge_points" in data
    assert len(data["students"]) >= 5


def test_02_teacher_knowledge_30_points():
    """GET /api/teacher/knowledge 必须权威返回全部 30 个考点且排序确定"""
    res = client.get("/api/teacher/knowledge")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 30
    kps = data["knowledge_points"]
    assert len(kps) == 30

    # 验证排序遵循 knowledge_id 升序
    kids = [k["knowledge_id"] for k in kps]
    assert kids == sorted(kids)
    assert kids[0] == "K01"
    assert kids[-1] == "K30"

    # 验证考点核心指标结构
    for kp in kps:
        assert "knowledge_id" in kp
        assert "knowledge_name" in kp
        assert "chapter" in kp
        assert 0.0 <= kp["average_mastery"] <= 1.0
        assert kp["student_count"] >= 0
        assert kp["weak_student_count"] >= 0
        assert kp["total_mistakes"] >= 0
        assert kp["urgency"] in ("HIGH", "MEDIUM", "LOW")


def test_03_teacher_students_list():
    """GET /api/teacher/students 返回全班学生花名册摘要"""
    res = client.get("/api/teacher/students")
    assert res.status_code == 200
    students = res.json()
    assert isinstance(students, list)
    assert len(students) >= 5

    sids = [s["student_id"] for s in students]
    assert "S001" in sids
    assert "S002" in sids

    for s in students:
        assert "student_id" in s
        assert "student_name" in s
        assert "overall_mastery" in s
        assert s["risk_level"] in ("HEALTHY", "NORMAL", "ATTENTION")


def test_04_teacher_student_detail_and_isolation():
    """验证 S001 与 S002 单生详情下钻与严格物理隔离"""
    r1 = client.get("/api/teacher/students/S001")
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["student_id"] == "S001"

    r2 = client.get("/api/teacher/students/S002")
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["student_id"] == "S002"

    # 隔离断言：S001 与 S002 的详情互不污染
    assert d1["student_id"] != d2["student_id"]
    assert d1["student_name"] != d2["student_name"]


def test_05_teacher_student_detail_404():
    """不存在的学生 ID 返回 404"""
    res = client.get("/api/teacher/students/NON_EXISTENT_STUDENT_999")
    assert res.status_code == 404


def test_06_zero_mutation_invariant():
    """教师端所有查询严格为只读操作，0 BKT 变更，0 PathState 变更，0 学习事件写入"""
    student_id = "S001"

    # 读取调用前的快照
    bkt_before = default_bkt_state_repository.get_student_states(student_id)
    path_before = get_all_path_states(student_id)
    events_before = len(default_event_repository.get_events_by_student(student_id))

    # 执行全部教师端接口调用
    client.get("/api/teacher/overview")
    client.get("/api/teacher/knowledge")
    client.get("/api/teacher/students")
    client.get(f"/api/teacher/students/{student_id}")

    # 读取调用后的快照
    bkt_after = default_bkt_state_repository.get_student_states(student_id)
    path_after = get_all_path_states(student_id)
    events_after = len(default_event_repository.get_events_by_student(student_id))

    assert bkt_before == bkt_after, "教师端查询不得修改 BKT 状态"
    assert path_before == path_after, "教师端查询不得修改 PathState"
    assert events_before == events_after, "教师端查询不得产生新的学习事件"


def test_07_deterministic_repeatability():
    """连续 20 次调用返回完全一致的 JSON 内容与顺序"""
    first_res = client.get("/api/teacher/knowledge").json()
    for _ in range(20):
        next_res = client.get("/api/teacher/knowledge").json()
        assert json.dumps(first_res, sort_keys=True) == json.dumps(next_res, sort_keys=True)
