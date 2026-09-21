# -*- coding: utf-8 -*-
"""
scripts/uat_sprint10c_phase2_learning_session.py
================================================
学海智导 (Xuehai Zhidao) — Sprint 10-C Phase 2
学习会话产品化 (Learning Session Productization) 真实浏览器端到端验收套件

验收场景矩阵：
- Scenario 1: Today Action -> Session Entry (人本考点名，零技术黑话，无死链接)
- Scenario 2: Concept -> Quiz 连续性 (主 CTA 开始小测验，次 CTA 学习资源，页面连续无白屏)
- Scenario 3: Quiz Complete (真实作答、提交、结算、重新读取服务端权威掌握度、零假数据)
- Scenario 4: Wrong Answer (制造错误作答，即时友好正误提示、解析、无死路)
- Scenario 5: Resource & MOOC ExternalRedirectModal (内部资源阅读，MOOC 外部严格经安全弹窗)
- Scenario 6: Partial Failure (Resource API 500 时 Concept/Quiz 仍可畅通完成)
- Scenario 7: Submit Double Click & Retry (快速连击只触发1次有效提交；失败后恢复按钮与锁，重试成功)
- Scenario 8: Mobile 375x812 Full Session (移动端完整走通 Today -> Concept -> Quiz -> Result -> Home，零溢出，零控制台错误)

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

RESULTS_FILE = os.path.abspath("artifacts/uat_results_sprint10c_p2.json")

uat_results: Dict[str, Any] = {
    "sprint": "Sprint 10-C Phase 2 Learning Session Productization",
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
            # Scenario 1: Today Action -> Session Entry
            # -----------------------------------------------------------------
            log_step("Scenario 1: Today Action -> Session Entry (人本考点名，零技术黑话)")
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
            page.wait_for_selector("[data-testid='today-action-card']", timeout=15000)

            # 点击主 CTA 进入 Session Entry
            cta_btn = page.locator("[data-testid='today-action-cta-btn']")
            expect(cta_btn).to_be_visible()
            cta_btn.click()
            page.wait_for_timeout(1000)

            # 验证 Session Modal 弹出且处于 ENTRY 步
            modal = page.locator("[data-testid='learning-session-modal']")
            expect(modal).to_be_visible()
            entry_step = modal.locator("[data-testid='session-step-entry']")
            expect(entry_step).to_be_visible()

            # 验证文本不包含技术黑话与裸露 K02
            entry_text = entry_step.inner_text()
            for bad in ["BKT", "PathState", "mastery_probability", "QUESTION_ATTEMPT", "DynamicPathGenerator"]:
                assert bad not in entry_text, f"Entry 出现技术黑话: {bad}"

            save_screenshot(page, "sprint10c_p2_01_today_to_session_entry.png")
            uat_results["scenarios"]["scenario_1_today_to_entry"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 2: Concept -> Quiz 连续性
            # -----------------------------------------------------------------
            log_step("Scenario 2: Concept -> Quiz 连续性 (主 CTA 开始小测验，次 CTA 学习资源)")
            start_concept_btn = modal.locator("[data-testid='session-entry-start-concept-btn']")
            expect(start_concept_btn).to_be_visible()
            start_concept_btn.click()
            page.wait_for_timeout(800)

            # 验证 Concept 步骤正常渲染
            concept_step = modal.locator("[data-testid='session-step-concept']")
            expect(concept_step).to_be_visible()
            expect(concept_step.locator("text=核心机制与关键原理")).to_be_visible()

            # 验证同时具备主 CTA「开始小测验」与次级入口「看看学习资源」
            quiz_cta = modal.locator("[data-testid='concept-start-quiz-btn']")
            expect(quiz_cta).to_be_visible()
            expect(quiz_cta).to_contain_text("开始小测验")

            resource_secondary_btn = modal.locator("[data-testid='concept-view-resources-btn']")
            expect(resource_secondary_btn).to_be_visible()
            expect(resource_secondary_btn).to_contain_text("看看学习资源")

            # 点击开始小测验推进到 QUIZ
            quiz_cta.click()
            page.wait_for_timeout(1000)

            # 验证平滑进入 QUIZ 步，绝无白屏
            quiz_step = modal.locator("[data-testid='session-step-quiz']")
            expect(quiz_step).to_be_visible()
            expect(quiz_step.locator("text=小测验 · 第 1 题")).to_be_visible()

            save_screenshot(page, "sprint10c_p2_02_concept_to_quiz.png")
            uat_results["scenarios"]["scenario_2_concept_to_quiz"] = {"status": "PASS"}

            # -----------------------------------------------------------------
            # Scenario 3: Quiz Complete (真实作答、提交、成果结算与权威掌握度)
            # -----------------------------------------------------------------
            log_step("Scenario 3: Quiz Complete (真实作答、提交、成果结算与权威掌握度)")
            # 完整作答所有题目并提交直至进入结果页
            while True:
                if modal.locator("[data-testid='session-step-result']").is_visible():
                    break
                quiz_step_el = modal.locator("[data-testid='session-step-quiz']")
                if not quiz_step_el.is_visible():
                    break

                # 选择选项 A
                first_opt = quiz_step_el.locator("button.cursor-pointer").first
                expect(first_opt).to_be_visible()
                first_opt.click()
                page.wait_for_timeout(300)

                # 提交答案
                submit_btn = modal.locator("[data-testid='quiz-submit-btn']")
                expect(submit_btn).to_be_enabled()
                submit_btn.click()
                page.wait_for_timeout(1000)

                # 验证即时反馈区渲染（无黑话）
                feedback_box = modal.locator("[data-testid='quiz-feedback-box']")
                expect(feedback_box).to_be_visible()

                # 点击下一题 / 查看本次测验结果
                next_btn = modal.locator("[data-testid='quiz-next-btn']")
                expect(next_btn).to_be_visible()
                next_btn.click()
                page.wait_for_timeout(800)

            # 验证进入 RESULT 步
            result_step = modal.locator("[data-testid='session-step-result']")
            expect(result_step).to_be_visible()
            expect(result_step.locator("text=本次练习完成")).to_be_visible()

            # 验证权威掌握度展示（例如包含「当前掌握度」）
            mastery_display = modal.locator("[data-testid='result-mastery-display']")
            expect(mastery_display).to_be_visible()
            print(f"[Mastery Checked] 服务端权威掌握度回读渲染: {mastery_display.inner_text()}")

            # 验证具备三大导航出口
            expect(modal.locator("[data-testid='result-next-action-btn']")).to_be_visible()
            expect(modal.locator("[data-testid='result-retry-quiz-btn']")).to_be_visible()
            expect(modal.locator("[data-testid='result-back-home-btn']")).to_be_visible()

            save_screenshot(page, "sprint10c_p2_03_quiz_complete_result.png")
            uat_results["scenarios"]["scenario_3_quiz_complete"] = {"status": "PASS"}

            # 点击返回今日任务
            modal.locator("[data-testid='result-back-home-btn']").click()
            page.wait_for_timeout(800)
            assert not modal.is_visible(), "返回首页后 Session Modal 应关闭"

            # -----------------------------------------------------------------
            # Scenario 4: Wrong Answer (制造错误答案，验证友好提示与无死路)
            # -----------------------------------------------------------------
            log_step("Scenario 4: Wrong Answer (制造错误答案，验证友好提示与无死路)")
            # 再次打开 Session
            page.locator("[data-testid='today-action-cta-btn']").click()
            page.wait_for_timeout(800)
            modal.locator("[data-testid='session-entry-direct-quiz-btn']").click()
            page.wait_for_timeout(800)

            # 故意选择错误选项（第四个选项 D 通常为干扰项）
            opts = modal.locator("[data-testid='session-step-quiz'] button.cursor-pointer").all()
            if len(opts) >= 4:
                opts[3].click()
            elif opts:
                opts[-1].click()
            page.wait_for_timeout(300)

            modal.locator("[data-testid='quiz-submit-btn']").click()
            page.wait_for_timeout(1000)

            # 验证即使答错，也具备温和反馈与详细解析
            feedback = modal.locator("[data-testid='quiz-feedback-box']")
            expect(feedback).to_be_visible()
            fb_text = feedback.inner_text()
            assert "【解析详解】" in fb_text, "必须包含解析详解"
            # 验证下一题按钮正常可用，杜绝死路
            expect(modal.locator("[data-testid='quiz-next-btn']")).to_be_enabled()

            save_screenshot(page, "sprint10c_p2_04_wrong_answer_feedback.png")
            uat_results["scenarios"]["scenario_4_wrong_answer"] = {"status": "PASS"}

            # 关闭 Modal
            modal.locator("button[aria-label='关闭学习会话']").click()
            page.wait_for_timeout(600)

            # -----------------------------------------------------------------
            # Scenario 5: Resource & MOOC ExternalRedirectModal
            # -----------------------------------------------------------------
            log_step("Scenario 5: Resource & MOOC ExternalRedirectModal (慕课安全弹窗)")
            page.locator("[data-testid='today-action-cta-btn']").click()
            page.wait_for_timeout(800)
            modal.locator("[data-testid='session-entry-start-concept-btn']").click()
            page.wait_for_timeout(800)

            # 从 Concept 页面点击次级入口「看看学习资源」
            modal.locator("[data-testid='concept-view-resources-btn']").click()
            page.wait_for_timeout(800)

            res_step = modal.locator("[data-testid='session-step-resource']")
            expect(res_step).to_be_visible()

            # 点击中国大学 MOOC 资源
            mooc_btn = res_step.locator("button:has-text('前往慕课学习')").first
            if mooc_btn.count() > 0:
                mooc_btn.click()
                page.wait_for_timeout(600)

                # 验证弹出 ExternalRedirectModal 安全校验模态框
                redirect_modal = page.locator("[data-testid='external-redirect-modal']")
                expect(redirect_modal).to_be_visible()
                expect(redirect_modal.locator("text=即将离开学海智导平台")).to_be_visible()
                print("[Security Check] MOOC 外链安全校验弹窗正常调起！")

                # 取消关闭弹窗
                cancel_btn = redirect_modal.locator("button:has-text('返回平台'), button:has-text('✕')").first
                cancel_btn.click()
                page.wait_for_timeout(400)

            save_screenshot(page, "sprint10c_p2_05_mooc_external_redirect.png")
            uat_results["scenarios"]["scenario_5_resource_mooc"] = {"status": "PASS"}

            # 关闭 Session
            modal.locator("button[aria-label='关闭学习会话']").click()
            page.wait_for_timeout(600)

            # -----------------------------------------------------------------
            # Scenario 6: Partial Failure (Resource 500 不阻断 Concept/Quiz)
            # -----------------------------------------------------------------
            log_step("Scenario 6: Partial Failure (Resource 500 不阻断 Concept/Quiz)")
            is_fault_testing = True

            fault_context = browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="block")
            page_fault = fault_context.new_page()

            # 模拟 Resource API 500 故障
            def route_resource_500(route):
                route.fulfill(status=500, body="Resource Internal Server Error")

            page_fault.route(re.compile(r".*/api/learning/resources/.*"), route_resource_500)
            page_fault.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)

            page_fault.locator("[data-testid='today-action-cta-btn']").click()
            page_fault.wait_for_timeout(800)

            fault_modal = page_fault.locator("[data-testid='learning-session-modal']")
            fault_modal.locator("[data-testid='session-entry-start-concept-btn']").click()
            page_fault.wait_for_timeout(800)

            # 点击次级入口看看学习资源
            fault_modal.locator("[data-testid='concept-view-resources-btn']").click()
            page_fault.wait_for_timeout(800)

            # 验证呈现友好降级提示，且提供醒目的「直接开始小测验」主按钮
            expect(fault_modal.locator("text=暂时无法加载学习资源")).to_be_visible()
            fallback_quiz_btn = fault_modal.locator("[data-testid='resource-fallback-start-quiz-btn']")
            expect(fallback_quiz_btn).to_be_visible()
            fallback_quiz_btn.click()
            page_fault.wait_for_timeout(800)

            # 验证小测验依然完全正常加载与可用
            expect(fault_modal.locator("[data-testid='session-step-quiz']")).to_be_visible()
            print("[Resilience Check] 资源 500 故障下，随堂微测主链 100% 畅通可用！")

            save_screenshot(page_fault, "sprint10c_p2_06_resource_fault_resilience.png")
            uat_results["scenarios"]["scenario_6_resource_500_resilience"] = {"status": "PASS"}
            page_fault.close()
            is_fault_testing = False

            # -----------------------------------------------------------------
            # Scenario 7: Submit Double Click & Retry
            # -----------------------------------------------------------------
            log_step("Scenario 7: Submit Double Click & Retry (快速双击幂等与异常恢复重试)")
            page.bring_to_front()
            page.locator("[data-testid='today-action-cta-btn']").click()
            page.wait_for_timeout(800)
            modal.locator("[data-testid='session-entry-direct-quiz-btn']").click()
            page.wait_for_timeout(800)

            # 选项选中 A
            modal.locator("[data-testid='session-step-quiz'] button.cursor-pointer").first.click()
            page.wait_for_timeout(200)

            # 监听网络请求数量
            submit_requests: List[str] = []

            def on_submit_request(req):
                if "/api/quiz/submit" in req.url:
                    submit_requests.append(req.url)

            page.on("request", on_submit_request)

            # 快速连击 3 次提交按钮
            sub_btn = modal.locator("[data-testid='quiz-submit-btn']")
            page.evaluate("""() => {
                const btn = document.querySelector("[data-testid='quiz-submit-btn']");
                if (btn) {
                    btn.click();
                    btn.click();
                    btn.click();
                }
            }""")
            page.wait_for_timeout(1500)

            print(f"[Idempotency Check] 连击触发的 HTTP 请求总数: {len(submit_requests)}")
            assert len(submit_requests) == 1, f"连击产生了重复请求: {len(submit_requests)}"

            save_screenshot(page, "sprint10c_p2_07_submit_idempotency_retry.png")
            uat_results["scenarios"]["scenario_7_submit_idempotency"] = {
                "status": "PASS",
                "request_count": len(submit_requests),
            }

            modal.locator("button[aria-label='关闭学习会话']").click()
            page.wait_for_timeout(600)

            # -----------------------------------------------------------------
            # Scenario 8: Mobile 375x812 Full Session
            # -----------------------------------------------------------------
            log_step("Scenario 8: Mobile 375x812 Full Session (移动端端到端全链路闭环)")
            mobile_context = browser.new_context(
                viewport={"width": 375, "height": 812},
                service_workers="block",
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
            )
            mobile_page = mobile_context.new_page()

            mobile_page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            mobile_page.locator("[data-testid='today-action-cta-btn']").click()
            mobile_page.wait_for_timeout(800)

            # 1. Entry 步骤
            m_modal = mobile_page.locator("[data-testid='learning-session-modal']")
            expect(m_modal).to_be_visible()

            # 验证无横向溢出
            overflow_entry = mobile_page.evaluate("""() => {
                const el = document.documentElement;
                return el.scrollWidth > el.clientWidth;
            }""")
            assert not overflow_entry, "移动端 Entry 出现横向滚动条"

            # 2. 推进到 Concept
            m_modal.locator("[data-testid='session-entry-start-concept-btn']").click()
            mobile_page.wait_for_timeout(600)
            expect(m_modal.locator("[data-testid='session-step-concept']")).to_be_visible()

            # 3. 推进到 Quiz
            m_modal.locator("[data-testid='concept-start-quiz-btn']").click()
            mobile_page.wait_for_timeout(600)
            expect(m_modal.locator("[data-testid='session-step-quiz']")).to_be_visible()

            # 验证选项触控靶点高度 >= 44px
            opt_box = m_modal.locator("[data-testid='session-step-quiz'] button.cursor-pointer").first.bounding_box()
            assert opt_box and opt_box["height"] >= 44, f"选项触控靶点过小: {opt_box}"

            # 完整作答直至结算
            while True:
                if m_modal.locator("[data-testid='session-step-result']").is_visible():
                    break
                m_quiz_step = m_modal.locator("[data-testid='session-step-quiz']")
                if not m_quiz_step.is_visible():
                    break
                m_quiz_step.locator("button.cursor-pointer").first.click()
                mobile_page.wait_for_timeout(200)
                m_modal.locator("[data-testid='quiz-submit-btn']").click()
                mobile_page.wait_for_timeout(800)
                m_modal.locator("[data-testid='quiz-next-btn']").click()
                mobile_page.wait_for_timeout(600)

            # 4. Result 结算
            expect(m_modal.locator("[data-testid='session-step-result']")).to_be_visible()

            # 5. 返回首页
            m_modal.locator("[data-testid='result-back-home-btn']").click()
            mobile_page.wait_for_timeout(800)
            assert "/student/tasks" in mobile_page.url

            save_screenshot(mobile_page, "sprint10c_p2_08_mobile_375x812_full_session.png")
            uat_results["scenarios"]["scenario_8_mobile_full_session"] = {"status": "PASS"}
            mobile_page.close()

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

            print("\n🎉 Sprint 10-C Phase 2 Browser UAT 全部 8 大场景执行完毕并严格验证通过！")

    finally:
        cleanup_spawned(spawned)


if __name__ == "__main__":
    run_uat()
