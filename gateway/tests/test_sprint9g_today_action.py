# -*- coding: utf-8 -*-
"""
gateway.tests.test_sprint9g_today_action
========================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-G
今日学习行动聚合 Lite 核心单元与集成测试 (12 Targeted Tests)

覆盖范围：
1. NEEDS_REINFORCEMENT 优先级最高
2. DUE_FOR_REVIEW 优先于 IN_PROGRESS
3. IN_PROGRESS 优先于 PRACTICE
4. PRACTICE 靶向微练兜底
5. VIEW_PROGRESS 阶段考点全达标
6. NONE 空状态静默兜底
7. 多 Retention 候选考点按 knowledge_id 升序平局仲裁
8. 多学生隔离性验证 (S001 vs S002)
9. 非法学生 ID 严格 404
10. 固定时间基准下 50 次连续调用确定性幂等
11. 纯只读性与零持久化污染 (Zero Mutation)
12. 保持度建议动作向今日行动正确透传与文案合规 (No Jargon)
"""

import copy
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from gateway.api import app
from gateway.learning.resources.models import (
    LearningResource,
    RecommendedResourcesResponse,
    ResourceRecommendation,
    ResourceType,
)
from gateway.learning.retention.models import RetentionProfile, RetentionStatus
from gateway.learning.today import (
    TodayActionResponse,
    TodayActionType,
    TodayLearningAction,
    TodayActionResolver,
    default_today_action_resolver,
)


def _get_file_hash(path: Path) -> str:
    """计算文件 SHA-256 哈希用于零篡改验证"""
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


class TestSprint9GTodayAction:
    """Sprint 9-G 今日学习行动聚合完整测试套件"""

    def test_01_needs_reinforcement_highest_priority(self):
        """1. NEEDS_REINFORCEMENT 优先于所有其他动作状态"""
        mock_retention = MagicMock()
        mock_retention.analyze.side_effect = lambda sid, kid, now=None: RetentionProfile(
            student_id=sid,
            knowledge_id=kid,
            retention_status=RetentionStatus.NEEDS_REINFORCEMENT if kid == "K03" else RetentionStatus.DUE_FOR_REVIEW,
            should_review=True,
            suggested_action="REVIEW_CONCEPT",
            current_mastery=0.45,
            days_since_learning=1,
        )

        resolver = TodayActionResolver(
            retention_analyzer=mock_retention,
        )
        res = resolver.resolve("S001", candidate_knowledge_ids=["K01", "K02", "K03"])
        assert res.student_id == "S001"
        assert res.action.action_type == TodayActionType.REVIEW_RETENTION
        assert res.action.knowledge_id == "K03"
        assert res.action.title == "建议再巩固一下"
        assert res.action.cta_label == "重新学习"
        assert "不够稳定" in res.action.description
        assert res.action.priority_reason == "已有考点复习未稳固，需针对性巩固"

    def test_02_due_for_review_priority_over_in_progress(self):
        """2. DUE_FOR_REVIEW 优先于 IN_PROGRESS 路径学习"""
        mock_retention = MagicMock()
        mock_retention.analyze.side_effect = lambda sid, kid, now=None: RetentionProfile(
            student_id=sid,
            knowledge_id=kid,
            retention_status=RetentionStatus.DUE_FOR_REVIEW if kid == "K02" else RetentionStatus.NOT_DUE,
            should_review=(kid == "K02"),
            suggested_action="RETAKE_QUIZ",
            current_mastery=0.75,
            days_since_learning=3,
        )

        mock_path_state = MagicMock()
        mock_path_state.get_all_path_states.return_value = {"K05": "IN_PROGRESS"}

        resolver = TodayActionResolver(
            retention_analyzer=mock_retention,
            path_state_service=mock_path_state,
        )
        res = resolver.resolve("S001", candidate_knowledge_ids=["K01", "K02"])
        assert res.action.action_type == TodayActionType.REVIEW_RETENTION
        assert res.action.knowledge_id == "K02"
        assert res.action.title == "该复习一下了"
        assert res.action.cta_label == "开始快速复测"

    def test_03_in_progress_priority_over_practice(self):
        """3. IN_PROGRESS 路径学习优先于 PRACTICE 练习"""
        mock_retention = MagicMock()
        mock_retention.analyze.side_effect = lambda sid, kid, now=None: RetentionProfile(
            student_id=sid,
            knowledge_id=kid,
            retention_status=RetentionStatus.NOT_DUE,
            should_review=False,
            suggested_action=None,
        )

        mock_path_state = MagicMock()
        mock_path_state.get_all_path_states.return_value = {"K04": "IN_PROGRESS"}

        mock_resource = MagicMock()
        mock_resource.resolve.return_value = RecommendedResourcesResponse(
            student_id="S001",
            knowledge_id="K01",
            mastery=0.5,
            case_code="CASE_A_WEAK_FOUNDATION",
            reason_summary="阶段导引说明",
            recommendations=[
                ResourceRecommendation(
                    resource=LearningResource(
                        resource_id="res_practice",
                        knowledge_id="K01",
                        resource_type=ResourceType.PRACTICE,
                        title="练习",
                        description="desc",
                        difficulty=0.5,
                    ),
                    rank=1,
                    recommended_reason="reason",
                    reason_category="TARGETED_PRACTICE",
                    suggested_order=1,
                )
            ],
        )

        resolver = TodayActionResolver(
            retention_analyzer=mock_retention,
            path_state_service=mock_path_state,
            resource_resolver=mock_resource,
        )
        res = resolver.resolve("S001", candidate_knowledge_ids=["K01", "K02"])
        assert res.action.action_type == TodayActionType.CONTINUE_LEARNING
        assert res.action.knowledge_id == "K04"
        assert "继续学习" in res.action.title
        assert res.action.cta_label == "开始学习"
        assert res.action.priority_reason == "当前学习路径中的首要未完成任务"

    def test_04_practice_fallback(self):
        """4. 无需复习且无进行中路径任务时，回退至 PRACTICE 靶向微练"""
        mock_retention = MagicMock()
        mock_retention.analyze.side_effect = lambda sid, kid, now=None: RetentionProfile(
            student_id=sid,
            knowledge_id=kid,
            retention_status=RetentionStatus.NOT_DUE,
            should_review=False,
            suggested_action=None,
        )

        mock_path_state = MagicMock()
        mock_path_state.get_all_path_states.return_value = {}

        mock_student_service = MagicMock()
        mock_student_service.get_student_profile.return_value = {"student": {"student_name": "测试"}}
        mock_student_service.get_student_dashboard.return_value = {
            "learning_path": {"learning_path": []}
        }

        mock_resource = MagicMock()
        mock_resource.resolve.return_value = RecommendedResourcesResponse(
            student_id="S001",
            knowledge_id="K01",
            mastery=0.5,
            case_code="CASE_A_WEAK_FOUNDATION",
            reason_summary="阶段导引说明",
            recommendations=[
                ResourceRecommendation(
                    resource=LearningResource(
                        resource_id="res_practice_1",
                        knowledge_id="K01",
                        resource_type=ResourceType.PRACTICE,
                        title="弹性概念基础习题",
                        description="desc",
                        difficulty=0.5,
                    ),
                    rank=1,
                    recommended_reason="保持练习节奏",
                    reason_category="TARGETED_PRACTICE",
                    suggested_order=1,
                )
            ],
        )

        resolver = TodayActionResolver(
            retention_analyzer=mock_retention,
            path_state_service=mock_path_state,
            resource_resolver=mock_resource,
            student_service=mock_student_service,
        )
        res = resolver.resolve("S001", candidate_knowledge_ids=["K01"])
        assert res.action.action_type == TodayActionType.PRACTICE
        assert res.action.knowledge_id == "K01"
        assert res.action.title == "做一道小练习"
        assert res.action.cta_label == "开始练习"
        assert res.action.priority_reason == "推荐靶向微练保持学习节奏"

    def test_05_view_progress_when_all_completed(self):
        """5. 当前学习路径考点全部达标完成时，呈现 VIEW_PROGRESS"""
        mock_retention = MagicMock()
        mock_retention.analyze.side_effect = lambda sid, kid, now=None: RetentionProfile(
            student_id=sid,
            knowledge_id=kid,
            retention_status=RetentionStatus.NOT_DUE,
            should_review=False,
            suggested_action=None,
        )

        mock_path_state = MagicMock()
        mock_path_state.get_all_path_states.return_value = {
            "K01": "COMPLETED",
            "K02": "COMPLETED",
        }

        mock_student_service = MagicMock()
        mock_student_service.get_student_profile.return_value = {"student": {"student_name": "测试"}}
        mock_student_service.get_student_dashboard.return_value = {
            "learning_path": {
                "learning_path": [
                    {"knowledge_id": "K01"},
                    {"knowledge_id": "K02"},
                ]
            }
        }

        mock_resource = MagicMock()
        mock_resource.resolve.return_value = RecommendedResourcesResponse(
            student_id="S001",
            knowledge_id="K01",
            mastery=0.9,
            case_code="CASE_D_TERMINAL_CONSOLIDATE",
            reason_summary="阶段导引说明",
            recommendations=[],
        )

        resolver = TodayActionResolver(
            retention_analyzer=mock_retention,
            path_state_service=mock_path_state,
            resource_resolver=mock_resource,
            student_service=mock_student_service,
        )
        res = resolver.resolve("S001", candidate_knowledge_ids=["K01", "K02"])
        assert res.action.action_type == TodayActionType.VIEW_PROGRESS
        assert res.action.title == "看看最近的学习进展"
        assert res.action.cta_label == "查看学情"
        assert res.action.priority_reason == "当前所有阶段任务已全部达标"
        assert res.action.knowledge_id is None

    def test_06_none_action_silent_fallback(self):
        """6. 所有条件均不满足时，返回 NONE 动作契约"""
        mock_retention = MagicMock()
        mock_retention.analyze.side_effect = lambda sid, kid, now=None: RetentionProfile(
            student_id=sid,
            knowledge_id=kid,
            retention_status=RetentionStatus.NOT_DUE,
            should_review=False,
            suggested_action=None,
        )

        mock_path_state = MagicMock()
        mock_path_state.get_all_path_states.return_value = {}

        mock_student_service = MagicMock()
        mock_student_service.get_student_profile.return_value = {"student": {"student_name": "测试"}}
        mock_student_service.get_student_dashboard.return_value = {
            "learning_path": {"learning_path": []}
        }

        mock_resource = MagicMock()
        mock_resource.resolve.return_value = RecommendedResourcesResponse(
            student_id="S001",
            knowledge_id="K01",
            mastery=0.5,
            case_code="CASE_A_WEAK_FOUNDATION",
            reason_summary="阶段导引说明",
            recommendations=[],
        )

        resolver = TodayActionResolver(
            retention_analyzer=mock_retention,
            path_state_service=mock_path_state,
            resource_resolver=mock_resource,
            student_service=mock_student_service,
        )
        res = resolver.resolve("S001", candidate_knowledge_ids=["K01"])
        assert res.action.action_type == TodayActionType.NONE
        assert res.action.title == ""
        assert res.action.cta_label == ""
        assert res.action.knowledge_id is None

    def test_07_deterministic_tie_break_by_knowledge_id_asc(self):
        """7. 多个考点处于相同保持度状态时，严格按 knowledge_id 升序仲裁"""
        mock_retention = MagicMock()
        # K05, K02, K08 同时需要强化
        mock_retention.analyze.side_effect = lambda sid, kid, now=None: RetentionProfile(
            student_id=sid,
            knowledge_id=kid,
            retention_status=(
                RetentionStatus.NEEDS_REINFORCEMENT
                if kid in ("K05", "K02", "K08")
                else RetentionStatus.NOT_DUE
            ),
            should_review=(kid in ("K05", "K02", "K08")),
            suggested_action="REVIEW_CONCEPT",
        )

        resolver = TodayActionResolver(
            retention_analyzer=mock_retention,
        )
        # 故意乱序传入
        res = resolver.resolve("S001", candidate_knowledge_ids=["K08", "K05", "K02"])
        assert res.action.action_type == TodayActionType.REVIEW_RETENTION
        # 必须选择升序最小的 K02
        assert res.action.knowledge_id == "K02"

    def test_08_multi_student_isolation(self):
        """8. 多学生状态物理隔离，S001 与 S002 产生不同且独立的今日行动"""
        client = TestClient(app)

        resp1 = client.get("/api/learning/today/S001")
        assert resp1.status_code == 200
        data1 = resp1.json()

        resp2 = client.get("/api/learning/today/S002")
        assert resp2.status_code == 200
        data2 = resp2.json()

        assert data1["student_id"] == "S001"
        assert data2["student_id"] == "S002"
        # S001 有学习历史 (REVIEW_RETENTION)，S002 无历史 (PRACTICE)
        assert data1["action"]["action_type"] == "REVIEW_RETENTION"
        assert data2["action"]["action_type"] == "PRACTICE"

    def test_09_invalid_student_404(self):
        """9. 不存在的非法学生编号严格返回 404 Not Found"""
        client = TestClient(app)
        resp = client.get("/api/learning/today/NON_EXISTENT_999")
        assert resp.status_code == 404
        assert "找不到学生档案" in resp.json()["detail"]

    def test_10_deterministic_reproducibility_under_fixed_now(self):
        """10. 固定时间基准下，同一学生连续 50 次解析产出完全一致的结果"""
        fixed_now = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)
        first_result = default_today_action_resolver.resolve("S001", now=fixed_now)
        first_dict = first_result.model_dump()

        for _ in range(50):
            repeated_result = default_today_action_resolver.resolve("S001", now=fixed_now)
            assert repeated_result.model_dump() == first_dict

    def test_11_read_only_zero_mutation_invariants(self):
        """11. 纯只读性验证：解析过程中绝对禁止修改 BKT 状态与学习事件日志"""
        bkt_path = settings.BKT_STATES_FILE
        events_path = settings.LEARNING_EVENTS_FILE

        hash_bkt_before = _get_file_hash(bkt_path)
        hash_events_before = _get_file_hash(events_path)

        client = TestClient(app)
        for sid in ("S001", "S002"):
            resp = client.get(f"/api/learning/today/{sid}")
            assert resp.status_code == 200

        hash_bkt_after = _get_file_hash(bkt_path)
        hash_events_after = _get_file_hash(events_path)

        assert hash_bkt_after == hash_bkt_before, "BKT 状态文件被非法修改！"
        assert hash_events_after == hash_events_before, "学习事件文件被非法修改！"

    def test_12_no_jargon_in_user_facing_fields(self):
        """12. 用户可见文案中绝对禁止技术黑话 (BKT, P(L), Bayesian, score, algorithm 等)"""
        client = TestClient(app)
        for sid in ("S001", "S002"):
            resp = client.get(f"/api/learning/today/{sid}")
            action = resp.json()["action"]

            text_corpus = f"{action['title']} {action['description']} {action['cta_label']} {action['priority_reason']}"
            forbidden_jargons = [
                "bkt",
                "p(l)",
                "bayesian",
                "贝叶斯",
                "mastery",
                "pathstate",
                "dynamicpathgenerator",
                "score",
                "分值",
                "算法",
                "retention analyzer",
                "effectiveness",
            ]
            text_lower = text_corpus.lower()
            for jargon in forbidden_jargons:
                assert jargon not in text_lower, f"行动文案中包含违禁黑话 '{jargon}': {text_corpus}"
