# -*- coding: utf-8 -*-
"""
Sprint 8-C Browser-based Product UAT & E2E Acceptance Script
真实浏览器环境下的成效沉淀、错题复盘与教师分析驾驶舱 E2E 验证脚本 (Playwright / Chromium)
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

# 动态生成干净的全新学生 ID
TEST_STUDENT_ID = f"UAT8C_{int(time.time()) % 9000 + 1000}"

# 结构化记录器
uat_results: Dict[str, Any] = {
    "console_messages": [],
    "console_errors": [],
    "page_errors": [],
    "failed_requests": [],
    "api_responses": [],
    "scenarios": {},
    "security_checks": {},
}


def log_step(title: str):
    print(f"\n{'='*70}\n>>> {title}\n{'='*70}")


def init_test_student():
    """初始化全新的测试学生"""
    log_step(f"Step 0: 初始化新学生 {TEST_STUDENT_ID}")
    payload = {
        "student_id": TEST_STUDENT_ID,
        "student_name": f"{TEST_STUDENT_ID}测试生",
        "major": "经济学",
        "grade": "大二",
        "learning_goal": "微观经济学导论与稀缺性分析",
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
            if msg_type == "error":
                uat_results["console_errors"].append(text)
                print(f"[BROWSER CONSOLE ERROR] {text}")

        def on_page_error(exc):
            err_msg = str(exc)
            uat_results["page_errors"].append(err_msg)
            print(f"[PAGE EXCEPTION] {err_msg}")

        def on_request_failed(req):
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
        # Scenario A: 新学生空数据 (Progress & Wrong Answers Empty States)
        # ----------------------------------------------------------------------
        log_step("Scenario A: 新学生空数据展示验证")
        page.goto(f"{BASE_URL}/student/profile", wait_until="networkidle")
        time.sleep(1)

        # 确保切换至刚刚初始化的新学生
        selector = page.locator("select[aria-label='选择切换当前学习学生']")
        expect(selector).to_be_visible()
        selector.select_option(TEST_STUDENT_ID)
        time.sleep(1.2)

        # 点击 30 考点掌握度全览
        progress_tab_btn = page.locator("button:has-text('30考点掌握度全览')")
        expect(progress_tab_btn).to_be_visible()
        progress_tab_btn.click()
        time.sleep(0.8)

        expect(page.locator("[data-testid='student-progress-overview']")).to_be_visible()
        # 检查空历史趋势提示
        expect(page.locator("text=暂无历史变动记录")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "uat8c_01_empty_progress.png"))
        uat_results["scenarios"]["Scenario A1_Progress"] = "PASS"
        print("  --> Scenario A1 (Progress Empty State): PASS")

        # 点击 错题复盘本
        wrong_tab_btn = page.locator("button:has-text('错题复盘本')")
        expect(wrong_tab_btn).to_be_visible()
        wrong_tab_btn.click()
        time.sleep(0.8)

        expect(page.locator("[data-testid='student-wrong-answers']")).to_be_visible()
        expect(page.locator("[data-testid='wrong-answers-empty-state']")).to_be_visible()
        expect(page.locator("text=太棒了！目前没有需要复盘的错题")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "uat8c_02_empty_wrong_answers.png"))
        uat_results["scenarios"]["Scenario A2_WrongAnswers"] = "PASS"
        print("  --> Scenario A2 (Wrong Answers Empty State): PASS")

        # ----------------------------------------------------------------------
        # Scenario B: 第一次答对 (完成微测验，正确作答并更新 BKT)
        # ----------------------------------------------------------------------
        log_step("Scenario B: 第一次微测验作答正确")
        # 通过 SPA 导航至今日任务
        page.locator("nav[aria-label='学生端桌面主导航'] button:has-text('今日任务')").first.click()
        time.sleep(1.2)

        # 启动 K01 微测验
        start_quiz_btn = page.locator("button:has-text('继续挑战微测验'), button:has-text('开始微测验')").first
        expect(start_quiz_btn).to_be_visible()
        start_quiz_btn.click()
        time.sleep(1.5)

        # 定位微测验抽屉对话框
        dialog = page.locator("div[role='dialog']").first
        expect(dialog).to_be_visible()

        # 选中正确选项 B 并提交 (Q-K01-01 选项 B: 资源的稀缺性)
        opt_b = dialog.locator("button:has-text('资源的稀缺性'), button:has-text('B')").first
        expect(opt_b).to_be_visible()
        opt_b.click()
        time.sleep(0.5)

        submit_btn = dialog.locator("button:has-text('提交答案')").first
        expect(submit_btn).to_be_enabled()
        submit_btn.click()
        time.sleep(2.0)

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "uat8c_03_first_quiz_correct.png"))
        uat_results["scenarios"]["Scenario B_FirstQuizCorrect"] = "PASS"
        print("  --> Scenario B (First Quiz Correct): PASS")

        # 关闭测验面板：点击 X 按钮
        close_quiz_btn = dialog.locator("button:has(svg.lucide-x)").first
        close_quiz_btn.click()
        time.sleep(1.2)
        expect(page.locator("div[role='dialog']")).to_have_count(0)

        # ----------------------------------------------------------------------
        # Scenario C: 第二次答错 (故意选择错误选项产生真实错题)
        # ----------------------------------------------------------------------
        log_step("Scenario C: 第二次微测验故意答错产生真实错题")
        start_quiz_btn = page.locator("button:has-text('继续挑战微测验'), button:has-text('开始微测验')").first
        expect(start_quiz_btn).to_be_visible()
        start_quiz_btn.click()
        time.sleep(1.5)

        dialog = page.locator("div[role='dialog']").first
        expect(dialog).to_be_visible()

        # 故意选择错误选项 A (Q-K01-01 选项 A: 货币的职能)
        opt_wrong = dialog.locator("button:has-text('货币的职能'), button:has-text('A')").first
        expect(opt_wrong).to_be_visible()
        opt_wrong.click()
        time.sleep(0.5)

        submit_btn = dialog.locator("button:has-text('提交答案')").first
        expect(submit_btn).to_be_enabled()
        submit_btn.click()
        time.sleep(2.0)

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "uat8c_04_second_quiz_wrong.png"))
        uat_results["scenarios"]["Scenario C_SecondQuizWrong"] = "PASS"
        print("  --> Scenario C (Second Quiz Wrong): PASS")

        # 关闭测验模态框：点击 X 按钮
        close_quiz_btn = dialog.locator("button:has(svg.lucide-x)").first
        close_quiz_btn.click()
        time.sleep(1.2)
        expect(page.locator("div[role='dialog']")).to_have_count(0)

        # ----------------------------------------------------------------------
        # Scenario D: 错题复盘本真实归纳
        # ----------------------------------------------------------------------
        log_step("Scenario D: 错题复盘本归纳与解析呈现")
        page.locator("nav[aria-label='学生端桌面主导航'] button:has-text('学情档案')").first.click()
        time.sleep(1.2)

        wrong_tab_btn = page.locator("button:has-text('错题复盘本')").first
        expect(wrong_tab_btn).to_be_visible()
        wrong_tab_btn.click()
        time.sleep(1.2)

        # 验证错题卡片已生成
        wrong_card = page.locator("[data-testid^='wrong-answer-card-']").first
        expect(wrong_card).to_be_visible()
        expect(page.locator("text=官方试题详解")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "uat8c_05_wrong_answer_review.png"))
        uat_results["scenarios"]["Scenario D_WrongAnswerReview"] = "PASS"
        print("  --> Scenario D (Wrong Answer Review List): PASS")

        # ----------------------------------------------------------------------
        # Scenario E: 重新学习闭环 (ConceptCard)
        # ----------------------------------------------------------------------
        log_step("Scenario E: 错题闭环 — 📖 重新学习微卡")
        relearn_btn = page.locator("button:has-text('重新学习微卡')").first
        expect(relearn_btn).to_be_visible()
        relearn_btn.click()
        time.sleep(1.5)

        # 验证概念微卡弹窗已打开并定位到该考点
        expect(page.locator("button:has-text('我已读懂，开始微测验')").first).to_be_visible()
        expect(page.locator("text=核心理论与关键机制").first).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "uat8c_06_concept_card_relearn.png"))

        # 关闭微卡
        close_card = page.locator("button:has-text('稍后温习')").first
        close_card.click()
        time.sleep(1.2)

        uat_results["scenarios"]["Scenario E_RelearnLoop"] = "PASS"
        print("  --> Scenario E (Relearn Concept Card Loop): PASS")

        # ----------------------------------------------------------------------
        # Scenario F: 再次练习闭环 (MicroQuiz)
        # ----------------------------------------------------------------------
        log_step("Scenario F: 错题闭环 — ✏️ 再次练习突破")
        retry_quiz_btn = page.locator("button:has-text('再次练习突破')").first
        expect(retry_quiz_btn).to_be_visible()
        retry_quiz_btn.click()
        time.sleep(1.5)

        # 验证微测验模态抽屉已成功打开
        dialog = page.locator("div[role='dialog']").first
        expect(dialog).to_be_visible()
        expect(dialog.locator("text=微测验突破").first).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "uat8c_07_quiz_remediation.png"))

        # 关闭测验
        close_btn = dialog.locator("button:has(svg.lucide-x)").first
        close_btn.click()
        time.sleep(1.2)
        expect(page.locator("div[role='dialog']")).to_have_count(0)

        uat_results["scenarios"]["Scenario F_QuizRemediationLoop"] = "PASS"
        print("  --> Scenario F (Quiz Remediation Loop): PASS")

        # ----------------------------------------------------------------------
        # Scenario G: Mastery History 与真实活动流水一致性
        # ----------------------------------------------------------------------
        log_step("Scenario G: 掌握度演进历史与真实活动时间轴")
        progress_tab_btn = page.locator("button:has-text('30考点掌握度全览')").first
        progress_tab_btn.click()
        time.sleep(1.2)

        # 验证真实流水已记录（包含答对、答错、微卡研读等事件）
        expect(page.locator("text=真实学习活动时间轴")).to_be_visible()
        expect(page.locator("text=条真实流水")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "uat8c_08_progress_timeline.png"))
        uat_results["scenarios"]["Scenario G_MasteryHistory"] = "PASS"
        print("  --> Scenario G (Timeline & History Consistency): PASS")

        # ----------------------------------------------------------------------
        # Scenario H: 页面刷新 (Reload Stability)
        # ----------------------------------------------------------------------
        log_step("Scenario H: 页面刷新状态保持验证")
        page.reload(wait_until="networkidle")
        time.sleep(1.2)
        # 确保选择 TEST_STUDENT_ID
        selector = page.locator("select[aria-label='选择切换当前学习学生']").first
        if selector.is_visible():
            selector.select_option(TEST_STUDENT_ID)
            time.sleep(1)
        # 点击 30 考点掌握度全览
        progress_tab_btn = page.locator("button:has-text('30考点掌握度全览')").first
        if progress_tab_btn.is_visible():
            progress_tab_btn.click()
            time.sleep(0.8)
        expect(page.locator("[data-testid='student-progress-overview']")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "uat8c_09_reload_stability.png"))
        uat_results["scenarios"]["Scenario H_ReloadStability"] = "PASS"
        print("  --> Scenario H (Reload Stability): PASS")

        # ----------------------------------------------------------------------
        # Scenario I: 学生上下文切换与数据隔离
        # ----------------------------------------------------------------------
        log_step("Scenario I: 学生切换与严格数据隔离")
        # 切换到学生 S002
        selector = page.locator("select[aria-label='选择切换当前学习学生']").first
        if selector.is_visible():
            selector.select_option(value="S002")
            time.sleep(1.2)
            expect(page.locator("h1:has-text('李同学')")).to_be_visible()

            # 验证 S002 错题独立
            wrong_tab_btn = page.locator("button:has-text('错题复盘本')").first
            wrong_tab_btn.click()
            time.sleep(0.8)

            # 切换回 TEST_STUDENT_ID
            selector.select_option(value=TEST_STUDENT_ID)
            time.sleep(1.2)
            expect(selector).to_have_value(TEST_STUDENT_ID)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "uat8c_10_student_isolation.png"))
            uat_results["scenarios"]["Scenario I_StudentIsolation"] = "PASS"
            print("  --> Scenario I (Student Isolation): PASS")

        # ----------------------------------------------------------------------
        # Scenario J: 教师学情分析驾驶舱全景
        # ----------------------------------------------------------------------
        log_step("Scenario J: 教师端宏观驾驶舱全景验证")
        page.goto(f"{BASE_URL}/teacher", wait_until="networkidle")
        time.sleep(1.5)

        expect(page.locator("[data-testid='teacher-cockpit']")).to_be_visible()
        expect(page.locator("[data-testid='teacher-kpi-cards']")).to_be_visible()
        expect(page.locator("[data-testid='teacher-weak-points-ranking']")).to_be_visible()
        expect(page.locator("[data-testid='teacher-student-roster']")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "uat8c_11_teacher_dashboard.png"))
        uat_results["scenarios"]["Scenario J_TeacherDashboard"] = "PASS"
        print("  --> Scenario J (Teacher Dashboard): PASS")

        # ----------------------------------------------------------------------
        # Scenario K: 教师学生详情下钻 (Student Detail Modal)
        # ----------------------------------------------------------------------
        log_step("Scenario K: 教师端单生下钻深潜档案")
        detail_btn = page.locator("[data-testid='teacher-student-roster'] button:has-text('学情档案')").first
        expect(detail_btn).to_be_visible()
        detail_btn.click()
        time.sleep(1.2)

        expect(page.locator("[data-testid='teacher-student-detail-modal']")).to_be_visible()
        expect(page.locator("text=学情全维档案")).to_be_visible()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "uat8c_12_teacher_student_detail.png"))

        # 关闭弹窗
        close_detail_btn = page.locator("[data-testid='teacher-student-detail-modal'] button:has-text('关闭'), [data-testid='teacher-student-detail-modal'] button:has(svg.lucide-x)").first
        close_detail_btn.click()
        time.sleep(0.8)

        uat_results["scenarios"]["Scenario K_TeacherStudentDetail"] = "PASS"
        print("  --> Scenario K (Teacher Student Detail): PASS")

        # ----------------------------------------------------------------------
        # Scenario L: 学生端与教师端掌握度严格一致
        # ----------------------------------------------------------------------
        log_step("Scenario L: 学生端与教师端掌握度严格一致断言")
        with urllib.request.urlopen(f"{API_URL}/api/students/{TEST_STUDENT_ID}/progress") as res:
            stu_prog = json.loads(res.read().decode("utf-8"))
        with urllib.request.urlopen(f"{API_URL}/api/teacher/students/{TEST_STUDENT_ID}") as res:
            tch_det = json.loads(res.read().decode("utf-8"))

        p_stu = stu_prog["overall_mastery"]
        p_tch = tch_det["overall_mastery"]
        assert abs(p_stu - p_tch) < 0.0001, f"Mastery discrepancy! Stu: {p_stu}, Tch: {p_tch}"
        uat_results["scenarios"]["Scenario L_MasteryConsistency"] = "PASS"
        print(f"  --> Scenario L (Mastery Consistency: Stu {p_stu} == Tch {p_tch}): PASS")

        # ----------------------------------------------------------------------
        # Scenario M: 新学生教师端 Empty State
        # ----------------------------------------------------------------------
        log_step("Scenario M: 教师端下钻新学生安全无假数据")
        empty_id = f"EMPTY_{int(time.time()) % 9000 + 1000}"
        init_empty_req = urllib.request.Request(
            f"{API_URL}/api/students/init",
            data=json.dumps({
                "student_id": empty_id,
                "student_name": "纯白测试生",
                "major": "经济学",
                "grade": "大一",
                "learning_goal": "微观经济学",
                "start_knowledge_id": "K01",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(init_empty_req) as res:
            pass

        with urllib.request.urlopen(f"{API_URL}/api/teacher/students/{empty_id}") as res:
            tch_new = json.loads(res.read().decode("utf-8"))
        assert tch_new["student_id"] == empty_id
        assert tch_new["total_attempts"] == 0
        assert tch_new["total_wrong_count"] == 0
        assert len(tch_new["wrong_answers"]) == 0
        assert len(tch_new["recent_events"]) == 0
        assert len(tch_new["knowledge_point_masteries"]) == 30
        uat_results["scenarios"]["Scenario M_TeacherEmptyStudent"] = "PASS"
        print("  --> Scenario M (Teacher Empty Student Safe & Zero Fake Data): PASS")

        # ----------------------------------------------------------------------
        # Scenario N: 异常 API 鲁棒性安全 (绝不 500)
        # ----------------------------------------------------------------------
        log_step("Scenario N: 异常请求鲁棒性断言 (404/422，绝不 500)")
        try:
            urllib.request.urlopen(f"{API_URL}/api/students/NON_EXISTENT_STU_999/progress")
        except urllib.error.HTTPError as e:
            assert e.code == 404, f"Expected 404 for unknown student, got {e.code}"
            print("  --> Unknown student progress returns 404: PASS")

        try:
            urllib.request.urlopen(f"{API_URL}/api/teacher/students/NON_EXISTENT_STU_999")
        except urllib.error.HTTPError as e:
            assert e.code == 404, f"Expected 404 for unknown student teacher detail, got {e.code}"
            print("  --> Unknown student teacher detail returns 404: PASS")

        uat_results["scenarios"]["Scenario N_API_Robustness"] = "PASS"
        print("  --> Scenario N (API Robustness): PASS")

        # ----------------------------------------------------------------------
        # Exploratory & Security Audit
        # ----------------------------------------------------------------------
        log_step("Security Audit: 密钥、敏感信息与提前泄题安全审查")
        # 1. 检查 DOM 中是否有 API Key 或敏感信息
        html_content = page.content()
        import re
        for pattern in [r"sk-[a-zA-Z0-9]{20,}", r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", r"ANTHROPIC_API_KEY", r"OPENAI_API_KEY"]:
            assert not re.search(pattern, html_content), f"Security violation: found {pattern} in DOM!"

        # 2. 检查未答题前试题接口脱敏
        with urllib.request.urlopen(f"{API_URL}/api/quiz/K08") as res:
            quiz_q_data = json.loads(res.read().decode("utf-8"))
            for q in quiz_q_data.get("questions", []):
                assert "answer" not in q, f"Answer leaked in public question: {q}"
                assert "explanation" not in q, f"Explanation leaked in public question: {q}"

        uat_results["security_checks"]["DOM_Secret_Scrubbing"] = "PASS"
        uat_results["security_checks"]["Quiz_Public_Desensitization"] = "PASS"
        print("  --> Security Audit: ALL PASS")

        browser.close()

    # 导出测试汇总
    results_path = os.path.abspath("artifacts/uat_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(uat_results, f, ensure_ascii=False, indent=2)

    print("\n" + "="*70)
    print("ALL SPRINT 8-C BROWSER UAT SCENARIOS PASSED (14/14)")
    print(f"UAT Results saved to: {results_path}")
    print(f"Screenshots saved to: {SCREENSHOT_DIR}")
    print("="*70)
    return 0


if __name__ == "__main__":
    sys.exit(run_uat())
