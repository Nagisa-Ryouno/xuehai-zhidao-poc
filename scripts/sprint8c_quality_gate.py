# -*- coding: utf-8 -*-
"""
scripts/sprint8c_quality_gate.py
Sprint 8-C: 学习成效沉淀、错题复盘与教师分析驾驶舱 Quality Gate (10 项自动化质检验收)
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from gateway.api import app
from gateway.learning.analytics.service import default_analytics_service, AnalyticsService
from gateway.learning.analytics.models import StudentProgressResponse, WrongAnswerReviewResponse
from app.core.constants import MASTERY_THRESHOLD_HIGH, MASTERY_THRESHOLD_LOW
from app.infrastructure.persistence.event_repository import EventRepository
from app.infrastructure.persistence.bkt_state_repository import BKTStateRepository
from app.domain.bkt.models import BKTState


def run_check(check_num: int, title: str, fn) -> bool:
    print(f"[{check_num:02d}/10] {title} ... ", end="", flush=True)
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
    print("=" * 75)
    print("Sprint 8-C: 学习成效沉淀与教师驾驶舱 Quality Gate (10 Checks)")
    print("=" * 75)

    client = TestClient(app)
    results = []

    # -------------------------------------------------------------
    # Check 1: Progress Aggregation (真实掌握度与30考点全景)
    # -------------------------------------------------------------
    def check_1():
        resp = client.get("/api/students/S001/progress")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["student_id"] == "S001"
        assert len(data["knowledge_point_masteries"]) == 30
        assert data["total_knowledge_points"] == 30
        assert 0.0 <= data["overall_mastery"] <= 1.0
        assert data["mastered_count"] + data["developing_count"] + data["reinforcement_count"] + data["unstudied_count"] == 30
    results.append(run_check(1, "Progress Aggregation (30 考点覆盖与掌握度守恒)", check_1))

    # -------------------------------------------------------------
    # Check 2: Mastery Consistency (单一掌握度标准，严格遵循 0.80)
    # -------------------------------------------------------------
    def check_2():
        svc = default_analytics_service
        # 验证阈值语义
        assert MASTERY_THRESHOLD_HIGH == 0.80
        assert MASTERY_THRESHOLD_LOW == 0.60

        prog = svc.get_student_progress("S001")
        assert prog is not None
        # 总体掌握度必须与 30 考点当前掌握度均值一致
        mean_mastery = sum(kp.mastery for kp in prog.knowledge_point_masteries) / 30.0
        assert abs(prog.overall_mastery - round(mean_mastery, 4)) < 0.001
        for kp in prog.knowledge_point_masteries:
            if kp.mastery >= 0.80:
                assert kp.state == "MASTERED"
    results.append(run_check(2, "Mastery Consistency (严格统一 0.80 阈值与均值守恒)", check_2))

    # -------------------------------------------------------------
    # Check 3: Wrong Answer Aggregation & Remediation Targets
    # -------------------------------------------------------------
    def check_3():
        resp = client.get("/api/students/S001/wrong-answers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["student_id"] == "S001"
        assert "total_wrong" in data
        assert isinstance(data["wrong_answers"], list)
        for w in data["wrong_answers"]:
            assert w["student_answer"] != w["correct_answer"]
            assert w["review_priority"] in ["HIGH", "MEDIUM", "LOW"]
            assert w["knowledge_id"].startswith("K")
            assert len(w["explanation"]) > 0
    results.append(run_check(3, "Wrong Answer Aggregation (纯真实错误提取与解析完备)", check_3))

    # -------------------------------------------------------------
    # Check 4: Empty History & New Student Zero Fake Data
    # -------------------------------------------------------------
    def check_4():
        with tempfile.TemporaryDirectory() as td:
            empty_events = Path(td) / "empty_events.jsonl"
            empty_bkt = Path(td) / "empty_bkt.json"
            empty_path = Path(td) / "empty_path.json"
            svc = AnalyticsService()
            prog = svc.get_student_progress(
                "S001",
                events_file=empty_events,
                bkt_file=empty_bkt,
                path_file=empty_path,
            )
            assert prog is not None
            assert prog.total_practice_count == 0
            assert prog.overall_accuracy == 0.0
            assert len(prog.mastery_trend) == 0
            assert len(prog.history_timeline) == 0

            wrongs = svc.get_student_wrong_answers(
                "S001",
                events_file=empty_events,
                bkt_file=empty_bkt,
                path_file=empty_path,
            )
            assert wrongs.total_wrong == 0
            assert len(wrongs.wrong_answers) == 0
    results.append(run_check(4, "Empty History Graceful Handling (零假数据与空状态规范)", check_4))

    # -------------------------------------------------------------
    # Check 5: Student Data Isolation (S001 vs S002 严格物理隔离)
    # -------------------------------------------------------------
    def check_5():
        p1 = client.get("/api/students/S001/progress").json()
        p2 = client.get("/api/students/S002/progress").json()
        assert p1["student_id"] == "S001"
        assert p2["student_id"] == "S002"

        w1 = client.get("/api/students/S001/wrong-answers").json()
        w2 = client.get("/api/students/S002/wrong-answers").json()
        assert w1["student_id"] == "S001"
        assert w2["student_id"] == "S002"
    results.append(run_check(5, "Student Data Isolation (学生学情与错题严格隔离)", check_5))

    # -------------------------------------------------------------
    # Check 6: Teacher Overview Aggregation (班级 KPI 真实聚合)
    # -------------------------------------------------------------
    def check_6():
        resp = client.get("/api/teacher/overview")
        assert resp.status_code == 200
        data = resp.json()
        kpis = data["class_kpis"]
        assert kpis["total_students"] >= 5
        assert kpis["active_students"] >= 0
        assert 0.0 <= kpis["class_avg_mastery"] <= 1.0
        assert kpis["at_risk_students_count"] >= 0
        assert len(data["students"]) >= 5
    results.append(run_check(6, "Teacher Overview Aggregation (班级全景统计 KPI 真实聚合)", check_6))

    # -------------------------------------------------------------
    # Check 7: Teacher Weak Knowledge Points (共性薄弱考点排行)
    # -------------------------------------------------------------
    def check_7():
        resp = client.get("/api/teacher/overview")
        data = resp.json()
        wps = data["weak_knowledge_points"]
        assert len(wps) <= 5
        for wp in wps:
            assert wp["knowledge_id"].startswith("K")
            assert wp["urgency"] in ["HIGH", "MEDIUM", "LOW"]
            assert 0.0 <= wp["avg_mastery"] <= 1.0
            assert 0.0 <= wp["error_rate"] <= 100.0
    results.append(run_check(7, "Teacher Weak Knowledge Points (Top-5 瓶颈考点排查)", check_7))

    # -------------------------------------------------------------
    # Check 8: Teacher Read-Only (教师端调阅绝不修改学生状态)
    # -------------------------------------------------------------
    def check_8():
        with tempfile.TemporaryDirectory() as td:
            bkt_f = Path(td) / "bkt_test.json"
            evt_f = Path(td) / "evt_test.jsonl"
            repo = BKTStateRepository()
            repo.save_state(BKTState(student_id="S001", knowledge_id="K01", mastery_probability=0.75, attempts=2), states_file=bkt_f)

            bkt_content_before = bkt_f.read_text(encoding="utf-8")
            svc = AnalyticsService()
            _ = svc.get_teacher_student_detail("S001", bkt_file=bkt_f, events_file=evt_f)
            bkt_content_after = bkt_f.read_text(encoding="utf-8")
            assert bkt_content_before == bkt_content_after, "Teacher detail MUST be strictly read-only!"
    results.append(run_check(8, "Teacher Read-Only Integrity (教师端调用严格只读)", check_8))

    # -------------------------------------------------------------
    # Check 9: Frozen Directories Integrity (app/, tests/, data/seeds/ 严格 0 diff)
    # -------------------------------------------------------------
    def check_9():
        proc = subprocess.run(
            ["git", "diff", "--stat", "--", "app/", "tests/", "data/seeds/"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        diff_out = proc.stdout.strip()
        assert diff_out == "", f"Frozen directories violated:\n{diff_out}"
    results.append(run_check(9, "Frozen Directories Integrity (app/ tests/ seeds/ 0 diff)", check_9))

    # -------------------------------------------------------------
    # Check 10: AI Judge Production Isolation (严禁 AI 参与生产决策)
    # -------------------------------------------------------------
    def check_10():
        from gateway.evaluation.judge.runtime import JudgeRuntimePolicy
        pol = JudgeRuntimePolicy()
        assert pol.allow_production_decision is False, "allow_production_decision must be False!"
    results.append(run_check(10, "AI Judge Production Isolation (AI 绝不参与生产决策)", check_10))

    print("=" * 75)
    passed_count = sum(1 for r in results if r)
    print(f"Sprint 8-C Quality Gate Result: {passed_count}/10 checks passed.")
    if passed_count == 10:
        print("ALL QUALITY GATE CHECKS PASSED SUCCESSFULLY!")
        return 0
    else:
        print("QUALITY GATE FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
