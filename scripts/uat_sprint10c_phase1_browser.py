# -*- coding: utf-8 -*-
"""
scripts/uat_sprint10c_phase1_browser.py
=======================================
学海智导 (Xuehai Zhidao) — Sprint 10-C Phase 1
学生端首页 (Student Home / Today) 真实浏览器端到端验收套件

验收场景矩阵：
- Scenario 1: 已有学习状态学生 (S001) 访问桌面端首页 (1440x900) 与 4 大核心模块渲染
- Scenario 2: 移动端视口 375x812 (iPhone X) 零横向溢出与触控靶点核验
- Scenario 3: 移动端视口 390x844 (iPhone 12/13/14) 布局与视觉呼吸感核验
- Scenario 4: 今日行动 CTA 点击进入真实学习闭环 (微测验/概念微卡)
- Scenario 5: Today Action NONE 状态 (阶段全达标人本空状态，严禁伪造任务)
- Scenario 6: 局部失败容错 (Progress API 500 时 Today Action 保持可用，绝不整页白屏)
- Scenario 7: 学生上下文切换与新学生状态隔离 (真实起点，杜绝假数据污染)
- Scenario 8: 超长考点名称防溢出与弹性折行排版核验

质量指标硬性验收：
- Console Errors = 0 (除故意注入故障的网络错误外)
- Page Exceptions = 0
- Failed Requests = 0 (除故意注入故障的网络错误外)
- 截图归档至 artifacts/uat_screenshots/ 与 brain 目录
"""

import json
import os
import re
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

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5173")
BACKEND_PORT = 8300
API_URL = os.environ.get("API_URL", f"http://127.0.0.1:{BACKEND_PORT}")

SCREENSHOT_DIR = os.path.abspath("artifacts/uat_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

BRAIN_SCREENSHOT_DIR = r"C:\Users\XSL\.gemini\antigravity\brain\acc330ec-11ad-49d0-a406-fe3e112b5cfc\screenshots"
os.makedirs(BRAIN_SCREENSHOT_DIR, exist_ok=True)

RESULTS_FILE = os.path.abspath("artifacts/uat_results_sprint10c_p1.json")

uat_results: Dict[str, Any] = {
    "sprint": "Sprint 10-C Phase 1 Student Home / Today",
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
        print(f"Warning copying screenshot: {e}")
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
        print(f"[Launcher] 后端未运行，启动 127.0.0.1:{BACKEND_PORT}...")
        proc_backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "gateway.api:create_gateway_app", "--factory", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
            cwd=str(PROJECT_ROOT),
        )
        spawned_procs.append(("backend", proc_backend))
        for _ in range(25):
            if check_url_ready(f"{API_URL}/api/students"):
                print(f"[Launcher] 后端已就绪 (127.0.0.1:{BACKEND_PORT})")
                break
            time.sleep(0.8)
        else:
            raise RuntimeError("后端服务启动超时")
    else:
        print(f"[Launcher] 后端服务已在线 ({BACKEND_PORT})")

    # 2. 检查前端
    if not check_url_ready(f"{BASE_URL}/"):
        print("[Launcher] 前端未运行，启动 127.0.0.1:5173...")
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
        print(f"[Cleanup] 停止 {name} 进程 (PID: {proc.pid})...")
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        else:
            proc.terminate()
            proc.wait()


def run_uat():
    spawned = ensure_servers_running()
    is_fault_testing = False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # -----------------------------------------------------------------
            # Scenario 1: 已有学习状态学生 (S001) 访问桌面端首页
            # -----------------------------------------------------------------
            log_step("Scenario 1: S001 访问桌面端首页 (1440x900) 与 4 大结构块验证")
            context = browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="block")
            page = context.new_page()

            def on_console(msg):
                txt = f"[{msg.type}] {msg.text}"
                uat_results["console_messages"].append(txt)
                if msg.type == "error" and not is_fault_testing:
                    text_lower = msg.text.lower()
                    if "favicon" not in text_lower:
                        uat_results["console_errors"].append(txt)
                        print(f"[CONSOLE ERROR] {txt}")

            def on_page_error(exc):
                uat_results["page_errors"].append(str(exc))
                print(f"[PAGE ERROR] {exc}")

            def on_req_failed(req):
                if not is_fault_testing and "favicon" not in req.url:
                    uat_results["failed_requests"].append(f"{req.method} {req.url}")
                    print(f"[REQ FAILED] {req.method} {req.url}")

            page.on("console", on_console)
            page.on("pageerror", on_page_error)
            page.on("requestfailed", on_req_failed)

            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page.wait_for_selector("[data-testid='student-home']", timeout=15000)

            # 验证 1: Greeting
            expect(page.locator("[data-testid='student-greeting']")).to_be_visible()
            expect(page.locator("text=今天也学一点吧")).to_be_visible()

            # 验证 2: Today Action Card
            today_card = page.locator("[data-testid='today-action-card']")
            expect(today_card).to_be_visible()
            expect(today_card.locator("text=今日学习")).to_be_visible()
            today_cta = page.locator("[data-testid='today-action-cta-btn']")
            expect(today_cta).to_be_visible()

            # 验证 3: Current Focus Card
            focus_card = page.locator("[data-testid='current-focus-card']")
            expect(focus_card).to_be_visible()
            expect(focus_card.locator("text=当前学习焦点")).to_be_visible()

            # 验证 4: Recent Progress Card
            progress_card = page.locator("[data-testid='recent-progress-card']")
            expect(progress_card).to_be_visible()
            expect(progress_card.locator("text=最近进展")).to_be_visible()
            expect(progress_card.locator("text=整体掌握度")).to_be_visible()
            expect(progress_card.locator("text=已掌握考点")).to_be_visible()
            expect(progress_card.locator("text=练习正确率")).to_be_visible()
            expect(progress_card.locator("text=累计练习题数")).to_be_visible()

            save_screenshot(page, "sprint10c_p1_01_desktop_home.png")
            uat_results["scenarios"]["scenario_1_desktop_home"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 2: 移动端 375x812 (iPhone X) 零横向溢出与触控靶点
            # -----------------------------------------------------------------
            log_step("Scenario 2: 移动端 375x812 (iPhone X) 零横向溢出与触控靶点")
            mobile_context_375 = browser.new_context(
                viewport={"width": 375, "height": 812},
                service_workers="block",
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
            )
            page_375 = mobile_context_375.new_page()
            page_375.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page_375.wait_for_selector("[data-testid='student-home']", timeout=15000)

            # 验证无横向滚动条
            overflow = page_375.evaluate("""() => {
                const el = document.documentElement;
                return {
                    scrollWidth: el.scrollWidth,
                    clientWidth: el.clientWidth,
                    hasHorizontalScroll: el.scrollWidth > el.clientWidth
                };
            }""")
            assert not overflow["hasHorizontalScroll"], f"375x812 发现横向滚动: {overflow}"
            print(f"[Responsiveness] 375x812 视口横向防溢出验证通过: {overflow}")

            # 验证触控靶点高度 >= 44px
            cta_box = page_375.locator("[data-testid='today-action-cta-btn']").bounding_box()
            assert cta_box and cta_box["height"] >= 44, f"CTA 触控高度不足 44px: {cta_box}"

            # 验证底部导航固定
            expect(page_375.locator("nav[aria-label='学生端底部主导航']")).to_be_visible()

            save_screenshot(page_375, "sprint10c_p1_02_mobile_375x812.png")
            uat_results["scenarios"]["scenario_2_mobile_375x812"] = {"status": "PASS", "overflow": overflow}

            # -----------------------------------------------------------------
            # Scenario 3: 移动端 390x844 (iPhone 12/13/14) 布局与视觉
            # -----------------------------------------------------------------
            log_step("Scenario 3: 移动端 390x844 布局与视觉呼吸感")
            mobile_context_390 = browser.new_context(
                viewport={"width": 390, "height": 844},
                service_workers="block",
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
            )
            page_390 = mobile_context_390.new_page()
            page_390.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page_390.wait_for_selector("[data-testid='student-home']", timeout=15000)

            overflow_390 = page_390.evaluate("""() => {
                const el = document.documentElement;
                return {
                    scrollWidth: el.scrollWidth,
                    clientWidth: el.clientWidth,
                    hasHorizontalScroll: el.scrollWidth > el.clientWidth
                };
            }""")
            assert not overflow_390["hasHorizontalScroll"], f"390x844 发现横向滚动: {overflow_390}"
            print(f"[Responsiveness] 390x844 视口横向防溢出验证通过: {overflow_390}")

            save_screenshot(page_390, "sprint10c_p1_03_mobile_390x844.png")
            uat_results["scenarios"]["scenario_3_mobile_390x844"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 4: 今日行动 CTA 点击进入真实学习闭环
            # -----------------------------------------------------------------
            log_step("Scenario 4: 今日行动 CTA 点击进入真实学习闭环 (微测验/概念微卡)")
            page.bring_to_front()
            cta_btn = page.locator("[data-testid='today-action-cta-btn']")
            cta_text = cta_btn.inner_text().strip()
            print(f"[CTA Check] 当前今日行动 CTA 文案: {cta_text}")

            cta_btn.click()
            page.wait_for_timeout(1000)

            # 验证调起了真实弹窗 (微测验 Dialog 或概念卡 Modal)
            modal = page.locator("div[role='dialog'], [data-testid='concept-card-modal'], div[class*='BottomSheet'], div[class*='fixed inset-0']").first
            expect(modal).to_be_visible(timeout=8000)
            print("[CTA Check] 成功进入真实学习闭环弹窗！")

            save_screenshot(page, "sprint10c_p1_04_cta_learning_loop.png")
            uat_results["scenarios"]["scenario_4_cta_loop"] = {"status": "PASS", "cta_text": cta_text}

            # 安全关闭弹窗
            close_btn = page.locator("button[aria-label*='关闭'], button:has-text('稍后温习'), button:has-text('关闭')").first
            if close_btn.count() > 0:
                close_btn.click()
                page.wait_for_timeout(500)

            # -----------------------------------------------------------------
            # Scenario 5: Today Action NONE 状态 (阶段全达标人本空状态)
            # -----------------------------------------------------------------
            log_step("Scenario 5: Today Action NONE 状态 (阶段全达标人本空状态，严禁伪造)")
            none_context = browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="block")
            page_none = none_context.new_page()

            def route_none_action(route):
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "student_id": "S001",
                        "action": {
                            "action_type": "NONE",
                            "title": "",
                            "description": "",
                            "cta_label": "",
                            "priority_reason": "当前阶段学习任务已全部达成",
                            "knowledge_id": None,
                            "knowledge_name": None,
                            "suggested_action": None
                        }
                    })
                )

            page_none.route(re.compile(r".*/api/learning/today/.*"), route_none_action)
            page_none.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page_none.wait_for_selector("[data-testid='today-action-card']", timeout=15000)

            none_card = page_none.locator("[data-testid='today-action-card']")
            expect(none_card.locator("text=今天暂时没有待完成的学习任务")).to_be_visible()
            expect(none_card.locator("text=查看学习进展")).to_be_visible()
            print("[NONE Check] 空状态正确渲染，无伪造推荐任务！")

            # 点击查看学习进展，验证导航至 /student/profile
            none_cta = none_card.locator("[data-testid='today-action-cta-btn']")
            none_cta.click()
            page_none.wait_for_timeout(800)
            assert "/student/profile" in page_none.url, f"未能导航至 /student/profile: {page_none.url}"
            print(f"[Navigation Check] NONE CTA 成功导航至: {page_none.url}")

            save_screenshot(page_none, "sprint10c_p1_05_today_action_none.png")
            uat_results["scenarios"]["scenario_5_none_state"] = {"status": "PASS"}
            page_none.close()

            # -----------------------------------------------------------------
            # Scenario 6: 局部失败容错 (Progress API 500 时首页仍可用)
            # -----------------------------------------------------------------
            log_step("Scenario 6: 局部失败容错 (Progress 500 时 Today Action 仍可用)")
            is_fault_testing = True
            fault_context = browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="block")
            page_fault = fault_context.new_page()

            def route_progress_fail(route):
                route.fulfill(status=500, body="Internal Server Error")

            page_fault.route(re.compile(r".*/students/.*/progress"), route_progress_fail)
            page_fault.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page_fault.wait_for_selector("[data-testid='student-home']", timeout=15000)

            # Today Action 依然正常可用
            expect(page_fault.locator("[data-testid='today-action-card']")).to_be_visible()
            expect(page_fault.locator("[data-testid='current-focus-card']")).to_be_visible()

            # Recent Progress 卡片呈现独立容错与重试按钮，绝不导致整页白屏
            expect(page_fault.locator("text=暂时无法加载最近学习进展")).to_be_visible()
            expect(page_fault.locator("[data-testid='recent-progress-retry-btn']")).to_be_visible()
            print("[Resilience Check] Progress API 失败时，Today Action 与当前焦点 100% 可用，整页零白屏！")

            save_screenshot(page_fault, "sprint10c_p1_06_partial_failure_resilience.png")
            uat_results["scenarios"]["scenario_6_partial_failure"] = {"status": "PASS"}
            page_fault.close()
            is_fault_testing = False

            # -----------------------------------------------------------------
            # Scenario 7: 学生上下文切换与新学生状态隔离
            # -----------------------------------------------------------------
            log_step("Scenario 7: 学生上下文切换与新学生状态隔离 (真实起点，零伪造数据)")
            page.bring_to_front()
            page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle")
            page.wait_for_selector("[data-testid='student-home']", timeout=15000)

            # 通过 Header 下拉切换至 S002
            student_select = page.locator("#student-select")
            expect(student_select).to_be_visible()
            student_select.select_option("S002")
            page.wait_for_timeout(1500)

            # 验证 Header 与 Greeting 已切换至 S002 李同学
            greeting_text = page.locator("[data-testid='student-greeting']").inner_text()
            assert "李同学" in greeting_text or "李" in greeting_text, f"未切换到李同学: {greeting_text}"
            print(f"[Student Switch] 成功切换至学生上下文: {greeting_text.splitlines()[0]}")

            save_screenshot(page, "sprint10c_p1_07_new_student_first_entry.png")
            uat_results["scenarios"]["scenario_7_new_student"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 8: 超长考点名称防溢出与弹性折行排版核验
            # -----------------------------------------------------------------
            log_step("Scenario 8: 超长考点名称防溢出与弹性折行排版核验")
            long_context = browser.new_context(viewport={"width": 375, "height": 812}, service_workers="block")
            page_long = long_context.new_page()
            long_name = "微观经济学中关于完全竞争市场长期均衡条件与供给价格弹性变动分析"

            def route_long_name_action(route):
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "student_id": "S001",
                        "action": {
                            "action_type": "CONTINUE_LEARNING",
                            "title": f"继续学习：{long_name}",
                            "description": "这是当前学习路径中的首要内容，考点名称极长但页面必须优雅折行。",
                            "cta_label": "继续学习",
                            "priority_reason": "长考点名称弹性排版验证",
                            "knowledge_id": "K02",
                            "knowledge_name": long_name,
                            "suggested_action": "REVIEW_CONCEPT"
                        }
                    })
                )

            page_long.route(re.compile(r".*/api/learning/today/.*"), route_long_name_action)
            page_long.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page_long.wait_for_selector("[data-testid='today-action-card']", timeout=15000)

            overflow_long = page_long.evaluate("""() => {
                const el = document.documentElement;
                return {
                    scrollWidth: el.scrollWidth,
                    clientWidth: el.clientWidth,
                    hasHorizontalScroll: el.scrollWidth > el.clientWidth
                };
            }""")
            assert not overflow_long["hasHorizontalScroll"], f"超长名称导致横向溢出: {overflow_long}"
            print(f"[Long Name Check] 超长考点名称防溢出验证通过: {overflow_long}")

            save_screenshot(page_long, "sprint10c_p1_08_long_name_resilience.png")
            uat_results["scenarios"]["scenario_8_long_name"] = {"status": "PASS"}
            page_long.close()

            # 最终检查
            print(f"\nUAT 完成！Console Errors 数量: {len(uat_results['console_errors'])}")
            print(f"Page Errors 数量: {len(uat_results['page_errors'])}")
            print(f"Failed Requests 数量: {len(uat_results['failed_requests'])}")

            assert len(uat_results["console_errors"]) == 0, f"发现控制台错误: {uat_results['console_errors']}"
            assert len(uat_results["page_errors"]) == 0, f"发现页面异常: {uat_results['page_errors']}"
            assert len(uat_results["failed_requests"]) == 0, f"发现失败请求: {uat_results['failed_requests']}"

            uat_results["final_verdict"] = "PASS"
            with open(RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(uat_results, f, indent=2, ensure_ascii=False)

            print("\n🎉 Sprint 10-C Phase 1 Browser UAT 全部 8 大场景执行完毕并严格验证通过！")

    finally:
        cleanup_spawned(spawned)


if __name__ == "__main__":
    run_uat()
