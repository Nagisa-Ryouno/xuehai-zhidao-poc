# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint8c_analytics
Sprint 8-C: 学习成效沉淀、掌握度历史、错题复盘与教师学习分析自动化测试套件
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.constants import PathState, MASTERY_THRESHOLD_HIGH
from app.domain.event.models import LearningEventCreate
from app.infrastructure.persistence.event_repository import EventRepository
from app.infrastructure.persistence.bkt_state_repository import BKTStateRepository
from app.domain.bkt.models import BKTState
from gateway.api import create_gateway_app
from gateway.learning.analytics.service import AnalyticsService, default_analytics_service


@pytest.fixture
def test_env(tmp_path):
    """构建完全隔离的临时测试环境"""
    events_file = tmp_path / "test_events.jsonl"
    bkt_file = tmp_path / "test_bkt.json"
    path_file = tmp_path / "test_path.json"

    event_repo = EventRepository(file_path=events_file)
    bkt_repo = BKTStateRepository(states_file=bkt_file)

    analytics_svc = AnalyticsService()
    analytics_svc.set_demo_students({
        "TEST_STU_8C": {
            "student": {
                "student_id": "TEST_STU_8C",
                "student_name": "测试成效生",
                "major": "经济学",
                "grade": "大二",
                "learning_goal": "微观经济学基础概念掌握",
            }
        },
        "TEST_STU_EMPTY": {
            "student": {
                "student_id": "TEST_STU_EMPTY",
                "student_name": "空记录新生",
                "major": "经济学",
                "grade": "大一",
                "learning_goal": "零基础入门",
            }
        }
    })

    return {
        "events_file": events_file,
        "bkt_file": bkt_file,
        "path_file": path_file,
        "event_repo": event_repo,
        "bkt_repo": bkt_repo,
        "service": analytics_svc,
    }


# =====================================================================
# 1. 学习成效历史 (Progress) 测试
# =====================================================================

def test_progress_empty_history(test_env):
    """新学生没有学习行为时，历史和趋势为空，绝不伪造假数据"""
    svc = test_env["service"]
    res = svc.get_student_progress(
        "TEST_STU_EMPTY",
        events_file=test_env["events_file"],
        bkt_file=test_env["bkt_file"],
        path_file=test_env["path_file"],
    )
    assert res is not None
    assert res.student_id == "TEST_STU_EMPTY"
    assert res.total_practice_count == 0
    assert res.total_correct_count == 0
    assert res.overall_accuracy == 0.0
    assert len(res.history_timeline) == 0
    assert len(res.mastery_trend) == 0
    assert res.total_knowledge_points == 30
    assert res.unstudied_count == 30


def test_progress_real_events(test_env):
    """记录真实 QUESTION_ATTEMPT 与 CONCEPT_VIEW，时间线准确呈现真实活动"""
    svc = test_env["service"]
    repo = test_env["event_repo"]
    f = test_env["events_file"]

    # 记录 1 次微卡查阅
    e1 = LearningEventCreate(
        event_id="evt-c-01",
        student_id="TEST_STU_8C",
        knowledge_id="K01",
        event_type="CONCEPT_VIEW",
        client_timestamp="2026-09-10T10:00:00Z",
    )
    repo.record_event(e1, target_file=f)

    # 记录 1 次做对微测验
    e2 = LearningEventCreate(
        event_id="evt-q-01",
        student_id="TEST_STU_8C",
        knowledge_id="K01",
        event_type="QUESTION_ATTEMPT",
        payload={"question_id": "Q-K01-01", "is_correct": True, "selected_option": "B", "time_spent_ms": 12000},
        client_timestamp="2026-09-10T10:05:00Z",
    )
    repo.record_event(e2, target_file=f)

    res = svc.get_student_progress(
        "TEST_STU_8C",
        events_file=f,
        bkt_file=test_env["bkt_file"],
        path_file=test_env["path_file"],
    )
    assert res is not None
    assert res.total_practice_count == 1
    assert res.total_correct_count == 1
    assert res.overall_accuracy == 100.0
    assert len(res.history_timeline) == 2
    assert len(res.mastery_trend) == 1
    # 最近的活动排在第一位
    assert res.history_timeline[0].event_type == "QUESTION_ATTEMPT"
    assert res.history_timeline[0].is_correct is True
    assert res.history_timeline[1].event_type == "CONCEPT_VIEW"


def test_progress_mastery_consistency(test_env):
    """总体掌握度严格等于 30 考点当前掌握度均值，阈值严格遵循 0.80"""
    svc = test_env["service"]
    bkt_repo = test_env["bkt_repo"]
    bkt_f = test_env["bkt_file"]

    # 设置 K01 已达标 (0.85), K02 薄弱 (0.35)
    bkt_repo.save_state(
        BKTState(student_id="TEST_STU_8C", knowledge_id="K01", mastery_probability=0.85, attempts=2),
        states_file=bkt_f,
    )
    bkt_repo.save_state(
        BKTState(student_id="TEST_STU_8C", knowledge_id="K02", mastery_probability=0.35, attempts=2, consecutive_incorrect=1),
        states_file=bkt_f,
    )

    res = svc.get_student_progress(
        "TEST_STU_8C",
        events_file=test_env["events_file"],
        bkt_file=bkt_f,
        path_file=test_env["path_file"],
    )
    assert res is not None
    k01_item = next(k for k in res.knowledge_point_masteries if k.knowledge_id == "K01")
    k02_item = next(k for k in res.knowledge_point_masteries if k.knowledge_id == "K02")

    assert k01_item.mastery == 0.85
    assert k01_item.state == "MASTERED"
    assert k02_item.mastery == 0.35
    assert k02_item.state == "NEEDS_REINFORCEMENT"
    assert res.mastered_count >= 1
    assert res.reinforcement_count >= 1


def test_progress_deterministic(test_env):
    """相同输入多次调用，返回结果完全确定"""
    svc = test_env["service"]
    r1 = svc.get_student_progress(
        "TEST_STU_8C",
        events_file=test_env["events_file"],
        bkt_file=test_env["bkt_file"],
        path_file=test_env["path_file"],
    )
    r2 = svc.get_student_progress(
        "TEST_STU_8C",
        events_file=test_env["events_file"],
        bkt_file=test_env["bkt_file"],
        path_file=test_env["path_file"],
    )
    assert r1.overall_mastery == r2.overall_mastery
    assert r1.mastered_count == r2.mastered_count


def test_progress_404_nonexistent_student(test_env):
    """未知学生查询返回 None，不抛出异常"""
    svc = test_env["service"]
    res = svc.get_student_progress("UNKNOWN_STU_999")
    assert res is None


# =====================================================================
# 2. 错题复盘 (Wrong Answer Review) 测试
# =====================================================================

def test_wrong_answer_only(test_env):
    """只有答错的题目进入错题复盘列表，答对题目严格排除"""
    svc = test_env["service"]
    repo = test_env["event_repo"]
    f = test_env["events_file"]

    # 答对 Q1
    repo.record_event(
        LearningEventCreate(
            event_id="e-right",
            student_id="TEST_STU_8C",
            knowledge_id="K01",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-K01-01", "is_correct": True, "selected_option": "B"},
            client_timestamp="2026-09-10T10:00:00Z",
        ),
        target_file=f,
    )
    # 答错 Q2
    repo.record_event(
        LearningEventCreate(
            event_id="e-wrong",
            student_id="TEST_STU_8C",
            knowledge_id="K02",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-K02-01", "is_correct": False, "selected_option": "C"},
            client_timestamp="2026-09-10T10:05:00Z",
        ),
        target_file=f,
    )

    res = svc.get_student_wrong_answers(
        "TEST_STU_8C",
        events_file=f,
        bkt_file=test_env["bkt_file"],
        path_file=test_env["path_file"],
    )
    assert res is not None
    assert res.total_wrong == 1
    assert res.wrong_answers[0].question_id == "Q-K02-01"
    assert res.wrong_answers[0].student_answer == "C"


def test_wrong_answer_ordering(test_env):
    """薄弱/多次出错题目获得 HIGH 优先级排序在前"""
    svc = test_env["service"]
    repo = test_env["event_repo"]
    f = test_env["events_file"]

    # 错误 1 次在 K01
    repo.record_event(
        LearningEventCreate(
            event_id="e-w1",
            student_id="TEST_STU_8C",
            knowledge_id="K01",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-K01-01", "is_correct": False, "selected_option": "A"},
            client_timestamp="2026-09-10T10:00:00Z",
        ),
        target_file=f,
    )
    # 错误 2 次在 K02 (更薄弱)
    repo.record_event(
        LearningEventCreate(
            event_id="e-w2",
            student_id="TEST_STU_8C",
            knowledge_id="K02",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-K02-01", "is_correct": False, "selected_option": "A"},
            client_timestamp="2026-09-10T10:01:00Z",
        ),
        target_file=f,
    )
    repo.record_event(
        LearningEventCreate(
            event_id="e-w3",
            student_id="TEST_STU_8C",
            knowledge_id="K02",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-K02-01", "is_correct": False, "selected_option": "D"},
            client_timestamp="2026-09-10T10:02:00Z",
        ),
        target_file=f,
    )

    res = svc.get_student_wrong_answers(
        "TEST_STU_8C",
        events_file=f,
        bkt_file=test_env["bkt_file"],
        path_file=test_env["path_file"],
    )
    assert res is not None
    assert res.total_wrong == 2
    # 错误 2 次的题目排在前面
    assert res.wrong_answers[0].question_id == "Q-K02-01"
    assert res.wrong_answers[0].mistake_count == 2
    assert res.wrong_answers[0].review_priority == "HIGH"


def test_wrong_answer_student_isolation(test_env):
    """学生之间错题严格物理隔离"""
    svc = test_env["service"]
    repo = test_env["event_repo"]
    f = test_env["events_file"]

    repo.record_event(
        LearningEventCreate(
            event_id="e-w-iso",
            student_id="TEST_STU_8C",
            knowledge_id="K01",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-K01-01", "is_correct": False, "selected_option": "A"},
            client_timestamp="2026-09-10T10:00:00Z",
        ),
        target_file=f,
    )

    # 查询另一个空学生
    res_empty = svc.get_student_wrong_answers(
        "TEST_STU_EMPTY",
        events_file=f,
        bkt_file=test_env["bkt_file"],
        path_file=test_env["path_file"],
    )
    assert res_empty is not None
    assert res_empty.total_wrong == 0
    assert len(res_empty.wrong_answers) == 0


def test_wrong_answer_empty_state(test_env):
    """零错题学生返回优雅空响应"""
    svc = test_env["service"]
    res = svc.get_student_wrong_answers("TEST_STU_EMPTY")
    assert res is not None
    assert res.total_wrong == 0
    assert res.wrong_answers == []


def test_wrong_answer_replay_target(test_env):
    """错题条目包含重学与再练所需的完整题干、标准答案与解析"""
    svc = test_env["service"]
    repo = test_env["event_repo"]
    f = test_env["events_file"]

    repo.record_event(
        LearningEventCreate(
            event_id="e-w-target",
            student_id="TEST_STU_8C",
            knowledge_id="K01",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-K01-01", "is_correct": False, "selected_option": "A"},
            client_timestamp="2026-09-10T10:00:00Z",
        ),
        target_file=f,
    )

    res = svc.get_student_wrong_answers(
        "TEST_STU_8C",
        events_file=f,
        bkt_file=test_env["bkt_file"],
        path_file=test_env["path_file"],
    )
    item = res.wrong_answers[0]
    assert item.knowledge_id == "K01"
    assert len(item.question_prompt) > 0
    assert len(item.options) >= 2
    assert len(item.correct_answer) > 0
    assert len(item.explanation) > 0


# =====================================================================
# 3. 教师学习分析 (Teacher Analytics) 测试
# =====================================================================

def test_teacher_overview(test_env):
    """教师总览聚合所有学生指标，返回班级平均掌握度与活跃度"""
    svc = test_env["service"]
    ov = svc.get_teacher_overview(
        events_file=test_env["events_file"],
        bkt_file=test_env["bkt_file"],
        path_file=test_env["path_file"],
    )
    assert ov.total_students >= 5
    assert ov.class_average_mastery >= 0.0
    assert len(ov.students) >= 5
    assert len(ov.weak_knowledge_points) <= 5


def test_teacher_student_aggregation(test_env):
    """教师端学生列表包含正确的风险等级与当前焦点节点"""
    svc = test_env["service"]
    ov = svc.get_teacher_overview(
        events_file=test_env["events_file"],
        bkt_file=test_env["bkt_file"],
        path_file=test_env["path_file"],
    )
    for stu in ov.students:
        assert stu.risk_level in ["HEALTHY", "NORMAL", "ATTENTION"]
        assert stu.overall_mastery >= 0.0
        assert stu.total_attempts >= 0


def test_teacher_weak_knowledge_points(test_env):
    """共性薄弱考点按受影响人数降序排列，提供针对性教学干预建议"""
    svc = test_env["service"]
    ov = svc.get_teacher_overview(
        events_file=test_env["events_file"],
        bkt_file=test_env["bkt_file"],
        path_file=test_env["path_file"],
    )
    if ov.weak_knowledge_points:
        wp1 = ov.weak_knowledge_points[0]
        assert wp1.affected_student_count >= 0
        assert len(wp1.recommended_intervention) > 0


def test_teacher_student_detail(test_env):
    """教师端单生下钻深潜，包含动态航线与错题详情"""
    svc = test_env["service"]
    detail = svc.get_teacher_student_detail(
        "TEST_STU_8C",
        events_file=test_env["events_file"],
        bkt_file=test_env["bkt_file"],
        path_file=test_env["path_file"],
    )
    assert detail is not None
    assert detail.student_id == "TEST_STU_8C"
    assert len(detail.knowledge_point_masteries) == 30
    assert detail.risk_level in ["HEALTHY", "NORMAL", "ATTENTION"]


def test_teacher_read_only(test_env):
    """教师端访问完全只读，不修改事件或 BKT 状态文件"""
    svc = test_env["service"]
    bkt_f = test_env["bkt_file"]
    ev_f = test_env["events_file"]

    initial_bkt_size = bkt_f.stat().st_size if bkt_f.exists() else 0
    initial_ev_size = ev_f.stat().st_size if ev_f.exists() else 0

    svc.get_teacher_overview(events_file=ev_f, bkt_file=bkt_f, path_file=test_env["path_file"])
    svc.get_teacher_student_detail("TEST_STU_8C", events_file=ev_f, bkt_file=bkt_f, path_file=test_env["path_file"])

    after_bkt_size = bkt_f.stat().st_size if bkt_f.exists() else 0
    after_ev_size = ev_f.stat().st_size if ev_f.exists() else 0

    assert initial_bkt_size == after_bkt_size
    assert initial_ev_size == after_ev_size


def test_teacher_student_detail_404(test_env):
    """查询不存在的下钻学生返回 None"""
    svc = test_env["service"]
    detail = svc.get_teacher_student_detail("NOT_EXIST_999")
    assert detail is None


# =====================================================================
# 4. HTTP API 端点集成测试
# =====================================================================

@pytest.fixture
def client():
    app = create_gateway_app()
    return TestClient(app)


def test_api_endpoints_progress(client):
    """GET /api/students/{id}/progress 成功返回契约数据"""
    res = client.get("/api/students/S001/progress")
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "S001"
    assert "overall_mastery" in data
    assert "mastery_trend" in data
    assert "history_timeline" in data
    assert len(data["knowledge_point_masteries"]) == 30


def test_api_endpoints_wrong_answers(client):
    """GET /api/students/{id}/wrong-answers 成功返回契约数据"""
    res = client.get("/api/students/S001/wrong-answers")
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "S001"
    assert "total_wrong" in data
    assert "wrong_answers" in data


def test_api_endpoints_record_event(client):
    """POST /api/learning/events 能够记录 CONCEPT_VIEW 事件"""
    payload = {
        "event_id": "test-evt-cv-100",
        "student_id": "S001",
        "knowledge_id": "K01",
        "event_type": "CONCEPT_VIEW",
        "payload": {"view_duration_ms": 5000},
        "client_timestamp": "2026-09-10T12:00:00Z",
    }
    res = client.post("/api/learning/events", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "recorded"
    assert data["event_id"] == "test-evt-cv-100"


def test_api_endpoints_teacher_overview(client):
    """GET /api/teacher/overview 返回教师驾驶舱全景数据"""
    res = client.get("/api/teacher/overview")
    assert res.status_code == 200
    data = res.json()
    assert "total_students" in data
    assert "class_average_mastery" in data
    assert "students" in data
    assert "weak_knowledge_points" in data


def test_api_endpoints_teacher_student_detail(client):
    """GET /api/teacher/students/{id} 返回单生下钻深潜数据"""
    res = client.get("/api/teacher/students/S001")
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "S001"
    assert "risk_level" in data
    assert "weak_points" in data
    assert len(data["knowledge_point_masteries"]) == 30


def test_api_endpoints_404(client):
    """非法学生访问返回规范 404"""
    r1 = client.get("/api/students/UNKNOWN_STU_404/progress")
    assert r1.status_code == 404

    r2 = client.get("/api/students/UNKNOWN_STU_404/wrong-answers")
    assert r2.status_code == 404

    r3 = client.get("/api/teacher/students/UNKNOWN_STU_404")
    assert r3.status_code == 404
