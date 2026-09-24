# -*- coding: utf-8 -*-
"""
gateway/tests/test_sprint10d_teacher_actions.py
===============================================
学海智导 (Xuehai Zhidao) — Sprint 10-D Phase 4-A: Teacher Action Loop
教师轻量教学动作核心领域模型与持久化仓储单元测试 (Phase 4-A)

测试目标与验收红线：
1. Action Domain Model 严格白名单校验 (REVIEW_CONCEPT / RETRY_PRACTICE / MARK_FOLLOWED)
2. TeacherActionRecord 字段逐项验证 (无 knowledge_name, 无 note, 无 status/expires_at/consumed 等状态机)
3. TeacherActionRepository 追加写 JSONL 与 tmp_path 测试数据隔离 (绝不触碰 data/teacher_actions.jsonl)
4. 服务端 5 秒防重复提交保护 (Duplicate Submission Protection)
5. 教师端全量历史读取 (全量流水永久保留，按 created_at 倒序，动态匹配 knowledge_name)
6. 学生端建议读取管道规则 (最近7天 freshness window、仅 actionable、同一考点最新去重、created_at DESC、最多3条)
7. MARK_FOLLOWED 语义锁定 (不流向学生端，且不覆盖、不撤回、不注销此前建议)
8. 零副作用与零核心污染断言 (0 BKT、0 PathState、0 学习事件增长、0 AI 调用)
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import settings
from gateway.api import create_gateway_app
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.teacher_actions import (
    TeacherActionCreateRequest,
    TeacherActionRecord,
    TeacherActionItem,
    TeacherActionHistoryResponse,
    StudentRecommendationItem,
    StudentRecommendationsResponse,
    TeacherActionRepository,
    VALID_ACTION_TYPES,
    ACTIONABLE_ACTION_TYPES,
    DEFAULT_TEACHER_ACTIONS_FILE,
)


# ==============================================================================
# 1. Action Domain Model & Record 字段结构测试
# ==============================================================================

def test_01_domain_model_action_whitelist():
    """验证动作类型严格限定于三种白名单，非法类型抛出验证错误"""
    for valid_type in ["REVIEW_CONCEPT", "RETRY_PRACTICE", "MARK_FOLLOWED"]:
        req = TeacherActionCreateRequest(knowledge_id="K02", action_type=valid_type)
        assert req.action_type == valid_type
        assert req.knowledge_id == "K02"

    with pytest.raises(ValidationError):
        TeacherActionCreateRequest(knowledge_id="K02", action_type="ASSIGN_HOMEWORK")  # 非法类型

    with pytest.raises(ValidationError):
        TeacherActionCreateRequest(knowledge_id="K02", action_type="SEND_MESSAGE")  # 非法类型

    with pytest.raises(ValidationError):
        TeacherActionCreateRequest(knowledge_id="K02", action_type="")  # 空字符串


def test_02_record_field_purity_and_provenance():
    """
    TeacherActionRecord 字段权威纯洁性断言：
    - 必须包含：action_id, teacher_id, student_id, knowledge_id, action_type, created_at
    - 绝不能包含：knowledge_name (动态获取), note/message (无自由文本),
                 status/expires_at/consumed/dismissed (无额外状态机)
    """
    record = TeacherActionRecord(
        action_id="act-tea-test123456",
        teacher_id="T001",
        student_id="S001",
        knowledge_id="K02",
        action_type="REVIEW_CONCEPT",
        created_at="2026-09-22T12:00:00+00:00",
    )

    data = record.model_dump()
    assert set(data.keys()) == {
        "action_id",
        "teacher_id",
        "student_id",
        "knowledge_id",
        "action_type",
        "created_at",
    }
    # 显式确认禁止字段不存在
    assert "knowledge_name" not in data
    assert "note" not in data
    assert "message" not in data
    assert "status" not in data
    assert "expires_at" not in data
    assert "consumed" not in data
    assert "dismissed" not in data


def test_03_request_payload_strips_untrusted_fields():
    """客户端请求 payload 中若夹带恶意或多余字段，必须被安全剥离，绝不进入 Record"""
    payload = {
        "knowledge_id": "K01",
        "action_type": "RETRY_PRACTICE",
        "teacher_id": "HACKER_999",  # 客户端伪造教师身份
        "note": "恶意备注",
        "is_affected": True,
    }
    req = TeacherActionCreateRequest(**payload)
    dumped = req.model_dump()
    assert "teacher_id" not in dumped
    assert "note" not in dumped
    assert "is_affected" not in dumped
    assert dumped == {"knowledge_id": "K01", "action_type": "RETRY_PRACTICE"}


# ==============================================================================
# 2. 持久化仓储与测试数据隔离测试 (Test Data Isolation)
# ==============================================================================

def test_04_repository_persistence_and_test_data_isolation(tmp_path: Path):
    """
    仓储依赖注入与物理隔离测试：
    注入 tmp_path / 'test_actions.jsonl'，断言：
    1. 真实追加单行 JSONL 记录；
    2. 生产文件 data/teacher_actions.jsonl 零增长、零改动。
    """
    prod_file = DEFAULT_TEACHER_ACTIONS_FILE
    prod_exists_before = prod_file.exists()
    prod_size_before = prod_file.stat().st_size if prod_exists_before else 0

    isolated_file = tmp_path / "test_teacher_actions.jsonl"
    repo = TeacherActionRepository(file_path=isolated_file)

    rec = repo.record_action(
        student_id="S001",
        knowledge_id="K02",
        action_type="REVIEW_CONCEPT",
        teacher_id="T001",
    )

    assert isolated_file.exists()
    lines = isolated_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    saved_data = json.loads(lines[0])
    assert saved_data["action_id"] == rec.action_id
    assert saved_data["student_id"] == "S001"
    assert saved_data["knowledge_id"] == "K02"
    assert saved_data["action_type"] == "REVIEW_CONCEPT"
    assert saved_data["teacher_id"] == "T001"

    # 断言生产文件绝对未受任何触碰
    if not prod_exists_before:
        assert not prod_file.exists(), "测试绝对不能在生产目录创建 teacher_actions.jsonl"
    else:
        assert prod_file.stat().st_size == prod_size_before, "测试绝对不能修改生产 teacher_actions.jsonl"


def test_05_repository_invalid_knowledge_point_rejected(tmp_path: Path):
    """提交不存在的考点时抛出 ValueError"""
    repo = TeacherActionRepository(file_path=tmp_path / "test_actions.jsonl")
    with pytest.raises(ValueError, match="找不到指定考点"):
        repo.record_action(student_id="S001", knowledge_id="K999", action_type="REVIEW_CONCEPT")


def test_06_repository_invalid_action_type_rejected(tmp_path: Path):
    """提交非法动作类型时抛出 ValueError"""
    repo = TeacherActionRepository(file_path=tmp_path / "test_actions.jsonl")
    with pytest.raises(ValueError, match="非法的教学动作类型"):
        repo.record_action(student_id="S001", knowledge_id="K02", action_type="DELETE_ACCOUNT")


# ==============================================================================
# 3. 服务端 5 秒防重复提交保护 (Duplicate Submission Protection)
# ==============================================================================

def test_07_duplicate_submission_protection_within_5_seconds(tmp_path: Path):
    """
    同一 (student_id, knowledge_id, action_type) 在 5 秒内重复提交：
    1. 返回已有记录 (相同的 action_id)；
    2. 文件中仅有 1 行记录，不产生冗余追加。
    """
    repo = TeacherActionRepository(file_path=tmp_path / "test_actions.jsonl")
    base_time = datetime(2026, 9, 22, 10, 0, 0, tzinfo=timezone.utc)

    # 首次提交 (t = 0s)
    rec1 = repo.record_action("S001", "K02", "REVIEW_CONCEPT", now=base_time)

    # 2 秒后重复提交 (t = 2.0s < 5.0s)
    t2 = base_time + timedelta(seconds=2.0)
    rec2 = repo.record_action("S001", "K02", "REVIEW_CONCEPT", now=t2)

    assert rec2.action_id == rec1.action_id
    assert rec2.created_at == rec1.created_at

    # 验证底层文件只有 1 条记录
    lines = (tmp_path / "test_actions.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1


def test_08_different_action_type_not_blocked_by_duplicate_protection(tmp_path: Path):
    """在 5 秒内如果动作类型不同，不触发防重，正常追加新记录"""
    repo = TeacherActionRepository(file_path=tmp_path / "test_actions.jsonl")
    base_time = datetime(2026, 9, 22, 10, 0, 0, tzinfo=timezone.utc)

    rec1 = repo.record_action("S001", "K02", "REVIEW_CONCEPT", now=base_time)
    t2 = base_time + timedelta(seconds=1.0)
    rec2 = repo.record_action("S001", "K02", "RETRY_PRACTICE", now=t2)

    assert rec2.action_id != rec1.action_id
    assert rec2.action_type == "RETRY_PRACTICE"

    lines = (tmp_path / "test_actions.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2


def test_09_subsequent_action_after_5_seconds_allowed(tmp_path: Path):
    """超过 5 秒的再次关注视为合法动作，正常产生新记录追加"""
    repo = TeacherActionRepository(file_path=tmp_path / "test_actions.jsonl")
    base_time = datetime(2026, 9, 22, 10, 0, 0, tzinfo=timezone.utc)

    rec1 = repo.record_action("S001", "K02", "REVIEW_CONCEPT", now=base_time)
    t2 = base_time + timedelta(seconds=6.0)  # 6 秒后
    rec2 = repo.record_action("S001", "K02", "REVIEW_CONCEPT", now=t2)

    assert rec2.action_id != rec1.action_id
    lines = (tmp_path / "test_actions.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2


# ==============================================================================
# 4. 教师端全量历史只读模型测试 (Teacher Action History)
# ==============================================================================

def test_10_teacher_action_history_permanent_and_dynamic_name(tmp_path: Path):
    """
    教师历史只读模型测试：
    1. 包含 MARK_FOLLOWED 在内的全量动作；
    2. 按时间倒序排列；
    3. 动态解析 knowledge_name (来自 CONCEPT_CARDS)；
    4. 不受 7 天时效限制，不受条数上限截断。
    """
    repo = TeacherActionRepository(file_path=tmp_path / "test_actions.jsonl")
    t0 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)  # 21 天前

    repo.record_action("S001", "K01", "MARK_FOLLOWED", now=t0)
    repo.record_action("S001", "K02", "REVIEW_CONCEPT", now=t0 + timedelta(days=5))
    repo.record_action("S001", "K03", "RETRY_PRACTICE", now=t0 + timedelta(days=10))
    repo.record_action("S001", "K04", "MARK_FOLLOWED", now=t0 + timedelta(days=15))

    history = repo.get_teacher_action_history("S001")
    assert history.student_id == "S001"
    assert history.total_count == 4
    assert len(history.actions) == 4

    # 验证时间倒序 (最新在前)
    assert history.actions[0].knowledge_id == "K04"
    assert history.actions[0].action_type == "MARK_FOLLOWED"
    assert history.actions[3].knowledge_id == "K01"

    # 验证动态匹配考点名称
    for item in history.actions:
        assert item.knowledge_name == CONCEPT_CARDS[item.knowledge_id].knowledge_name
        assert item.teacher_id == "T001"


# ==============================================================================
# 5. 学生端建议读取规则测试 (Student Recommendations Pipeline)
# ==============================================================================

def test_11_student_recommendations_filters_mark_followed(tmp_path: Path):
    """MARK_FOLLOWED 绝不流向学生端推荐"""
    repo = TeacherActionRepository(file_path=tmp_path / "test_actions.jsonl")
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)

    repo.record_action("S001", "K01", "MARK_FOLLOWED", now=now - timedelta(hours=2))
    repo.record_action("S001", "K02", "REVIEW_CONCEPT", now=now - timedelta(hours=1))

    recs = repo.get_student_recommendations("S001", now=now)
    assert recs.total_count == 1
    assert len(recs.recommendations) == 1
    assert recs.recommendations[0].knowledge_id == "K02"
    assert recs.recommendations[0].action_type == "REVIEW_CONCEPT"


def test_12_mark_followed_does_not_cancel_previous_actionable_recommendation(tmp_path: Path):
    """
    语义锁定断言：
    MARK_FOLLOWED 仅表示教师关注，不具有撤回/关闭/覆盖此前建议的语义。
    先建议 REVIEW_CONCEPT，后标记 MARK_FOLLOWED，学生端该考点的建议依然有效存在！
    """
    repo = TeacherActionRepository(file_path=tmp_path / "test_actions.jsonl")
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)

    # 1. 教师提出 K02 复习建议
    repo.record_action("S001", "K02", "REVIEW_CONCEPT", now=now - timedelta(hours=2))
    # 2. 教师后续在同一考点标记为已关注
    repo.record_action("S001", "K02", "MARK_FOLLOWED", now=now - timedelta(hours=1))

    # 学生端读取：K02 的复习建议仍然存在且有效
    recs = repo.get_student_recommendations("S001", now=now)
    assert recs.total_count == 1
    assert recs.recommendations[0].knowledge_id == "K02"
    assert recs.recommendations[0].action_type == "REVIEW_CONCEPT"


def test_13_student_recommendations_7d_freshness_window(tmp_path: Path):
    """
    7 天 Freshness Window 断言：
    - 8 天前的建议：学生端自动过滤，不再显示；教师历史依然完整保留；
    - 6 天前的建议：学生端正常展示。
    """
    repo = TeacherActionRepository(file_path=tmp_path / "test_actions.jsonl")
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)

    # 8 天前的建议
    repo.record_action("S001", "K01", "REVIEW_CONCEPT", now=now - timedelta(days=8))
    # 6 天前的建议
    repo.record_action("S001", "K02", "RETRY_PRACTICE", now=now - timedelta(days=6))

    recs = repo.get_student_recommendations("S001", now=now)
    assert recs.total_count == 1
    assert len(recs.recommendations) == 1
    assert recs.recommendations[0].knowledge_id == "K02"

    # 验证教师端历史依然包含 8 天前的记录
    history = repo.get_teacher_action_history("S001")
    assert history.total_count == 2


def test_14_student_recommendations_dedup_latest_per_knowledge(tmp_path: Path):
    """同一考点存在多次建议时，仅保留最新一条建议"""
    repo = TeacherActionRepository(file_path=tmp_path / "test_actions.jsonl")
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)

    # 3 天前建议复习 K02
    repo.record_action("S001", "K02", "REVIEW_CONCEPT", now=now - timedelta(days=3))
    # 1 天前建议重新练习 K02
    repo.record_action("S001", "K02", "RETRY_PRACTICE", now=now - timedelta(days=1))

    recs = repo.get_student_recommendations("S001", now=now)
    assert recs.total_count == 1
    assert recs.recommendations[0].knowledge_id == "K02"
    assert recs.recommendations[0].action_type == "RETRY_PRACTICE"  # 最新的一条


def test_15_student_recommendations_limit_max_3_items(tmp_path: Path):
    """
    学生端建议数量上限严格为 3 条：
    存在 5 个不同考点的有效建议时，仅返回最新的 3 条；
    教师端历史依然完整返回 5 条，不发生截断。
    """
    repo = TeacherActionRepository(file_path=tmp_path / "test_actions.jsonl")
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)

    repo.record_action("S001", "K01", "REVIEW_CONCEPT", now=now - timedelta(days=5))
    repo.record_action("S001", "K02", "REVIEW_CONCEPT", now=now - timedelta(days=4))
    repo.record_action("S001", "K03", "RETRY_PRACTICE", now=now - timedelta(days=3))
    repo.record_action("S001", "K04", "REVIEW_CONCEPT", now=now - timedelta(days=2))
    repo.record_action("S001", "K05", "RETRY_PRACTICE", now=now - timedelta(days=1))

    recs = repo.get_student_recommendations("S001", now=now, max_items=3)
    assert recs.total_count == 3
    assert len(recs.recommendations) == 3
    # 倒序取最新的 3 条 (K05, K04, K03)
    assert [r.knowledge_id for r in recs.recommendations] == ["K05", "K04", "K03"]

    # 教师历史不受影响，依然是 5 条
    history = repo.get_teacher_action_history("S001")
    assert history.total_count == 5


# ==============================================================================
# 6. 零副作用与零核心污染断言 (Zero Side-Effects Invariants)
# ==============================================================================

def test_16_zero_bkt_and_learning_events_pollution(tmp_path: Path):
    """
    严格红线断言：
    执行教师动作记录与读取前后，
    1. data/learning_events.jsonl 零写入、零增长；
    2. data/bkt_states.json 绝对 0 字节变化；
    3. data/learning_path_states.json 绝对 0 字节变化。
    """
    learning_events_file = settings.DATA_DIR / "learning_events.jsonl"
    bkt_file = settings.DATA_DIR / "bkt_states.json"
    path_file = settings.DATA_DIR / "learning_path_states.json"

    le_before = learning_events_file.read_bytes() if learning_events_file.exists() else b""
    bkt_before = bkt_file.read_bytes() if bkt_file.exists() else b""
    path_before = path_file.read_bytes() if path_file.exists() else b""

    # 执行完整的动作记录与推荐读取
    repo = TeacherActionRepository(file_path=tmp_path / "test_actions.jsonl")
    repo.record_action("S001", "K02", "REVIEW_CONCEPT")
    repo.record_action("S001", "K02", "RETRY_PRACTICE")
    repo.record_action("S001", "K02", "MARK_FOLLOWED")
    _ = repo.get_teacher_action_history("S001")
    _ = repo.get_student_recommendations("S001")

    le_after = learning_events_file.read_bytes() if learning_events_file.exists() else b""
    bkt_after = bkt_file.read_bytes() if bkt_file.exists() else b""
    path_after = path_file.read_bytes() if path_file.exists() else b""

    assert le_before == le_after, "教师教学动作绝对不能写入正式 learning_events.jsonl！"
    assert bkt_before == bkt_after, "教师教学动作绝对不能修改 bkt_states.json！"
    assert path_before == path_after, "教师教学动作绝对不能修改 learning_path_states.json！"


# ==============================================================================
# 7. Phase 4-B API 端点契约与行为测试 (API Contract Tests)
# ==============================================================================

@pytest.fixture
def api_test_setup(tmp_path: Path):
    """创建挂载了隔离仓储的 TestClient 与仓储实例"""
    isolated_file = tmp_path / "api_test_actions.jsonl"
    repo = TeacherActionRepository(file_path=isolated_file)
    app = create_gateway_app(teacher_action_repo=repo)
    client = TestClient(app)
    return client, repo, isolated_file


def test_17_api_post_action_success(api_test_setup):
    """POST /api/teacher/students/{student_id}/actions: 成功创建动作并返回 TeacherActionItem"""
    client, repo, _ = api_test_setup
    payload = {"knowledge_id": "K02", "action_type": "REVIEW_CONCEPT"}
    res = client.post("/api/teacher/students/S001/actions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "S001"
    assert data["knowledge_id"] == "K02"
    assert data["knowledge_name"] == "机会成本与生产可能性边界"
    assert data["action_type"] == "REVIEW_CONCEPT"
    assert data["teacher_id"] == "T001"
    assert data["action_id"].startswith("act-tea-")
    assert "created_at" in data


def test_18_api_post_action_404_invalid_student(api_test_setup):
    """POST 针对不存在的学生返回 404"""
    client, _, _ = api_test_setup
    payload = {"knowledge_id": "K02", "action_type": "REVIEW_CONCEPT"}
    res = client.post("/api/teacher/students/S999/actions", json=payload)
    assert res.status_code == 404
    assert "找不到指定学生" in res.json()["detail"]


def test_19_api_post_action_404_invalid_knowledge(api_test_setup):
    """POST 针对不存在的考点返回 404"""
    client, _, _ = api_test_setup
    payload = {"knowledge_id": "K999", "action_type": "REVIEW_CONCEPT"}
    res = client.post("/api/teacher/students/S001/actions", json=payload)
    assert res.status_code == 404
    assert "找不到指定考点" in res.json()["detail"]


def test_20_api_post_action_422_invalid_action_type(api_test_setup):
    """POST 针对非白名单 action_type 返回 422 Unprocessable Entity"""
    client, _, _ = api_test_setup
    payload = {"knowledge_id": "K02", "action_type": "ASSIGN_HOMEWORK"}
    res = client.post("/api/teacher/students/S001/actions", json=payload)
    assert res.status_code == 422


def test_21_api_post_action_client_teacher_id_untrusted(api_test_setup):
    """POST 时客户端伪造的 teacher_id 及额外字段被安全忽略，服务端强制使用 T001"""
    client, _, isolated_file = api_test_setup
    payload = {
        "knowledge_id": "K02",
        "action_type": "REVIEW_CONCEPT",
        "teacher_id": "HACKER_999",
        "note": "恶意文本",
        "status": "fake_status",
    }
    res = client.post("/api/teacher/students/S001/actions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["teacher_id"] == "T001"
    assert "note" not in data
    assert "status" not in data

    # 检查底层落盘文件
    lines = isolated_file.read_text(encoding="utf-8").strip().split("\n")
    saved = json.loads(lines[0])
    assert saved["teacher_id"] == "T001"
    assert "note" not in saved


def test_22_api_duplicate_submission_protection(api_test_setup):
    """API 连续快速调用 POST 同一动作触发 5 秒防重复提交保护"""
    client, _, isolated_file = api_test_setup
    payload = {"knowledge_id": "K02", "action_type": "REVIEW_CONCEPT"}

    res1 = client.post("/api/teacher/students/S001/actions", json=payload)
    assert res1.status_code == 200
    res2 = client.post("/api/teacher/students/S001/actions", json=payload)
    assert res2.status_code == 200

    # 相同的 action_id
    assert res1.json()["action_id"] == res2.json()["action_id"]
    # 底层仅追加 1 行
    lines = isolated_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1


def test_23_api_get_teacher_history_full_and_permanent(api_test_setup):
    """GET /api/teacher/students/{student_id}/actions: 返回包含 MARK_FOLLOWED 在内的全量永久历史"""
    client, repo, _ = api_test_setup
    base_t = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    repo.record_action("S001", "K01", "MARK_FOLLOWED", now=base_t)
    repo.record_action("S001", "K02", "REVIEW_CONCEPT", now=base_t + timedelta(days=5))
    repo.record_action("S001", "K03", "RETRY_PRACTICE", now=base_t + timedelta(days=10))

    res = client.get("/api/teacher/students/S001/actions")
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "S001"
    assert data["total_count"] == 3
    assert len(data["actions"]) == 3
    assert data["actions"][0]["knowledge_id"] == "K03"  # 最新在前
    assert data["actions"][2]["knowledge_id"] == "K01"  # MARK_FOLLOWED 完整保留
    assert data["actions"][2]["action_type"] == "MARK_FOLLOWED"
    assert data["actions"][2]["knowledge_name"] == CONCEPT_CARDS["K01"].knowledge_name


def test_24_api_get_teacher_history_404_invalid_student(api_test_setup):
    """GET 教师历史针对不存在的学生返回 404"""
    client, _, _ = api_test_setup
    res = client.get("/api/teacher/students/S999/actions")
    assert res.status_code == 404
    assert "找不到指定学生" in res.json()["detail"]


def test_25_api_get_student_recommendations_pipeline(api_test_setup):
    """
    GET /api/students/{student_id}/teacher-actions:
    严格验证读取管道规则：
    1. 7天外 (8天前) 过滤；
    2. MARK_FOLLOWED 过滤且不冲销先前建议；
    3. 同一考点最新去重；
    4. created_at DESC；
    5. 最多 3 条。
    """
    client, repo, _ = api_test_setup
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)

    # 8天前 (超期): K01 REVIEW_CONCEPT
    repo.record_action("S001", "K01", "REVIEW_CONCEPT", now=now - timedelta(days=8))
    # 5天前: K02 REVIEW_CONCEPT
    repo.record_action("S001", "K02", "REVIEW_CONCEPT", now=now - timedelta(days=5))
    # 4天前: K03 RETRY_PRACTICE
    repo.record_action("S001", "K03", "RETRY_PRACTICE", now=now - timedelta(days=4))
    # 3天前: K04 REVIEW_CONCEPT
    repo.record_action("S001", "K04", "REVIEW_CONCEPT", now=now - timedelta(days=3))
    # 2天前: K05 RETRY_PRACTICE
    repo.record_action("S001", "K05", "RETRY_PRACTICE", now=now - timedelta(days=2))
    # 1天前: K02 MARK_FOLLOWED (关注记录，不覆盖5天前的建议)
    repo.record_action("S001", "K02", "MARK_FOLLOWED", now=now - timedelta(days=1))
    # 12小时前: K03 REVIEW_CONCEPT (同一考点去重覆盖，K03变为 REVIEW_CONCEPT)
    repo.record_action("S001", "K03", "REVIEW_CONCEPT", now=now - timedelta(hours=12))

    res = client.get("/api/students/S001/teacher-actions")
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "S001"
    # 有效考点为 K03 (12h), K05 (2d), K04 (3d), K02 (5d)，按数量截断上限最多 3 条
    assert data["total_count"] == 3
    recs = data["recommendations"]
    assert len(recs) == 3

    # 验证按时间倒序截取的 3 条是 K03, K05, K04
    assert [r["knowledge_id"] for r in recs] == ["K03", "K05", "K04"]
    # 验证 K03 聚合为最新的 REVIEW_CONCEPT
    assert recs[0]["action_type"] == "REVIEW_CONCEPT"
    # 验证全部都有 dynamic knowledge_name
    for r in recs:
        assert r["knowledge_name"] == CONCEPT_CARDS[r["knowledge_id"]].knowledge_name


def test_26_api_get_student_recommendations_404_invalid_student(api_test_setup):
    """GET 学生端建议针对不存在的学生返回 404"""
    client, _, _ = api_test_setup
    res = client.get("/api/students/S999/teacher-actions")
    assert res.status_code == 404
    assert "找不到指定学生" in res.json()["detail"]


def test_27_api_zero_mutation_and_data_isolation(api_test_setup):
    """
    通过 API 调用完整链路，严格验证：
    1. 生产 data/teacher_actions.jsonl 零触碰；
    2. data/learning_events.jsonl 零增长；
    3. data/bkt_states.json 绝对 0 变更；
    4. data/learning_path_states.json 绝对 0 变更。
    """
    client, _, isolated_file = api_test_setup
    learning_events_file = settings.DATA_DIR / "learning_events.jsonl"
    bkt_file = settings.DATA_DIR / "bkt_states.json"
    path_file = settings.DATA_DIR / "learning_path_states.json"
    prod_teacher_actions = DEFAULT_TEACHER_ACTIONS_FILE

    prod_exists_before = prod_teacher_actions.exists()
    prod_size_before = prod_teacher_actions.stat().st_size if prod_exists_before else 0
    le_before = learning_events_file.read_bytes() if learning_events_file.exists() else b""
    bkt_before = bkt_file.read_bytes() if bkt_file.exists() else b""
    path_before = path_file.read_bytes() if path_file.exists() else b""

    # 发起多个 API 调用
    client.post("/api/teacher/students/S001/actions", json={"knowledge_id": "K02", "action_type": "REVIEW_CONCEPT"})
    client.post("/api/teacher/students/S001/actions", json={"knowledge_id": "K03", "action_type": "RETRY_PRACTICE"})
    client.post("/api/teacher/students/S001/actions", json={"knowledge_id": "K02", "action_type": "MARK_FOLLOWED"})
    client.get("/api/teacher/students/S001/actions")
    client.get("/api/students/S001/teacher-actions")

    # 验证生产文件完全未受触碰
    if not prod_exists_before:
        assert not prod_teacher_actions.exists(), "测试绝对不能在生产目录创建 teacher_actions.jsonl"
    else:
        assert prod_teacher_actions.stat().st_size == prod_size_before

    le_after = learning_events_file.read_bytes() if learning_events_file.exists() else b""
    bkt_after = bkt_file.read_bytes() if bkt_file.exists() else b""
    path_after = path_file.read_bytes() if path_file.exists() else b""

    assert le_before == le_after, "API 绝对不能写入 learning_events.jsonl！"
    assert bkt_before == bkt_after, "API 绝对不能修改 bkt_states.json！"
    assert path_before == path_after, "API 绝对不能修改 learning_path_states.json！"

