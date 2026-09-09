# -*- coding: utf-8 -*-
"""
gateway.evaluation.evaluator
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G1: Evaluation Executor & Immutability Verification (评测执行器与不可变性断言)

核心原则：
1. 深度不可变性 (Core Immutability)：执行评测前后严格深拷贝快照对比，断言上下文零改变
2. 确定性比对：验证语义校验结果与用例预期 (expected_valid, expected_violations) 完全吻合
3. 聚合全景报告：生成结构化 EvaluationReport，单独提供 Safety Hard Gate 裁决
"""

import copy
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from gateway.evaluation.dataset import (
    DATASET_VERSION,
    VALIDATOR_VERSION,
    load_evaluation_dataset,
)
from gateway.evaluation.models import (
    CaseEvaluationResult,
    EvaluationCase,
    EvaluationCategory,
    EvaluationReport,
    SemanticValidationResult,
)
from gateway.evaluation.validator import validate_ai_response
from gateway.models import LearningPromptContext, StructuredAIResponse


def evaluate_case(
    case: EvaluationCase,
    validator_func: Callable[[LearningPromptContext, StructuredAIResponse], SemanticValidationResult] = validate_ai_response,
) -> CaseEvaluationResult:
    """
    评估单条评测用例并验证状态深度不可变性

    @param case 强类型评测用例
    @param validator_func 语义校验函数（默认 validate_ai_response）
    @return CaseEvaluationResult 单用例评测执行结果
    """
    start_time = time.perf_counter()

    # 1. 执行前状态深拷贝快照
    context_before = copy.deepcopy(case.learning_context.model_dump())
    response_before = copy.deepcopy(case.candidate_response.model_dump())

    # 2. 执行确定性语义校验
    val_result = validator_func(case.learning_context, case.candidate_response)

    # 3. 执行后状态快照对比（断言深度不可变性）
    context_after = case.learning_context.model_dump()
    response_after = case.candidate_response.model_dump()

    state_unchanged = bool(
        context_before == context_after and response_before == response_after
    )

    duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

    # 4. 比对校验结果与用例预期
    # (a) 综合有效性吻合
    valid_matches = (val_result.valid == case.expected_valid)

    # (b) 违规项捕获判定：若预期不合法且定义了 expected_violations，必须至少命中预期违规之一
    violation_matches = True
    if not case.expected_valid and case.expected_violations:
        violation_matches = any(ev in val_result.violations for ev in case.expected_violations)

    # (c) 安全类用例特殊保护：若为 SAFETY 或 ADVERSARIAL，policy_compliant 或 factual_consistency 必须按预期拦截
    safety_rule_ok = True
    if case.category == EvaluationCategory.ADVERSARIAL:
        # 对抗类必须触发 policy_compliant=False 或相应违规
        if val_result.policy_compliant is True and not val_result.violations:
            safety_rule_ok = False
    elif case.category == EvaluationCategory.SAFETY:
        # 事实安全类必须触发 valid=False
        if val_result.valid is True:
            safety_rule_ok = False

    passed = bool(valid_matches and violation_matches and safety_rule_ok and state_unchanged)

    return CaseEvaluationResult(
        case_id=case.case_id,
        category=case.category,
        validation_result=val_result,
        passed=passed,
        expected_valid=case.expected_valid,
        expected_violations=case.expected_violations,
        actual_violations=val_result.violations,
        state_unchanged=state_unchanged,
        duration_ms=duration_ms,
    )


def run_evaluation_suite(
    cases: Optional[List[EvaluationCase]] = None,
    fixtures_dir: Optional[Path] = None,
    validator_func: Callable[[LearningPromptContext, StructuredAIResponse], SemanticValidationResult] = validate_ai_response,
) -> EvaluationReport:
    """
    运行全量评估套件并聚合 EvaluationReport

    @param cases 可选显式注入的用例列表，为空时自动加载标准数据集
    @param fixtures_dir 可选夹具目录路径
    @param validator_func 语义校验函数
    @return EvaluationReport 结构化评估套件报告
    """
    suite_start = time.perf_counter()

    if cases is None:
        cases = load_evaluation_dataset(fixtures_dir=fixtures_dir)

    total_cases = len(cases)
    passed_cases = 0
    failed_cases = 0

    category_stats: Dict[str, Dict[str, Any]] = {}
    for cat in EvaluationCategory:
        category_stats[cat.value] = {"total": 0, "passed": 0, "failed": 0}

    all_safety_passed = True
    core_state_unchanged = True
    violations_summary: List[Dict[str, Any]] = []

    for case in cases:
        result = evaluate_case(case, validator_func=validator_func)
        cat_key = case.category.value

        category_stats[cat_key]["total"] += 1

        if not result.state_unchanged:
            core_state_unchanged = False

        if result.passed:
            passed_cases += 1
            category_stats[cat_key]["passed"] += 1
        else:
            failed_cases += 1
            category_stats[cat_key]["failed"] += 1
            violations_summary.append({
                "case_id": case.case_id,
                "category": cat_key,
                "expected_valid": case.expected_valid,
                "actual_valid": result.validation_result.valid,
                "expected_violations": case.expected_violations,
                "actual_violations": result.actual_violations,
                "state_unchanged": result.state_unchanged,
            })

            if case.category in (EvaluationCategory.SAFETY, EvaluationCategory.ADVERSARIAL):
                all_safety_passed = False

    pass_rate = round((passed_cases / total_cases) * 100.0, 2) if total_cases > 0 else 0.0
    suite_duration_ms = round((time.perf_counter() - suite_start) * 1000, 2)

    return EvaluationReport(
        dataset_version=DATASET_VERSION,
        validator_version=VALIDATOR_VERSION,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        pass_rate=pass_rate,
        category_statistics=category_stats,
        duration_ms=suite_duration_ms,
        all_safety_cases_passed=all_safety_passed,
        core_state_unchanged=core_state_unchanged,
        violations_summary=violations_summary,
    )
