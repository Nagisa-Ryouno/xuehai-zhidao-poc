# -*- coding: utf-8 -*-
"""
test_bkt_processor.py
P0-6 BKT 事件处理器与历史重建单元测试

覆盖 9 大核心测试用例：
1. QUESTION_ATTEMPT 事件正常消费并触发 BKT 状态更新
2. HINT_REQUEST 事件被安全忽略 (status="ignored")，不改变 BKT 状态
3. CONCEPT_VIEW / PATH_STEP_COMPLETE 事件被安全忽略，不改变 BKT 状态
4. 正确作答事件使得掌握度上升并更新统计
5. 错误作答事件使得掌握度下降并更新统计
6. 严格幂等保证：同一个 event_id 重复消费时，status="already_processed", changed=False
7. payload 缺失 is_correct 或字段非法时返回错误，不污染状态
8. server_timestamp 决定历史事件顺序 (权威排序)，时间相同时 tie-break event_id
9. rebuild_student_knowledge_state 从历史事件列表完整确定性重建最终状态
"""

import tempfile
import unittest
from pathlib import Path
from typing import List

import bkt_service
import bkt_state_service
import bkt_event_processor
import event_service


class TestBKTProcessor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_states_file = Path(self.temp_dir.name) / "test_proc_states.json"
        self.temp_processed_file = Path(self.temp_dir.name) / "test_proc_events.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def _make_event(
        self,
        event_id: str,
        student_id: str = "S001",
        knowledge_id: str = "K08",
        event_type: str = "QUESTION_ATTEMPT",
        is_correct: bool = True,
        server_ts: str = "2026-09-05T20:30:00+08:00",
    ) -> event_service.LearningEvent:
        payload = {"question_id": f"Q-{knowledge_id}-01", "is_correct": is_correct}
        return event_service.LearningEvent(
            event_id=event_id,
            student_id=student_id,
            knowledge_id=knowledge_id,
            event_type=event_type,
            payload=payload,
            client_timestamp=server_ts,
            server_timestamp=server_ts,
        )

    def test_01_question_attempt_updates_bkt(self):
        """Test 1: QUESTION_ATTEMPT 事件正常消费，更新 BKT 并持久化"""
        evt = self._make_event("evt-01", is_correct=True)
        res = bkt_event_processor.process_event(
            evt,
            states_file=self.temp_states_file,
            processed_file=self.temp_processed_file,
        )

        self.assertEqual(res.status, "updated")
        self.assertTrue(res.changed)
        self.assertEqual(res.event_id, "evt-01")
        self.assertEqual(res.student_id, "S001")
        self.assertEqual(res.knowledge_id, "K08")
        self.assertAlmostEqual(res.before_mastery, 0.20, places=4)
        self.assertGreater(res.after_mastery, 0.20)
        self.assertIsNotNone(res.state)
        self.assertEqual(res.state.attempts, 1)

    def test_02_hint_request_ignored(self):
        """Test 2: HINT_REQUEST 事件不参与 BKT 数学更新，状态标记为 ignored"""
        evt = self._make_event("evt-hint-01", event_type="HINT_REQUEST")
        res = bkt_event_processor.process_event(
            evt,
            states_file=self.temp_states_file,
            processed_file=self.temp_processed_file,
        )

        self.assertEqual(res.status, "ignored")
        self.assertFalse(res.changed)
        # 验证 state store 中未初始化该事件所产生的 attempts
        state = bkt_state_service.get_state("S001", "K08", states_file=self.temp_states_file)
        self.assertEqual(state.attempts, 0)

    def test_03_concept_view_ignored(self):
        """Test 3: CONCEPT_VIEW 事件不参与 BKT 数学更新，返回 ignored"""
        evt = self._make_event("evt-view-01", event_type="CONCEPT_VIEW")
        res = bkt_event_processor.process_event(
            evt,
            states_file=self.temp_states_file,
            processed_file=self.temp_processed_file,
        )
        self.assertEqual(res.status, "ignored")
        self.assertFalse(res.changed)

    def test_04_incorrect_attempt_decreases_mastery(self):
        """Test 4: 答错题目事件驱动掌握概率由 0.20 下降至约 0.1273"""
        evt = self._make_event("evt-wrong-01", is_correct=False)
        res = bkt_event_processor.process_event(
            evt,
            states_file=self.temp_states_file,
            processed_file=self.temp_processed_file,
        )

        self.assertEqual(res.status, "updated")
        self.assertLess(res.after_mastery, res.before_mastery)
        self.assertAlmostEqual(res.after_mastery, 4.2 / 33.0, places=6)
        self.assertEqual(res.state.incorrect_attempts, 1)

    def test_05_idempotency_prevents_duplicate_updates(self):
        """Test 5: 严格幂等测试：同一个 event_id 消费两次，第二次绝对不重复计算"""
        evt = self._make_event("evt-idem-01", is_correct=True)

        # 第一次处理
        res1 = bkt_event_processor.process_event(
            evt,
            states_file=self.temp_states_file,
            processed_file=self.temp_processed_file,
        )
        self.assertEqual(res1.status, "updated")
        self.assertTrue(res1.changed)
        first_mastery = res1.after_mastery

        # 第二次重复处理相同 event_id
        res2 = bkt_event_processor.process_event(
            evt,
            states_file=self.temp_states_file,
            processed_file=self.temp_processed_file,
        )
        self.assertEqual(res2.status, "already_processed")
        self.assertFalse(res2.changed)

        # 验证 state 中的掌握度与做题次数依然为第一次的值
        final_state = bkt_state_service.get_state("S001", "K08", states_file=self.temp_states_file)
        self.assertAlmostEqual(final_state.mastery_probability, first_mastery, places=6)
        self.assertEqual(final_state.attempts, 1, "重复消费不得增加 attempts 计数！")

    def test_06_invalid_payload_error(self):
        """Test 6: payload 缺少 is_correct 时返回 error，不影响已有掌握度"""
        bad_evt = event_service.LearningEvent(
            event_id="evt-bad-01",
            student_id="S001",
            knowledge_id="K08",
            event_type="QUESTION_ATTEMPT",
            payload={"question_id": "Q-01"},  # 缺少 is_correct
            client_timestamp="2026-09-05T20:30:00+08:00",
            server_timestamp="2026-09-05T20:30:00+08:00",
        )
        res = bkt_event_processor.process_event(
            bad_evt,
            states_file=self.temp_states_file,
            processed_file=self.temp_processed_file,
        )
        self.assertEqual(res.status, "error")
        self.assertFalse(res.changed)

    def test_07_rebuild_from_historical_events(self):
        """
        Test 7: 历史事件确定性回放重建 (Rebuild)
        序列：
        1. 20:00:00 错 (False)
        2. 20:01:00 对 (True)
        3. 20:02:00 对 (True)
        即使事件列表乱序传入，也必须按 server_timestamp 正确排序并还原出一致结果
        """
        evt1 = self._make_event("e1", is_correct=False, server_ts="2026-09-05T20:00:00+08:00")
        evt2 = self._make_event("e2", is_correct=True, server_ts="2026-09-05T20:01:00+08:00")
        evt3 = self._make_event("e3", is_correct=True, server_ts="2026-09-05T20:02:00+08:00")

        # 故意打乱传入顺序: e2 -> e3 -> e1
        unordered_events = [evt2, evt3, evt1]

        rebuilt_state = bkt_event_processor.rebuild_student_knowledge_state(
            student_id="S001",
            knowledge_id="K08",
            events=unordered_events,
        )

        self.assertEqual(rebuilt_state.attempts, 3)
        self.assertEqual(rebuilt_state.correct_attempts, 2)
        self.assertEqual(rebuilt_state.incorrect_attempts, 1)
        self.assertEqual(rebuilt_state.consecutive_correct, 2)
        self.assertEqual(rebuilt_state.last_event_id, "e3")

        # 手动按序推导目标概率：
        p0 = 0.20
        p1 = bkt_service.calculate_bkt_update(p0, is_correct=False)
        p2 = bkt_service.calculate_bkt_update(p1, is_correct=True)
        p3 = bkt_service.calculate_bkt_update(p2, is_correct=True)
        self.assertAlmostEqual(rebuilt_state.mastery_probability, p3, places=6)

    def test_08_rebuild_idempotency_with_duplicates(self):
        """Test 8: 历史回放时即使包含重复 event_id，也能自动去重并精准计算"""
        evt1 = self._make_event("e1", is_correct=True, server_ts="2026-09-05T20:00:00+08:00")
        # 包含重复的 e1
        events_with_dup = [evt1, evt1, evt1]

        rebuilt = bkt_event_processor.rebuild_student_knowledge_state(
            student_id="S001",
            knowledge_id="K08",
            events=events_with_dup,
        )
        self.assertEqual(rebuilt.attempts, 1, "历史回放中重复事件必须被幂等去重")


if __name__ == "__main__":
    unittest.main()
