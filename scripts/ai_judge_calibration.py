# -*- coding: utf-8 -*-
"""
scripts/ai_judge_calibration.py
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: AI Judge Calibration CLI Tool
"""

import argparse
import json
import sys
from pathlib import Path

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gateway.evaluation.calibration.analyzer import run_calibration
from gateway.evaluation.calibration.bias import run_full_bias_audit
from gateway.evaluation.calibration.dataset import (
    load_calibration_dataset,
    load_human_labels,
    load_sentinel_cases,
)
from gateway.evaluation.judge.adapter import JudgeAdapter
from gateway.evaluation.judge.fake import FakeLLMJudge
from gateway.evaluation.judge.fusion import EvaluationFusionEngine
from gateway.evaluation.judge.models import JudgeDecision
from gateway.evaluation.validator import validate_ai_response


def show_dataset():
    cases = load_calibration_dataset()
    labels = load_human_labels()
    print("\n" + "=" * 50)
    print("  CALIBRATION DATASET OVERVIEW (g3-cp3.0)")
    print("=" * 50)
    print(f"Total Cases:        {len(cases)}")
    print(f"Total Human Labels: {len(labels)}")

    cat_counts = {}
    for c in cases:
        cat_counts[c.category.value] = cat_counts.get(c.category.value, 0) + 1

    print("\nCategory Distribution:")
    for cat, count in sorted(cat_counts.items()):
        print(f"  {cat:<18}: {count} cases")
    print("=" * 50 + "\n")


def show_metrics():
    judge = FakeLLMJudge(forced_mode="HIGH", forced_confidence=0.9)
    adapter = JudgeAdapter(judge=judge)
    report = run_calibration(judge_adapter=adapter)

    print("\n" + "=" * 50)
    print("  CALIBRATION METRICS SUMMARY")
    print("=" * 50)
    print(f"Dataset Size:           {report.dataset_size}")
    print(f"Decision Accuracy:      {report.decision_metrics.get('accuracy') * 100:.2f}%")
    print(f"Decision Precision:     {report.decision_metrics.get('precision') * 100:.2f}%")
    print(f"Decision Recall:        {report.decision_metrics.get('recall') * 100:.2f}%")
    print(f"Decision F1:            {report.decision_metrics.get('f1'):.4f}")
    print(f"False Accept Rate(FAR): {report.risk_metrics.get('false_accept_rate') * 100:.2f}%")
    print(f"False Reject Rate(FRR): {report.risk_metrics.get('false_reject_rate') * 100:.2f}%")
    print(f"Critical False Pass:    {report.risk_metrics.get('critical_false_pass_rate') * 100:.2f}%")
    print(f"Critical Recall:        {report.risk_metrics.get('critical_recall') * 100:.2f}%")
    print(f"Overall Score MAE:      {report.score_metrics.get('overall_mae'):.4f}")
    print(f"Human-Human Agreement:  {report.human_human_agreement}")
    print("=" * 50 + "\n")


def show_bias():
    judge = FakeLLMJudge(forced_mode="HIGH", forced_confidence=0.9)
    adapter = JudgeAdapter(judge=judge)
    bias_report = run_full_bias_audit(adapter)

    print("\n" + "=" * 50)
    print("  BIAS AUDIT REPORT")
    print("=" * 50)
    print(f"Verbosity Bias:   {bias_report['verbosity_bias']['status']} (delta={bias_report['verbosity_bias'].get('delta')})")
    print(f"Position Bias:    {bias_report['position_bias']['status']} ({bias_report['position_bias']['reason']})")
    print(f"Style Bias:       {bias_report['style_bias']['status']} (max_delta={bias_report['style_bias'].get('max_delta')})")
    print(f"Self-Preference:  {bias_report['self_preference']['status']} ({bias_report['self_preference']['reason']})")
    print("=" * 50 + "\n")


def show_sentinel():
    sentinels = load_sentinel_cases()
    engine = EvaluationFusionEngine()
    judge = FakeLLMJudge(forced_mode="HIGH", forced_confidence=0.95)
    adapter = JudgeAdapter(judge=judge)

    print("\n" + "=" * 50)
    print("  SENTINEL CASES VERIFICATION (G1 Supremacy)")
    print("=" * 50)
    passed_all = True
    for s in sentinels:
        det_res = validate_ai_response(s.context, s.candidate_response)
        j_res, failure = adapter.evaluate_safe(s.context, s.candidate_response)
        fusion_res = engine.fuse(det_res, j_res, failure)

        g1_block = (not det_res.valid or not det_res.policy_compliant or not det_res.factual_consistency)
        fusion_block = (fusion_res.decision == JudgeDecision.REJECT and fusion_res.final_valid is False)

        case_pass = g1_block and fusion_block
        if not case_pass:
            passed_all = False

        status_str = "PASS" if case_pass else "FAIL"
        print(f"  [{status_str}] {s.case_id} (G1 Block: {g1_block}, Fusion Block: {fusion_block})")

    print("-" * 50)
    print(f"Result: {'ALL SENTINELS BLOCKED (PASS)' if passed_all else 'SENTINEL FAILURE DETECTED'}")
    print("=" * 50 + "\n")


def show_report():
    judge = FakeLLMJudge(forced_mode="HIGH", forced_confidence=0.9)
    adapter = JudgeAdapter(judge=judge)
    report = run_calibration(judge_adapter=adapter)
    print(json.dumps(report.model_dump(), ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="AI Judge Calibration CLI Tool")
    parser.add_argument("--dataset", action="store_true", help="Display dataset overview")
    parser.add_argument("--metrics", action="store_true", help="Display calibration metrics")
    parser.add_argument("--bias", action="store_true", help="Display bias audit report")
    parser.add_argument("--sentinel", action="store_true", help="Run sentinel cases verification")
    parser.add_argument("--report", action="store_true", help="Output full calibration JSON report")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return

    if args.dataset:
        show_dataset()
    if args.metrics:
        show_metrics()
    if args.bias:
        show_bias()
    if args.sentinel:
        show_sentinel()
    if args.report:
        show_report()


if __name__ == "__main__":
    main()
