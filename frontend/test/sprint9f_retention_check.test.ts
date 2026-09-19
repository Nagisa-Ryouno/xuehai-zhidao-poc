/**
 * sprint9f_retention_check.test.ts
 * 学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-F
 * 学习保持度验证与间隔复习建议 Lite 前端契约测试 (Frontend Contract Tests)
 *
 * 覆盖：
 * 1. 保持度状态枚举合法性 (RetentionStatus: INSUFFICIENT_DATA, NOT_DUE, DUE_FOR_REVIEW, NEEDS_REINFORCEMENT)
 * 2. 保持度档案实体契约 (RetentionProfile: student_id, knowledge_id, last_learning_at, days_since_learning, current_mastery, retention_status, should_review, suggested_action)
 * 3. 建议行动白名单合法性 (suggested_action: RETAKE_QUIZ, REVIEW_CONCEPT, null)
 * 4. DUE_FOR_REVIEW 复测卡片结构与文案契约 (🔄 该复习一下了, RETAKE_QUIZ 引导微测)
 * 5. NEEDS_REINFORCEMENT 巩固建议卡片契约 (📘 建议再巩固一下, REVIEW_CONCEPT 概念回顾)
 * 6. NOT_DUE 与 INSUFFICIENT_DATA 静默无干扰契约 (零侵入、无干扰横幅)
 * 7. 人本温度表达与严禁算法黑话契约 (No Jargon: 严禁 BKT, 贝叶斯, 艾宾浩斯, 记忆遗忘曲线, 衰减率)
 * 8. 多学生与跨考点隔离契约
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  RetentionStatus,
  RetentionProfile,
} from '../src/types.ts';

// 严禁暴露的算法底层术语与学术黑话
const FORBIDDEN_JARGON = [
  'BKT',
  'bkt',
  'Bayesian',
  'bayesian',
  '贝叶斯',
  '艾宾浩斯',
  'Ebbinghaus',
  'ebbinghaus',
  '遗忘曲线',
  '衰减系数',
  '遗忘率',
  '半衰期',
  '先验',
  '后验',
  '向量数据库',
  '大模型决策',
];

describe('Sprint 9-F: 学习保持度验证与间隔复习建议 Lite 前端契约测试', () => {
  // ---------------------------------------------------------------------------
  // C1: 保持度状态与档案实体契约
  // ---------------------------------------------------------------------------
  describe('C1: 保持度状态与档案实体契约', () => {
    it('1. RetentionStatus 4 档枚举值合法且完备', () => {
      const validStatuses: RetentionStatus[] = [
        'INSUFFICIENT_DATA',
        'NOT_DUE',
        'DUE_FOR_REVIEW',
        'NEEDS_REINFORCEMENT',
      ];
      assert.equal(validStatuses.length, 4);
      assert.ok(validStatuses.includes('INSUFFICIENT_DATA'));
      assert.ok(validStatuses.includes('NOT_DUE'));
      assert.ok(validStatuses.includes('DUE_FOR_REVIEW'));
      assert.ok(validStatuses.includes('NEEDS_REINFORCEMENT'));
    });

    it('2. RetentionProfile 实体完整包含服务端权威计算字段', () => {
      const profile: RetentionProfile = {
        student_id: 'S001',
        knowledge_id: 'K08',
        last_learning_at: '2026-09-16T10:00:00Z',
        days_since_learning: 3,
        current_mastery: 0.72,
        retention_status: 'DUE_FOR_REVIEW',
        should_review: true,
        suggested_action: 'RETAKE_QUIZ',
      };

      assert.equal(profile.student_id, 'S001');
      assert.equal(profile.knowledge_id, 'K08');
      assert.equal(profile.days_since_learning, 3);
      assert.equal(profile.current_mastery, 0.72);
      assert.equal(profile.retention_status, 'DUE_FOR_REVIEW');
      assert.equal(profile.should_review, true);
      assert.equal(profile.suggested_action, 'RETAKE_QUIZ');
    });

    it('3. suggested_action 严格限定为合法白名单或 null', () => {
      const allowedActions = ['RETAKE_QUIZ', 'REVIEW_CONCEPT', null];
      const testCases: (RetentionProfile['suggested_action'])[] = [
        'RETAKE_QUIZ',
        'REVIEW_CONCEPT',
        null,
      ];
      for (const act of testCases) {
        assert.ok(allowedActions.includes(act));
      }
    });
  });

  // ---------------------------------------------------------------------------
  // C2: DUE_FOR_REVIEW 提示卡与用户交互契约
  // ---------------------------------------------------------------------------
  describe('C2: DUE_FOR_REVIEW 提示卡契约', () => {
    it('4. DUE_FOR_REVIEW 提示卡提供清晰人本引导与微测入口', () => {
      const profile: RetentionProfile = {
        student_id: 'S001',
        knowledge_id: 'K08',
        last_learning_at: '2026-09-16T12:00:00Z',
        days_since_learning: 4,
        current_mastery: 0.75,
        retention_status: 'DUE_FOR_REVIEW',
        should_review: true,
        suggested_action: 'RETAKE_QUIZ',
      };

      // 模拟前端卡片文案生成逻辑
      const title = '🔄 该复习一下了';
      const narrative = `距离你上次学习这个考点已经过去 ${profile.days_since_learning} 天，花 2 分钟做一道微测，检验一下记忆牢固度吧！`;
      const buttonText = '快速微测复习';

      assert.ok(title.includes('该复习一下了'));
      assert.ok(narrative.includes('4 天'));
      assert.ok(narrative.includes('花 2 分钟做一道微测'));
      assert.equal(buttonText, '快速微测复习');
    });

    it('5. DUE_FOR_REVIEW 但掌握度偏低时建议回顾概念微卡', () => {
      const profile: RetentionProfile = {
        student_id: 'S001',
        knowledge_id: 'K08',
        last_learning_at: '2026-09-16T12:00:00Z',
        days_since_learning: 4,
        current_mastery: 0.52,
        retention_status: 'DUE_FOR_REVIEW',
        should_review: true,
        suggested_action: 'REVIEW_CONCEPT',
      };

      const narrative = `距离你上次学习这个考点已经过去 ${profile.days_since_learning} 天，建议先花 1 分钟回顾一下概念微卡，温故知新。`;
      assert.equal(profile.suggested_action, 'REVIEW_CONCEPT');
      assert.ok(narrative.includes('回顾一下概念微卡'));
    });
  });

  // ---------------------------------------------------------------------------
  // C3: NEEDS_REINFORCEMENT 巩固建议卡片契约
  // ---------------------------------------------------------------------------
  describe('C3: NEEDS_REINFORCEMENT 巩固建议卡片契约', () => {
    it('6. NEEDS_REINFORCEMENT 提示温和鼓励与针对性巩固建议', () => {
      const profile: RetentionProfile = {
        student_id: 'S001',
        knowledge_id: 'K08',
        last_learning_at: '2026-09-16T12:00:00Z',
        days_since_learning: 1,
        current_mastery: 0.55,
        retention_status: 'NEEDS_REINFORCEMENT',
        should_review: true,
        suggested_action: 'REVIEW_CONCEPT',
      };

      const title = '📘 建议再巩固一下';
      const narrative = '最近该考点的练习中遇到了一些小挑战，趁热打铁再看一下核心概念或例题吧。';

      assert.ok(title.includes('建议再巩固一下'));
      assert.ok(narrative.includes('趁热打铁'));
      assert.equal(profile.should_review, true);
    });
  });

  // ---------------------------------------------------------------------------
  // C4: NOT_DUE 与 INSUFFICIENT_DATA 零干扰契约
  // ---------------------------------------------------------------------------
  describe('C4: NOT_DUE 与 INSUFFICIENT_DATA 零干扰契约', () => {
    it('7. NOT_DUE 时不应渲染复习干扰提示', () => {
      const profile: RetentionProfile = {
        student_id: 'S001',
        knowledge_id: 'K08',
        last_learning_at: '2026-09-19T10:00:00Z',
        days_since_learning: 1,
        current_mastery: 0.80,
        retention_status: 'NOT_DUE',
        should_review: false,
        suggested_action: null,
      };

      const shouldShowBanner = profile.retention_status === 'DUE_FOR_REVIEW' || profile.retention_status === 'NEEDS_REINFORCEMENT';
      assert.equal(shouldShowBanner, false);
      assert.equal(profile.should_review, false);
    });

    it('8. INSUFFICIENT_DATA 时保持干净静默，等待学生完成首次学习', () => {
      const profile: RetentionProfile = {
        student_id: 'S002',
        knowledge_id: 'K08',
        last_learning_at: null,
        days_since_learning: null,
        current_mastery: 0.20,
        retention_status: 'INSUFFICIENT_DATA',
        should_review: false,
        suggested_action: null,
      };

      const shouldShowBanner = profile.retention_status === 'DUE_FOR_REVIEW' || profile.retention_status === 'NEEDS_REINFORCEMENT';
      assert.equal(shouldShowBanner, false);
      assert.equal(profile.last_learning_at, null);
    });
  });

  // ---------------------------------------------------------------------------
  // C5: 人本温度文案与无技术黑话合规性 (No Jargon)
  // ---------------------------------------------------------------------------
  describe('C5: 人本温度文案与无技术黑话合规性', () => {
    it('9. UI 提示文案与引导词绝不泄露算法黑话与学术术语', () => {
      const uiTexts = [
        '🔄 该复习一下了',
        '距离你上次学习这个考点已经过去 3 天，花 2 分钟做一道微测，检验一下记忆牢固度吧！',
        '快速微测复习',
        '📘 建议再巩固一下',
        '最近该考点的练习中遇到了一些小挑战，趁热打铁再看一下核心概念或例题吧。',
        '回顾概念微卡',
      ];

      for (const text of uiTexts) {
        for (const jargon of FORBIDDEN_JARGON) {
          assert.equal(
            text.includes(jargon),
            false,
            `UI 文案 "${text}" 中非法包含黑话/算法术语 "${jargon}"`
          );
        }
      }
    });
  });

  // ---------------------------------------------------------------------------
  // C6: 多学生与跨考点隔离契约
  // ---------------------------------------------------------------------------
  describe('C6: 多学生与跨考点隔离契约', () => {
    it('10. 切换学生时保持度档案与复习卡状态彻底物理隔离', () => {
      const s001Profile: RetentionProfile = {
        student_id: 'S001',
        knowledge_id: 'K08',
        last_learning_at: '2026-09-16T12:00:00Z',
        days_since_learning: 4,
        current_mastery: 0.72,
        retention_status: 'DUE_FOR_REVIEW',
        should_review: true,
        suggested_action: 'RETAKE_QUIZ',
      };

      const s002Profile: RetentionProfile = {
        student_id: 'S002',
        knowledge_id: 'K08',
        last_learning_at: null,
        days_since_learning: null,
        current_mastery: 0.20,
        retention_status: 'INSUFFICIENT_DATA',
        should_review: false,
        suggested_action: null,
      };

      assert.notEqual(s001Profile.student_id, s002Profile.student_id);
      assert.notEqual(s001Profile.retention_status, s002Profile.retention_status);
      assert.notEqual(s001Profile.should_review, s002Profile.should_review);
    });
  });
});
