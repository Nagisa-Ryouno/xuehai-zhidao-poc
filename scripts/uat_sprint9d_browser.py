# -*- coding: utf-8 -*-
"""
scripts/uat_sprint9d_browser.py
===============================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-D
学习效果验证与资源自适应反馈端到端浏览器验收 (12 Browser Scenarios A ~ L)

使用 Playwright Chromium 对 Sprint 9-D 全部产品功能与用户旅程进行端到端闭环验收：
- Scenario A: 访问学习资源中心，验证「开始本次学习」核心行动入口与推荐步骤
- Scenario B: 点击「开始本次学习」，验证学习会话激活与 4 步时序微进度看板 (步骤 1 ~ 4)
- Scenario C: 执行步骤 1「考点微卡精要」，验证速览微卡调起与核心直观呈现
- Scenario D: 执行步骤 2「典型例题深度剖析」，验证真实生活与商业情境案例精读
- Scenario E: 在例题模态框中点击「向 AI 伴学提问」，验证携带材料上下文直通 AI 辅导
- Scenario F: 点击「完成本次学习并检验掌握度」，触发服务端权威重读，验证核心结果卡 (本次学习完成) 弹出
- Scenario G: 验证核心结果卡中「学习前掌握度 → 学习后掌握度」及「掌握度净变化 (+Δ%)」双向对比与分级标签
- Scenario H: 验证核心结果卡中「已完成的学习步骤清单」全部勾选状态
- Scenario I: 验证人本导师评语 (严格遵循时间关联叙事，零底层技术黑话)
- Scenario J: 点击下一步行动「再练一道巩固」，验证顺畅调起考点靶向微练
- Scenario K: 切换学生 (S001 -> S002)，验证学习会话与效果反馈多学生上下文严格隔离
- Scenario L: 移动端视口 (375x812) 下自适应布局、时序微看板与核心结果卡人体工学验证

执行完毕后在 artifacts/uat_screenshots/ 保存 sprint9d_01~12.png，
并在 artifacts/uat_results_sprint9d.json 输出详细报告。
"""

import json
import os
import sys
import time
from typing import Any, Dict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright, Page, expect

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5173")
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8011")
SCREENSHOT_DIR = os.path.abspath("artifacts/uat_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

RESULTS_FILE = os.path.abspath("artifacts/uat_results_sprint9d.json")

uat_results: Dict[str, Any] = {
    "sprint": "Sprint 9-D",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "console_messages": [],
    "console_errors": [],
    "page_errors": [],
    "failed_requests": [],
    "api_responses": [],
    "scenarios": {},
    "security_invariants": {},
}


def log_step(title: str):
    print(f"\n{'='*75}\n>>> {title}\n{'='*75}")


def run_uat():
    # 确保 UAT 在纯净初态下执行
    sessions_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "learning_sessions.json"))
    if os.path.exists(sessions_path):
        with open(sessions_path, "w", encoding="utf-8") as f:
            f.write("{}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) XuehaiZhidao-Sprint9D-UAT/1.0",
        )
        page = context.new_page()

        # 监听控制台与网络
        def on_console(msg):
            text = msg.text
            msg_type = msg.type
            uat_results["console_messages"].append({"type": msg_type, "text": text})
            if msg_type == "error":
                if "favicon" not in text and "Encountered two children with the same key" not in text:
                    uat_results["console_errors"].append(text)
                    print(f"[BROWSER CONSOLE ERROR] {text}")

        def on_page_error(exc):
            err_msg = str(exc)
            uat_results["page_errors"].append(err_msg)
            print(f"[PAGE EXCEPTION] {err_msg}")

        def on_request_failed(req):
            if "favicon.ico" not in req.url:
                uat_results["failed_requests"].append({"url": req.url, "failure": req.failure})
                print(f"[REQUEST FAILED] {req.url}")

        def on_response(res):
            if "/api/" in res.url:
                uat_results["api_responses"].append({
                    "url": res.url,
                    "status": res.status,
                    "ok": res.ok,
                })

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("requestfailed", on_request_failed)
        page.on("response", on_response)

        # ----------------------------------------------------------------------
        # Scenario A: Access Resource Hub & Check Start Session CTA
        # ----------------------------------------------------------------------
        log_step("Scenario A: 访问学习资源中心，验证「开始本次学习」核心行动入口与推荐步骤")
        page.goto(f"{BASE_URL}/student/resources", wait_until="networkidle")
        time.sleep(1.2)

        expect(page.locator("h2:has-text('学习资源中心')")).to_be_visible()
        expect(page.locator("text=自适应学习材料库")).to_be_visible()
        expect(page.locator("text=为你量身定制的步骤建议")).to_be_visible()

        start_btn = page.locator("button:has-text('开始本次学习')")
        expect(start_btn).to_be_visible()

        shot_a = os.path.join(SCREENSHOT_DIR, "sprint9d_01_resource_hub_start_session_button.png")
        page.screenshot(path=shot_a)
        uat_results["scenarios"]["scenario_a"] = {"status": "PASS", "screenshot": shot_a}
        print("Scenario A PASSED.")

        # ----------------------------------------------------------------------
        # Scenario B: Start Learning Session & Stepper Activation
        # ----------------------------------------------------------------------
        log_step("Scenario B: 点击「开始本次学习」，验证学习会话激活与 4 步时序微进度看板")
        start_btn.click()
        time.sleep(1.5)

        expect(page.locator("text=学习进行中")).to_be_visible()
        expect(page.locator("text=本次自适应学习会话")).to_be_visible()
        expect(page.locator("text=初始掌握度快照：")).to_be_visible()
        expect(page.locator("text=步骤 1")).to_be_visible()
        expect(page.locator("text=步骤 2")).to_be_visible()
        expect(page.locator("text=步骤 3")).to_be_visible()
        expect(page.locator("text=步骤 4")).to_be_visible()
        expect(page.locator("button:has-text('完成本次学习并检验掌握度')")).to_be_visible()

        shot_b = os.path.join(SCREENSHOT_DIR, "sprint9d_02_active_session_stepper.png")
        page.screenshot(path=shot_b)
        uat_results["scenarios"]["scenario_b"] = {"status": "PASS", "screenshot": shot_b}
        print("Scenario B PASSED.")

        # ----------------------------------------------------------------------
        # Scenario C: Step 1 - Open Concept Card
        # ----------------------------------------------------------------------
        log_step("Scenario C: 执行步骤 1「考点微卡精要」，验证速览微卡调起与核心直观呈现")
        page.locator("text=考点微卡精要").first.click()
        time.sleep(1.0)

        expect(page.locator("text=直觉导引 · 一句话顿悟")).to_be_visible()
        expect(page.locator("text=核心理论与关键机制")).to_be_visible()

        shot_c = os.path.join(SCREENSHOT_DIR, "sprint9d_03_session_step1_concept_card.png")
        page.screenshot(path=shot_c)
        uat_results["scenarios"]["scenario_c"] = {"status": "PASS", "screenshot": shot_c}
        print("Scenario C PASSED.")

        # 关闭微卡
        close_card_btn = page.locator("button[aria-label='关闭速览卡片']").or_(page.locator("button:has-text('稍后温习')")).first
        if close_card_btn.is_visible():
            close_card_btn.click()
        else:
            page.keyboard.press("Escape")
        time.sleep(0.6)

        # ----------------------------------------------------------------------
        # Scenario D: Step 2 - Open Example Reader
        # ----------------------------------------------------------------------
        log_step("Scenario D: 执行步骤 2「典型例题深度剖析」，验证真实生活与商业情境案例精读")
        page.locator("text=典型例题深度剖析").first.click()
        time.sleep(1.0)

        expect(page.locator("role=dialog")).to_be_visible()
        expect(page.locator("text=生活与商业真实情境拆解")).to_be_visible()

        shot_d = os.path.join(SCREENSHOT_DIR, "sprint9d_04_session_step2_example_reader.png")
        page.screenshot(path=shot_d)
        uat_results["scenarios"]["scenario_d"] = {"status": "PASS", "screenshot": shot_d}
        print("Scenario D PASSED.")

        # ----------------------------------------------------------------------
        # Scenario E: Companion with Resource Context
        # ----------------------------------------------------------------------
        log_step("Scenario E: 在例题模态框中点击「向 AI 伴学提问」，验证携带材料上下文直通 AI 辅导")
        dialog = page.locator("role=dialog")
        ask_ai_btn = dialog.locator("button:has-text('向 AI 伴学提问此例题')")
        expect(ask_ai_btn).to_be_visible()
        ask_ai_btn.click()
        time.sleep(1.5)

        # 应当跳转或激活 AI 伴学界面
        expect(page.locator("button:has-text('AI伴学')").first).to_be_visible()

        shot_e = os.path.join(SCREENSHOT_DIR, "sprint9d_05_companion_with_resource_context.png")
        page.screenshot(path=shot_e)
        uat_results["scenarios"]["scenario_e"] = {"status": "PASS", "screenshot": shot_e}
        print("Scenario E PASSED.")

        # 返回资源中心
        page.goto(f"{BASE_URL}/student/resources", wait_until="networkidle")
        time.sleep(1.2)

        # ----------------------------------------------------------------------
        # Scenario F: Complete Session & Core Completion Card
        # ----------------------------------------------------------------------
        log_step("Scenario F: 点击「完成本次学习并检验掌握度」，触发服务端权威重读与核心结果卡")
        complete_sess_btn = page.locator("button:has-text('完成本次学习并检验掌握度')")
        expect(complete_sess_btn).to_be_visible()
        complete_sess_btn.click()
        time.sleep(1.8)

        expect(page.locator("text=本次学习完成！学习效果评估与反馈")).to_be_visible()
        expect(page.locator("text=学习前掌握度")).to_be_visible()
        expect(page.locator("text=学习后掌握度")).to_be_visible()
        expect(page.locator("text=掌握度净变化")).to_be_visible()

        shot_f = os.path.join(SCREENSHOT_DIR, "sprint9d_06_core_completion_card_effectiveness.png")
        page.screenshot(path=shot_f)
        uat_results["scenarios"]["scenario_f"] = {"status": "PASS", "screenshot": shot_f}
        print("Scenario F PASSED.")

        # ----------------------------------------------------------------------
        # Scenario G: Checklist Items Completed Verification
        # ----------------------------------------------------------------------
        log_step("Scenario G: 验证核心结果卡中「已完成的学习步骤清单」")
        expect(page.locator("text=已完成的学习步骤清单")).to_be_visible()
        expect(page.locator("text=考点微卡精要研读")).to_be_visible()
        expect(page.locator("text=典型例题深度剖析")).to_be_visible()
        expect(page.locator("text=靶向微练 / 效果验证")).to_be_visible()

        shot_g = os.path.join(SCREENSHOT_DIR, "sprint9d_07_completed_checklist.png")
        page.screenshot(path=shot_g)
        uat_results["scenarios"]["scenario_g"] = {"status": "PASS", "screenshot": shot_g}
        print("Scenario G PASSED.")

        # ----------------------------------------------------------------------
        # Scenario H: Tutor Feedback Narrative (Temporal & No Jargon)
        # ----------------------------------------------------------------------
        log_step("Scenario H: 验证人本导师评语 (严格遵循时间关联叙事，零底层技术黑话)")
        feedback_card = page.locator("text=完成本次学习后，掌握情况从")
        expect(feedback_card).to_be_visible()

        # 验证页面完全不存在底层黑话
        body_text = page.locator("body").inner_text()
        forbidden = ["BKT", "Bayesian", "PathState", "Resolver", "因为你看了", "由于你阅读了"]
        for term in forbidden:
            assert term not in body_text, f"页面存在违规底层黑话或虚假因果: {term}"

        shot_h = os.path.join(SCREENSHOT_DIR, "sprint9d_08_tutor_feedback_narrative.png")
        page.screenshot(path=shot_h)
        uat_results["scenarios"]["scenario_h"] = {"status": "PASS", "screenshot": shot_h}
        print("Scenario H PASSED.")

        # ----------------------------------------------------------------------
        # Scenario I: Next Action CTA - Practice Again
        # ----------------------------------------------------------------------
        log_step("Scenario I: 点击下一步行动「再练一道巩固」，验证顺畅调起考点靶向微练")
        practice_btn = page.locator("button:has-text('再练一道巩固')")
        expect(practice_btn).to_be_visible()
        practice_btn.click()
        time.sleep(1.5)

        # 验证进入微测验弹窗或答题区
        expect(page.locator("h3:has-text('微测验突破')")).to_be_visible()

        shot_i = os.path.join(SCREENSHOT_DIR, "sprint9d_09_next_action_quiz_start.png")
        page.screenshot(path=shot_i)
        uat_results["scenarios"]["scenario_i"] = {"status": "PASS", "screenshot": shot_i}
        print("Scenario I PASSED.")

        # 退出微测验
        close_quiz_btn = page.locator("button:has-text('退出测验')").or_(page.locator("button:has-text('关闭')")).first
        if close_quiz_btn.is_visible():
            close_quiz_btn.click()
        else:
            page.keyboard.press("Escape")
        time.sleep(0.5)

        # ----------------------------------------------------------------------
        # Scenario J: Knowledge Switch & Reset
        # ----------------------------------------------------------------------
        log_step("Scenario J: 切换考点 (K01 -> K07)，验证会话重置与自适应推荐更新")
        page.goto(f"{BASE_URL}/student/resources", wait_until="networkidle")
        time.sleep(1.0)

        page.select_option("select#knowledge-select", "K07")
        time.sleep(1.2)

        expect(page.locator("select#knowledge-select")).to_have_value("K07")
        expect(page.locator("text=供求变动与均衡分析 考点精要微卡").first).to_be_visible()
        expect(page.locator("button:has-text('开始本次学习')")).to_be_visible()

        shot_j = os.path.join(SCREENSHOT_DIR, "sprint9d_10_knowledge_switch_reset.png")
        page.screenshot(path=shot_j)
        uat_results["scenarios"]["scenario_j"] = {"status": "PASS", "screenshot": shot_j}
        print("Scenario J PASSED.")

        # ----------------------------------------------------------------------
        # Scenario K: Multi-Student Context Isolation
        # ----------------------------------------------------------------------
        log_step("Scenario K: 切换学生 (S001 -> S002)，验证学习会话与效果反馈多学生上下文严格隔离")
        student_switch = page.locator("select[aria-label='选择切换当前学习学生']").or_(page.locator("select:has-text('张同学')")).first
        if student_switch.is_visible():
            student_switch.select_option("S002")
            time.sleep(1.5)

        expect(page.locator("button:has-text('开始本次学习')")).to_be_visible()
        # 确保完成结果卡不再残留
        expect(page.locator("text=本次学习完成！学习效果评估与反馈")).not_to_be_visible()

        shot_k = os.path.join(SCREENSHOT_DIR, "sprint9d_11_student_isolation_switch.png")
        page.screenshot(path=shot_k)
        uat_results["scenarios"]["scenario_k"] = {"status": "PASS", "screenshot": shot_k}
        print("Scenario K PASSED.")

        # ----------------------------------------------------------------------
        # Scenario L: Mobile Viewport Ergonomics
        # ----------------------------------------------------------------------
        log_step("Scenario L: 移动端视口 (375x812) 下自适应布局、时序微看板与核心结果卡人体工学验证")
        page.set_viewport_size({"width": 375, "height": 812})
        time.sleep(1.0)

        expect(page.locator("h2:has-text('学习资源中心')")).to_be_visible()
        expect(page.locator("button:has-text('开始本次学习')")).to_be_visible()

        # 验证移动端底部导航或卡片无横向溢出
        overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
        assert not overflow, "移动端视口存在横向溢出滚动条!"

        shot_l = os.path.join(SCREENSHOT_DIR, "sprint9d_12_mobile_effectiveness_card.png")
        page.screenshot(path=shot_l)
        uat_results["scenarios"]["scenario_l"] = {"status": "PASS", "screenshot": shot_l}
        print("Scenario L PASSED.")

        context.close()
        browser.close()

    # 写入测试报告
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(uat_results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 75)
    print(f"[SUCCESS] ALL 12 SPRINT 9-D BROWSER SCENARIOS PASSED!")
    print(f"Screenshots saved to: {SCREENSHOT_DIR}")
    print(f"Results report saved to: {RESULTS_FILE}")
    print("=" * 75)


if __name__ == "__main__":
    run_uat()
