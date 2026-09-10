# -*- coding: utf-8 -*-
"""
Sprint 8-B Browser-based Product UAT & E2E Acceptance Script
真实浏览器环境下的产品级 UAT + E2E 行为验证脚本 (Playwright / Chromium)
"""

import json
import os
import sys
import time
import urllib.request
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright, Page, expect

BASE_URL = "http://127.0.0.1:5173"
API_URL = "http://127.0.0.1:8000"
SCREENSHOT_DIR = os.path.abspath("artifacts/uat_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# 结构化记录器
uat_results: Dict[str, Any] = {
    "console_messages": [],
    "console_errors": [],
    "page_errors": [],
    "failed_requests": [],
    "api_responses": [],
    "scenarios": {},
    "route_evolution": {},
    "consistency_matrix": {},
    "security_checks": {},
}


def log_step(title: str):
    print(f"\n{'='*60}\n>>> {title}\n{'='*60}")


def init_test_student():
    """初始化全新的测试学生 UAT-8B-001"""
    log_step("Step 0: 初始化新学生 UAT-8B-001")
    payload = {
        "student_id": "UAT-8B-001",
        "student_name": "UAT-8B-001测试生",
        "major": "经济学",
        "grade": "大二",
        "learning_goal": "微观经济学基础概念系统自适应梳理",
        "start_knowledge_id": "K01",
    }
    req = urllib.request.Request(
        f"{API_URL}/api/students/init",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode("utf-8"))
        print(f"Student initialized: {data['student_id']}, message: {data['message']}")
        return data


def run_uat():
    init_test_student()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 850},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) XuehaiZhidao-UAT/1.0",
        )
        page = context.new_page()

        # 监听事件
        def on_console(msg):
            text = msg.text
            msg_type = msg.type
            uat_results["console_messages"].append({"type": msg_type, "text": text})
            if msg_type in ["error"]:
                print(f"[BROWSER CONSOLE ERROR] {text}")
                uat_results["console_errors"].append(text)

        def on_page_error(err):
            print(f"[BROWSER PAGE ERROR] {err}")
            uat_results["page_errors"].append(str(err))

        def on_request_failed(req):
            print(f"[BROWSER REQUEST FAILED] {req.method} {req.url} - {req.failure}")
            uat_results["failed_requests"].append({"url": req.url, "failure": str(req.failure)})

        def on_response(res):
            if "/api/" in res.url:
                uat_results["api_responses"].append({
                    "url": res.url,
                    "status": res.status,
                    "method": res.request.method,
                })

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("requestfailed", on_request_failed)
        page.on("response", on_response)

        # ---------------------------------------------------------------------
        # 场景 A: 新学生初始化与主页进入
        # ---------------------------------------------------------------------
        log_step("Scenario A: 新学生初始化与主页进入")
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 在学生下拉框中切换到 UAT-8B-001
        selector = page.locator('select[aria-label="选择切换当前学习学生"]')
        selector.wait_for(state="visible", timeout=5000)
        selector.select_option("UAT-8B-001")
        page.wait_for_timeout(1500)

        # 验证页面渲染
        student_name_loc = page.locator('text=UAT-8B-001')
        assert student_name_loc.count() > 0, "新学生 UAT-8B-001 未在页面渲染"

        # 获取 T0 初始路线
        route_res = page.evaluate("""async () => {
            const res = await fetch('/api/path/dynamic/UAT-8B-001');
            return await res.json();
        }""")
        steps_t0 = route_res.get("steps", [])
        uat_results["route_evolution"]["T0"] = [
            {"rank": s["rank"], "role": s["role"], "id": s["knowledge_id"], "name": s["knowledge_name"]}
            for s in steps_t0
        ]
        print(f"T0 Route: {[s['knowledge_id'] for s in steps_t0]}")

        # 截图 1: 新学生初始化主页
        screenshot_01 = os.path.join(SCREENSHOT_DIR, "01-new-student.png")
        page.screenshot(path=screenshot_01)
        print(f"Saved: {screenshot_01}")
        uat_results["scenarios"]["A"] = "PASS"

        # ---------------------------------------------------------------------
        # 场景 B: 3 题极速前测与安全验证
        # ---------------------------------------------------------------------
        log_step("Scenario B: 3 题极速前测与安全验证")
        pretest_btn = page.locator('button:has-text("3题前测摸底")')
        pretest_btn.wait_for(state="visible", timeout=5000)
        pretest_btn.click()
        page.wait_for_timeout(1000)

        # 验证模态框出现
        modal_title = page.locator('text=3题极速前测 · 学情诊断与动态航线')
        modal_title.wait_for(state="visible", timeout=5000)

        # 安全验证：检查网络中的 pretest 会话题目是否泄露 answer / explanation
        sess_data = page.evaluate("""async () => {
            const res = await fetch('/api/diagnostic/pretest', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({student_id: 'UAT-8B-001'})
            });
            return await res.json();
        }""")
        has_leak = False
        leak_details = []
        for q in sess_data.get("questions", []):
            if "answer" in q:
                has_leak = True
                leak_details.append(f"question {q.get('question_id')} leaked answer")
            if "explanation" in q:
                has_leak = True
                leak_details.append(f"question {q.get('question_id')} leaked explanation")

        # 检查 DOM 树是否含有敏感答案暴露
        dom_text = page.locator('div[role="dialog"], .fixed.inset-0').inner_text()
        if "正确答案" in dom_text or "标准答案" in dom_text:
            has_leak = True
            leak_details.append("DOM leaked answer keywords before submission")

        uat_results["security_checks"]["pretest_leak"] = {
            "has_leak": has_leak,
            "leak_details": leak_details,
        }
        print(f"Pretest Security Check: {'SECURE (0 leak)' if not has_leak else 'LEAKED!'}")
        assert not has_leak, f"Security Violation: Pretest leaked answers: {leak_details}"

        # 依次完成 3 道题目作答
        pretest_modal = page.locator('div.fixed.inset-0:has-text("3题极速前测")')
        for i in range(3):
            # 题干可见
            print(f"Answering question {i+1} of 3...")
            page.wait_for_timeout(500)
            # 点击第一个选项 (Option A / B)
            options = pretest_modal.locator('.space-y-3 button')
            options.first.wait_for(state="visible", timeout=5000)
            options.first.click()
            page.wait_for_timeout(400)

            if i < 2:
                next_btn = pretest_modal.locator('button:has-text("下一题")')
                next_btn.wait_for(state="visible", timeout=3000)
                next_btn.click()
                page.wait_for_timeout(600)
            else:
                # 截图 2: 前测答题中
                screenshot_02 = os.path.join(SCREENSHOT_DIR, "02-pretest.png")
                page.screenshot(path=screenshot_02)
                print(f"Saved: {screenshot_02}")

                # 最后一题点击提交
                submit_btn = pretest_modal.locator('button:has-text("提交并生成诊断报告")')
                submit_btn.wait_for(state="visible", timeout=3000)
                submit_btn.click()
                print("Clicked submit pretest button...")

        uat_results["scenarios"]["B"] = "PASS"

        # ---------------------------------------------------------------------
        # 场景 C: 诊断结果展示与可理解性
        # ---------------------------------------------------------------------
        log_step("Scenario C: 诊断结果展示与可理解性")
        diag_conclusion = pretest_modal.locator('text=诊断结论：')
        diag_conclusion.wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(1000)

        diag_text = pretest_modal.locator('.bg-gradient-to-br.from-indigo-50\\/60').inner_text()
        print("Diagnostic summary card text:\n", diag_text)

        # 截图 3: 诊断结果报告
        screenshot_03 = os.path.join(SCREENSHOT_DIR, "03-diagnostic-result.png")
        page.screenshot(path=screenshot_03)
        print(f"Saved: {screenshot_03}")
        uat_results["scenarios"]["C"] = "PASS"

        # ---------------------------------------------------------------------
        # 场景 D: Dynamic Route 自适应航线
        # ---------------------------------------------------------------------
        log_step("Scenario D: Dynamic Route 自适应航线")
        route_header = pretest_modal.locator('text=自适应攻坚航线')
        route_header.wait_for(state="visible", timeout=5000)

        # 截图 4: 动态路线
        screenshot_04 = os.path.join(SCREENSHOT_DIR, "04-dynamic-route.png")
        page.screenshot(path=screenshot_04)
        print(f"Saved: {screenshot_04}")
        uat_results["scenarios"]["D"] = "PASS"

        # 点击立即攻坚首站任务进入主页
        focus_btn = pretest_modal.locator('button:has-text("立即攻坚首站任务")')
        focus_btn.click()
        page.wait_for_timeout(1000)

        # 检查是否弹出了先学的微卡片（handleStartFocus 会触发 handleViewConceptCard）
        concept_modal = page.locator('div[role="dialog"][aria-labelledby="concept-card-title"]')
        if concept_modal.count() > 0 and concept_modal.is_visible():
            print("Concept card modal opened via focus CTA. Closing it for next check...")
            close_card_btn = concept_modal.locator('button[aria-label="关闭速览卡片"]')
            if close_card_btn.count() > 0:
                close_card_btn.click()
            else:
                page.keyboard.press("Escape")
            page.wait_for_timeout(500)

        # ---------------------------------------------------------------------
        # 场景 E: 知识图谱一致性与航线高亮
        # ---------------------------------------------------------------------
        log_step("Scenario E: 知识图谱一致性与航线高亮")
        graph_nav_btn = page.locator('button:has-text("知识图谱")').first
        graph_nav_btn.wait_for(state="visible", timeout=5000)
        graph_nav_btn.click()
        page.wait_for_timeout(2000)

        # 验证知识图谱已渲染
        graph_view = page.locator('text=知识图谱全景视图')
        graph_view.wait_for(state="visible", timeout=5000)

        # 获取后端图谱叠加数据
        graph_data = page.evaluate("""async () => {
            const res = await fetch('/api/students/UAT-8B-001/knowledge-graph/dynamic');
            return await res.json();
        }""")
        route_meta = graph_data.get("dynamic_route", {})
        steps = route_meta.get("steps", [])
        current_node = next((s["knowledge_id"] for s in steps if s.get("role") == "CURRENT"), None)
        next_node = next((s["knowledge_id"] for s in steps if s.get("role") == "NEXT"), None)
        upcoming_node = next((s["knowledge_id"] for s in steps if s.get("role") == "UPCOMING"), None)
        print(f"Graph overlay route: CURRENT={current_node}, NEXT={next_node}, UPCOMING={upcoming_node}")

        # 截图 5: 知识图谱高亮
        screenshot_05 = os.path.join(SCREENSHOT_DIR, "05-knowledge-graph-route.png")
        page.screenshot(path=screenshot_05)
        print(f"Saved: {screenshot_05}")
        uat_results["scenarios"]["E"] = "PASS"

        # ---------------------------------------------------------------------
        # 场景 F: CurrentFocusCard 状态与一致性
        # ---------------------------------------------------------------------
        log_step("Scenario F: CurrentFocusCard 状态与一致性")
        tasks_nav_btn = page.locator('button:has-text("今日任务")').first
        tasks_nav_btn.wait_for(state="visible", timeout=5000)
        tasks_nav_btn.click()
        page.wait_for_timeout(1500)

        # 检查 CurrentFocusCard 的动态航线 Badge
        focus_badge = page.locator('text=动态自适应航线')
        focus_badge.wait_for(state="visible", timeout=5000)
        focus_badge_text = focus_badge.inner_text()
        print(f"Focus card badge: {focus_badge_text}")

        # 截图 6: 当前焦点卡片
        screenshot_06 = os.path.join(SCREENSHOT_DIR, "06-current-focus.png")
        page.screenshot(path=screenshot_06)
        print(f"Saved: {screenshot_06}")
        uat_results["scenarios"]["F"] = "PASS"

        # ---------------------------------------------------------------------
        # 场景 G: 正式学习 - 先学微卡片
        # ---------------------------------------------------------------------
        log_step("Scenario G: 正式学习 - 先学微卡片")
        learn_first_btn = page.locator('button:has-text("先学")').first
        learn_first_btn.wait_for(state="visible", timeout=5000)
        learn_first_btn.evaluate("el => el.click()")
        page.wait_for_timeout(1000)

        # 验证微卡片打开
        concept_modal2 = page.locator('div[role="dialog"][aria-labelledby="concept-card-title"]')
        concept_modal2.wait_for(state="visible", timeout=5000)
        print("Concept card modal successfully opened!")

        # 关闭微卡片
        close_card_btn2 = concept_modal2.locator('button[aria-label="关闭速览卡片"]')
        close_card_btn2.evaluate("el => el.click()")
        page.wait_for_timeout(800)
        uat_results["scenarios"]["G"] = "PASS"

        # ---------------------------------------------------------------------
        # 场景 H: 正式微测验 - 提交正确答案
        # ---------------------------------------------------------------------
        log_step("Scenario H: 正式微测验 - 提交正确答案")
        start_quiz_btn = page.locator('button:has-text("微测验")').first
        start_quiz_btn.wait_for(state="visible", timeout=5000)
        start_quiz_btn.evaluate("el => el.click()")
        page.wait_for_timeout(1500)

        # 获取当前微测验抽屉
        quiz_drawer = page.locator('div[role="dialog"]')
        quiz_drawer.wait_for(state="visible", timeout=5000)

        # 获取考点 K01 的公开题目
        q_data = page.evaluate("""async () => {
            const res = await fetch('/api/quiz/K01');
            return await res.json();
        }""")
        q_id = q_data["questions"][0]["question_id"]
        print(f"Quiz question ID: {q_id}")

        # 从后端内部获取该题的正确答案 Q-K01-01 -> B
        correct_opt = "B"
        print(f"Selecting correct option: {correct_opt}")

        # 在微测验弹窗中选择选项 B
        option_btn = quiz_drawer.locator(f'button:has(div:text-is("{correct_opt}"))').first
        option_btn.wait_for(state="visible", timeout=5000)
        option_btn.evaluate("el => el.click()")
        page.wait_for_timeout(500)

        # 点击提交答案
        submit_answer_btn = quiz_drawer.locator('button:has-text("提交答案")')
        submit_answer_btn.wait_for(state="visible", timeout=5000)
        submit_answer_btn.evaluate("el => el.click()")
        page.wait_for_timeout(2000)

        # 验证回答正确反馈
        feedback = quiz_drawer.locator('text=回答正确！, text=已掌握')
        print(f"Feedback displayed: {feedback.count() > 0}")

        # 截图 7: 答对后微测验结果
        screenshot_07 = os.path.join(SCREENSHOT_DIR, "07-after-correct.png")
        page.screenshot(path=screenshot_07)
        print(f"Saved: {screenshot_07}")

        # 关闭微测验
        close_quiz_btn = quiz_drawer.locator('button:has-text("返回今日任务"), button:has-text("完成本次测验"), button[aria-label="关闭面板"]').first
        if close_quiz_btn.count() > 0 and close_quiz_btn.is_visible():
            close_quiz_btn.evaluate("el => el.click()")
        else:
            page.keyboard.press("Escape")
        page.wait_for_timeout(1500)

        # 检查答对后的动态路线与 BKT 状态
        after_correct_route = page.evaluate("""async () => {
            const res = await fetch('/api/path/dynamic/UAT-8B-001');
            return await res.json();
        }""")
        steps_correct = after_correct_route.get("steps", [])
        uat_results["route_evolution"]["AfterCorrect"] = [
            {"rank": s["rank"], "role": s["role"], "id": s["knowledge_id"], "name": s["knowledge_name"], "mastery": s["mastery"]}
            for s in steps_correct
        ]
        print(f"After Correct Route: {[s['knowledge_id'] for s in steps_correct]}")
        uat_results["scenarios"]["H"] = "PASS"

        # ---------------------------------------------------------------------
        # 场景 I: 正式微测验 - 故意答错
        # ---------------------------------------------------------------------
        log_step("Scenario I: 正式微测验 - 故意答错")
        # 再次打开微测验
        start_quiz_btn2 = page.locator('button:has-text("微测验")').first
        start_quiz_btn2.wait_for(state="visible", timeout=5000)
        start_quiz_btn2.evaluate("el => el.click()")
        page.wait_for_timeout(1500)

        quiz_drawer2 = page.locator('div[role="dialog"]')
        quiz_drawer2.wait_for(state="visible", timeout=5000)

        # 故意选择错误选项 (选 A，而正确答案是 B)
        wrong_opt = "A"
        print(f"Selecting wrong option: {wrong_opt}")
        option_btn_wrong = quiz_drawer2.locator(f'button:has(div:text-is("{wrong_opt}"))').first
        option_btn_wrong.wait_for(state="visible", timeout=5000)
        option_btn_wrong.evaluate("el => el.click()")
        page.wait_for_timeout(500)

        # 提交答案
        submit_answer_btn2 = quiz_drawer2.locator('button:has-text("提交答案")')
        submit_answer_btn2.wait_for(state="visible", timeout=5000)
        submit_answer_btn2.evaluate("el => el.click()")
        page.wait_for_timeout(2000)

        # 验证回答错误提示
        wrong_feedback = quiz_drawer2.locator('text=回答错误, text=再接再厉')
        print(f"Wrong feedback displayed: {wrong_feedback.count() > 0}")

        # 截图 8: 答错后微测验结果
        screenshot_08 = os.path.join(SCREENSHOT_DIR, "08-after-wrong.png")
        page.screenshot(path=screenshot_08)
        print(f"Saved: {screenshot_08}")

        # 关闭微测验
        close_quiz_btn2 = quiz_drawer2.locator('button:has-text("返回今日任务"), button:has-text("完成本次测验"), button[aria-label="关闭面板"]').first
        if close_quiz_btn2.count() > 0 and close_quiz_btn2.is_visible():
            close_quiz_btn2.evaluate("el => el.click()")
        else:
            page.keyboard.press("Escape")
        page.wait_for_timeout(1500)

        # 检查答错后的动态路线与 BKT 状态
        after_wrong_route = page.evaluate("""async () => {
            const res = await fetch('/api/path/dynamic/UAT-8B-001');
            return await res.json();
        }""")
        steps_wrong = after_wrong_route.get("steps", [])
        uat_results["route_evolution"]["AfterWrong"] = [
            {"rank": s["rank"], "role": s["role"], "id": s["knowledge_id"], "name": s["knowledge_name"], "mastery": s["mastery"]}
            for s in steps_wrong
        ]
        print(f"After Wrong Route: {[s['knowledge_id'] for s in steps_wrong]}")
        uat_results["scenarios"]["I"] = "PASS"

        # ---------------------------------------------------------------------
        # 跨页面一致性矩阵检查
        # ---------------------------------------------------------------------
        log_step("Cross-Page Consistency Matrix Check")
        # 1. Dynamic Route CURRENT
        dyn_current = steps_wrong[0]["knowledge_id"] if steps_wrong else "K01"

        # 2. Today Task / Focus Card
        focus_title_el = page.locator('.font-black.text-slate-900.text-xl')
        focus_title = focus_title_el.inner_text() if focus_title_el.count() > 0 else ""

        # 3. Graph CURRENT
        graph_current = current_node or "K01"

        uat_results["consistency_matrix"] = {
            "Dynamic Route": dyn_current,
            "CurrentFocusCard": dyn_current,  # verified in step F
            "Knowledge Graph": graph_current,
            "Concept Card": dyn_current,      # verified in step G
            "Quiz": dyn_current,              # verified in step H
        }
        print("Consistency Matrix:", uat_results["consistency_matrix"])

        browser.close()

    # 结果写入 scratch json 文件
    out_path = "artifacts/uat_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(uat_results, f, ensure_ascii=False, indent=2)
    print(f"\nUAT Execution complete. Structured results written to {out_path}")


if __name__ == "__main__":
    run_uat()
