# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint9f_retention_check
===========================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-F
学习保持度验证与间隔复习建议自动化测试套件 (12 项核心测试)
"""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from gateway.api import app
from gateway.learning.retention import (
    RetentionStatus,
    RetentionProfile,
    RetentionAnalyzer,
    default_retention_analyzer,
    REVIEW_AFTER_DAYS,
    ALLOWED_RETENTION_ACTIONS,
)


class MockBKTRepo:
    def __init__(self, mastery_map=None):
        self.mastery_map = mastery_map or {}

    def get_state(self, student_id: str, knowledge_id: str, auto_init: bool = False):
        key = f"{student_id}:{knowledge_id}"
        if key in self.mastery_map:
            class MockState:
                def __init__(self, m):
                    self.mastery_probability = m
            return MockState(self.mastery_map[key])
        if auto_init:
            class MockState:
                def __init__(self):
                    self.mastery_probability = 0.20
            return MockState()
        raise KeyError(f"No BKT state for {key}")


@pytest.fixture
def temp_events_file():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl", encoding="utf-8") as f:
        file_path = Path(f.name)
    yield file_path
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass


@pytest.fixture
def temp_quiz_events_file():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl", encoding="utf-8") as f:
        file_path = Path(f.name)
    yield file_path
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass


@pytest.fixture
def fixed_now():
    return datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)


def test_01_no_learning_history_insufficient_data(temp_events_file, temp_quiz_events_file, fixed_now):
    """Test 01: 无历史学习记录时，判定为 INSUFFICIENT_DATA，不建议复习"""
    analyzer = RetentionAnalyzer(
        effectiveness_file=temp_events_file,
        events_file=temp_quiz_events_file,
    )
    profile = analyzer.analyze(student_id="S001", knowledge_id="K08", now=fixed_now)

    assert profile.retention_status == RetentionStatus.INSUFFICIENT_DATA
    assert profile.should_review is False
    assert profile.suggested_action is None
    assert profile.last_learning_at is None
    assert profile.days_since_learning is None


def test_02_learning_two_days_ago_not_due(temp_events_file, temp_quiz_events_file, fixed_now):
    """Test 02: 2 天前完成正式学习，未达 3 天阈值，判定为 NOT_DUE"""
    two_days_ago = fixed_now - timedelta(days=2)
    record = {
        "event_id": "evt-test-1",
        "student_id": "S001",
        "knowledge_id": "K08",
        "event_type": "RESOURCE_SESSION_COMPLETE",
        "server_timestamp": two_days_ago.isoformat(),
        "final_mastery": 0.75,
    }
    with open(temp_events_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    analyzer = RetentionAnalyzer(
        effectiveness_file=temp_events_file,
        events_file=temp_quiz_events_file,
    )
    profile = analyzer.analyze(student_id="S001", knowledge_id="K08", now=fixed_now)

    assert profile.retention_status == RetentionStatus.NOT_DUE
    assert profile.should_review is False
    assert profile.days_since_learning == 2
    assert profile.suggested_action is None


def test_03_learning_exactly_three_days_due_for_review(temp_events_file, temp_quiz_events_file, fixed_now):
    """Test 03: 刚好 3 天达到阈值，触发 DUE_FOR_REVIEW"""
    three_days_ago = fixed_now - timedelta(days=3)
    record = {
        "event_id": "evt-test-2",
        "student_id": "S001",
        "knowledge_id": "K08",
        "event_type": "RESOURCE_SESSION_COMPLETE",
        "server_timestamp": three_days_ago.isoformat(),
        "final_mastery": 0.70,
    }
    with open(temp_events_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    analyzer = RetentionAnalyzer(
        effectiveness_file=temp_events_file,
        events_file=temp_quiz_events_file,
        bkt_repo=MockBKTRepo({"S001:K08": 0.70}),
    )
    profile = analyzer.analyze(student_id="S001", knowledge_id="K08", now=fixed_now)

    assert profile.retention_status == RetentionStatus.DUE_FOR_REVIEW
    assert profile.should_review is True
    assert profile.days_since_learning == 3


def test_04_four_days_high_mastery_retake_quiz(temp_events_file, temp_quiz_events_file, fixed_now):
    """Test 04: 4 天 + 掌握度 0.72 (>= 0.60)，建议进行快速复测 RETAKE_QUIZ"""
    four_days_ago = fixed_now - timedelta(days=4)
    record = {
        "event_id": "evt-test-3",
        "student_id": "S001",
        "knowledge_id": "K08",
        "event_type": "RESOURCE_SESSION_COMPLETE",
        "server_timestamp": four_days_ago.isoformat(),
        "final_mastery": 0.72,
    }
    with open(temp_events_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    analyzer = RetentionAnalyzer(
        effectiveness_file=temp_events_file,
        events_file=temp_quiz_events_file,
        bkt_repo=MockBKTRepo({"S001:K08": 0.72}),
    )
    profile = analyzer.analyze(student_id="S001", knowledge_id="K08", now=fixed_now)

    assert profile.retention_status == RetentionStatus.DUE_FOR_REVIEW
    assert profile.should_review is True
    assert profile.days_since_learning == 4
    assert profile.current_mastery == 0.72
    assert profile.suggested_action == "RETAKE_QUIZ"


def test_05_four_days_low_mastery_review_concept(temp_events_file, temp_quiz_events_file, fixed_now):
    """Test 05: 4 天 + 掌握度 0.55 (< 0.60)，建议先回顾概念微卡 REVIEW_CONCEPT"""
    four_days_ago = fixed_now - timedelta(days=4)
    record = {
        "event_id": "evt-test-4",
        "student_id": "S001",
        "knowledge_id": "K08",
        "event_type": "RESOURCE_SESSION_COMPLETE",
        "server_timestamp": four_days_ago.isoformat(),
        "final_mastery": 0.55,
    }
    with open(temp_events_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    analyzer = RetentionAnalyzer(
        effectiveness_file=temp_events_file,
        events_file=temp_quiz_events_file,
        bkt_repo=MockBKTRepo({"S001:K08": 0.55}),
    )
    profile = analyzer.analyze(student_id="S001", knowledge_id="K08", now=fixed_now)

    assert profile.retention_status == RetentionStatus.DUE_FOR_REVIEW
    assert profile.should_review is True
    assert profile.days_since_learning == 4
    assert profile.current_mastery == 0.55
    assert profile.suggested_action == "REVIEW_CONCEPT"


def test_06_student_context_isolation(temp_events_file, temp_quiz_events_file, fixed_now):
    """Test 06: 多学生上下文隔离：S001 有学习记录，S002 无记录，状态严格隔离"""
    four_days_ago = fixed_now - timedelta(days=4)
    record_s1 = {
        "event_id": "evt-s1",
        "student_id": "S001",
        "knowledge_id": "K08",
        "event_type": "RESOURCE_SESSION_COMPLETE",
        "server_timestamp": four_days_ago.isoformat(),
        "final_mastery": 0.75,
    }
    with open(temp_events_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record_s1) + "\n")

    analyzer = RetentionAnalyzer(
        effectiveness_file=temp_events_file,
        events_file=temp_quiz_events_file,
        bkt_repo=MockBKTRepo({"S001:K08": 0.75, "S002:K08": 0.20}),
    )
    p_s1 = analyzer.analyze(student_id="S001", knowledge_id="K08", now=fixed_now)
    p_s2 = analyzer.analyze(student_id="S002", knowledge_id="K08", now=fixed_now)

    assert p_s1.retention_status == RetentionStatus.DUE_FOR_REVIEW
    assert p_s1.should_review is True

    assert p_s2.retention_status == RetentionStatus.INSUFFICIENT_DATA
    assert p_s2.should_review is False
    assert p_s2.last_learning_at is None


def test_07_knowledge_point_isolation(temp_events_file, temp_quiz_events_file, fixed_now):
    """Test 07: 考点维度隔离：K08 有学习记录，K09 无记录，状态互不交叉"""
    four_days_ago = fixed_now - timedelta(days=4)
    record = {
        "event_id": "evt-k8",
        "student_id": "S001",
        "knowledge_id": "K08",
        "event_type": "RESOURCE_SESSION_COMPLETE",
        "server_timestamp": four_days_ago.isoformat(),
        "final_mastery": 0.75,
    }
    with open(temp_events_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    analyzer = RetentionAnalyzer(
        effectiveness_file=temp_events_file,
        events_file=temp_quiz_events_file,
        bkt_repo=MockBKTRepo({"S001:K08": 0.75, "S001:K09": 0.20}),
    )
    p_k8 = analyzer.analyze(student_id="S001", knowledge_id="K08", now=fixed_now)
    p_k9 = analyzer.analyze(student_id="S001", knowledge_id="K09", now=fixed_now)

    assert p_k8.retention_status == RetentionStatus.DUE_FOR_REVIEW
    assert p_k9.retention_status == RetentionStatus.INSUFFICIENT_DATA


def test_08_deterministic_idempotency(temp_events_file, temp_quiz_events_file, fixed_now):
    """Test 08: 纯确定性与幂等性：固定 now 重复计算 50 次结果完全一致"""
    four_days_ago = fixed_now - timedelta(days=4)
    record = {
        "event_id": "evt-repeat",
        "student_id": "S001",
        "knowledge_id": "K08",
        "event_type": "RESOURCE_SESSION_COMPLETE",
        "server_timestamp": four_days_ago.isoformat(),
        "final_mastery": 0.72,
    }
    with open(temp_events_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    analyzer = RetentionAnalyzer(
        effectiveness_file=temp_events_file,
        events_file=temp_quiz_events_file,
        bkt_repo=MockBKTRepo({"S001:K08": 0.72}),
    )

    baseline = analyzer.analyze(student_id="S001", knowledge_id="K08", now=fixed_now).model_dump()
    for _ in range(50):
        current = analyzer.analyze(student_id="S001", knowledge_id="K08", now=fixed_now).model_dump()
        assert current == baseline


def test_08b_retention_retest_failed_needs_reinforcement(temp_events_file, temp_quiz_events_file, fixed_now):
    """Test 08b: 4 天前完成学习，1 天前复测答错或掌握度低，判定为 NEEDS_REINFORCEMENT"""
    four_days_ago = fixed_now - timedelta(days=4)
    one_day_ago = fixed_now - timedelta(days=1)
    record = {
        "event_id": "evt-learn-fail",
        "student_id": "S001",
        "knowledge_id": "K08",
        "event_type": "RESOURCE_SESSION_COMPLETE",
        "server_timestamp": four_days_ago.isoformat(),
        "final_mastery": 0.70,
    }
    with open(temp_events_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    quiz_record = {
        "event_id": "evt-quiz-wrong",
        "student_id": "S001",
        "knowledge_id": "K08",
        "event_type": "QUESTION_ATTEMPT",
        "server_timestamp": one_day_ago.isoformat(),
        "payload": {"is_correct": False},
    }
    with open(temp_quiz_events_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(quiz_record) + "\n")

    analyzer = RetentionAnalyzer(
        effectiveness_file=temp_events_file,
        events_file=temp_quiz_events_file,
        bkt_repo=MockBKTRepo({"S001:K08": 0.55}),
    )
    profile = analyzer.analyze(student_id="S001", knowledge_id="K08", now=fixed_now)
    assert profile.retention_status == RetentionStatus.NEEDS_REINFORCEMENT
    assert profile.should_review is True
    assert profile.suggested_action == "REVIEW_CONCEPT"


def test_08c_retention_retest_passed_not_due(temp_events_file, temp_quiz_events_file, fixed_now):
    """Test 08c: 4 天前完成学习，1 天前复测答对且掌握度高，判定为 NOT_DUE"""
    four_days_ago = fixed_now - timedelta(days=4)
    one_day_ago = fixed_now - timedelta(days=1)
    record = {
        "event_id": "evt-learn-pass",
        "student_id": "S001",
        "knowledge_id": "K08",
        "event_type": "RESOURCE_SESSION_COMPLETE",
        "server_timestamp": four_days_ago.isoformat(),
        "final_mastery": 0.70,
    }
    with open(temp_events_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    quiz_record = {
        "event_id": "evt-quiz-right",
        "student_id": "S001",
        "knowledge_id": "K08",
        "event_type": "QUESTION_ATTEMPT",
        "server_timestamp": one_day_ago.isoformat(),
        "payload": {"is_correct": True},
    }
    with open(temp_quiz_events_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(quiz_record) + "\n")

    analyzer = RetentionAnalyzer(
        effectiveness_file=temp_events_file,
        events_file=temp_quiz_events_file,
        bkt_repo=MockBKTRepo({"S001:K08": 0.75}),
    )
    profile = analyzer.analyze(student_id="S001", knowledge_id="K08", now=fixed_now)
    assert profile.retention_status == RetentionStatus.NOT_DUE
    assert profile.should_review is False


def test_09_server_authoritative_ignores_client_tampering():
    """Test 09: 服务端绝对权威：客户端传入虚假参数不影响服务端真实判定"""
    client = TestClient(app)
    # 模拟客户端试图传入参数篡改掌握度与天数
    res = client.get("/api/learning/retention/S001/K08?mastery=0.999&days=0&retention_status=NOT_DUE")
    assert res.status_code == 200
    data = res.json()

    # 结果必须是由服务端自己读取计算的权威值
    assert "current_mastery" in data
    assert data["current_mastery"] != 0.999
    assert data["student_id"] == "S001"
    assert data["knowledge_id"] == "K08"


def test_10_analyzer_zero_mutation_invariant(fixed_now):
    """Test 10: 零数据突变不变量：Analyzer 只读分析绝对不修改 bkt_states 或 learning_events"""
    from app.core.config import settings

    bkt_file = settings.BKT_STATES_FILE
    events_file = settings.LEARNING_EVENTS_FILE

    bkt_mtime_before = bkt_file.stat().st_mtime if bkt_file.exists() else None
    events_mtime_before = events_file.stat().st_mtime if events_file.exists() else None

    # 连续执行 20 次保持度分析
    for _ in range(20):
        default_retention_analyzer.analyze(student_id="S001", knowledge_id="K08", now=fixed_now)

    bkt_mtime_after = bkt_file.stat().st_mtime if bkt_file.exists() else None
    events_mtime_after = events_file.stat().st_mtime if events_file.exists() else None

    assert bkt_mtime_before == bkt_mtime_after
    assert events_mtime_before == events_mtime_after


def test_11_micro_quiz_submission_updates_bkt_normally():
    """Test 11: 正式 Micro Quiz 提交流程正常触发 BKT 更新与行为事件沉淀"""
    client = TestClient(app)
    # 查询微测验题
    quiz_res = client.get("/api/quiz/K08")
    assert quiz_res.status_code == 200
    questions = quiz_res.json().get("questions", [])
    assert len(questions) > 0

    target_q = questions[0]
    # 正常提交作答
    submit_payload = {
        "student_id": "S001",
        "knowledge_id": "K08",
        "question_id": target_q["question_id"],
        "selected_option": target_q["options"][0]["key"],
        "time_spent_ms": 2500,
    }
    submit_res = client.post("/api/quiz/submit", json=submit_payload)
    assert submit_res.status_code == 200
    result_data = submit_res.json()
    assert "is_correct" in result_data
    assert "learning_state" in result_data
    assert "mastery_probability" in result_data["learning_state"]
    assert result_data["learning_state"]["updated"] is True


def test_12_api_contract_and_404_handling():
    """Test 12: API 契约完整性与异常处理 (200, 404)"""
    client = TestClient(app)

    # 正常请求
    res_ok = client.get("/api/learning/retention/S001/K08")
    assert res_ok.status_code == 200
    profile = res_ok.json()
    assert profile["student_id"] == "S001"
    assert profile["knowledge_id"] == "K08"
    assert profile["retention_status"] in [
        "NOT_DUE",
        "DUE_FOR_REVIEW",
        "NEEDS_REINFORCEMENT",
        "INSUFFICIENT_DATA",
    ]
    if profile["suggested_action"]:
        assert profile["suggested_action"] in ALLOWED_RETENTION_ACTIONS

    # 非法学生
    res_invalid_stu = client.get("/api/learning/retention/NON_EXISTENT_STUDENT/K08")
    assert res_invalid_stu.status_code == 404

    # 非法考点
    res_invalid_kp = client.get("/api/learning/retention/S001/INVALID_KP")
    assert res_invalid_kp.status_code == 404
