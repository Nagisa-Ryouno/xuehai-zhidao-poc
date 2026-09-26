# -*- coding: utf-8 -*-
"""
Verification Script for Final Critical Bugs:
- BUG-1: Scroll position restored upon modal close (0px loss)
- BUG-2: Background scroll locked when modal is open
- BUG-3: Real DeepSeek API invocation & non-mock reply
"""

import sys
import io
import time
import json
import urllib.request
from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_bug_3_real_deepseek():
    print("=" * 60)
    print("TESTING BUG-3: Real DeepSeek Runtime Invocation")
    print("=" * 60)
    url = "http://127.0.0.1:8011/api/ai/companion"
    payload = {
        "student_id": "S001",
        "mode": "conversation",
        "message": "请解释为什么当需求价格弹性大于1时，降低商品价格会增加总收益？请用一两句话精简说明核心经济学逻辑。",
        "knowledge_id": "K08",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    start_t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            elapsed = time.time() - start_t
            status = resp.status
            body = json.loads(resp.read().decode("utf-8"))
            print(f"HTTP Status: {status} (Elapsed: {elapsed:.2f}s)")
            provider = body.get('provider')
            mode = body.get('mode')
            answer = body.get('answer', '')
            print(f"Provider: {provider}")
            print(f"Mode: {mode}")
            print(f"Answer Preview:\n{answer[:300]}...")
            
            # Assertions
            assert status == 200, f"Expected 200, got {status}"
            assert provider in ("deepseek", "deepseek-flash"), f"Expected deepseek provider, got {provider}"
            assert "【AI 伴学服务当前不可用】" not in answer, "Encountered fallback error message"
            assert len(answer) > 20, "Answer too short"
            print(">>> BUG-3 VERIFICATION PASSED: Real DeepSeek response received successfully!")
            return True
    except Exception as e:
        print(f"BUG-3 FAILED with exception: {e}")
        return False

def test_bug_1_and_2_scroll(playwright):
    print("\n" + "=" * 60)
    print("TESTING BUG-1 & BUG-2: Scroll Restoration & Background Scroll Lock")
    print("=" * 60)
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()

    # 1. Visit Profile page where table has many KPs
    page.goto("http://127.0.0.1:5173/student/profile")
    page.wait_for_timeout(2000)

    # 2. Scroll to 1000px
    page.evaluate("window.scrollTo(0, 1000)")
    page.wait_for_timeout(300)
    y_before = page.evaluate("window.scrollY")
    print(f"[BUG-1] Scroll position before modal open: {y_before}px")
    assert y_before == 1000, f"Initial scroll target expected 1000, was {y_before}"

    # 3. Find and click "速览微卡"
    btn = page.locator("button", has_text="速览微卡").first
    assert btn.count() > 0, "No '速览微卡' button found"
    btn.click()
    page.wait_for_timeout(800)

    # 4. Check BUG-2: Background scroll locked
    body_overflow = page.evaluate("document.body.style.overflow")
    body_position = page.evaluate("document.body.style.position")
    body_top = page.evaluate("document.body.style.top")
    print(f"[BUG-2] Body overflow during modal: '{body_overflow}', position: '{body_position}', top: '{body_top}'")
    assert body_overflow == "hidden", f"Expected overflow: hidden, got '{body_overflow}'"
    assert body_position == "fixed", f"Expected position: fixed, got '{body_position}'"
    assert body_top == f"-{y_before}px", f"Expected body.top = -{y_before}px, got '{body_top}'"

    # Try wheeling on background backdrop
    page.mouse.wheel(0, 500)
    page.wait_for_timeout(300)
    # The fixed top style should hold the scroll at -y_before
    body_top_after_wheel = page.evaluate("document.body.style.top")
    assert body_top_after_wheel == f"-{y_before}px", f"Expected body.top to remain -{y_before}px after wheel, got '{body_top_after_wheel}'"
    print(">>> BUG-2 VERIFICATION PASSED: Background scroll is strictly locked against wheel/touch!")

    # 5. Check BUG-1: Close modal and verify scroll restored
    close_btn = page.locator("button[aria-label='关闭学习会话']").first
    assert close_btn.count() > 0, "Close session button not found"
    close_btn.click()

    # Wait for post-close refetch and double rAF scroll restoration
    page.wait_for_timeout(1000)

    y_after = page.evaluate("window.scrollY")
    body_overflow_after = page.evaluate("document.body.style.overflow")
    print(f"[BUG-1] Scroll position after modal close: {y_after}px (Body overflow: '{body_overflow_after}')")
    
    scroll_diff = abs(y_after - y_before)
    print(f"[BUG-1] Scroll position difference: {scroll_diff}px")
    assert scroll_diff == 0, f"Scroll position lost! Expected exact {y_before}px, got {y_after}px"
    print(">>> BUG-1 VERIFICATION PASSED: Scroll position perfectly restored (0px difference)!")

    browser.close()
    return True

def main():
    b3_ok = test_bug_3_real_deepseek()
    with sync_playwright() as p:
        b1_2_ok = test_bug_1_and_2_scroll(p)

    if b3_ok and b1_2_ok:
        print("\n" + "=" * 60)
        print("ALL 3 CRITICAL BUGS VERIFIED FIXED SUCCESSFULLY!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("VERIFICATION FAILED")
        print("=" * 60)
        sys.exit(1)

if __name__ == '__main__':
    main()
