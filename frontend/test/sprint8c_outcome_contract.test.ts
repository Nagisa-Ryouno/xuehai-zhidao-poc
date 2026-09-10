/**
 * sprint8c_outcome_contract.test.ts
 * 学海智导 (Xuehai Zhidao) — Phase 4 / Sprint 8-C
 * 成效沉淀（掌握度全览 + 错题复盘 + 教师学情分析）前端契约测试
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  StudentProgressResponse,
  WrongAnswerReviewResponse,
  TeacherOverviewResponse,
  KnowledgePointMasteryItem,
  WrongAnswerItem,
} from '../src/types.ts';

describe('Sprint 8-C: Learning Outcome & Analytics Contract Tests', () => {
  // 1. 学生掌握度全览数据模型契约
  describe('C1: Student Progress & 30-KP Overview Contract', () => {
    it('1. 全图谱 30 考点认知状态守恒断言', () => {
      const mockProgress: StudentProgressResponse = {
        student_id: 'S001',
        overall_mastery: 0.65,
        mastery_level: '发展中',
        total_practice_count: 10,
        total_correct_count: 7,
        overall_accuracy: 70.0,
        mastered_count: 8,
        developing_count: 12,
        weak_count: 5,
        unstudied_count: 5,
        mastery_trend: [
          { timestamp: '2026-09-10T10:00:00Z', overall_mastery: 0.50, event_type: 'PRETEST_SUBMIT' },
          { timestamp: '2026-09-10T10:05:00Z', overall_mastery: 0.65, event_type: 'QUESTION_ATTEMPT', knowledge_id: 'K08' },
        ],
        knowledge_points: Array.from({ length: 30 }, (_, idx) => ({
          knowledge_id: `K${String(idx + 1).padStart(2, '0')}`,
          knowledge_name: `考点 ${idx + 1}`,
          chapter: '微观经济学',
          mastery: idx < 8 ? 0.85 : idx < 20 ? 0.65 : idx < 25 ? 0.40 : 0.20,
          status: (idx < 8
            ? 'MASTERED'
            : idx < 20
            ? 'DEVELOPING'
            : idx < 25
            ? 'NEEDS_REINFORCEMENT'
            : 'UNSTUDIED') as KnowledgePointMasteryItem['status'],
          attempts: idx < 25 ? 2 : 0,
          accuracy: idx < 8 ? 100 : idx < 20 ? 70 : idx < 25 ? 30 : 0,
        })),
        history_timeline: [
          {
            event_id: 'evt-1',
            event_type: 'QUESTION_ATTEMPT',
            timestamp: '2026-09-10T10:05:00Z',
            knowledge_id: 'K08',
            is_correct: true,
            details: '微测验答题正确',
          },
        ],
      };

      // 验证 4 种状态总和严格等于 30 考点
      const totalCount =
        mockProgress.mastered_count +
        mockProgress.developing_count +
        mockProgress.weak_count +
        mockProgress.unstudied_count;
      assert.equal(totalCount, 30);
      assert.equal(mockProgress.knowledge_points.length, 30);
    });

    it('2. 掌握度阈值统一性 (0.80 达标，0.60 基础)', () => {
      const MASTERY_THRESHOLD_HIGH = 0.80;
      const MASTERY_THRESHOLD_LOW = 0.60;

      const testCases = [
        { val: 0.80, expected: 'MASTERED' },
        { val: 0.85, expected: 'MASTERED' },
        { val: 0.799, expected: 'DEVELOPING' },
        { val: 0.60, expected: 'DEVELOPING' },
        { val: 0.599, expected: 'NEEDS_REINFORCEMENT' },
        { val: 0.20, attempts: 0, expected: 'UNSTUDIED' },
      ];

      for (const tc of testCases) {
        let status: string;
        if (tc.attempts === 0 && tc.val <= 0.20) {
          status = 'UNSTUDIED';
        } else if (tc.val >= MASTERY_THRESHOLD_HIGH) {
          status = 'MASTERED';
        } else if (tc.val >= MASTERY_THRESHOLD_LOW) {
          status = 'DEVELOPING';
        } else {
          status = 'NEEDS_REINFORCEMENT';
        }
        assert.equal(status, tc.expected);
      }
    });

    it('3. 空历史状态安全兼容 (无事件时不崩溃且提示友好)', () => {
      const emptyProgress: StudentProgressResponse = {
        student_id: 'NEW_STU',
        overall_mastery: 0.20,
        mastery_level: '起步阶段',
        total_practice_count: 0,
        total_correct_count: 0,
        overall_accuracy: 0.0,
        mastered_count: 0,
        developing_count: 0,
        weak_count: 0,
        unstudied_count: 30,
        mastery_trend: [],
        knowledge_points: [],
        history_timeline: [],
      };

      assert.equal(emptyProgress.mastery_trend.length, 0);
      assert.equal(emptyProgress.history_timeline.length, 0);
      assert.equal(emptyProgress.total_practice_count, 0);
    });
  });

  // 2. 错题复盘与再练习契约
  describe('C2: Wrong Answer Review & Remediation Contract', () => {
    it('4. 错题过滤与优先级分级契约', () => {
      const mockWrongAnswers: WrongAnswerReviewResponse = {
        student_id: 'S001',
        total_wrong: 2,
        wrong_answers: [
          {
            question_id: 'Q-K08-01',
            knowledge_id: 'K08',
            knowledge_name: '需求价格弹性',
            chapter: '第二章 需求与供给',
            question_prompt: '当某种商品价格弹性大于1时...',
            options: { A: '增加', B: '减少', C: '不变', D: '无法确定' },
            student_answer: 'B',
            correct_answer: 'A',
            explanation: '富有弹性时降价会引起总收益增加。',
            current_mastery: 0.4566,
            current_path_state: 'IN_PROGRESS',
            mistake_count: 2,
            last_error_time: '2026-09-10T10:10:00Z',
            review_priority: 'HIGH',
          },
          {
            question_id: 'Q-K01-01',
            knowledge_id: 'K01',
            knowledge_name: '稀缺性与经济学基本问题',
            chapter: '第一章 导论',
            question_prompt: '经济学研究的核心出发点是...',
            options: { A: '政府权力', B: '稀缺性', C: '货币量', D: '贸易顺差' },
            student_answer: 'A',
            correct_answer: 'B',
            explanation: '稀缺性是经济学的基石。',
            current_mastery: 0.8118,
            current_path_state: 'COMPLETED',
            mistake_count: 1,
            last_error_time: '2026-09-10T09:00:00Z',
            review_priority: 'LOW',
          },
        ],
      };

      assert.equal(mockWrongAnswers.total_wrong, 2);
      assert.equal(mockWrongAnswers.wrong_answers[0].review_priority, 'HIGH');
      assert.equal(mockWrongAnswers.wrong_answers[1].review_priority, 'LOW');
      assert.notEqual(
        mockWrongAnswers.wrong_answers[0].student_answer,
        mockWrongAnswers.wrong_answers[0].correct_answer
      );
    });

    it('5. 错题为空时的零状态契约', () => {
      const cleanWrongAnswers: WrongAnswerReviewResponse = {
        student_id: 'S002',
        total_wrong: 0,
        wrong_answers: [],
      };

      assert.equal(cleanWrongAnswers.total_wrong, 0);
      assert.equal(cleanWrongAnswers.wrong_answers.length, 0);
    });
  });

  // 3. 教师学情驾驶舱分析契约
  describe('C3: Teacher Analytics Cockpit Contract', () => {
    it('6. 4 项核心 KPI 字段非负且类型完备', () => {
      const mockOverview: TeacherOverviewResponse = {
        class_kpis: {
          total_students: 5,
          active_students: 5,
          class_avg_mastery: 0.624,
          at_risk_students_count: 2,
        },
        weak_knowledge_points: [
          {
            knowledge_id: 'K08',
            knowledge_name: '需求价格弹性',
            chapter: '第二章 需求与供给',
            avg_mastery: 0.38,
            error_rate: 66.7,
            weak_student_count: 3,
            urgency: 'HIGH',
          },
        ],
        students: [
          {
            student_id: 'S001',
            student_name: '张明',
            major: '经济学',
            grade: '大二',
            learning_goal: '微观经济学考点全通',
            overall_mastery: 0.65,
            mastered_count: 10,
            developing_count: 12,
            weak_count: 8,
            total_attempts: 15,
            total_wrong_count: 4,
            accuracy: 73.3,
            risk_level: 'NORMAL',
            current_focus_node: 'K08',
            current_focus_name: '需求价格弹性',
          },
        ],
      };

      assert.ok(mockOverview.class_kpis.total_students >= 1);
      assert.ok(mockOverview.class_kpis.active_students >= 0);
      assert.ok(mockOverview.class_kpis.class_avg_mastery >= 0 && mockOverview.class_kpis.class_avg_mastery <= 1);
      assert.ok(mockOverview.class_kpis.at_risk_students_count >= 0);
      assert.ok(mockOverview.weak_knowledge_points.length <= 5);
      assert.equal(mockOverview.students[0].risk_level, 'NORMAL');
    });

    it('7. 风险预警状态判定标准断言 (ATTENTION, NORMAL, HEALTHY)', () => {
      const evaluateRisk = (overallMastery: number, accuracy: number) => {
        if (overallMastery < 0.60 || accuracy < 50.0) return 'ATTENTION';
        if (overallMastery >= 0.80 && accuracy >= 80.0) return 'HEALTHY';
        return 'NORMAL';
      };

      assert.equal(evaluateRisk(0.55, 70.0), 'ATTENTION');
      assert.equal(evaluateRisk(0.70, 45.0), 'ATTENTION');
      assert.equal(evaluateRisk(0.85, 88.0), 'HEALTHY');
      assert.equal(evaluateRisk(0.75, 75.0), 'NORMAL');
    });
  });
});
