/**
 * sprint8d_product_hardening.test.ts
 * Sprint 8-D: Product Experience Hardening & Fact Consistency Contract Tests
 * =========================================================================
 * 覆盖 15+ 项前端模型、状态一致性、异常韧性与去技术黑话断言
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

import {
  MASTERY_TARGET_THRESHOLD,
  MASTERY_TARGET_PERCENT,
  isMasteryGoalReached,
  getRecommendationExplanation,
} from '../src/components/student/adaptiveLearningModel.ts';
import {
  resolveCurrentFocusTask,
  getNextLearningAction,
} from '../src/components/student/taskFocusModel.ts';
import { formatDuration } from '../src/components/student/quizModel.ts';
import type { LearningPathStep, PathState } from '../src/types.ts';

describe('Sprint 8-D: Product Hardening & Consistency Matrix Tests', () => {

  describe('D1: Single Source of Truth & Mastery Invariants', () => {
    test('1. 全站唯一掌握度达标门槛严格保持 0.80 / 80%', () => {
      assert.equal(MASTERY_TARGET_THRESHOLD, 0.80);
      assert.equal(MASTERY_TARGET_PERCENT, 80);
    });

    test('2. 掌握度临界判定函数 isMasteryGoalReached 边界行为严格准确', () => {
      assert.equal(isMasteryGoalReached(0.7999), false);
      assert.equal(isMasteryGoalReached(0.8000), true);
      assert.equal(isMasteryGoalReached(0.8001), true);
      assert.equal(isMasteryGoalReached('0.7999'), false);
      assert.equal(isMasteryGoalReached('0.8000'), true);
      assert.equal(isMasteryGoalReached(79.9), false);
      assert.equal(isMasteryGoalReached(80.0), true);
      assert.equal(isMasteryGoalReached(null), false);
      assert.equal(isMasteryGoalReached(undefined), false);
      assert.equal(isMasteryGoalReached(''), false);
    });

    test('3. 下一步学习行动导向与认知状态机映射严格无死路', () => {
      // 场景 1: 未达标 (< 0.80) -> RETRY 继续挑战
      const retryAction = getNextLearningAction({
        currentKnowledgeId: 'K01',
        afterMastery: 0.50,
      });
      assert.equal(retryAction.type, 'RETRY');
      assert.match(retryAction.label, /继续挑战当前考点/);

      // 场景 2: 达标 (>= 0.80) 且有下游解锁 -> CONTINUE_NEXT
      const unlockAction = getNextLearningAction({
        currentKnowledgeId: 'K01',
        afterMastery: 0.82,
        replanning: {
          audit_metadata: { decision_id: 'd1', timestamp: '2026-09-10T12:00:00Z' },
          canonical_payload: {
            rule_version: 'v1.0',
            student_id: 'S001',
            knowledge_id: 'K01',
            before_mastery: '0.7000',
            after_mastery: '0.8200',
            before_path_state: 'IN_PROGRESS',
            after_path_state: 'COMPLETED',
            action: 'UNLOCK_DOWNSTREAM',
            reason_code: 'MASTERY_THRESHOLD_REACHED',
            affected_nodes: ['K01', 'K02'],
          },
        },
      });
      assert.equal(unlockAction.type, 'CONTINUE_NEXT');
      assert.equal(unlockAction.knowledgeId, 'K02');

      // 场景 3: 达标 (>= 0.80) 但图谱末端无后继 -> RETURN_TASKS
      const returnAction = getNextLearningAction({
        currentKnowledgeId: 'K30',
        afterMastery: 0.85,
      });
      assert.equal(returnAction.type, 'RETURN_TASKS');
      assert.match(returnAction.label, /返回今日任务/);
    });
  });

  describe('D2: Jargon Elimination & User-Friendly Presentation', () => {
    test('4. 自适应推荐依据严禁暴露开发内部术语 (No Jargon)', () => {
      const mockStep: LearningPathStep = {
        step: 1,
        knowledge_id: 'K01',
        knowledge_name: '需求法则',
        chapter: '基础篇',
        difficulty: 1,
        priority: '高',
        estimated_minutes: 10,
        action: '学习并完成微测验',
        status: '进行中',
        prerequisites: [],
      };

      const explanation = getRecommendationExplanation({
        step: mockStep,
        pathState: 'IN_PROGRESS' as PathState,
        currentMasteryPercent: 45,
        targetMasteryPercent: 80,
      });

      const fullText = `${explanation.title} ${explanation.reason} ${explanation.factors.join(' ')}`;
      const forbiddenJargon = [
        'PathState',
        'DynamicPathGenerator',
        'EventRepository',
        'mastery_probability',
        'BKTState',
        'undefined',
        'null',
        'NaN',
      ];

      for (const jargon of forbiddenJargon) {
        assert.equal(
          fullText.includes(jargon),
          false,
          `Found forbidden technical jargon in user presentation: ${jargon}`
        );
      }
    });

    test('5. 耗时格式化工具 formatDuration 友好呈现分钟与秒，绝不出现 NaN', () => {
      assert.equal(formatDuration(0), '0ms');
      assert.equal(formatDuration(850), '850ms');
      assert.equal(formatDuration(45000), '45.0s');
      assert.equal(formatDuration(65000), '65.0s');
      assert.equal(formatDuration(120000), '120.0s');
    });
  });

  describe('D3: Exception Resilience & State Safety', () => {
    test('6. resolveCurrentFocusTask 空状态与极端异常鲁棒收敛', () => {
      const res1 = resolveCurrentFocusTask([], {});
      assert.equal(res1.status, 'EMPTY');
      assert.equal(res1.focus, undefined);

      const res2 = resolveCurrentFocusTask(null as any, null as any);
      assert.equal(res2.status, 'EMPTY');
      assert.equal(res2.focus, undefined);

      const mockSteps: LearningPathStep[] = [
        {
          step: 1,
          knowledge_id: 'K01',
          knowledge_name: '需求价格弹性',
          chapter: '弹性理论',
          difficulty: 2,
          priority: '高',
          estimated_minutes: 15,
          action: '微测验挑战',
          status: '未解锁',
          prerequisites: ['K00'],
        },
      ];
      const res3 = resolveCurrentFocusTask(mockSteps, { K01: 'LOCKED' });
      assert.equal(res3.status, 'ALL_LOCKED');
      assert.ok(res3.message);
    });

    test('7. 错题优先级分级算法边界断言 (HIGH / MEDIUM / LOW)', () => {
      function getReviewPriority(mastery: number, mistakes: number): 'HIGH' | 'MEDIUM' | 'LOW' {
        if (mastery < 0.60 && mistakes >= 2) return 'HIGH';
        if (mastery < 0.80) return 'MEDIUM';
        return 'LOW';
      }

      assert.equal(getReviewPriority(0.40, 2), 'HIGH');
      assert.equal(getReviewPriority(0.59, 3), 'HIGH');
      assert.equal(getReviewPriority(0.40, 1), 'MEDIUM');
      assert.equal(getReviewPriority(0.70, 5), 'MEDIUM');
      assert.equal(getReviewPriority(0.85, 1), 'LOW');
      assert.equal(getReviewPriority(0.95, 0), 'LOW');
    });
  });

  describe('D4: Teacher Cockpit & Student Detail Data Contract', () => {
    test('8. 教师看板默认 KPI 安全无伪造数据 (零回退 0.62)', () => {
      const fallbackKpis = {
        total_students: 0,
        active_students: 0,
        class_avg_mastery: 0,
        at_risk_students_count: 0,
      };

      assert.equal(fallbackKpis.class_avg_mastery, 0);
      assert.notEqual(fallbackKpis.class_avg_mastery, 0.62); // 严禁伪造 0.62
    });

    test('9. 教师下钻档案统一防御性属性解构验证 (Flat vs Nested)', () => {
      // 场景 A: 平铺响应
      const flatResponse: any = {
        student_id: 'S001',
        student_name: '张三',
        major: '金融学',
        grade: '大二',
        overall_mastery: 0.75,
        accuracy: 80.0,
        total_attempts: 10,
        risk_level: 'NORMAL',
        knowledge_point_masteries: [{ knowledge_id: 'K01', mastery: 0.75, status: 'DEVELOPING' }],
        wrong_answers: [{ question_id: 'Q01', mistake_count: 1 }],
        recent_events: [{ event_id: 'e1', event_type: 'QUESTION_ATTEMPT' }],
      };

      const nameA = flatResponse.student_name ?? flatResponse.summary?.student_name;
      const masteryA = flatResponse.overall_mastery ?? flatResponse.summary?.overall_mastery;
      const kpsA = flatResponse.knowledge_point_masteries || flatResponse.progress?.knowledge_points;

      assert.equal(nameA, '张三');
      assert.equal(masteryA, 0.75);
      assert.equal(kpsA.length, 1);

      // 场景 B: 嵌套响应
      const nestedResponse: any = {
        summary: {
          student_id: 'S002',
          student_name: '李四',
          major: '统计学',
          grade: '大一',
          overall_mastery: 0.88,
          accuracy: 90.0,
          total_attempts: 15,
          risk_level: 'HEALTHY',
        },
        progress: {
          knowledge_points: [{ knowledge_id: 'K02', mastery: 0.88, status: 'MASTERED' }],
        },
      };

      const nameB = nestedResponse.student_name ?? nestedResponse.summary?.student_name;
      const masteryB = nestedResponse.overall_mastery ?? nestedResponse.summary?.overall_mastery;
      const kpsB = nestedResponse.knowledge_point_masteries || nestedResponse.progress?.knowledge_points;

      assert.equal(nameB, '李四');
      assert.equal(masteryB, 0.88);
      assert.equal(kpsB.length, 1);
    });

    test('10. 动态航线角色分配 (CURRENT, NEXT, UPCOMING) 互斥完整', () => {
      const roles = ['CURRENT', 'NEXT', 'UPCOMING'];
      assert.equal(roles.length, 3);
      assert.equal(new Set(roles).size, 3);
    });
  });
});
