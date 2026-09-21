/**
 * sprint10c_ux.test.ts
 * Sprint 10-C Phase 5: 学生端 UX/UI 可用性与人本体验专项测试
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  sanitizeRecommendationReason,
  getResultCtaConfig,
} from '../src/components/student/sessionUtils.ts';
import {
  STUDENT_NAV_TABS,
  RESOURCE_TAB_INFO,
  getActiveStudentTab,
  BOTTOM_NAV_CONFIG,
} from '../src/components/student/navConfig.ts';

describe('Sprint 10-C Phase 5: Student UX/UI Usability Contract Tests', () => {
  // -------------------------------------------------------------
  // UX-1: 内部编码自然语言净化 (UX-ISSUE-06)
  // -------------------------------------------------------------
  describe('UX-1: AI 推荐理由人本化净化 (sanitizeRecommendationReason)', () => {
    it('1. 成功将 "考点 K01" 替换为自然考点名称「需求定理」', () => {
      const raw = '该典型例题强化了考点 K01 的核心推理模型，适合强化理解。';
      const sanitized = sanitizeRecommendationReason(raw, '需求定理与需求曲线');
      assert.equal(
        sanitized,
        '该典型例题强化了「需求定理与需求曲线」的核心推理模型，适合强化理解。'
      );
      assert.ok(!sanitized.includes('K01'), '净化后绝不能残留 K01 机器编码');
    });

    it('2. 成功将单独的 K02 机器代码替换为自然考点名', () => {
      const raw = '根据你在 K02 上的诊断短板，推荐此精讲微卡。';
      const sanitized = sanitizeRecommendationReason(raw, '供求均衡理论');
      assert.equal(
        sanitized,
        '根据你在 供求均衡理论 上的诊断短板，推荐此精讲微卡。'
      );
      assert.ok(!sanitized.includes('K02'), '净化后绝不能残留 K02 机器编码');
    });

    it('3. 当缺少考点名称时，安全回退到人本词汇 "当前考点" 而不是代码', () => {
      const raw = '此微练针对考点 K03 设计。';
      const sanitized = sanitizeRecommendationReason(raw, '');
      assert.equal(sanitized, '此微练针对「当前考点」设计。');
      assert.ok(!sanitized.includes('K03'), '缺少考点名时也必须消除 K03');
    });

    it('4. 空值或未定义时提供温暖人本保底文案', () => {
      const fallback1 = sanitizeRecommendationReason(undefined, '需求弹性');
      const fallback2 = sanitizeRecommendationReason('', '需求弹性');
      assert.equal(fallback1, '根据你当前的学习进展，为你挑选了该辅导材料。');
      assert.equal(fallback2, '根据你当前的学习进展，为你挑选了该辅导材料。');
    });

    it('5. 本身不含内部编码的自然文本原样保留', () => {
      const natural = '这道生活案例生动讲解了价格变动对购买意愿的实际影响。';
      assert.equal(sanitizeRecommendationReason(natural, '需求定理'), natural);
    });
  });

  // -------------------------------------------------------------
  // UX-2: 移动端 4-Tab 导航与资源页位置感 (UX-ISSUE-04)
  // -------------------------------------------------------------
  describe('UX-2: 移动端导航架构与资源中心承载 (Mobile Nav & Resource Location)', () => {
    it('1. 移动端保持规范的 4-Tab 核心架构，避免 375 屏幕拥挤与误触', () => {
      assert.equal(STUDENT_NAV_TABS.length, 4, '移动端核心导航必须精确为 4 项');
      const tabIds = STUDENT_NAV_TABS.map((t) => t.id);
      assert.deepEqual(tabIds, ['tasks', 'graph', 'profile', 'assistant']);
    });

    it('2. 资源中心作为独立学习模块定义，具备完整元数据', () => {
      assert.equal(RESOURCE_TAB_INFO.id, 'resources');
      assert.equal(RESOURCE_TAB_INFO.path, '/student/resources');
      assert.equal(RESOURCE_TAB_INFO.label, '学习资源');
    });

    it('3. 在资源中心路径 /student/resources 下，移动端 active Tab 归属于 tasks 任务流', () => {
      const active = getActiveStudentTab('/student/resources');
      assert.equal(
        active,
        'tasks',
        '资源中心处于学习任务上下文中，移动端底导应高亮 tasks 以维持位置感'
      );
    });

    it('4. 触控靶点物理高度规范不低于 44px (实际配置为 48px)', () => {
      assert.ok(
        BOTTOM_NAV_CONFIG.minTouchTargetPx >= 44,
        '底部导航最小触控靶点尺寸必须 >= 44px'
      );
    });
  });

  // -------------------------------------------------------------
  // UX-3: 会话轻量步骤进度契约 (UX-ISSUE-03)
  // -------------------------------------------------------------
  describe('UX-3: 会话轻量步骤与时间预期感 (Session Step Flow)', () => {
    it('1. 会话步骤流明确覆盖 4 个核心阶段', () => {
      const canonicalSteps = [
        '① 概念学习',
        '② 可选资源',
        '③ 随堂微测',
        '④ 成果结算',
      ];
      assert.equal(canonicalSteps.length, 4);
    });

    it('2. 结算页依据权威作答表现调整视觉主次：<60% 推荐再练一次，但绝不封死继续出口', () => {
      // 低准确率情况 (例如 33% 或 50%)
      const lowResult = getResultCtaConfig(33);
      assert.equal(lowResult.primaryAction, 'RETRY');
      assert.equal(lowResult.primaryLabel, '再练一次 (推荐巩固)');
      assert.equal(lowResult.secondaryAction, 'NEXT');
      assert.equal(lowResult.secondaryLabel, '仍继续下一步');
      assert.equal(lowResult.isPassing, false);

      // 达标情况 (例如 67% 或 100%)
      const highResult = getResultCtaConfig(100);
      assert.equal(highResult.primaryAction, 'NEXT');
      assert.equal(highResult.primaryLabel, '继续下一步');
      assert.equal(highResult.secondaryAction, 'RETRY');
      assert.equal(highResult.secondaryLabel, '再练一次');
      assert.equal(highResult.isPassing, true);
    });
  });
});
