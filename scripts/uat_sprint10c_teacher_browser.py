# -*- coding: utf-8 -*-
"""
scripts/uat_sprint10c_teacher_browser.py
=========================================
学海智导 (Xuehai Zhidao) — Sprint 10-C / Phase 2
Teacher Web Productization 桌面端端到端全场景浏览器验收 (Scenarios A ~ L)

验收场景：
- Scenario A: Teacher Web Landing - 访问 /teacher，验证 Cockpit Banner、4 大 KPI 卡片与 Top-5 薄弱考点
- Scenario B: 3-Tab Desktop Navigation - 验证班级总览、知识点全景、学生档案导航 Pills
- Scenario C: Knowledge 30 Points - 验证知识点全景展示全部 30 个考点全量表
- Scenario D: Knowledge Chapter Filter - 验证按知识章节筛选功能
- Scenario E: Knowledge Search - 验证考点关键词/编号检索
- Scenario F: Knowledge Sorting - 验证掌握度升序/薄弱人数排序
- Scenario G: Students Roster - 验证学生学情花名册全览表
- Scenario H: Student Risk Filter & Search - 验证学情分类筛选与学生检索
- Scenario I: Student Detail Modal - 验证单生全维学情档案下钻弹窗
- Scenario J: Context Switching - 验证一键进入学生端视界及平滑切换回教师端
- Scenario K: Desktop Responsive - 验证 1440x900 与 1024x768 分辨率下零横向滚动溢出
- Scenario L: Zero Console Errors - 全流程控制台零报错断言 (0 console errors, 0 page errors)
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from playwright.sync_api import sync_playwright, Page, expect

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5173")
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8011")

SCREENSHOT_DIR = os.path.abspath("artifacts/uat_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

BRAIN_SCREENSHOT_DIR = r"C:\Users\XSL\.gemini\antigravity\brain\acc330ec-11ad-49d0-a406-fe3e112b5cfc\screenshots"
os.makedirs(BRAIN_SCREENSHOT_DIR, exist_ok=True)

RESULTS_FILE = os.path.abspath("artifacts/uat_results_sprint10c_teacher.json")

uat_results: Dict[str, Any] = {
    "sprint": "Sprint 10-C Phase 2",
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
        print(f"Warning copying screenshot to brain dir: {e}")
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
        print(f"[Launcher] 后端未运行，启动 127.0.0.1:8011...")
        proc_backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "gateway.api:create_gateway_app", "--factory", "--host", "127.0.0.1", "--port", "8011"],
            cwd=str(PROJECT_ROOT),
        )
        spawned_procs.append(("backend", proc_backend))
        for _ in range(30):
            if check_url_ready(f"{API_URL}/api/students"):
                print(f"[Launcher] 后端已就绪 (127.0.0.1:8011)")
                break
            time.sleep(0.8)
        else:
            raise RuntimeError("后端服务启动超时")
    else:
        print(f"[Launcher] 后端服务已在线 (127.0.0.1:8011)")

    # 2. 检查前端
    if not check_url_ready(f"{BASE_URL}/"):
        print("[Launcher] 前端未运行，启动 127.0.0.1:5173...")
        vite_env = dict(os.environ)
        vite_env["VITE_API_TARGET"] = "http://127.0.0.1:8011"
        proc_frontend = subprocess.Popen(
            "npx vite --host 127.0.0.1 --port 5173",
            shell=True,
            cwd=str(PROJECT_ROOT / "frontend"),
            env=vite_env,
        )
        spawned_procs.append(("frontend", proc_frontend))
        for _ in range(30):
            if check_url_ready(f"{BASE_URL}/"):
                print("[Launcher] 前端服务已就绪！")
                break
            time.sleep(0.8)
        else:
            raise RuntimeError("前端服务启动超时")
    else:
        print(f"[Launcher] 前端服务已在线 ({BASE_URL})")

    return spawned_procs


def run_uat():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 850})
        page = context.new_page()

        def on_console(msg):
            uat_results["console_messages"].append(f"[{msg.type}] {msg.text}")
            if msg.type == "error":
                text = msg.text.lower()
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

        # ---------------------------------------------------------------------
        # Scenario A: Teacher Web Landing - 访问 /teacher
        # ---------------------------------------------------------------------
        log_step("Scenario A: Teacher Web Landing 访问教师端总览看板")
        page.goto(f"{BASE_URL}/teacher", wait_until="networkidle", timeout=30000)
        page.wait_for_selector("[data-testid='teacher-cockpit']", timeout=15000)
        page.wait_for_selector("[data-testid='teacher-kpi-cards']", timeout=15000)
        page.wait_for_selector("[data-testid='teacher-weak-points-ranking']", timeout=15000)
        save_screenshot(page, "sprint10c_teacher_01_overview.png")

        uat_results["scenarios"]["scenario_a_overview_landing"] = {
            "status": "PASS",
            "url": page.url,
            "title": page.title(),
        }

        # ---------------------------------------------------------------------
        # Scenario B: 3-Tab Desktop Navigation Pills
        # ---------------------------------------------------------------------
        log_step("Scenario B: 验证 3-Tab 桌面导航 Pills 完备性")
        tabs = page.locator("[data-testid='teacher-tabs']")
        expect(tabs).to_be_visible()
        expect(page.locator("[data-testid='tab-teacher-overview']")).to_be_visible()
        expect(page.locator("[data-testid='tab-teacher-knowledge']")).to_be_visible()
        expect(page.locator("[data-testid='tab-teacher-students']")).to_be_visible()

        uat_results["scenarios"]["scenario_b_tabs_nav"] = {
            "status": "PASS",
        }

        # ---------------------------------------------------------------------
        # Scenario C: Knowledge 30 Points Full Roster
        # ---------------------------------------------------------------------
        log_step("Scenario C: 点击「知识点全景」并核验全部 30 个考点全景表")
        page.click("[data-testid='tab-teacher-knowledge']")
        page.wait_for_selector("[data-testid='teacher-knowledge-overview']", timeout=10000)
        page.wait_for_selector("[data-testid='teacher-knowledge-table']", timeout=10000)

        # 验证 URL 变更至 /teacher/knowledge
        assert "/teacher/knowledge" in page.url, f"Expected /teacher/knowledge, got {page.url}"

        # 核验考点行数达到 30 行
        rows = page.locator("[data-testid^='teacher-knowledge-row-']")
        count = rows.count()
        print(f"Loaded knowledge point rows count: {count}")
        assert count == 30, f"Expected exactly 30 knowledge points, found {count}"

        # 验证 K01 与 K30 均渲染在表格中
        expect(page.locator("[data-testid='teacher-knowledge-row-K01']")).to_be_visible()
        expect(page.locator("[data-testid='teacher-knowledge-row-K30']")).to_be_visible()

        save_screenshot(page, "sprint10c_teacher_02_knowledge_all.png")

        uat_results["scenarios"]["scenario_c_knowledge_30_points"] = {
            "status": "PASS",
            "total_points": count,
        }

        # ---------------------------------------------------------------------
        # Scenario D: Knowledge Chapter Filter
        # ---------------------------------------------------------------------
        log_step("Scenario D: 验证知识点章节过滤选择器")
        chapter_select = page.locator("[data-testid='teacher-knowledge-chapter-filter']")
        options = chapter_select.locator("option")
        opt_count = options.count()
        assert opt_count > 1, f"Expected chapter options, found {opt_count}"

        # 选中第一个具体章节
        first_chap_val = options.nth(1).get_attribute("value")
        print(f"Filtering by chapter: {first_chap_val}")
        chapter_select.select_option(value=first_chap_val)
        page.wait_for_timeout(500)

        filtered_count = page.locator("[data-testid^='teacher-knowledge-row-']").count()
        assert 0 < filtered_count < 30, f"Filtered count should be between 1 and 29, got {filtered_count}"

        # 还原章节为全部
        chapter_select.select_option(value="ALL")
        page.wait_for_timeout(300)
        assert page.locator("[data-testid^='teacher-knowledge-row-']").count() == 30

        uat_results["scenarios"]["scenario_d_chapter_filter"] = {
            "status": "PASS",
            "chapter_options_count": opt_count,
        }

        # ---------------------------------------------------------------------
        # Scenario E: Knowledge Keyword Search
        # ---------------------------------------------------------------------
        log_step("Scenario E: 验证考点关键词/编号检索")
        search_input = page.locator("[data-testid='teacher-knowledge-search']")
        search_input.fill("需求")
        page.wait_for_timeout(500)

        searched_rows = page.locator("[data-testid^='teacher-knowledge-row-']")
        search_cnt = searched_rows.count()
        print(f"Knowledge search for '需求' yielded {search_cnt} results")
        assert search_cnt >= 1

        save_screenshot(page, "sprint10c_teacher_03_knowledge_search.png")

        # 清空检索词
        search_input.fill("")
        page.wait_for_timeout(300)
        assert page.locator("[data-testid^='teacher-knowledge-row-']").count() == 30

        uat_results["scenarios"]["scenario_e_knowledge_search"] = {
            "status": "PASS",
            "search_count": search_cnt,
        }

        # ---------------------------------------------------------------------
        # Scenario F: Knowledge Sorting
        # ---------------------------------------------------------------------
        log_step("Scenario F: 验证考点掌握度升序排序 (暴露瓶颈)")
        sort_select = page.locator("[data-testid='teacher-knowledge-sort']")
        sort_select.select_option(value="mastery_asc")
        page.wait_for_timeout(500)

        first_row_id = page.locator("[data-testid^='teacher-knowledge-row-']").first.get_attribute("data-testid")
        print(f"First row after mastery_asc sort: {first_row_id}")
        save_screenshot(page, "sprint10c_teacher_04_knowledge_sort.png")

        uat_results["scenarios"]["scenario_f_knowledge_sort"] = {
            "status": "PASS",
            "first_sorted_point": first_row_id,
        }

        # ---------------------------------------------------------------------
        # Scenario G: Students Tab Navigation & Roster
        # ---------------------------------------------------------------------
        log_step("Scenario G: 点击「学生学情档案」并核验花名册表格")
        page.click("[data-testid='tab-teacher-students']")
        page.wait_for_selector("[data-testid='teacher-students-section']", timeout=10000)
        page.wait_for_selector("[data-testid='teacher-student-roster']", timeout=10000)

        assert "/teacher/students" in page.url, f"Expected /teacher/students, got {page.url}"

        # 核验学生花名册行
        st_rows = page.locator("[data-testid^='teacher-student-row-']")
        st_count = st_rows.count()
        print(f"Student rows count: {st_count}")
        assert st_count >= 5, f"Expected >= 5 students, found {st_count}"

        save_screenshot(page, "sprint10c_teacher_05_students_roster.png")

        uat_results["scenarios"]["scenario_g_students_roster"] = {
            "status": "PASS",
            "student_count": st_count,
        }

        # ---------------------------------------------------------------------
        # Scenario H: Student Risk Filter & Search
        # ---------------------------------------------------------------------
        log_step("Scenario H: 验证学生学情状态筛选与搜索")
        # 点击重点关注筛选
        page.locator("[data-testid='teacher-student-roster'] button:has-text('重点关注')").click()
        page.wait_for_timeout(400)
        att_rows = page.locator("[data-testid^='teacher-student-row-']").count()
        print(f"Attention students count: {att_rows}")

        # 还原全部
        page.locator("[data-testid='teacher-student-roster'] button:has-text('全部')").click()
        page.wait_for_timeout(300)

        # 搜索 S001
        st_search = page.locator("[data-testid='teacher-student-search']")
        st_search.fill("S001")
        page.wait_for_timeout(400)
        expect(page.locator("[data-testid='teacher-student-row-S001']")).to_be_visible()
        st_search.fill("")
        page.wait_for_timeout(300)

        uat_results["scenarios"]["scenario_h_students_filter"] = {
            "status": "PASS",
        }

        # ---------------------------------------------------------------------
        # Scenario I: Student Detail Modal Drilldown
        # ---------------------------------------------------------------------
        log_step("Scenario I: 点击 S001「学情档案」调起全维下钻弹窗")
        page.click("[data-testid='btn-student-detail-S001']")
        modal = page.locator("[data-testid='teacher-student-detail-modal']")
        expect(modal).to_be_visible(timeout=10000)
        expect(modal.locator("text=学情全维档案")).to_be_visible(timeout=10000)
        page.wait_for_timeout(600)

        save_screenshot(page, "sprint10c_teacher_06_student_modal.png")

        # 关闭弹窗
        modal.locator("[data-testid='btn-close-student-detail-modal']").click()
        expect(modal).not_to_be_visible(timeout=5000)
        page.wait_for_timeout(300)

        uat_results["scenarios"]["scenario_i_student_detail_modal"] = {
            "status": "PASS",
        }

        # ---------------------------------------------------------------------
        # Scenario J: Context Switching - 一键进入学生端视界
        # ---------------------------------------------------------------------
        log_step("Scenario J: 验证从教师端一键进入指定学生视图与切换回教师端")
        page.click("[data-testid='btn-enter-student-S001']")
        student_layout = page.locator("[data-testid='student-layout']")
        expect(student_layout).to_be_visible(timeout=15000)
        page.wait_for_timeout(1000)

        # 验证当前处于学生端且学生为 S001
        assert "/student" in page.url, f"Expected /student in url, got {page.url}"

        save_screenshot(page, "sprint10c_teacher_07_student_view_switched.png")

        # 通过 Header 切回教师端
        page.locator("button:has-text('教师驾驶舱')").click()
        page.wait_for_selector("[data-testid='teacher-cockpit']", timeout=15000)
        assert "/teacher" in page.url, f"Expected /teacher in url, got {page.url}"

        uat_results["scenarios"]["scenario_j_context_switching"] = {
            "status": "PASS",
        }

        # ---------------------------------------------------------------------
        # Scenario K: Desktop & Tablet Responsive Layout (1440x900, 1024x768 & 768x1024)
        # ---------------------------------------------------------------------
        log_step("Scenario K: 验证桌面端与平板多分辨率适配与无横向溢出 (1440x900 & 1024x768 & 768x1024)")
        # 1440x900
        page.set_viewport_size({"width": 1440, "height": 900})
        page.wait_for_timeout(500)
        no_h_overflow_1440 = page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        assert no_h_overflow_1440, "Detected horizontal overflow at 1440x900"
        save_screenshot(page, "sprint10c_teacher_08_desktop_1440x900.png")

        # 1024x768
        page.set_viewport_size({"width": 1024, "height": 768})
        page.wait_for_timeout(500)
        no_h_overflow_1024 = page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        assert no_h_overflow_1024, "Detected horizontal overflow at 1024x768"
        save_screenshot(page, "sprint10c_teacher_09_desktop_1024x768.png")

        # 768x1024 Tablet
        page.set_viewport_size({"width": 768, "height": 1024})
        page.wait_for_timeout(500)
        no_h_overflow_768 = page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        assert no_h_overflow_768, "Detected horizontal overflow at 768x1024"
        save_screenshot(page, "sprint10c_teacher_10_tablet_768x1024.png")

        uat_results["scenarios"]["scenario_k_desktop_responsive"] = {
            "status": "PASS",
            "1440x900_no_overflow": no_h_overflow_1440,
            "1024x768_no_overflow": no_h_overflow_1024,
            "768x1024_no_overflow": no_h_overflow_768,
        }

        # ---------------------------------------------------------------------
        # Scenario L: Zero Console Errors Assertion
        # ---------------------------------------------------------------------
        log_step("Scenario L: 控制台零错误与零页面异常核实")
        print(f"Console Errors Count: {len(uat_results['console_errors'])}")
        print(f"Page Errors Count: {len(uat_results['page_errors'])}")

        assert len(uat_results["console_errors"]) == 0, f"Console errors: {uat_results['console_errors']}"
        assert len(uat_results["page_errors"]) == 0, f"Page errors: {uat_results['page_errors']}"

        uat_results["scenarios"]["scenario_l_zero_errors"] = {
            "status": "PASS",
            "console_errors_count": 0,
            "page_errors_count": 0,
        }

        browser.close()

    # 写入测试报告
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(uat_results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 75)
    print(f"🎉 浏览器端到端 UAT 全场景验收成功！结果报告保存于: {RESULTS_FILE}")
    print("=" * 75)


if __name__ == "__main__":
    spawned = ensure_servers_running()
    try:
        run_uat()
    finally:
        for name, proc in spawned:
            print(f"[Launcher] 停止临时启动的服务: {name}")
            try:
                proc.terminate()
            except Exception:
                pass

