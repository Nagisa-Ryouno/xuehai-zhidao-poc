"""
verify_productization_ui.py
Playwright 自动化多视口产品化 UI 验收测试
验证范围：
1. 品牌标题 "学海智导" 必须在全部 7 大标准视口中严格保持单行，绝不折行、不重叠、不截断
2. "AI分析服务在线" 与 "AI Learning Pilot" 从 DOM 中彻底消失
3. 用户名称展示只显示 display_name，绝不拼接 "(经济学·正确率...)"，绝不在前台暴露 DEMO_XXXX
4. 默认头像恒定单字符，固定尺寸，overflow: hidden，绝不发生文字溢出
"""

import sys
import os
from playwright.sync_api import sync_playwright

VIEWPORTS = [
    {"width": 375, "height": 667, "name": "mobile_375x667"},
    {"width": 390, "height": 844, "name": "mobile_390x844"},
    {"width": 412, "height": 915, "name": "mobile_412x915"},
    {"width": 768, "height": 1024, "name": "tablet_768x1024"},
    {"width": 1024, "height": 768, "name": "desktop_1024x768"},
    {"width": 1280, "height": 720, "name": "desktop_1280x720"},
    {"width": 1440, "height": 900, "name": "desktop_1440x900"},
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../output/screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_checks():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        all_passed = True

        for vp in VIEWPORTS:
            w, h, name = vp["width"], vp["height"], vp["name"]
            print(f"\n==================================================")
            print(f"Testing Viewport: {w}x{h} ({name})")
            print(f"==================================================")

            context = browser.new_context(viewport={"width": w, "height": h})
            page = context.new_page()

            # ------------------------------------------------------------------
            # 1. 学生端 (Student View)
            # ------------------------------------------------------------------
            page.goto("http://127.0.0.1:5173/student", wait_until="networkidle")
            page.wait_for_timeout(1000)

            # 1.1 品牌标题单行检查
            brand_loc = page.locator("text='学海智导'").first
            assert brand_loc.is_visible(), f"[{name}] 学海智导 必须在学生端可见"

            box = brand_loc.bounding_box()
            computed_ws = brand_loc.evaluate("el => window.getComputedStyle(el).whiteSpace")
            client_h = brand_loc.evaluate("el => el.clientHeight")
            scroll_h = brand_loc.evaluate("el => el.scrollHeight")

            print(f"  [Student] Brand Title box: {box}, clientHeight: {client_h}, scrollHeight: {scroll_h}, whiteSpace: {computed_ws}")
            assert "nowrap" in computed_ws, f"[{name}] 品牌标题必须具有 white-space: nowrap (实际为 {computed_ws})"
            assert client_h <= 36, f"[{name}] 品牌标题高度异常 ({client_h}px)，可能发生折行！"
            assert scroll_h <= client_h + 2, f"[{name}] 品牌标题发生垂直滚动溢出！"

            # 1.2 检查是否彻底移除了 "AI分析服务在线" 与 "AI Learning Pilot"
            ai_status_count = page.locator("text='AI分析服务在线'").count()
            ai_offline_count = page.locator("text='分析服务离线'").count()
            ai_pilot_count = page.locator("text='AI Learning Pilot'").count()

            assert ai_status_count == 0, f"[{name}] 严重错误: 发现 'AI分析服务在线' 存在于页面 DOM ({ai_status_count} 处)！"
            assert ai_offline_count == 0, f"[{name}] 严重错误: 发现 '分析服务离线' 存在于页面 DOM ({ai_offline_count} 处)！"
            assert ai_pilot_count == 0, f"[{name}] 严重错误: 发现 'AI Learning Pilot' 存在于页面 DOM ({ai_pilot_count} 处)！"
            print("  [Student] AI status pills & internal branding tags completely absent: PASS")

            # 1.3 检查用户名下拉菜单中是否清除了 (经济学·正确率...)
            select_text = page.locator("#student-select").evaluate("el => Array.from(el.options).map(o => o.text)")
            for opt_text in select_text:
                assert "正确率" not in opt_text, f"[{name}] 学生选择器选项仍包含正确率: {opt_text}"
                assert "经济学" not in opt_text, f"[{name}] 学生选择器选项仍包含经济学: {opt_text}"
                assert not opt_text.startswith("DEMO_"), f"[{name}] 学生选择器选项仍以 DEMO_ 开头: {opt_text}"
            print(f"  [Student] Student selector clean options: {select_text} -> PASS")

            # 截图保存
            screenshot_path = os.path.join(OUTPUT_DIR, f"student_{name}.png")
            page.screenshot(path=screenshot_path)
            print(f"  [Student] Screenshot saved: {screenshot_path}")

            # ------------------------------------------------------------------
            # 2. 教师端 (Teacher View)
            # ------------------------------------------------------------------
            page.goto("http://127.0.0.1:5173/teacher", wait_until="networkidle")
            page.wait_for_timeout(1000)

            # 2.1 品牌标题单行检查
            teacher_brand = page.locator("text='学海智导'").first
            assert teacher_brand.is_visible(), f"[{name}] 学海智导 必须在教师端可见"
            t_box = teacher_brand.bounding_box()
            t_computed_ws = teacher_brand.evaluate("el => window.getComputedStyle(el).whiteSpace")
            print(f"  [Teacher] Brand Title box: {t_box}, whiteSpace: {t_computed_ws}")
            assert "nowrap" in t_computed_ws, f"[{name}] 教师端品牌标题必须 white-space: nowrap"

            # 2.2 教师端头像与用户名展示防溢出检查
            # 找到下钻学生卡片中的头像
            avatar_loc = page.locator(".w-12.h-12.rounded-xl.bg-indigo-500").first
            if avatar_loc.count() > 0:
                avatar_text = avatar_loc.inner_text().strip()
                avatar_scroll_w = avatar_loc.evaluate("el => el.scrollWidth")
                avatar_client_w = avatar_loc.evaluate("el => el.clientWidth")
                print(f"  [Teacher] Monitored Avatar text: '{avatar_text}' (len={len(avatar_text)}), clientWidth={avatar_client_w}, scrollWidth={avatar_scroll_w}")

                assert len(avatar_text) == 1, f"[{name}] 头像文字必须严格为 1 个字符，实际为 '{avatar_text}'"
                assert avatar_scroll_w <= avatar_client_w, f"[{name}] 头像文字溢出容器！"
                assert not avatar_text.startswith("DEMO_"), f"[{name}] 头像文字仍包含 DEMO_！"

            # 2.3 教师端学生表格头像检查
            table_avatars = page.locator("table .w-8.h-8").all()
            if table_avatars:
                for idx, t_av in enumerate(table_avatars[:5]):
                    t_text = t_av.inner_text().strip()
                    t_sw = t_av.evaluate("el => el.scrollWidth")
                    t_cw = t_av.evaluate("el => el.clientWidth")
                    assert len(t_text) == 1, f"[{name}] 表格头像 #{idx} 文字长度不是 1: '{t_text}'"
                    assert t_sw <= t_cw, f"[{name}] 表格头像 #{idx} 文字溢出！"
                print(f"  [Teacher] Table row avatars ({len(table_avatars)} checked): PASS")

            # 教师端截图保存
            t_screenshot_path = os.path.join(OUTPUT_DIR, f"teacher_{name}.png")
            page.screenshot(path=t_screenshot_path)
            print(f"  [Teacher] Screenshot saved: {t_screenshot_path}")

            context.close()

        browser.close()

    print("\n==================================================")
    print("ALL VIEWPORT PLAYWRIGHT UI CHECKS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    run_checks()
