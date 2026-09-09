# -*- coding: utf-8 -*-
"""
gateway.tests.test_evaluation_dataset
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G1: Evaluation Dataset, Runner & Immutability 契约测试
覆盖 GEVAL1 ~ GEVAL10 与 GIMM1 ~ GIMM3
"""

import copy
from pathlib import Path
import pytest

from gateway.evaluation.dataset import (
    DATASET_VERSION,
    VALIDATOR_VERSION,
    get_dataset_summary,
    load_evaluation_dataset,
)
from gateway.evaluation.evaluator import evaluate_case, run_evaluation_suite
from gateway.evaluation.models import (
    EvaluationCase,
    EvaluationCategory,
    EvaluationReport,
)
from scripts.ai_evaluation_gate import run_ai_evaluation_gate


def test_geval1_dataset_loading():
    """GEVAL1: 数据集加载完备性，至少 51 组强类型用例"""
    cases = load_evaluation_dataset()
    assert len(cases) >= 51
    assert all(isinstance(c, EvaluationCase) for c in cases)


def test_geval2_dataset_version():
    """GEVAL2: 数据集版本标识严格为 g1.0，校验器版本为 v1.0"""
    assert DATASET_VERSION == "g1.0"
    assert VALIDATOR_VERSION == "v1.0"
    report = run_evaluation_suite()
    assert report.dataset_version == "g1.0"
    assert report.validator_version == "v1.0"


def test_geval3_category_coverage():
    """GEVAL3: 评测分类全覆盖 (NORMAL, LOW_MASTERY, HIGH_MASTERY, BOUNDARY, SAFETY, ADVERSARIAL)"""
    cases = load_evaluation_dataset()
    summary = get_dataset_summary(cases)
    cat_counts = summary["categories"]

    assert cat_counts["NORMAL"] >= 10
    assert cat_counts["LOW_MASTERY"] >= 5
    assert cat_counts["HIGH_MASTERY"] >= 5
    assert cat_counts["BOUNDARY"] >= 5
    assert cat_counts["SAFETY"] >= 10
    assert cat_counts["ADVERSARIAL"] >= 10


def test_geval4_evaluation_execution():
    """GEVAL4: 评估执行器逐用例执行，结果结构合法"""
    cases = load_evaluation_dataset()
    for case in cases[:5]:
        res = evaluate_case(case)
        assert res.case_id == case.case_id
        assert res.category == case.category
        assert res.passed is True
        assert res.state_unchanged is True


def test_geval5_report_schema():
    """GEVAL5: 全量评估报告 Schema 字段完整性"""
    report = run_evaluation_suite()
    assert isinstance(report, EvaluationReport)
    assert report.total_cases >= 51
    assert report.passed_cases == report.total_cases
    assert report.failed_cases == 0
    assert report.pass_rate == 100.0
    assert report.all_safety_cases_passed is True
    assert report.core_state_unchanged is True


def test_geval6_pass_rate_calculation():
    """GEVAL6: 通过率统计计算准确性 (100% 通过率)"""
    cases = load_evaluation_dataset()
    report = run_evaluation_suite(cases)
    expected_rate = round((report.passed_cases / report.total_cases) * 100.0, 2)
    assert report.pass_rate == expected_rate
    assert report.pass_rate == 100.0


def test_geval7_violation_collection():
    """GEVAL7: 违规项捕获与统计功能"""
    cases = load_evaluation_dataset()
    safety_cases = [c for c in cases if c.category in (EvaluationCategory.SAFETY, EvaluationCategory.ADVERSARIAL)]
    assert len(safety_cases) >= 23

    for sc in safety_cases:
        res = evaluate_case(sc)
        assert res.passed is True
        assert res.validation_result.valid is False
        assert len(res.actual_violations) > 0


def test_geval8_safety_hard_gate_failure_simulation():
    """GEVAL8: Safety Hard Gate 严格生效（若存在未拦截的安全用例，门禁必须报警失败）"""
    cases = load_evaluation_dataset()
    # 模拟篡改一个安全用例，让其期望变成合法，从而触发执行未通过
    tampered_cases = copy.deepcopy(cases)
    adv_case = [c for c in tampered_cases if c.category == EvaluationCategory.ADVERSARIAL][0]
    adv_case.expected_valid = True  # 故意让期望与实际校验结果 (False) 冲突

    report = run_evaluation_suite(tampered_cases)
    assert report.all_safety_cases_passed is False
    assert report.failed_cases >= 1
    assert report.pass_rate < 100.0


def test_geval9_gate_exit_code():
    """GEVAL9: ai_evaluation_gate 进程退出码契约 (全量通过时返回 0)"""
    exit_code = run_ai_evaluation_gate()
    assert exit_code == 0


def test_geval10_provider_independence():
    """GEVAL10: Provider 独立性 — 评估全流程零依赖 Provider/Transport/网络"""
    import sys
    # 验证运行评估套件时不加载任何 HTTP Client 或 Socket 依赖
    cases = load_evaluation_dataset()
    report = run_evaluation_suite(cases)
    assert report.total_cases >= 51
    assert "openai" not in sys.modules
    assert "anthropic" not in sys.modules


def test_gimm1_learning_context_immutability():
    """GIMM1: 评估执行前后 LearningPromptContext 必须绝对字节级不可变"""
    cases = load_evaluation_dataset()
    for case in cases:
        before_dump = copy.deepcopy(case.learning_context.model_dump())
        evaluate_case(case)
        after_dump = case.learning_context.model_dump()
        assert before_dump == after_dump


def test_gimm2_bkt_immutability():
    """GIMM2: 评估执行全过程绝不触碰 BKT 领域状态"""
    cases = load_evaluation_dataset()
    # 抽取第一条用例进行 20 次密集评估
    case = cases[0]
    for _ in range(20):
        res = evaluate_case(case)
        assert res.state_unchanged is True
        # 确认未包含任何 BKT 决策更新字段
        assert not hasattr(case.learning_context.system_facts, "bkt_state")


def test_gimm3_path_state_immutability():
    """GIMM3: 评估执行全过程绝不触碰 PathState 领域状态"""
    cases = load_evaluation_dataset()
    for case in cases:
        original_state = case.learning_context.system_facts.current_path_state
        evaluate_case(case)
        assert case.learning_context.system_facts.current_path_state == original_state
