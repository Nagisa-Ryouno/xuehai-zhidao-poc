# -*- coding: utf-8 -*-
"""
Sprint 8-D: Product Experience Hardening & Fact Consistency Test Suite
======================================================================
涵盖:
1. Single Source of Truth 一致性矩阵 (学生端掌握度 == 教师端下钻掌握度)
2. 全链路 API 错误契约 (404/422/500 防御，绝不 500)
3. 学习事件流 Append-Only 不可篡改断言
4. 真实数据零假伪断言 (Empty State 绝对无假数据、无假趋势)
5. 学生间物理级数据隔离断言
6. 教师端绝对只读契约 (GET 操作零副作用)
7. 公开试题与接口安全审查 (不提前泄题、无敏感信息)
"""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from gateway.api import create_gateway_app
from gateway.learning.analytics.service import AnalyticsService
from app.domain.event.models import LearningEventCreate
from app.infrastructure.persistence.event_repository import EventRepository
from gateway.evaluation.judge.runtime import JudgeRuntimePolicy


@pytest.fixture
def test_env(tmp_path):
    events_file = tmp_path / "learning_events.jsonl"
    bkt_file = tmp_path / "bkt_states.json"
    path_file = tmp_path / "learning_path_states.json"

    event_repo = EventRepository(file_path=events_file)
    service = AnalyticsService()

    return {
        "tmp_path": tmp_path,
        "events_file": events_file,
        "bkt_file": bkt_file,
        "path_file": path_file,
        "event_repo": event_repo,
        "service": service,
    }


@pytest.fixture
def client():
    app = create_gateway_app()
    return TestClient(app)


# ============================================================================
# 1. Single Source of Truth 事实一致性矩阵测试 (D2)
# ============================================================================

def test_single_source_of_truth_mastery_consistency(test_env):
    """断言 1: 学生端进展掌握度与教师端下钻掌握度严格保持同一数学事实 (差值 < 0.0001)"""
    svc = test_env["service"]
    ev_f = test_env["events_file"]
    bkt_f = test_env["bkt_file"]
    path_f = test_env["path_file"]
    student_id = "S001"

    # 模拟真实做题事件
    test_env["event_repo"].record_event(
        LearningEventCreate(
            event_id="evt-01",
            student_id=student_id,
            knowledge_id="K01",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-K01-01", "is_correct": True, "selected_option": "B"},
            client_timestamp="2026-09-10T12:00:00Z",
        ),
        target_file=ev_f,
    )

    prog = svc.get_student_progress(student_id, events_file=ev_f, bkt_file=bkt_f, path_file=path_f)
    detail = svc.get_teacher_student_detail(student_id, events_file=ev_f, bkt_file=bkt_f, path_file=path_f)

    assert prog is not None
    assert detail is not None
    assert abs(prog.overall_mastery - detail.overall_mastery) < 0.0001
    assert prog.total_practice_count == detail.total_attempts
    assert abs(prog.overall_accuracy - detail.accuracy) < 0.0001


def test_single_source_of_truth_kp_distribution_consistency(test_env):
    """断言 2: 单生 30 考点在学生端与教师端映射的掌握度完全一致"""
    svc = test_env["service"]
    ev_f = test_env["events_file"]
    bkt_f = test_env["bkt_file"]
    path_f = test_env["path_file"]
    student_id = "S002"

    prog = svc.get_student_progress(student_id, events_file=ev_f, bkt_file=bkt_f, path_file=path_f)
    detail = svc.get_teacher_student_detail(student_id, events_file=ev_f, bkt_file=bkt_f, path_file=path_f)

    assert len(prog.knowledge_point_masteries) == 30
    assert len(detail.knowledge_point_masteries) == 30

    prog_map = {kp.knowledge_id: kp.mastery for kp in prog.knowledge_point_masteries}
    detail_map = {kp.knowledge_id: kp.mastery for kp in detail.knowledge_point_masteries}

    for kid, m_prog in prog_map.items():
        assert kid in detail_map
        assert abs(m_prog - detail_map[kid]) < 0.0001


def test_teacher_nested_summary_matches_top_level(test_env):
    """断言 3: 教师端下钻响应中 summary 嵌套字段与顶层字段完全一致"""
    svc = test_env["service"]
    ev_f = test_env["events_file"]
    bkt_f = test_env["bkt_file"]
    path_f = test_env["path_file"]
    student_id = "S003"

    detail = svc.get_teacher_student_detail(student_id, events_file=ev_f, bkt_file=bkt_f, path_file=path_f)
    assert detail.summary is not None
    assert detail.summary.overall_mastery == detail.overall_mastery
    assert detail.summary.accuracy == detail.accuracy
    assert detail.summary.total_attempts == detail.total_attempts
    assert detail.summary.risk_level == detail.risk_level


# ============================================================================
# 2. 全链路 API 错误契约 (404/422，绝不 500) (D3 / D5-O)
# ============================================================================

def test_api_unknown_student_progress_404(client):
    """断言 4: 查询未知学生进展返回标准 404，绝不抛出 500"""
    res = client.get("/api/students/UNKNOWN_STU_HARDEN_999/progress")
    assert res.status_code == 404
    data = res.json()
    assert "detail" in data


def test_api_unknown_student_wrong_answers_404(client):
    """断言 5: 查询未知学生错题本返回标准 404，绝不抛出 500"""
    res = client.get("/api/students/UNKNOWN_STU_HARDEN_999/wrong-answers")
    assert res.status_code == 404
    data = res.json()
    assert "detail" in data


def test_api_unknown_teacher_student_detail_404(client):
    """断言 6: 教师端下钻未知学生返回标准 404，绝不抛出 500"""
    res = client.get("/api/teacher/students/UNKNOWN_STU_HARDEN_999")
    assert res.status_code == 404
    data = res.json()
    assert "detail" in data


def test_api_unknown_knowledge_quiz_404(client):
    """断言 7: 获取不存在的知识点试题返回标准 404"""
    res = client.get("/api/quiz/K999_NON_EXIST")
    assert res.status_code == 404


def test_api_invalid_student_init_payload_422(client):
    """断言 8: 学生初始化缺少必需字段返回标准 422 验证异常，绝不 500"""
    res = client.post("/api/students/init", json={"learning_goal": "仅有目标"})
    assert res.status_code == 422


# ============================================================================
# 3. 学习事件流 Append-Only 不可篡改断言 (D3 / Red Lines)
# ============================================================================

def test_event_log_strictly_append_only(test_env):
    """断言 9: 学习事件流仅允许顺序追加，文件体积单调递增，严禁改写或删除"""
    ev_f = test_env["events_file"]
    repo = test_env["event_repo"]

    size_0 = ev_f.stat().st_size if ev_f.exists() else 0
    repo.record_event(
        LearningEventCreate(
            event_id="evt-app-1",
            student_id="STU_APP",
            knowledge_id="K01",
            event_type="CONCEPT_VIEW",
            payload={},
            client_timestamp="2026-09-10T12:00:00Z",
        ),
        target_file=ev_f,
    )
    size_1 = ev_f.stat().st_size
    assert size_1 > size_0

    repo.record_event(
        LearningEventCreate(
            event_id="evt-app-2",
            student_id="STU_APP",
            knowledge_id="K01",
            event_type="QUESTION_ATTEMPT",
            payload={"is_correct": False},
            client_timestamp="2026-09-10T12:05:00Z",
        ),
        target_file=ev_f,
    )
    size_2 = ev_f.stat().st_size
    assert size_2 > size_1

    # 验证读取出的事件按物理追加顺序保存
    all_events = repo.get_events_by_student("STU_APP", target_file=ev_f)
    assert len(all_events) == 2
    assert all_events[0].event_id == "evt-app-1"
    assert all_events[1].event_id == "evt-app-2"


# ============================================================================
# 4. 真实数据零假伪断言 (Empty State 绝对无假数据、无假趋势) (D4 / UX-03)
# ============================================================================

def test_empty_student_zero_fake_data(test_env):
    """断言 10: 纯新学生学习成效无假图表、无假历史、无假错题"""
    svc = test_env["service"]
    ev_f = test_env["events_file"]
    bkt_f = test_env["bkt_file"]
    path_f = test_env["path_file"]
    student_id = "NEW_WHITE_STU"

    svc.set_demo_students({
        student_id: {
            "student": {
                "student_id": student_id,
                "student_name": "纯白测试生",
                "major": "经济学",
                "grade": "大一",
                "learning_goal": "微观经济学",
            }
        }
    })

    prog = svc.get_student_progress(student_id, events_file=ev_f, bkt_file=bkt_f, path_file=path_f)
    wrongs = svc.get_student_wrong_answers(student_id, events_file=ev_f, bkt_file=bkt_f, path_file=path_f)

    assert prog is not None
    assert prog.total_practice_count == 0
    assert prog.total_correct_count == 0
    assert prog.overall_accuracy == 0.0
    assert len(prog.history_timeline) == 0
    assert len(prog.mastery_trend) == 0  # 绝对严禁伪造折线点
    assert wrongs.total_wrong == 0
    assert len(wrongs.wrong_answers) == 0


# ============================================================================
# 5. 学生间物理级数据隔离断言 (D3.1 / D5-K)
# ============================================================================

def test_strict_student_data_isolation(test_env):
    """断言 11: 学生 S001 的答题与错题绝不泄漏至学生 S002"""
    svc = test_env["service"]
    ev_f = test_env["events_file"]
    bkt_f = test_env["bkt_file"]
    path_f = test_env["path_file"]

    # 给学生 S001 记 1 错题
    test_env["event_repo"].record_event(
        LearningEventCreate(
            event_id="e-a-1",
            student_id="S001",
            knowledge_id="K05",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-K05-01", "is_correct": False},
            client_timestamp="2026-09-10T12:00:00Z",
        ),
        target_file=ev_f,
    )

    # 给学生 S002 记 1 正确题
    test_env["event_repo"].record_event(
        LearningEventCreate(
            event_id="e-b-1",
            student_id="S002",
            knowledge_id="K08",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-K08-01", "is_correct": True},
            client_timestamp="2026-09-10T12:05:00Z",
        ),
        target_file=ev_f,
    )

    wrongs_a = svc.get_student_wrong_answers("S001", events_file=ev_f, bkt_file=bkt_f, path_file=path_f)
    wrongs_b = svc.get_student_wrong_answers("S002", events_file=ev_f, bkt_file=bkt_f, path_file=path_f)

    assert wrongs_a is not None
    assert wrongs_a.total_wrong == 1
    assert wrongs_a.wrong_answers[0].question_id == "Q-K05-01"

    assert wrongs_b is not None
    assert wrongs_b.total_wrong == 0
    assert len(wrongs_b.wrong_answers) == 0


# ============================================================================
# 6. 教师端绝对只读契约断言 (D2 / D5-L / D5-M)
# ============================================================================

def test_teacher_analytics_zero_side_effects(test_env):
    """断言 12: 教师端所有接口均为纯只读，重复调用不改变任何磁盘数据哈希"""
    svc = test_env["service"]
    ev_f = test_env["events_file"]
    bkt_f = test_env["bkt_file"]
    path_f = test_env["path_file"]
    student_id = "S001"

    # 预先写入一条基准事件
    test_env["event_repo"].record_event(
        LearningEventCreate(
            event_id="e-base",
            student_id=student_id,
            knowledge_id="K01",
            event_type="CONCEPT_VIEW",
            payload={},
            client_timestamp="2026-09-10T12:00:00Z",
        ),
        target_file=ev_f,
    )

    before_ev_bytes = ev_f.read_bytes()
    before_bkt_bytes = bkt_f.read_bytes() if bkt_f.exists() else b""

    # 重复调用 20 次教师看板与下钻接口 (可靠性 Smoke)
    for _ in range(20):
        svc.get_teacher_overview(events_file=ev_f, bkt_file=bkt_f, path_file=path_f)
        svc.get_teacher_student_detail(student_id, events_file=ev_f, bkt_file=bkt_f, path_file=path_f)

    after_ev_bytes = ev_f.read_bytes()
    after_bkt_bytes = bkt_f.read_bytes() if bkt_f.exists() else b""

    assert before_ev_bytes == after_ev_bytes
    assert before_bkt_bytes == after_bkt_bytes


# ============================================================================
# 7. 安全与脱敏断言 (D5-P)
# ============================================================================

def test_public_quiz_questions_strictly_desensitized(client):
    """断言 13: 微测验公共接口严格脱敏，绝不向学生端泄露 answer 与 explanation"""
    res = client.get("/api/quiz/K01")
    assert res.status_code == 200
    data = res.json()
    questions = data.get("questions", [])
    assert len(questions) >= 1
    for q in questions:
        assert "answer" not in q
        assert "explanation" not in q


def test_pretest_public_questions_strictly_desensitized(client):
    """断言 14: 极速前测创建会话返回的题目严格脱敏，不含正确选项"""
    res = client.post("/api/diagnostic/pretest", json={"student_id": "S001", "goal": "微观经济学"})
    assert res.status_code == 200
    data = res.json()
    questions = data.get("questions", [])
    assert len(questions) == 3
    for q in questions:
        assert "answer" not in q
        assert "correct_option" not in q
        assert "explanation" not in q


def test_ai_judge_production_authority_strictly_disabled():
    """断言 15: AI Judge allow_production_decision 保持严格为 False，绝不接管生产决策"""
    policy = JudgeRuntimePolicy()
    assert policy.allow_production_decision is False
    with pytest.raises(Exception):
        # 尝试非法启用生产裁决必须抛出校验异常
        JudgeRuntimePolicy(allow_production_decision=True)
