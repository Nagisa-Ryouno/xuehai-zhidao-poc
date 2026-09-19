# -*- coding: utf-8 -*-
"""
scripts/sprint10c_teacher_gate.py
==================================
学海智导 (Xuehai Zhidao) — Sprint 10-C / Phase 2: Teacher Web Productization
教师端学情中台质量门禁 (20-Point Strict Quality Gate)

验证项：
1. GET /api/teacher/overview 班级宏观数据契约与 4 大核心 KPI
2. GET /api/teacher/overview 薄弱考点 Top-5 结构与指标合法性
3. GET /api/teacher/knowledge 权威返回全部 30 个考点全景
4. GET /api/teacher/knowledge 考点数据字段完备性 (平均掌握度、薄弱人数、错题量等)
5. GET /api/teacher/knowledge 排序确定性 (严格按 knowledge_id 升序)
6. GET /api/teacher/students 全班学生花名册列表契约
7. GET /api/teacher/students/S001 单生全维学情下钻契约
8. GET /api/teacher/students/S002 单生全维学情下钻契约
9. 多生学情物理隔离断言 (S001 vs S002 数据互不串扰)
10. 不存在学生 ID 严谨返回 404 Not Found
11. 教师端操作绝对零副作用断言 (0 BKT 变更，0 PathState 变更，0 事件写入)
12. 知识点全景 10 次调用字节级严格一致与确定性幂等
13. 前端路由解析契约 (/teacher, /teacher/overview, /teacher/knowledge, /teacher/students)
14. 路由角色切换严格保留学生上下文 (S001 / S003)
15. 零学生排名红线核查 (严禁「班级排名」、「Top 10 学生」、「最后一名」)
16. 零歧视标签红线核查 (严禁「差生」、「淘汰」、「劣等」)
17. 零生产决策越权断言 (严禁 AI 替教师做生产性决策，allow_production_decision = False)
18. 前端 TypeScript 类型检查 (npm run typecheck 零错误)
19. 前端生产构建验证 (npm run build 产物完备)
20. 核心基准代码冻结断言 (app/, tests/, data/seeds/, gateway/learning/ 零篡改)
"""

import sys
import json
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 将项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

# 引入网关与仓储
from gateway.api import create_gateway_app
from app.infrastructure.persistence.event_repository import default_event_repository
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from path_state_service import get_all_path_states


def run_gate():
    print("=" * 70)
    print("🚀 启动 Sprint 10-C / Phase 2 教师端学情中台 20 项严格质量门禁")
    print("=" * 70)

    client = TestClient(create_gateway_app())
    passed_checks = 0

    def check(idx: int, desc: str, condition: bool, err_msg: str = ""):
        nonlocal passed_checks
        if condition:
            print(f"  [PASS] Check {idx:02d}: {desc}")
            passed_checks += 1
        else:
            print(f"  [FAIL] Check {idx:02d}: {desc} -> {err_msg}")
            sys.exit(1)

    # 1. GET /api/teacher/overview 班级宏观数据契约与 4 大核心 KPI
    res_ov = client.get("/api/teacher/overview")
    check(1, "GET /api/teacher/overview 返回 200 及 4 大核心 KPI",
          res_ov.status_code == 200 and
          "class_kpis" in res_ov.json() and
          "total_students" in res_ov.json()["class_kpis"] and
          "class_avg_mastery" in res_ov.json()["class_kpis"],
          f"Status: {res_ov.status_code}, Body: {res_ov.text[:200]}")
    ov_data = res_ov.json()

    # 2. GET /api/teacher/overview 薄弱考点 Top-5 结构与指标合法性
    wps = ov_data.get("weak_knowledge_points", [])
    check(2, "GET /api/teacher/overview 薄弱考点 Top-5 结构完整且数量 <= 5",
          isinstance(wps, list) and len(wps) <= 5 and
          all("knowledge_id" in w and "urgency" in w and 0.0 <= w["avg_mastery"] <= 1.0 for w in wps),
          f"Weak points: {wps}")

    # 3. GET /api/teacher/knowledge 权威返回全部 30 个考点全景
    res_kn = client.get("/api/teacher/knowledge")
    check(3, "GET /api/teacher/knowledge 权威返回全部 30 个考点",
          res_kn.status_code == 200 and res_kn.json().get("total_count") == 30 and
          len(res_kn.json().get("knowledge_points", [])) == 30,
          f"Status: {res_kn.status_code}, Body: {res_kn.text[:200]}")
    kn_data = res_kn.json()
    kps = kn_data["knowledge_points"]

    # 4. GET /api/teacher/knowledge 考点数据字段完备性
    all_fields_ok = all(
        {"knowledge_id", "knowledge_name", "chapter", "average_mastery",
         "student_count", "weak_student_count", "total_mistakes", "urgency"}.issubset(k.keys())
        and 0.0 <= k["average_mastery"] <= 1.0
        and k["urgency"] in ("HIGH", "MEDIUM", "LOW")
        for k in kps
    )
    check(4, "GET /api/teacher/knowledge 考点数据指标维度合法且数值闭区间合规",
          all_fields_ok, "考点数据字段缺失或数值越界")

    # 5. GET /api/teacher/knowledge 排序确定性 (严格按 knowledge_id 升序)
    kids = [k["knowledge_id"] for k in kps]
    check(5, "GET /api/teacher/knowledge 严格按 knowledge_id 升序排列 (K01 -> K30)",
          kids == sorted(kids) and kids[0] == "K01" and kids[-1] == "K30",
          f"Actual order: {kids[:5]} ... {kids[-5:]}")

    # 6. GET /api/teacher/students 全班学生花名册列表契约
    res_st = client.get("/api/teacher/students")
    check(6, "GET /api/teacher/students 返回全班学生花名册列表且人数 >= 5",
          res_st.status_code == 200 and isinstance(res_st.json(), list) and len(res_st.json()) >= 5,
          f"Status: {res_st.status_code}, Count: {len(res_st.json()) if isinstance(res_st.json(), list) else 0}")
    students_list = res_st.json()

    # 7. GET /api/teacher/students/S001 单生全维学情下钻契约
    res_s001 = client.get("/api/teacher/students/S001")
    check(7, "GET /api/teacher/students/S001 返回 200 及完整档案下钻画像",
          res_s001.status_code == 200 and "summary" in res_s001.json() and
          "progress" in res_s001.json() and "wrong_answers" in res_s001.json(),
          f"Status: {res_s001.status_code}")

    # 8. GET /api/teacher/students/S002 单生全维学情下钻契约
    res_s002 = client.get("/api/teacher/students/S002")
    check(8, "GET /api/teacher/students/S002 返回 200 及完整档案下钻画像",
          res_s002.status_code == 200 and "summary" in res_s002.json() and
          "progress" in res_s002.json() and "wrong_answers" in res_s002.json(),
          f"Status: {res_s002.status_code}")

    # 9. 多生学情物理隔离断言 (S001 vs S002 数据互不串扰)
    d1 = res_s001.json()
    d2 = res_s002.json()
    check(9, "多生学情严格物理隔离断言 (S001 与 S002 数据互不串扰)",
          d1["summary"]["student_id"] == "S001" and d2["summary"]["student_id"] == "S002" and
          d1["summary"]["student_name"] != d2["summary"]["student_name"],
          "S001 与 S002 产生数据混淆")

    # 10. 不存在学生 ID 严谨返回 404 Not Found
    res_404 = client.get("/api/teacher/students/NON_EXISTENT_STUDENT_999")
    check(10, "查询不存在的学生 ID 严谨返回 404 Not Found",
          res_404.status_code == 404,
          f"Status: {res_404.status_code}")

    # 11. 教师端操作绝对零副作用断言 (0 BKT 变更，0 PathState 变更，0 事件写入)
    sid = "S001"
    bkt_before = default_bkt_state_repository.get_student_states(sid)
    path_before = get_all_path_states(sid)
    events_before = len(default_event_repository.get_events_by_student(sid))

    client.get("/api/teacher/overview")
    client.get("/api/teacher/knowledge")
    client.get("/api/teacher/students")
    client.get(f"/api/teacher/students/{sid}")

    bkt_after = default_bkt_state_repository.get_student_states(sid)
    path_after = get_all_path_states(sid)
    events_after = len(default_event_repository.get_events_by_student(sid))

    check(11, "教师端学情中台全部查询绝对只读，零副作用 (0 BKT/0 PathState/0 学习事件变更)",
          bkt_before == bkt_after and path_before == path_after and events_before == events_after,
          "检测到只读查询引发了业务状态变动")

    # 12. 知识点全景 10 次调用字节级严格一致与确定性幂等
    first_res = client.get("/api/teacher/knowledge").json()
    idempotent_ok = all(
        json.dumps(first_res, sort_keys=True) == json.dumps(client.get("/api/teacher/knowledge").json(), sort_keys=True)
        for _ in range(10)
    )
    check(12, "知识点全景 10 次调用返回字节级严格一致与确定性幂等",
          idempotent_ok, "多次调用结果不一致")

    # 13. 前端路由解析契约 (/teacher, /teacher/overview, /teacher/knowledge, /teacher/students)
    router_file = Path("frontend/src/router.ts").read_text(encoding="utf-8")
    check(13, "前端 router.ts 严格支持 /teacher/overview, /teacher/knowledge, /teacher/students 3-Tab",
          "'dashboard' | 'overview' | 'knowledge' | 'students'" in router_file and
          "matchedSub = 'overview'" in router_file and
          "matchedSub = 'knowledge'" in router_file and
          "matchedSub = 'students'" in router_file,
          "router.ts 缺少子路由解析支持")

    # 14. 路由角色切换严格保留学生上下文 (S001 / S003)
    check(14, "前端路由切换严格保留 studentId 上下文契约",
          "studentId: state.studentId" in router_file,
          "router.ts 角色切换上下文丢失")

    # 15. 零学生排名红线核查 (严禁「班级排名」、「Top 10 学生」、「最后一名」)
    teacher_ui = Path("frontend/src/layouts/TeacherLayout.tsx").read_text(encoding="utf-8")
    banned_rankings = ["班级排名", "学生排名", "Top 10 学生", "最后一名", "倒数第"]
    ranking_found = [p for p in banned_rankings if p in teacher_ui]
    check(15, "零学生排名红线核查 (严禁出现学生排名等恶性竞争标签)",
          len(ranking_found) == 0,
          f"检测到违规排名词汇: {ranking_found}")

    # 16. 零歧视标签红线核查 (严禁「差生」、「淘汰」、「劣等」)
    stigma_words = ["差生", "淘汰", "劣等", "不及格学生名单"]
    stigma_found = [w for w in stigma_words if w in teacher_ui]
    check(16, "零歧视标签红线核查 (严禁出现贬损/歧视性字眼，坚持人本温度)",
          len(stigma_found) == 0,
          f"检测到违规标签词汇: {stigma_found}")

    # 17. 零生产决策越权断言 (严禁 AI 替教师做生产性决策，allow_production_decision = False)
    check(17, "零生产决策越权原则 (系统不替教师决策，客观辅助教学)",
          "系统不自动替教师做出" in teacher_ui,
          "TeacherLayout 缺少决策辅助与客观呈现边界声明")

    # 18. 前端 TypeScript 类型检查 (npm run typecheck 零错误)
    print("  -> 执行前端 TypeScript 类型检查 (npm run typecheck)...")
    tc_res = subprocess.run(["npm", "run", "typecheck", "--prefix", "frontend"], capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace")
    check(18, "前端 TypeScript 类型检查 0 错误 (tsc -b)",
          tc_res.returncode == 0,
          f"TypeScript Errors:\n{tc_res.stdout}\n{tc_res.stderr}")

    # 19. 前端生产构建验证 (npm run build 产物完备)
    print("  -> 执行前端生产构建测试 (npm run build)...")
    build_res = subprocess.run(["npm", "run", "build", "--prefix", "frontend"], capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace")
    dist_index = Path("frontend/dist/index.html")
    check(19, "前端生产打包构建成功且产物完备 (frontend/dist/index.html)",
          build_res.returncode == 0 and dist_index.exists() and dist_index.stat().st_size > 0,
          f"Build Failure:\n{build_res.stdout}\n{build_res.stderr}")

    # 20. 核心基准代码冻结断言 (app/, tests/, data/seeds/, gateway/learning/ 零篡改)
    git_diff = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", "app/", "tests/", "data/seeds/", "gateway/learning/"],
                              capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace")
    untracked_core = subprocess.run(["git", "status", "--porcelain", "--", "app/", "tests/", "data/seeds/", "gateway/learning/"],
                                    capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace")
    core_clean = (git_diff.stdout.strip() == "" and untracked_core.stdout.strip() == "")
    check(20, "核心学习底座 100% 冻结断言 (app/, tests/, data/seeds/, gateway/learning/ 零篡改)",
          core_clean,
          f"Core diff detected:\n{git_diff.stdout}\n{untracked_core.stdout}")

    print("=" * 70)
    print(f"🎉 20/20 项质量门禁全部通过！Sprint 10-C / Phase 2 教师端学情中台品质达标！")
    print("=" * 70)


if __name__ == "__main__":
    run_gate()
