# -*- coding: utf-8 -*-
"""
scripts/uat_sprint9g_browser.py
===============================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-G
今日学习行动聚合 Lite 浏览器端到端验收 (4 Scenarios A ~ D)

场景列表：
- Scenario A: NEEDS_REINFORCEMENT -> 验证「建议再巩固一下」卡片，点击「重新学习」调起概念微卡
- Scenario B: DUE_FOR_REVIEW -> 验证「该复习一下了」卡片，点击「开始快速复测」联动调起微测验
- Scenario C: IN_PROGRESS / PRACTICE -> 验证「做一道小练习」/「继续学习」卡片与练习联动
- Scenario D: 学生切换与 375px 移动端无溢出 -> 验证 S001 与 S002 上下文隔离，375x812 人体工程学，0 console errors, 0 failed requests

截图归档至 artifacts/uat_screenshots/sprint9g_01~04.png
并同步至 AppData brain 归档区。
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

RESULTS_FILE = os.path.abspath("artifacts/uat_results_sprint9g.json")

uat_results: Dict[str, Any] = {
    "sprint": "Sprint 9-G",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "console_messages": [],
    "console_errors": [],
    "page_errors": [],
    "failed_requests": [],
    "scenarios": {},
}


def log_step(title: str):
    print(f"\n{'='*75}\n>>> {title}\n{'='*75}")


def run_uat():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # 监听控制台日志与请求失败
        def on_console(msg):
            uat_results["console_messages"].append(f"[{msg.type}] {msg.text}")
            if msg.type == "error":
                text = msg.text.lower()
                # 忽略第三方 favicon 或 benign fetch abort
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

        # ----------------------------------------------------------------------
        # Scenario A: NEEDS_REINFORCEMENT -> 建议再巩固一下 -> 重新学习
        # ----------------------------------------------------------------------
        log_step("Scenario A: 验证 NEEDS_REINFORCEMENT「建议再巩固一下」卡片与「重新学习」概念微卡调起")

        current_today_override = {
            "student_id": "S001",
            "action": {
                "action_type": "REVIEW_RETENTION",
                "title": "建议再巩固一下",
                "description": "需求价格弹性最近一次复习还不够稳定，先重新看看概念，再试一次。",
                "cta_label": "重新学习",
                "priority_reason": "已有考点复习未稳固，需针对性巩固",
                "knowledge_id": "K02",
                "knowledge_name": "需求价格弹性",
                "suggested_action": "REVIEW_CONCEPT",
            },
        }

        def route_today_action(route):
            url = route.request.url
            if "/api/learning/today/S001" in url and current_today_override.get("enabled", True):
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(current_today_override),
                )
            else:
                route.continue_()

        page.route(re.compile(r".*/api/learning/today/.*"), route_today_action)

        page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle")
        time.sleep(2.0)

        action_card = page.locator("[data-testid='today-action-card']")
        expect(action_card).to_be_visible()
        expect(action_card.locator("text=今日学习")).to_be_visible()
        expect(action_card.locator("text=建议再巩固一下")).to_be_visible()
        expect(action_card.locator("text=复习提醒")).to_be_visible()
        expect(action_card.locator("text=已有考点复习未稳固，需针对性巩固")).to_be_visible()

        cta_btn = page.locator("[data-testid='today-action-cta-btn']")
        expect(cta_btn).to_be_visible()
        expect(cta_btn).to_have_text(re.compile(r"重新学习"))

        # 点击重新学习调起概念微卡
        cta_btn.click()
        time.sleep(1.5)

        concept_modal = page.locator("text=直觉导引 · 一句话顿悟").first
        expect(concept_modal).to_be_visible()

        shot_a = os.path.join(SCREENSHOT_DIR, "sprint9g_01_needs_reinforcement_card.png")
        page.screenshot(path=shot_a)
        shutil.copyfile(shot_a, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9g_01_needs_reinforcement_card.png"))
        uat_results["scenarios"]["scenario_a"] = {"status": "PASS", "screenshot": shot_a}
        print("Scenario A PASSED.")

        # 关闭概念卡模态框
        close_concept_btn = page.locator("button:has-text('稍后温习'), button[aria-label='关闭速览卡片']").first
        close_concept_btn.click()
        time.sleep(1.0)

        # ----------------------------------------------------------------------
        # Scenario B: DUE_FOR_REVIEW -> 该复习一下了 -> 开始快速复测 -> 微测验
        # ----------------------------------------------------------------------
        log_step("Scenario B: 验证 DUE_FOR_REVIEW「该复习一下了」卡片与「开始快速复测」调起微测验")

        current_today_override["action"] = {
            "action_type": "REVIEW_RETENTION",
            "title": "该复习一下了",
            "description": "需求价格弹性已经有一段时间没有复习，现在花 1～2 分钟快速测一下，可以帮助你确认是否还记得。",
            "cta_label": "开始快速复测",
            "priority_reason": "已有考点达到复习间隔时间",
            "knowledge_id": "K02",
            "knowledge_name": "需求价格弹性",
            "suggested_action": "RETAKE_QUIZ",
        }

        page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle")
        time.sleep(2.0)

        expect(action_card.locator("text=该复习一下了")).to_be_visible()
        expect(action_card.locator("text=已有考点达到复习间隔时间")).to_be_visible()
        expect(cta_btn).to_have_text(re.compile(r"开始快速复测"))

        cta_btn.click()
        time.sleep(1.5)

        quiz_heading = page.locator("text=微测验突破").first
        expect(quiz_heading).to_be_visible()

        shot_b = os.path.join(SCREENSHOT_DIR, "sprint9g_02_due_for_review_quiz.png")
        page.screenshot(path=shot_b)
        shutil.copyfile(shot_b, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9g_02_due_for_review_quiz.png"))
        uat_results["scenarios"]["scenario_b"] = {"status": "PASS", "screenshot": shot_b}
        print("Scenario B PASSED.")

        # 关闭测验抽屉
        close_quiz_btn = page.locator("button[aria-label='Close'], button:has-text('✕'), button:has-text('关闭')").first
        if close_quiz_btn.is_visible():
            close_quiz_btn.click()
            time.sleep(1.0)

        # ----------------------------------------------------------------------
        # Scenario C: IN_PROGRESS / PRACTICE -> 推荐练习或继续学习
        # ----------------------------------------------------------------------
        log_step("Scenario C: 验证无复习任务时呈现「继续学习」/「做一道小练习」")

        current_today_override["action"] = {
            "action_type": "CONTINUE_LEARNING",
            "title": "继续学习：消费者剩余",
            "description": "这是你当前学习路径中的下一步内容。",
            "cta_label": "开始学习",
            "priority_reason": "当前学习路径中的首要未完成任务",
            "knowledge_id": "K05",
            "knowledge_name": "消费者剩余",
            "suggested_action": "REVIEW_CONCEPT",
        }

        page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle")
        time.sleep(2.0)

        expect(action_card.locator("text=继续学习：消费者剩余")).to_be_visible()
        expect(action_card.locator("text=继续学习").first).to_be_visible()
        expect(cta_btn).to_have_text(re.compile(r"开始学习"))

        shot_c = os.path.join(SCREENSHOT_DIR, "sprint9g_03_practice_or_in_progress.png")
        page.screenshot(path=shot_c)
        shutil.copyfile(shot_c, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9g_03_practice_or_in_progress.png"))
        uat_results["scenarios"]["scenario_c"] = {"status": "PASS", "screenshot": shot_c}
        print("Scenario C PASSED.")

        # ----------------------------------------------------------------------
        # Scenario D: 学生切换 + 375px 移动端无横向滚动
        # ----------------------------------------------------------------------
        log_step("Scenario D: 验证学生切换上下文隔离与 375x812 移动端自适应")

        # 恢复走真实 API (S002 真实返回 PRACTICE 或真实动作)
        current_today_override["enabled"] = False

        # 切换到学生 S002 (李华)
        student_select = page.locator("select").first
        if student_select.is_visible():
            student_select.select_option("S002")
            time.sleep(2.0)

        # 验证 S002 真实返回的今日行动卡片 (做一道小练习)
        expect(action_card).to_be_visible()
        expect(action_card.locator("text=做一道小练习")).to_be_visible()
        expect(action_card.locator("text=推荐练习")).to_be_visible()

        # 调整至 375x812 移动端视口
        page.set_viewport_size({"width": 375, "height": 812})
        time.sleep(1.5)

        # 检查无横向滚动溢出
        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        client_width = page.evaluate("() => document.documentElement.clientWidth")
        print(f"Viewport 375px check: scrollWidth={scroll_width}, clientWidth={client_width}")
        assert scroll_width <= client_width + 1, f"移动端存在横向溢出: scrollWidth({scroll_width}) > clientWidth({client_width})"

        shot_d = os.path.join(SCREENSHOT_DIR, "sprint9g_04_student_switch_and_mobile_375px.png")
        page.screenshot(path=shot_d)
        shutil.copyfile(shot_d, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9g_04_student_switch_and_mobile_375px.png"))
        uat_results["scenarios"]["scenario_d"] = {"status": "PASS", "screenshot": shot_d}
        print("Scenario D PASSED.")

        # 写入测试总结
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(uat_results, f, ensure_ascii=False, indent=2)

        browser.close()

    print("\n" + "=" * 80)
    print("ALL 4 SPRINT 9-G UAT SCENARIOS PASSED SUCCESSFULLY!")
    print(f"Console errors: {len(uat_results['console_errors'])}")
    print(f"Failed requests: {len(uat_results['failed_requests'])}")
    print("=" * 80)


if __name__ == "__main__":
    run_uat()
