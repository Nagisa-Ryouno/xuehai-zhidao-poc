# -*- coding: utf-8 -*-
"""
tests/test_path_state.py
测试路径执行状态模型、默认初始化、状态迁移、学生隔离、并发安全与原子持久化
"""
import concurrent.futures
import json
import tempfile
import unittest
from pathlib import Path

import path_state_service
from path_state_service import PathState, StudentPathStates, StudentPathProfile


class TestPathStateService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.states_file = Path(self.temp_dir.name) / "test_path_states.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_default_state_is_locked(self):
        """未初始化的节点默认状态为 LOCKED"""
        state = path_state_service.get_path_state(
            "stu_001", "K08", states_file=self.states_file
        )
        self.assertEqual(state, PathState.LOCKED)

        # 自定义 default 测试
        custom_state = path_state_service.get_path_state(
            "stu_001", "K08", states_file=self.states_file, default=PathState.AVAILABLE
        )
        self.assertEqual(custom_state, PathState.AVAILABLE)

    def test_02_set_and_get_path_state(self):
        """单节点状态读写与持久化验证"""
        path_state_service.set_path_state(
            "stu_001", "K08", PathState.IN_PROGRESS, states_file=self.states_file
        )
        state = path_state_service.get_path_state(
            "stu_001", "K08", states_file=self.states_file
        )
        self.assertEqual(state, PathState.IN_PROGRESS)

        # 检查持久化文件已生成且内容正确
        self.assertTrue(self.states_file.exists())
        with open(self.states_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        self.assertIn("stu_001", raw_data)
        self.assertEqual(raw_data["stu_001"]["K08"], "IN_PROGRESS")

    def test_03_bulk_update_path_states(self):
        """批量原子更新多节点状态"""
        updates = {
            "K08": PathState.COMPLETED,
            "K09": PathState.AVAILABLE,
            "K11": PathState.LOCKED,
        }
        path_state_service.set_path_states_bulk(
            "stu_001", updates, states_file=self.states_file
        )
        all_states = path_state_service.get_all_path_states(
            "stu_001", states_file=self.states_file
        )
        self.assertEqual(all_states["K08"], PathState.COMPLETED)
        self.assertEqual(all_states["K09"], PathState.AVAILABLE)
        self.assertEqual(all_states["K11"], PathState.LOCKED)

        # 验证模型转换
        profile = path_state_service.get_student_path_profile(
            "stu_001", states_file=self.states_file
        )
        self.assertIsInstance(profile, (StudentPathStates, StudentPathProfile))
        self.assertEqual(profile.states["K08"], PathState.COMPLETED)

    def test_04_student_isolation(self):
        """不同学生之间的路径状态物理隔离"""
        path_state_service.set_path_state(
            "stu_001", "K08", PathState.COMPLETED, states_file=self.states_file
        )
        path_state_service.set_path_state(
            "stu_002", "K08", PathState.LOCKED, states_file=self.states_file
        )
        self.assertEqual(
            path_state_service.get_path_state("stu_001", "K08", states_file=self.states_file),
            PathState.COMPLETED,
        )
        self.assertEqual(
            path_state_service.get_path_state("stu_002", "K08", states_file=self.states_file),
            PathState.LOCKED,
        )

    def test_05_init_student_path(self):
        """学生初始路径设置与全量状态获取"""
        initial_states = {
            "K01": PathState.AVAILABLE,
            "K02": PathState.LOCKED,
            "K03": PathState.LOCKED,
        }
        path_state_service.init_student_path(
            "stu_new", initial_states=initial_states, states_file=self.states_file
        )
        states = path_state_service.get_all_path_states("stu_new", states_file=self.states_file)
        self.assertEqual(len(states), 3)
        self.assertEqual(states["K01"], PathState.AVAILABLE)
        self.assertEqual(states["K02"], PathState.LOCKED)
        self.assertEqual(states["K03"], PathState.LOCKED)

    def test_06_concurrent_write_safety(self):
        """多线程并发写入原子性与数据一致性"""
        threads_count = 10
        nodes_per_thread = 5

        def worker(worker_id: int):
            updates = {
                f"K_{worker_id}_{i}": PathState.AVAILABLE if i % 2 == 0 else PathState.IN_PROGRESS
                for i in range(nodes_per_thread)
            }
            path_state_service.set_path_states_bulk(
                f"stu_thread_{worker_id}", updates, states_file=self.states_file
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads_count) as executor:
            futures = [executor.submit(worker, i) for i in range(threads_count)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # 校验所有线程写入的学生与节点均完整落盘无损坏
        with open(self.states_file, "r", encoding="utf-8") as f:
            persisted = json.load(f)

        self.assertEqual(len(persisted), threads_count)
        for i in range(threads_count):
            stu_key = f"stu_thread_{i}"
            self.assertIn(stu_key, persisted)
            self.assertEqual(len(persisted[stu_key]), nodes_per_thread)

    def test_07_physical_isolation_from_bkt(self):
        """严禁写入或影响 data/bkt_states.json，实现物理隔离"""
        bkt_file = Path(self.temp_dir.name) / "bkt_states.json"
        bkt_file.write_text(json.dumps({"dummy": "value"}), encoding="utf-8")

        # 写入路径状态
        path_state_service.set_path_state(
            "stu_iso", "K99", PathState.AVAILABLE, states_file=self.states_file
        )

        # 验证 bkt_states.json 未受任何修改
        bkt_content = json.loads(bkt_file.read_text(encoding="utf-8"))
        self.assertEqual(bkt_content, {"dummy": "value"})
        self.assertNotIn("stu_iso", bkt_content)
