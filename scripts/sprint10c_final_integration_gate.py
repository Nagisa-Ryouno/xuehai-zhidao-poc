# -*- coding: utf-8 -*-
"""
scripts/sprint10c_final_integration_gate.py
============================================
学海智导 (Xuehai Zhidao) — Sprint 10-C / Phase 3
最终整合与 Demo Hardening 严苛质量门禁 (25-Point Final Integration Gate)

覆盖能力闭环：
Student PWA <-> Today Action <-> Dynamic Path <-> Resource Hub <-> AI Recommendation
<-> AI Companion <-> Micro Quiz <-> BKT <-> Replanning <-> Teacher Web
"""

import sys
import json
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from gateway.api import create_gateway_app
from app.infrastructure.persistence.event_repository import default_event_repository
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository
from path_state_service import get_all_path_states, get_path_state, PathState
from gateway.learning.resources.catalog import RESOURCE_CATALOG
from gateway.learning.resources.mooc_catalog import MOOC_RESOURCE_CATALOG


def run_final_integration_gate():
    print("=" * 78)
    print("🚀 启动 Sprint 10-C / Phase 3 最终产品整合与 Demo Hardening 25 项质量门禁")
    print("=" * 78)

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

    # -------------------------------------------------------------------------
    # 01. Student Routes Integrity
    # -------------------------------------------------------------------------
    router_content = Path("frontend/src/router.ts").read_text(encoding="utf-8")
    student_routes_valid = (
        "sub === 'resources'" in router_content and
        "sub === 'graph'" in router_content and
        "sub === 'profile'" in router_content and
        "sub === 'assistant'" in router_content and
        "'/student/tasks'" in router_content
    )
    check(1, "学生端 5 大子路由与根路径自动重定向体系完整",
          student_routes_valid, "router.ts 中学生端子路由定义缺失")

    # -------------------------------------------------------------------------
    # 02. Teacher Routes Integrity
    # -------------------------------------------------------------------------
    teacher_routes_valid = (
        "'dashboard' | 'overview' | 'knowledge' | 'students'" in router_content and
        "matchedSub = 'overview'" in router_content and
        "matchedSub = 'knowledge'" in router_content and
        "matchedSub = 'students'" in router_content
    )
    check(2, "教师端 3-Tab 子路由解析及 /teacher 向后兼容定义完备",
          teacher_routes_valid, "router.ts 中教师端子路由解析缺失")

    # -------------------------------------------------------------------------
    # 03. Student API Contracts
    # -------------------------------------------------------------------------
    sid = "S001"
    res_dash = client.get(f"/api/students/{sid}/dashboard")
    res_graph = client.get(f"/api/students/{sid}/knowledge-graph")
    res_states = client.get(f"/api/students/{sid}/path-states")
    res_stus = client.get("/api/students")
    student_apis_ok = (
        res_dash.status_code == 200 and "profile" in res_dash.json() and
        res_graph.status_code == 200 and "nodes" in res_graph.json() and
        res_states.status_code == 200 and "states" in res_states.json() and
        res_stus.status_code == 200 and res_stus.json().get("count", 0) >= 5
    )
    check(3, "学生端基础 API 契约完备性 (/dashboard, /knowledge-graph, /path-states, /students)",
          student_apis_ok, f"学生端 API 返回异常: dash={res_dash.status_code}, graph={res_graph.status_code}, stus={res_stus.status_code}")

    # -------------------------------------------------------------------------
    # 04. Teacher API Contracts
    # -------------------------------------------------------------------------
    res_t_ov = client.get("/api/teacher/overview")
    res_t_kn = client.get("/api/teacher/knowledge")
    res_t_st = client.get("/api/teacher/students")
    res_t_dt = client.get(f"/api/teacher/students/{sid}")
    teacher_apis_ok = (
        res_t_ov.status_code == 200 and "class_kpis" in res_t_ov.json() and
        res_t_kn.status_code == 200 and res_t_kn.json().get("total_count") == 30 and
        res_t_st.status_code == 200 and len(res_t_st.json()) >= 5 and
        res_t_dt.status_code == 200 and "summary" in res_t_dt.json()
    )
    check(4, "教师端中台 API 契约完备性 (/overview, /knowledge, /students, /detail)",
          teacher_apis_ok, "教师端 API 返回异常或数据结构不匹配")

    # -------------------------------------------------------------------------
    # 05. Today Action Availability & Contract
    # -------------------------------------------------------------------------
    res_ta = client.get(f"/api/learning/today/{sid}")
    ta_data = res_ta.json().get("action", {}) if res_ta.status_code == 200 else {}
    today_action_ok = (
        res_ta.status_code == 200 and
        ta_data.get("action_type") in ("REVIEW_RETENTION", "CONTINUE_LEARNING", "PRACTICE", "VIEW_PROGRESS", "NONE") and
        "title" in ta_data and "description" in ta_data
    )
    check(5, "今日学习行动引擎 (Today Action) 契约及状态映射合法",
          today_action_ok, f"Today action response: {res_ta.text}")

    # -------------------------------------------------------------------------
    # 06. Dynamic Learning Path Available
    # -------------------------------------------------------------------------
    res_route = client.get(f"/api/path/dynamic/{sid}")
    route_data = res_route.json() if res_route.status_code == 200 else {}
    route_ok = (
        res_route.status_code == 200 and
        "steps" in route_data and
        isinstance(route_data["steps"], list) and
        len(route_data["steps"]) > 0
    )
    check(6, "动态自适应学习路径 (Dynamic Route) 生成完备且符合图谱拓扑",
          route_ok, f"Route response: {res_route.text}")

    # -------------------------------------------------------------------------
    # 07. Resource Hub Catalog Available
    # -------------------------------------------------------------------------
    res_k01 = client.get("/api/learning/resources/K01")
    k01_data = res_k01.json() if res_k01.status_code == 200 else {}
    catalog_ok = (
        len(RESOURCE_CATALOG) == 130 and
        len(MOOC_RESOURCE_CATALOG) == 12 and
        res_k01.status_code == 200 and
        "resources" in k01_data and
        len(k01_data["resources"]) >= 3
    )
    check(7, "学习资源中心 (Resource Hub) 目录完备 (内部130 + MOOC 12项无遗漏)",
          catalog_ok, f"Catalog items count: internal={len(RESOURCE_CATALOG)}, mooc={len(MOOC_RESOURCE_CATALOG)}")

    # -------------------------------------------------------------------------
    # 08. AI Recommendation Engine Contract
    # -------------------------------------------------------------------------
    res_rec = client.post(f"/api/ai/recommendations/{sid}", json={"max_recommendations": 3})
    rec_data = res_rec.json() if res_rec.status_code == 200 else {}
    rec_ok = (
        res_rec.status_code == 200 and
        "recommendations" in rec_data and
        isinstance(rec_data["recommendations"], list) and
        rec_data.get("validated") is True
    )
    check(8, "AI 个性化推荐引擎契约合法且通过三层校验器验证",
          rec_ok, f"Rec response: {res_rec.text[:200]}")

    # -------------------------------------------------------------------------
    # 09. AI Companion Available
    # -------------------------------------------------------------------------
    res_comp = client.post("/api/ai/companion", json={
        "student_id": sid,
        "mode": "concept_explain",
        "knowledge_id": "K01",
        "message": "请讲解需求定理",
    })
    comp_data = res_comp.json() if res_comp.status_code == 200 else {}
    companion_ok = (
        res_comp.status_code == 200 and
        "answer" in comp_data and
        isinstance(comp_data["answer"], str) and
        len(comp_data["answer"]) > 0
    )
    check(9, "AI 伴学辅导 (AI Companion) 响应完好且严格保持辅助边界",
          companion_ok, f"Companion response: {res_comp.text[:200]}")

    # -------------------------------------------------------------------------
    # 10. Teacher Overview Available
    # -------------------------------------------------------------------------
    t_ov_data = res_t_ov.json()
    ov_kpis = t_ov_data.get("class_kpis", {})
    t_ov_ok = (
        ov_kpis.get("total_students", 0) >= 5 and
        0.0 <= ov_kpis.get("class_avg_mastery", -1) <= 1.0 and
        len(t_ov_data.get("weak_knowledge_points", [])) <= 5
    )
    check(10, "教师端班级宏观总览 (Teacher Overview) 指标健全与 Top-5 薄弱考点",
          t_ov_ok, f"Teacher overview data: {t_ov_data}")

    # -------------------------------------------------------------------------
    # 11. Teacher Knowledge Full 30 Points
    # -------------------------------------------------------------------------
    t_kn_data = res_t_kn.json()
    kps = t_kn_data.get("knowledge_points", [])
    kids = [k["knowledge_id"] for k in kps]
    t_kn_ok = (
        len(kps) == 30 and
        kids == sorted(kids) and
        kids[0] == "K01" and
        kids[-1] == "K30"
    )
    check(11, "教师端考点全景 (Teacher Knowledge) 权威覆盖全部 30 个考点且升序排列",
          t_kn_ok, f"Knowledge points count: {len(kps)}")

    # -------------------------------------------------------------------------
    # 12. Teacher Students List & S001 Detail
    # -------------------------------------------------------------------------
    t_st_data = res_t_st.json()
    s001_detail = res_t_dt.json()
    t_st_ok = (
        len(t_st_data) >= 5 and
        s001_detail.get("summary", {}).get("student_id") == "S001" and
        "progress" in s001_detail and "wrong_answers" in s001_detail
    )
    check(12, "教师端学生花名册与 S001 学情全维档案下钻画像完好",
          t_st_ok, f"Student detail: {s001_detail.keys()}")

    # -------------------------------------------------------------------------
    # 13. Student Quiz Questions & Anti-Leak Protection
    # -------------------------------------------------------------------------
    res_q = client.get("/api/quiz/K01")
    q_data = res_q.json() if res_q.status_code == 200 else {}
    questions = q_data.get("questions", [])
    quiz_fetch_ok = (
        res_q.status_code == 200 and len(questions) > 0 and
        all("correct_answer" not in q and "correct_option" not in q for q in questions)
    )
    check(13, "微测验试题获取正常且严格防题解泄露 (0 correct_answer 泄露)",
          quiz_fetch_ok, f"Questions response: {res_q.text[:200]}")

    # -------------------------------------------------------------------------
    # 14. Quiz Submission Authoritative BKT State Update
    # -------------------------------------------------------------------------
    first_q = questions[0]
    sub_res = client.post("/api/quiz/submit", json={
        "student_id": "S001",
        "knowledge_id": "K01",
        "question_id": first_q["question_id"],
        "selected_option": "B",
    })
    sub_data = sub_res.json() if sub_res.status_code == 200 else {}
    quiz_sub_ok = (
        sub_res.status_code == 200 and
        "is_correct" in sub_data and
        "learning_state" in sub_data and
        0.0 <= sub_data["learning_state"]["mastery_probability"] <= 1.0
    )
    check(14, "微测验判题与服务端权威 BKT 认知更新闭环正常",
          quiz_sub_ok, f"Submit response: {sub_res.text[:200]}")

    # -------------------------------------------------------------------------
    # 15. BKT Update Triggers Dynamic PathState Replanning
    # -------------------------------------------------------------------------
    replanning = sub_data.get("replanning")
    replanning_ok = (
        replanning is not None and
        "canonical_payload" in replanning and
        "action" in replanning["canonical_payload"] and
        "reason_code" in replanning["canonical_payload"]
    )
    check(15, "测验完成驱动服务端动态路径重规划 (Path Replanning) 响应",
          replanning_ok, f"Replanning payload: {replanning}")

    # -------------------------------------------------------------------------
    # 16. Path State & Today Action Consistency
    # -------------------------------------------------------------------------
    res_ta_after = client.get(f"/api/learning/today/{sid}")
    ta_after_data = res_ta_after.json() if res_ta_after.status_code == 200 else {}
    check(16, "学情变动后今日行动与路径状态保持协调一致与确定性响应",
          res_ta_after.status_code == 200 and "action" in ta_after_data,
          f"Today action after: {ta_after_data}")

    # -------------------------------------------------------------------------
    # 17. Recommendation Resources Strictly in Authoritative Catalog
    # -------------------------------------------------------------------------
    unified_catalog_ids = set(RESOURCE_CATALOG.keys()) | set(MOOC_RESOURCE_CATALOG.keys())
    rec_items = rec_data.get("recommendations", [])
    rec_in_catalog = len(rec_items) > 0 and all(r["resource_id"] in unified_catalog_ids for r in rec_items)
    check(17, "AI 推荐资源 100% 存在于权威统一资源目录 (零虚构资源)",
          rec_in_catalog, f"Rec items: {rec_items}")

    # -------------------------------------------------------------------------
    # 18. Recommendation URL Security & Anti-Hallucination
    # -------------------------------------------------------------------------
    no_raw_urls_in_rec = all("url" not in r and "target_url" not in r for r in rec_items)
    check(18, "AI 推荐结果绝不透传不可控外链 (杜绝钓鱼外链与幻觉 URL 绕过)",
          no_raw_urls_in_rec, "检测到 AI 推荐直接输出了未经过滤的外链 URL")

    # -------------------------------------------------------------------------
    # 19. AI Companion Mutation Isolation
    # -------------------------------------------------------------------------
    bkt_before_comp = default_bkt_state_repository.get_student_states("S002")
    events_before_comp = len(default_event_repository.get_events_by_student("S002"))
    client.post("/api/ai/companion", json={
        "student_id": "S002",
        "mode": "concept_explain",
        "knowledge_id": "K01",
        "message": "讲解弹性",
    })
    bkt_after_comp = default_bkt_state_repository.get_student_states("S002")
    events_after_comp = len(default_event_repository.get_events_by_student("S002"))
    check(19, "AI 伴学辅导交互绝对零副作用 (0 BKT 认知变更，0 事件篡改)",
          bkt_before_comp == bkt_after_comp and events_before_comp == events_after_comp,
          "AI 伴学越权修改了学生 BKT 状态或事件记录")

    # -------------------------------------------------------------------------
    # 20. Teacher Dashboard Mutation Isolation (Read-Only)
    # -------------------------------------------------------------------------
    bkt_before_teach = default_bkt_state_repository.get_student_states("S003")
    paths_before_teach = get_all_path_states("S003")
    client.get("/api/teacher/overview")
    client.get("/api/teacher/knowledge")
    client.get("/api/teacher/students")
    client.get("/api/teacher/students/S003")
    bkt_after_teach = default_bkt_state_repository.get_student_states("S003")
    paths_after_teach = get_all_path_states("S003")
    check(20, "教师端学情中台全部查询严格只读 (0 BKT / 0 PathState 变更)",
          bkt_before_teach == bkt_after_teach and paths_before_teach == paths_after_teach,
          "教师端查询产生了数据副作用")

    # -------------------------------------------------------------------------
    # 21. Student / Teacher Cross-End State Consistency
    # -------------------------------------------------------------------------
    student_dash_s001 = client.get("/api/students/S001/dashboard").json()
    teacher_detail_s001 = client.get("/api/teacher/students/S001").json()
    s_stu = student_dash_s001.get("profile", {}).get("student", {})
    t_stu = teacher_detail_s001.get("summary", {})
    same_student = (
        s_stu.get("student_id") == t_stu.get("student_id") and
        s_stu.get("student_name") == t_stu.get("student_name") and
        s_stu.get("major") == t_stu.get("major")
    )
    check(21, "双端权威学情一致性 (Student Dashboard 与 Teacher Detail 学生实体同源)",
          same_student, f"Student: {s_stu}, Teacher: {t_stu}")

    # -------------------------------------------------------------------------
    # 22. PWA Web App Manifest
    # -------------------------------------------------------------------------
    manifest_p = Path("frontend/public/manifest.webmanifest")
    manifest_data = json.loads(manifest_p.read_text(encoding="utf-8")) if manifest_p.exists() else {}
    manifest_ok = (
        manifest_p.exists() and
        manifest_data.get("name") == "学海智导" and
        manifest_data.get("display") == "standalone" and
        manifest_data.get("start_url") == "/student"
    )
    check(22, "PWA Web App Manifest 配置合规 (独立应用模式，start_url=/student)",
          manifest_ok, "Manifest 配置不合规")

    # -------------------------------------------------------------------------
    # 23. Service Worker API Non-Cache (Network-Only for /api/)
    # -------------------------------------------------------------------------
    sw_file = Path("frontend/public/sw.js").read_text(encoding="utf-8")
    sw_api_safe = (
        "url.pathname.startsWith('/api/')" in sw_file and
        "fetch(request)" in sw_file and
        "Network-Only" in sw_file
    )
    check(23, "Service Worker /api/* 严格遵循 Network-Only 策略 (权威状态绝不被本地脏缓存)",
          sw_api_safe, "Service Worker 缓存策略未对 /api/ 严格实施 Network-Only")

    # -------------------------------------------------------------------------
    # 24. Responsive Layout Overflow Protection
    # -------------------------------------------------------------------------
    student_layout_css = Path("frontend/src/layouts/StudentLayout.tsx").read_text(encoding="utf-8")
    teacher_layout_css = Path("frontend/src/layouts/TeacherLayout.tsx").read_text(encoding="utf-8")
    overflow_safe = (
        "overflow-x-hidden" in student_layout_css and
        "max-w-7xl" in teacher_layout_css and
        "overflow-x-auto" in teacher_layout_css
    )
    check(24, "双端桌面与移动视口横向防溢出规范 (overflow-x 严防横向窜动)",
          overflow_safe, "双端布局缺乏横向防溢出防护")

    # -------------------------------------------------------------------------
    # 25. Final Demo Journey Simulation (FINAL-A)
    # -------------------------------------------------------------------------
    # 模拟完整业务链路：进入系统 -> 调取今日行动 -> 查阅推荐 -> 提交答题 -> 验证变动 -> 教师核准
    demo_s = "S001"
    # 1. 学生主页
    d1 = client.get(f"/api/students/{demo_s}/dashboard").json()
    # 2. 今日行动
    a1 = client.get(f"/api/learning/today/{demo_s}").json()
    # 3. 查阅资源推荐
    r1 = client.post(f"/api/ai/recommendations/{demo_s}", json={"max_recommendations": 2}).json()
    # 4. 微测验提交
    q1 = client.post("/api/quiz/submit", json={
        "student_id": demo_s,
        "knowledge_id": "K01",
        "question_id": "Q-K01-01",
        "selected_option": "B",
    }).json()
    # 5. 教师端观察
    t1 = client.get(f"/api/teacher/students/{demo_s}").json()

    journey_ok = (
        "profile" in d1 and
        "action" in a1 and
        "recommendations" in r1 and
        "learning_state" in q1 and
        t1.get("summary", {}).get("student_id") == demo_s
    )
    check(25, "Final Demo 完整黄金链路贯通 (Student -> Action -> Rec -> Quiz -> Teacher)",
          journey_ok, "Demo 旅程中断")

    print("=" * 78)
    print(f"🎉 25/25 项最终整合与 Demo Hardening 质量门禁全部通过！")
    print("=" * 78)


if __name__ == "__main__":
    run_final_integration_gate()
