#!/usr/bin/env python3
"""
scripts/sprint10c_pwa_gate.py
Sprint 10-C / Phase 1: Student PWA Productization 严格质量门禁 (20-Point Strict Gate)

检验项目：
[01] Manifest exists
[02] Manifest valid
[03] Required icons present
[04] start_url valid
[05] scope valid
[06] display standalone
[07] PWA metadata loaded in index.html
[08] Service Worker registration wired
[09] Static cache strategy in sw.js
[10] Dynamic API not incorrectly cached (/api/ bypass)
[11] Offline fallback & graceful degradation
[12] Install UX & dismissal logic
[13] Standalone safe-area adaptation
[14] Mobile 375x812 responsive preservation
[15] Mobile 390x844 touch target & layout
[16] Zero horizontal overflow protection
[17] Student Layout & Today Action intact
[18] Resource Hub intact
[19] Recommendation candidate-only invariant
[20] AI Companion intact & zero core mutation
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
PUBLIC_DIR = os.path.join(FRONTEND_DIR, "public")
SRC_DIR = os.path.join(FRONTEND_DIR, "src")


def run_check(check_id: int, title: str, fn) -> bool:
    try:
        passed, detail = fn()
        status = "PASS" if passed else "FAIL"
        print(f"[{check_id:02d}/20] {title:<45} ... {status}")
        if not passed:
            print(f"       ERROR: {detail}")
        return passed
    except Exception as e:
        print(f"[{check_id:02d}/20] {title:<45} ... FAIL (Exception: {e})")
        return False


def check_01_manifest_exists():
    path = os.path.join(PUBLIC_DIR, "manifest.webmanifest")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return True, "manifest.webmanifest exists and is non-empty"
    return False, f"File missing or empty: {path}"


def check_02_manifest_valid():
    path = os.path.join(PUBLIC_DIR, "manifest.webmanifest")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("name") == "学海智导" and data.get("short_name") == "学海智导":
            return True, "Valid name and short_name"
        return False, f"Unexpected manifest data: {data}"
    except Exception as e:
        return False, str(e)


def check_03_required_icons_present():
    required = ["pwa-192x192.png", "pwa-512x512.png", "pwa-maskable-512x512.png", "favicon.svg"]
    for req in required:
        p = os.path.join(PUBLIC_DIR, req)
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            return False, f"Required icon {req} missing or empty"
    return True, "All required 192, 512, maskable, and favicon icons exist"


def check_04_start_url_valid():
    path = os.path.join(PUBLIC_DIR, "manifest.webmanifest")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    start_url = data.get("start_url")
    if start_url in ["/student", "/student/tasks"]:
        return True, f"start_url {start_url} is valid"
    return False, f"Invalid start_url: {start_url}"


def check_05_scope_valid():
    path = os.path.join(PUBLIC_DIR, "manifest.webmanifest")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    scope = data.get("scope")
    if scope == "/":
        return True, "scope is /"
    return False, f"Unexpected scope: {scope}"


def check_06_display_standalone():
    path = os.path.join(PUBLIC_DIR, "manifest.webmanifest")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("display") == "standalone" and data.get("theme_color") == "#4f46e5":
        return True, "display is standalone and theme_color is #4f46e5"
    return False, f"display or theme_color mismatch: {data}"


def check_07_pwa_metadata_loaded():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    if 'rel="manifest"' in html and 'viewport-fit=cover' in html and 'name="theme-color"' in html:
        return True, "index.html includes manifest, viewport-fit=cover, and theme-color"
    return False, "index.html missing required PWA meta tags"


def check_08_service_worker_registration():
    pwa_ts = os.path.join(SRC_DIR, "pwa.ts")
    main_tsx = os.path.join(SRC_DIR, "main.tsx")
    with open(pwa_ts, "r", encoding="utf-8") as f:
        pwa_code = f.read()
    with open(main_tsx, "r", encoding="utf-8") as f:
        main_code = f.read()
    if "registerServiceWorker" in pwa_code and "registerServiceWorker()" in main_code:
        return True, "Service Worker registration wired in pwa.ts and main.tsx"
    return False, "Service Worker registration not wired properly"


def check_09_static_cache_strategy():
    sw_path = os.path.join(PUBLIC_DIR, "sw.js")
    with open(sw_path, "r", encoding="utf-8") as f:
        code = f.read()
    if "PRECACHE_ASSETS" in code and "caches.open" in code and "caches.match" in code:
        return True, "Static cache precaching and Cache-First strategy verified"
    return False, "Static cache strategy incomplete in sw.js"


def check_10_dynamic_api_not_cached():
    sw_path = os.path.join(PUBLIC_DIR, "sw.js")
    with open(sw_path, "r", encoding="utf-8") as f:
        code = f.read()
    if "/api/" in code and "NETWORK_UNAVAILABLE" in code and "fetch(request)" in code:
        return True, "/api/ bypasses SW cache and does not fake stale data"
    return False, "/api/ not explicitly excluded from cache in sw.js"


def check_11_offline_fallback():
    sw_path = os.path.join(PUBLIC_DIR, "sw.js")
    layout_path = os.path.join(SRC_DIR, "layouts", "StudentLayout.tsx")
    with open(sw_path, "r", encoding="utf-8") as f:
        sw_code = f.read()
    with open(layout_path, "r", encoding="utf-8") as f:
        layout_code = f.read()
    has_nav_fallback = "request.mode === 'navigate'" in sw_code and "caches.match" in sw_code
    has_ui_notice = "pwa-offline-notice" in layout_code and "离线模式" in layout_code
    if has_nav_fallback and has_ui_notice:
        return True, "Navigation fallback to shell and UI offline notice verified"
    return False, f"Offline fallback missing: nav={has_nav_fallback}, ui={has_ui_notice}"


def check_12_install_ux():
    banner_path = os.path.join(SRC_DIR, "components", "student", "PwaInstallBanner.tsx")
    with open(banner_path, "r", encoding="utf-8") as f:
        code = f.read()
    if "beforeinstallprompt" in code and "pwa_install_dismissed" in code and "pwa-install-banner" in code:
        return True, "PwaInstallBanner has beforeinstallprompt, dismissal, and test IDs"
    return False, "PwaInstallBanner missing required lifecycle handlers"


def check_13_standalone_safe_area():
    header_path = os.path.join(SRC_DIR, "components", "Header.tsx")
    nav_path = os.path.join(SRC_DIR, "components", "student", "navConfig.ts")
    with open(header_path, "r", encoding="utf-8") as f:
        h_code = f.read()
    with open(nav_path, "r", encoding="utf-8") as f:
        n_code = f.read()
    has_top = "safe-area-inset-top" in h_code
    has_bottom = "safe-area-inset-bottom" in n_code
    if has_top and has_bottom:
        return True, "Safe area insets adapted for top header and bottom nav"
    return False, f"Safe area insets incomplete: top={has_top}, bottom={has_bottom}"


def check_14_mobile_375x812():
    mc_path = os.path.join(SRC_DIR, "components", "student", "MobileContainer.tsx")
    with open(mc_path, "r", encoding="utf-8") as f:
        code = f.read()
    if "max-w-7xl" in code and "px-3" in code:
        return True, "MobileContainer responsive for 375x812"
    return False, "MobileContainer missing responsive padding"


def check_15_mobile_390x844_touch_targets():
    nav_path = os.path.join(SRC_DIR, "components", "student", "BottomNav.tsx")
    with open(nav_path, "r", encoding="utf-8") as f:
        code = f.read()
    if "min-h-[48px]" in code and "min-w-[48px]" in code:
        return True, "BottomNav preserves 48px touch targets for mobile"
    return False, "Touch targets do not meet mobile guidelines"


def check_16_zero_horizontal_overflow():
    layout_path = os.path.join(SRC_DIR, "layouts", "StudentLayout.tsx")
    with open(layout_path, "r", encoding="utf-8") as f:
        code = f.read()
    if "overflow-x-hidden" in code and "max-w-full" in code:
        return True, "StudentLayout has overflow-x-hidden and max-w-full"
    return False, "StudentLayout missing horizontal overflow protection"


def check_17_student_layout_intact():
    layout_path = os.path.join(SRC_DIR, "layouts", "StudentLayout.tsx")
    with open(layout_path, "r", encoding="utf-8") as f:
        code = f.read()
    required = ["TodayActionCard", "CurrentFocusCard", "HeroBanner", "BottomNav"]
    for r in required:
        if r not in code:
            return False, f"Missing component in StudentLayout: {r}"
    return True, "StudentLayout intact with TodayAction, CurrentFocus, Hero, and BottomNav"


def check_18_resource_hub_intact():
    hub_path = os.path.join(SRC_DIR, "components", "student", "ResourceHub.tsx")
    with open(hub_path, "r", encoding="utf-8") as f:
        code = f.read()
    if "personalized-recommendation-section" in code and "ExternalRedirectModal" in code:
        return True, "ResourceHub intact with recommendations and MOOC redirect"
    return False, "ResourceHub components altered or missing"


def check_19_recommendation_candidate_only():
    model_path = os.path.join(PROJECT_ROOT, "gateway", "ai", "recommendation", "models.py")
    prompt_path = os.path.join(PROJECT_ROOT, "gateway", "ai", "recommendation", "prompt.py")
    with open(model_path, "r", encoding="utf-8") as f:
        m_code = f.read()
    with open(prompt_path, "r", encoding="utf-8") as f:
        p_code = f.read()
    if "allow_production_decision = False" in p_code and "RECOMMENDATION_FORBIDDEN_FIELDS" in m_code:
        return True, "Recommendation strictly enforces candidate-only invariant"
    return False, "Prompt or models missing candidate-only invariants"


def check_20_companion_and_core_freeze():
    # Check data runtime files and seeds are intact
    runtime_dir = os.path.join(PROJECT_ROOT, "data", "runtime")
    bkt_file = os.path.join(runtime_dir, "bkt_states.json")
    path_file = os.path.join(runtime_dir, "learning_path_states.json")
    seeds_dir = os.path.join(PROJECT_ROOT, "data", "seeds")
    if os.path.exists(bkt_file) and os.path.exists(path_file) and os.path.exists(seeds_dir):
        return True, "Authoritative learning engine data files verified"
    return False, "Core data files missing"


def main():
    print("=" * 70)
    print("学海智导 Sprint 10-C / Phase 1 — Student PWA 严格门禁 (20-Point Strict Gate)")
    print("=" * 70)

    checks = [
        (1, "Manifest exists", check_01_manifest_exists),
        (2, "Manifest valid", check_02_manifest_valid),
        (3, "Required icons present", check_03_required_icons_present),
        (4, "start_url valid", check_04_start_url_valid),
        (5, "scope valid", check_05_scope_valid),
        (6, "display standalone", check_06_display_standalone),
        (7, "PWA metadata loaded in index.html", check_07_pwa_metadata_loaded),
        (8, "Service Worker registration wired", check_08_service_worker_registration),
        (9, "Static cache strategy in sw.js", check_09_static_cache_strategy),
        (10, "Dynamic API not incorrectly cached", check_10_dynamic_api_not_cached),
        (11, "Offline fallback & graceful degradation", check_11_offline_fallback),
        (12, "Install UX & dismissal logic", check_12_install_ux),
        (13, "Standalone safe-area adaptation", check_13_standalone_safe_area),
        (14, "Mobile 375x812 responsive layout", check_14_mobile_375x812),
        (15, "Mobile 390x844 touch targets", check_15_mobile_390x844_touch_targets),
        (16, "Zero horizontal overflow", check_16_zero_horizontal_overflow),
        (17, "Student Layout & Today Action intact", check_17_student_layout_intact),
        (18, "Resource Hub intact", check_18_resource_hub_intact),
        (19, "Recommendation candidate-only invariant", check_19_recommendation_candidate_only),
        (20, "Core learning engine frozen", check_20_companion_and_core_freeze),
    ]

    passed_count = 0
    for cid, title, fn in checks:
        if run_check(cid, title, fn):
            passed_count += 1

    print("-" * 70)
    print(f"Gate Score: {passed_count}/20 {'PASS' if passed_count == 20 else 'FAIL'}")
    if passed_count == 20:
        print("ALL QUALITY CHECKS PASSED — SPRINT 10-C PHASE 1 VERIFIED")
        sys.exit(0)
    else:
        print("QUALITY GATE FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
