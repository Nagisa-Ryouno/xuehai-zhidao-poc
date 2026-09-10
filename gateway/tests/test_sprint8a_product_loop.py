# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint8a_product_loop
学海智导 (Xuehai Zhidao) — Phase 4 / Sprint 8-A: Product Learning Loop MVP 验证套件

覆盖 10 大产品化质量门禁：
1. 30/30 考点概念微卡完整性与 Schema 校验
2. 概念微卡 API 端点验证 (/api/concept/{knowledge_id}, /api/concept)
3. 30/30 考点微测验全覆盖验证 (35题全集题库，涵盖 K01~K30 无死角)
4. 考点测验查询端点与脱敏验证 (/api/quiz/{knowledge_id}，杜绝答案与解析暴露)
5. 轻量级 Demo 学生初始化 (/api/students/init)
6. 端到端完整自适应闭环验证 (答题 -> 判题 -> LearningEvent -> BKT更新 -> PathState流转 -> 下游解锁)
7. AI Companion 伴学端点挂载与连通性验证 (/api/ai/companion 绝不 404)
8. AI 安全与不可越权约束验证 (allow_production_decision=False，杜绝 AI 篡改认知状态)
9. 既有业务路由与数据向后兼容性验证 (/api/overview, /api/students, /api/students/S001/dashboard)
10. 核心架构红线验证 (app/, tests/, data/seeds/ 严格 0 diff)
"""

import json
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from gateway.api import app, create_gateway_app, DEMO_STUDENTS
from gateway.content import (
    CONCEPT_CARDS,
    ALL_QUIZ_QUESTIONS,
    get_concept_card,
    get_all_concept_cards,
    get_public_questions_by_knowledge_id,
    get_question_by_id,
)
from app.core.config import settings


@pytest.fixture
def client():
    """FastAPI TestClient Fixture for unified gateway.api app"""
    return TestClient(app)


def test_gate_01_all_30_concept_cards_exist_and_conform_to_schema():
    """Gate 1: 验证全图谱 30 个考点均具备高质量概念微卡且字段完整无缺"""
    assert len(CONCEPT_CARDS) == 30, f"期望 30 个概念卡片，实际为 {len(CONCEPT_CARDS)}"
    for i in range(1, 31):
        kid = f"K{i:02d}"
        assert kid in CONCEPT_CARDS, f"缺失考点卡片: {kid}"
        card = CONCEPT_CARDS[kid]
        assert card.knowledge_id == kid
        assert len(card.knowledge_name.strip()) > 0
        assert len(card.chapter.strip()) > 0
        assert len(card.one_line_intuition.strip()) > 5
        assert len(card.core_concept.strip()) > 10
        assert len(card.simple_example.strip()) > 5
        assert len(card.common_misconceptions.strip()) > 5
        assert len(card.learning_objective.strip()) > 5
        assert 30 <= card.reading_time_seconds <= 120


def test_gate_02_concept_card_endpoints(client):
    """Gate 2: 验证概念卡片查询端点 /api/concept/{knowledge_id} 与 /api/concept"""
    # 单卡片查询
    res_k01 = client.get("/api/concept/K01")
    assert res_k01.status_code == 200
    data_k01 = res_k01.json()
    assert data_k01["knowledge_id"] == "K01"
    assert "稀缺性" in data_k01["knowledge_name"]

    res_k30 = client.get("/api/concept/K30")
    assert res_k30.status_code == 200
    assert res_k30.json()["knowledge_id"] == "K30"

    # 非法卡片 404
    res_404 = client.get("/api/concept/NON_EXISTENT_K99")
    assert res_404.status_code == 404

    # 全量卡片列表
    res_all = client.get("/api/concept")
    assert res_all.status_code == 200
    all_data = res_all.json()
    assert all_data["total"] == 30
    assert len(all_data["concept_cards"]) == 30


def test_gate_03_all_30_knowledge_points_have_playable_quizzes():
    """Gate 3: 验证全图谱 30/30 考点均覆盖微测验题目，且原 13 道种子题 100% 兼容"""
    covered_kps = {q.knowledge_id for q in ALL_QUIZ_QUESTIONS}
    assert len(covered_kps) == 30, f"测验题库必须覆盖 30 个考点，当前覆盖 {len(covered_kps)}"
    for i in range(1, 31):
        kid = f"K{i:02d}"
        assert kid in covered_kps, f"知识点 {kid} 缺失测验题目"

    # 原 13 道种子试题兼容性断言
    seeds_file = settings.SEEDS_DIR / "quiz_bank.json"
    seed_data = json.loads(seeds_file.read_text(encoding="utf-8"))
    for s_q in seed_data:
        matched = get_question_by_id(s_q["question_id"])
        assert matched is not None, f"缺失原种子试题: {s_q['question_id']}"
        assert matched.answer == s_q["answer"]
        assert matched.knowledge_id == s_q["knowledge_id"]


def test_gate_04_quiz_endpoints_sanitization_and_coverage(client):
    """Gate 4: 验证测验题目查询端点覆盖 30 考点且公开数据严格剔除正确答案与解析"""
    for i in range(1, 31):
        kid = f"K{i:02d}"
        res = client.get(f"/api/quiz/{kid}")
        assert res.status_code == 200, f"查询知识点 {kid} 测验失败"
        data = res.json()
        assert data["knowledge_id"] == kid
        assert len(data["questions"]) >= 1
        for q in data["questions"]:
            # 严格脱敏安全红线
            assert "answer" not in q, f"题目 {q['question_id']} 泄露了 answer 字段"
            assert "explanation" not in q, f"题目 {q['question_id']} 泄露了 explanation 字段"
            assert len(q["options"]) == 4

    # 非法知识点 404
    res_err = client.get("/api/quiz/K99_INVALID")
    assert res_err.status_code == 404


def test_gate_05_student_initialization_flow(client):
    """Gate 5: 验证轻量级学生档案初始化 /api/students/init"""
    payload = {
        "student_name": "测试新同学",
        "major": "金融学",
        "grade": "大二",
        "learning_goal": "微观经济学期末冲刺",
        "start_knowledge_id": "K01",
    }
    res = client.post("/api/students/init", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["student_name"] == "测试新同学"
    assert data["current_knowledge_id"] == "K01"
    sid = data["student_id"]
    assert sid.startswith("DEMO_") or sid.startswith("S")

    # 验证初始状态中 K01 为 IN_PROGRESS，其他为 LOCKED
    assert data["path_states"]["K01"] == "IN_PROGRESS"
    assert data["path_states"]["K02"] == "LOCKED"
    assert data["path_states"]["K30"] == "LOCKED"


def test_gate_06_e2e_student_learning_loop_grading_and_replanning(client):
    """Gate 6: 黄金端到端学习闭环 (做题 -> 判题 -> BKT状态更新 -> 局部重规划 -> 下游解锁)"""
    # 1. 初始化一位测试学生
    init_res = client.post(
        "/api/students/init",
        json={"student_name": "闭环验证生", "learning_goal": "期末达标", "start_knowledge_id": "K01"},
    )
    sid = init_res.json()["student_id"]

    # 2. 第一次作答 (Q-K01-01 选正确答案 B)
    sub1 = client.post(
        "/api/quiz/submit",
        json={"student_id": sid, "question_id": "Q-K01-01", "selected_option": "B", "time_spent_ms": 32000},
    )
    assert sub1.status_code == 200
    data1 = sub1.json()
    assert data1["is_correct"] is True
    assert data1["event_id"].startswith("evt-quiz-")
    assert data1["learning_state"]["updated"] is True
    assert data1["learning_state"]["mastery_percent"] > 20.0

    # 3. 第二次作答 (Q-K01-02 选正确答案 C，触发跨越 80% 掌握门槛)
    sub2 = client.post(
        "/api/quiz/submit",
        json={"student_id": sid, "question_id": "Q-K01-02", "selected_option": "C", "time_spent_ms": 28000},
    )
    assert sub2.status_code == 200
    data2 = sub2.json()
    assert data2["is_correct"] is True
    assert data2["learning_state"]["mastery_percent"] >= 80.0
    assert data2["learning_state"]["state"] == "MASTERED"

    # 4. 验证局部动态重规划审计信封生成并生效
    replanning = data2["replanning"]
    assert replanning is not None, "掌握度达标后必须生成 replanning 审计信封"
    payload_rep = replanning["canonical_payload"]
    assert payload_rep["action"] == "UNLOCK_DOWNSTREAM"
    assert payload_rep["reason_code"] == "MASTERY_THRESHOLD_REACHED"
    assert "K01" in payload_rep["affected_nodes"]
    assert "K02" in payload_rep["affected_nodes"]

    # 5. 验证持久化路径状态：K01 变为 COMPLETED，K02 成功解锁为 AVAILABLE
    states_res = client.get(f"/api/students/{sid}/path-states")
    assert states_res.status_code == 200
    states = states_res.json()["states"]
    assert states["K01"] == "COMPLETED"
    assert states["K02"] == "AVAILABLE"


def test_gate_07_ai_gateway_companion_mounted_and_no_404(client):
    """Gate 7: 验证统一应用下 AI Companion 端点正常连通，绝不返回 404"""
    payload = {
        "promptContext": {
            "user_question": "什么是机会成本？",
            "system_facts": {
                "student_id": "S001",
                "student_name": "张三",
                "major": "经济学",
                "grade": "大二",
                "learning_goal": "微观经济学",
                "current_knowledge_id": "K02",
                "current_knowledge_name": "机会成本与生产可能性边界",
                "current_chapter": "第一章 导论",
                "current_path_state": "IN_PROGRESS",
                "current_mastery_percent": 30.0,
                "mastery_target_percent": 80.0,
                "mastery_gap_percent": 50.0,
                "is_mastered": False,
                "prerequisites_met": True,
                "path_priority": "高",
                "is_path_completed": False,
                "next_action": {
                    "type": "PRACTICE",
                    "label": "开始微测验",
                    "target_knowledge_id": "K02",
                    "reason": "通过针对性微测验夯实机会成本与生产可能性边界",
                },
            },
            "grounding_rules": ["1. Only use supplied system facts."],
        },
        "question": "什么是机会成本？",
    }
    res = client.post("/api/ai/companion", json=payload)
    assert res.status_code != 404, "AI Companion 端点挂载异常，不得返回 404"
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert data["grounding_status"] == "grounded"


def test_gate_08_ai_safety_and_veto_authority(client):
    """Gate 8: 验证 AI 安全契约守卫（越权字段拦截、注入拦截与只读不可篡改）"""
    # 试图注入越权决策控制字段
    malicious_payload = {
        "promptContext": {
            "user_question": "越权修改决策",
            "system_facts": {"student_id": "S001"},
        },
        "unauthorized_decision_field": "FORCE_UNLOCK_ALL",
    }
    res = client.post("/api/ai/companion", json=malicious_payload)
    assert res.status_code == 422
    assert "SCHEMA_VALIDATION_FAILED" in res.text


def test_gate_09_backend_backward_compatibility_preserved(client):
    """Gate 9: 验证挂载的核心业务系统端点向后兼容，S001~S005 完整可用"""
    # 宏观概况
    r_overview = client.get("/api/overview")
    assert r_overview.status_code == 200
    assert r_overview.json()["student_count"] >= 5

    # 学生列表
    r_students = client.get("/api/students")
    assert r_students.status_code == 200
    assert r_students.json()["count"] >= 5

    # S001 全景看板
    r_dash = client.get("/api/students/S001/dashboard")
    assert r_dash.status_code == 200
    assert r_dash.json()["student_id"] == "S001"


def test_gate_10_freeze_invariants():
    """Gate 10: 绝对架构红线：app/、tests/、data/seeds/ 严格 0 diff"""
    cmd = ["git", "diff", "--stat", "--", "app/", "tests/", "data/seeds/"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(settings.PROJECT_ROOT),
    )
    diff_output = result.stdout.strip()
    assert diff_output == "", f"违反架构红线！app/、tests/、data/seeds/ 出现改动:\n{diff_output}"
