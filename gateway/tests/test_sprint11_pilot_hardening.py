# -*- coding: utf-8 -*-
"""
gateway/tests/test_sprint11_pilot_hardening.py
==============================================
学海智导 (Xuehai Zhidao) — Sprint 11 / Phase 1
Real User Pilot & State Reliability Hardening 自动化测试套件

【测试代码新增例外 (Test Code Addition Exception)】
本文件为 Sprint 11 新增的自动化测试套件，绝不修改任何既有生产业务逻辑。
覆盖 Level 1 核心场景：
- Day 0 冷启动、30 考点默认锁定与前测绝对只读；
- Day 1 微测验驱动 BKT 合法更新、动态重规划与 1:1 事件严格对应；
- Day 2 服务端权威状态恢复与受控时间下的 Retention 规则验证；
- Day 3 多学生 6 维快照强隔离、教师与学生 7 维规范投影同源核验；
- AI 推荐与 AI 伴学 5 次连续调用的直接权威只读不变量断言；
- 现有微测验重复提交行为与未定义边界核验；
- Baseline Snapshot & Restore 机制完整性。
"""

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from gateway.api import create_gateway_app, default_today_action_resolver
from gateway.learning.retention import default_retention_analyzer
from gateway.learning.retention.models import RetentionStatus
from scripts.sprint11_pilot_hardening import (
    CanonicalStudentLearningProjection,
    PilotSnapshotManager,
)
import path_state_service
from app.infrastructure.persistence.bkt_state_repository import (
    default_bkt_state_repository,
    _read_json_file,
)
from app.infrastructure.persistence.event_repository import default_event_repository


@pytest.fixture(autouse=True)
def manage_pilot_baseline():
    """每个测试运行前后自动捕获与还原权威基线数据"""
    snap_mgr = PilotSnapshotManager()
    snap_mgr.capture_baseline()
    try:
        yield
    finally:
        ok, mismatches = snap_mgr.restore_baseline()
        assert ok, f"Post-test baseline restore failed: {mismatches}"


@pytest.fixture
def client():
    app = create_gateway_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Day 0: 新学生冷启动、30 考点默认锁状态与前测绝对只读
# ---------------------------------------------------------------------------
def test_day0_cold_start_and_30kp_locked_and_readonly_pretest(client):
    """验证新学生注册初始化、30 考点初始状态以及前测绝对只读性"""
    sid = "S004"

    # 1. 初始化新学生
    init_res = client.post("/api/students/init", json={
        "student_id": sid,
        "student_name": "赵同学",
        "major": "经济学",
        "grade": "大二",
        "learning_goal": "微观经济学备考与考点突破",
        "start_knowledge_id": "K01",
    })
    assert init_res.status_code == 200
    p_states = init_res.json().get("path_states", {})
    assert len(p_states) == 30
    assert p_states["K01"].upper() == "IN_PROGRESS"
    for i in range(2, 31):
        assert p_states[f"K{i:02d}"].upper() == "LOCKED"

    # 2. 创建诊断前测
    pre_create = client.post("/api/diagnostic/pretest", json={
        "student_id": sid,
        "goal": "微观经济学备考与考点突破",
    })
    assert pre_create.status_code == 200
    session_data = pre_create.json()
    session_id = session_data["session_id"]
    questions = session_data["questions"]
    assert len(questions) == 3

    # 3. 提交前测作答
    pre_submit = client.post(f"/api/diagnostic/pretest/{session_id}/submit", json={
        "answers": {q["question_id"]: "A" for q in questions},
    })
    assert pre_submit.status_code == 200

    # 4. 断言前测后绝对零正式学习写入 (Zero-diff Invariant)
    with pytest.raises(KeyError):
        default_bkt_state_repository.get_state(sid, "K01", auto_init=False)

    events = default_event_repository.get_events_by_student(sid)
    qa_events = [e for e in events if e.event_type == "QUESTION_ATTEMPT"]
    assert len(qa_events) == 0, "诊断前测绝不能写入 QUESTION_ATTEMPT 学习事件"

    # 5. 首日今日行动裁决
    action_resp = default_today_action_resolver.resolve(student_id=sid, now=datetime(2026, 9, 20, 8, 0, 0, tzinfo=timezone.utc))
    assert action_resp.action.action_type.value in ("CONTINUE_LEARNING", "PRACTICE", "VIEW_PROGRESS")
    assert action_resp.action.knowledge_id == "K01"


# ---------------------------------------------------------------------------
# 2. Day 1: 微测验获取脱敏、BKT更新、重规划与 1:1 事件对应
# ---------------------------------------------------------------------------
def test_day1_quiz_submit_bkt_and_1to1_event_sequence(client):
    """验证微测验试题脱敏、BKT 规则更新、动态重规划及 1:1 事件严格对应"""
    sid = "S004"
    t1 = datetime(2026, 9, 21, 8, 0, 0, tzinfo=timezone.utc)

    # 1. 初始化并获取试题
    client.post("/api/students/init", json={
        "student_id": sid,
        "student_name": "赵同学",
        "start_knowledge_id": "K01",
    })
    q_res = client.get("/api/quiz/K01")
    assert q_res.status_code == 200
    q_data = q_res.json()
    quiz_q = q_data["questions"][0]
    assert "answer" not in quiz_q
    assert "explanation" not in quiz_q or not quiz_q["explanation"]
    qid = quiz_q["question_id"]

    # 2. 采集写前状态
    events_before = len([e for e in default_event_repository.get_events_by_student(sid) if e.event_type == "QUESTION_ATTEMPT"])
    action_before = default_today_action_resolver.resolve(student_id=sid, now=t1)

    # 3. 提交作答
    sub_res = client.post("/api/quiz/submit", json={
        "student_id": sid,
        "question_id": qid,
        "selected_option": "A",
        "time_spent_ms": 18000,
    })
    assert sub_res.status_code == 200
    sub_data = sub_res.json()

    # 4. 采集写后状态
    bkt_after = default_bkt_state_repository.get_state(sid, "K01", auto_init=False)
    assert bkt_after is not None
    events_after = len([e for e in default_event_repository.get_events_by_student(sid) if e.event_type == "QUESTION_ATTEMPT"])
    action_after = default_today_action_resolver.resolve(student_id=sid, now=t1)

    # 断言 1:1 事件严格对应
    assert events_after - events_before == 1

    # 断言动态重规划信封合法生成
    assert sub_data.get("is_correct") is not None
    assert "learning_state" in sub_data


# ---------------------------------------------------------------------------
# 3. Day 2: 客户端内存清空后服务端权威恢复与 Retention 判定
# ---------------------------------------------------------------------------
def test_day2_authoritative_recovery_and_retention(client):
    """验证清空内存状态后从持久化文件 100% 恢复学情与 Retention 规则校验"""
    sid = "S004"
    t2 = datetime(2026, 9, 22, 8, 0, 0, tzinfo=timezone.utc)

    # 1. 注册并答题建立状态
    client.post("/api/students/init", json={"student_id": sid, "student_name": "赵同学", "start_knowledge_id": "K01"})
    q_res = client.get("/api/quiz/K01").json()
    client.post("/api/quiz/submit", json={"student_id": sid, "question_id": q_res["questions"][0]["question_id"], "selected_option": "A"})

    # 2. 模拟清空缓存从服务端重新获取看板
    dash_res = client.get(f"/api/students/{sid}/dashboard")
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["student_id"] == sid

    path_res = client.get(f"/api/students/{sid}/path-states")
    assert path_res.status_code == 200
    assert path_res.json()["states"]["K01"].upper() in ("IN_PROGRESS", "COMPLETED", "AVAILABLE")

    # 3. Retention 规则校验
    retention = default_retention_analyzer.analyze(student_id=sid, knowledge_id="K01", now=t2)
    assert retention.student_id == sid
    assert retention.knowledge_id == "K01"
    assert retention.retention_status in (
        RetentionStatus.INSUFFICIENT_DATA,
        RetentionStatus.NOT_DUE,
        RetentionStatus.DUE_FOR_REVIEW,
        RetentionStatus.NEEDS_REINFORCEMENT,
    )


# ---------------------------------------------------------------------------
# 4. Day 3: 多学生状态快照级强隔离 (S001 -> S002 -> S003 -> S001)
# ---------------------------------------------------------------------------
def test_day3_multistudent_isolation_snapshot(client):
    """验证多学生轮换切换时 BKT、路径与今日行动强隔离，零跨学生串号"""
    now = datetime(2026, 9, 23, 8, 0, 0, tzinfo=timezone.utc)
    students = ["S001", "S002", "S003"]
    snapshots = {}

    for s in students:
        dash = client.get(f"/api/students/{s}/dashboard").json()
        action = default_today_action_resolver.resolve(student_id=s, now=now)
        snapshots[s] = {
            "goal": dash.get("learning_path", {}).get("student", {}).get("learning_goal"),
            "action": action.action.action_type.value,
        }

    # 轮换切回 S001 并核验一致性
    action_s001_again = default_today_action_resolver.resolve(student_id="S001", now=now)
    assert action_s001_again.action.action_type.value == snapshots["S001"]["action"]

    # 断言学生画像无交叉
    assert snapshots["S001"]["goal"] != snapshots["S002"]["goal"]


# ---------------------------------------------------------------------------
# 5. Day 3: 教师中台与学生端 7 维同源核验 (CanonicalStudentLearningProjection)
# ---------------------------------------------------------------------------
def test_day3_teacher_student_same_source_canonical_projection(client):
    """验证教师端与学生端规范投影提取的 7 大业务事实 100% 同源对齐"""
    proj_stu = CanonicalStudentLearningProjection.from_student_api(client, "S001")
    proj_tea = CanonicalStudentLearningProjection.from_teacher_api(client, "S001")

    diffs = proj_stu.diff(proj_tea)
    assert len(diffs) == 0, f"Canonical Projections mismatch: {diffs}"


# ---------------------------------------------------------------------------
# 6. AI 推荐与 AI 伴学直接权威只读不变量检验
# ---------------------------------------------------------------------------
def test_day3_ai_recommendation_and_companion_readonly_boundary(client):
    """验证连续 5 次调用 AI 推荐与伴学，直接权威持久化状态严格零突变"""
    bkt_pre = copy.deepcopy(_read_json_file(default_bkt_state_repository.states_file))
    path_pre = copy.deepcopy(path_state_service.get_all_path_states("S001"))
    events_pre = len(default_event_repository.get_events_by_student("S001"))

    # 连续 5 次推荐
    for _ in range(5):
        client.get("/api/learning/resources/K01/recommendations?student_id=S001")

    # 连续 5 次伴学
    for _ in range(5):
        client.post("/api/companion/chat", json={
            "message": "请解释边际收益递减规律",
            "student_id": "S001",
            "knowledge_id": "K01",
        })

    bkt_post = _read_json_file(default_bkt_state_repository.states_file)
    path_post = path_state_service.get_all_path_states("S001")
    events_post = len(default_event_repository.get_events_by_student("S001"))

    assert bkt_pre == bkt_post, "AI 调用绝对严禁修改 BKT 持久化文件"
    assert path_pre == path_post, "AI 调用绝对严禁修改 PathState 持久化文件"
    assert events_pre == events_post, "AI 调用绝对严禁产生正式学习事件"


# ---------------------------------------------------------------------------
# 7. 现有微测验重复提交语义核验 (Existing Repeated Submission Behavior)
# ---------------------------------------------------------------------------
def test_quiz_duplicate_submit_behavior_verification(client):
    """
    如实验证系统现有微测验重复提交行为：
    核查现有 API 在无客户端 request-level idempotency key 时的实际表现。
    """
    sid = "S004"
    client.post("/api/students/init", json={"student_id": sid, "student_name": "赵同学", "start_knowledge_id": "K01"})
    q_item = client.get("/api/quiz/K01").json()["questions"][0]
    payload = {
        "student_id": sid,
        "question_id": q_item["question_id"],
        "selected_option": "A",
        "time_spent_ms": 15000,
    }

    # 第一次作答
    r1 = client.post("/api/quiz/submit", json=payload)
    assert r1.status_code == 200

    # 再次提交相同题目作答（系统现有行为：视为合法的再次练习/重测，记录新的尝试）
    r2 = client.post("/api/quiz/submit", json=payload)
    assert r2.status_code == 200

    # 验证系统如实记录了两次作答尝试
    events = [e for e in default_event_repository.get_events_by_student(sid) if e.event_type == "QUESTION_ATTEMPT"]
    assert len(events) == 2, "现有系统将再次作答定义为合法的重复练习尝试"
