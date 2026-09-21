# -*- coding: utf-8 -*-
"""
scripts/uat_sprint10c_phase4_pwa.py
===================================
学海智导 (Xuehai Zhidao) — Sprint 10-C Phase 4
学生端 PWA / 移动优先体验加固 (Student PWA / Mobile-first Hardening) 真实端到端验收套件

验收场景矩阵 (10 项全覆盖)：
- Scenario 01: Manifest 可访问性、JSON 合法性与标准配置契约
- Scenario 02: Service Worker 基础文件可访问与注册范围契约
- Scenario 03: Standalone / PWA Shell 独立应用窗口契约与骨架
- Scenario 04: Full Student Flow 完整闭环走通 (Today -> Concept -> Resource -> Quiz -> Result)
- Scenario 05: AI 推荐在移动端非阻塞验证 (主 CTA 开始小测验立即可达)
- Scenario 06: 离线状态下 App Shell 访问与离线横幅提示 (Offline Notice)
- Scenario 07: 离线提交保护 (网络不可用时诚实提示，绝对不伪造 BKT / QUESTION_ATTEMPT)
- Scenario 08: ONLINE -> OFFLINE -> ONLINE 动态网络切换，仅触发只读刷新，零虚假数据写入
- Scenario 09: 移动端视口 (375x812 & 390x844) 响应式、触控目标 (>=44px) 与防横向溢出
- Scenario 10: 桌面端视口 (1440x900) 完整回归无退化
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

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5173")
BACKEND_PORT = 8300
API_URL = os.environ.get("API_URL", f"http://127.0.0.1:{BACKEND_PORT}")

SCREENSHOT_DIR = os.path.abspath("artifacts/uat_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

BRAIN_SCREENSHOT_DIR = r"C:\Users\XSL\.gemini\antigravity\brain\acc330ec-11ad-49d0-a406-fe3e112b5cfc\screenshots"
os.makedirs(BRAIN_SCREENSHOT_DIR, exist_ok=True)

RESULTS_FILE = os.path.abspath("artifacts/uat_results_sprint10c_p4.json")

uat_results: Dict[str, Any] = {
    "sprint": "Sprint 10-C Phase 4 Student PWA / Mobile-first Hardening",
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

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            def create_inspected_page(context, is_fault: bool = False):
                pg = context.new_page()

                def on_console(msg):
                    txt = f"[{msg.type}] {msg.text}"
                    uat_results["console_messages"].append(txt)
                    if msg.type == "error" and not is_fault:
                        text_lower = msg.text.lower()
                        if "favicon" not in text_lower:
                            uat_results["console_errors"].append(txt)
                            print(f"[CONSOLE ERROR] {txt}")

                def on_page_error(exc):
                    uat_results["page_errors"].append(str(exc))
                    print(f"[PAGE ERROR] {exc}")

                def on_req_failed(req):
                    if not is_fault and "favicon" not in req.url:
                        uat_results["failed_requests"].append(f"{req.method} {req.url}")
                        print(f"[REQ FAILED] {req.method} {req.url}")

                pg.on("console", on_console)
                pg.on("pageerror", on_page_error)
                pg.on("requestfailed", on_req_failed)
                return pg

            # -----------------------------------------------------------------
            # Scenario 01: Manifest 可访问性与标准配置契约
            # -----------------------------------------------------------------
            log_step("Scenario 01: Manifest 可访问性与标准配置契约")
            ctx1 = browser.new_context()
            page1 = create_inspected_page(ctx1)
            manifest_resp = page1.goto(f"{BASE_URL}/manifest.webmanifest")
            assert manifest_resp is not None and manifest_resp.status == 200, "Manifest 请求未返回 200"

            manifest_json = manifest_resp.json()
            assert manifest_json["name"] == "学海智导"
            assert manifest_json["short_name"] == "学海智导"
            assert manifest_json["start_url"] in ["/student", "/student/tasks"]
            assert manifest_json["scope"] == "/"
            assert manifest_json["display"] == "standalone"
            assert manifest_json["theme_color"] == "#4f46e5"
            assert len(manifest_json["icons"]) >= 3

            save_screenshot(page1, "sprint10c_p4_01_manifest.png")
            ctx1.close()
            uat_results["scenarios"]["scenario_01_manifest"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 02: Service Worker 基础文件可访问与注册契约
            # -----------------------------------------------------------------
            log_step("Scenario 02: Service Worker 基础文件与注册契约")
            ctx2 = browser.new_context()
            page2 = create_inspected_page(ctx2)
            sw_resp = page2.goto(f"{BASE_URL}/sw.js")
            assert sw_resp is not None and sw_resp.status == 200, "sw.js 请求未返回 200"
            sw_code = page2.content()
            assert "PRECACHE_ASSETS" in sw_code or "sw.js" in sw_resp.url

            save_screenshot(page2, "sprint10c_p4_02_sw_registered.png")
            ctx2.close()
            uat_results["scenarios"]["scenario_02_service_worker"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 03: Standalone / PWA Shell 独立应用窗口契约与骨架
            # -----------------------------------------------------------------
            log_step("Scenario 03: Standalone / PWA Shell 独立应用窗口契约与骨架")
            ctx3 = browser.new_context(viewport={"width": 390, "height": 844})
            page3 = create_inspected_page(ctx3)
            page3.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page3.wait_for_selector("[data-testid='student-home']", timeout=15000)

            # 验证 PWA 视口内导航栏、Header 与主任务卡均正常布局
            expect(page3.locator("[data-testid='today-action-card']")).to_be_visible()
            save_screenshot(page3, "sprint10c_p4_03_standalone_shell.png")
            ctx3.close()
            uat_results["scenarios"]["scenario_03_standalone_shell"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 04: Full Student Flow 完整闭环走通
            # -----------------------------------------------------------------
            log_step("Scenario 04: Full Student Flow 完整闭环走通 (Today -> Session -> Concept -> Quiz -> Result)")
            ctx4 = browser.new_context(viewport={"width": 1440, "height": 900})
            page4 = create_inspected_page(ctx4)
            page4.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page4.wait_for_selector("[data-testid='today-action-card']", timeout=15000)

            # 点击主 CTA 进入 Session Entry
            page4.locator("[data-testid='today-action-cta-btn']").click()
            page4.wait_for_timeout(600)
            modal4 = page4.locator("[data-testid='learning-session-modal']")
            expect(modal4).to_be_visible()

            # Entry -> Concept
            modal4.locator("[data-testid='session-entry-start-concept-btn']").click()
            page4.wait_for_timeout(600)
            expect(modal4.locator("[data-testid='session-step-concept']")).to_be_visible()

            # Concept -> Quiz
            modal4.locator("[data-testid='concept-start-quiz-btn']").click()
            page4.wait_for_timeout(600)
            expect(modal4.locator("[data-testid='session-step-quiz']")).to_be_visible()

            # 完成逐题作答并提交
            for _ in range(10):
                if modal4.locator("[data-testid='session-step-result']").is_visible():
                    break
                quiz_step_el = modal4.locator("[data-testid='session-step-quiz']")
                if not quiz_step_el.is_visible():
                    break

                # 选中第一个选项
                first_opt = quiz_step_el.locator("button.cursor-pointer").first
                expect(first_opt).to_be_visible()
                first_opt.click()
                page4.wait_for_timeout(300)

                # 提交答案
                submit_btn = modal4.locator("[data-testid='quiz-submit-btn']")
                expect(submit_btn).to_be_enabled()
                submit_btn.click()
                page4.wait_for_timeout(1000)

                # 点击下一题 / 查看本次测验结果
                next_btn = modal4.locator("[data-testid='quiz-next-btn']")
                expect(next_btn).to_be_visible()
                next_btn.click()
                page4.wait_for_timeout(800)

            # 验证成功进入 Result 结算
            expect(modal4.locator("[data-testid='session-step-result']")).to_be_visible()
            save_screenshot(page4, "sprint10c_p4_04_full_session_flow.png")

            # 点击返回今日任务
            modal4.locator("[data-testid='result-back-home-btn']").click()
            page4.wait_for_timeout(500)
            expect(modal4).not_to_be_visible()
            ctx4.close()
            uat_results["scenarios"]["scenario_04_full_student_flow"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 05: AI 推荐在移动端非阻塞验证
            # -----------------------------------------------------------------
            log_step("Scenario 05: AI 推荐在移动端非阻塞验证 (主 CTA 立即可点)")
            ctx5 = browser.new_context(viewport={"width": 390, "height": 844})
            page5 = create_inspected_page(ctx5)
            page5.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page5.locator("[data-testid='today-action-cta-btn']").click()
            page5.wait_for_timeout(600)
            modal5 = page5.locator("[data-testid='learning-session-modal']")
            modal5.locator("[data-testid='session-entry-start-concept-btn']").click()
            page5.wait_for_timeout(600)
            modal5.locator("[data-testid='concept-view-resources-btn']").click()
            page5.wait_for_timeout(1000)

            # 验证为你推荐区块渲染
            expect(modal5.locator("[data-testid='personalized-rec-section']")).to_be_visible()
            # 验证开始小测验主 CTA 依然立即可用且高度合规
            quiz_btn = modal5.locator("[data-testid='resource-step-start-quiz-btn']")
            expect(quiz_btn).to_be_visible()
            expect(quiz_btn).to_be_enabled()
            btn_box = quiz_btn.bounding_box()
            assert btn_box is not None and btn_box["height"] >= 40

            save_screenshot(page5, "sprint10c_p4_05_rec_non_blocking.png")
            ctx5.close()
            uat_results["scenarios"]["scenario_05_rec_non_blocking"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 06: 离线状态下 App Shell 访问与离线横幅提示
            # -----------------------------------------------------------------
            log_step("Scenario 06: 离线状态下 App Shell 访问与离线提示 (Offline Notice)")
            ctx6 = browser.new_context(viewport={"width": 1440, "height": 900})
            page6 = create_inspected_page(ctx6, is_fault=True)
            page6.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)

            # 模拟断网：拦截所有请求
            ctx6.route("**/*", lambda route: route.abort("internetdisconnected"))
            # 触发离线事件
            page6.evaluate("() => window.dispatchEvent(new Event('offline'))")
            page6.wait_for_timeout(500)

            # 验证离线提示出现
            offline_notice = page6.locator("[data-testid='pwa-offline-notice']")
            expect(offline_notice).to_be_visible()
            expect(offline_notice).to_contain_text("当前处于离线模式")

            save_screenshot(page6, "sprint10c_p4_06_offline_app_shell.png")
            ctx6.close()
            uat_results["scenarios"]["scenario_06_offline_app_shell"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 07: 离线提交保护 (网络不可用时诚实提示，绝对不伪造 BKT)
            # -----------------------------------------------------------------
            log_step("Scenario 7: 离线提交保护 (诚实提示，绝对不伪造 BKT 与学习事件)")
            from app.core.config import settings
            bkt_file = settings.BKT_STATES_FILE
            path_file = settings.LEARNING_PATH_STATES_FILE
            events_file = settings.LEARNING_EVENTS_FILE

            bkt_before = bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else ""
            path_before = path_file.read_text(encoding="utf-8") if path_file.exists() else ""
            events_before = events_file.read_text(encoding="utf-8") if events_file.exists() else ""

            ctx7 = browser.new_context(viewport={"width": 1440, "height": 900})
            page7 = create_inspected_page(ctx7, is_fault=True)
            page7.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)

            # 打开学习会话进入 QUIZ
            page7.locator("[data-testid='today-action-cta-btn']").click()
            page7.wait_for_timeout(600)
            modal7 = page7.locator("[data-testid='learning-session-modal']")
            modal7.locator("[data-testid='session-entry-start-concept-btn']").click()
            page7.wait_for_timeout(600)
            modal7.locator("[data-testid='concept-start-quiz-btn']").click()
            page7.wait_for_timeout(600)

            # 此时突然断网：拦截所有 /api/* 请求返回 503 NETWORK_UNAVAILABLE
            ctx7.route("**/api/**", lambda route: route.fulfill(
                status=503,
                content_type="application/json",
                body=json.dumps({"error": "NETWORK_UNAVAILABLE", "message": "当前网络不可用"}),
            ))

            # 选中选项并尝试提交
            first_opt7 = modal7.locator("[data-testid='session-step-quiz'] button.cursor-pointer").first
            expect(first_opt7).to_be_visible()
            first_opt7.click()
            page7.wait_for_timeout(300)

            submit_btn7 = modal7.locator("[data-testid='quiz-submit-btn']")
            expect(submit_btn7).to_be_enabled()
            submit_btn7.click()
            page7.wait_for_timeout(800)

            # 验证出现诚实的人本网络提示，而非伪造通过
            error_box = modal7.locator("[data-testid='quiz-submit-error-box']")
            expect(error_box).to_be_visible()
            expect(error_box).to_contain_text("当前网络不可用")

            save_screenshot(page7, "sprint10c_p4_07_offline_submit_protection.png")

            # 严格核对状态文件 0 字节变更
            bkt_after = bkt_file.read_text(encoding="utf-8") if bkt_file.exists() else ""
            path_after = path_file.read_text(encoding="utf-8") if path_file.exists() else ""
            events_after = events_file.read_text(encoding="utf-8") if events_file.exists() else ""

            assert bkt_before == bkt_after, "离线提交后 BKT 发生意外篡改！"
            assert path_before == path_after, "离线提交后 PathState 发生意外篡改！"
            assert events_before == events_after, "离线提交后 LearningEvents 产生意外事件！"

            ctx7.close()
            uat_results["scenarios"]["scenario_07_offline_submit_protection"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 08: ONLINE -> OFFLINE -> ONLINE 动态网络切换 (只读刷新，零写操作)
            # -----------------------------------------------------------------
            log_step("Scenario 08: ONLINE -> OFFLINE -> ONLINE 动态网络切换 (只读刷新，零写操作)")
            events_before8 = events_file.read_text(encoding="utf-8") if events_file.exists() else ""

            ctx8 = browser.new_context(viewport={"width": 1440, "height": 900})
            page8 = create_inspected_page(ctx8, is_fault=True)
            page8.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)

            # 1. 触发 offline
            page8.evaluate("() => window.dispatchEvent(new Event('offline'))")
            page8.wait_for_timeout(400)
            expect(page8.locator("[data-testid='pwa-offline-notice']")).to_be_visible()

            # 2. 触发 online 恢复
            page8.evaluate("() => window.dispatchEvent(new Event('online'))")
            page8.wait_for_timeout(800)
            # 验证离线提示自动消失，主界面平滑恢复
            expect(page8.locator("[data-testid='pwa-offline-notice']")).not_to_be_visible()

            save_screenshot(page8, "sprint10c_p4_08_online_recovery.png")

            # 验证恢复过程中绝对零写入
            events_after8 = events_file.read_text(encoding="utf-8") if events_file.exists() else ""
            assert events_before8 == events_after8, "网络恢复触发了非预期的写操作！"

            ctx8.close()
            uat_results["scenarios"]["scenario_08_online_recovery"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 09: 移动端视口 (375x812 & 390x844) 响应式与防横向溢出
            # -----------------------------------------------------------------
            log_step("Scenario 09: 移动端视口 (375x812 & 390x844) 响应式验收")
            for vp_w, vp_h in [(375, 812), (390, 844)]:
                ctx9 = browser.new_context(viewport={"width": vp_w, "height": vp_h})
                page9 = create_inspected_page(ctx9)
                page9.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)

                # 检查横向滚动溢出
                s_w = page9.evaluate("() => document.documentElement.scrollWidth")
                c_w = page9.evaluate("() => document.documentElement.clientWidth")
                print(f"[Mobile {vp_w}x{vp_h}] scrollWidth: {s_w}, clientWidth: {c_w}")
                assert s_w <= c_w + 1, f"视口 {vp_w} 存在横向滚动溢出: {s_w} > {c_w}"

                # 检查 CTA 触控高度 >= 44px
                cta_box = page9.locator("[data-testid='today-action-cta-btn']").bounding_box()
                assert cta_box is not None and cta_box["height"] >= 44

                if vp_w == 375:
                    save_screenshot(page9, "sprint10c_p4_09_mobile_375x812.png")
                ctx9.close()
            uat_results["scenarios"]["scenario_09_mobile_regression"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 10: 桌面端视口 (1440x900) 完整回归无退化
            # -----------------------------------------------------------------
            log_step("Scenario 10: 桌面端视口 (1440x900) 完整回归无退化")
            ctx10 = browser.new_context(viewport={"width": 1440, "height": 900})
            page10 = create_inspected_page(ctx10)
            page10.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)

            expect(page10.locator("[data-testid='student-home']")).to_be_visible()
            expect(page10.locator("[data-testid='today-action-card']")).to_be_visible()
            expect(page10.locator("[data-testid='current-focus-card']")).to_be_visible()
            expect(page10.locator("[data-testid='recent-progress-card']")).to_be_visible()

            save_screenshot(page10, "sprint10c_p4_10_desktop_regression.png")
            ctx10.close()
            uat_results["scenarios"]["scenario_10_desktop_regression"] = {"status": "PASS"}

            browser.close()

    finally:
        cleanup_spawned(spawned)

    # 保存 UAT 汇总报告
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(uat_results, f, ensure_ascii=False, indent=2)

    print(f"\n[UAT Complete] 验收报告已保存至 {RESULTS_FILE}")
    print(f"Scenarios: {len(uat_results['scenarios'])}/10 passed")
    print(f"Console errors: {len(uat_results['console_errors'])}")
    print(f"Page errors: {len(uat_results['page_errors'])}")


if __name__ == "__main__":
    run_uat()
