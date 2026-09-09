# -*- coding: utf-8 -*-
"""
gateway.evaluation.calibration.metrics
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Calibration Metrics & Agreement Computations
"""

import math
from typing import Any, Dict, List, Optional, Set

from gateway.evaluation.calibration.models import (
    CalibrationCategory,
    ComparisonResult,
    HumanLabel,
)
from gateway.evaluation.judge.models import JudgeDecision


def calculate_decision_metrics(
    comparison_results: List[ComparisonResult],
    positive_class: JudgeDecision = JudgeDecision.ACCEPT,
) -> Dict[str, Any]:
    """
    计算裁决层面对齐指标（Accuracy, Precision, Recall, F1, 混淆矩阵）
    """
    total = len(comparison_results)
    if total == 0:
        return {
            "total": 0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "confusion_matrix": {},
        }

    # 初始化 3x3 混淆矩阵: [Human][Judge]
    cm: Dict[str, Dict[str, int]] = {
        h.value: {j.value: 0 for j in JudgeDecision}
        for h in JudgeDecision
    }

    correct_count = 0
    tp = 0
    fp = 0
    fn = 0

    for comp in comparison_results:
        h_dec = comp.human_decision.value
        j_dec = comp.judge_decision.value
        cm[h_dec][j_dec] += 1

        if comp.decision_match:
            correct_count += 1

        is_h_pos = (comp.human_decision == positive_class)
        is_j_pos = (comp.judge_decision == positive_class)

        if is_h_pos and is_j_pos:
            tp += 1
        elif not is_h_pos and is_j_pos:
            fp += 1
        elif is_h_pos and not is_j_pos:
            fn += 1

    accuracy = round(correct_count / total, 4)
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    return {
        "total": total,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "positive_class": positive_class.value,
        "confusion_matrix": cm,
    }


def calculate_risk_metrics(
    comparison_results: List[ComparisonResult],
    critical_case_ids: Set[str],
) -> Dict[str, Any]:
    """
    计算安全与事实风控关键指标 (FAR, FRR, Critical False Pass, Critical Recall)

    - False Accept Rate (FAR): 人工判为 REVIEW 或 REJECT（非 ACCEPT），但 Judge 错误判为 ACCEPT 的比率
    - False Reject Rate (FRR): 人工判为 ACCEPT，但 Judge 错误判为 REJECT 的比率
    - Critical False-Pass Rate: 关键安全/事实阻断样本中，被 Judge 放行判为 ACCEPT 的比率（零容忍）
    - Critical Recall: 关键安全/事实阻断样本中，被 Judge 正确识别并判为 REJECT 的比率
    """
    non_accept_human_count = 0
    false_accept_count = 0

    accept_human_count = 0
    false_reject_count = 0

    critical_total = 0
    critical_false_pass = 0
    critical_rejection = 0

    for comp in comparison_results:
        is_crit = comp.case_id in critical_case_ids

        # FAR 计算
        if comp.human_decision != JudgeDecision.ACCEPT:
            non_accept_human_count += 1
            if comp.judge_decision == JudgeDecision.ACCEPT:
                false_accept_count += 1

        # FRR 计算
        if comp.human_decision == JudgeDecision.ACCEPT:
            accept_human_count += 1
            if comp.judge_decision == JudgeDecision.REJECT:
                false_reject_count += 1

        # Critical 指标
        if is_crit:
            critical_total += 1
            if comp.judge_decision == JudgeDecision.ACCEPT:
                critical_false_pass += 1
            if comp.judge_decision == JudgeDecision.REJECT:
                critical_rejection += 1

    far = round(false_accept_count / non_accept_human_count, 4) if non_accept_human_count > 0 else 0.0
    frr = round(false_reject_count / accept_human_count, 4) if accept_human_count > 0 else 0.0
    crit_fp_rate = round(critical_false_pass / critical_total, 4) if critical_total > 0 else 0.0
    crit_recall = round(critical_rejection / critical_total, 4) if critical_total > 0 else 0.0

    return {
        "false_accept_rate": far,
        "false_reject_rate": frr,
        "critical_cases_total": critical_total,
        "critical_false_pass_count": critical_false_pass,
        "critical_false_pass_rate": crit_fp_rate,
        "critical_recall": crit_recall,
    }


def _calculate_pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    diff_x = [x - mean_x for x in xs]
    diff_y = [y - mean_y for y in ys]
    var_x = sum(d * d for d in diff_x)
    var_y = sum(d * d for d in diff_y)
    if var_x <= 1e-9 or var_y <= 1e-9:
        return None
    cov = sum(dx * dy for dx, dy in zip(diff_x, diff_y))
    return round(cov / math.sqrt(var_x * var_y), 4)


def _calculate_spearman(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) < 2 or len(xs) != len(ys):
        return None

    def rank(seq: List[float]) -> List[float]:
        sorted_indices = sorted(range(len(seq)), key=lambda i: seq[i])
        ranks = [0.0] * len(seq)
        for r, idx in enumerate(sorted_indices, start=1):
            ranks[idx] = float(r)
        return ranks

    rank_x = rank(xs)
    rank_y = rank(ys)
    return _calculate_pearson(rank_x, rank_y)


def calculate_score_metrics(
    comparison_results: List[ComparisonResult],
) -> Dict[str, Any]:
    """
    计算评分连续层面对齐指标（MAE，相关系数）
    """
    if not comparison_results:
        return {"overall_mae": 0.0, "dimensions": {}}

    # 汇总各维度得分对
    dim_pairs: Dict[str, Dict[str, List[float]]] = {}
    all_errors: List[float] = []

    for comp in comparison_results:
        for dim, h_val in comp.human_scores.items():
            if dim not in dim_pairs:
                dim_pairs[dim] = {"human": [], "judge": []}
            # 兼容 judge_scores 命名（如 overall_score 对齐 overall_quality）
            j_val = comp.judge_scores.get(dim)
            if j_val is None and dim == "overall_quality":
                j_val = comp.judge_scores.get("overall_score")
            if j_val is not None:
                dim_pairs[dim]["human"].append(h_val)
                dim_pairs[dim]["judge"].append(j_val)
                all_errors.append(abs(h_val - j_val))

    dimensions_result: Dict[str, Any] = {}
    for dim, pairs in dim_pairs.items():
        h_vals = pairs["human"]
        j_vals = pairs["judge"]
        if not h_vals:
            continue
        mae = round(sum(abs(h - j) for h, j in zip(h_vals, j_vals)) / len(h_vals), 4)
        spearman = _calculate_spearman(h_vals, j_vals)
        pearson = _calculate_pearson(h_vals, j_vals)
        dimensions_result[dim] = {
            "count": len(h_vals),
            "mae": mae,
            "spearman": spearman if spearman is not None else "NOT_AVAILABLE",
            "pearson": pearson if pearson is not None else "NOT_AVAILABLE",
        }

    overall_mae = round(sum(all_errors) / len(all_errors), 4) if all_errors else 0.0

    return {
        "overall_mae": overall_mae,
        "dimensions": dimensions_result,
    }


def calculate_category_breakdown(
    comparison_results: List[ComparisonResult],
    case_categories: Dict[str, CalibrationCategory],
) -> Dict[str, Any]:
    """
    按用例分类输出详细表现细分
    """
    breakdown: Dict[str, Dict[str, Any]] = {}

    for comp in comparison_results:
        cat_enum = case_categories.get(comp.case_id, CalibrationCategory.NORMAL)
        cat_name = cat_enum.value

        if cat_name not in breakdown:
            breakdown[cat_name] = {
                "total": 0,
                "matched": 0,
                "false_accepts": 0,
                "false_rejects": 0,
            }

        entry = breakdown[cat_name]
        entry["total"] += 1
        if comp.decision_match:
            entry["matched"] += 1

        if comp.human_decision != JudgeDecision.ACCEPT and comp.judge_decision == JudgeDecision.ACCEPT:
            entry["false_accepts"] += 1
        if comp.human_decision == JudgeDecision.ACCEPT and comp.judge_decision == JudgeDecision.REJECT:
            entry["false_rejects"] += 1

    for cat_name, entry in breakdown.items():
        entry["accuracy"] = (
            round(entry["matched"] / entry["total"], 4) if entry["total"] > 0 else 0.0
        )

    return breakdown


def calculate_human_agreement(
    labels_by_case: Dict[str, List[HumanLabel]],
) -> Dict[str, Any]:
    """
    计算人工标注者之间的一致性 (Human-Human Agreement)
    若只有 1 名标注者，明确返回 NOT_AVAILABLE，严禁伪造数字
    """
    max_annotators = max((len(labels) for labels in labels_by_case.values()), default=0)

    if max_annotators < 2:
        return {
            "status": "NOT_AVAILABLE",
            "annotators_count": max_annotators,
            "reason": "Only one annotator available in gold dataset; cannot compute inter-annotator agreement",
            "cohen_kappa": None,
            "raw_agreement": None,
        }

    # 若存在两名标注者，计算两两 Cohen's Kappa 和 Raw Agreement
    paired_cases = [c for c, labels in labels_by_case.items() if len(labels) >= 2]
    if not paired_cases:
        return {
            "status": "NOT_AVAILABLE",
            "annotators_count": max_annotators,
            "reason": "No common cases annotated by multiple annotators",
            "cohen_kappa": None,
            "raw_agreement": None,
        }

    matches = 0
    total = len(paired_cases)
    for c in paired_cases:
        l1, l2 = labels_by_case[c][0], labels_by_case[c][1]
        if l1.decision == l2.decision:
            matches += 1

    raw_agreement = round(matches / total, 4)

    return {
        "status": "AVAILABLE",
        "annotators_count": max_annotators,
        "paired_cases_count": total,
        "raw_agreement": raw_agreement,
        "cohen_kappa": None,  # 简化支持
    }
