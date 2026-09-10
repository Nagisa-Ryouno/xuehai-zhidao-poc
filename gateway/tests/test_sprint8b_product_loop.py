# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint8b_product_loop
Sprint 8-B: 极速前测 -> 学情诊断 -> 动态自适应路径 -> 微卡 -> 微测验 -> BKT演进 -> 路径重算 端到端黄金闭环
"""

import pytest
from fastapi.testclient import TestClient

from gateway.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_sprint8b_full_e2e_adaptive_product_loop(client):
    """
    Sprint 8-B 完整产品闭环：
    新学生 -> 设定目标 -> 3题极速前测 -> 学情诊断 -> 动态路径生成(Top-3) -> 知识图谱航线高亮
    -> 当前焦点卡片学习 -> 微测验答题 -> BKT演进 -> 动态路径重新计算
    """
    # ----------------------------------------------------
    # Step 1: 初始化新学生
    # ----------------------------------------------------
    student_init_payload = {
        "student_name": "王自适",
        "major": "数字经济",
        "grade": "大二",
        "learning_goal": "攻坚微观经济学弹性与税收分析",
        "start_knowledge_id": "K01",
    }
    init_res = client.post("/api/students/init", json=student_init_payload)
    assert init_res.status_code == 200
    student_data = init_res.json()
    student_id = student_data["student_id"]
    assert student_id.startswith("DEMO_") or student_id.startswith("S")

    # ----------------------------------------------------
    # Step 2: 开启 3 题极速前测
    # ----------------------------------------------------
    pretest_res = client.post(
        "/api/diagnostic/pretest",
        json={"student_id": student_id, "goal": "攻坚微观经济学弹性与税收分析"},
    )
    assert pretest_res.status_code == 200
    session_data = pretest_res.json()
    session_id = session_data["session_id"]
    questions = session_data["questions"]
    assert len(questions) == 3
    # 验证脱敏：公开接口不泄露答案
    for q in questions:
        assert "answer" not in q
        assert "explanation" not in q

    # ----------------------------------------------------
    # Step 3: 提交前测作答并获取学情诊断与首条动态路线
    # ----------------------------------------------------
    # 模拟作答：第 1 题正确，第 2 题错误，第 3 题正确
    # Q-K02-01: C(对), Q-K04-01: A(错，标准是B), Q-K08-01: A(对)
    q_answers = {
        questions[0]["question_id"]: "C",
        questions[1]["question_id"]: "A",
        questions[2]["question_id"]: "A",
    }
    submit_res = client.post(
        f"/api/diagnostic/pretest/{session_id}/submit",
        json={"answers": q_answers},
    )
    assert submit_res.status_code == 200
    diag_body = submit_res.json()
    assert "diagnostic" in diag_body
    assert "dynamic_route" in diag_body
    
    diagnostic = diag_body["diagnostic"]
    assert diagnostic["total_questions"] == 3
    assert diagnostic["correct_count"] in [1, 2, 3]
    assert len(diagnostic["summary_text"]) > 5
    
    initial_route = diag_body["dynamic_route"]
    assert initial_route["student_id"] == student_id
    assert 1 <= initial_route["route_length"] <= 3
    assert initial_route["steps"][0]["role"] == "CURRENT"
    
    # ----------------------------------------------------
    # Step 4: 查询知识图谱并验证航线高亮与流动边
    # ----------------------------------------------------
    graph_res = client.get(f"/api/students/{student_id}/knowledge-graph/dynamic?goal=攻坚微观经济学弹性与税收分析")
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert "route_overlay" in graph_data
    assert graph_data["route_overlay"]["route_length"] == initial_route["route_length"]
    
    # ----------------------------------------------------
    # Step 5: 获取当前第一站焦点考点微卡并学习
    # ----------------------------------------------------
    focus_kid = initial_route["steps"][0]["knowledge_id"]
    card_res = client.get(f"/api/concept/{focus_kid}")
    assert card_res.status_code == 200
    card_data = card_res.json()
    assert card_data["knowledge_id"] == focus_kid
    assert len(card_data["core_concept"]) > 10

    # ----------------------------------------------------
    # Step 6: 获取当前考点微测验题目并完成正式作答
    # ----------------------------------------------------
    quiz_res = client.get(f"/api/quiz/{focus_kid}")
    assert quiz_res.status_code == 200
    quiz_data = quiz_res.json()
    assert "questions" in quiz_data
    assert len(quiz_data["questions"]) >= 1
    target_q = quiz_data["questions"][0]

    # 正式提交答题 (答对)
    quiz_submit_payload = {
        "student_id": student_id,
        "question_id": target_q["question_id"],
        "selected_option": target_q["options"][0]["key"],  # 提交有效选项
    }
    quiz_sub_res = client.post("/api/quiz/submit", json=quiz_submit_payload)
    assert quiz_sub_res.status_code == 200
    quiz_sub_data = quiz_sub_res.json()
    assert "is_correct" in quiz_sub_data
    assert "learning_state" in quiz_sub_data

    # ----------------------------------------------------
    # Step 7: 状态演进后，验证自适应动态路径即时重算
    # ----------------------------------------------------
    updated_route_res = client.get(f"/api/path/dynamic/{student_id}?goal=攻坚微观经济学弹性与税收分析")
    assert updated_route_res.status_code == 200
    updated_route = updated_route_res.json()
    assert updated_route["student_id"] == student_id
    assert 0 <= updated_route["route_length"] <= 3

    # ----------------------------------------------------
    # Step 8: 验证动态路径解释端点
    # ----------------------------------------------------
    exp_res = client.get(f"/api/path/dynamic/{student_id}/explanation?goal=攻坚微观经济学弹性与税收分析")
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert "steps" in exp_data
    for step in exp_data["steps"]:
        assert "reason_codes" in step
        assert "explanation" in step
        assert len(step["explanation"]) > 0
