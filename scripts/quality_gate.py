# -*- coding: utf-8 -*-
"""
scripts/quality_gate.py
学海智导 (Xuehai Zhidao) V2 - Phase 2.2-E / Sprint 6
统一工程质量门禁 (Unified Quality Gate Runner)

执行维度：
Gate 1 — Frontend Type Safety (tsc -b)
Gate 2 — Frontend Contract & Integration Tests (node --experimental-strip-types --test)
Gate 3 — Frontend Production Build (vite build)
Gate 4 — Backend Regression (pytest architecture + full regression)
Gate 5 — Backend Freeze Invariant (git diff -- app/ tests/)
"""

import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def run_cmd(cmd, cwd, capture=True):
    """运行子进程命令，返回 (returncode, stdout, stderr)"""
    shell = True if os.name == "nt" else False
    res = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=shell,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return res.returncode, res.stdout or "", res.stderr or ""


def print_banner(title):
    print("\n" + "=" * 50)
    print(f"  {title}")
    print("=" * 50)


def main():
    print_banner("XUEHAI ZHIDAO QUALITY GATE (Sprint 6)")
    gates_passed = 0
    total_gates = 5
    summary_lines = []

    # -------------------------------------------------------------
    # Gate 1: Frontend Type Safety
    # -------------------------------------------------------------
    print("\n[1/5] Checking Frontend Type Safety (tsc -b)...")
    code, out, err = run_cmd("npx tsc -b", FRONTEND_DIR)
    if code == 0:
        gates_passed += 1
        print("  --> PASS: 0 TypeScript errors")
        summary_lines.append(("[1/5] Frontend Type Check", "PASS (0 TS errors)"))
    else:
        print("  --> FAIL: TypeScript compilation errors detected")
        print(f"\n[GATE 1 FAILED: Frontend Type Safety]")
        print("WHAT FAILED: tsc -b failed with type errors")
        print(f"WHY:\n{err or out}")
        print("WHICH GATE: Gate 1\n")
        summary_lines.append(("[1/5] Frontend Type Check", "FAIL"))
        print_banner("QUALITY GATE: FAILED")
        return 1

    # -------------------------------------------------------------
    # Gate 2: Frontend Contract & Integration Tests
    # -------------------------------------------------------------
    print("\n[2/5] Running Frontend Contract & Integration Tests...")
    test_cmd = "node --experimental-strip-types --test test/*.test.ts"
    code, out, err = run_cmd(test_cmd, FRONTEND_DIR)

    pass_match = re.search(r"pass\s+(\d+)", out)
    fail_match = re.search(r"fail\s+(\d+)", out)
    suites_match = re.search(r"suites\s+(\d+)", out)

    pass_count = int(pass_match.group(1)) if pass_match else 0
    fail_count = int(fail_match.group(1)) if fail_match else 0
    suites_count = int(suites_match.group(1)) if suites_match else 0

    if code == 0 and fail_count == 0:
        gates_passed += 1
        print(f"  --> PASS: {pass_count}/{pass_count} passed ({suites_count} suites, 0 failures)")
        summary_lines.append(("[2/5] Frontend Contract Tests", f"PASS ({pass_count}/{pass_count}, {suites_count} suites)"))
    else:
        print(f"  --> FAIL: {fail_count} tests failed out of {pass_count + fail_count}")
        print(f"\n[GATE 2 FAILED: Frontend Contract Tests]")
        print("WHAT FAILED: Frontend unit/contract/integration tests failed")
        print(f"WHY:\n{out[-800:]}")
        print("WHICH GATE: Gate 2\n")
        summary_lines.append(("[2/5] Frontend Contract Tests", f"FAIL ({fail_count} failed)"))
        print_banner("QUALITY GATE: FAILED")
        return 1

    # -------------------------------------------------------------
    # Gate 3: Production Build
    # -------------------------------------------------------------
    print("\n[3/5] Verifying Frontend Production Build (vite build)...")
    code, out, err = run_cmd("npx vite build", FRONTEND_DIR)
    if code == 0:
        gates_passed += 1
        print("  --> PASS: Vite production build succeeded without errors")
        summary_lines.append(("[3/5] Production Build", "PASS (Vite client build ready)"))
    else:
        print("  --> FAIL: Production build failed")
        print(f"\n[GATE 3 FAILED: Production Build]")
        print("WHAT FAILED: vite build failed")
        print(f"WHY:\n{err or out}")
        print("WHICH GATE: Gate 3\n")
        summary_lines.append(("[3/5] Production Build", "FAIL"))
        print_banner("QUALITY GATE: FAILED")
        return 1

    # -------------------------------------------------------------
    # Gate 4: Backend Regression Tests
    # -------------------------------------------------------------
    print("\n[4/5] Running Backend Architecture & Regression Tests...")
    code_arch, out_arch, err_arch = run_cmd("pytest tests/architecture/ -v", PROJECT_ROOT)
    arch_match = re.search(r"(\d+)\s+passed", out_arch)
    arch_count = int(arch_match.group(1)) if arch_match else 0

    code_full, out_full, err_full = run_cmd("pytest tests/ -q", PROJECT_ROOT)
    full_match = re.search(r"(\d+)\s+passed", out_full)
    full_count = int(full_match.group(1)) if full_match else 0

    if code_arch == 0 and code_full == 0:
        gates_passed += 1
        print(f"  --> PASS: {arch_count} architecture tests + {full_count} full regression tests passed")
        summary_lines.append(("[4/5] Backend Regression", f"PASS ({arch_count} arch + {full_count} full)"))
    else:
        print("  --> FAIL: Backend tests failed")
        print(f"\n[GATE 4 FAILED: Backend Regression]")
        print("WHAT FAILED: Pytest regression suite detected failures")
        print(f"WHY:\n{out_arch if code_arch != 0 else out_full}")
        print("WHICH GATE: Gate 4\n")
        summary_lines.append(("[4/5] Backend Regression", "FAIL"))
        print_banner("QUALITY GATE: FAILED")
        return 1

    # -------------------------------------------------------------
    # Gate 5: Backend Freeze Invariant
    # -------------------------------------------------------------
    print("\n[5/5] Verifying Backend Freeze Invariant (git diff -- app/ tests/)...")
    code_diff, out_diff, err_diff = run_cmd("git diff -- app/ tests/", PROJECT_ROOT)
    diff_clean = (code_diff == 0 and out_diff.strip() == "")

    if diff_clean:
        gates_passed += 1
        print("  --> PASS: 0 modifications in app/ and tests/ (Strict Freeze maintained)")
        summary_lines.append(("[5/5] Backend Freeze Invariant", "PASS (0 diff in app/ and tests/)"))
    else:
        print("  --> FAIL: Backend freeze violation detected in app/ or tests/")
        print(f"\n[GATE 5 FAILED: Backend Freeze Invariant]")
        print("WHAT FAILED: git diff -- app/ tests/ is not empty")
        print(f"WHY: Detected unexpected modifications:\n{out_diff}")
        print("WHICH GATE: Gate 5\n")
        summary_lines.append(("[5/5] Backend Freeze Invariant", "FAIL (diff detected)"))
        print_banner("QUALITY GATE: FAILED")
        return 1

    # -------------------------------------------------------------
    # Final Summary
    # -------------------------------------------------------------
    print_banner("QUALITY GATE SUMMARY")
    for name, status in summary_lines:
        print(f"  {name:<32} {status}")
    print("-" * 50)
    print(f"  Result: {gates_passed}/{total_gates} Gates Passed (100%)")
    print("=" * 50)
    print("  STATUS: QUALITY GATE PASS -> READY FOR RELEASE")
    print("=" * 50 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
