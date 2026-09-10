# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint8b_diagnostic
Sprint 8-B: 极速前测与学情诊断测试套件 (D1~D7)
"""

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.persistence.event_repository import default_event_repository
from gateway.api import app
from gateway.learning.diagnostic import (
    clear_pretest_cache,
    create_pretest_session,
    evaluate_pretest,
    get_latest_diagnostic_result,
    get_pretest_session,
    select_diagnostic_question_ids,
)


@pytest.fixture(autouse=True)
def reset_cache():
    clear_pretest_cache()
    yield
    clear_pretest_cache()


@pytest.fixture
def client():
    return TestClient(app)


def test_d1_pretest_returns_strictly_3_questions():
    """D1: 前测严格返回 3 道题目"""
    session = create_pretest_session(student_id="TEST_S8B_01", goal="掌握微观经济学基础")
    assert len(session.questions) == 3
    assert session.student_id == "TEST_S8B_01"
    assert session.completed is False


def test_d2_deterministic_question_selection():
    """D2: 相同输入产生完全一致且确定性的题目序列"""
    q1 = select_diagnostic_question_ids("微观经济学弹性与税收")
    q2 = select_diagnostic_question_ids("微观经济学弹性与税收")
    assert q1 == q2
    assert q1 == ["Q-K02-01", "Q-K04-01", "Q-K08-01"]

    q_default1 = select_diagnostic_question_ids("导论与基础")
    q_default2 = select_diagnostic_question_ids("导论与基础")
    assert q_default1 == q_default2
    assert q_default1 == ["Q-K01-01", "Q-K02-01", "Q-K04-01"]


def test_d3_questions_cover_distinct_knowledge_points_in_prereq_order():
    """D3: 题目覆盖不同知识点并按前置拓扑先后排序"""
    session = create_pretest_session(student_id="TEST_S8B_03", goal="弹性与税收")
    kids = [q.knowledge_id for q in session.questions]
    # 考点各不相同
    assert len(set(kids)) == 3
    # 拓扑序：K02 (导论) -> K04 (需求) -> K08 (弹性)
    assert kids == ["K02", "K04", "K08"]


def test_d4_public_questions_strictly_redact_answers():
    """D4: 前测公开模型严格剔除正确答案与解析"""
    session = create_pretest_session(student_id="TEST_S8B_04", goal="基础理论")
    for q in session.questions:
        dumped = q.model_dump()
        assert "answer" not in dumped
        assert "explanation" not in dumped
        assert len(q.options) >= 2
        for opt in q.options:
            assert opt.key in ["A", "B", "C", "D"]
            assert len(opt.text) > 0


def test_d5_evaluate_pretest_generates_comprehensive_diagnostic():
    """D5: 前测提交生成包含综合等级与单点掌握度初估的诊断报告"""
    session = create_pretest_session(student_id="TEST_S8B_05", goal="基础理论")
    # Q-K01-01 ans: B, Q-K02-01 ans: C, Q-K04-01 ans: B
    # 模拟答对 2 题，答错 1 题
    answers = {
        "Q-K01-01": "B",  # 对
        "Q-K02-01": "A",  # 错 (标准是 C)
        "Q-K04-01": "B",  # 对
    }
    result = evaluate_pretest(session.session_id, answers)
    
    assert result.session_id == session.session_id
    assert result.total_questions == 3
    assert result.correct_count == 2
    assert result.accuracy == 0.6667
    assert result.overall_level == "PARTIAL_FOUNDATION"
    assert result.overall_level_label == "部分掌握"
    assert "K02" in result.weaknesses
    assert "K01" in result.strengths
    assert "K04" in result.strengths
    assert result.recommended_focus_id == "K02"  # 优先推荐薄弱前置
    assert len(result.summary_text) > 10


def test_d6_pretest_does_not_mutate_formal_learning_events():
    """D6: 前测是诊断证据，绝不向正式 EventRepository 写入 QUESTION_ATTEMPT 事件"""
    initial_events = default_event_repository.get_events_by_student("TEST_S8B_06")
    assert len(initial_events) == 0

    session = create_pretest_session(student_id="TEST_S8B_06", goal="基础理论")
    evaluate_pretest(session.session_id, {"Q-K01-01": "B", "Q-K02-01": "C", "Q-K04-01": "B"})

    after_events = default_event_repository.get_events_by_student("TEST_S8B_06")
    assert len(after_events) == 0, "前测不应向正式事件库添加任何事件"


def test_d7_pretest_api_endpoints(client):
    """D7: 前测 API 端点完整交互验证"""
    # 1. 创建会话
    res = client.post(
        "/api/diagnostic/pretest",
        json={"student_id": "TEST_API_S8B", "goal": "市场供求与弹性"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert len(data["questions"]) == 3
    sid = data["session_id"]
    
    # 2. 提交作答
    ans_payload = {
        "answers": {
            data["questions"][0]["question_id"]: "B",
            data["questions"][1]["question_id"]: "B",
            data["questions"][2]["question_id"]: "A",
        }
    }
    submit_res = client.post(f"/api/diagnostic/pretest/{sid}/submit", json=ans_payload)
    assert submit_res.status_code == 200
    submit_data = submit_res.json()
    assert "diagnostic" in submit_data
    assert "dynamic_route" in submit_data
    assert submit_data["diagnostic"]["total_questions"] == 3
    assert submit_data["dynamic_route"]["student_id"] == "TEST_API_S8B"
    assert submit_data["dynamic_route"]["route_length"] <= 3
