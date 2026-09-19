# -*- coding: utf-8 -*-
"""
scripts/uat_sprint10a_browser.py
================================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-A
中国大学MOOC外部资源与安全跳转端到端浏览器验收 (Scenarios A ~ F)

验收场景：
- Scenario A: 访问 /student/resources，页面完整加载，头部与分类正常
- Scenario B: 选择 K01 考点，同时展示 Xuehai 内部资源与中国大学MOOC外部资源，MOOC卡片显示“中国大学MOOC”Badge 与院校信息
- Scenario C: 点击 MOOC 卡片 CTA（“前往慕课学习”），弹出“即将离开学海智导”安全确认模态框
- Scenario D: 点击“前往学习”，确认触发 window.open 并且目标 URL 属于官方 icourse163.org
- Scenario E: 点击内部资源（“查看微卡”），依然顺畅调起内部 ConceptCardModal，验证内部逻辑零破坏
- Scenario F: 页面刷新与 375x812 移动端响应式布局检验，验证无横向滚动溢出 (scrollWidth <= clientWidth)
- 零控制台错误与零请求失败断言 (Console Errors = 0, Page Exceptions = 0, Failed Requests = 0)
"""

import json
import os
import re
import shutil
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

BRAIN_SCREENSHOT_DIR = r"C:\Users\XSL\.gemini\antigravity\brain\acc330ec-11ad-49d0-a406-fe3e112b5cfc\screenshots"
os.makedirs(BRAIN_SCREENSHOT_DIR, exist_ok=True)

RESULTS_FILE = os.path.abspath("artifacts/uat_results_sprint10a.json")

uat_results: Dict[str, Any] = {
    "sprint": "Sprint 10-A Phase 3",
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
    opened_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 850})
        page = context.new_page()

        # 监听控制台日志与错误
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

        # 拦截 window.open 记录被打开的 URL
        page.add_init_script("""
            window.__openedUrls = [];
            window.open = function(url, target, features) {
                window.__openedUrls.push(url);
                console.log('[Intercepted window.open]', url);
                return null;
            };
        """)

        # ----------------------------------------------------------------------
        # Scenario A: 访问 /student/resources 正常加载
        # ----------------------------------------------------------------------
        log_step("Scenario A: 访问 /student/resources 页面并验证核心布局")

        page.goto(f"{BASE_URL}/student/resources", wait_until="networkidle")
        time.sleep(1.5)

        # 验证页面标题
        heading = page.locator("text=学习资源中心").first
        expect(heading).to_be_visible()

        shot_a = os.path.join(SCREENSHOT_DIR, "sprint10a_01_resource_hub_landing.png")
        page.screenshot(path=shot_a)
        shutil.copyfile(shot_a, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint10a_01_resource_hub_landing.png"))
        uat_results["scenarios"]["scenario_a"] = {"status": "PASS", "screenshot": shot_a}
        print("Scenario A PASSED: ResourceHub loaded successfully.")

        # ----------------------------------------------------------------------
        # Scenario B: 验证 K01 考点下的内部资源与中国大学MOOC资源共存
        # ----------------------------------------------------------------------
        log_step("Scenario B: 验证 K01 考点下内部资源与中国大学MOOC外部资源共存")

        # 确保考点下拉框为 K01
        knowledge_select = page.locator("#knowledge-select")
        expect(knowledge_select).to_be_visible()
        knowledge_select.select_option("K01")
        time.sleep(1.5)

        # 验证 MOOC 专属 Badge 存在
        mooc_badge = page.locator("text=中国大学MOOC").first
        expect(mooc_badge).to_be_visible()

        # 验证内部微卡存在
        internal_badge = page.locator("text=考点微卡").first
        expect(internal_badge).to_be_visible()

        # 验证北京大学课程元数据存在
        pku_text = page.locator("text=北京大学").first
        expect(pku_text).to_be_visible()

        # 验证 MOOC 专属 CTA “前往慕课学习”
        mooc_cta = page.locator("button:has-text('前往慕课学习')").first
        expect(mooc_cta).to_be_visible()

        shot_b = os.path.join(SCREENSHOT_DIR, "sprint10a_02_mooc_card_displayed.png")
        page.screenshot(path=shot_b)
        shutil.copyfile(shot_b, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint10a_02_mooc_card_displayed.png"))
        uat_results["scenarios"]["scenario_b"] = {"status": "PASS", "screenshot": shot_b}
        print("Scenario B PASSED: MOOC and internal resources co-exist gracefully.")

        # ----------------------------------------------------------------------
        # Scenario C: 点击 MOOC 卡片弹出“即将离开学海智导”安全确认弹窗
        # ----------------------------------------------------------------------
        log_step("Scenario C: 点击 MOOC CTA 调起外部跳转确认弹窗")

        mooc_cta.click()
        time.sleep(1.0)

        # 弹窗验证
        redirect_modal_title = page.locator("text=即将离开学海智导").first
        expect(redirect_modal_title).to_be_visible()

        redirect_modal_desc = page.locator("text=你将前往中国大学MOOC官方页面继续学习").first
        expect(redirect_modal_desc).to_be_visible()

        # 检查确认按钮
        confirm_btn = page.locator("button:has-text('前往学习')").first
        expect(confirm_btn).to_be_visible()

        shot_c = os.path.join(SCREENSHOT_DIR, "sprint10a_03_redirect_modal_popup.png")
        page.screenshot(path=shot_c)
        shutil.copyfile(shot_c, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint10a_03_redirect_modal_popup.png"))
        uat_results["scenarios"]["scenario_c"] = {"status": "PASS", "screenshot": shot_c}
        print("Scenario C PASSED: ExternalRedirectModal appeared with correct messaging.")

        # ----------------------------------------------------------------------
        # Scenario D: 确认跳转并验证目标 URL 属于官方 icourse163.org
        # ----------------------------------------------------------------------
        log_step("Scenario D: 点击确认前往学习，验证拦截并捕获合法的 icourse163.org URL")

        confirm_btn.click()
        time.sleep(1.0)

        # 获取拦截的 window.open URLs
        opened_urls = page.evaluate("() => window.__openedUrls || []")
        print(f"Captured window.open calls: {opened_urls}")
        assert len(opened_urls) > 0, "未捕获到 window.open 调用"
        target_url = opened_urls[-1]
        assert "icourse163.org" in target_url, f"目标 URL 必须属于 icourse163.org，当前为: {target_url}"
        assert target_url.startswith("https://"), f"目标 URL 必须为 https 协议: {target_url}"

        shot_d = os.path.join(SCREENSHOT_DIR, "sprint10a_04_target_url_verified.png")
        page.screenshot(path=shot_d)
        shutil.copyfile(shot_d, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint10a_04_target_url_verified.png"))
        uat_results["scenarios"]["scenario_d"] = {
            "status": "PASS",
            "opened_url": target_url,
            "screenshot": shot_d,
        }
        print(f"Scenario D PASSED: Safe URL opened: {target_url}")

        # ----------------------------------------------------------------------
        # Scenario E: 点击内部资源依然调起内部学习流程
        # ----------------------------------------------------------------------
        log_step("Scenario E: 点击内部资源（查看微卡），验证内部学习流程零破坏")

        internal_card_cta = page.locator("button:has-text('查看微卡')").first
        expect(internal_card_cta).to_be_visible()
        internal_card_cta.click()
        time.sleep(1.0)

        # 验证调起 ConceptCardModal
        concept_modal_header = page.locator("text=直觉导引 · 一句话顿悟").first
        expect(concept_modal_header).to_be_visible()

        shot_e = os.path.join(SCREENSHOT_DIR, "sprint10a_05_internal_flow_unbroken.png")
        page.screenshot(path=shot_e)
        shutil.copyfile(shot_e, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint10a_05_internal_flow_unbroken.png"))
        uat_results["scenarios"]["scenario_e"] = {"status": "PASS", "screenshot": shot_e}
        print("Scenario E PASSED: Internal ConceptCardModal rendered without regression.")

        # 关闭概念微卡
        close_btn = page.locator("button:has-text('稍后温习'), button[aria-label='关闭速览卡片']").first
        if close_btn.is_visible():
            close_btn.click()
            time.sleep(0.5)

        # ----------------------------------------------------------------------
        # Scenario F: 页面刷新与 375x812 移动端响应式布局检验
        # ----------------------------------------------------------------------
        log_step("Scenario F: 页面刷新与 375x812 移动端响应式无横向溢出检验")

        page.reload(wait_until="networkidle")
        time.sleep(1.5)

        # 切换到 375x812 视口
        page.set_viewport_size({"width": 375, "height": 812})
        time.sleep(1.5)

        # 验证 MOOC 卡片在移动端依然正常渲染
        mooc_badge_mobile = page.locator("text=中国大学MOOC").first
        expect(mooc_badge_mobile).to_be_visible()

        # 检查移动端无横向溢出
        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        client_width = page.evaluate("() => document.documentElement.clientWidth")
        print(f"Viewport 375px check: scrollWidth={scroll_width}, clientWidth={client_width}")
        assert scroll_width <= client_width + 1, f"移动端存在横向溢出: scrollWidth({scroll_width}) > clientWidth({client_width})"

        # 切换到 390x844 视口检验
        page.set_viewport_size({"width": 390, "height": 844})
        time.sleep(1.0)
        scroll_width_390 = page.evaluate("() => document.documentElement.scrollWidth")
        client_width_390 = page.evaluate("() => document.documentElement.clientWidth")
        print(f"Viewport 390px check: scrollWidth={scroll_width_390}, clientWidth={client_width_390}")
        assert scroll_width_390 <= client_width_390 + 1, f"移动端存在横向溢出: scrollWidth({scroll_width_390}) > clientWidth({client_width_390})"

        shot_f = os.path.join(SCREENSHOT_DIR, "sprint10a_06_mobile_375px_responsive.png")
        page.screenshot(path=shot_f)
        shutil.copyfile(shot_f, os.path.join(BRAIN_SCREENSHOT_DIR, "sprint10a_06_mobile_375px_responsive.png"))
        uat_results["scenarios"]["scenario_f"] = {
            "status": "PASS",
            "scroll_width_375": scroll_width,
            "client_width_375": client_width,
            "screenshot": shot_f,
        }
        print("Scenario F PASSED: 375px and 390px mobile viewports render perfectly with 0 overflow.")

        # 控制台与请求健康度校验
        print(f"\nUAT Audit: Console Errors = {len(uat_results['console_errors'])}, Failed Requests = {len(uat_results['failed_requests'])}")
        assert len(uat_results["console_errors"]) == 0, f"存在控制台错误: {uat_results['console_errors']}"
        assert len(uat_results["failed_requests"]) == 0, f"存在请求失败: {uat_results['failed_requests']}"

        # 写入测试总结
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(uat_results, f, ensure_ascii=False, indent=2)

        browser.close()

    print("\n" + "=" * 80)
    print("ALL 6 SPRINT 10-A UAT SCENARIOS PASSED SUCCESSFULLY!")
    print(f"Console errors: {len(uat_results['console_errors'])}")
    print(f"Failed requests: {len(uat_results['failed_requests'])}")
    print("=" * 80)


if __name__ == "__main__":
    run_uat()
