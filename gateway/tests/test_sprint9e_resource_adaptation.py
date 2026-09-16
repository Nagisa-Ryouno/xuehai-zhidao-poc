# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint9e_resource_adaptation
===============================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-E
资源学习效果档案与自适应策略二次排序自动化测试套件

涵盖：
1. 确定性效果分级边界：usage_count = 0, 1, 2 与 average_delta = 0.10, 0.02, -0.02 严谨断言；
2. 分值调整映射：+2/+1/0/-1/0 严格对应；
3. 只读聚合计算准确性：usage_count, average_delta, last_delta；
4. 学生隔离性：S001 绝不泄露至 S002；
5. 考点隔离性：K07 绝不混入 K08；
6. 候选池内确定性二次排序：B(+2) 跃升超越 A(+1)；
7. 相同分数平局仲裁：严格保持原始候选顺序；
8. 样本不足优雅降级：无历史数据时候选推荐顺序完全不变；
9. 权威不变性：推荐操作绝对不修改 bkt_states.json 与 learning_events.jsonl；
10. HTTP API 端点正确性与 404 边界防御。
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient

from gateway.api import app
from gateway.learning.resource_effectiveness import (
    ADJUSTMENT_SCORES,
    DeterministicAdaptationStrategy,
    HistoricalEffectiveness,
    ResourceEffectivenessAggregator,
    ResourceEffectivenessProfile,
    classify_effectiveness,
    default_adaptation_strategy,
)
from gateway.learning.resources import (
    LearningResource,
    ResourceType,
    default_resource_resolver,
)
from gateway.learning.resources.resolver import ResourceResolver

client = TestClient(app)


@pytest.fixture
def api_client():
    return client


@pytest.fixture
def temp_events_file(tmp_path: Path) -> Path:
    """提供独立的临时 resource_effectiveness_events.jsonl 测试文件"""
    file_path = tmp_path / "test_effectiveness_events.jsonl"
    file_path.write_text("", encoding="utf-8")
    return file_path


# =============================================================================
# 1. 效果分级判定与边界测试
# =============================================================================

def test_01_classify_insufficient_data_when_usage_less_than_2():
    """usage_count < 2 时一律判定为 INSUFFICIENT_DATA，哪怕单次增量极大"""
    assert classify_effectiveness(0, 0.25) == HistoricalEffectiveness.INSUFFICIENT_DATA
    assert classify_effectiveness(1, 0.25) == HistoricalEffectiveness.INSUFFICIENT_DATA
    assert classify_effectiveness(1, -0.15) == HistoricalEffectiveness.INSUFFICIENT_DATA


def test_02_classify_very_effective_boundary():
    """average_delta >= 0.10 严格判定为 VERY_EFFECTIVE"""
    assert classify_effectiveness(2, 0.10) == HistoricalEffectiveness.VERY_EFFECTIVE
    assert classify_effectiveness(2, 0.1001) == HistoricalEffectiveness.VERY_EFFECTIVE
    assert classify_effectiveness(5, 0.20) == HistoricalEffectiveness.VERY_EFFECTIVE


def test_03_classify_effective_boundary():
    """0.02 <= average_delta < 0.10 严格判定为 EFFECTIVE"""
    assert classify_effectiveness(2, 0.02) == HistoricalEffectiveness.EFFECTIVE
    assert classify_effectiveness(2, 0.05) == HistoricalEffectiveness.EFFECTIVE
    assert classify_effectiveness(2, 0.0999) == HistoricalEffectiveness.EFFECTIVE


def test_04_classify_neutral_boundary():
    """-0.02 <= average_delta < 0.02 严格判定为 NEUTRAL"""
    assert classify_effectiveness(2, -0.02) == HistoricalEffectiveness.NEUTRAL
    assert classify_effectiveness(2, 0.0) == HistoricalEffectiveness.NEUTRAL
    assert classify_effectiveness(2, 0.0199) == HistoricalEffectiveness.NEUTRAL


def test_05_classify_ineffective_boundary():
    """average_delta < -0.02 严格判定为 INEFFECTIVE"""
    assert classify_effectiveness(2, -0.0201) == HistoricalEffectiveness.INEFFECTIVE
    assert classify_effectiveness(3, -0.08) == HistoricalEffectiveness.INEFFECTIVE


def test_06_adjustment_scores_contract():
    """验证分值调整常量字典完全符合契约规范"""
    assert ADJUSTMENT_SCORES[HistoricalEffectiveness.VERY_EFFECTIVE] == 2
    assert ADJUSTMENT_SCORES[HistoricalEffectiveness.EFFECTIVE] == 1
    assert ADJUSTMENT_SCORES[HistoricalEffectiveness.NEUTRAL] == 0
    assert ADJUSTMENT_SCORES[HistoricalEffectiveness.INEFFECTIVE] == -1
    assert ADJUSTMENT_SCORES[HistoricalEffectiveness.INSUFFICIENT_DATA] == 0


# =============================================================================
# 2. 只读聚合器准确性与多维隔离性
# =============================================================================

def test_07_aggregator_calculates_usage_and_deltas_correctly(temp_events_file: Path):
    """验证聚合器能准确统计有效次数、平均增量与最近一次增量"""
    records = [
        # S001 / K07 两次 example 学习
        {"student_id": "S001", "knowledge_id": "K07", "delta": 0.08, "metadata": {"resource_type": "EXAMPLE"}},
        {"student_id": "S001", "knowledge_id": "K07", "delta": 0.14, "metadata": {"resource_type": "EXAMPLE"}},
        # S001 / K07 一次 concept_card 学习 (样本不足)
        {"student_id": "S001", "knowledge_id": "K07", "delta": 0.05, "metadata": {"resource_type": "CONCEPT_CARD"}},
    ]
    with open(temp_events_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    agg = ResourceEffectivenessAggregator(events_file=temp_events_file)
    res = agg.get_resource_effectiveness("S001", "K07")

    # 验证 EXAMPLE
    ex_prof = res.get("EXAMPLE")
    assert ex_prof is not None
    assert ex_prof.usage_count == 2
    assert ex_prof.average_delta == pytest.approx(0.11, 0.0001)
    assert ex_prof.last_delta == pytest.approx(0.14, 0.0001)
    assert ex_prof.effectiveness == HistoricalEffectiveness.VERY_EFFECTIVE

    # 验证 CONCEPT_CARD
    cc_prof = res.get("CONCEPT_CARD")
    assert cc_prof is not None
    assert cc_prof.usage_count == 1
    assert cc_prof.effectiveness == HistoricalEffectiveness.INSUFFICIENT_DATA


def test_08_aggregator_student_isolation(temp_events_file: Path):
    """多学生隔离：S001 的历史数据绝不污染 S002"""
    records = [
        {"student_id": "S001", "knowledge_id": "K07", "delta": 0.15, "metadata": {"resource_type": "PRACTICE"}},
        {"student_id": "S001", "knowledge_id": "K07", "delta": 0.15, "metadata": {"resource_type": "PRACTICE"}},
    ]
    with open(temp_events_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    agg = ResourceEffectivenessAggregator(events_file=temp_events_file)

    # S001 拥有数据
    s1_res = agg.get_resource_effectiveness("S001", "K07")
    assert s1_res["PRACTICE"].effectiveness == HistoricalEffectiveness.VERY_EFFECTIVE

    # S002 查无数据，安全返回空字典
    s2_res = agg.get_resource_effectiveness("S002", "K07")
    assert "PRACTICE" not in s2_res


def test_09_aggregator_knowledge_isolation(temp_events_file: Path):
    """考点隔离：K07 的历史数据绝不混入 K08"""
    records = [
        {"student_id": "S001", "knowledge_id": "K07", "delta": 0.12, "metadata": {"resource_type": "EXAMPLE"}},
        {"student_id": "S001", "knowledge_id": "K07", "delta": 0.12, "metadata": {"resource_type": "EXAMPLE"}},
    ]
    with open(temp_events_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    agg = ResourceEffectivenessAggregator(events_file=temp_events_file)

    assert "EXAMPLE" in agg.get_resource_effectiveness("S001", "K07")
    assert "EXAMPLE" not in agg.get_resource_effectiveness("S001", "K08")


def test_10_aggregator_fault_tolerance_with_corrupted_lines(temp_events_file: Path):
    """容错性：空行、非法 JSON 与缺失 delta 安全跳过，不崩溃"""
    content = (
        "\n"
        "MALFORMED_JSON_LINE\n"
        "{\"student_id\": \"S001\"}\n"  # 缺少 knowledge_id
        "{\"student_id\": \"S001\", \"knowledge_id\": \"K07\", \"delta\": null}\n"
        "{\"student_id\": \"S001\", \"knowledge_id\": \"K07\", \"delta\": 0.05, \"metadata\": {\"resource_type\": \"EXAMPLE\"}}\n"
        "{\"student_id\": \"S001\", \"knowledge_id\": \"K07\", \"delta\": 0.05, \"metadata\": {\"resource_type\": \"EXAMPLE\"}}\n"
    )
    temp_events_file.write_text(content, encoding="utf-8")

    agg = ResourceEffectivenessAggregator(events_file=temp_events_file)
    res = agg.get_resource_effectiveness("S001", "K07")
    assert res["EXAMPLE"].usage_count == 2
    assert res["EXAMPLE"].effectiveness == HistoricalEffectiveness.EFFECTIVE


# =============================================================================
# 3. 确定性二次排序算法验证
# =============================================================================

def test_11_candidate_reordering_example_case():
    """
    黄金算例（遵循 Section 31 与 Section 8）：
    原候选次序：A (order 1) -> B (order 2) -> C (order 3)
    效果调整：A: EFFECTIVE (+1), B: VERY_EFFECTIVE (+2), C: INSUFFICIENT (0)
    最终重排：B -> A -> C
    """
    res_a = LearningResource(resource_id="res_a", knowledge_id="K01", resource_type=ResourceType.CONCEPT_CARD, title="Card A", description="Desc A")
    res_b = LearningResource(resource_id="res_b", knowledge_id="K01", resource_type=ResourceType.EXAMPLE, title="Example B", description="Desc B")
    res_c = LearningResource(resource_id="res_c", knowledge_id="K01", resource_type=ResourceType.PRACTICE, title="Quiz C", description="Desc C")

    candidates = [
        {"resource": res_a, "recommended_reason": "Reason A", "reason_category": "FOUNDATION", "suggested_order": 1},
        {"resource": res_b, "recommended_reason": "Reason B", "reason_category": "APPLICATION", "suggested_order": 2},
        {"resource": res_c, "recommended_reason": "Reason C", "reason_category": "CONSOLIDATION", "suggested_order": 3},
    ]

    profiles = {
        "CONCEPT_CARD": ResourceEffectivenessProfile(
            student_id="S001", knowledge_id="K01", resource_type="CONCEPT_CARD",
            usage_count=2, average_delta=0.04, last_delta=0.04, effectiveness=HistoricalEffectiveness.EFFECTIVE
        ),
        "EXAMPLE": ResourceEffectivenessProfile(
            student_id="S001", knowledge_id="K01", resource_type="EXAMPLE",
            usage_count=2, average_delta=0.12, last_delta=0.12, effectiveness=HistoricalEffectiveness.VERY_EFFECTIVE
        ),
        "PRACTICE": ResourceEffectivenessProfile(
            student_id="S001", knowledge_id="K01", resource_type="PRACTICE",
            usage_count=0, average_delta=0.0, last_delta=0.0, effectiveness=HistoricalEffectiveness.INSUFFICIENT_DATA
        ),
    }

    adapted = DeterministicAdaptationStrategy.apply_adaptation(candidates, profiles)

    # 验证最终顺序：B -> A -> C
    assert adapted[0]["resource"].resource_id == "res_b"
    assert adapted[0]["rank"] == 1
    assert adapted[0]["suggested_order"] == 1
    assert adapted[0]["score_adjustment"] == 2
    assert "明显的提升" in adapted[0]["why_recommended"]

    assert adapted[1]["resource"].resource_id == "res_a"
    assert adapted[1]["rank"] == 2
    assert adapted[1]["suggested_order"] == 2
    assert adapted[1]["score_adjustment"] == 1
    assert "稳定提升" in adapted[1]["why_recommended"]

    assert adapted[2]["resource"].resource_id == "res_c"
    assert adapted[2]["rank"] == 3
    assert adapted[2]["suggested_order"] == 3
    assert adapted[2]["score_adjustment"] == 0
    assert "当前学习阶段适合你的学习方式" in adapted[2]["why_recommended"]


def test_12_stable_sorting_on_tie():
    """相同分值时，稳定保持原有输入次序"""
    res_1 = LearningResource(resource_id="res_1", knowledge_id="K01", resource_type=ResourceType.CONCEPT_CARD, title="1", description="1")
    res_2 = LearningResource(resource_id="res_2", knowledge_id="K01", resource_type=ResourceType.EXAMPLE, title="2", description="2")

    candidates = [
        {"resource": res_1, "recommended_reason": "R1", "reason_category": "F", "suggested_order": 1},
        {"resource": res_2, "recommended_reason": "R2", "reason_category": "A", "suggested_order": 2},
    ]

    # 两个资源效果调整分值均为 0 (NEUTRAL)
    profiles = {
        "CONCEPT_CARD": ResourceEffectivenessProfile(
            student_id="S001", knowledge_id="K01", resource_type="CONCEPT_CARD",
            usage_count=2, average_delta=0.0, last_delta=0.0, effectiveness=HistoricalEffectiveness.NEUTRAL
        ),
        "EXAMPLE": ResourceEffectivenessProfile(
            student_id="S001", knowledge_id="K01", resource_type="EXAMPLE",
            usage_count=2, average_delta=0.0, last_delta=0.0, effectiveness=HistoricalEffectiveness.NEUTRAL
        ),
    }

    adapted = DeterministicAdaptationStrategy.apply_adaptation(candidates, profiles)
    assert adapted[0]["resource"].resource_id == "res_1"
    assert adapted[1]["resource"].resource_id == "res_2"


def test_13_insufficient_data_graceful_fallback(temp_events_file: Path):
    """无历史数据或数据不足时，原有推荐顺序完全不变 (before == after)"""
    # 模拟真实空历史
    resp = ResourceResolver.resolve(student_id="S001", knowledge_id="K01", events_file=temp_events_file)
    assert len(resp.recommendations) > 0

    # 验证全部标记为 INSUFFICIENT_DATA 且 adjustment 为 0
    for rec in resp.recommendations:
        assert rec.historical_effectiveness == HistoricalEffectiveness.INSUFFICIENT_DATA.value
        assert rec.score_adjustment == 0
        assert rec.why_recommended == "这是当前学习阶段适合你的学习方式。"


# =============================================================================
# 4. 权威事实源与核心状态零修改不变性
# =============================================================================

def test_14_zero_mutation_on_bkt_and_learning_events(temp_events_file: Path):
    """运行推荐与聚合前后，底层权威 bkt_states.json 与 learning_events.jsonl 绝对零改动"""
    bkt_file = Path("data/bkt_states.json")
    ev_file = Path("data/learning_events.jsonl")

    bkt_before = bkt_file.read_bytes() if bkt_file.exists() else b""
    ev_before = ev_file.read_bytes() if ev_file.exists() else b""

    # 执行推荐与聚合
    ResourceResolver.resolve(student_id="S001", knowledge_id="K01", events_file=temp_events_file)
    agg = ResourceEffectivenessAggregator(events_file=temp_events_file)
    agg.get_resource_effectiveness("S001", "K01")

    bkt_after = bkt_file.read_bytes() if bkt_file.exists() else b""
    ev_after = ev_file.read_bytes() if ev_file.exists() else b""

    assert bkt_before == bkt_after, "bkt_states.json 不得被修改！"
    assert ev_before == ev_after, "learning_events.jsonl 不得被修改！"


# =============================================================================
# 5. HTTP API 接口集成测试
# =============================================================================

def test_15_api_effectiveness_profile_endpoint(api_client: TestClient):
    """验证 GET /api/learning/resources/effectiveness-profile/{student_id} 端点"""
    resp = api_client.get("/api/learning/resources/effectiveness-profile/S001?knowledge_id=K07")
    assert resp.status_code == 200
    data = resp.json()
    assert data["student_id"] == "S001"
    assert data["knowledge_id"] == "K07"
    assert isinstance(data["profiles"], list)


def test_16_api_effectiveness_profile_404_on_unknown_student_or_kid(api_client: TestClient):
    """验证未知学生或未知考点抛出 404"""
    r1 = api_client.get("/api/learning/resources/effectiveness-profile/UNKNOWN_999?knowledge_id=K01")
    assert r1.status_code == 404

    r2 = api_client.get("/api/learning/resources/effectiveness-profile/S001?knowledge_id=K99")
    assert r2.status_code == 404


def test_17_api_recommended_resources_includes_sprint9e_fields(api_client: TestClient):
    """验证 GET /api/learning/resources/recommended/{student_id} 返回载荷携带 Sprint 9-E 字段"""
    resp = api_client.get("/api/learning/resources/recommended/S001?knowledge_id=K01")
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0

    first_rec = data["recommendations"][0]
    assert "historical_effectiveness" in first_rec
    assert "why_recommended" in first_rec
    assert "score_adjustment" in first_rec
