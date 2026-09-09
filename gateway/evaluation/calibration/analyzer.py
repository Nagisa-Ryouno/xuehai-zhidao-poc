# -*- coding: utf-8 -*-
"""
gateway.evaluation.calibration.analyzer
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Calibration Pipeline & Analysis Engine
"""

import copy
from typing import Any, Dict, List, Optional, Set

from gateway.evaluation.calibration.bias import run_full_bias_audit
from gateway.evaluation.calibration.dataset import (
    load_calibration_dataset,
    load_human_labels,
    load_sentinel_cases,
)
from gateway.evaluation.calibration.metrics import (
    calculate_category_breakdown,
    calculate_decision_metrics,
    calculate_human_agreement,
    calculate_risk_metrics,
    calculate_score_metrics,
)
from gateway.evaluation.calibration.models import (
    CALIBRATION_DATASET_VERSION,
    CALIBRATION_RUBRIC_VERSION,
    JUDGE_PROMPT_VERSION,
    CalibrationCase,
    CalibrationReport,
    ComparisonResult,
    HumanLabel,
)
from gateway.evaluation.judge.adapter import JudgeAdapter
from gateway.evaluation.judge.fusion import EvaluationFusionEngine
from gateway.evaluation.judge.models import (
    JudgeDecision,
    JudgeFailureClass,
    JudgeResult,
)
from gateway.evaluation.validator import validate_ai_response


def _infer_judge_decision(
    judge_res: Optional[JudgeResult],
    failure_class: JudgeFailureClass,
    accept_thresh: float = 0.80,
    review_thresh: float = 0.60,
    conf_thresh: float = 0.70,
) -> JudgeDecision:
    """从 Judge 独立打分与置信度推导 Judge 单独的判定倾向"""
    if judge_res is None or failure_class != JudgeFailureClass.NONE:
        return JudgeDecision.REVIEW
    if judge_res.overall_score >= accept_thresh and judge_res.confidence >= conf_thresh:
        return JudgeDecision.ACCEPT
    if judge_res.overall_score < review_thresh:
        return JudgeDecision.REJECT
    return JudgeDecision.REVIEW


def run_calibration(
    judge_adapter: JudgeAdapter,
    fusion_engine: Optional[EvaluationFusionEngine] = None,
    dataset: Optional[List[CalibrationCase]] = None,
    labels_map: Optional[Dict[str, List[HumanLabel]]] = None,
    sentinels: Optional[List[CalibrationCase]] = None,
) -> CalibrationReport:
    """
    运行全量校准评测分析管道 (Offline Calibration Pipeline)
    """
    cases = dataset if dataset is not None else load_calibration_dataset()
    labels = labels_map if labels_map is not None else load_human_labels()
    sentinel_list = sentinels if sentinels is not None else load_sentinel_cases()
    engine = fusion_engine if fusion_engine is not None else EvaluationFusionEngine()

    comparison_results: List[ComparisonResult] = []
    critical_ids: Set[str] = set()
    categories_map: Dict[str, Any] = {}

    for case in cases:
        categories_map[case.case_id] = case.category
        if case.critical_failure:
            critical_ids.add(case.case_id)

        # 状态不可变性快照
        before_dump = copy.deepcopy(case.context.model_dump())

        # G1 确定性底座校验
        det_res = validate_ai_response(case.context, case.candidate_response)

        # Judge 评估
        judge_res, failure = judge_adapter.evaluate_safe(case.context, case.candidate_response)

        # G1 + Judge 融合
        fusion_res = engine.fuse(det_res, judge_res, failure)

        # 状态不可变性断言
        after_dump = case.context.model_dump()
        if before_dump != after_dump:
            raise RuntimeError(f"State mutation detected during calibration of case '{case.case_id}'")

        # 获取人工黄金标签（取首要标注者）
        human_labels_for_case = labels.get(case.case_id)
        if not human_labels_for_case:
            raise ValueError(f"Missing human label for case '{case.case_id}'")
        primary_label = human_labels_for_case[0]

        # 计算 Judge 单独裁决倾向
        j_dec = _infer_judge_decision(judge_res, failure)

        # 是否发生关键缺陷错误放行 (Critical False Pass)
        is_crit_fp = bool(case.critical_failure and (j_dec == JudgeDecision.ACCEPT))

        h_scores = {
            "pedagogical_value": primary_label.pedagogical_value,
            "explanation_depth": primary_label.explanation_depth,
            "tone_appropriateness": primary_label.tone_appropriateness,
            "guidance_clarity": primary_label.guidance_clarity,
            "overall_quality": primary_label.overall_quality,
        }

        j_scores = (
            {
                "pedagogical_value": judge_res.dimension_scores.get("PEDAGOGICAL_QUALITY", 0.0),
                "explanation_depth": judge_res.dimension_scores.get("EXPLANATION_DEPTH", 0.0),
                "tone_appropriateness": judge_res.dimension_scores.get("EMPATHY", 0.0),
                "guidance_clarity": judge_res.dimension_scores.get("CLARITY", 0.0),
                "overall_quality": judge_res.overall_score,
                "overall_score": judge_res.overall_score,
            }
            if judge_res
            else {k: 0.0 for k in h_scores}
        )

        score_errors = {
            k: round(abs(h_scores[k] - j_scores[k]), 4)
            for k in h_scores
        }

        comp = ComparisonResult(
            case_id=case.case_id,
            human_decision=primary_label.decision,
            judge_decision=j_dec,
            decision_match=(primary_label.decision == j_dec),
            human_scores=h_scores,
            judge_scores=j_scores,
            score_errors=score_errors,
            critical_failure_match=bool(primary_label.critical_failure == case.critical_failure),
            is_critical_false_pass=is_crit_fp,
        )
        comparison_results.append(comp)

    # 1. 指标汇总
    decision_metrics = calculate_decision_metrics(comparison_results)
    risk_metrics = calculate_risk_metrics(comparison_results, critical_ids)
    score_metrics = calculate_score_metrics(comparison_results)
    category_breakdown = calculate_category_breakdown(comparison_results, categories_map)
    human_agreement = calculate_human_agreement(labels)

    # 2. 偏见审计
    bias_report = run_full_bias_audit(judge_adapter)

    # 3. Sentinel 安全底线测试
    sentinel_passed_count = 0
    sentinel_details = []
    for s_case in sentinel_list:
        s_det = validate_ai_response(s_case.context, s_case.candidate_response)
        s_judge, s_fail = judge_adapter.evaluate_safe(s_case.context, s_case.candidate_response)
        s_fusion = engine.fuse(s_det, s_judge, s_fail)

        # 核心断言：G1 必须拒绝，Fusion 必须强制 REJECT
        g1_rejected = not s_det.valid or not s_det.policy_compliant or not s_det.factual_consistency
        fusion_rejected = (s_fusion.decision == JudgeDecision.REJECT and s_fusion.final_valid is False)

        passed = g1_rejected and fusion_rejected
        if passed:
            sentinel_passed_count += 1

        sentinel_details.append({
            "case_id": s_case.case_id,
            "g1_rejected": g1_rejected,
            "fusion_rejected": fusion_rejected,
            "passed": passed,
            "violations": s_fusion.violations,
        })

    sentinel_report = {
        "total": len(sentinel_list),
        "passed": sentinel_passed_count,
        "status": "PASS" if sentinel_passed_count == len(sentinel_list) else "FAIL",
        "details": sentinel_details,
    }

    return CalibrationReport(
        dataset_version=CALIBRATION_DATASET_VERSION,
        rubric_version=CALIBRATION_RUBRIC_VERSION,
        judge_prompt_version=JUDGE_PROMPT_VERSION,
        dataset_size=len(cases),
        decision_metrics=decision_metrics,
        risk_metrics=risk_metrics,
        score_metrics=score_metrics,
        category_breakdown=category_breakdown,
        human_human_agreement=human_agreement["status"],
        bias_report=bias_report,
        sentinel_report=sentinel_report,
        offline_status="OFFLINE",
        privacy_status="SECURE",
    )
