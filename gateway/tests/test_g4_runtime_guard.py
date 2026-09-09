# -*- coding: utf-8 -*-
"""
gateway.tests.test_g4_runtime_guard
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G4: Runtime Safety Guard Test Suite (G4-R1 ~ G4-R8)
"""

import copy
import pytest
from pydantic import ValidationError

from gateway.evaluation.calibration.dataset import load_calibration_dataset
from gateway.evaluation.judge.runtime import JudgeRuntimePolicy
from gateway.evaluation.judge.runtime_guard import JudgeRuntimeGuard
from gateway.models import LearningPromptContext


@pytest.fixture
def sample_context():
    cases = load_calibration_dataset()
    return cases[0].context


class TestG4RuntimeGuard:
    def test_g4_r1_disabled_by_default(self):
        """G4-R1: 默认运行时策略为关闭状态"""
        pol = JudgeRuntimePolicy()
        assert pol.enabled is False
        assert pol.shadow_only is True
        assert pol.allow_production_decision is False

    def test_g4_r2_production_decision_forbidden(self):
        """G4-R2: 任何尝试开启 allow_production_decision 强制抛出异常阻断"""
        with pytest.raises(ValidationError) as exc:
            JudgeRuntimePolicy(allow_production_decision=True)
        assert "JUDGE_PRODUCTION_DECISION_FORBIDDEN" in str(exc.value)

    def test_g4_r3_pii_scrub(self, sample_context):
        """G4-R3: 自动清洗学生身份、电话号码与邮箱"""
        guard = JudgeRuntimeGuard()
        ctx = copy.deepcopy(sample_context)
        ctx.user_question = "我叫李四，学号S999，电话13912345678，邮箱lisi@pku.edu.cn，请答疑。"

        proj = guard.scrub_context_for_pii_and_secrets(ctx)

        assert "13912345678" not in proj.current_question
        assert "[REDACTED_PHONE]" in proj.current_question
        assert "lisi@pku.edu.cn" not in proj.current_question
        assert "[REDACTED_EMAIL]" in proj.current_question
        assert not hasattr(proj, "student_id")
        assert not hasattr(proj, "student_name")

    def test_g4_r4_secret_scrub(self, sample_context):
        """G4-R4: 自动清洗 API Key、Bearer Token 与密码"""
        guard = JudgeRuntimeGuard()
        ctx = copy.deepcopy(sample_context)
        ctx.user_question = "测试 token: Bearer eyJhbGciOi... 和密钥 sk-live998877665544332211 以及 password: AdminPass123"

        proj = guard.scrub_context_for_pii_and_secrets(ctx)

        assert "sk-live998877665544332211" not in proj.current_question
        assert "[REDACTED_KEY]" in proj.current_question
        assert "[REDACTED_BEARER]" in proj.current_question
        assert "[REDACTED_PASS]" in proj.current_question

    def test_g4_r5_timeout_bounded(self):
        """G4-R5: 超时时间必须在 [0.1, 30.0] 闭区间内"""
        with pytest.raises(ValidationError):
            JudgeRuntimePolicy(timeout_seconds=0.05)  # < 0.1

        with pytest.raises(ValidationError):
            JudgeRuntimePolicy(timeout_seconds=60.0)  # > 30.0

        pol = JudgeRuntimePolicy(timeout_seconds=10.0)
        assert pol.timeout_seconds == 10.0

    def test_g4_r6_rate_limit_bounded(self):
        """G4-R6: 频控配额必须为正数"""
        with pytest.raises(ValidationError):
            JudgeRuntimePolicy(max_requests_per_minute=0)

        with pytest.raises(ValidationError):
            JudgeRuntimePolicy(max_daily_requests=-1)

    def test_g4_r7_state_immutability(self, sample_context):
        """G4-R7: 状态发生突变时抛出 SHADOW_STATE_MUTATION"""
        guard = JudgeRuntimeGuard()
        snap_before = copy.deepcopy(sample_context.model_dump())
        snap_after = copy.deepcopy(snap_before)
        snap_after["system_facts"]["current_mastery_percent"] = 99.9  # 模拟突变

        with pytest.raises(RuntimeError) as exc:
            guard.verify_state_isolation(snap_before, snap_after)
        assert "SHADOW_STATE_MUTATION" in str(exc.value)

    def test_g4_r8_invalid_configuration_rejected(self):
        """G4-R8: 非法额外字段或非法属性直接拒绝"""
        guard = JudgeRuntimeGuard()
        with pytest.raises(ValidationError):
            JudgeRuntimePolicy(shadow_only=False)  # shadow_only 必须为 True

        with pytest.raises(ValidationError):
            JudgeRuntimePolicy(injected_secret="hack")  # extra="forbid"
