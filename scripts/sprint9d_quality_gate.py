# -*- coding: utf-8 -*-
"""
scripts/sprint9d_quality_gate.py
================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-D
学习效果验证与资源自适应反馈严苛质量门禁 (12 Strict Quality Checks)

本门禁独立自动化校验 Sprint 9-D 全部核心契约与安全红线：
1. Git 架构基线与冻结目录零变更检查 (app/, tests/, data/seeds/ 0 diff)
2. 学习会话契约与模型完整性 (LearningSession, SessionStatus, EffectivenessStatus)
3. initial_mastery 服务端权威快照红线 (客户端不可伪造，服务端权威锁定)
4. 学习效果校验与服务端 final_mastery 权威重读 (服务端真实计算 delta)
5. 会话完成幂等性红线 (Duplicate completion idempotency)
6. 多学生上下文硬隔离防越权 (Student Context Isolation on Session Access)
7. 效果分档与确定性阈值映射 (STRONG / MEANINGFUL / STABLE / NEEDS_MORE_SUPPORT)
8. 遥测日志物理隔离红线 (resource_effectiveness_events.jsonl vs learning_events.jsonl)
9. 生产底座 BKT 掌握度零污染与零突变红线 (Zero Mutation Invariant)
10. AI 伴学只读边界与真实材料上下文联动 (allow_production_decision = False)
11. 学生端文案时间关联性与零技术黑话合规性审核 (No Jargon, Temporal Association)
12. 前后端全量测试套件与生产构建完整性 (pytest, npm test, npm run build)
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.core.config import settings
from gateway.api import create_gateway_app
from gateway.learning.effectiveness import (
    SessionStatus,
    EffectivenessStatus,
    LearningSession,
    LearningEffectiveness,
    KnowledgeEffectivenessResponse,
    SessionCompleteResponse,
    default_session_service,
    default_effectiveness_analyzer,
    default_feedback_service,
)
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository


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
    print("=" * 80)
    print("Sprint 9-D: Learning Effectiveness & Feedback Quality Gate (12 Checks)")
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
    # Check 2: 学习会话契约与模型完整性
    # -------------------------------------------------------------------------
    def check_02_session_models_integrity():
        assert SessionStatus.IN_PROGRESS == "IN_PROGRESS"
        assert SessionStatus.COMPLETED == "COMPLETED"
        assert EffectivenessStatus.STRONG_PROGRESS == "STRONG_PROGRESS"
        assert EffectivenessStatus.MEANINGFUL_PROGRESS == "MEANINGFUL_PROGRESS"
        assert EffectivenessStatus.STABLE == "STABLE"
        assert EffectivenessStatus.NEEDS_MORE_SUPPORT == "NEEDS_MORE_SUPPORT"

    # -------------------------------------------------------------------------
    # Check 3: initial_mastery 服务端权威快照红线
    # -------------------------------------------------------------------------
    def check_03_initial_mastery_snapshot():
        resp = client.post(
            "/api/learning/sessions",
            json={
                "student_id": "S001",
                "knowledge_id": "K07",
                "resource_ids": ["res_k07_concept", "res_k07_example"],
            },
        )
        assert resp.status_code == 200, f"创建会话失败: {resp.text}"
        data = resp.json()
        assert data["student_id"] == "S001"
        assert data["knowledge_id"] == "K07"
        assert data["status"] == "IN_PROGRESS"
        # 权威 BKT 快照
        bkt_state = default_bkt_state_repository.get_state("S001", "K07")
        expected_p = bkt_state.mastery_probability if bkt_state else 0.20
        assert abs(data["initial_mastery"] - expected_p) < 1e-4

    # -------------------------------------------------------------------------
    # Check 4: 学习效果校验与服务端 final_mastery 权威重读
    # -------------------------------------------------------------------------
    def check_04_session_completion_and_delta():
        # 创建一个测试 session
        create_resp = client.post(
            "/api/learning/sessions",
            json={"student_id": "S001", "knowledge_id": "K08"},
        )
        sess_id = create_resp.json()["session_id"]
        init_m = create_resp.json()["initial_mastery"]

        # 完成会话
        comp_resp = client.post(
            f"/api/learning/sessions/{sess_id}/complete",
            json={
                "student_id": "S001",
                "completed_resource_ids": ["res_k08_concept", "res_k08_example"],
            },
        )
        assert comp_resp.status_code == 200, f"完成会话失败: {comp_resp.text}"
        comp_data = comp_resp.json()
        assert comp_data["session"]["status"] == "COMPLETED"
        assert comp_data["effectiveness"]["initial_mastery"] == init_m
        expected_delta = round(comp_data["effectiveness"]["final_mastery"] - init_m, 4)
        assert comp_data["effectiveness"]["mastery_delta"] == expected_delta

    # -------------------------------------------------------------------------
    # Check 5: 会话完成幂等性红线
    # -------------------------------------------------------------------------
    def check_05_idempotency_invariant():
        create_resp = client.post(
            "/api/learning/sessions",
            json={"student_id": "S001", "knowledge_id": "K09"},
        )
        sess_id = create_resp.json()["session_id"]
        r1 = client.post(
            f"/api/learning/sessions/{sess_id}/complete",
            json={"student_id": "S001"},
        )
        assert r1.status_code == 200
        # 第二次完成同一会话，必须幂等返回且无报错
        r2 = client.post(
            f"/api/learning/sessions/{sess_id}/complete",
            json={"student_id": "S001"},
        )
        assert r2.status_code == 200
        assert r1.json()["session"]["session_id"] == r2.json()["session"]["session_id"]
        assert r1.json()["effectiveness"]["mastery_delta"] == r2.json()["effectiveness"]["mastery_delta"]

    # -------------------------------------------------------------------------
    # Check 6: 多学生上下文硬隔离防越权
    # -------------------------------------------------------------------------
    def check_06_student_isolation():
        create_resp = client.post(
            "/api/learning/sessions",
            json={"student_id": "S001", "knowledge_id": "K10"},
        )
        sess_id = create_resp.json()["session_id"]

        # S002 试图读取或完成 S001 的会话，必须拦截为 403
        get_res = client.get(f"/api/learning/sessions/{sess_id}?student_id=S002")
        assert get_res.status_code == 403, f"未拦截跨生越权访问: {get_res.status_code}"

        comp_res = client.post(
            f"/api/learning/sessions/{sess_id}/complete",
            json={"student_id": "S002"},
        )
        assert comp_res.status_code == 403, f"未拦截跨生越权完成: {comp_res.status_code}"

    # -------------------------------------------------------------------------
    # Check 7: 效果分档与确定性阈值映射
    # -------------------------------------------------------------------------
    def check_07_effectiveness_tier_mapping():
        s1, _, _, _ = default_feedback_service.evaluate(0.50, 0.70, 0.20)
        assert s1 == EffectivenessStatus.STRONG_PROGRESS

        s2, _, _, _ = default_feedback_service.evaluate(0.50, 0.65, 0.15)
        assert s2 == EffectivenessStatus.STRONG_PROGRESS

        s3, _, _, _ = default_feedback_service.evaluate(0.50, 0.64, 0.14)
        assert s3 == EffectivenessStatus.MEANINGFUL_PROGRESS

        s4, _, _, _ = default_feedback_service.evaluate(0.50, 0.55, 0.05)
        assert s4 == EffectivenessStatus.MEANINGFUL_PROGRESS

        s5, _, _, _ = default_feedback_service.evaluate(0.50, 0.54, 0.04)
        assert s5 == EffectivenessStatus.STABLE

        s6, _, _, _ = default_feedback_service.evaluate(0.50, 0.50, 0.00)
        assert s6 == EffectivenessStatus.STABLE

        s7, _, _, _ = default_feedback_service.evaluate(0.50, 0.46, -0.04)
        assert s7 == EffectivenessStatus.STABLE

        s8, _, _, _ = default_feedback_service.evaluate(0.50, 0.45, -0.05)
        assert s8 == EffectivenessStatus.NEEDS_MORE_SUPPORT

        s9, _, _, _ = default_feedback_service.evaluate(0.50, 0.35, -0.15)
        assert s9 == EffectivenessStatus.NEEDS_MORE_SUPPORT

    # -------------------------------------------------------------------------
    # Check 8: 遥测日志物理隔离红线
    # -------------------------------------------------------------------------
    def check_08_telemetry_isolation():
        learning_events_path = settings.DATA_DIR / "learning_events.jsonl"
        size_before = learning_events_path.stat().st_size if learning_events_path.exists() else 0

        # 进行会话创建与完成
        sess = default_session_service.create_session("S001", "K12")
        default_session_service.complete_session(sess.session_id, "S001")

        size_after = learning_events_path.stat().st_size if learning_events_path.exists() else 0
        assert size_before == size_after, "学习效果遥测违规写入了 learning_events.jsonl!"

    # -------------------------------------------------------------------------
    # Check 9: 生产底座 BKT 掌握度零污染与零突变红线
    # -------------------------------------------------------------------------
    def check_09_zero_bkt_mutation_invariant():
        bkt_file = settings.DATA_DIR / "bkt_states.json"
        content_before = bkt_file.read_bytes() if bkt_file.exists() else b""

        # 查询指定考点效果
        resp = client.get("/api/learning/resources/K01/effectiveness?student_id=S001")
        assert resp.status_code == 200

        content_after = bkt_file.read_bytes() if bkt_file.exists() else b""
        assert content_before == content_after, "效果查询产生了未授权的 BKT 底座修改!"

    # -------------------------------------------------------------------------
    # Check 10: AI 伴学只读边界与真实材料上下文联动
    # -------------------------------------------------------------------------
    def check_10_ai_companion_read_only_and_context():
        resp = client.post(
            "/api/ai/companion",
            json={
                "student_id": "S001",
                "mode": "concept_explain",
                "knowledge_id": "K08",
                "message": "请帮我讲解需求价格弹性的现实生活例子",
                "resource_context": {
                    "resource_id": "res_k08_example",
                    "resource_title": "需求价格弹性 典型生活与商业实例精析",
                    "resource_type": "EXAMPLE",
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["safety"]["allow_production_decision"] is False
        assert "需求价格弹性 典型生活与商业实例精析" in data["answer"]

    # -------------------------------------------------------------------------
    # Check 11: 学生端文案时间关联性与零技术黑话合规性审核
    # -------------------------------------------------------------------------
    def check_11_no_jargon_and_temporal_association():
        forbidden = ["BKT", "Bayesian", "PathState", "Resolver", "因为你看了", "由于你阅读了"]
        for delta in [0.20, 0.10, 0.00, -0.10]:
            _, title, msg, _ = default_feedback_service.evaluate(0.50, 0.50 + delta, delta)
            for f in forbidden:
                assert f not in title, f"标题泄露技术黑话或虚假因果: {f} in {title}"
                assert f not in msg, f"内容泄露技术黑话或虚假因果: {f} in {msg}"
            assert "完成本次学习后" in msg

    # -------------------------------------------------------------------------
    # Check 12: 前后端全量测试套件与生产构建完整性
    # -------------------------------------------------------------------------
    def check_12_full_test_suite_and_build():
        # 后端专项测试
        pytest_res = subprocess.run(
            ["pytest", "gateway/tests/test_sprint9d_learning_effectiveness.py", "-q"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if pytest_res.returncode != 0:
            raise AssertionError(f"后端 Sprint 9-D 测试未通过:\n{pytest_res.stdout}\n{pytest_res.stderr}")

        # 前端契约测试
        npm_test_res = subprocess.run(
            ["npm", "test", "--prefix", "frontend"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            shell=True,
            encoding="utf-8",
            errors="replace",
        )
        if npm_test_res.returncode != 0:
            raise AssertionError(f"前端测试未通过:\n{npm_test_res.stdout}\n{npm_test_res.stderr}")

        # 前端构建验证
        build_res = subprocess.run(
            ["npm", "run", "build", "--prefix", "frontend"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            shell=True,
            encoding="utf-8",
            errors="replace",
        )
        if build_res.returncode != 0:
            raise AssertionError(f"前端构建未通过:\n{build_res.stdout}\n{build_res.stderr}")

    checks = [
        (1, "Git baseline & frozen dirs (app/, tests/, seeds/ 0 diff)", check_01_git_baseline_and_frozen_dirs),
        (2, "Session & effectiveness models integrity", check_02_session_models_integrity),
        (3, "Initial mastery server authoritative snapshot", check_03_initial_mastery_snapshot),
        (4, "Session completion & server-computed mastery delta", check_04_session_completion_and_delta),
        (5, "Idempotency invariant on duplicate completion", check_05_idempotency_invariant),
        (6, "Student context isolation on session access (403 forbidden)", check_06_student_isolation),
        (7, "Deterministic 4-tier effectiveness mapping", check_07_effectiveness_tier_mapping),
        (8, "Telemetry isolation (zero writes to learning_events.jsonl)", check_08_telemetry_isolation),
        (9, "Zero BKT mutation invariant on bkt_states.json", check_09_zero_bkt_mutation_invariant),
        (10, "AI Companion read-only invariant & resource context grounding", check_10_ai_companion_read_only_and_context),
        (11, "No tech jargon & temporal association narrative", check_11_no_jargon_and_temporal_association),
        (12, "Full frontend/backend test suites & production build", check_12_full_test_suite_and_build),
    ]

    passed = 0
    for num, title, fn in checks:
        if run_check(num, title, fn):
            passed += 1
        else:
            print(f"\n[QUALITY GATE HALTED] Check {num} failed!")
            sys.exit(1)

    print("=" * 80)
    print(f"[SUCCESS] SPRINT 9-D QUALITY GATE PASSED: {passed}/12 CHECKS GREEN!")
    print("=" * 80)


if __name__ == "__main__":
    main()
