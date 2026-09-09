# -*- coding: utf-8 -*-
"""
scripts/ai_judge_shadow.py
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: AI Judge Shadow Runtime CLI Tool (默认离线演练工具)
"""

import argparse
import json
import sys
from pathlib import Path

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gateway.evaluation.calibration.dataset import load_calibration_dataset
from gateway.evaluation.drift.baseline import load_default_drift_baseline
from gateway.evaluation.drift.detector import JudgeDriftDetector
from gateway.evaluation.judge.adapter import JudgeAdapter
from gateway.evaluation.judge.real import RealLLMJudge
from gateway.evaluation.judge.runtime import JudgeRuntimePolicy
from gateway.evaluation.review.queue import HumanReviewQueue
from gateway.evaluation.shadow.fixtures.mock_transport import MockRealJudgeTransport
from gateway.evaluation.shadow.runtime import ShadowEvaluationRuntime
from gateway.evaluation.shadow.sampling import ShadowSamplingPolicy
from gateway.evaluation.validator import validate_ai_response


def run_dry_run():
    print("\n" + "=" * 50)
    print("  AI JUDGE SHADOW RUNTIME: DRY-RUN MODE")
    print("=" * 50)
    policy = JudgeRuntimePolicy(enabled=False, shadow_only=True, allow_production_decision=False)
    sampling = ShadowSamplingPolicy(sample_rate=0.0)
    runtime = ShadowEvaluationRuntime(policy=policy, sampling_policy=sampling)

    cases = load_calibration_dataset()
    sample_case = cases[0]
    g1_res = validate_ai_response(sample_case.context, sample_case.candidate_response)

    outcome = runtime.evaluate(
        case_id=sample_case.case_id,
        context=sample_case.context,
        response=sample_case.candidate_response,
        g1_result=g1_res,
    )

    print(f"Policy Enabled:               {policy.enabled}")
    print(f"Sampling Rate:                {sampling.sample_rate}")
    print(f"Allow Production Decision:    {policy.allow_production_decision}")
    print(f"Runtime Evaluation Outcome:   {outcome} (Expected: None, skipped silently)")
    print(f"Network Status:               100% OFFLINE")
    print("=" * 50 + "\n")


def run_simulate():
    print("\n" + "=" * 50)
    print("  AI JUDGE SHADOW RUNTIME: SIMULATION HARNESS")
    print("=" * 50)
    mock_transport = MockRealJudgeTransport(mode="SUCCESS")
    real_judge = RealLLMJudge(transport=mock_transport, model="simulated-gpt")
    adapter = JudgeAdapter(judge=real_judge)

    policy = JudgeRuntimePolicy(
        enabled=True, shadow_only=True, allow_production_decision=False, provider="mock", model="sim-v1"
    )
    sampling = ShadowSamplingPolicy(sample_rate=1.0)
    review_queue = HumanReviewQueue()

    runtime = ShadowEvaluationRuntime(
        policy=policy,
        sampling_policy=sampling,
        judge_adapter=adapter,
        review_queue=review_queue,
    )

    cases = load_calibration_dataset()
    sim_count = min(5, len(cases))
    print(f"Simulating {sim_count} Shadow Evaluations in offline sandbox...")

    for i in range(sim_count):
        case = cases[i]
        g1_res = validate_ai_response(case.context, case.candidate_response)
        outcome = runtime.evaluate(
            case_id=case.case_id,
            context=case.context,
            response=case.candidate_response,
            g1_result=g1_res,
            risk_level=case.risk_level.value,
            category=case.category.value,
        )
        assert outcome is not None
        assert outcome.production_decision_affected is False
        print(f"  [{i+1}/{sim_count}] Case {case.case_id}: Shadow Recorded={outcome.record is not None}, "
              f"Escalated={outcome.escalated_to_human_review}, ProductionAffected={outcome.production_decision_affected}")

    print(f"\nReview Queue Pending Items: {review_queue.count()}")
    print("=" * 50 + "\n")


def run_drift():
    print("\n" + "=" * 50)
    print("  AI JUDGE DRIFT DETECTOR AUDIT")
    print("=" * 50)
    detector = JudgeDriftDetector()
    base = load_default_drift_baseline()

    # 模拟正常无漂移指标
    normal_report = detector.detect_drift({
        "accept_rate": base.accept_rate + 0.02,
        "average_score": base.average_score + 0.01,
        "critical_false_pass_rate": 0.0,
        "failure_rate": 0.0,
    })
    print(f"[Normal Batch] Status: {normal_report.status.value}, Alerts: {len(normal_report.alerts)}")

    # 模拟严重漂移指标
    drift_report = detector.detect_drift({
        "accept_rate": base.accept_rate + 0.35, # 严重偏离
        "average_score": 0.95,
        "critical_false_pass_rate": 0.15,       # 致命漂移
        "failure_rate": 0.20,
    })
    print(f"[Drifted Batch] Status: {drift_report.status.value}, Alerts: {len(drift_report.alerts)}")
    for a in drift_report.alerts:
        print(f"  - [{a.severity}] {a.metric_name}: {a.reason}")
    print("=" * 50 + "\n")


def run_review():
    print("\n" + "=" * 50)
    print("  HUMAN REVIEW QUEUE STATUS")
    print("=" * 50)
    queue = HumanReviewQueue()
    print(f"Active Review Queue Items: {queue.count()}")
    print("Queue Semantics: In-memory, read-only observation, zero production mutation.")
    print("=" * 50 + "\n")


def run_report():
    base = load_default_drift_baseline()
    policy = JudgeRuntimePolicy()
    sampling = ShadowSamplingPolicy()
    report_dict = {
        "runtime_policy_version": policy.version,
        "shadow_schema_version": "g4.0",
        "policy": policy.model_dump(),
        "sampling": sampling.model_dump(),
        "drift_baseline": base.model_dump(),
        "status": "OFFLINE_AND_SAFE",
    }
    print(json.dumps(report_dict, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="AI Judge Shadow Runtime CLI")
    parser.add_argument("--dry-run", action="store_true", help="Execute safe default dry-run")
    parser.add_argument("--simulate", action="store_true", help="Run offline simulation harness")
    parser.add_argument("--drift", action="store_true", help="Run drift detection audit")
    parser.add_argument("--review", action="store_true", help="Check human review queue status")
    parser.add_argument("--report", action="store_true", help="Output runtime configuration JSON report")

    args = parser.parse_args()

    # 默认行为: --dry-run
    if len(sys.argv) == 1 or args.dry_run:
        run_dry_run()
        return

    if args.simulate:
        run_simulate()
    if args.drift:
        run_drift()
    if args.review:
        run_review()
    if args.report:
        run_report()


if __name__ == "__main__":
    main()
