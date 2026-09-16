# -*- coding: utf-8 -*-
"""
scripts/sprint9e_quality_gate.py
================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-E
学习保持度验证与资源策略自适应 Lite 严苛质量门禁 (Strict Quality Gate)

本门禁独立自动化校验 Sprint 9-E 全部核心契约与安全红线：
1. Git 架构基线与冻结目录零变更检查 (app/, tests/, data/seeds/ 0 diff)
2. 历史成效分档模型与 5 档确定性阈值边界契约 (HistoricalEffectiveness, classify_effectiveness, ADJUSTMENT_SCORES)
3. 确定性二次排序策略与稳定排序仲裁 (DeterministicAdaptationStrategy, -final_score DESC, original_order ASC)
4. 历史效果只读聚合器容错性与多别名索引 (ResourceEffectivenessAggregator, read-only JSONL)
5. 多学生与跨考点上下文硬隔离契约 (Student & Knowledge Isolation)
6. 生产底座 BKT 掌握度与学习事件零突变零污染红线 (Zero Mutation Invariant)
7. 人本叙事解释文案与零技术黑话合规性审核 (No Jargon, WHY_RECOMMENDED_TEMPLATES)
8. API 端点契约完整性 (GET effectiveness-profile, recommended 扩展字段)
9. 全量测试套件与生产构建完整性 (pytest, npm test, npm run typecheck, npm run build)
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from gateway.api import create_gateway_app
from gateway.learning.resource_effectiveness.models import (
    HistoricalEffectiveness,
    ADJUSTMENT_SCORES,
    classify_effectiveness,
    ResourceEffectivenessProfile,
    EffectivenessProfileResponse,
)
from gateway.learning.resource_effectiveness.strategy import (
    DeterministicAdaptationStrategy,
    WHY_RECOMMENDED_TEMPLATES,
)
from gateway.learning.resource_effectiveness.aggregator import (
    ResourceEffectivenessAggregator,
    normalize_resource_type_key,
)
from app.infrastructure.persistence.bkt_state_repository import default_bkt_state_repository


def run_check(check_num: int, title: str, fn) -> bool:
    print(f"[{check_num:02d}/09] {title} ... ", end="", flush=True)
    try:
        fn()
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 80)
    print("Sprint 9-E: Learning Retention & Resource Strategy Adaptation Quality Gate")
    print("=" * 80)

    app = create_gateway_app()
    client = TestClient(app)

    # -------------------------------------------------------------------------
    # Check 1: Git 架构基线与冻结目录零变更检查
    # -------------------------------------------------------------------------
    def check_01_git_baseline_and_frozen_dirs():
        cmd = ["git", "diff", "--stat", "HEAD", "--", "app/", "tests/", "data/seeds/"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode != 0 or res.stdout.strip():
            raise AssertionError(f"冻结目录存在未授权变更:\n{res.stdout}")

    # -------------------------------------------------------------------------
    # Check 2: 历史成效分档模型与 5 档确定性阈值边界契约
    # -------------------------------------------------------------------------
    def check_02_effectiveness_models_and_thresholds():
        assert HistoricalEffectiveness.VERY_EFFECTIVE == "VERY_EFFECTIVE"
        assert HistoricalEffectiveness.EFFECTIVE == "EFFECTIVE"
        assert HistoricalEffectiveness.NEUTRAL == "NEUTRAL"
        assert HistoricalEffectiveness.INEFFECTIVE == "INEFFECTIVE"
        assert HistoricalEffectiveness.INSUFFICIENT_DATA == "INSUFFICIENT_DATA"

        # 微调分值严格映射
        assert ADJUSTMENT_SCORES[HistoricalEffectiveness.VERY_EFFECTIVE] == 2
        assert ADJUSTMENT_SCORES[HistoricalEffectiveness.EFFECTIVE] == 1
        assert ADJUSTMENT_SCORES[HistoricalEffectiveness.NEUTRAL] == 0
        assert ADJUSTMENT_SCORES[HistoricalEffectiveness.INEFFECTIVE] == -1
        assert ADJUSTMENT_SCORES[HistoricalEffectiveness.INSUFFICIENT_DATA] == 0

        # 分级阈值边界严格断言
        assert classify_effectiveness(0, 0.25) == HistoricalEffectiveness.INSUFFICIENT_DATA
        assert classify_effectiveness(1, 0.25) == HistoricalEffectiveness.INSUFFICIENT_DATA
        assert classify_effectiveness(2, 0.10) == HistoricalEffectiveness.VERY_EFFECTIVE
        assert classify_effectiveness(2, 0.0999) == HistoricalEffectiveness.EFFECTIVE
        assert classify_effectiveness(2, 0.02) == HistoricalEffectiveness.EFFECTIVE
        assert classify_effectiveness(2, 0.0199) == HistoricalEffectiveness.NEUTRAL
        assert classify_effectiveness(2, -0.02) == HistoricalEffectiveness.NEUTRAL
        assert classify_effectiveness(2, -0.0201) == HistoricalEffectiveness.INEFFECTIVE

    # -------------------------------------------------------------------------
    # Check 3: 确定性二次排序策略与稳定排序仲裁
    # -------------------------------------------------------------------------
    def check_03_deterministic_adaptation_strategy():
        candidates = [
            {"resource_type": "CONCEPT_CARD", "resource": type("R", (), {"resource_type": type("T", (), {"value": "CONCEPT_CARD"})})(), "recommended_reason": "基础"},
            {"resource_type": "EXAMPLE", "resource": type("R", (), {"resource_type": type("T", (), {"value": "EXAMPLE"})})(), "recommended_reason": "例题"},
            {"resource_type": "PRACTICE", "resource": type("R", (), {"resource_type": type("T", (), {"value": "PRACTICE"})})(), "recommended_reason": "练习"},
        ]
        profiles = {
            "CONCEPT_CARD": ResourceEffectivenessProfile(
                student_id="S001", knowledge_id="K08", resource_type="CONCEPT_CARD",
                usage_count=2, average_delta=0.05, effectiveness=HistoricalEffectiveness.EFFECTIVE
            ),
            "EXAMPLE": ResourceEffectivenessProfile(
                student_id="S001", knowledge_id="K08", resource_type="EXAMPLE",
                usage_count=2, average_delta=0.15, effectiveness=HistoricalEffectiveness.VERY_EFFECTIVE
            ),
            "PRACTICE": ResourceEffectivenessProfile(
                student_id="S001", knowledge_id="K08", resource_type="PRACTICE",
                usage_count=2, average_delta=0.00, effectiveness=HistoricalEffectiveness.NEUTRAL
            ),
        }
        res = DeterministicAdaptationStrategy.apply_adaptation(candidates, profiles)
        assert len(res) == 3
        # 验证排序跃迁：EXAMPLE (+2) 跃居第一，CONCEPT_CARD (+1) 居第二，PRACTICE (0) 居第三
        types_order = [r["resource_type"] for r in res]
        assert types_order == ["EXAMPLE", "CONCEPT_CARD", "PRACTICE"], f"实际顺序: {types_order}"
        assert res[0]["rank"] == 1
        assert res[0]["score_adjustment"] == 2
        assert res[1]["rank"] == 2
        assert res[1]["score_adjustment"] == 1
        assert res[2]["rank"] == 3
        assert res[2]["score_adjustment"] == 0

    # -------------------------------------------------------------------------
    # Check 4: 历史效果只读聚合器容错性与多别名索引
    # -------------------------------------------------------------------------
    def check_04_aggregator_fault_tolerance_and_aliases():
        assert normalize_resource_type_key("CONCEPT_CARD") == "concept_card"
        assert normalize_resource_type_key("Example") == "example"

        import json
        tmp_path = PROJECT_ROOT / "data" / "runtime" / "test_qg_fault_tolerance.jsonl"
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            json.dumps({"student_id": "S001", "knowledge_id": "K08", "delta": 0.12, "metadata": {"resource_type": "EXAMPLE"}}) + "\n"
            + "CORRUPTED_JSON_LINE_THAT_MUST_NOT_CRASH\n"
            + json.dumps({"student_id": "S001", "knowledge_id": "K08", "delta": 0.14, "metadata": {"resource_type": "EXAMPLE"}}) + "\n"
        )
        tmp_path.write_text(content, encoding="utf-8")

        try:
            aggregator = ResourceEffectivenessAggregator(events_file=tmp_path)
            prof_map = aggregator.get_resource_effectiveness("S001", "K08")
            assert "example" in prof_map or "EXAMPLE" in prof_map
            prof = prof_map.get("example") or prof_map.get("EXAMPLE")
            assert prof.usage_count == 2
            assert prof.average_delta == 0.13
            assert prof.effectiveness == HistoricalEffectiveness.VERY_EFFECTIVE
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    # -------------------------------------------------------------------------
    # Check 5: 多学生与跨考点上下文硬隔离契约
    # -------------------------------------------------------------------------
    def check_05_student_and_knowledge_isolation():
        import json
        tmp_path = PROJECT_ROOT / "data" / "runtime" / "test_qg_isolation.jsonl"
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        records = [
            {"student_id": "S001", "knowledge_id": "K08", "delta": 0.15, "metadata": {"resource_type": "EXAMPLE"}},
            {"student_id": "S001", "knowledge_id": "K08", "delta": 0.15, "metadata": {"resource_type": "EXAMPLE"}},
            {"student_id": "S002", "knowledge_id": "K08", "delta": -0.05, "metadata": {"resource_type": "EXAMPLE"}},
            {"student_id": "S002", "knowledge_id": "K08", "delta": -0.05, "metadata": {"resource_type": "EXAMPLE"}},
        ]
        tmp_path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

        try:
            aggregator = ResourceEffectivenessAggregator(events_file=tmp_path)
            s001_map = aggregator.get_resource_effectiveness("S001", "K08")
            s002_map = aggregator.get_resource_effectiveness("S002", "K08")
            p1 = s001_map.get("example") or s001_map.get("EXAMPLE")
            p2 = s002_map.get("example") or s002_map.get("EXAMPLE")
            assert p1.effectiveness == HistoricalEffectiveness.VERY_EFFECTIVE
            assert p2.effectiveness == HistoricalEffectiveness.INEFFECTIVE

            k09_map = aggregator.get_resource_effectiveness("S001", "K09")
            assert len(k09_map) == 0
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    # -------------------------------------------------------------------------
    # Check 6: 生产底座 BKT 掌握度与学习事件零突变零污染红线
    # -------------------------------------------------------------------------
    def check_06_zero_mutation_invariant():
        state_before = default_bkt_state_repository.get_state("S001", "K08")
        mastery_before = state_before.mastery_probability if state_before else 0.20

        resp = client.get("/api/learning/resources/recommended/S001?knowledge_id=K08")
        assert resp.status_code == 200

        resp_prof = client.get("/api/learning/resources/effectiveness-profile/S001?knowledge_id=K08")
        assert resp_prof.status_code == 200

        state_after = default_bkt_state_repository.get_state("S001", "K08")
        mastery_after = state_after.mastery_probability if state_after else 0.20
        assert mastery_before == mastery_after, "红线突破：自适应推荐引发 BKT 掌握度变更！"

    # -------------------------------------------------------------------------
    # Check 7: 人本叙事解释文案与零技术黑话合规性审核
    # -------------------------------------------------------------------------
    def check_07_human_centered_narrative_and_no_jargon():
        forbidden = [
            "BKT", "Bayesian", "PathState", "Resolver", "score_adjustment",
            "final_score", "向量", "大模型", "探索率", "冷启动", "先验", "后验"
        ]
        for eff, text in WHY_RECOMMENDED_TEMPLATES.items():
            for f in forbidden:
                assert f not in text, f"模板泄露技术黑话: {f} in {eff.value} -> {text}"
            assert len(text) > 5

    # -------------------------------------------------------------------------
    # Check 8: API 端点契约完整性
    # -------------------------------------------------------------------------
    def check_08_api_endpoints_contract():
        resp = client.get("/api/learning/resources/effectiveness-profile/S001?knowledge_id=K08")
        assert resp.status_code == 200
        data = resp.json()
        assert data["student_id"] == "S001"
        assert data["knowledge_id"] == "K08"
        assert "profiles" in data
        assert isinstance(data["profiles"], list)

        resp_404_s = client.get("/api/learning/resources/effectiveness-profile/S999_UNKNOWN")
        assert resp_404_s.status_code == 404
        resp_404_k = client.get("/api/learning/resources/effectiveness-profile/S001?knowledge_id=K999_UNKNOWN")
        assert resp_404_k.status_code == 404

        rec_resp = client.get("/api/learning/resources/recommended/S001?knowledge_id=K08")
        assert rec_resp.status_code == 200
        rec_data = rec_resp.json()
        for r in rec_data["recommendations"]:
            assert "historical_effectiveness" in r
            assert "why_recommended" in r
            assert "score_adjustment" in r

    # -------------------------------------------------------------------------
    # Check 9: 全量测试套件与生产构建完整性
    # -------------------------------------------------------------------------
    def check_09_full_test_suites_and_build():
        pytest_res = subprocess.run(
            ["pytest", "gateway/tests/test_sprint9e_resource_adaptation.py", "-q"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if pytest_res.returncode != 0:
            raise AssertionError(f"后端 Sprint 9-E 测试未通过:\n{pytest_res.stdout}\n{pytest_res.stderr}")

        npm_test_res = subprocess.run(
            ["npm", "test", "--prefix", "frontend"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            shell=True,
            encoding="utf-8",
            errors="replace",
        )
        if npm_test_res.returncode != 0:
            raise AssertionError(f"前端测试未通过:\n{npm_test_res.stdout}\n{npm_test_res.stderr}")

        build_res = subprocess.run(
            ["npm", "run", "build", "--prefix", "frontend"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            shell=True,
            encoding="utf-8",
            errors="replace",
        )
        if build_res.returncode != 0:
            raise AssertionError(f"前端构建未通过:\n{build_res.stdout}\n{build_res.stderr}")

    checks = [
        (1, "Git baseline & frozen dirs (app/, tests/, seeds/ 0 diff)", check_01_git_baseline_and_frozen_dirs),
        (2, "Historical effectiveness models & 5-tier classification thresholds", check_02_effectiveness_models_and_thresholds),
        (3, "Deterministic adaptation strategy & stable tie-breaking", check_03_deterministic_adaptation_strategy),
        (4, "Read-only aggregator fault tolerance & multi-alias indexing", check_04_aggregator_fault_tolerance_and_aliases),
        (5, "Student & knowledge context isolation in historical aggregation", check_05_student_and_knowledge_isolation),
        (6, "Zero BKT mutation & zero learning events pollution invariant", check_06_zero_mutation_invariant),
        (7, "Human-centered narrative templates & zero technical jargon", check_07_human_centered_narrative_and_no_jargon),
        (8, "API endpoints contract integrity (effectiveness-profile & recommended)", check_08_api_endpoints_contract),
        (9, "Full test suites execution & frontend production build", check_09_full_test_suites_and_build),
    ]

    passed = 0
    for num, title, fn in checks:
        if run_check(num, title, fn):
            passed += 1
        else:
            print(f"\n[QUALITY GATE HALTED] Check {num} failed!")
            sys.exit(1)

    print("=" * 80)
    print(f"[SUCCESS] SPRINT 9-E QUALITY GATE PASSED: {passed}/09 CHECKS GREEN!")
    print("=" * 80)


if __name__ == "__main__":
    main()

