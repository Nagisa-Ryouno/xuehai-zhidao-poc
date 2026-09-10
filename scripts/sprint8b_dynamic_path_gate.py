# -*- coding: utf-8 -*-
"""
scripts/sprint8b_dynamic_path_gate.py
Sprint 8-B: 动态自适应路径与极速诊断质量门禁 (12 项自动化验收)
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from gateway.api import app
from gateway.learning.diagnostic import (
    clear_pretest_cache,
    create_pretest_session,
    evaluate_pretest,
    select_diagnostic_question_ids,
)
from gateway.learning.path_generation import (
    DynamicLearningRoute,
    DynamicPathGenerator,
    RouteStep,
    calculate_node_priority,
    default_dynamic_path_generator,
    WEIGHT_WEAKNESS,
    WEIGHT_TARGET_RELEVANCE,
    WEIGHT_PREREQUISITE_READINESS,
    WEIGHT_PATH_AVAILABILITY,
    WEIGHT_DIAGNOSTIC_PRIORITY,
)
from gateway.learning.graph import (
    apply_route_overlay_to_graph,
    get_route_graph_overlay,
)
from app.services.knowledge_graph_service import knowledge_graph_service
from app.infrastructure.persistence.event_repository import default_event_repository


def run_check(check_num: int, title: str, fn) -> bool:
    print(f"[{check_num:02d}/12] {title} ... ", end="", flush=True)
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
    print("=" * 70)
    print("Sprint 8-B: 动态自适应路径与极速诊断 Quality Gate (12 Checks)")
    print("=" * 70)

    clear_pretest_cache()
    client = TestClient(app)
    results = []

    # Check 1: 3-question deterministic pretest selection
    def check_1():
        q_ids = select_diagnostic_question_ids("弹性与税收")
        assert len(q_ids) == 3, f"Expected 3 questions, got {len(q_ids)}"
        assert q_ids == ["Q-K02-01", "Q-K04-01", "Q-K08-01"]
        # Repeat to ensure 100% determinism
        assert q_ids == select_diagnostic_question_ids("弹性与税收")
    results.append(run_check(1, "前测 3 题极速选题确定性与拓扑依赖保序", check_1))

    # Check 2: Public pretest questions sanitize answer & explanation
    def check_2():
        session = create_pretest_session("GATE_STU", "基础导论")
        assert len(session.questions) == 3
        for q in session.questions:
            dumped = q.model_dump()
            assert "answer" not in dumped, f"Question {q.question_id} leaked answer"
            assert "explanation" not in dumped, f"Question {q.question_id} leaked explanation"
            assert len(q.options) >= 2
    results.append(run_check(2, "前测公开模型严格剔除正确答案与解析脱敏", check_2))

    # Check 3: DiagnosticResult generated without formal BKT/Event mutation
    def check_3():
        session = create_pretest_session("GATE_STU_3", "导论")
        initial_events = default_event_repository.get_events_by_student("GATE_STU_3")
        res = evaluate_pretest(session.session_id, {"Q-K01-01": "B", "Q-K02-01": "C", "Q-K04-01": "B"})
        assert res.correct_count == 3
        assert res.overall_level == "SOLID_FOUNDATION"
        assert res.overall_level_label == "稳固基础"
        after_events = default_event_repository.get_events_by_student("GATE_STU_3")
        assert len(initial_events) == len(after_events), "前测绝不污染正式 Event 仓储"
    results.append(run_check(3, "诊断结果客观生成且只读隔离不污染正式学习记录", check_3))

    # Check 4: Scoring weights normalization
    def check_4():
        total_w = (
            WEIGHT_WEAKNESS
            + WEIGHT_TARGET_RELEVANCE
            + WEIGHT_PREREQUISITE_READINESS
            + WEIGHT_PATH_AVAILABILITY
            + WEIGHT_DIAGNOSTIC_PRIORITY
        )
        assert abs(total_w - 1.0) < 1e-6, f"Weight sum must be 1.0, got {total_w}"
        score, factors, _, _ = calculate_node_priority(
            knowledge_id="K01",
            mastery=0.20,
            is_target_ancestor_or_self=True,
            is_same_chapter=True,
            all_prereqs_mastered=True,
            path_state="AVAILABLE",
        )
        assert 0.0 <= score <= 1.0
    results.append(run_check(4, "集中优先级打分公式与权重归一化校验", check_4))

    # Check 5: Prerequisite Supremacy hard constraint
    def check_5():
        route = default_dynamic_path_generator.generate_route("GATE_P5", "需求弹性 K08")
        step_kids = [s.knowledge_id for s in route.steps]
        # K08 requires K04, K07. K04 requires K03. K03 requires K01, K02.
        # K08 cannot be recommended ahead of K01 or K02 for a fresh student!
        assert route.steps[0].knowledge_id in ["K01", "K02"]
    results.append(run_check(5, "前置知识绝对霸权硬约束 (Prerequisite Supremacy)", check_5))

    # Check 6: Route length <= 3 and no locked node as step 1
    def check_6():
        route = default_dynamic_path_generator.generate_route("S001", "微观经济学总览")
        assert 0 <= route.route_length <= 3, f"Route length must be <= 3, got {route.route_length}"
        assert len(route.steps) == route.route_length
        assert route.steps[0].role == "CURRENT"
    results.append(run_check(6, "动态航线长度上限 Top-3 与第一站可达性保证", check_6))

    # Check 7: Deterministic tie-breaking across repeated invocations
    def check_7():
        r1 = default_dynamic_path_generator.generate_route("S001", "需求价格弹性")
        r2 = default_dynamic_path_generator.generate_route("S001", "需求价格弹性")
        assert r1.route_length == r2.route_length
        for s1, s2 in zip(r1.steps, r2.steps):
            assert s1.knowledge_id == s2.knowledge_id
            assert s1.rank == s2.rank
            assert s1.score == s2.score
            assert s1.role == s2.role
            assert s1.reason_codes == s2.reason_codes
    results.append(run_check(7, "多次执行相同输入生成确定性决策字段", check_7))

    # Check 8: Route step structured reasons and explanation
    def check_8():
        route = default_dynamic_path_generator.generate_route("S002", "导论")
        for step in route.steps:
            assert len(step.reason_codes) > 0
            assert len(step.explanation.strip()) > 5
            assert step.path_state in ["AVAILABLE", "IN_PROGRESS", "LOCKED"]
    results.append(run_check(8, "动态路线推荐理由与结构化原因编码完整性", check_8))

    # Check 9: Safe fallback behavior on unexpected input
    def check_9():
        route = default_dynamic_path_generator.generate_route("NON_EXISTENT_STUDENT_GATE", "")
        assert isinstance(route, DynamicLearningRoute)
        assert 0 <= route.route_length <= 3
    results.append(run_check(9, "异常边界场景下安全降级不抛 500", check_9))

    # Check 10: Knowledge graph overlay labels and flow edges
    def check_10():
        route = default_dynamic_path_generator.generate_route("S001", "导论")
        overlay = get_route_graph_overlay("S001", route)
        assert overlay["student_id"] == "S001"
        assert len(overlay["node_roles"]) == route.route_length
        for step in route.steps:
            assert step.knowledge_id in overlay["node_roles"]
            assert overlay["node_roles"][step.knowledge_id] == step.role
    results.append(run_check(10, "知识图谱航线节点高亮与时序流动边叠加", check_10))

    # Check 11: Unified gateway API endpoints
    def check_11():
        # Pretest create
        res1 = client.post("/api/diagnostic/pretest", json={"student_id": "GATE_API", "goal": "弹性"})
        assert res1.status_code == 200
        sid = res1.json()["session_id"]
        # Pretest submit
        res2 = client.post(f"/api/diagnostic/pretest/{sid}/submit", json={"answers": {"Q-K02-01": "C"}})
        assert res2.status_code == 200
        # Dynamic path
        res3 = client.get("/api/path/dynamic/GATE_API?goal=弹性")
        assert res3.status_code == 200
        # Explanation
        res4 = client.get("/api/path/dynamic/GATE_API/explanation?goal=弹性")
        assert res4.status_code == 200
    results.append(run_check(11, "统一 AI Gateway 极速前测与自适应路线 API 端点连通性", check_11))

    # Check 12: Frozen path invariant (app/, tests/, data/seeds/ 0 diff)
    def check_12():
        cmd = ["git", "diff", "--stat", "--", "app/", "tests/", "data/seeds/"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        assert res.returncode == 0, f"git diff failed: {res.stderr}"
        diff_out = res.stdout.strip()
        assert diff_out == "", f"Frozen paths mutated! Output:\n{diff_out}"
    results.append(run_check(12, "核心业务代码与测试目录绝对冻结 (0 diff)", check_12))

    print("=" * 70)
    passed_count = sum(1 for r in results if r)
    total_count = len(results)
    print(f"Sprint 8-B Quality Gate Summary: {passed_count}/{total_count} PASS")
    print("=" * 70)

    if passed_count == total_count:
        print("ALL 12 CHECKS PASSED SUCCESSFULLY.")
        sys.exit(0)
    else:
        print("SOME CHECKS FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
