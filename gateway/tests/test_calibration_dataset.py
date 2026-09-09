# -*- coding: utf-8 -*-
"""
gateway.tests.test_calibration_dataset
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Calibration Dataset & Fixture Loading Test Suite
"""

import pytest
from pathlib import Path

from gateway.evaluation.calibration.dataset import (
    load_calibration_dataset,
    load_human_labels,
    load_sentinel_cases,
    DEFAULT_CALIBRATION_FIXTURES_DIR,
)
from gateway.evaluation.calibration.models import (
    CalibrationCategory,
    CalibrationCase,
    HumanLabel,
)


class TestCalibrationDataset:
    def test_fixtures_directory_exists(self):
        assert DEFAULT_CALIBRATION_FIXTURES_DIR.exists()
        assert DEFAULT_CALIBRATION_FIXTURES_DIR.is_dir()

    def test_load_calibration_dataset_count_and_uniqueness(self):
        cases = load_calibration_dataset()
        assert len(cases) == 50

        # Check unique case IDs
        case_ids = [c.case_id for c in cases]
        assert len(case_ids) == len(set(case_ids))

    def test_category_distribution(self):
        cases = load_calibration_dataset()
        counts = {}
        for c in cases:
            counts[c.category] = counts.get(c.category, 0) + 1

        assert counts[CalibrationCategory.NORMAL] == 10
        assert counts[CalibrationCategory.LOW_MASTERY] == 5
        assert counts[CalibrationCategory.HIGH_MASTERY] == 5
        assert counts[CalibrationCategory.BOUNDARY] == 8
        assert counts[CalibrationCategory.SAFETY] == 8
        assert counts[CalibrationCategory.FACT_CRITICAL] == 6
        assert counts[CalibrationCategory.ADVERSARIAL] == 5
        assert counts[CalibrationCategory.OFF_TOPIC] == 3

    def test_boundary_cases_coverage(self):
        cases = load_calibration_dataset()
        boundary_cases = [c for c in cases if c.category == CalibrationCategory.BOUNDARY]
        masteries = {c.context.system_facts.current_mastery_percent for c in boundary_cases}
        # Must cover 0%, 79.9%, 80.0%, 80.1%, 100%
        assert 0.0 in masteries
        assert 79.9 in masteries
        assert 80.0 in masteries
        assert 80.1 in masteries
        assert 100.0 in masteries

    def test_human_labels_match_dataset(self):
        cases = load_calibration_dataset()
        labels_by_case = load_human_labels()

        assert len(labels_by_case) == 50
        for c in cases:
            assert c.case_id in labels_by_case
            labels = labels_by_case[c.case_id]
            assert len(labels) >= 1
            for label in labels:
                assert label.case_id == c.case_id
                assert 0.0 <= label.overall_quality <= 1.0

    def test_sentinel_cases_count_and_validity(self):
        sentinels = load_sentinel_cases()
        assert len(sentinels) >= 9

        seen_ids = set()
        for s in sentinels:
            assert s.case_id not in seen_ids
            seen_ids.add(s.case_id)
            assert s.critical_failure is True
            assert len(s.expected_violations) > 0

    def test_no_pii_or_secrets_in_fixtures(self):
        cases = load_calibration_dataset()
        sentinels = load_sentinel_cases()

        forbidden_patterns = [
            "sk-", "bearer ", "api_key=", "api_secret=",
            "@example.com", "13800138000", "身份证"
        ]

        for c in cases + sentinels:
            raw_text = c.model_dump_json().lower()
            for pattern in forbidden_patterns:
                assert pattern not in raw_text, f"Potential PII/Secret '{pattern}' detected in case {c.case_id}"
