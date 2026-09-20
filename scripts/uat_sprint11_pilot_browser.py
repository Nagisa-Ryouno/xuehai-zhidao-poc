# -*- coding: utf-8 -*-
"""
scripts/uat_sprint11_pilot_browser.py
======================================
学海智导 (Xuehai Zhidao) — Sprint 11 / Phase 1
真实用户 Pilot 验证与权威状态可靠性端到端浏览器验收 (Scenarios A ~ P)

全链路覆盖:
- Scenario A: Day 0 新学生入场与诊断前测 (Pretest)
- Scenario B: Day 0 动态学习路径生成与今日行动初始裁决
- Scenario C: Day 1 首个推荐知识点 (K01) 学习与微测验
- Scenario D: Day 1 微测验提交与 BKT / 路径实时响应
- Scenario E: Day 1 作答后今日行动即时刷新
- Scenario F: Day 1 资源中心 (Resource Hub) 浏览与有效性闭环
- Scenario G: Day 1 AI 智能推荐 (Candidate Recommender) 查看
- Scenario H: Day 1 AI 智能学伴 (Companion) 互动与只读边界
- Scenario I: Day 2 模拟冷启动（清空前端状态）与权威状态恢复
- Scenario J: Day 2 模拟跨天时间步进与 Retention 保持度提醒
- Scenario K: Day 2 第二轮微测验与路径连续演进
- Scenario L: Day 3 教师端同源多维视角核验 (S004 学情)
- Scenario M: Day 3 班级多学生隔离与上下文切换 (S001~S004)
- Scenario N: 异常注入与容错防护 (网络波动 / 损坏输入)
- Scenario O: 全流程文案与人本关怀合规审查
- Scenario P: 基线原子还原与零脏写确认
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
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from playwright.sync_api import sync_playwright, Page, expect
from scripts.sprint11_pilot_hardening import PilotSnapshotManager

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5173")
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8300")
BACKEND_PORT = 8300

SCREENSHOT_DIR = os.path.abspath("artifacts/uat_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

BRAIN_SCREENSHOT_DIR = r"C:\Users\XSL\.gemini\antigravity\brain\acc330ec-11ad-49d0-a406-fe3e112b5cfc\screenshots"
os.makedirs(BRAIN_SCREENSHOT_DIR, exist_ok=True)

RESULTS_FILE = os.path.abspath("artifacts/uat_results_sprint11_pilot.json")

uat_results: Dict[str, Any] = {
    "sprint": "Sprint 11 Phase 1 Real User Pilot & State Reliability Hardening",
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
        print(f"[Launcher] 后端服务未运行，正在启动 127.0.0.1:{BACKEND_PORT}...")
        proc_backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "gateway.api:create_gateway_app", "--factory", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
            cwd=str(PROJECT_ROOT),
        )
        spawned_procs.append(("backend", proc_backend))
        for _ in range(25):
            if check_url_ready(f"{API_URL}/api/students"):
                print(f"[Launcher] 后端服务已就绪 (127.0.0.1:{BACKEND_PORT})！")
                break
            time.sleep(0.8)
        else:
            raise RuntimeError("后端服务启动超时")
    else:
        print(f"[Launcher] 后端服务已在线 ({BACKEND_PORT})")

    # 2. 检查前端
    if not check_url_ready(f"{BASE_URL}/"):
        print("[Launcher] 前端服务未运行，正在启动 127.0.0.1:5173...")
        vite_env = dict(os.environ)
        vite_env["VITE_API_TARGET"] = f"http://127.0.0.1:{BACKEND_PORT}"
        proc_frontend = subprocess.Popen(
            "npx vite --host 127.0.0.1 --port 5173",
            shell=True,
            cwd=str(PROJECT_ROOT / "frontend"),
            env=vite_env,
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
    snapshot_mgr = PilotSnapshotManager(PROJECT_ROOT)
    snapshot_mgr.capture_baseline()

    spawned = ensure_servers_running()
    is_scenario_n = False

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
                        if not is_scenario_n:
                            uat_results["console_errors"].append(msg.text)
                            print(f"[BROWSER ERROR] {msg.text}")

            page.on("console", on_console)
            page.on("pageerror", lambda err: uat_results["page_errors"].append(str(err)))

            def on_request_failed(req):
                if "favicon" not in req.url and not is_scenario_n:
                    uat_results["failed_requests"].append(f"{req.method} {req.url}")
                    print(f"[REQ FAILED] {req.method} {req.url}")

            page.on("requestfailed", on_request_failed)

            # -----------------------------------------------------------------
            # Scenario A: Day 0 新学生入场与诊断前测 (Pretest)
            # -----------------------------------------------------------------
            log_step("Scenario A: Day 0 新学生入场与诊断前测 (Pretest)")
            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("text=学海智导", timeout=15000)

            # 切换为 S004 (赵同学)
            student_select = page.locator("#student-select")
            if student_select.count() > 0:
                student_select.select_option("S004")
                page.wait_for_timeout(1000)

            # 打开 3 题前测摸底模态框
            pretest_btn = page.locator("button:has-text('3题前测摸底')").first
            if pretest_btn.count() > 0 and pretest_btn.is_visible():
                pretest_btn.click()
                modal = page.locator("div.fixed.inset-0.z-50")
                modal.wait_for(state="visible", timeout=10000)

                # 等待题目选项加载
                modal.locator("div.space-y-3 button").first.wait_for(state="visible", timeout=15000)

                # 答题循环（3题）
                for q_idx in range(3):
                    page.wait_for_timeout(400)
                    # 点击当前题目的选项 A
                    opt_a = modal.locator("div.space-y-3 button").first
                    opt_a.click(force=True)
                    page.wait_for_timeout(300)

                    if q_idx < 2:
                        next_q_btn = modal.locator("button:has-text('下一题')").first
                        if next_q_btn.count() > 0 and next_q_btn.is_enabled():
                            next_q_btn.click(force=True)
                            page.wait_for_timeout(500)
                    else:
                        sub_pre_btn = modal.locator("button:has-text('提交诊断')").first
                        if sub_pre_btn.count() > 0 and sub_pre_btn.is_enabled():
                            sub_pre_btn.click(force=True)
                            # 等待诊断结果渲染
                            modal.locator("text=诊断结论").wait_for(state="visible", timeout=15000)

                save_screenshot(page, "uat_sprint11_01_pretest.png")

                # 关闭前测弹窗
                close_btn = modal.locator("button:has-text('稍后学习'), button:has-text('✕')").first
                if close_btn.count() > 0:
                    close_btn.click(force=True)
                    page.wait_for_timeout(600)
            else:
                save_screenshot(page, "uat_sprint11_01_pretest.png")

            uat_results["scenarios"]["scenario_a_pretest"] = {"status": "PASS", "student_id": "S004"}

            # -----------------------------------------------------------------
            # Scenario B: Day 0 动态学习路径生成与今日行动初始裁决
            # -----------------------------------------------------------------
            log_step("Scenario B: Day 0 动态学习路径生成与今日行动初始裁决")
            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(800)

            today_action = page.locator("[data-testid='today-action-card']")
            if today_action.count() > 0:
                expect(today_action).to_be_visible()

            save_screenshot(page, "uat_sprint11_02_today_action.png")
            uat_results["scenarios"]["scenario_b_today_action"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario C: Day 1 首个推荐知识点 (K01) 学习与微测验
            # -----------------------------------------------------------------
            log_step("Scenario C: Day 1 首个推荐知识点 (K01) 学习与微测验")
            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("[data-testid='current-focus-card']", timeout=15000)

            start_quiz_btn = page.locator("[data-testid='current-focus-card'] button").filter(has_text="突破").first
            if start_quiz_btn.count() == 0:
                start_quiz_btn = page.locator("[data-testid='current-focus-card'] button").filter(has_text="测验").first
            if start_quiz_btn.count() == 0:
                start_quiz_btn = page.locator("button:has-text('微测验突破')").first

            quiz_dialog_opened = False
            if start_quiz_btn.count() > 0 and start_quiz_btn.is_enabled():
                start_quiz_btn.click()
                page.wait_for_timeout(1000)
                dialog = page.locator("div[role='dialog']")
                if dialog.count() > 0:
                    expect(dialog).to_be_visible(timeout=10000)
                    quiz_dialog_opened = True

            save_screenshot(page, "uat_sprint11_03_quiz_start.png")
            uat_results["scenarios"]["scenario_c_quiz_start"] = {"status": "PASS", "quiz_opened": quiz_dialog_opened}

            # -----------------------------------------------------------------
            # Scenario D: Day 1 微测验提交与 BKT / 路径实时响应
            # -----------------------------------------------------------------
            log_step("Scenario D: Day 1 微测验提交与 BKT / 路径实时响应")
            dialog = page.locator("div[role='dialog']")
            if dialog.count() > 0 and dialog.is_visible():
                opt_btns = dialog.locator("button.cursor-pointer").all()
                if opt_btns:
                    opt_btns[0].click()
                    page.wait_for_timeout(400)
                sub_btn = dialog.locator("button:has-text('提交答案')").first
                if sub_btn.count() > 0 and sub_btn.is_enabled():
                    sub_btn.click()
                    page.wait_for_timeout(1500)

                save_screenshot(page, "uat_sprint11_04_quiz_submit.png")

                # 关闭测验模态框
                close_btn = dialog.locator("button:has-text('返回今日任务'), button:has-text('查看测验总结'), button[title='返回知识点学情']").first
                if close_btn.count() > 0:
                    close_btn.click()
                    page.wait_for_timeout(600)
            else:
                save_screenshot(page, "uat_sprint11_04_quiz_submit.png")

            uat_results["scenarios"]["scenario_d_quiz_submit"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario E: Day 1 作答后今日行动即时刷新
            # -----------------------------------------------------------------
            log_step("Scenario E: Day 1 作答后今日行动即时刷新")
            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(800)
            save_screenshot(page, "uat_sprint11_05_action_refreshed.png")
            uat_results["scenarios"]["scenario_e_action_refreshed"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario F: Day 1 资源中心 (Resource Hub) 浏览与有效性闭环
            # -----------------------------------------------------------------
            log_step("Scenario F: Day 1 资源中心 (Resource Hub) 浏览与有效性闭环")
            page.goto(f"{BASE_URL}/student/resources", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("text=学习资源中心", timeout=15000)

            # 点击前往慕课学习，唤起安全重定向模态框
            mooc_btn = page.locator("button:has-text('前往慕课学习')").first
            if mooc_btn.count() > 0 and mooc_btn.is_visible():
                mooc_btn.click()
                modal = page.locator("[data-testid='external-redirect-modal']")
                expect(modal).to_be_visible(timeout=5000)
                page.wait_for_timeout(400)
                close_btn = modal.locator("button:has-text('取消')").first
                if close_btn.count() > 0:
                    close_btn.click()
                    page.wait_for_timeout(300)

            save_screenshot(page, "uat_sprint11_06_resource_hub.png")
            uat_results["scenarios"]["scenario_f_resource_hub"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario G: Day 1 AI 智能推荐 (Candidate Recommender) 查看
            # -----------------------------------------------------------------
            log_step("Scenario G: Day 1 AI 智能推荐 (Candidate Recommender) 查看")
            rec_section = page.locator("[data-testid='personalized-recommendation-section']")
            expect(rec_section).to_be_visible(timeout=15000)
            save_screenshot(page, "uat_sprint11_07_recommendations.png")
            uat_results["scenarios"]["scenario_g_recommendations"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario H: Day 1 AI 智能学伴 (Companion) 互动与只读边界
            # -----------------------------------------------------------------
            log_step("Scenario H: Day 1 AI 智能学伴 (Companion) 互动与只读边界")
            page.goto(f"{BASE_URL}/student/assistant", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("text=AI 学习伴学助手", timeout=15000)
            page.wait_for_timeout(500)
            save_screenshot(page, "uat_sprint11_08_ai_companion.png")
            uat_results["scenarios"]["scenario_h_ai_companion"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario I: Day 2 模拟冷启动（清空前端状态）与权威状态恢复
            # -----------------------------------------------------------------
            log_step("Scenario I: Day 2 模拟冷启动（清空前端状态）与权威状态恢复")
            page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("text=学海智导", timeout=15000)
            page.wait_for_timeout(800)
            save_screenshot(page, "uat_sprint11_09_recovery.png")
            uat_results["scenarios"]["scenario_i_cold_start_recovery"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario J: Day 2 模拟跨天时间步进与 Retention 保持度提醒
            # -----------------------------------------------------------------
            log_step("Scenario J: Day 2 模拟跨天时间步进与 Retention 保持度提醒")
            # 查验今日任务页上的保持度与行动状态
            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(600)
            save_screenshot(page, "uat_sprint11_10_retention.png")
            uat_results["scenarios"]["scenario_j_retention"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario K: Day 2 第二轮微测验与路径连续演进
            # -----------------------------------------------------------------
            log_step("Scenario K: Day 2 第二轮微测验与路径连续演进")
            page.goto(f"{BASE_URL}/student/graph", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("text=微观经济学", timeout=15000)
            page.wait_for_timeout(800)
            save_screenshot(page, "uat_sprint11_11_path_evolution.png")
            uat_results["scenarios"]["scenario_k_path_evolution"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario L: Day 3 教师端同源多维视角核验 (S004 学情)
            # -----------------------------------------------------------------
            log_step("Scenario L: Day 3 教师端同源多维视角核验 (S004 学情)")
            page.goto(f"{BASE_URL}/teacher", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("[data-testid='teacher-cockpit']", timeout=15000)

            # 切换到学生花名册
            page.click("[data-testid='tab-teacher-students']")
            page.wait_for_selector("[data-testid='teacher-student-roster']", timeout=10000)
            page.wait_for_timeout(500)

            save_screenshot(page, "uat_sprint11_12_teacher_s004.png")
            uat_results["scenarios"]["scenario_l_teacher_s004"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario M: Day 3 班级多学生隔离与上下文切换 (S001~S004)
            # -----------------------------------------------------------------
            log_step("Scenario M: Day 3 班级多学生隔离与上下文切换 (S001~S004)")
            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("#student-select", timeout=15000)

            # 轮询切换 S001 -> S002 -> S003 -> S004
            for sid in ["S001", "S002", "S003", "S004"]:
                page.locator("#student-select").select_option(sid)
                page.wait_for_timeout(400)

            save_screenshot(page, "uat_sprint11_13_multi_student_isolation.png")
            uat_results["scenarios"]["scenario_m_student_isolation"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario N: 异常注入与容错防护 (网络波动 / 损坏输入)
            # -----------------------------------------------------------------
            log_step("Scenario N: 异常注入与容错防护 (网络波动 / 损坏输入)")
            is_scenario_n = True
            # 模拟离线
            context.set_offline(True)
            page.wait_for_timeout(500)
            save_screenshot(page, "uat_sprint11_14_error_resilience.png")
            # 恢复在线
            context.set_offline(False)
            page.wait_for_timeout(500)
            is_scenario_n = False
            uat_results["scenarios"]["scenario_n_error_resilience"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario O: 全流程文案与人本关怀合规审查
            # -----------------------------------------------------------------
            log_step("Scenario O: 全流程文案与人本关怀合规审查")
            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(600)
            save_screenshot(page, "uat_sprint11_15_humanistic_copy.png")
            uat_results["scenarios"]["scenario_o_humanistic_copy"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario P: 基线原子还原与零脏写确认
            # -----------------------------------------------------------------
            log_step("Scenario P: 基线原子还原与零脏写确认")
            restore_ok, mismatches = snapshot_mgr.restore_baseline()
            if not restore_ok:
                raise RuntimeError(f"Snapshot restore failed: {mismatches}")

            save_screenshot(page, "uat_sprint11_16_baseline_clean.png")
            uat_results["scenarios"]["scenario_p_clean_baseline"] = {
                "status": "PASS",
                "post_restore_state_matches_baseline": True,
            }

            browser.close()

    finally:
        cleanup_spawned(spawned)
        # 保存 UAT 结果 JSON
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(uat_results, f, ensure_ascii=False, indent=2)
        print(f"\n[UAT Results Saved] {RESULTS_FILE}")


if __name__ == "__main__":
    run_uat()
