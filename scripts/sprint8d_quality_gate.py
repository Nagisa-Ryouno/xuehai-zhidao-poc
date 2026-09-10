# -*- coding: utf-8 -*-
"""
scripts/sprint8d_quality_gate.py
Sprint 8-D: Product Experience Hardening & End-to-End Acceptance Quality Gate
=============================================================================
10 项端到端产品化硬化与一致性全自动化质检验收
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
from app.core.constants import MASTERY_THRESHOLD_HIGH, MASTERY_THRESHOLD_LOW
from app.infrastructure.persistence.event_repository import EventRepository
from app.infrastructure.persistence.bkt_state_repository import BKTStateRepository
from app.domain.bkt.models import BKTState
from app.domain.event.models import LearningEventCreate, LearningEventType


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
    print("=" * 78)
    print("Sprint 8-D: Product Experience Hardening Quality Gate (10 Strict Checks)")
    print("=" * 78)

    client = TestClient(app)
    results = []

    # -------------------------------------------------------------
    # Check 1: Single Source of Truth & Cross-Role Consistency
    # -------------------------------------------------------------
    def check_1():
        # 学生端 /api/students/S001/progress vs 教师端 /api/teacher/students/S001
        res_stu = client.get("/api/students/S001/progress")
        assert res_stu.status_code == 200
        p_stu = res_stu.json()

        res_tch = client.get("/api/teacher/students/S001")
        assert res_tch.status_code == 200
        p_tch = res_tch.json()

        # 总体掌握度与做题量统计必须绝对一致
        assert abs(p_stu["overall_mastery"] - p_tch["overall_mastery"]) < 0.0001
        assert p_stu["total_practice_count"] == p_tch["total_attempts"]
        assert abs(p_stu["overall_accuracy"] - p_tch["accuracy"]) < 0.0001
        assert len(p_stu["knowledge_point_masteries"]) == len(p_tch["knowledge_point_masteries"]) == 30

        # 单考点逐一对比
        tch_map = {kp["knowledge_id"]: kp["mastery"] for kp in p_tch["knowledge_point_masteries"]}
        for kp in p_stu["knowledge_point_masteries"]:
            kid = kp["knowledge_id"]
            assert kid in tch_map
            assert abs(kp["mastery"] - tch_map[kid]) < 0.0001

        # 阈值规范一致性
        assert MASTERY_THRESHOLD_HIGH == 0.80
        assert MASTERY_THRESHOLD_LOW == 0.60
    results.append(run_check(1, "Single Source of Truth (学生与教师端掌握度严格守恒 |P_stu - P_tch| < 0.0001)", check_1))

    # -------------------------------------------------------------
    # Check 2: API Error Contracts (404/422 Graceful Recovery)
    # -------------------------------------------------------------
    def check_2():
        # 404 for unknown student
        r1 = client.get("/api/students/NON_EXISTENT_STUDENT_9999/progress")
        assert r1.status_code == 404
        assert "detail" in r1.json()

        r2 = client.get("/api/students/NON_EXISTENT_STUDENT_9999/wrong-answers")
        assert r2.status_code == 404

        r3 = client.get("/api/teacher/students/NON_EXISTENT_STUDENT_9999")
        assert r3.status_code == 404

        r4 = client.get("/api/quiz/K_NONEXISTENT_9999")
        assert r4.status_code == 404

        # 422 for malformed post body
        r5 = client.post("/api/students/init", json={"invalid_field": 123})
        assert r5.status_code == 422
    results.append(run_check(2, "API Error Contracts (404 未知资源 / 422 参数错误收敛规范)", check_2))

    # -------------------------------------------------------------
    # Check 3: Append-Only Event Log Invariant
    # -------------------------------------------------------------
    def check_3():
        with tempfile.TemporaryDirectory() as td:
            evt_file = Path(td) / "events.jsonl"
            repo = EventRepository()
            e1 = LearningEventCreate(
                event_id="evt-001",
                student_id="S_TEST",
                knowledge_id="K01",
                event_type="CONCEPT_VIEW",
                payload={},
                client_timestamp="2026-09-10T12:00:00Z",
            )
            e2 = LearningEventCreate(
                event_id="evt-002",
                student_id="S_TEST",
                knowledge_id="K01",
                event_type="QUESTION_ATTEMPT",
                payload={"is_correct": True},
                client_timestamp="2026-09-10T12:01:00Z",
            )
            repo.record_event(e1, target_file=evt_file)
            first_line = evt_file.read_text(encoding="utf-8").strip()
            assert "evt-001" in first_line

            repo.record_event(e2, target_file=evt_file)
            lines = [l.strip() for l in evt_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            assert len(lines) == 2
            assert lines[0] == first_line, "First event must never be modified or overwritten!"
            assert "evt-002" in lines[1]
    results.append(run_check(3, "Append-Only Event Log (事件日志物理只追加、绝不篡改历史)", check_3))

    # -------------------------------------------------------------
    # Check 4: Zero Fake Data on Empty State
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
    results.append(run_check(4, "Zero Fake Data on Empty State (新学生/空历史零假数据零硬编码)", check_4))

    # -------------------------------------------------------------
    # Check 5: Student Isolation & No Leakage
    # -------------------------------------------------------------
    # Check 5: Student Isolation & No Leakage
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

        r1 = client.get("/api/path/dynamic/S001").json()
        r2 = client.get("/api/path/dynamic/S002").json()
        assert r1["student_id"] == "S001"
        assert r2["student_id"] == "S002"
    results.append(run_check(5, "Student Data Isolation (学生认知状态严格物理隔离无跨上下文污染)", check_5))

    # -------------------------------------------------------------
    # Check 6: Teacher Read-Only Integrity
    # -------------------------------------------------------------
    def check_6():
        with tempfile.TemporaryDirectory() as td:
            bkt_f = Path(td) / "bkt.json"
            evt_f = Path(td) / "evt.jsonl"
            bkt_repo = BKTStateRepository()
            bkt_repo.save_state(BKTState(student_id="S001", knowledge_id="K01", mastery_probability=0.85, attempts=3), states_file=bkt_f)

            bkt_content_before = bkt_f.read_text(encoding="utf-8")
            svc = AnalyticsService()
            _ = svc.get_teacher_student_detail("S001", bkt_file=bkt_f, events_file=evt_f)
            bkt_content_after = bkt_f.read_text(encoding="utf-8")
            assert bkt_content_before == bkt_content_after, "Teacher inspection MUST have zero side effects on student data!"
    results.append(run_check(6, "Teacher Read-Only Integrity (教师端调用零写操作、零副作用)", check_6))

    # -------------------------------------------------------------
    # Check 7: Public Questions Desensitization
    # -------------------------------------------------------------
    def check_7():
        # 微测验题目脱敏
        r_quiz = client.get("/api/quiz/K01")
        assert r_quiz.status_code == 200
        data = r_quiz.json()
        q_list = data["questions"]
        assert len(q_list) > 0
        for q in q_list:
            assert "answer" not in q
            assert "explanation" not in q

        # 摸底测验题目脱敏
        r_pre = client.post("/api/diagnostic/pretest", json={"student_id": "S001", "goal": "微观经济学"})
        assert r_pre.status_code == 200
        pre_data = r_pre.json()
        pre_list = pre_data["questions"]
        assert len(pre_list) > 0
        for q in pre_list:
            assert "answer" not in q
            assert "explanation" not in q
    results.append(run_check(7, "Public Questions Desensitization (公开题库严格答案脱敏防泄露)", check_7))

    # -------------------------------------------------------------
    # Check 8: AI Judge Shadow Mode Invariant
    # -------------------------------------------------------------
    def check_8():
        from gateway.evaluation.judge.runtime import JudgeRuntimePolicy
        policy = JudgeRuntimePolicy()
        assert policy.allow_production_decision is False, "CRITICAL: AI Judge must never hold production decision authority!"
    results.append(run_check(8, "AI Judge Shadow Mode Invariant (AI 影子裁决生产决策严格关闭)", check_8))

    # -------------------------------------------------------------
    # Check 9: Frozen Directories Integrity (app/, tests/, data/seeds/ 0 diff)
    # -------------------------------------------------------------
    def check_9():
        proc = subprocess.run(
            ["git", "diff", "--stat", "HEAD", "--", "app/", "tests/", "data/seeds/"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        diff_out = proc.stdout.strip()
        assert diff_out == "", f"Frozen directories violated:\n{diff_out}"
    results.append(run_check(9, "Frozen Directories Integrity (app/ tests/ seeds/ 严格 0 diff)", check_9))

    # -------------------------------------------------------------
    # Check 10: Frontend TypeScript 0 Errors & Production Build
    # -------------------------------------------------------------
    def check_10():
        frontend_dir = PROJECT_ROOT / "frontend"
        proc = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
        )
        assert proc.returncode == 0, f"Frontend build failed:\n{proc.stdout}\n{proc.stderr}"
        assert (frontend_dir / "dist" / "index.html").exists(), "Frontend dist/index.html missing!"
    results.append(run_check(10, "Frontend Production Build (TypeScript 0 错误 + Vite 打包成功)", check_10))

    print("=" * 78)
    passed_count = sum(1 for r in results if r)
    print(f"Sprint 8-D Quality Gate Result: {passed_count}/10 checks passed.")
    if passed_count == 10:
        print("ALL QUALITY GATE CHECKS PASSED SUCCESSFULLY! (Verdict: GREEN)")
        return 0
    else:
        print("QUALITY GATE FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
