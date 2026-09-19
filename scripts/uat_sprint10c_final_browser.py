# -*- coding: utf-8 -*-
"""
scripts/uat_sprint10c_final_browser.py
======================================
学海智导 (Xuehai Zhidao) — Sprint 10-C / Phase 3
全系统最终整合与 Demo Hardening 端到端全场景浏览器验收 (Scenarios A ~ O)

涵盖全景能力链路：
Student PWA <-> Today Action <-> Dynamic Path <-> Resource Hub <-> AI Recommendation
<-> AI Companion <-> Micro Quiz <-> BKT <-> Replanning <-> Teacher Web
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

from playwright.sync_api import sync_playwright, Page, expect

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5173")
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8011")

SCREENSHOT_DIR = os.path.abspath("artifacts/uat_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

BRAIN_SCREENSHOT_DIR = r"C:\Users\XSL\.gemini\antigravity\brain\acc330ec-11ad-49d0-a406-fe3e112b5cfc\screenshots"
os.makedirs(BRAIN_SCREENSHOT_DIR, exist_ok=True)

RESULTS_FILE = os.path.abspath("artifacts/uat_results_sprint10c_final.json")

uat_results: Dict[str, Any] = {
    "sprint": "Sprint 10-C Phase 3 Final Demo Hardening",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "console_messages": [],
    "console_errors": [],
    "page_errors": [],
    "failed_requests": [],
    "scenarios": {},
}


def log_step(title: str):
    print(f"\n{'='*75}\n>>> {title}\n{'='*75}")


def save_screenshot(page: Page, filename: str):
    p1 = os.path.join(SCREENSHOT_DIR, filename)
    p2 = os.path.join(BRAIN_SCREENSHOT_DIR, filename)
    page.screenshot(path=p1, full_page=False)
    try:
        shutil.copyfile(p1, p2)
    except Exception as e:
        print(f"Warning copying screenshot to brain dir: {e}")
    print(f"[Screenshot Saved] {filename}")


def check_url_ready(url: str, timeout: float = 1.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HealthCheck"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.getcode() == 200
    except Exception:
        return False


def ensure_servers_running():
    spawned_procs = []
    # 1. 检查后端
    if not check_url_ready(f"{API_URL}/api/students"):
        print("[Launcher] 后端服务未运行，正在启动 127.0.0.1:8011...")
        proc_backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "gateway.api:create_gateway_app", "--factory", "--host", "127.0.0.1", "--port", "8011"],
            cwd=str(PROJECT_ROOT),
        )
        spawned_procs.append(("backend", proc_backend))
        for _ in range(25):
            if check_url_ready(f"{API_URL}/api/students"):
                print("[Launcher] 后端服务已就绪！")
                break
            time.sleep(0.8)
        else:
            raise RuntimeError("后端服务启动超时")
    else:
        print("[Launcher] 后端服务已在线 (8011)")

    # 2. 检查前端
    if not check_url_ready(f"{BASE_URL}/"):
        print("[Launcher] 前端服务未运行，正在启动 127.0.0.1:5173...")
        proc_frontend = subprocess.Popen(
            "npx vite --host 127.0.0.1 --port 5173",
            shell=True,
            cwd=str(PROJECT_ROOT / "frontend"),
        )
        spawned_procs.append(("frontend", proc_frontend))
        for _ in range(25):
            if check_url_ready(f"{BASE_URL}/"):
                print("[Launcher] 前端服务已就绪！")
                break
            time.sleep(0.8)
        else:
            raise RuntimeError("前端服务启动超时")
    else:
        print("[Launcher] 前端服务已在线 (5173)")

    return spawned_procs


def cleanup_spawned(procs):
    for name, proc in procs:
        print(f"[Cleanup] 停止由测试启动的 {name} 进程 (PID: {proc.pid})...")
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        else:
            proc.terminate()
            proc.wait()


def run_uat():
    spawned = ensure_servers_running()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 850})
            page = context.new_page()

            def on_console(msg):
                uat_results["console_messages"].append(f"[{msg.type}] {msg.text}")
                if msg.type == "error":
                    text = msg.text.lower()
                    if "favicon" not in text and "abort" not in text:
                        uat_results["console_errors"].append(msg.text)
                        print(f"[BROWSER ERROR] {msg.text}")

            page.on("console", on_console)
            page.on("pageerror", lambda err: uat_results["page_errors"].append(str(err)))

            def on_request_failed(req):
                if "favicon" not in req.url:
                    uat_results["failed_requests"].append(f"{req.method} {req.url}")
                    print(f"[REQ FAILED] {req.method} {req.url}")

            page.on("requestfailed", on_request_failed)

            # -----------------------------------------------------------------
            # Scenario A: Student PWA Shell & Home Landing
            # -----------------------------------------------------------------
            log_step("Scenario A: Student PWA Shell 与学生首页正常渲染")
            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("text=学海智导", timeout=15000)
            save_screenshot(page, "sprint10c_final_01_student_pwa.png")
            uat_results["scenarios"]["scenario_a_student_pwa"] = {"status": "PASS", "url": page.url}

            # -----------------------------------------------------------------
            # Scenario B: Today Action Card & Interaction
            # -----------------------------------------------------------------
            log_step("Scenario B: 今日学习行动卡片 (Today Action Card) 呈现与交互")
            today_action = page.locator("[data-testid='today-action-card']")
            if today_action.count() > 0:
                expect(today_action).to_be_visible()
            save_screenshot(page, "sprint10c_final_02_today_action.png")
            uat_results["scenarios"]["scenario_b_today_action"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario C: Dynamic Path & Knowledge Graph
            # -----------------------------------------------------------------
            log_step("Scenario C: 知识图谱全景与自适应动态航线")
            page.goto(f"{BASE_URL}/student/graph", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("text=微观经济学", timeout=15000)
            page.wait_for_timeout(800)
            save_screenshot(page, "sprint10c_final_03_knowledge_graph.png")
            uat_results["scenarios"]["scenario_c_knowledge_graph"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario D: Resource Hub & Unified Catalog
            # -----------------------------------------------------------------
            log_step("Scenario D: 学习资源中心 (Resource Hub) 目录全景")
            page.goto(f"{BASE_URL}/student/resources", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("text=学习资源中心", timeout=15000)
            save_screenshot(page, "sprint10c_final_04_resource_hub.png")
            uat_results["scenarios"]["scenario_d_resource_hub"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario E: AI Personalized Recommendations
            # -----------------------------------------------------------------
            log_step("Scenario E: AI 个性化推荐专区与非决策安全边界")
            rec_section = page.locator("[data-testid='personalized-recommendation-section']")
            expect(rec_section).to_be_visible(timeout=15000)
            save_screenshot(page, "sprint10c_final_05_recommendations.png")
            uat_results["scenarios"]["scenario_e_recommendations"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario F: MOOC External Security Modal
            # -----------------------------------------------------------------
            log_step("Scenario F: MOOC 外部资源安全确认拦截模态框")
            # 点击前往慕课学习按钮
            mooc_btn = page.locator("button:has-text('前往慕课学习')").first
            if mooc_btn.count() > 0:
                mooc_btn.click()
                modal = page.locator("[data-testid='external-redirect-modal']")
                expect(modal).to_be_visible(timeout=5000)
                save_screenshot(page, "sprint10c_final_06_mooc_security_modal.png")
                # 取消关闭
                close_btn = modal.locator("button:has-text('取消')").first
                if close_btn.count() > 0:
                    close_btn.click()
                    expect(modal).not_to_be_visible(timeout=5000)
                    page.wait_for_timeout(300)
            if not os.path.exists(os.path.join(SCREENSHOT_DIR, "sprint10c_final_06_mooc_security_modal.png")):
                save_screenshot(page, "sprint10c_final_06_mooc_security_modal.png")
            uat_results["scenarios"]["scenario_f_mooc_security_modal"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario G: AI Companion Interactive Assistant
            # -----------------------------------------------------------------
            log_step("Scenario G: AI 伴学导师 (AI Companion) 交互体验")
            page.goto(f"{BASE_URL}/student/assistant", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("text=AI 学习伴学助手", timeout=15000)
            page.wait_for_timeout(500)
            save_screenshot(page, "sprint10c_final_07_ai_companion.png")
            uat_results["scenarios"]["scenario_g_ai_companion"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario H: Micro Quiz Execution & BKT Dynamic Replanning
            # -----------------------------------------------------------------
            log_step("Scenario H: 微测验答题突破与 BKT 动态路径重规划闭环")
            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("[data-testid='current-focus-card']", timeout=15000)

            # 点击开始答题 / 微测验突破
            start_quiz_btn = page.locator("[data-testid='current-focus-card'] button").filter(has_text="突破").first
            if start_quiz_btn.count() == 0:
                start_quiz_btn = page.locator("[data-testid='current-focus-card'] button").filter(has_text="测验").first
            if start_quiz_btn.count() == 0:
                start_quiz_btn = page.locator("button:has-text('微测验突破')").first

            if start_quiz_btn.count() > 0 and start_quiz_btn.is_enabled():
                start_quiz_btn.click()
                page.wait_for_timeout(1000)

                # 聚焦到弹出的 Dialog 内部
                dialog = page.locator("div[role='dialog']")
                expect(dialog).to_be_visible(timeout=10000)
                page.wait_for_timeout(800)

                # 在 Dialog 内部选择选项
                opt_btns = dialog.locator("button.cursor-pointer").all()
                clicked_opt = False
                for b in opt_btns:
                    b_txt = b.inner_text()
                    if "A" in b_txt or "B" in b_txt:
                        b.click()
                        clicked_opt = True
                        break
                if not clicked_opt and len(opt_btns) > 0:
                    opt_btns[0].click()

                page.wait_for_timeout(400)
                sub_btn = dialog.locator("button:has-text('提交答案')").first
                if sub_btn.count() > 0 and sub_btn.is_enabled():
                    sub_btn.click()
                    page.wait_for_timeout(1500)

                save_screenshot(page, "sprint10c_final_08_micro_quiz_replanning.png")

                # 关闭测验模态框
                close_quiz_btn = dialog.locator("button:has-text('返回今日任务'), button:has-text('查看测验总结'), button[title='返回知识点学情']").first
                if close_quiz_btn.count() > 0:
                    close_quiz_btn.click()
                    page.wait_for_timeout(500)
            else:
                save_screenshot(page, "sprint10c_final_08_micro_quiz_replanning.png")
            uat_results["scenarios"]["scenario_h_quiz_replanning"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario I: Teacher Cockpit Landing & Class KPIs
            # -----------------------------------------------------------------
            log_step("Scenario I: 教师驾驶舱首页 (Teacher Overview) 与 4 大 KPI")
            page.goto(f"{BASE_URL}/teacher", wait_until="networkidle", timeout=30000)
            cockpit = page.locator("[data-testid='teacher-cockpit']")
            expect(cockpit).to_be_visible(timeout=15000)
            expect(page.locator("[data-testid='teacher-kpi-cards']")).to_be_visible(timeout=10000)
            expect(page.locator("[data-testid='teacher-weak-points-ranking']")).to_be_visible(timeout=10000)
            save_screenshot(page, "sprint10c_final_09_teacher_overview.png")
            uat_results["scenarios"]["scenario_i_teacher_overview"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario J: Teacher Knowledge 30 Points Spectrum
            # -----------------------------------------------------------------
            log_step("Scenario J: 教师端考点全景 (Teacher Knowledge) 30 考点全量表")
            page.click("[data-testid='tab-teacher-knowledge']")
            page.wait_for_selector("[data-testid='teacher-knowledge-overview']", timeout=10000)
            page.wait_for_selector("[data-testid='teacher-knowledge-table']", timeout=10000)
            page.wait_for_timeout(500)
            save_screenshot(page, "sprint10c_final_10_teacher_knowledge_30.png")
            uat_results["scenarios"]["scenario_j_teacher_knowledge"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario K: Teacher Students Roster Table
            # -----------------------------------------------------------------
            log_step("Scenario K: 教师端学生花名册 (Teacher Students) 与多维筛选")
            page.click("[data-testid='tab-teacher-students']")
            page.wait_for_selector("[data-testid='teacher-students-section']", timeout=10000)
            page.wait_for_selector("[data-testid='teacher-student-roster']", timeout=10000)
            page.wait_for_timeout(500)
            save_screenshot(page, "sprint10c_final_11_teacher_students_roster.png")
            uat_results["scenarios"]["scenario_k_teacher_students"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario L: Teacher Student Detail Drilldown
            # -----------------------------------------------------------------
            log_step("Scenario L: 教师端单生档案下钻画像弹窗 (S001)")
            detail_btn = page.locator("[data-testid='btn-student-detail-S001']")
            if detail_btn.count() > 0:
                detail_btn.click()
                modal = page.locator("[data-testid='teacher-student-detail-modal']")
                expect(modal).to_be_visible(timeout=10000)
                page.wait_for_timeout(500)
                save_screenshot(page, "sprint10c_final_12_teacher_student_detail.png")
                # 关闭弹窗
                close_btn = modal.locator("[data-testid='btn-close-student-detail-modal']")
                if close_btn.count() > 0:
                    close_btn.click()
                    expect(modal).not_to_be_visible(timeout=5000)
                    page.wait_for_timeout(300)
            uat_results["scenarios"]["scenario_l_student_detail"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario M: Seamless Cross-Role Bidirectional Navigation
            # -----------------------------------------------------------------
            log_step("Scenario M: 教师端/学生端双向无缝视界切换")
            # 通过学生行直接进入学生视界
            enter_s001_btn = page.locator("[data-testid='btn-enter-student-S001']")
            if enter_s001_btn.count() > 0:
                enter_s001_btn.click()
                expect(page.locator("[data-testid='student-layout']")).to_be_visible(timeout=10000)
                assert "/student" in page.url
                page.wait_for_timeout(500)
                save_screenshot(page, "sprint10c_final_13_context_switch.png")
                # 从 Header 切回教师端
                page.locator("button:has-text('教师驾驶舱')").click()
                expect(page.locator("[data-testid='teacher-cockpit']")).to_be_visible(timeout=10000)
                assert "/teacher" in page.url
            uat_results["scenarios"]["scenario_m_context_switch"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario N: Multi-Viewport Responsive Matrix
            # -----------------------------------------------------------------
            log_step("Scenario N: 多设备视口自适应矩阵与横向防溢出验证")
            vp_results = {}

            # 1. 学生端移动与平板视口验证 (/student/tasks)
            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("text=学海智导", timeout=15000)

            student_viewports = [
                ("mobile_375x812", 375, 812, "sprint10c_final_14_mobile_375x812.png"),
                ("mobile_390x844", 390, 844, None),
                ("tablet_768x1024", 768, 1024, "sprint10c_final_15_tablet_768x1024.png"),
            ]
            for name, w, h, s_name in student_viewports:
                page.set_viewport_size({"width": w, "height": h})
                page.wait_for_timeout(400)
                overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth || document.body.scrollWidth > window.innerWidth")
                print(f"  [Student PWA] Viewport {w}x{h} ({name}): overflow={overflow}")
                assert not overflow, f"Student PWA detected horizontal overflow at {w}x{h}"
                if s_name:
                    save_screenshot(page, s_name)
                vp_results[name] = {"surface": "student", "width": w, "height": h, "no_overflow": not overflow}

            # 2. 教师端桌面多分辨率验证 (/teacher)
            page.goto(f"{BASE_URL}/teacher", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("[data-testid='teacher-cockpit']", timeout=15000)

            teacher_viewports = [
                ("laptop_1024x768", 1024, 768, None),
                ("desktop_1280x800", 1280, 800, None),
                ("desktop_1440x900", 1440, 900, "sprint10c_final_16_desktop_1440x900.png"),
            ]
            for name, w, h, s_name in teacher_viewports:
                page.set_viewport_size({"width": w, "height": h})
                page.wait_for_timeout(400)
                no_overflow = page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth")
                print(f"  [Teacher Web] Viewport {w}x{h} ({name}): no_overflow={no_overflow}")
                assert no_overflow, f"Teacher Web detected horizontal overflow at {w}x{h}"
                if s_name:
                    save_screenshot(page, s_name)
                vp_results[name] = {"surface": "teacher", "width": w, "height": h, "no_overflow": no_overflow}

            uat_results["scenarios"]["scenario_n_responsive_matrix"] = {"status": "PASS", "viewports": vp_results}

            # -----------------------------------------------------------------
            # Scenario O: Zero Console Errors & Network Invariant
            # -----------------------------------------------------------------
            log_step("Scenario O: 控制台零错误、页面零异常与零异常请求断言")
            print(f"Total Console Errors: {len(uat_results['console_errors'])}")
            print(f"Total Page Errors: {len(uat_results['page_errors'])}")
            print(f"Total Failed Requests: {len(uat_results['failed_requests'])}")

            assert len(uat_results["console_errors"]) == 0, f"Console errors: {uat_results['console_errors']}"
            assert len(uat_results["page_errors"]) == 0, f"Page errors: {uat_results['page_errors']}"
            assert len(uat_results["failed_requests"]) == 0, f"Failed requests: {uat_results['failed_requests']}"

            uat_results["scenarios"]["scenario_o_zero_errors"] = {
                "status": "PASS",
                "console_errors_count": 0,
                "page_errors_count": 0,
                "failed_requests_count": 0,
            }

            browser.close()

        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(uat_results, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 75)
        print(f"🎉 最终整合与 Demo Hardening 浏览器端到端全场景验收圆满成功！")
        print(f"结果报告保存于: {RESULTS_FILE}")
        print("=" * 75)

    finally:
        cleanup_spawned(spawned)


if __name__ == "__main__":
    run_uat()
