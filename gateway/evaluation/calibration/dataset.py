# -*- coding: utf-8 -*-
"""
gateway.evaluation.calibration.dataset
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Calibration Dataset & Human Gold Label Loader
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from gateway.evaluation.calibration.models import (
    CALIBRATION_DATASET_VERSION,
    CalibrationCase,
    CalibrationCategory,
    HumanLabel,
)

DEFAULT_CALIBRATION_FIXTURES_DIR: Path = (
    Path(__file__).resolve().parent / "fixtures"
)

FORBIDDEN_PII_OR_SECRET_PATTERNS: List[str] = [
    "sk-",
    "bearer ",
    "api_key=",
    "api_secret=",
    "@example.com",
    "13800138000",
    "身份证",
]


def _check_security_and_pii(raw_text: str, source_identifier: str) -> None:
    lower_text = raw_text.lower()
    for pattern in FORBIDDEN_PII_OR_SECRET_PATTERNS:
        if pattern in lower_text:
            raise ValueError(
                f"Security violation: detected forbidden pattern '{pattern}' in {source_identifier}"
            )


def load_calibration_dataset(
    fixtures_dir: Optional[Path] = None,
) -> List[CalibrationCase]:
    """
    加载并强类型校验版本化的 Calibration Dataset (g3-cp3.0)

    @param fixtures_dir 夹具目录路径（默认 gateway/evaluation/calibration/fixtures）
    @return List[CalibrationCase] 校验通过的校准用例列表
    """
    target_dir = Path(fixtures_dir) if fixtures_dir is not None else DEFAULT_CALIBRATION_FIXTURES_DIR
    cases_file = target_dir / "calibration_cases.json"

    if not cases_file.exists():
        raise FileNotFoundError(f"Calibration cases fixture not found: {cases_file}")

    with open(cases_file, "r", encoding="utf-8") as f:
        content = f.read()

    _check_security_and_pii(content, str(cases_file))

    try:
        raw_list = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in {cases_file}: {e}") from e

    if not isinstance(raw_list, list):
        raise ValueError(f"Root of {cases_file} must be a JSON array")

    if len(raw_list) < 50:
        raise ValueError(f"Calibration dataset must contain at least 50 cases, found {len(raw_list)}")

    cases: List[CalibrationCase] = []
    seen_ids: set[str] = set()
    found_categories: set[CalibrationCategory] = set()

    for idx, raw_item in enumerate(raw_list):
        try:
            case = CalibrationCase.model_validate(raw_item)
        except Exception as e:
            raise ValueError(f"Invalid CalibrationCase at index {idx} in {cases_file}: {e}") from e

        if case.case_id in seen_ids:
            raise ValueError(f"Duplicate case_id '{case.case_id}' in {cases_file}")
        seen_ids.add(case.case_id)
        found_categories.add(case.category)
        cases.append(case)

    # 验证分类覆盖度：8 个分类必须全部存在
    all_categories = set(CalibrationCategory)
    missing = all_categories - found_categories
    if missing:
        raise ValueError(f"Missing required calibration categories in dataset: {missing}")

    return cases


def load_human_labels(
    fixtures_dir: Optional[Path] = None,
) -> Dict[str, List[HumanLabel]]:
    """
    加载并强类型校验人工黄金标注 (Human Gold Labels)

    @param fixtures_dir 夹具目录路径（默认 gateway/evaluation/calibration/fixtures）
    @return Dict[str, List[HumanLabel]] 按 case_id 索引的人工标注列表字典
    """
    target_dir = Path(fixtures_dir) if fixtures_dir is not None else DEFAULT_CALIBRATION_FIXTURES_DIR
    labels_file = target_dir / "human_labels.json"

    if not labels_file.exists():
        raise FileNotFoundError(f"Human labels fixture not found: {labels_file}")

    with open(labels_file, "r", encoding="utf-8") as f:
        content = f.read()

    _check_security_and_pii(content, str(labels_file))

    try:
        raw_dict = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in {labels_file}: {e}") from e

    if not isinstance(raw_dict, dict):
        raise ValueError(f"Root of {labels_file} must be a JSON object mapping case_id to labels")

    if len(raw_dict) < 50:
        raise ValueError(f"Human labels fixture must map at least 50 cases, found {len(raw_dict)}")

    result: Dict[str, List[HumanLabel]] = {}
    for case_id, label_items in raw_dict.items():
        if not isinstance(label_items, list) or len(label_items) == 0:
            raise ValueError(f"Case '{case_id}' must have at least one HumanLabel in {labels_file}")

        labels: List[HumanLabel] = []
        for idx, item in enumerate(label_items):
            try:
                label = HumanLabel.model_validate(item)
            except Exception as e:
                raise ValueError(f"Invalid HumanLabel for case '{case_id}' index {idx}: {e}") from e

            if label.case_id != case_id:
                raise ValueError(
                    f"Label case_id '{label.case_id}' mismatch with map key '{case_id}' in {labels_file}"
                )
            labels.append(label)

        result[case_id] = labels

    return result


def load_sentinel_cases(
    fixtures_dir: Optional[Path] = None,
) -> List[CalibrationCase]:
    """
    加载并强类型校验安全底线 Sentinel 样本集

    @param fixtures_dir 夹具目录路径（默认 gateway/evaluation/calibration/fixtures）
    @return List[CalibrationCase] Sentinel 安全用例列表
    """
    target_dir = Path(fixtures_dir) if fixtures_dir is not None else DEFAULT_CALIBRATION_FIXTURES_DIR
    sentinel_file = target_dir / "sentinel_cases.json"

    if not sentinel_file.exists():
        raise FileNotFoundError(f"Sentinel cases fixture not found: {sentinel_file}")

    with open(sentinel_file, "r", encoding="utf-8") as f:
        content = f.read()

    _check_security_and_pii(content, str(sentinel_file))

    try:
        raw_list = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in {sentinel_file}: {e}") from e

    if not isinstance(raw_list, list):
        raise ValueError(f"Root of {sentinel_file} must be a JSON array")

    if len(raw_list) < 9:
        raise ValueError(f"Sentinel cases must contain at least 9 cases, found {len(raw_list)}")

    sentinels: List[CalibrationCase] = []
    seen_ids: set[str] = set()

    for idx, raw_item in enumerate(raw_list):
        try:
            case = CalibrationCase.model_validate(raw_item)
        except Exception as e:
            raise ValueError(f"Invalid Sentinel CalibrationCase at index {idx}: {e}") from e

        if case.case_id in seen_ids:
            raise ValueError(f"Duplicate sentinel case_id '{case.case_id}' in {sentinel_file}")
        seen_ids.add(case.case_id)

        if not case.critical_failure:
            raise ValueError(f"Sentinel case '{case.case_id}' must set critical_failure=True")
        if not case.expected_violations:
            raise ValueError(f"Sentinel case '{case.case_id}' must specify expected_violations")

        sentinels.append(case)

    return sentinels
