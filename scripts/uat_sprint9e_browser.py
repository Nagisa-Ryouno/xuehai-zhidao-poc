# -*- coding: utf-8 -*-
"""
scripts/uat_sprint9e_browser.py
===============================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-E
学习保持度验证与资源策略自适应 Lite 端到端浏览器验收 (6 Browser Scenarios A ~ F)

使用 Playwright Chromium 对 Sprint 9-E 全部产品功能与用户旅程进行端到端闭环验收：
- Scenario A: 访问学习资源中心，验证候选资源基于真实历史成效的确定性重排序（例题跃居第一步）
- Scenario B: 验证高成效资源卡片展示「💡 为什么推荐？」及确定性解释文案
- Scenario C: 验证较弱成效资源卡片展示「🔄 这次换一种方式试试」及反思文案
- Scenario D: 切换至无历史数据的考点，验证优雅降级（INSUFFICIENT_DATA 零伪造历史标签）
- Scenario E: 切换学生 (S001 -> S002)，验证自适应排序与微调状态的多学生上下文严格隔离
- Scenario F: 移动端视口 (375x812) 下卡片自适应、文字换行与无横向滚动条验证

执行完毕后在 artifacts/uat_screenshots/ 保存 sprint9e_01~06.png，
并在 artifacts/uat_results_sprint9e.json 输出详细报告。
"""

import json
import os
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

RESULTS_FILE = os.path.abspath("artifacts/uat_results_sprint9e.json")

uat_results: Dict[str, Any] = {
    "sprint": "Sprint 9-E",
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
        # Scenario A: Candidate Resource Reordering based on Historical Effectiveness
        # ----------------------------------------------------------------------
        log_step("Scenario A: 访问学习资源中心，验证候选资源基于历史成效的二次重排序（例题跃居第一步）")
        page.goto(f"{BASE_URL}/student/resources", wait_until="networkidle")
        time.sleep(1.5)

        expect(page.locator("h2:has-text('学习资源中心')")).to_be_visible()

        # 确保考点选择为 K08
        kp_select = page.locator("select#knowledge-select")
        expect(kp_select).to_be_visible()
        kp_select.select_option("K08")
        time.sleep(1.5)

        expect(page.locator("text=为你量身定制的步骤建议")).to_be_visible()

        # 验证推荐卡片列表
        rec_cards = page.locator("[data-testid='recommended-resource-card']")
        expect(rec_cards.first).to_be_visible()
        card_count = rec_cards.count()
        assert card_count >= 3, f"期望至少 3 个推荐卡片，实际找到 {card_count}"

        # 验证第一步卡片为「典型例题」
        first_card = rec_cards.nth(0)
        expect(first_card.locator("text=步骤 1")).to_be_visible()
        expect(first_card.locator("text=典型生活与商业实例精析")).to_be_visible()

        shot_a = os.path.join(SCREENSHOT_DIR, "sprint9e_01_resource_hub_adaptive_ranking.png")
        page.screenshot(path=shot_a)
        shutil.copyfile(shot_a, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9e_01_resource_hub_adaptive_ranking.png"))
        uat_results["scenarios"]["scenario_a"] = {"status": "PASS", "screenshot": shot_a}
        print("Scenario A PASSED.")

        # ----------------------------------------------------------------------
        # Scenario B: High Effectiveness Card Displays Why Recommended & Narrative
        # ----------------------------------------------------------------------
        log_step("Scenario B: 验证高成效资源展示「💡 为什么推荐？」及确定性解释文案")
        expect(first_card.locator("text=💡 为什么推荐？")).to_be_visible()
        expect(first_card.locator("text=成效优选 (+2)")).to_be_visible()
        expect(first_card.locator("text=你之前用这种学习方式时，掌握情况有过比较明显的提升。")).to_be_visible()

        shot_b = os.path.join(SCREENSHOT_DIR, "sprint9e_02_why_recommended_badge_and_narrative.png")
        page.screenshot(path=shot_b)
        shutil.copyfile(shot_b, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9e_02_why_recommended_badge_and_narrative.png"))
        uat_results["scenarios"]["scenario_b"] = {"status": "PASS", "screenshot": shot_b}
        print("Scenario B PASSED.")

        # ----------------------------------------------------------------------
        # Scenario C: Ineffective Resource Card Displays Try Alternative Badge
        # ----------------------------------------------------------------------
        log_step("Scenario C: 验证较弱成效资源卡片展示「🔄 这次换一种方式试试」及反思文案")
        third_card = rec_cards.nth(2)
        expect(third_card.locator("text=步骤 3")).to_be_visible()
        expect(third_card.locator("text=🔄 这次换一种方式试试")).to_be_visible()
        expect(third_card.locator("text=你之前用这种学习方式时，提升比较有限，这次换一种方式试试。")).to_be_visible()

        shot_c = os.path.join(SCREENSHOT_DIR, "sprint9e_03_ineffective_try_alternative_card.png")
        page.screenshot(path=shot_c)
        shutil.copyfile(shot_c, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9e_03_ineffective_try_alternative_card.png"))
        uat_results["scenarios"]["scenario_c"] = {"status": "PASS", "screenshot": shot_c}
        print("Scenario C PASSED.")

        # ----------------------------------------------------------------------
        # Scenario D: Insufficient Data / No History Graceful Fallback
        # ----------------------------------------------------------------------
        log_step("Scenario D: 切换至无历史数据的考点 (K15)，验证优雅降级（零伪造历史成效标签）")
        kp_select.select_option("K15")
        time.sleep(1.5)

        k15_rec_cards = page.locator("[data-testid='recommended-resource-card']")
        expect(k15_rec_cards.first).to_be_visible()

        # 验证 K15 卡片不含历史成效徽章
        expect(page.locator("text=💡 为什么推荐？")).not_to_be_visible()
        expect(page.locator("text=🔄 这次换一种方式试试")).not_to_be_visible()
        expect(page.locator("text=成效优选")).not_to_be_visible()

        shot_d = os.path.join(SCREENSHOT_DIR, "sprint9e_04_insufficient_data_graceful_fallback.png")
        page.screenshot(path=shot_d)
        shutil.copyfile(shot_d, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9e_04_insufficient_data_graceful_fallback.png"))
        uat_results["scenarios"]["scenario_d"] = {"status": "PASS", "screenshot": shot_d}
        print("Scenario D PASSED.")

        # ----------------------------------------------------------------------
        # Scenario E: Multi-Student Adaptation Isolation
        # ----------------------------------------------------------------------
        log_step("Scenario E: 切换学生 (S001 -> S002)，验证自适应排序与微调状态的多学生上下文严格隔离")
        student_switch = page.locator("select#student-select")
        if student_switch.is_visible():
            student_switch.select_option("S002")
            time.sleep(1.5)

        # 切换回 K08
        kp_select.select_option("K08")
        time.sleep(1.5)

        # 验证 S002 不继承 S001 在 K08 上的微调历史
        expect(page.locator("text=成效优选 (+2)")).not_to_be_visible()
        expect(page.locator("text=🔄 这次换一种方式试试")).not_to_be_visible()

        shot_e = os.path.join(SCREENSHOT_DIR, "sprint9e_05_multi_student_adaptation_isolation.png")
        page.screenshot(path=shot_e)
        shutil.copyfile(shot_e, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9e_05_multi_student_adaptation_isolation.png"))
        uat_results["scenarios"]["scenario_e"] = {"status": "PASS", "screenshot": shot_e}
        print("Scenario E PASSED.")

        # ----------------------------------------------------------------------
        # Scenario F: Mobile 375px Ergonomics & No Horizontal Scrollbar
        # ----------------------------------------------------------------------
        log_step("Scenario F: 移动端视口 (375x812) 下卡片自适应、文字换行与无横向滚动条验证")
        # 切换回 S001 查看成效徽章在移动端的显示效果
        student_switch.select_option("S001")
        kp_select.select_option("K08")
        time.sleep(1.5)

        page.set_viewport_size({"width": 375, "height": 812})
        time.sleep(1.2)

        expect(page.locator("h2:has-text('学习资源中心')")).to_be_visible()
        expect(page.locator("text=💡 为什么推荐？").first).to_be_visible()

        # 严格验证移动端无横向滚动条
        overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
        assert not overflow, "移动端视口存在横向溢出滚动条!"

        shot_f = os.path.join(SCREENSHOT_DIR, "sprint9e_06_mobile_375px_ergonomics_no_overflow.png")
        page.screenshot(path=shot_f)
        shutil.copyfile(shot_f, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint9e_06_mobile_375px_ergonomics_no_overflow.png"))
        uat_results["scenarios"]["scenario_f"] = {"status": "PASS", "screenshot": shot_f}
        print("Scenario F PASSED.")

        context.close()
        browser.close()

    # 写入测试报告
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(uat_results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 75)
    print(f"[SUCCESS] ALL 6 SPRINT 9-E BROWSER SCENARIOS PASSED!")
    print(f"Screenshots saved to: {SCREENSHOT_DIR}")
    print(f"Artifacts synced to: {BRAIN_SCREENSHOT_DIR}")
    print(f"Results report saved to: {RESULTS_FILE}")
    print("=" * 75)


if __name__ == "__main__":
    run_uat()
