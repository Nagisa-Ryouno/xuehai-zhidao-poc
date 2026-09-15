# -*- coding: utf-8 -*-
"""
scripts/sprint9c_quality_gate.py
================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-C
学习资源中心与资源感知自适应学习严苛质量门禁 (12 Strict Quality Checks)

本门禁独立自动化校验 Sprint 9-C 全部核心契约与安全红线：
1. Git 架构基线与冻结目录零变更检查 (app/, tests/, data/seeds/ 0 diff)
2. 全图谱 30 考点 (K01~K30) 100% 学习资源目录覆盖
3. 考点资源完备性校验 (每个考点至少含 CONCEPT_CARD, EXAMPLE, PRACTICE，总数 >= 90)
4. 杜绝虚假/失效外链校验 (is_external=False, source='xuehai_internal', source_url=None)
5. 确定性资源感知自适应推荐规则矩阵全覆盖 (Cases A ~ E)
6. 边界判定与纯函数 100 次调用确定性哈希一致性 (0.59/0.60, 0.79/0.80)
7. 遥测日志物理隔离红线 (data/resource_events.jsonl vs data/learning_events.jsonl)
8. 生产掌握度事实守恒与零副作用红线 (Zero Mutation Invariant on bkt_states.json)
9. 学生端文案零技术黑话合规性审核 (No Jargon)
10. 后端全量单元测试与 API 契约执行 (pytest gateway/tests/test_sprint9c_learning_resources.py)
11. 前端全量契约测试执行 (npm test --prefix frontend)
12. 前端类型安全与生产构建完整性 (npm run typecheck & npm run build)
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.core.config import settings
from gateway.api import create_gateway_app
from gateway.content.concept_cards import CONCEPT_CARDS
from gateway.learning.resources import (
    ResourceType,
    RESOURCE_CATALOG,
    get_all_resources,
    get_resources_by_knowledge,
    get_resource_by_id,
    ResourceResolver,
    default_resource_resolver,
    record_resource_event,
    get_student_resource_events,
)


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
    print("Sprint 9-C: Learning Resource Hub & Adaptive Learning Quality Gate (12 Checks)")
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
    # Check 2: 全图谱 30 考点 (K01~K30) 100% 学习资源目录覆盖
    # -------------------------------------------------------------------------
    def check_02_all_30_kps_covered():
        all_kids = [f"K{i:02d}" for i in range(1, 31)]
        for kid in all_kids:
            items = get_resources_by_knowledge(kid)
            if not items:
                raise AssertionError(f"考点 {kid} 缺少任何学习资源")
            if len(items) < 3:
                raise AssertionError(f"考点 {kid} 资源数量不足 3 项: {len(items)}")

    # -------------------------------------------------------------------------
    # Check 3: 考点资源完备性校验 (CONCEPT_CARD, EXAMPLE, PRACTICE，总数 >= 90)
    # -------------------------------------------------------------------------
    def check_03_resource_completeness():
        all_res = get_all_resources()
        if len(all_res) < 90:
            raise AssertionError(f"总资源数量不足 90 项: {len(all_res)}")

        all_kids = [f"K{i:02d}" for i in range(1, 31)]
        for kid in all_kids:
            types = {r.resource_type for r in get_resources_by_knowledge(kid)}
            if ResourceType.CONCEPT_CARD not in types:
                raise AssertionError(f"考点 {kid} 缺少 CONCEPT_CARD")
            if ResourceType.EXAMPLE not in types:
                raise AssertionError(f"考点 {kid} 缺少 EXAMPLE")
            if ResourceType.PRACTICE not in types:
                raise AssertionError(f"考点 {kid} 缺少 PRACTICE")

    # -------------------------------------------------------------------------
    # Check 4: 杜绝虚假/失效外链校验
    # -------------------------------------------------------------------------
    def check_04_no_external_links():
        for r in RESOURCE_CATALOG.values():
            if r.is_external:
                raise AssertionError(f"资源 {r.resource_id} 标为外部链接")
            if r.source != "xuehai_internal":
                raise AssertionError(f"资源 {r.resource_id} 来源非内部: {r.source}")
            if r.source_url is not None:
                raise AssertionError(f"资源 {r.resource_id} 包含外部URL: {r.source_url}")

    # -------------------------------------------------------------------------
    # Check 5: 确定性资源感知自适应推荐规则矩阵全覆盖 (Cases A ~ E)
    # -------------------------------------------------------------------------
    def check_05_cases_a_to_e_matrix():
        # Case A: mastery < 0.60
        res_a = ResourceResolver.resolve("S001", "K01", mastery_override=0.35, consecutive_incorrect_override=0)
        if res_a.case_code != "CASE_A_WEAK_FOUNDATION":
            raise AssertionError(f"Case A 期望 CASE_A_WEAK_FOUNDATION, 实际: {res_a.case_code}")
        if res_a.recommendations[0].resource.resource_type != ResourceType.CONCEPT_CARD:
            raise AssertionError("Case A 首选必须为 CONCEPT_CARD")

        # Case B: 0.60 <= mastery < 0.80
        res_b = ResourceResolver.resolve("S001", "K01", mastery_override=0.70, consecutive_incorrect_override=0)
        if res_b.case_code != "CASE_B_DEVELOPING":
            raise AssertionError(f"Case B 期望 CASE_B_DEVELOPING, 实际: {res_b.case_code}")
        if res_b.recommendations[0].resource.resource_type != ResourceType.EXAMPLE:
            raise AssertionError("Case B 首选必须为 EXAMPLE")

        # Case C: mastery >= 0.80 且有后继 (K01)
        res_c = ResourceResolver.resolve("S001", "K01", mastery_override=0.85, consecutive_incorrect_override=0)
        if res_c.case_code != "CASE_C_MASTERED_ADVANCE":
            raise AssertionError(f"Case C 期望 CASE_C_MASTERED_ADVANCE, 实际: {res_c.case_code}")

        # Case D: mastery >= 0.80 且终点无后继 (K30)
        res_d = ResourceResolver.resolve("S001", "K30", mastery_override=0.90, consecutive_incorrect_override=0)
        if res_d.case_code != "CASE_D_TERMINAL_CONSOLIDATE":
            raise AssertionError(f"Case D 期望 CASE_D_TERMINAL_CONSOLIDATE, 实际: {res_d.case_code}")

        # Case E: consecutive_incorrect >= 2
        res_e = ResourceResolver.resolve("S001", "K01", mastery_override=0.75, consecutive_incorrect_override=2)
        if res_e.case_code != "CASE_E_ROADBLOCK_REPAIR":
            raise AssertionError(f"Case E 期望 CASE_E_ROADBLOCK_REPAIR, 实际: {res_e.case_code}")
        if res_e.recommendations[0].resource.resource_type != ResourceType.CONCEPT_CARD:
            raise AssertionError("Case E 首选必须为 CONCEPT_CARD 排查阻碍")

    # -------------------------------------------------------------------------
    # Check 6: 边界判定与纯函数 100 次调用确定性一致性
    # -------------------------------------------------------------------------
    def check_06_boundary_and_determinism():
        r_059 = ResourceResolver.resolve("S001", "K01", mastery_override=0.59)
        r_060 = ResourceResolver.resolve("S001", "K01", mastery_override=0.60)
        if r_059.case_code != "CASE_A_WEAK_FOUNDATION" or r_060.case_code != "CASE_B_DEVELOPING":
            raise AssertionError("0.59 vs 0.60 临界边界判定错误")

        r_079 = ResourceResolver.resolve("S001", "K01", mastery_override=0.79)
        r_080 = ResourceResolver.resolve("S001", "K01", mastery_override=0.80)
        if r_079.case_code != "CASE_B_DEVELOPING" or r_080.case_code != "CASE_C_MASTERED_ADVANCE":
            raise AssertionError("0.79 vs 0.80 临界边界判定错误")

        # 100 次完全确定性
        base = ResourceResolver.resolve("S001", "K01", mastery_override=0.45).model_dump_json()
        for _ in range(100):
            cur = ResourceResolver.resolve("S001", "K01", mastery_override=0.45).model_dump_json()
            if cur != base:
                raise AssertionError("100 次重复调用出现非确定性漂移")

    # -------------------------------------------------------------------------
    # Check 7: 遥测日志物理隔离红线
    # -------------------------------------------------------------------------
    def check_07_telemetry_isolation():
        learning_path = settings.DATA_DIR / "learning_events.jsonl"
        init_lines = len(learning_path.read_text(encoding="utf-8").strip().splitlines()) if learning_path.exists() else 0

        # 发送资源行为
        resp = client.post(
            "/api/learning/resources/events",
            json={
                "student_id": "QG_TEST_STU",
                "resource_id": "res_k01_concept",
                "knowledge_id": "K01",
                "event_type": "RESOURCE_COMPLETE",
                "duration_seconds": 60,
            },
        )
        if resp.status_code != 200:
            raise AssertionError(f"资源事件上报失败: {resp.text}")

        cur_lines = len(learning_path.read_text(encoding="utf-8").strip().splitlines()) if learning_path.exists() else 0
        if cur_lines != init_lines:
            raise AssertionError(f"资源事件违规写入了 learning_events.jsonl: 原 {init_lines} 行，现 {cur_lines} 行")

    # -------------------------------------------------------------------------
    # Check 8: 生产掌握度事实守恒与零副作用红线
    # -------------------------------------------------------------------------
    def check_08_bkt_zero_mutation():
        bkt_path = settings.DATA_DIR / "bkt_states.json"
        init_bkt = bkt_path.read_bytes() if bkt_path.exists() else b""

        # 访问推荐与资源端点
        client.get("/api/learning/resources/recommended/S001?knowledge_id=K01")
        client.get("/api/learning/resources/K01")
        client.get("/api/learning/resources/item/res_k01_concept")
        client.post(
            "/api/learning/resources/events",
            json={
                "student_id": "S001",
                "resource_id": "res_k01_example",
                "knowledge_id": "K01",
                "event_type": "RESOURCE_OPEN",
                "duration_seconds": 30,
            },
        )

        cur_bkt = bkt_path.read_bytes() if bkt_path.exists() else b""
        if cur_bkt != init_bkt:
            raise AssertionError("资源查询或浏览行为篡改了 bkt_states.json 掌握度数据！")

    # -------------------------------------------------------------------------
    # Check 9: 学生端文案零技术黑话合规性审核 (No Jargon)
    # -------------------------------------------------------------------------
    def check_09_no_jargon():
        jargon = ["bkt", "dag", "mutationdomain", "round_half_up", "jsonl", "sql", "backend", "p_transit"]
        for kid in ["K01", "K08", "K30"]:
            for m in [0.35, 0.70, 0.85]:
                resp = ResourceResolver.resolve("S001", kid, mastery_override=m)
                for w in jargon:
                    if w in resp.reason_summary.lower():
                        raise AssertionError(f"推荐说明暴露黑话: {w}")
                    for r in resp.recommendations:
                        if w in r.recommended_reason.lower():
                            raise AssertionError(f"推荐理由暴露黑话: {w}")

    # -------------------------------------------------------------------------
    # Check 10: 后端全量单元测试与 API 契约执行
    # -------------------------------------------------------------------------
    def check_10_pytest_backend():
        cmd = [sys.executable, "-m", "pytest", "gateway/tests/test_sprint9c_learning_resources.py", "-q"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode != 0:
            raise AssertionError(f"后端测试失败:\n{res.stdout}\n{res.stderr}")

    # -------------------------------------------------------------------------
    # Check 11: 前端全量契约测试执行
    # -------------------------------------------------------------------------
    def check_11_npm_test_frontend():
        cmd = ["npm", "test", "--prefix", "frontend"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True)
        if res.returncode != 0:
            raise AssertionError(f"前端测试失败:\n{res.stdout}\n{res.stderr}")

    # -------------------------------------------------------------------------
    # Check 12: 前端类型安全与生产构建完整性
    # -------------------------------------------------------------------------
    def check_12_frontend_build():
        cmd_type = ["npm", "run", "typecheck", "--prefix", "frontend"]
        res_type = subprocess.run(cmd_type, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True)
        if res_type.returncode != 0:
            raise AssertionError(f"前端类型检查失败:\n{res_type.stdout}\n{res_type.stderr}")

        cmd_build = ["npm", "run", "build", "--prefix", "frontend"]
        res_build = subprocess.run(cmd_build, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True)
        if res_build.returncode != 0:
            raise AssertionError(f"前端构建失败:\n{res_build.stdout}\n{res_build.stderr}")

    checks = [
        (1, "Git 架构基线与冻结目录零变更检查 (app/, tests/, data/seeds/ 0 diff)", check_01_git_baseline_and_frozen_dirs),
        (2, "全图谱 30 考点 (K01~K30) 100% 学习资源目录覆盖", check_02_all_30_kps_covered),
        (3, "考点资源完备性校验 (CONCEPT_CARD, EXAMPLE, PRACTICE, 总数 >= 90)", check_03_resource_completeness),
        (4, "杜绝虚假/失效外链校验 (is_external=False, source='xuehai_internal')", check_04_no_external_links),
        (5, "确定性资源感知自适应推荐规则矩阵全覆盖 (Cases A ~ E)", check_05_cases_a_to_e_matrix),
        (6, "边界判定与纯函数 100 次调用确定性一致性", check_06_boundary_and_determinism),
        (7, "遥测日志物理隔离红线 (resource_events.jsonl 独立存储)", check_07_telemetry_isolation),
        (8, "生产掌握度事实守恒与零副作用红线 (Zero Mutation on bkt_states.json)", check_08_bkt_zero_mutation),
        (9, "学生端文案零技术黑话合规性审核 (No Jargon)", check_09_no_jargon),
        (10, "后端全量单元测试与 API 契约执行", check_10_pytest_backend),
        (11, "前端全量契约测试执行 (npm test --prefix frontend)", check_11_npm_test_frontend),
        (12, "前端类型安全与生产构建完整性 (npm run typecheck & build)", check_12_frontend_build),
    ]

    all_passed = True
    for num, title, fn in checks:
        if not run_check(num, title, fn):
            all_passed = False

    print("=" * 80)
    if all_passed:
        print("ALL 12 SPRINT 9-C QUALITY CHECKS PASSED! [QUALITY GATE: GREEN]")
        sys.exit(0)
    else:
        print("SOME QUALITY CHECKS FAILED! [QUALITY GATE: RED]")
        sys.exit(1)


if __name__ == "__main__":
    main()
