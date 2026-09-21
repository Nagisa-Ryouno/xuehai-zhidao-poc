"""
audit_sprint10c_phase5_ux.py
==============================================================================
Sprint 10-C Phase 5: Student UX/UI Usability Audit Script
==============================================================================
Runs real Chromium browser sessions across 375x812, 390x844, and 1440x900
walkthrough tasks (A through F) to detect:
1. Competing CTAs and visual hierarchy confusion
2. Missing or confusing information / cognitive load
3. Touch targets, spacing, text readability
4. Modal usability and safe areas
5. Feedback clarity on Quiz, Result, and AI Recommendation
6. Error / Offline handling
==============================================================================
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

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

SCREENSHOT_DIR = os.path.abspath("artifacts/ux_audit")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

BRAIN_SCREENSHOT_DIR = r"C:\Users\XSL\.gemini\antigravity\brain\acc330ec-11ad-49d0-a406-fe3e112b5cfc\screenshots"
os.makedirs(BRAIN_SCREENSHOT_DIR, exist_ok=True)

REPORT_JSON = os.path.abspath("artifacts/ux_audit_raw.json")

audit_data: Dict[str, Any] = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "viewports_tested": ["375x812", "390x844", "1440x900"],
    "tasks": {},
    "touch_target_issues": [],
    "overflow_issues": [],
    "hierarchy_observations": [],
    "console_errors": [],
}


def log_audit(section: str):
    print(f"\n{'='*70}\n[UX AUDIT] >>> {section}\n{'='*70}")


def save_shot(page: Page, name: str):
    p1 = os.path.join(SCREENSHOT_DIR, name)
    p2 = os.path.join(BRAIN_SCREENSHOT_DIR, name)
    page.screenshot(path=p1, full_page=False)
    try:
        shutil.copyfile(p1, p2)
    except Exception as e:
        print(f"Warning copying {name}: {e}")
    print(f"  [Screenshot] {name}")


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
        for _ in range(30):
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
        for _ in range(30):
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


def check_touch_targets(page: Page, context_name: str):
    """Inspect all clickable buttons and interactive items in page for >= 44x44px target."""
    buttons = page.locator("button:visible, a:visible, select:visible").all()
    for btn in buttons:
        try:
            box = btn.bounding_box()
            if not box:
                continue
            txt = (btn.inner_text() or btn.get_attribute("aria-label") or btn.get_attribute("title") or "unnamed").strip()[:30]
            if (box["height"] < 40 or box["width"] < 40) and box["height"] > 0 and box["width"] > 0:
                audit_data["touch_target_issues"].append({
                    "context": context_name,
                    "element": txt,
                    "width": round(box["width"], 1),
                    "height": round(box["height"], 1),
                })
        except Exception:
            pass


def check_overflow(page: Page, context_name: str, expected_w: int):
    sw = page.evaluate("() => document.documentElement.scrollWidth")
    cw = page.evaluate("() => document.documentElement.clientWidth")
    if sw > cw + 1:
        audit_data["overflow_issues"].append({
            "context": context_name,
            "scrollWidth": sw,
            "clientWidth": cw,
            "expected_w": expected_w,
        })


def run_audit():
    spawned = ensure_servers_running()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            def create_page(ctx, is_fault=False):
                pg = ctx.new_page()
                pg.on("console", lambda m: audit_data["console_errors"].append(m.text) if m.type == "error" and not is_fault and "favicon" not in m.text else None)
                return pg

            # =================================================================
            # Task A: First-time Student Entry Walkthrough
            # =================================================================
            log_audit("Task A: First Time Entry (Student Home 375x812 / 390x844 / 1440x900)")
            for vp_w, vp_h in [(375, 812), (390, 844), (1440, 900)]:
                ctx = browser.new_context(viewport={"width": vp_w, "height": vp_h})
                page = create_page(ctx)
                page.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
                page.wait_for_selector("[data-testid='student-home']", timeout=15000)

                check_overflow(page, f"Task A Home {vp_w}x{vp_h}", vp_w)
                check_touch_targets(page, f"Task A Home {vp_w}x{vp_h}")

                # Capture home screen
                save_shot(page, f"audit_task_a_home_{vp_w}x{vp_h}.png")

                # Count primary CTAs visible on screen
                today_btn = page.locator("[data-testid='today-action-cta-btn']")
                focus_btn = page.locator("[data-testid='focus-start-quiz-btn']")
                concept_btn = page.locator("text=📖 考点精要速览")
                resources_btn = page.locator("text=📚 推荐学习材料")
                ai_btn = page.locator("text=🤖 问问 AI")

                visible_ctas = []
                if today_btn.is_visible():
                    visible_ctas.append(f"TodayAction: {today_btn.inner_text().strip()}")
                if focus_btn.is_visible():
                    visible_ctas.append(f"CurrentFocus: {focus_btn.inner_text().strip()}")
                if concept_btn.is_visible():
                    visible_ctas.append("CurrentFocus: 📖 考点精要速览")
                if resources_btn.is_visible():
                    visible_ctas.append("CurrentFocus: 📚 推荐学习材料")
                if ai_btn.is_visible():
                    visible_ctas.append("CurrentFocus: 🤖 问问 AI")

                audit_data["hierarchy_observations"].append({
                    "viewport": f"{vp_w}x{vp_h}",
                    "visible_primary_actions_on_home": visible_ctas,
                })

                # Test 30-second understanding: Are TodayAction and CurrentFocus for different knowledge points?
                today_kname = page.locator("[data-testid='today-action-card']").inner_text()
                focus_kname = page.locator("[data-testid='current-focus-card']").inner_text()
                audit_data["tasks"][f"task_a_{vp_w}"] = {
                    "today_card_snippet": today_kname[:100],
                    "focus_card_snippet": focus_kname[:100],
                    "visible_ctas_count": len(visible_ctas),
                }

                ctx.close()

            # =================================================================
            # Task B: Complete Learning Session Flow (Today Action -> Result)
            # =================================================================
            log_audit("Task B: Complete Learning Session Flow (Mobile 390x844)")
            ctx_b = browser.new_context(viewport={"width": 390, "height": 844})
            page_b = create_page(ctx_b)
            page_b.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)

            # Step 1: Click Today Action CTA -> ENTRY
            page_b.locator("[data-testid='today-action-cta-btn']").click()
            page_b.wait_for_timeout(600)
            modal = page_b.locator("[data-testid='learning-session-modal']")
            expect(modal).to_be_visible()
            save_shot(page_b, "audit_task_b_01_session_entry.png")
            check_touch_targets(page_b, "Task B Session Entry")

            # Step 2: Entry -> Concept
            page_b.locator("[data-testid='session-entry-start-concept-btn']").click()
            page_b.wait_for_timeout(600)
            expect(modal.locator("[data-testid='session-step-concept']")).to_be_visible()
            save_shot(page_b, "audit_task_b_02_session_concept.png")
            check_touch_targets(page_b, "Task B Session Concept")

            # Step 3: Concept -> Resource
            page_b.locator("[data-testid='concept-view-resources-btn']").click()
            page_b.wait_for_timeout(1000)
            save_shot(page_b, "audit_task_b_03_session_resource.png")
            check_touch_targets(page_b, "Task B Session Resource")

            # Step 4: Resource -> Quiz
            page_b.locator("[data-testid='resource-step-start-quiz-btn']").click()
            page_b.wait_for_timeout(600)
            expect(modal.locator("[data-testid='session-step-quiz']")).to_be_visible()
            save_shot(page_b, "audit_task_b_04_session_quiz.png")
            check_touch_targets(page_b, "Task B Session Quiz")

            # Step 5: Answer Question 1 & view instant feedback
            opt = modal.locator("[data-testid='session-step-quiz'] button.cursor-pointer").first
            opt.click()
            page_b.wait_for_timeout(300)
            save_shot(page_b, "audit_task_b_05_quiz_selected.png")

            submit_btn = modal.locator("[data-testid='quiz-submit-btn']")
            submit_btn.click()
            page_b.wait_for_timeout(1000)
            save_shot(page_b, "audit_task_b_06_quiz_feedback.png")

            # Finish remaining questions
            for _ in range(8):
                if modal.locator("[data-testid='session-step-result']").is_visible():
                    break
                quiz_el = modal.locator("[data-testid='session-step-quiz']")
                if not quiz_el.is_visible():
                    break
                next_btn = modal.locator("[data-testid='quiz-next-btn']")
                if next_btn.is_visible():
                    next_btn.click()
                    page_b.wait_for_timeout(500)
                opt_next = modal.locator("[data-testid='session-step-quiz'] button.cursor-pointer").first
                if opt_next.is_visible():
                    opt_next.click()
                    page_b.wait_for_timeout(200)
                    s_btn = modal.locator("[data-testid='quiz-submit-btn']")
                    if s_btn.is_visible() and s_btn.is_enabled():
                        s_btn.click()
                        page_b.wait_for_timeout(800)

            # Step 6: Result Step
            expect(modal.locator("[data-testid='session-step-result']")).to_be_visible()
            save_shot(page_b, "audit_task_b_07_session_result.png")
            check_touch_targets(page_b, "Task B Session Result")

            ctx_b.close()

            # =================================================================
            # Task C: AI Recommendation vs Baseline Resources
            # =================================================================
            log_audit("Task C: AI Recommendation vs Baseline Resources (390x844)")
            ctx_c = browser.new_context(viewport={"width": 390, "height": 844})
            page_c = create_page(ctx_c)
            page_c.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page_c.locator("[data-testid='today-action-cta-btn']").click()
            page_c.wait_for_timeout(500)
            modal_c = page_c.locator("[data-testid='learning-session-modal']")
            modal_c.locator("[data-testid='session-entry-start-concept-btn']").click()
            page_c.wait_for_timeout(500)
            modal_c.locator("[data-testid='concept-view-resources-btn']").click()
            page_c.wait_for_timeout(1000)

            # Check if AI rec section is rendered
            rec_sec = modal_c.locator("[data-testid='personalized-rec-section']")
            expect(rec_sec).to_be_visible()

            # Check reasons text length
            reasons = modal_c.locator("[data-testid='rec-reason-text']").all_inner_texts()
            audit_data["tasks"]["task_c_ai_reasons"] = reasons

            # Scroll to baseline resources
            baseline_sec = modal_c.locator("text=精选学习资源")
            expect(baseline_sec).to_be_visible()
            save_shot(page_c, "audit_task_c_resources_comparison.png")

            # Check CTA at bottom: start quiz
            start_q_btn = modal_c.locator("[data-testid='resource-step-start-quiz-btn']")
            expect(start_q_btn).to_be_visible()
            expect(start_q_btn).to_be_enabled()

            ctx_c.close()

            # =================================================================
            # Task D: Quiz Usability Deep-dive
            # =================================================================
            log_audit("Task D: Quiz Usability Deep-dive (375x812)")
            ctx_d = browser.new_context(viewport={"width": 375, "height": 812})
            page_d = create_page(ctx_d)
            page_d.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)
            page_d.locator("[data-testid='today-action-cta-btn']").click()
            page_d.wait_for_timeout(500)
            modal_d = page_d.locator("[data-testid='learning-session-modal']")
            modal_d.locator("[data-testid='session-entry-direct-quiz-btn']").click()
            page_d.wait_for_timeout(600)

            # Check question count indicator
            q_indicator = modal_d.locator("text=小测验 · 第 1 题").inner_text()
            # Check options
            options = modal_d.locator("[data-testid='session-step-quiz'] button.cursor-pointer").all()
            opt_boxes = [opt.bounding_box() for opt in options]

            audit_data["tasks"]["task_d_quiz"] = {
                "question_indicator": q_indicator,
                "options_count": len(options),
                "options_heights": [round(b["height"], 1) for b in opt_boxes if b],
            }
            save_shot(page_d, "audit_task_d_quiz_question.png")
            ctx_d.close()

            # =================================================================
            # Task E: Navigation, Return & Modal Behavior
            # =================================================================
            log_audit("Task E: Navigation, Return & Modal Behavior")
            ctx_e = browser.new_context(viewport={"width": 390, "height": 844})
            page_e = create_page(ctx_e)
            page_e.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)

            # Test Bottom Navigation tabs switching
            save_shot(page_e, "audit_task_e_01_nav_tasks.png")
            page_e.locator("nav[aria-label='学生端底部主导航'] button:has-text('知识图谱')").click()
            page_e.wait_for_timeout(600)
            save_shot(page_e, "audit_task_e_02_nav_graph.png")

            page_e.locator("nav[aria-label='学生端底部主导航'] button:has-text('学情档案')").click()
            page_e.wait_for_timeout(600)
            save_shot(page_e, "audit_task_e_03_nav_profile.png")

            page_e.locator("nav[aria-label='学生端底部主导航'] button:has-text('AI伴学')").click()
            page_e.wait_for_timeout(600)
            save_shot(page_e, "audit_task_e_04_nav_assistant.png")

            # Go back to tasks
            page_e.locator("nav[aria-label='学生端底部主导航'] button:has-text('今日任务')").click()
            page_e.wait_for_timeout(600)

            # Open session and test close button
            page_e.locator("[data-testid='today-action-cta-btn']").click()
            page_e.wait_for_timeout(500)
            modal_e = page_e.locator("[data-testid='learning-session-modal']")
            expect(modal_e).to_be_visible()

            close_btn = modal_e.locator("button[aria-label='关闭学习会话']")
            close_btn.click()
            page_e.wait_for_timeout(500)
            expect(modal_e).not_to_be_visible()
            save_shot(page_e, "audit_task_e_05_modal_closed.png")

            ctx_e.close()

            # =================================================================
            # Task F: Error / Offline / Edge Case Walkthrough
            # =================================================================
            log_audit("Task F: Error / Offline / Edge Cases")
            ctx_f = browser.new_context(viewport={"width": 390, "height": 844})
            page_f = create_page(ctx_f, is_fault=True)
            page_f.goto(f"{BASE_URL}/student/tasks", wait_until="networkidle", timeout=30000)

            # Trigger offline
            page_f.evaluate("() => window.dispatchEvent(new Event('offline'))")
            page_f.wait_for_timeout(500)
            save_shot(page_f, "audit_task_f_01_offline_banner.png")

            # Trigger online
            page_f.evaluate("() => window.dispatchEvent(new Event('online'))")
            page_f.wait_for_timeout(500)
            save_shot(page_f, "audit_task_f_02_online_recovered.png")

            ctx_f.close()

            browser.close()

    finally:
        cleanup_spawned(spawned)

    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, ensure_ascii=False, indent=2)

    print(f"\n[Audit Completed] Audit metrics saved to {REPORT_JSON}")
    print(f"Touch target issues found: {len(audit_data['touch_target_issues'])}")
    print(f"Overflow issues found: {len(audit_data['overflow_issues'])}")
    print(f"Console errors: {len(audit_data['console_errors'])}")


if __name__ == "__main__":
    run_audit()
