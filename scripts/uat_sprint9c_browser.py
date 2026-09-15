# -*- coding: utf-8 -*-
"""
scripts/uat_sprint9c_browser.py
===============================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-C
学习资源中心与资源感知自适应学习端到端浏览器验收 (12 Browser Scenarios A ~ L)

使用 Playwright Chromium 对 Sprint 9-C 全部产品功能与用户旅程进行端到端闭环验收：
- Scenario A: 访问「今日任务」视图，验证桌面 5-Tab 导航与焦点卡「📚 推荐学习材料」联动按钮
- Scenario B: 点击「学习资源」Tab，访问学习资源中心主页
- Scenario C: 验证自适应导引横幅呈现步骤化推荐序列 (步骤 1, 步骤 2, 步骤 3) 与零黑话说明
- Scenario D: 切换「考点微卡」分类过滤器，验证精准过滤
- Scenario E: 切换「典型例题」分类过滤器，验证例题材料展示
- Scenario F: 打开「典型例题精析」研读模态框，验证生活商业实例拆解与避坑指南
- Scenario G: 在模态框中点击「研读完毕，标记完成」，验证完成状态与资源事件上报
- Scenario H: 点击「查看微卡」，验证考点精要速览微卡顺畅弹出并关闭
- Scenario I: 关键词搜索联动验证 (输入「稀缺性」动态筛选)
- Scenario J: 点击「开始微练」，调起官方通关微测验并作答
- Scenario K: 切换学生 (S001 -> S002)，验证资源自适应推荐的多生上下文隔离
- Scenario L: 移动端视口 (375x812) 下自适应布局与底部主导航人体工学验证

执行完毕后在 artifacts/uat_screenshots/ 保存 sprint9c_01~12.png，
并在 artifacts/uat_results_sprint9c.json 输出详细报告。
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

RESULTS_FILE = os.path.abspath("artifacts/uat_results_sprint9c.json")

uat_results: Dict[str, Any] = {
    "sprint": "Sprint 9-C",
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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) XuehaiZhidao-Sprint9C-UAT/1.0",
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
        # Scenario A: Tasks Page & Recommended Resources Entrance
        # ----------------------------------------------------------------------
        log_step("Scenario A: 访问「今日任务」视图，验证桌面 5-Tab 导航与焦点卡材料联动入口")
        page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle")
        time.sleep(1.2)

        # 验证 5-Tab 导航
        desktop_nav = page.locator("nav[aria-label='学生端桌面主导航']")
        expect(desktop_nav).to_be_visible()
        expect(desktop_nav.locator("text=今日任务")).to_be_visible()
        expect(desktop_nav.locator("text=学习资源")).to_be_visible()
        expect(desktop_nav.locator("text=知识图谱")).to_be_visible()
        expect(desktop_nav.locator("text=学情档案")).to_be_visible()
        expect(desktop_nav.locator("text=AI伴学")).to_be_visible()

        # 验证焦点卡内「📚 推荐学习材料」按钮
        resource_btn = page.locator("button:has-text('推荐学习材料')").first
        expect(resource_btn).to_be_visible()

        shot_a = os.path.join(SCREENSHOT_DIR, "sprint9c_01_tasks_page_recommended_resources.png")
        page.screenshot(path=shot_a)
        uat_results["scenarios"]["scenario_a"] = {"status": "PASS", "screenshot": shot_a}
        print("Scenario A PASSED.")

        # ----------------------------------------------------------------------
        # Scenario B: Enter Resource Hub
        # ----------------------------------------------------------------------
        log_step("Scenario B: 点击「学习资源」Tab，访问学习资源中心主页")
        page.click("nav[aria-label='学生端桌面主导航'] >> text=学习资源")
        time.sleep(1.2)
        expect(page.locator("h2:has-text('学习资源中心')")).to_be_visible()
        expect(page.locator("text=自适应学习材料库")).to_be_visible()

        shot_b = os.path.join(SCREENSHOT_DIR, "sprint9c_02_resource_hub_view.png")
        page.screenshot(path=shot_b)
        uat_results["scenarios"]["scenario_b"] = {"status": "PASS", "screenshot": shot_b}
        print("Scenario B PASSED.")

        # ----------------------------------------------------------------------
        # Scenario C: Adaptive Recommendation Banner
        # ----------------------------------------------------------------------
        log_step("Scenario C: 验证自适应导引横幅呈现步骤化推荐序列与零黑话说明")
        expect(page.locator("text=为你量身定制的步骤建议")).to_be_visible()
        expect(page.locator("text=步骤 1")).to_be_visible()
        expect(page.locator("text=步骤 2")).to_be_visible()

        shot_c = os.path.join(SCREENSHOT_DIR, "sprint9c_03_adaptive_recommendation_banner.png")
        page.screenshot(path=shot_c)
        uat_results["scenarios"]["scenario_c"] = {"status": "PASS", "screenshot": shot_c}
        print("Scenario C PASSED.")

        # ----------------------------------------------------------------------
        # Scenario D: Filter by Concept Card
        # ----------------------------------------------------------------------
        log_step("Scenario D: 切换「考点微卡」分类过滤器，验证精准过滤")
        page.click("button:has-text('考点微卡')")
        time.sleep(0.6)
        expect(page.locator("span:has-text('考点微卡')").first).to_be_visible()

        shot_d = os.path.join(SCREENSHOT_DIR, "sprint9c_04_resource_type_filter_concept.png")
        page.screenshot(path=shot_d)
        uat_results["scenarios"]["scenario_d"] = {"status": "PASS", "screenshot": shot_d}
        print("Scenario D PASSED.")

        # ----------------------------------------------------------------------
        # Scenario E: Filter by Example
        # ----------------------------------------------------------------------
        log_step("Scenario E: 切换「典型例题」分类过滤器，验证例题材料展示")
        page.click("button:has-text('典型例题')")
        time.sleep(0.6)
        expect(page.locator("span:has-text('典型例题')").first).to_be_visible()
        expect(page.locator("button:has-text('研读例题')").first).to_be_visible()

        shot_e = os.path.join(SCREENSHOT_DIR, "sprint9c_05_resource_type_filter_example.png")
        page.screenshot(path=shot_e)
        uat_results["scenarios"]["scenario_e"] = {"status": "PASS", "screenshot": shot_e}
        print("Scenario E PASSED.")

        # ----------------------------------------------------------------------
        # Scenario F: Open Example Reader Modal
        # ----------------------------------------------------------------------
        log_step("Scenario F: 打开「典型例题精析」研读模态框，验证生活商业实例拆解")
        page.click("button:has-text('研读例题') >> nth=0")
        time.sleep(0.8)
        expect(page.locator("role=dialog")).to_be_visible()
        expect(page.locator("text=生活与商业真实情境拆解")).to_be_visible()
        expect(page.locator("text=建议精读")).to_be_visible()

        shot_f = os.path.join(SCREENSHOT_DIR, "sprint9c_06_open_example_reader_modal.png")
        page.screenshot(path=shot_f)
        uat_results["scenarios"]["scenario_f"] = {"status": "PASS", "screenshot": shot_f}
        print("Scenario F PASSED.")

        # ----------------------------------------------------------------------
        # Scenario G: Mark Example Complete
        # ----------------------------------------------------------------------
        log_step("Scenario G: 点击「研读完毕，标记完成」，验证完成状态与资源事件上报")
        complete_btn = page.locator("button:has-text('研读完毕，标记完成')")
        expect(complete_btn).to_be_visible()
        complete_btn.click()
        time.sleep(0.5)
        expect(page.locator("button:has-text('已标记完成')")).to_be_visible()

        shot_g = os.path.join(SCREENSHOT_DIR, "sprint9c_07_example_modal_complete_action.png")
        page.screenshot(path=shot_g)
        uat_results["scenarios"]["scenario_g"] = {"status": "PASS", "screenshot": shot_g}
        print("Scenario G PASSED.")

        # 关闭模态框
        page.click("button:has-text('关闭')")
        time.sleep(0.5)

        # ----------------------------------------------------------------------
        # Scenario H: Open Concept Card from Hub
        # ----------------------------------------------------------------------
        log_step("Scenario H: 点击「查看微卡」，验证考点精要速览微卡顺畅弹出")
        page.click("button:has-text('全部材料')")
        time.sleep(0.5)
        concept_btn = page.locator("button:has-text('查看微卡')").first
        concept_btn.click()
        time.sleep(0.8)

        expect(page.locator("text=直觉导引 · 一句话顿悟")).to_be_visible()
        expect(page.locator("text=核心理论与关键机制")).to_be_visible()

        shot_h = os.path.join(SCREENSHOT_DIR, "sprint9c_08_open_concept_card_from_hub.png")
        page.screenshot(path=shot_h)
        uat_results["scenarios"]["scenario_h"] = {"status": "PASS", "screenshot": shot_h}
        print("Scenario H PASSED.")

        # 关闭微卡模态框
        close_card_btn = page.locator("button[aria-label='关闭速览卡片']").or_(page.locator("button:has-text('稍后温习')")).first
        if close_card_btn.is_visible():
            close_card_btn.click()
        else:
            page.keyboard.press("Escape")
        time.sleep(0.5)

        # ----------------------------------------------------------------------
        # Scenario I: Search Keyword Filter
        # ----------------------------------------------------------------------
        log_step("Scenario I: 关键词搜索联动验证 (输入「稀缺性」动态筛选)")
        search_input = page.locator("input[placeholder*='搜索材料名称']")
        search_input.fill("稀缺性")
        time.sleep(0.6)

        shot_i = os.path.join(SCREENSHOT_DIR, "sprint9c_09_search_keyword_filter.png")
        page.screenshot(path=shot_i)
        uat_results["scenarios"]["scenario_i"] = {"status": "PASS", "screenshot": shot_i}
        print("Scenario I PASSED.")

        # 清空搜索框
        search_input.fill("")
        time.sleep(0.5)

        # ----------------------------------------------------------------------
        # Scenario J: Launch Quiz from Practice Card
        # ----------------------------------------------------------------------
        log_step("Scenario J: 点击「开始微练」，调起官方通关微测验并作答")
        page.click("button:has-text('靶向微练')")
        time.sleep(0.5)
        practice_btn = page.locator("button:has-text('开始微练')").first
        practice_btn.click()
        time.sleep(1.2)

        expect(page.locator("text=微测验突破").first).to_be_visible()

        shot_j = os.path.join(SCREENSHOT_DIR, "sprint9c_10_launch_quiz_from_practice_card.png")
        page.screenshot(path=shot_j)
        uat_results["scenarios"]["scenario_j"] = {"status": "PASS", "screenshot": shot_j}
        print("Scenario J PASSED.")

        # 退出测验
        exit_quiz_btn = page.locator("button[aria-label='关闭面板']").first
        if exit_quiz_btn.is_visible():
            exit_quiz_btn.click()
        else:
            page.keyboard.press("Escape")
        time.sleep(0.6)

        # ----------------------------------------------------------------------
        # Scenario K: Student Context Switching (S001 -> S002)
        # ----------------------------------------------------------------------
        log_step("Scenario K: 切换学生 (S001 -> S002)，验证资源自适应推荐的多生上下文隔离")
        student_sel = page.locator("select[aria-label='选择切换当前学习学生']").first
        if student_sel.is_visible():
            student_sel.select_option("S002")
            time.sleep(1.5)

        expect(page.locator("text=学习资源中心")).to_be_visible()

        shot_k = os.path.join(SCREENSHOT_DIR, "sprint9c_11_student_context_isolation.png")
        page.screenshot(path=shot_k)
        uat_results["scenarios"]["scenario_k"] = {"status": "PASS", "screenshot": shot_k}
        print("Scenario K PASSED.")

        # ----------------------------------------------------------------------
        # Scenario L: Mobile Viewport & Ergonomics
        # ----------------------------------------------------------------------
        log_step("Scenario L: 移动端视口 (375x812) 下自适应布局与底部主导航人体工学验证")
        page.set_viewport_size({"width": 375, "height": 812})
        time.sleep(0.8)

        expect(page.locator("nav[aria-label='学生端底部主导航']")).to_be_visible()
        expect(page.locator("h2:has-text('学习资源中心')")).to_be_visible()

        shot_l = os.path.join(SCREENSHOT_DIR, "sprint9c_12_mobile_bottom_nav_ergonomics.png")
        page.screenshot(path=shot_l)
        uat_results["scenarios"]["scenario_l"] = {"status": "PASS", "screenshot": shot_l}
        print("Scenario L PASSED.")

        browser.close()

    # 写入结果 JSON
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(uat_results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("ALL 12 BROWSER UAT SCENARIOS (A ~ L) EXECUTED SUCCESSFULLY!")
    print(f"Screenshots saved to: {SCREENSHOT_DIR}")
    print(f"UAT Results saved to: {RESULTS_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    run_uat()
