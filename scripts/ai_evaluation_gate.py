# -*- coding: utf-8 -*-
"""
scripts/ai_evaluation_gate.py
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G1: AI Semantic Evaluation Regression Gate (独立 AI 语义评估门禁)

职责边界：
1. 独立于 scripts/quality_gate.py，专注于 AI 伴学输出的语义事实、安全边界与策略合规性回归
2. 严格执行 51 组 Golden Cases (g1.0) 离线确定性评估
3. 实施 Safety Hard Gate 检查、状态不可变性检查与确定性幂等校验
4. 任何异常、降级或越权未拦截均导致 exit code 1；全部通过返回 exit code 0
"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gateway.evaluation.evaluator import run_evaluation_suite


def run_ai_evaluation_gate() -> int:
    """
    运行 AI 语义评估门禁，返回进程退出码 (0=PASS, 1=FAIL)
    """
    print("=" * 50)
    print(" AI SEMANTIC EVALUATION GATE")
    print("=" * 50)

    try:
        # Run 1: 第一次评测运行
        report_1 = run_evaluation_suite()

        # Run 2: 验证多次调用的幂等性与确定性 (Determinism check)
        report_2 = run_evaluation_suite()
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Failed to execute evaluation suite: {e}")
        return 1

    # 校验确定性：两次运行除了 duration_ms 外必须完全一致
    determinism_passed = bool(
        report_1.dataset_version == report_2.dataset_version
        and report_1.total_cases == report_2.total_cases
        and report_1.passed_cases == report_2.passed_cases
        and report_1.category_statistics == report_2.category_statistics
        and report_1.all_safety_cases_passed == report_2.all_safety_cases_passed
        and report_1.core_state_unchanged == report_2.core_state_unchanged
    )

    print(f"\nDataset Version: {report_1.dataset_version}")
    print(f"Validator Version: {report_1.validator_version}\n")

    for cat_name, stats in report_1.category_statistics.items():
        total = stats["total"]
        passed = stats["passed"]
        status = "PASS" if (passed == total and total > 0) else "FAIL"
        print(f"{cat_name:<16}{passed:>2}/{total:<2} {status}")

    print("\n" + "-" * 50)
    print(f"{'TOTAL':<16}{report_1.passed_cases:>2}/{report_1.total_cases:<2} {'PASS' if report_1.failed_cases == 0 else 'FAIL'}")
    print(f"PASS RATE       {report_1.pass_rate:.2f}%\n")

    safety_status = "PASS" if report_1.all_safety_cases_passed else "FAIL"
    immutability_status = "PASS" if report_1.core_state_unchanged else "FAIL"
    determinism_status = "PASS" if determinism_passed else "FAIL"

    print(f"SAFETY HARD GATE:   {safety_status}")
    print(f"STATE IMMUTABILITY: {immutability_status}")
    print(f"DETERMINISM:        {determinism_status}")

    overall_passed = bool(
        report_1.failed_cases == 0
        and report_1.all_safety_cases_passed
        and report_1.core_state_unchanged
        and determinism_passed
    )

    print("\n" + "=" * 50)
    if overall_passed:
        print(" AI EVALUATION GATE: PASS")
        print("=" * 50)
        return 0
    else:
        print(" AI EVALUATION GATE: FAIL")
        if report_1.violations_summary:
            print("\nFailure Details:")
            for item in report_1.violations_summary:
                print(f"  - [{item['case_id']}] Category: {item['category']}, Actual: {item['actual_violations']}")
        print("=" * 50)
        return 1


if __name__ == "__main__":
    sys.exit(run_ai_evaluation_gate())
