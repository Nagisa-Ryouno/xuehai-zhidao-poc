# -*- coding: utf-8 -*-
"""
tests.architecture.test_domain_contracts
Invariant 09: 核心领域数学模型与决策契约不可篡改性测试

验证规则：
1. BKT 认知诊断核心超参数物理冻结：
   p_init = 0.20, p_transit = 0.10, p_guess = 0.20, p_slip = 0.10
2. BKT 掌握度更新数学轨迹黄金断言 (Golden Trajectory):
   - 初始: 0.2000
   - 第 1 次作答错误 (Wrong): 严格计算为 0.1273 (四舍五入 4 位定点)
   - 第 2 次作答正确 (Correct): 严格计算为 0.4566 (四舍五入 4 位定点)
   - 第 3 次作答正确 (Correct): 严格计算为 0.8118 (四舍五入 4 位定点)
3. 决策流转核心 (Decision Core):
   - 严格且仅有 5 组法定合法配对 LEGAL_DECISION_PAIRS
   - 非法配对显式抛出 ValueError
   - 规范化业务载荷 (CanonicalBusinessPayload) 的 to_canonical_json() 必须 100% 确定性并保证 SHA-256 跨调用字节级严格一致
"""

import hashlib
import unittest
from decimal import Decimal

from app.core.constants import DEFAULT_BKT_PARAMS, PathState
from app.domain.bkt import (
    BKTParameters,
    apply_attempt,
    create_initial_state,
)
from app.domain.path_replanning import (
    LEGAL_DECISION_PAIRS,
    CanonicalBusinessPayload,
    PathAction,
    ReplanningReasonCode,
    format_canonical_mastery,
    validate_decision_pair,
)


class TestDomainContracts(unittest.TestCase):
    """核心领域数学模型与确定性契约测试"""

    def test_bkt_hyperparameters_strictly_frozen(self):
        """验证 BKT 超参数严格冻结，防止任何未授权篡改"""
        # 1. 验证 app.core.constants 中的全局常数
        self.assertEqual(DEFAULT_BKT_PARAMS.p_init, 0.20)
        self.assertEqual(DEFAULT_BKT_PARAMS.p_transit, 0.10)
        self.assertEqual(DEFAULT_BKT_PARAMS.p_guess, 0.20)
        self.assertEqual(DEFAULT_BKT_PARAMS.p_slip, 0.10)

        # 2. 验证 app.domain.bkt 中的领域模型与默认单例
        bkt_domain_params = BKTParameters()
        self.assertEqual(bkt_domain_params.p_l0, 0.20)
        self.assertEqual(bkt_domain_params.p_t, 0.10)
        self.assertEqual(bkt_domain_params.p_g, 0.20)
        self.assertEqual(bkt_domain_params.p_s, 0.10)

    def test_bkt_golden_3step_trajectory(self):
        """验证黄金作答序列 (Wrong -> Correct -> Correct) 数学轨迹精确无偏"""
        # Step 0: 初始状态
        state_0 = create_initial_state("S999", "K99")
        self.assertEqual(state_0.mastery_probability, 0.20)
        self.assertEqual(format_canonical_mastery(state_0.mastery_probability), "0.2000")

        # Step 1: 答错 (Wrong)
        res_1 = apply_attempt(state_0, is_correct=False, event_id="evt-1", timestamp="2026-09-05T12:00:00Z")
        self.assertAlmostEqual(res_1.state.mastery_probability, 0.12727, places=4)
        self.assertEqual(format_canonical_mastery(res_1.state.mastery_probability), "0.1273")

        # Step 2: 答对 (Correct)
        res_2 = apply_attempt(res_1.state, is_correct=True, event_id="evt-2", timestamp="2026-09-05T12:01:00Z")
        self.assertAlmostEqual(res_2.state.mastery_probability, 0.45661, places=4)
        self.assertEqual(format_canonical_mastery(res_2.state.mastery_probability), "0.4566")

        # Step 3: 答对 (Correct)
        res_3 = apply_attempt(res_2.state, is_correct=True, event_id="evt-3", timestamp="2026-09-05T12:02:00Z")
        self.assertAlmostEqual(res_3.state.mastery_probability, 0.81180, places=4)
        self.assertEqual(format_canonical_mastery(res_3.state.mastery_probability), "0.8118")

    def test_decision_core_legal_pairs_and_validation(self):
        """验证决策核心法定 5 组动作与原因配对"""
        expected_pairs = {
            (PathAction.UNLOCK_DOWNSTREAM, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED),
            (PathAction.RETAIN, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED),
            (PathAction.RETAIN, ReplanningReasonCode.MASTERY_STATE_UNCHANGED),
            (PathAction.RETAIN, ReplanningReasonCode.PREREQUISITE_NOT_READY),
            (PathAction.DEMOTE_TO_REVIEW, ReplanningReasonCode.REVIEW_REQUIRED_DEMOTION),
        }
        self.assertEqual(LEGAL_DECISION_PAIRS, expected_pairs)

        # 验证 5 组均合法通过
        for action, reason in LEGAL_DECISION_PAIRS:
            validate_decision_pair(action, reason)

        # 验证非法配对抛出 ValueError
        illegal_pairs = [
            (PathAction.UNLOCK_DOWNSTREAM, ReplanningReasonCode.MASTERY_STATE_UNCHANGED),
            (PathAction.UNLOCK_DOWNSTREAM, ReplanningReasonCode.PREREQUISITE_NOT_READY),
            (PathAction.DEMOTE_TO_REVIEW, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED),
        ]
        for bad_action, bad_reason in illegal_pairs:
            with self.assertRaises(ValueError):
                validate_decision_pair(bad_action, bad_reason)

    def test_canonical_payload_byte_for_byte_determinism(self):
        """验证规范化业务载荷字节级确定性序列化与 SHA-256 哈希稳定性"""
        payload = CanonicalBusinessPayload(
            student_id="S001",
            knowledge_id="K08",
            before_mastery="0.4566",
            after_mastery="0.8118",
            before_path_state=PathState.IN_PROGRESS,
            after_path_state=PathState.COMPLETED,
            action=PathAction.UNLOCK_DOWNSTREAM,
            reason_code=ReplanningReasonCode.MASTERY_THRESHOLD_REACHED,
            affected_nodes=["K09", "K08"],  # 故意乱序传入
        )

        # 断言 affected_nodes 必须自动 ASCII 升序排序
        self.assertEqual(payload.affected_nodes, ["K08", "K09"])

        json_str_1 = payload.to_canonical_json()
        hash_1 = hashlib.sha256(json_str_1.encode("utf-8")).hexdigest()

        for _ in range(50):
            json_str_i = payload.to_canonical_json()
            hash_i = hashlib.sha256(json_str_i.encode("utf-8")).hexdigest()
            self.assertEqual(json_str_i, json_str_1)
            self.assertEqual(hash_i, hash_1)
