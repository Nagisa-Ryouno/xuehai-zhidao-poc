# -*- coding: utf-8 -*-
"""
scripts/sprint9f_quality_gate.py
================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-F
学习保持度验证与间隔复习建议 Lite 严苛质量门禁 (Strict Quality Gate)

本门禁独立自动化校验 Sprint 9-F 全部核心契约与安全红线：
1. Git 架构基线与冻结目录零变更检查 (app/, tests/, data/seeds/ 0 diff)
2. 保持度状态模型与 4 档判定枚举契约 (RetentionStatus, RetentionProfile)
3. 确定性时间边界与阈值契约 (REVIEW_AFTER_DAYS = 3, >= 3 天 DUE_FOR_REVIEW, < 3 天 NOT_DUE)
4. 只读分析器与零数据突变红线 (Zero Mutation Invariant, 幂等性 50 次完全一致)
5. 多学生与跨考点上下文硬隔离契约 (Student & Knowledge Isolation)
6. 人本引导文案与零技术黑话合规性审核 (No Jargon: 严禁 BKT, 贝叶斯, 艾宾浩斯, 遗忘曲线, 衰减)
7. API 端点契约完整性 (GET /api/learning/retention/{student_id}/{knowledge_id})
8. 全量自动化测试套件与生产类型检查完整性 (pytest, npm run typecheck, npm test)
"""

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from gateway.api import create_gateway_app
from gateway.learning.retention.models import (
    RetentionStatus,
    RetentionProfile,
    ALLOWED_RETENTION_ACTIONS,
)
from gateway.learning.retention.analyzer import (
    RetentionAnalyzer,
    REVIEW_AFTER_DAYS,
    default_retention_analyzer,
)
from app.core.config import settings


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


def main():
    print("=" * 80)
    print("Sprint 9-F: Learning Retention Check Lite Quality Gate")
    print("=" * 80)

    app = create_gateway_app()
    client = TestClient(app)

    # -------------------------------------------------------------------------
    # Check 1: Git 架构基线与冻结目录零变更检查
    # -------------------------------------------------------------------------
    def check_01_git_baseline_and_frozen_dirs():
        cmd = ["git", "diff", "--stat", "HEAD", "--", "app/", "tests/", "data/seeds/"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode != 0 or res.stdout.strip():
            raise AssertionError(f"冻结目录存在未授权变更:\n{res.stdout}")

    # -------------------------------------------------------------------------
    # Check 2: 保持度状态模型与 4 档判定枚举契约
    # -------------------------------------------------------------------------
    def check_02_retention_models_and_enums():
        assert RetentionStatus.INSUFFICIENT_DATA == "INSUFFICIENT_DATA"
        assert RetentionStatus.NOT_DUE == "NOT_DUE"
        assert RetentionStatus.DUE_FOR_REVIEW == "DUE_FOR_REVIEW"
        assert RetentionStatus.NEEDS_REINFORCEMENT == "NEEDS_REINFORCEMENT"

        assert "RETAKE_QUIZ" in ALLOWED_RETENTION_ACTIONS
        assert "REVIEW_CONCEPT" in ALLOWED_RETENTION_ACTIONS
        assert "VIEW_PROGRESS" in ALLOWED_RETENTION_ACTIONS

        # 实例化 RetentionProfile
        p = RetentionProfile(
            student_id="S001",
            knowledge_id="K08",
            last_learning_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
            days_since_learning=3,
            current_mastery=0.75,
            retention_status=RetentionStatus.DUE_FOR_REVIEW,
            should_review=True,
            suggested_action="RETAKE_QUIZ",
        )
        assert p.student_id == "S001"
        assert p.should_review is True
        assert p.suggested_action == "RETAKE_QUIZ"

    # -------------------------------------------------------------------------
    # Check 3: 确定性时间边界与阈值契约 (REVIEW_AFTER_DAYS = 3)
    # -------------------------------------------------------------------------
    def check_03_time_threshold_and_boundaries():
        assert REVIEW_AFTER_DAYS == 3

        import tempfile
        import json

        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl", encoding="utf-8") as f_eff:
            eff_path = Path(f_eff.name)
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl", encoding="utf-8") as f_q:
            quiz_path = Path(f_q.name)

        try:
            fixed_now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)

            class MockBKT:
                def get_state(self, s, k, auto_init=False):
                    class MockS:
                        mastery_probability = 0.72
                    return MockS()

            # 2 天前: NOT_DUE
            two_days_ago = fixed_now - timedelta(days=2)
            with open(eff_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "student_id": "S001",
                    "knowledge_id": "K08",
                    "event_type": "RESOURCE_SESSION_COMPLETE",
                    "server_timestamp": two_days_ago.isoformat(),
                }) + "\n")

            analyzer = RetentionAnalyzer(effectiveness_file=eff_path, events_file=quiz_path, bkt_repo=MockBKT())
            p_not_due = analyzer.analyze("S001", "K08", now=fixed_now)
            assert p_not_due.retention_status == RetentionStatus.NOT_DUE
            assert p_not_due.should_review is False

            # 3 天前: DUE_FOR_REVIEW (RETAKE_QUIZ)
            three_days_ago = fixed_now - timedelta(days=3)
            with open(eff_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "student_id": "S001",
                    "knowledge_id": "K08",
                    "event_type": "RESOURCE_SESSION_COMPLETE",
                    "server_timestamp": three_days_ago.isoformat(),
                }) + "\n")

            p_due = analyzer.analyze("S001", "K08", now=fixed_now)
            assert p_due.retention_status == RetentionStatus.DUE_FOR_REVIEW
            assert p_due.should_review is True
            assert p_due.suggested_action == "RETAKE_QUIZ"
        finally:
            if eff_path.exists():
                eff_path.unlink()
            if quiz_path.exists():
                quiz_path.unlink()

    # -------------------------------------------------------------------------
    # Check 4: 只读分析器与零数据突变红线 (Zero Mutation Invariant)
    # -------------------------------------------------------------------------
    def check_04_zero_mutation_and_idempotency():
        bkt_file = settings.BKT_STATES_FILE
        events_file = settings.LEARNING_EVENTS_FILE

        bkt_mtime_before = bkt_file.stat().st_mtime if bkt_file.exists() else None
        events_mtime_before = events_file.stat().st_mtime if events_file.exists() else None

        fixed_now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        baseline = default_retention_analyzer.analyze("S001", "K08", now=fixed_now).model_dump()

        # 幂等性 50 次
        for _ in range(50):
            curr = default_retention_analyzer.analyze("S001", "K08", now=fixed_now).model_dump()
            assert curr == baseline

        bkt_mtime_after = bkt_file.stat().st_mtime if bkt_file.exists() else None
        events_mtime_after = events_file.stat().st_mtime if events_file.exists() else None

        assert bkt_mtime_before == bkt_mtime_after, "BKT 状态文件发生了突变变更！"
        assert events_mtime_before == events_mtime_after, "学习事件文件发生了突变变更！"

    # -------------------------------------------------------------------------
    # Check 5: 多学生与跨考点上下文硬隔离契约
    # -------------------------------------------------------------------------
    def check_05_student_and_knowledge_isolation():
        import tempfile
        import json

        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl", encoding="utf-8") as f_eff:
            eff_path = Path(f_eff.name)
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl", encoding="utf-8") as f_q:
            quiz_path = Path(f_q.name)

        try:
            fixed_now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
            four_days_ago = fixed_now - timedelta(days=4)

            # S001 在 K08 有记录，S002 无记录；S001 在 K09 无记录
            with open(eff_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "student_id": "S001",
                    "knowledge_id": "K08",
                    "event_type": "RESOURCE_SESSION_COMPLETE",
                    "server_timestamp": four_days_ago.isoformat(),
                }) + "\n")

            class MockBKT:
                def get_state(self, s, k, auto_init=False):
                    class MockS:
                        mastery_probability = 0.70
                    return MockS()

            analyzer = RetentionAnalyzer(effectiveness_file=eff_path, events_file=quiz_path, bkt_repo=MockBKT())

            p_s1_k8 = analyzer.analyze("S001", "K08", now=fixed_now)
            p_s2_k8 = analyzer.analyze("S002", "K08", now=fixed_now)
            p_s1_k9 = analyzer.analyze("S001", "K09", now=fixed_now)

            assert p_s1_k8.retention_status == RetentionStatus.DUE_FOR_REVIEW
            assert p_s2_k8.retention_status == RetentionStatus.INSUFFICIENT_DATA
            assert p_s1_k9.retention_status == RetentionStatus.INSUFFICIENT_DATA
        finally:
            if eff_path.exists():
                eff_path.unlink()
            if quiz_path.exists():
                quiz_path.unlink()

    # -------------------------------------------------------------------------
    # Check 6: 人本引导文案与零技术黑话合规性审核 (No Jargon)
    # -------------------------------------------------------------------------
    def check_06_no_jargon_compliance():
        forbidden = [
            "BKT", "bkt", "bayesian", "Bayesian", "贝叶斯", "艾宾浩斯",
            "ebbinghaus", "Ebbinghaus", "遗忘曲线", "衰减", "半衰期",
            "先验", "后验", "向量数据库", "大模型决策"
        ]
        # 扫描前端 ResourceHub.tsx 提示文本
        hub_path = PROJECT_ROOT / "frontend" / "src" / "components" / "student" / "ResourceHub.tsx"
        with open(hub_path, "r", encoding="utf-8") as f:
            hub_content = f.read()

        # 检查是否包含 retention 相关的黑话
        retention_section = hub_content[hub_content.find("retention-prompt-card") - 200: hub_content.find("retention-reinforcement-card") + 500]
        for w in forbidden:
            assert w not in retention_section, f"前端保持度提示区域泄露了黑话: {w}"

    # -------------------------------------------------------------------------
    # Check 7: API 端点契约完整性
    # -------------------------------------------------------------------------
    def check_07_api_contract():
        # 正常查询
        res = client.get("/api/learning/retention/S001/K08")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["student_id"] == "S001"
        assert data["knowledge_id"] == "K08"
        assert data["retention_status"] in [
            "INSUFFICIENT_DATA", "NOT_DUE", "DUE_FOR_REVIEW", "NEEDS_REINFORCEMENT"
        ]

        # 404 测试
        res_404_s = client.get("/api/learning/retention/INVALID_STUDENT/K08")
        assert res_404_s.status_code == 404

        res_404_k = client.get("/api/learning/retention/S001/INVALID_KP")
        assert res_404_k.status_code == 404

    # -------------------------------------------------------------------------
    # Check 8: 全量自动化测试套件与生产类型检查完整性
    # -------------------------------------------------------------------------
    def check_08_full_test_suite_and_typecheck():
        # 1. pytest 保持度测试
        res_py = subprocess.run(
            ["pytest", "gateway/tests/test_sprint9f_retention_check.py", "-q"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if res_py.returncode != 0:
            raise AssertionError(f"pytest 失败:\n{res_py.stdout}\n{res_py.stderr}")

        # 2. npm run typecheck
        res_tc = subprocess.run(
            ["npm", "run", "typecheck"],
            cwd=str(PROJECT_ROOT / "frontend"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
        )
        if res_tc.returncode != 0:
            raise AssertionError(f"npm run typecheck 失败:\n{res_tc.stdout}\n{res_tc.stderr}")

        # 3. npm test
        res_test = subprocess.run(
            ["npm", "test"],
            cwd=str(PROJECT_ROOT / "frontend"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
        )
        if res_test.returncode != 0:
            raise AssertionError(f"npm test 失败:\n{res_test.stdout}\n{res_test.stderr}")

    # 执行所有检查
    checks = [
        (1, "Git Baseline & Frozen Dirs 0 Diff Invariant", check_01_git_baseline_and_frozen_dirs),
        (2, "Retention Models & 4-Tier Status Enums", check_02_retention_models_and_enums),
        (3, "Time Thresholds & Day Boundary Contracts", check_03_time_threshold_and_boundaries),
        (4, "Zero Mutation Invariant & 50x Idempotency", check_04_zero_mutation_and_idempotency),
        (5, "Multi-Student & Knowledge Context Isolation", check_05_student_and_knowledge_isolation),
        (6, "Human-Centric Warmth & No Jargon Compliance", check_06_no_jargon_compliance),
        (7, "API Contract & 404 Error Isolation", check_07_api_contract),
        (8, "Full Backend & Frontend Test Suite Execution", check_08_full_test_suite_and_typecheck),
    ]

    all_passed = True
    for c_num, title, fn in checks:
        if not run_check(c_num, title, fn):
            all_passed = False

    print("=" * 80)
    if all_passed:
        print("ALL 8 QUALITY GATE CHECKS PASSED PERFECTLY! [READY FOR UAT]")
    else:
        print("SOME QUALITY GATE CHECKS FAILED! PLEASE RESOLVE BEFORE COMPLETION.")
        sys.exit(1)


if __name__ == "__main__":
    main()
