# -*- coding: utf-8 -*-
"""
test_bkt_service.py
P0-6 动态学情状态建模与 BKT 核心引擎单元测试 (数学模型与纯函数)

覆盖 10 大核心测试用例：
1. 默认参数合法性验证 (P(L0)=0.20, P(T)=0.10, P(G)=0.20, P(S)=0.10)
2. 初始状态工厂验证 (mastery_probability == P(L0), attempts == 0)
3. 单次答对后 mastery 严格上升，且手算数学精确吻合
4. 单次答错后 mastery 严格下降，且手算数学精确吻合
5. 连续答对 mastery 单调递增并趋向上限
6. 连续答错 mastery 单调递减
7. 极端概率边界值与防溢出断言 (mastery 永远在 [0, 1] 闭区间内)
8. 参数合法性校验拦截 (概率必须在 (0, 1) 且 P(G)+P(S) < 1.0)
9. 统计辅助计数正确性 (attempts, correct/incorrect, consecutive counters)
10. 正确率 (accuracy) 与掌握度 (mastery_probability) 的解耦验证
"""

import unittest
import bkt_service


class TestBKTService(unittest.TestCase):

    def test_01_default_parameters(self):
        """Test 1: 验证 BKT 默认参数严格符合设计规范且可配置"""
        params = bkt_service.BKTParameters()
        self.assertAlmostEqual(params.p_l0, 0.20, places=4)
        self.assertAlmostEqual(params.p_t, 0.10, places=4)
        self.assertAlmostEqual(params.p_g, 0.20, places=4)
        self.assertAlmostEqual(params.p_s, 0.10, places=4)

    def test_02_create_initial_state(self):
        """Test 2: 初始状态工厂必须以 P(L0) 为初值，各统计项置零"""
        state = bkt_service.create_initial_state("S001", "K08")
        self.assertEqual(state.student_id, "S001")
        self.assertEqual(state.knowledge_id, "K08")
        self.assertAlmostEqual(state.mastery_probability, 0.20, places=4)
        self.assertEqual(state.attempts, 0)
        self.assertEqual(state.correct_attempts, 0)
        self.assertEqual(state.incorrect_attempts, 0)
        self.assertEqual(state.consecutive_correct, 0)
        self.assertEqual(state.consecutive_incorrect, 0)
        self.assertIsNone(state.last_event_id)
        self.assertIsNone(state.last_updated)

    def test_03_single_correct_attempt_exact_math(self):
        """
        Test 3: 单次答对后 mastery 严格上升，且与手算值精确吻合
        理论手算推导：
        P(L) = 0.20, P(T) = 0.10, P(G) = 0.20, P(S) = 0.10
        P(L|correct) = (0.20 * 0.90) / (0.20 * 0.90 + 0.80 * 0.20)
                     = 0.18 / (0.18 + 0.16) = 0.18 / 0.34 = 9/17 ≈ 0.52941176
        P(L_new) = P(L|correct) + (1 - P(L|correct)) * P(T)
                 = 9/17 + (8/17) * 0.10 = (9 + 0.8) / 17 = 9.8 / 17 ≈ 0.576470588
        """
        initial_prob = 0.20
        new_prob = bkt_service.calculate_bkt_update(initial_prob, is_correct=True)
        expected = 9.8 / 17.0  # ≈ 0.5764705882352941
        self.assertAlmostEqual(new_prob, expected, places=6)
        self.assertGreater(new_prob, initial_prob, "答对后掌握概率必须上升")

    def test_04_single_incorrect_attempt_exact_math(self):
        """
        Test 4: 单次答错后 mastery 严格下降，且与手算值精确吻合
        理论手算推导：
        P(L) = 0.20, P(T) = 0.10, P(G) = 0.20, P(S) = 0.10
        P(L|incorrect) = (0.20 * 0.10) / (0.20 * 0.10 + 0.80 * 0.80)
                       = 0.02 / (0.02 + 0.64) = 0.02 / 0.66 = 1/33 ≈ 0.03030303
        P(L_new) = P(L|incorrect) + (1 - P(L|incorrect)) * P(T)
                 = 1/33 + (32/33) * 0.10 = (1 + 3.2) / 33 = 4.2 / 33 ≈ 0.127272727
        """
        initial_prob = 0.20
        new_prob = bkt_service.calculate_bkt_update(initial_prob, is_correct=False)
        expected = 4.2 / 33.0  # ≈ 0.12727272727272726
        self.assertAlmostEqual(new_prob, expected, places=6)
        self.assertLess(new_prob, initial_prob, "答错后掌握概率必须下降")

    def test_05_consecutive_correct_monotonicity(self):
        """Test 5: 连续答对 5 次，mastery 必须严格单调递增并趋于 1.0"""
        prob = 0.20
        history = [prob]
        for _ in range(5):
            prob = bkt_service.calculate_bkt_update(prob, is_correct=True)
            self.assertGreater(prob, history[-1], "连续答对过程中每一次掌握度都必须增加")
            self.assertLessEqual(prob, 1.0)
            history.append(prob)

        # 5 次全对后掌握度应显著大于 0.90
        self.assertGreater(history[-1], 0.90)

    def test_06_consecutive_incorrect_monotonicity(self):
        """Test 6: 连续答错 5 次，mastery 必须严格单调递减（受转移学习率 P(T) 保底）"""
        prob = 0.80
        history = [prob]
        for _ in range(5):
            prob = bkt_service.calculate_bkt_update(prob, is_correct=False)
            self.assertLess(prob, history[-1], "连续答错过程中每一次掌握度都必须降低")
            self.assertGreaterEqual(prob, 0.0)
            history.append(prob)

    def test_07_extreme_boundary_protection(self):
        """Test 7: 即使输入接近 0 或 1 的极端概率，输出也绝不超出 [0, 1] 区间"""
        for p in [0.0, 0.00001, 0.5, 0.99999, 1.0]:
            next_corr = bkt_service.calculate_bkt_update(p, is_correct=True)
            next_inc = bkt_service.calculate_bkt_update(p, is_correct=False)
            self.assertTrue(0.0 <= next_corr <= 1.0, f"p={p} 答对更新超出边界: {next_corr}")
            self.assertTrue(0.0 <= next_inc <= 1.0, f"p={p} 答错更新超出边界: {next_inc}")

    def test_08_invalid_parameters_validation(self):
        """Test 8: 参数范围不在 (0, 1) 或 P(G)+P(S) >= 1 时必须抛出 ValueError"""
        # 超出 [0, 1] 范围
        with self.assertRaises(ValueError):
            bkt_service.BKTParameters(p_l0=-0.1)
        with self.assertRaises(ValueError):
            bkt_service.BKTParameters(p_t=1.2)
        with self.assertRaises(ValueError):
            bkt_service.BKTParameters(p_g=0.0)
        # 违反 BKT 可识别性 (Identifiability) 条件: P(G) + P(S) 必须 < 1.0 (否则猜测+失误率超过随机水平)
        with self.assertRaises(ValueError):
            bkt_service.BKTParameters(p_g=0.6, p_s=0.5)

    def test_09_apply_attempt_statistics(self):
        """Test 9: apply_attempt 必须正确维护连续答对/答错计数与时间戳"""
        state = bkt_service.create_initial_state("S001", "K08")

        # 第 1 次: 答对
        res1 = bkt_service.apply_attempt(
            state,
            is_correct=True,
            event_id="evt-01",
            timestamp="2026-09-05T20:10:00+08:00",
        )
        s1 = res1.state
        self.assertEqual(s1.attempts, 1)
        self.assertEqual(s1.correct_attempts, 1)
        self.assertEqual(s1.incorrect_attempts, 0)
        self.assertEqual(s1.consecutive_correct, 1)
        self.assertEqual(s1.consecutive_incorrect, 0)
        self.assertEqual(s1.last_event_id, "evt-01")

        # 第 2 次: 答对
        res2 = bkt_service.apply_attempt(
            s1,
            is_correct=True,
            event_id="evt-02",
            timestamp="2026-09-05T20:11:00+08:00",
        )
        s2 = res2.state
        self.assertEqual(s2.attempts, 2)
        self.assertEqual(s2.consecutive_correct, 2)
        self.assertEqual(s2.consecutive_incorrect, 0)

        # 第 3 次: 答错 (清空 consecutive_correct，累加 consecutive_incorrect)
        res3 = bkt_service.apply_attempt(
            s2,
            is_correct=False,
            event_id="evt-03",
            timestamp="2026-09-05T20:12:00+08:00",
        )
        s3 = res3.state
        self.assertEqual(s3.attempts, 3)
        self.assertEqual(s3.correct_attempts, 2)
        self.assertEqual(s3.incorrect_attempts, 1)
        self.assertEqual(s3.consecutive_correct, 0)
        self.assertEqual(s3.consecutive_incorrect, 1)
        self.assertEqual(s3.last_event_id, "evt-03")

    def test_10_accuracy_vs_mastery_decoupling(self):
        """
        Test 10: 验证正确率与掌握概率的严格解耦
        场景：序列 A (错, 错, 对, 对, 对) vs 序列 B (对, 对, 错, 错, 错)
        虽然两者正确率均为 3/5 = 60%，但序列 A 掌握度显著高于序列 B
        """
        # 序列 A
        state_a = bkt_service.create_initial_state("S001", "K08")
        for i, corr in enumerate([False, False, True, True, True]):
            res = bkt_service.apply_attempt(state_a, is_correct=corr, event_id=f"a-{i}", timestamp="t")
            state_a = res.state

        # 序列 B: 同样答对 3 题答错 2 题，但后段滑坡
        state_b = bkt_service.create_initial_state("S002", "K08")
        for i, corr in enumerate([True, True, True, False, False]):
            res = bkt_service.apply_attempt(state_b, is_correct=corr, event_id=f"b-{i}", timestamp="t")
            state_b = res.state

        # 表面正确率完全相同
        acc_a = state_a.correct_attempts / state_a.attempts
        acc_b = state_b.correct_attempts / state_b.attempts
        self.assertAlmostEqual(acc_a, acc_b, places=4)
        self.assertAlmostEqual(acc_a, 0.60, places=4)

        # 但 BKT 掌握概率序列 A (后段成长) 必须明显高于 序列 B (后段遗忘/滑坡)
        self.assertGreater(
            state_a.mastery_probability,
            state_b.mastery_probability,
            f"序列 A 掌握度 ({state_a.mastery_probability:.4f}) 必须高于 序列 B ({state_b.mastery_probability:.4f})",
        )


if __name__ == "__main__":
    unittest.main()
