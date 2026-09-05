# -*- coding: utf-8 -*-
"""
test_bkt_state.py
P0-6 BKT 知识状态存储与并发持久化单元测试

覆盖 6 大核心测试用例：
1. 新学生知识点状态自动初始化 (初值 P(L0))
2. 状态写入 JSON 文件并持久化
3. 状态重新读取一致性 (完整反序列化验证)
4. 并发更新原子性与线程安全性 (多线程写入文件不损坏)
5. 测试环境与生产环境隔离 (使用临时目录，绝不污染 data/bkt_states.json)
6. 幂等处理事件追踪文件 (processed_events) 读写持久化
"""

import json
import tempfile
import threading
import unittest
from pathlib import Path

import bkt_service
import bkt_state_service


class TestBKTState(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_states_file = Path(self.temp_dir.name) / "test_bkt_states.json"
        self.temp_processed_file = Path(self.temp_dir.name) / "test_processed_events.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_auto_initialization_on_missing_state(self):
        """Test 1: 读取尚未存在的学生知识点状态时，自动以 P(L0)=0.20 初始化"""
        state = bkt_state_service.get_state(
            student_id="S001",
            knowledge_id="K08",
            states_file=self.temp_states_file,
            auto_init=True,
        )
        self.assertEqual(state.student_id, "S001")
        self.assertEqual(state.knowledge_id, "K08")
        self.assertAlmostEqual(state.mastery_probability, 0.20, places=4)
        self.assertEqual(state.attempts, 0)

    def test_02_state_save_and_persistence(self):
        """Test 2: 保存状态后正确落盘为 JSON，且 JSON 文件格式合法"""
        state = bkt_service.create_initial_state("S001", "K08")
        res = bkt_service.apply_attempt(
            state,
            is_correct=True,
            event_id="evt-test-01",
            timestamp="2026-09-05T20:15:00+08:00",
        )
        bkt_state_service.save_state(res.state, states_file=self.temp_states_file)

        self.assertTrue(self.temp_states_file.exists())
        data = json.loads(self.temp_states_file.read_text(encoding="utf-8"))
        self.assertIn("S001:K08", data)
        self.assertEqual(data["S001:K08"]["student_id"], "S001")
        self.assertEqual(data["S001:K08"]["attempts"], 1)
        self.assertEqual(data["S001:K08"]["correct_attempts"], 1)

    def test_03_state_reloading_consistency(self):
        """Test 3: 从文件重新加载状态，所有字段值与原状态完全一致"""
        state = bkt_service.create_initial_state("S003", "K01")
        res = bkt_service.apply_attempt(
            state,
            is_correct=False,
            event_id="evt-test-02",
            timestamp="2026-09-05T20:16:00+08:00",
        )
        bkt_state_service.save_state(res.state, states_file=self.temp_states_file)

        loaded = bkt_state_service.get_state(
            student_id="S003",
            knowledge_id="K01",
            states_file=self.temp_states_file,
        )
        self.assertEqual(loaded.student_id, "S003")
        self.assertEqual(loaded.knowledge_id, "K01")
        self.assertAlmostEqual(loaded.mastery_probability, res.after_mastery, places=6)
        self.assertEqual(loaded.attempts, 1)
        self.assertEqual(loaded.incorrect_attempts, 1)
        self.assertEqual(loaded.last_event_id, "evt-test-02")

    def test_04_concurrent_write_safety(self):
        """Test 4: 20 个线程并发更新不同知识点状态，文件保持完整无损且全部落盘"""
        threads = []
        errors = []

        def worker(idx: int):
            try:
                kid = f"K{idx:02d}"
                st = bkt_state_service.get_state(
                    student_id="S001",
                    knowledge_id=kid,
                    states_file=self.temp_states_file,
                )
                res = bkt_service.apply_attempt(
                    st,
                    is_correct=(idx % 2 == 0),
                    event_id=f"evt-c-{idx}",
                    timestamp="2026-09-05T20:20:00+08:00",
                )
                bkt_state_service.save_state(res.state, states_file=self.temp_states_file)
            except Exception as e:
                errors.append(e)

        for i in range(1, 21):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"并发写入产生异常: {errors}")
        data = json.loads(self.temp_states_file.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 20, "20 个知识点状态必须全部完整持久化")

    def test_05_isolation_from_production(self):
        """Test 5: 测试环境写入临时文件，严禁触碰生产 data/bkt_states.json"""
        prod_file = bkt_state_service.DEFAULT_STATES_FILE
        prod_existed_before = prod_file.exists()
        prod_mtime_before = prod_file.stat().st_mtime if prod_existed_before else None

        # 执行测试写入
        st = bkt_state_service.get_state("S005", "K20", states_file=self.temp_states_file)
        bkt_state_service.save_state(st, states_file=self.temp_states_file)

        # 检查生产文件状态未受波及
        if not prod_existed_before:
            self.assertFalse(prod_file.exists(), "测试绝不能在生产路径创建 bkt_states.json")
        else:
            self.assertEqual(prod_file.stat().st_mtime, prod_mtime_before)

    def test_06_processed_events_tracking(self):
        """Test 6: processed_events 幂等文件记录与查询"""
        self.assertFalse(
            bkt_state_service.is_event_processed("evt-unique-01", processed_file=self.temp_processed_file)
        )

        bkt_state_service.mark_event_processed(
            "evt-unique-01",
            event_info={"student_id": "S001", "knowledge_id": "K08"},
            processed_file=self.temp_processed_file,
        )

        self.assertTrue(
            bkt_state_service.is_event_processed("evt-unique-01", processed_file=self.temp_processed_file)
        )


if __name__ == "__main__":
    unittest.main()
