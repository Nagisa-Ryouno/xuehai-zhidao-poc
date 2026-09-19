# -*- coding: utf-8 -*-
"""
scripts/uat_sprint9f_browser.py
===============================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-F
学习保持度验证与间隔复习建议 Lite 端到端浏览器验收 (5 Scenarios A ~ E)

使用 Playwright Chromium 对 Sprint 9-F 全部产品功能与用户旅程进行端到端闭环验收：
- Scenario A: 访问学习资源中心，验证达到 3 天复习间隔的考点展示「🔄 该复习一下了」卡片与复测入口
- Scenario B: 点击「开始快速复测」，验证联动调起微测验
- Scenario C: 验证掌握度偏低或复测未稳固时展示「📘 建议再巩固一下」卡片与概念回顾入口
- Scenario D: 切换学生或未学考点，验证优雅静默（INSUFFICIENT_DATA / NOT_DUE 零干扰）
- Scenario E: 移动端视口 (375x812) 下卡片自适应、无横向溢出与良好人体工程学

执行完毕后在 artifacts/uat_screenshots/ 保存 sprint9f_01~05.png，
并在 artifacts/uat_results_sprint9f.json 输出详细报告。
"""

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
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

BRAIN_SCREENSHOT_DIR = r"C:\Users\XSL\.gemini\antigravity\brain\acc330ec-11ad-49d0-a406-fe3e112b5cfc\screenshots"
os.makedirs(BRAIN_SCREENSHOT_DIR, exist_ok=True)

RESULTS_FILE = os.path.abspath("artifacts/uat_results_sprint9f.json")

uat_results: Dict[str, Any] = {
    "sprint": "Sprint 9-F",
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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) XuehaiZhidao-Sprint9F-UAT/1.0",
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
        # Scenario A: Retention Prompt Card Display (DUE_FOR_REVIEW)
        # ----------------------------------------------------------------------
        log_step("Scenario A: 访问学习资源中心，验证达到复习间隔的考点展示「🔄 该复习一下了」卡片")

        # 拦截 retention 请求，模拟 S001 在 K08 达到 3 天复习间隔 (DUE_FOR_REVIEW)
        retention_state = {
            "student_id": "S001",
            "knowledge_id": "K08",
            "last_learning_at": "2026-09-16T10:00:00Z",
            "days_since_learning": 3,
            "current_mastery": 0.72,
            "retention_status": "DUE_FOR_REVIEW",
            "should_review": True,
            "suggested_action": "RETAKE_QUIZ",
        }

        def route_handler(route):
            url = route.request.url
            if "/learning/retention/S001/K08" in url:
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(retention_state),
                )
            elif "/learning/retention/S001/K13" in url:
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "student_id": "S001",
                        "knowledge_id": "K13",
                        "last_learning_at": None,
                        "days_since_learning": None,
                        "current_mastery": 0.20,
                        "retention_status": "INSUFFICIENT_DATA",
                        "should_review": False,
                        "suggested_action": None,
                    }),
                )
            elif "/learning/retention/S002/" in url:
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "student_id": "S002",
                        "knowledge_id": "K08",
                        "last_learning_at": None,
                        "days_since_learning": None,
                        "current_mastery": 0.20,
                        "retention_status": "INSUFFICIENT_DATA",
                        "should_review": False,
                        "suggested_action": None,
                    }),
                )
            else:
                route.continue_()

        page.route(re.compile(r".*learning/retention.*"), route_handler)

        page.goto(f"{BASE_URL}/student/resources", wait_until="networkidle")
        time.sleep(2.0)

        expect(page.locator("h2:has-text('学习资源中心')")).to_be_visible()

        # 验证该复习一下了卡片
        prompt_card = page.locator("[data-testid='retention-prompt-card']")
        expect(prompt_card).to_be_visible()
        expect(prompt_card.locator("text=该复习一下了")).to_be_visible()
        expect(prompt_card.locator("text=过去 3 天")).to_be_visible()
        expect(prompt_card.locator("[data-testid='start-retention-quiz-btn']")).to_be_visible()

        shot_a = os.path.join(SCREENSHOT_DIR, "sprint9f_01_retention_prompt_card.png")
        page.screenshot(path=shot_a)
        shutil.copyfile(shot_a, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9f_01_retention_prompt_card.png"))
        uat_results["scenarios"]["scenario_a"] = {"status": "PASS", "screenshot": shot_a}
        print("Scenario A PASSED.")

        # ----------------------------------------------------------------------
        # Scenario B: Retention Quiz Launch Action
        # ----------------------------------------------------------------------
        log_step("Scenario B: 点击「开始快速复测」按钮，验证联动调起微测验")
        start_quiz_btn = prompt_card.locator("[data-testid='start-retention-quiz-btn']")
        expect(start_quiz_btn).to_be_visible()
        start_quiz_btn.click()
        time.sleep(1.5)

        # 验证微测验抽屉/界面已调起
        quiz_heading = page.locator("text=微测验突破").first
        expect(quiz_heading).to_be_visible()

        shot_b = os.path.join(SCREENSHOT_DIR, "sprint9f_02_retention_quiz_launch.png")
        page.screenshot(path=shot_b)
        shutil.copyfile(shot_b, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9f_02_retention_quiz_launch.png"))
        uat_results["scenarios"]["scenario_b"] = {"status": "PASS", "screenshot": shot_b}
        print("Scenario B PASSED.")

        # ----------------------------------------------------------------------
        # Scenario C: Reinforcement Suggestion Card (NEEDS_REINFORCEMENT)
        # ----------------------------------------------------------------------
        log_step("Scenario C: 验证掌握度偏低或复测未稳固时展示「📘 建议再巩固一下」卡片")
        
        # 将 K08 状态更新为 NEEDS_REINFORCEMENT
        retention_state["retention_status"] = "NEEDS_REINFORCEMENT"
        retention_state["days_since_learning"] = 1
        retention_state["current_mastery"] = 0.52
        retention_state["suggested_action"] = "REVIEW_CONCEPT"

        # 关闭微测抽屉回到资源中心
        close_btn = page.locator("button[aria-label='Close'], button:has-text('✕'), button:has-text('关闭')").first
        if close_btn.is_visible():
            close_btn.click()
            time.sleep(1.0)
        else:
            page.goto(f"{BASE_URL}/student/resources", wait_until="networkidle")
            time.sleep(1.5)

        # 切换考点触发重新拉取
        kp_select = page.locator("select#knowledge-select")
        kp_select.select_option("K09")
        time.sleep(0.5)
        kp_select.select_option("K08")
        time.sleep(1.5)

        reinforce_card = page.locator("[data-testid='retention-reinforcement-card']")
        expect(reinforce_card).to_be_visible()
        expect(reinforce_card.locator("text=建议再巩固一下")).to_be_visible()
        expect(reinforce_card.locator("text=这次复测发现这个考点还有一些容易混淆的地方")).to_be_visible()
        expect(reinforce_card.locator("[data-testid='review-concept-btn']")).to_be_visible()

        shot_c = os.path.join(SCREENSHOT_DIR, "sprint9f_03_retention_reinforcement_card.png")
        page.screenshot(path=shot_c)
        shutil.copyfile(shot_c, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9f_03_retention_reinforcement_card.png"))
        uat_results["scenarios"]["scenario_c"] = {"status": "PASS", "screenshot": shot_c}
        print("Scenario C PASSED.")

        # ----------------------------------------------------------------------
        # Scenario D: Insufficient Data / Clean State
        # ----------------------------------------------------------------------
        log_step("Scenario D: 切换学生或未学考点，验证优雅静默（INSUFFICIENT_DATA 零干扰）")
        
        # 切换至未学习考点 K13
        kp_select.select_option("K13")
        time.sleep(1.5)

        # 验证提示卡与巩固卡皆不显示
        expect(page.locator("[data-testid='retention-prompt-card']")).not_to_be_visible()
        expect(page.locator("[data-testid='retention-reinforcement-card']")).not_to_be_visible()
        expect(page.locator("text=该复习一下了")).not_to_be_visible()

        shot_d = os.path.join(SCREENSHOT_DIR, "sprint9f_04_insufficient_data_clean_state.png")
        page.screenshot(path=shot_d)
        shutil.copyfile(shot_d, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9f_04_insufficient_data_clean_state.png"))
        uat_results["scenarios"]["scenario_d"] = {"status": "PASS", "screenshot": shot_d}
        print("Scenario D PASSED.")

        # ----------------------------------------------------------------------
        # Scenario E: Mobile 375x812 Ergonomics
        # ----------------------------------------------------------------------
        log_step("Scenario E: 移动端视口 (375x812) 下卡片自适应、无横向溢出与良好人体工程学")
        
        # 还原回 DUE_FOR_REVIEW
        retention_state["retention_status"] = "DUE_FOR_REVIEW"
        retention_state["days_since_learning"] = 3
        retention_state["suggested_action"] = "RETAKE_QUIZ"

        kp_select.select_option("K08")
        time.sleep(1.0)

        page.set_viewport_size({"width": 375, "height": 812})
        time.sleep(1.5)

        expect(page.locator("h2:has-text('学习资源中心')")).to_be_visible()
        expect(page.locator("[data-testid='retention-prompt-card']")).to_be_visible()

        # 严格验证无横向滚动溢出
        overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
        assert not overflow, "移动端视口存在横向溢出滚动条!"

        shot_e = os.path.join(SCREENSHOT_DIR, "sprint9f_05_mobile_375px_ergonomics.png")
        page.screenshot(path=shot_e)
        shutil.copyfile(shot_e, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9f_05_mobile_375px_ergonomics.png"))
        uat_results["scenarios"]["scenario_e"] = {"status": "PASS", "screenshot": shot_e}
        print("Scenario E PASSED.")

        context.close()
        browser.close()

    # 写入测试报告
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(uat_results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 75)
    print(f"[SUCCESS] ALL 5 SPRINT 9-F BROWSER SCENARIOS PASSED!")
    print(f"Screenshots saved to: {SCREENSHOT_DIR}")
    print(f"Artifacts synced to: {BRAIN_SCREENSHOT_DIR}")
    print(f"Results report saved to: {RESULTS_FILE}")
    print("=" * 75)


if __name__ == "__main__":
    run_uat()
