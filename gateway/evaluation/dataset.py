# -*- coding: utf-8 -*-
"""
gateway.evaluation.dataset
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G1: Evaluation Dataset Loader & Versioning (黄金评测集加载器)

核心原则：
1. 绝对离线：仅从本地静态 JSON 夹具加载，禁止网络请求、外部下载或随机生成
2. 强类型校验：每一条用例均经过 EvaluationCase 强类型反序列化校验
3. 完整性防御：严格校验 case_id 唯一性、分类覆盖度、总数下限 (>=51) 以及预期结果完备性
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from gateway.evaluation.models import EvaluationCase, EvaluationCategory

DATASET_VERSION: str = "g1.0"
VALIDATOR_VERSION: str = "v1.0"

DEFAULT_FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures"

REQUIRED_FIXTURE_FILES: List[str] = [
    "normal_cases.json",
    "boundary_cases.json",
    "safety_cases.json",
    "adversarial_cases.json",
]


def load_evaluation_dataset(
    fixtures_dir: Optional[Path] = None,
) -> List[EvaluationCase]:
    """
    加载并强类型校验版本化的 Golden Evaluation Dataset (g1.0)

    @param fixtures_dir 夹具目录路径（默认 gateway/evaluation/fixtures）
    @return List[EvaluationCase] 验证通过的完整评测用例列表
    @raises FileNotFoundError 当夹具文件缺失时受控抛出
    @raises ValueError 当 JSON 格式非法、用例字段缺失、ID 重复或数量不合规时受控抛出
    """
    target_dir = Path(fixtures_dir) if fixtures_dir is not None else DEFAULT_FIXTURES_DIR

    if not target_dir.exists() or not target_dir.is_dir():
        raise FileNotFoundError(f"Evaluation fixtures directory not found: {target_dir}")

    all_cases: List[EvaluationCase] = []
    seen_case_ids: set[str] = set()
    found_categories: set[EvaluationCategory] = set()

    for filename in REQUIRED_FIXTURE_FILES:
        file_path = target_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(
                f"Required evaluation fixture file missing: {file_path}"
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Malformed JSON in evaluation fixture {filename}: {str(e)}"
            ) from e
        except Exception as e:
            raise ValueError(
                f"Failed to read evaluation fixture {filename}: {str(e)}"
            ) from e

        if not isinstance(raw_data, list):
            raise ValueError(
                f"Invalid fixture format in {filename}: root element must be a JSON array"
            )

        for idx, raw_item in enumerate(raw_data):
            try:
                case = EvaluationCase.model_validate(raw_item)
            except Exception as e:
                raise ValueError(
                    f"Validation failed for case at index {idx} in {filename}: {str(e)}"
                ) from e

            # 校验唯一性
            if case.case_id in seen_case_ids:
                raise ValueError(
                    f"Duplicate case_id detected in dataset: '{case.case_id}' in {filename}"
                )
            seen_case_ids.add(case.case_id)
            found_categories.add(case.category)

            # 校验 Safety 与 Adversarial 用例的预期完整性
            if case.category in (EvaluationCategory.SAFETY, EvaluationCategory.ADVERSARIAL):
                if case.expected_valid is not False:
                    raise ValueError(
                        f"Safety/Adversarial case '{case.case_id}' must have expected_valid=False"
                    )
                if not case.expected_violations:
                    raise ValueError(
                        f"Safety/Adversarial case '{case.case_id}' must define non-empty expected_violations"
                    )

            all_cases.append(case)

    # 校验数量底线 (>= 51)
    if len(all_cases) < 51:
        raise ValueError(
            f"Dataset incomplete: expected at least 51 cases, got {len(all_cases)}"
        )

    # 校验 6 大分类完整覆盖
    expected_categories = {cat for cat in EvaluationCategory}
    missing_categories = expected_categories - found_categories
    if missing_categories:
        missing_names = [c.value for c in missing_categories]
        raise ValueError(
            f"Dataset missing required evaluation categories: {missing_names}"
        )

    return all_cases


def get_dataset_summary(cases: List[EvaluationCase]) -> Dict[str, Any]:
    """
    提取评测数据集的统计概览
    """
    cat_counts: Dict[str, int] = {}
    for case in cases:
        cat_key = case.category.value
        cat_counts[cat_key] = cat_counts.get(cat_key, 0) + 1

    return {
        "dataset_version": DATASET_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "total_cases": len(cases),
        "categories": cat_counts,
        "safety_total": cat_counts.get("SAFETY", 0) + cat_counts.get("ADVERSARIAL", 0),
    }
