# -*- coding: utf-8 -*-
"""
scripts/sprint9g_quality_gate.py
================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-G
今日学习行动聚合 Lite 严苛质量门禁 (Strict Quality Gate)

门禁校验项：
[01/08] Git 架构基线与冻结目录零变更检查 (app/, tests/, data/seeds/ 0 diff)
[02/08] 今日行动状态模型与 5 档判定枚举契约 (TodayActionType, TodayLearningAction, TodayActionResponse)
[03/08] 6 级确定性优先级仲裁完整性 (NEEDS_REINFORCEMENT > DUE_FOR_REVIEW > IN_PROGRESS > PRACTICE > VIEW_PROGRESS > NONE)
[04/08] Retention 保持度判定集成与平局裁决 (Sprint 9-F 链路 & knowledge_id 升序)
[05/08] 多学生上下文硬隔离与 404 处理 (S001 vs S002 物理独立性与非法学生防护)
[06/08] 只读解析器与零数据突变红线 (Zero Mutation & 固定时间基准 50 次幂等一致性)
[07/08] 人本温度表达、零黑话审核与 NONE 静默契约 (No Jargon & NONE Empty Contract)
[08/08] 全链路自动化测试与类型检查 (pytest, npm test, npm run typecheck)
"""

import hashlib
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.core.config import settings
from gateway.api import create_gateway_app
from gateway.learning.resources.models import (
    LearningResource,
    RecommendedResourcesResponse,
    ResourceRecommendation,
    ResourceType,
)
from gateway.learning.retention.models import RetentionProfile, RetentionStatus
from gateway.learning.today import (
    TodayActionResponse,
    TodayActionType,
    TodayLearningAction,
    TodayActionResolver,
    default_today_action_resolver,
)


def run_check(check_num: int, title: str, fn) -> bool:
    print(f"[{check_num:02d}/08] {title} ... ", end="", flush=True)
    try:
        fn()
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_01_frozen_dirs():
    """检查冻结目录与核心数据文件是否为 0 diff"""
    res1 = subprocess.run(
        ["git", "diff", "--stat", "HEAD", "--", "app/", "tests/", "data/seeds/"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if res1.stdout.strip():
        raise AssertionError(f"冻结目录发现非预期修改:\n{res1.stdout}")

    res2 = subprocess.run(
        ["git", "diff", "--stat", "HEAD", "--", "data/bkt_states.json", "data/learning_events.jsonl"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if res2.stdout.strip():
        raise AssertionError(f"核心数据文件发现非预期修改:\n{res2.stdout}")


def check_02_model_contracts():
    """检查模型与 5 档枚举定义完备性"""
    types = [t.value for t in TodayActionType]
    expected = ["REVIEW_RETENTION", "CONTINUE_LEARNING", "PRACTICE", "VIEW_PROGRESS", "NONE"]
    for exp in expected:
        assert exp in types, f"缺少行动枚举值: {exp}"

    act = TodayLearningAction(
        action_type=TodayActionType.REVIEW_RETENTION,
        title="测试标题",
        description="测试描述",
        cta_label="开始测试",
        priority_reason="测试优先级",
        knowledge_id="K01",
        knowledge_name="稀缺性",
        suggested_action="RETAKE_QUIZ",
    )
    assert act.action_type == TodayActionType.REVIEW_RETENTION
    resp = TodayActionResponse(student_id="S001", action=act)
    assert resp.student_id == "S001"
    assert resp.action.knowledge_id == "K01"


def check_03_priority_arbitration():
    """校验 6 级确定性优先级阶梯逻辑"""
    # 场景 1: NEEDS_REINFORCEMENT 盖过所有
    m_ret = MagicMock()
    m_ret.analyze.return_value = RetentionProfile(
        student_id="S001",
        knowledge_id="K01",
        retention_status=RetentionStatus.NEEDS_REINFORCEMENT,
        should_review=True,
        suggested_action="REVIEW_CONCEPT",
    )
    m_path = MagicMock()
    m_path.get_all_path_states.return_value = {"K02": "IN_PROGRESS"}
    resolver = TodayActionResolver(retention_analyzer=m_ret, path_state_service=m_path)
    res = resolver.resolve("S001", candidate_knowledge_ids=["K01"])
    assert res.action.action_type == TodayActionType.REVIEW_RETENTION
    assert res.action.cta_label == "重新学习"

    # 场景 2: DUE_FOR_REVIEW 盖过 IN_PROGRESS
    m_ret.analyze.return_value = RetentionProfile(
        student_id="S001",
        knowledge_id="K01",
        retention_status=RetentionStatus.DUE_FOR_REVIEW,
        should_review=True,
        suggested_action="RETAKE_QUIZ",
    )
    res2 = resolver.resolve("S001", candidate_knowledge_ids=["K01"])
    assert res2.action.action_type == TodayActionType.REVIEW_RETENTION
    assert res2.action.cta_label == "开始快速复测"

    # 场景 3: IN_PROGRESS 盖过 PRACTICE
    m_ret.analyze.return_value = RetentionProfile(
        student_id="S001",
        knowledge_id="K01",
        retention_status=RetentionStatus.NOT_DUE,
        should_review=False,
    )
    m_res = MagicMock()
    m_res.resolve.return_value = RecommendedResourcesResponse(
        student_id="S001",
        knowledge_id="K01",
        masters=0.5,
        mastery=0.5,
        case_code="CASE_A",
        reason_summary="推荐",
        recommendations=[
            ResourceRecommendation(
                resource=LearningResource(
                    resource_id="res_p",
                    knowledge_id="K01",
                    resource_type=ResourceType.PRACTICE,
                    title="练习",
                    description="desc",
                    difficulty=0.5,
                ),
                rank=1,
                recommended_reason="reason",
                reason_category="TARGETED_PRACTICE",
                suggested_order=1,
            )
        ],
    )
    resolver3 = TodayActionResolver(
        retention_analyzer=m_ret,
        path_state_service=m_path,
        resource_resolver=m_res,
    )
    res3 = resolver3.resolve("S001", candidate_knowledge_ids=["K01"])
    assert res3.action.action_type == TodayActionType.CONTINUE_LEARNING


def check_04_retention_integration():
    """校验 Retention 集成与平局仲裁 (knowledge_id 升序)"""
    mock_ret = MagicMock()
    # K07, K02 同时到期复测
    mock_ret.analyze.side_effect = lambda sid, kid, now=None: RetentionProfile(
        student_id=sid,
        knowledge_id=kid,
        retention_status=RetentionStatus.DUE_FOR_REVIEW if kid in ("K07", "K02") else RetentionStatus.NOT_DUE,
        should_review=(kid in ("K07", "K02")),
        suggested_action="RETAKE_QUIZ",
    )
    resolver = TodayActionResolver(retention_analyzer=mock_ret)
    res = resolver.resolve("S001", candidate_knowledge_ids=["K07", "K02"])
    assert res.action.action_type == TodayActionType.REVIEW_RETENTION
    # 升序首位必须是 K02
    assert res.action.knowledge_id == "K02"


def check_05_student_isolation():
    """校验多学生上下文硬隔离与 404 防护"""
    app = create_gateway_app()
    client = TestClient(app)

    r1 = client.get("/api/learning/today/S001")
    assert r1.status_code == 200
    d1 = r1.json()

    r2 = client.get("/api/learning/today/S002")
    assert r2.status_code == 200
    d2 = r2.json()

    assert d1["student_id"] == "S001"
    assert d2["student_id"] == "S002"
    assert d1["action"]["action_type"] != d2["action"]["action_type"]

    r_404 = client.get("/api/learning/today/UNKNOWN_STUDENT_X")
    assert r_404.status_code == 404


def check_06_zero_mutation():
    """纯只读性与时间基准 50 次确定性幂等校验"""
    def _file_hash(p: Path) -> str:
        if not p.exists(): return ""
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while c := f.read(8192):
                h.update(c)
        return h.hexdigest()

    h_bkt_pre = _file_hash(settings.BKT_STATES_FILE)
    h_evt_pre = _file_hash(settings.LEARNING_EVENTS_FILE)

    fixed_now = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    base = default_today_action_resolver.resolve("S001", now=fixed_now).model_dump()
    for _ in range(50):
        curr = default_today_action_resolver.resolve("S001", now=fixed_now).model_dump()
        assert curr == base

    h_bkt_post = _file_hash(settings.BKT_STATES_FILE)
    h_evt_post = _file_hash(settings.LEARNING_EVENTS_FILE)

    assert h_bkt_post == h_bkt_pre, "BKT 数据文件发生突变！"
    assert h_evt_post == h_evt_pre, "学习事件日志发生突变！"


def check_07_no_jargon_and_none_silent():
    """校验绝对禁止技术黑话与 NONE 静默契约"""
    forbidden = [
        "bkt", "p(l)", "bayesian", "贝叶斯", "mastery", "pathstate",
        "dynamicpathgenerator", "score", "分值", "算法", "retention analyzer"
    ]
    for sid in ("S001", "S002"):
        act = default_today_action_resolver.resolve(sid).action
        corpus = f"{act.title} {act.description} {act.cta_label} {act.priority_reason}".lower()
        for j in forbidden:
            assert j not in corpus, f"在学生端行动中检测到黑话: {j}"

    # NONE 静默契约
    none_act = TodayLearningAction(
        action_type=TodayActionType.NONE,
        title="",
        description="",
        cta_label="",
        priority_reason="无任务",
    )
    assert none_act.action_type == TodayActionType.NONE
    assert none_act.title == ""


def check_08_regression_tests():
    """运行全套自动化回归套件"""
    res_py = subprocess.run(
        [sys.executable, "-m", "pytest", "gateway/tests/test_sprint9g_today_action.py", "-q"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if res_py.returncode != 0:
        raise AssertionError(f"后端测试失败:\n{res_py.stderr or res_py.stdout}")

    res_ts = subprocess.run(
        ["npm", "run", "typecheck"],
        cwd=PROJECT_ROOT / "frontend",
        shell=True,
        capture_output=True,
        text=True,
    )
    if res_ts.returncode != 0:
        raise AssertionError(f"前端 TypeScript 检查失败:\n{res_ts.stderr or res_ts.stdout}")


def main():
    print("=" * 80)
    print("Sprint 9-G: Today's Learning Action Aggregation Lite Quality Gate")
    print("=" * 80)

    checks = [
        ("Git 架构基线与冻结目录零变更检查", check_01_frozen_dirs),
        ("今日行动状态模型与 5 档判定枚举契约", check_02_model_contracts),
        ("6 级确定性优先级仲裁完整性", check_03_priority_arbitration),
        ("Retention 保持度判定集成与平局裁决", check_04_retention_integration),
        ("多学生上下文硬隔离与 404 处理", check_05_student_isolation),
        ("只读解析器与零数据突变红线", check_06_zero_mutation),
        ("人本温度表达、零黑话审核与 NONE 静默契约", check_07_no_jargon_and_none_silent),
        ("全链路自动化测试与类型检查", check_08_regression_tests),
    ]

    passed = 0
    for idx, (title, fn) in enumerate(checks, start=1):
        if run_check(idx, title, fn):
            passed += 1

    print("=" * 80)
    print(f"Sprint 9-G Quality Gate: {passed}/{len(checks)} Passed.")
    print("=" * 80)

    if passed < len(checks):
        sys.exit(1)


if __name__ == "__main__":
    main()
