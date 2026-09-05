# -*- coding: utf-8 -*-
"""
tests/test_path_replanning_dag.py
测试 DAG 只读探针、1-hop MutationDomain 物理隔离与全套负向/边界测试用例：
1. P < 0.80 时绝不能产生 PREREQUISITE_NOT_READY (必须为 RETAIN × MASTERY_STATE_UNCHANGED)
2. 1-hop 隔离：K08 达标解锁 K09 为 AVAILABLE，K11 保持 LOCKED 且严禁进入 affected_nodes；affected_nodes 仅为 ['K08', 'K09']；K09 绝不自动转为 IN_PROGRESS
3. 当且仅当 Kc 达成 P>=0.80 且所有后继均受阻于未掌握同辈前置时，产生 RETAIN × PREREQUISITE_NOT_READY
4. 非任务上下文 (is_task_context=False) 下达成 MASTERED，PathState 不得修改为 COMPLETED
5. 曾掌握且跌破 0.70 且连错 >= 2 触发 DEMOTE_TO_REVIEW × REVIEW_REQUIRED_DEMOTION
6. 图谱终点节点（无后继）达成 P>=0.80 时返回 RETAIN × MASTERY_THRESHOLD_REACHED
7. DAG 只读探针与后继准入评估函数正确性
"""
import tempfile
import unittest
from pathlib import Path

import bkt_state_service
import path_state_service
import path_replanning_service
from path_state_service import PathState
from path_replanning_service import (
    PathAction,
    ReplanningReasonCode,
    get_prerequisites,
    get_successors,
    is_knowledge_mastered,
    can_unlock_successor,
    evaluate_and_replan,
)


class TestPathReplanningDAG(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path_states_file = Path(self.temp_dir.name) / "test_path_states.json"
        self.bkt_states_file = Path(self.temp_dir.name) / "test_bkt_states.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_negative_p_below_080_never_prerequisite_not_ready(self):
        """负向测试 1: 当 P(L) < 0.80 时，无论下游前置情况如何，绝对严禁生成 PREREQUISITE_NOT_READY"""
        # 设定 K08 此时仅 0.4566 (< 0.80)，且下游 K11 确有未满足前置
        envelope = evaluate_and_replan(
            student_id="stu_001",
            knowledge_id="K08",
            before_mastery=0.1273,
            after_mastery=0.4566,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        payload = envelope.canonical_payload
        self.assertEqual(payload.action, PathAction.RETAIN)
        self.assertEqual(payload.reason_code, ReplanningReasonCode.MASTERY_STATE_UNCHANGED)
        self.assertNotEqual(payload.reason_code, ReplanningReasonCode.PREREQUISITE_NOT_READY)

    def test_02_mutation_domain_1hop_isolation_and_k11_locked(self):
        """负向测试 2 & 3: K08 达标解锁 K09 为 AVAILABLE，K11 保持 LOCKED 且严禁进入 affected_nodes；affected_nodes 仅为 ['K08', 'K09']；K09 绝不自动转为 IN_PROGRESS"""
        path_state_service.set_path_states_bulk(
            "stu_001",
            {
                "K08": PathState.IN_PROGRESS,
                "K09": PathState.LOCKED,
                "K11": PathState.LOCKED,
            },
            states_file=self.path_states_file,
        )

        envelope = evaluate_and_replan(
            student_id="stu_001",
            knowledge_id="K08",
            before_mastery=0.4566,
            after_mastery=0.8118,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        payload = envelope.canonical_payload
        # K08 完结，K09 解锁为 AVAILABLE
        self.assertEqual(payload.action, PathAction.UNLOCK_DOWNSTREAM)
        self.assertEqual(payload.reason_code, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED)
        self.assertEqual(payload.affected_nodes, ["K08", "K09"])
        self.assertNotIn("K11", payload.affected_nodes)

        # 检查持久化状态：K11 必须依然是 LOCKED
        k11_state = path_state_service.get_path_state("stu_001", "K11", states_file=self.path_states_file)
        self.assertEqual(k11_state, PathState.LOCKED)

        # 检查 K09 必须是 AVAILABLE，绝不可自动变为 IN_PROGRESS
        k09_state = path_state_service.get_path_state("stu_001", "K09", states_file=self.path_states_file)
        self.assertEqual(k09_state, PathState.AVAILABLE)

    def test_03_prerequisite_not_ready_fired_only_when_mastered_and_all_succ_blocked(self):
        """当且仅当 Kc 达标 (P>=0.80) 且所有后继均因联合前置未满足而受阻时，产生 PREREQUISITE_NOT_READY"""
        # 设定场景：K09 已先被置为 AVAILABLE，只剩下 K11 作为需要解锁的后继，但 K10 未掌握
        path_state_service.set_path_states_bulk(
            "stu_001",
            {
                "K08": PathState.IN_PROGRESS,
                "K09": PathState.AVAILABLE,  # 已是 AVAILABLE，不需要再次解锁
                "K11": PathState.LOCKED,     # 依赖 K08, K09, K10，但 K10 未掌握
            },
            states_file=self.path_states_file,
        )

        envelope = evaluate_and_replan(
            student_id="stu_001",
            knowledge_id="K08",
            before_mastery=0.7500,
            after_mastery=0.8500,  # 达标
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        payload = envelope.canonical_payload
        # K09 状态未变，K11 无法解锁，因此所有后继均无法解锁，且 K11 受到未掌握同辈前置阻塞
        self.assertEqual(payload.action, PathAction.RETAIN)
        self.assertEqual(payload.reason_code, ReplanningReasonCode.PREREQUISITE_NOT_READY)
        self.assertEqual(payload.affected_nodes, ["K08"])

    def test_04_negative_non_task_context_does_not_complete_path_state(self):
        """负向测试 4: 非任务上下文（如自主测验），MASTERED 不得修改 PathState 为 COMPLETED"""
        path_state_service.set_path_state(
            "stu_001", "K08", PathState.AVAILABLE, states_file=self.path_states_file
        )
        envelope = evaluate_and_replan(
            student_id="stu_001",
            knowledge_id="K08",
            before_mastery=0.75,
            after_mastery=0.85,
            is_task_context=False,  # 非任务上下文
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        payload = envelope.canonical_payload
        # 路径状态保持原样 AVAILABLE
        self.assertEqual(payload.before_path_state, PathState.AVAILABLE)
        self.assertEqual(payload.after_path_state, PathState.AVAILABLE)
        # K08 不应该被持久化为 COMPLETED
        k08_state = path_state_service.get_path_state("stu_001", "K08", states_file=self.path_states_file)
        self.assertEqual(k08_state, PathState.AVAILABLE)

    def test_05_regression_demotion_trigger(self):
        """认知退化检查：曾掌握且跌破 0.70 且连错 >= 2 触发 DEMOTE_TO_REVIEW × REVIEW_REQUIRED_DEMOTION"""
        envelope = evaluate_and_replan(
            student_id="stu_001",
            knowledge_id="K08",
            before_mastery=0.72,
            after_mastery=0.65,
            consecutive_incorrect=2,
            previously_mastered=True,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        payload = envelope.canonical_payload
        self.assertEqual(payload.action, PathAction.DEMOTE_TO_REVIEW)
        self.assertEqual(payload.reason_code, ReplanningReasonCode.REVIEW_REQUIRED_DEMOTION)

    def test_06_terminal_node_without_successors_retains_mastery_reached(self):
        """图谱终点节点（无后继）达成 P>=0.80 时返回 RETAIN × MASTERY_THRESHOLD_REACHED"""
        path_state_service.set_path_state(
            "stu_001", "K30", PathState.IN_PROGRESS, states_file=self.path_states_file
        )
        envelope = evaluate_and_replan(
            student_id="stu_001",
            knowledge_id="K30",
            before_mastery=0.4566,
            after_mastery=0.8500,
            states_file=self.path_states_file,
            bkt_states_file=self.bkt_states_file,
        )
        payload = envelope.canonical_payload
        self.assertEqual(payload.action, PathAction.RETAIN)
        self.assertEqual(payload.reason_code, ReplanningReasonCode.MASTERY_THRESHOLD_REACHED)
        self.assertEqual(payload.before_path_state, PathState.IN_PROGRESS)
        self.assertEqual(payload.after_path_state, PathState.COMPLETED)
        self.assertEqual(payload.affected_nodes, ["K30"])

        k30_state = path_state_service.get_path_state("stu_001", "K30", states_file=self.path_states_file)
        self.assertEqual(k30_state, PathState.COMPLETED)

    def test_07_dag_probes_and_helpers(self):
        """验证 DAG 只读探针与后继准入评估函数"""
        self.assertEqual(get_prerequisites("K08"), ["K04", "K07"])
        self.assertEqual(get_successors("K08"), ["K09", "K11"])
        self.assertEqual(get_successors("K30"), [])

        # K09 依赖 K08，当 K08 just mastered 时，可以解锁 K09
        self.assertTrue(can_unlock_successor("stu_001", "K09", current_just_mastered="K08", bkt_states_file=self.bkt_states_file))
        # K11 依赖 K08, K09, K10，当仅 K08 just mastered 时，K11 不能解锁
        self.assertFalse(can_unlock_successor("stu_001", "K11", current_just_mastered="K08", bkt_states_file=self.bkt_states_file))
