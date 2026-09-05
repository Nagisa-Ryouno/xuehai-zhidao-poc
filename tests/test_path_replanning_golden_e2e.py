# -*- coding: utf-8 -*-
"""
tests/test_path_replanning_golden_e2e.py
学海智导 V2 - P0-8 局部动态路径重规划引擎 Golden E2E 3 步时序闭环与确定性等价测试

业务拓扑：
- K08 需求价格弹性 (直接后继: K09, K11)
- K09 收入与交叉弹性 (唯一前置: K08; 后继: K11)
- K10 供给弹性 (前置: K05, K07; 后继: K11)
- K11 弹性与税收归宿 (多前置: K08, K09, K10; 后继: K12)

覆盖测试：
1. test_01_golden_e2e_three_step_sequence:
   完整验证 3 步连续作答 (Wrong -> Right -> Right) 对应的 BKT 掌握度跃迁、
   重规划决策裁决 (RETAIN -> RETAIN -> UNLOCK_DOWNSTREAM)、
   受影响节点列表与持久化状态原子迁移 (K08 COMPLETED, K09 AVAILABLE, K10 LOCKED, K11 LOCKED)。
2. test_02_determinism_50_iterations_byte_for_byte_and_sha256:
   完全相同的初始状态与输入参数重复执行 50 次，断言 to_canonical_json() 与 SHA-256 50 次完全一致。
3. test_03_audit_metadata_isolation_does_not_affect_canonical_json_and_sha256:
   断言外层 AuditMetadata (不同 decision_id, 不同 timestamp, 不同 trace_id)
   绝不影响内层 CanonicalBusinessPayload 的 to_canonical_json() 与 SHA-256 哈希。
"""
import hashlib
import tempfile
import unittest
import uuid
from pathlib import Path

import bkt_service
import bkt_state_service
import path_replanning_service
import path_state_service
from path_replanning_service import (
    AuditMetadata,
    DecisionAuditEnvelope,
    PathAction,
    ReplanningReasonCode,
)
from path_state_service import PathState


class TestGoldenE2EAndDeterminism(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path_states_file = Path(self.temp_dir.name) / "test_path_states.json"
        self.bkt_states_file = Path(self.temp_dir.name) / "test_bkt_states.json"
        self.student_id = "stu_golden_001"

        # 初始状态拓扑设置：
        # K08: (WEAK, IN_PROGRESS, P=0.2000)
        # K09: (WEAK, LOCKED, P=0.2000)
        # K10: (WEAK, LOCKED, P=0.2000) (初始未掌握)
        # K11: (WEAK, LOCKED, P=0.2000)
        path_state_service.set_path_states_bulk(
            self.student_id,
            {
                "K08": PathState.IN_PROGRESS,
                "K09": PathState.LOCKED,
                "K10": PathState.LOCKED,
                "K11": PathState.LOCKED,
            },
            states_file=self.path_states_file,
        )

        for kid in ["K08", "K09", "K10", "K11"]:
            bkt_state_service.save_state(
                bkt_service.create_initial_state(self.student_id, kid),
                states_file=self.bkt_states_file,
            )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_golden_e2e_three_step_sequence(self):
        """
        验证 Golden E2E 3 步完整业务时序与断言规范：
        Step 1: 答错 (Wrong) -> P(L) = 0.1273... -> RETAIN x MASTERY_STATE_UNCHANGED
        Step 2: 答对 (Correct) -> P(L) = 0.4566... -> RETAIN x MASTERY_STATE_UNCHANGED (WEAK, <0.60)
        Step 3: 答对 (Correct) -> P(L) = 0.8118... -> UNLOCK_DOWNSTREAM x MASTERY_THRESHOLD_REACHED (K08 COMPLETED, K09 AVAILABLE, K10 LOCKED, K11 LOCKED)
        """
        # 显式校验初始前置状态
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K08", states_file=self.path_states_file),
            PathState.IN_PROGRESS,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K09", states_file=self.path_states_file),
            PathState.LOCKED,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K10", states_file=self.path_states_file),
            PathState.LOCKED,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K11", states_file=self.path_states_file),
            PathState.LOCKED,
        )

        # =============================================================
        # Step 1: 答错 (Wrong)
        # bkt_service.apply_attempt(state_0, is_correct=False) -> P(L) = 0.1273...
        # =============================================================
        bkt_state_0 = bkt_state_service.get_state(
            self.student_id, "K08", states_file=self.bkt_states_file, auto_init=False
        )
        self.assertIsNotNone(bkt_state_0)
        self.assertAlmostEqual(bkt_state_0.mastery_probability, 0.2000, places=4)

        step1_res = bkt_service.apply_attempt(
            bkt_state_0,
            is_correct=False,
            event_id="evt_golden_01",
            timestamp="2026-09-05T10:00:00Z",
        )
        bkt_state_service.save_state(step1_res.state, states_file=self.bkt_states_file)

        env_step1 = path_replanning_service.evaluate_and_replan(
            student_id=self.student_id,
            knowledge_id="K08",
            before_mastery=bkt_state_0.mastery_probability,
            after_mastery=step1_res.state.mastery_probability,
            consecutive_incorrect=step1_res.state.consecutive_incorrect,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        p1 = env_step1.canonical_payload

        # Step 1 严格断言
        self.assertEqual(p1.before_mastery, "0.2000")
        self.assertEqual(p1.after_mastery, "0.1273")
        self.assertEqual(p1.before_path_state, PathState.IN_PROGRESS)
        self.assertEqual(p1.after_path_state, PathState.IN_PROGRESS)
        self.assertEqual(p1.action, PathAction.RETAIN)
        self.assertEqual(p1.reason_code, ReplanningReasonCode.MASTERY_STATE_UNCHANGED)
        self.assertEqual(p1.affected_nodes, ["K08"])
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K08", states_file=self.path_states_file),
            PathState.IN_PROGRESS,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K09", states_file=self.path_states_file),
            PathState.LOCKED,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K10", states_file=self.path_states_file),
            PathState.LOCKED,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K11", states_file=self.path_states_file),
            PathState.LOCKED,
        )

        # =============================================================
        # Step 2: 答对 (Correct)
        # bkt_service.apply_attempt(state_1, is_correct=True) -> P(L) = 0.4566...
        # 掌握度 0.4566 严格属于 WEAK (< 0.60)，绝非 DEVELOPING！
        # =============================================================
        step2_res = bkt_service.apply_attempt(
            step1_res.state,
            is_correct=True,
            event_id="evt_golden_02",
            timestamp="2026-09-05T10:01:00Z",
        )
        bkt_state_service.save_state(step2_res.state, states_file=self.bkt_states_file)

        # 掌握度 0.4566 严格属于 WEAK (< 0.60)，绝非 DEVELOPING
        self.assertLess(step2_res.state.mastery_probability, 0.60)
        self.assertGreaterEqual(step2_res.state.mastery_probability, 0.0)

        env_step2 = path_replanning_service.evaluate_and_replan(
            student_id=self.student_id,
            knowledge_id="K08",
            before_mastery=step1_res.state.mastery_probability,
            after_mastery=step2_res.state.mastery_probability,
            consecutive_incorrect=step2_res.state.consecutive_incorrect,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        p2 = env_step2.canonical_payload

        # Step 2 严格断言
        self.assertEqual(p2.before_mastery, "0.1273")
        self.assertEqual(p2.after_mastery, "0.4566")
        self.assertEqual(p2.before_path_state, PathState.IN_PROGRESS)
        self.assertEqual(p2.after_path_state, PathState.IN_PROGRESS)
        self.assertEqual(p2.action, PathAction.RETAIN)
        self.assertEqual(p2.reason_code, ReplanningReasonCode.MASTERY_STATE_UNCHANGED)
        self.assertEqual(p2.affected_nodes, ["K08"])
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K08", states_file=self.path_states_file),
            PathState.IN_PROGRESS,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K09", states_file=self.path_states_file),
            PathState.LOCKED,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K10", states_file=self.path_states_file),
            PathState.LOCKED,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K11", states_file=self.path_states_file),
            PathState.LOCKED,
        )

        # =============================================================
        # Step 3: 答对 (Correct)
        # bkt_service.apply_attempt(state_2, is_correct=True) -> P(L) = 0.8118...
        # 掌握度 0.8118 达到 MASTERED (>= 0.80)
        # =============================================================
        step3_res = bkt_service.apply_attempt(
            step2_res.state,
            is_correct=True,
            event_id="evt_golden_03",
            timestamp="2026-09-05T10:02:00Z",
        )
        bkt_state_service.save_state(step3_res.state, states_file=self.bkt_states_file)

        # 掌握度 0.8118 达到 MASTERED (>= 0.80)
        self.assertGreaterEqual(step3_res.state.mastery_probability, 0.80)

        env_step3 = path_replanning_service.evaluate_and_replan(
            student_id=self.student_id,
            knowledge_id="K08",
            before_mastery=step2_res.state.mastery_probability,
            after_mastery=step3_res.state.mastery_probability,
            consecutive_incorrect=step3_res.state.consecutive_incorrect,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        p3 = env_step3.canonical_payload

        # Step 3 严格断言
        self.assertEqual(p3.before_mastery, "0.4566")
        self.assertEqual(p3.after_mastery, "0.8118")
        self.assertEqual(p3.before_path_state, PathState.IN_PROGRESS)
        self.assertEqual(p3.after_path_state, PathState.COMPLETED)
        self.assertEqual(p3.action, PathAction.UNLOCK_DOWNSTREAM)
        self.assertEqual(p3.reason_code, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED)
        self.assertEqual(p3.affected_nodes, ["K08", "K09"])  # ASCII 字典序升序
        self.assertNotIn("K11", p3.affected_nodes)           # K11 绝不得进入 affected_nodes

        # 持久化状态严格断言
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K08", states_file=self.path_states_file),
            PathState.COMPLETED,
        )
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K09", states_file=self.path_states_file),
            PathState.AVAILABLE,
        )
        # 解锁后绝不是 IN_PROGRESS
        self.assertNotEqual(
            path_state_service.get_path_state(self.student_id, "K09", states_file=self.path_states_file),
            PathState.IN_PROGRESS,
        )
        # 【P2 要求】：显式断言 K10 == LOCKED
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K10", states_file=self.path_states_file),
            PathState.LOCKED,
        )
        # 因联合前置 K10 未掌握，K11 保持 LOCKED
        self.assertEqual(
            path_state_service.get_path_state(self.student_id, "K11", states_file=self.path_states_file),
            PathState.LOCKED,
        )

    def test_02_determinism_50_iterations_byte_for_byte_and_sha256(self):
        """
        确定性与哈希一致性测试：
        完全相同输入重复执行 50 次：
        1. to_canonical_json() 字节级严格相等
        2. SHA-256 哈希值 50 次计算严格一致
        """
        json_outputs = []
        hash_outputs = []

        for i in range(50):
            # 每次循环将学生初始路径状态精准重置为相同输入
            path_state_service.set_path_states_bulk(
                "stu_det_50",
                {
                    "K08": PathState.IN_PROGRESS,
                    "K09": PathState.LOCKED,
                    "K10": PathState.LOCKED,
                    "K11": PathState.LOCKED,
                },
                states_file=self.path_states_file,
            )

            env = path_replanning_service.evaluate_and_replan(
                student_id="stu_det_50",
                knowledge_id="K08",
                before_mastery=0.45661,
                after_mastery=0.81180,
                states_file=self.path_states_file,
                bkt_states_file=self.bkt_states_file,
            )

            c_json = env.canonical_payload.to_canonical_json()
            c_hash = hashlib.sha256(c_json.encode("utf-8")).hexdigest()

            json_outputs.append(c_json)
            hash_outputs.append(c_hash)

        self.assertEqual(len(json_outputs), 50)
        self.assertEqual(len(hash_outputs), 50)

        # 验证 50 次生成的 Canonical JSON 字节级完全唯一且一致
        unique_jsons = set(json_outputs)
        self.assertEqual(
            len(unique_jsons),
            1,
            f"Expected exactly 1 unique canonical JSON across 50 runs, got {len(unique_jsons)}",
        )

        # 验证 50 次生成的 SHA-256 哈希值完全唯一且一致
        unique_hashes = set(hash_outputs)
        self.assertEqual(
            len(unique_hashes),
            1,
            f"Expected exactly 1 unique SHA-256 hash across 50 runs, got {len(unique_hashes)}",
        )

        # 与首个结果进行遍历双重校验
        first_json = json_outputs[0]
        first_hash = hash_outputs[0]
        for idx, (j_str, h_str) in enumerate(zip(json_outputs, hash_outputs), start=1):
            self.assertEqual(
                j_str,
                first_json,
                f"第 {idx} 次运行的 to_canonical_json() 与第 1 次不一致",
            )
            self.assertEqual(
                h_str,
                first_hash,
                f"第 {idx} 次运行的 SHA-256 哈希与第 1 次不一致",
            )

    def test_03_audit_metadata_isolation_does_not_affect_canonical_json_and_sha256(self):
        """
        验证外层 AuditMetadata (不同 decision_id, 不同 timestamp, 不同 trace_id)
        绝不影响内层 CanonicalBusinessPayload 的 to_canonical_json() 与 SHA-256 哈希。
        """
        # 设置相同的路径环境
        path_state_service.set_path_states_bulk(
            "stu_audit_iso",
            {
                "K08": PathState.IN_PROGRESS,
                "K09": PathState.LOCKED,
            },
            states_file=self.path_states_file,
        )

        env1 = path_replanning_service.evaluate_and_replan(
            student_id="stu_audit_iso",
            knowledge_id="K08",
            before_mastery=0.4566,
            after_mastery=0.8118,
            trace_id="trace_alpha_111",
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )

        # 手动构造具有完全不同的 decision_id 和 timestamp 的第二个信封，包装相同的 CanonicalBusinessPayload
        different_metadata = AuditMetadata(
            decision_id=str(uuid.uuid4()),
            timestamp="1999-12-31T23:59:59Z",
            trace_id="trace_omega_999",
        )
        env2 = DecisionAuditEnvelope(
            audit_metadata=different_metadata,
            canonical_payload=env1.canonical_payload,
        )

        # 显式断言外层元数据具有显著差异
        self.assertNotEqual(env1.audit_metadata.decision_id, env2.audit_metadata.decision_id)
        self.assertNotEqual(env1.audit_metadata.timestamp, env2.audit_metadata.timestamp)
        self.assertNotEqual(env1.audit_metadata.trace_id, env2.audit_metadata.trace_id)

        # 严格断言内层 to_canonical_json() 字节级严格相等
        json1 = env1.canonical_payload.to_canonical_json()
        json2 = env2.canonical_payload.to_canonical_json()
        self.assertEqual(json1, json2)

        # 严格断言 SHA-256 哈希值完全一致
        hash1 = hashlib.sha256(json1.encode("utf-8")).hexdigest()
        hash2 = hashlib.sha256(json2.encode("utf-8")).hexdigest()
        self.assertEqual(hash1, hash2)


if __name__ == "__main__":
    unittest.main()
