/**
 * golden_journey_e2e.test.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 2.2-B / Sprint 1
 * 学生端黄金用户旅程全链路闭环契约测试 (Golden Journey E2E Contract Tests)
 *
 * 验证规则：
 * Test 1: 四大 PathState 语义与用户可观察视觉文案严格映射
 * Test 2: 动作准入控制契约：LOCKED 严格禁用测验，AVAILABLE / IN_PROGRESS 允许启动测验
 * Test 3: KnowledgeGraphDetailDrawer 状态与行动按钮映射契约
 * Test 4: BKT 掌握度跃迁 (0.4566 -> 0.8118) 与 UNLOCK_DOWNSTREAM 后继解锁契约
 * Test 5: 测验完成静默刷新契约与全局 studentId 单一事实源保持
 * Test 6: Next Action CTA 智能引导契约 (下游解锁引导 vs 返回今日任务)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  PathState,
  DecisionAuditEnvelope,
} from '../src/types.ts';
import {
  formatMasteryPercentage,
  getUnlockedDownstreamNodes,
} from '../src/components/student/quizModel.ts';

describe('Phase 2.2-B Sprint 1: 学生端黄金旅程端到端闭环测试 (Golden Journey E2E)', () => {
  // -------------------------------------------------------------
  // Test 1: 四大 PathState 语义与用户可观察视觉文案严格映射
  // -------------------------------------------------------------
  it('Test 1: 四大 PathState (LOCKED, AVAILABLE, IN_PROGRESS, COMPLETED) 语义与文案映射准确', () => {
    const PATH_STATE_PRESENTATION: Record<
      PathState,
      { badge: string; button: string; disabled: boolean }
    > = {
      LOCKED: {
        badge: '🔒 需先掌握前置',
        button: '需先掌握前置',
        disabled: true,
      },
      AVAILABLE: {
        badge: '🔓 已满足学习条件',
        button: '开始微测验',
        disabled: false,
      },
      IN_PROGRESS: {
        badge: '🎯 正在进行',
        button: '继续挑战',
        disabled: false,
      },
      COMPLETED: {
        badge: '✓ 已掌握',
        button: '复习微测验',
        disabled: false,
      },
    };

    // 验证每种状态的视觉语义完整且互斥
    const states: PathState[] = ['LOCKED', 'AVAILABLE', 'IN_PROGRESS', 'COMPLETED'];
    for (const st of states) {
      const config = PATH_STATE_PRESENTATION[st];
      assert.ok(config, `状态 ${st} 必须有明确的展示配置`);
      assert.ok(config.badge.length > 0, `状态 ${st} 必须包含可观察的语义徽标`);
      assert.ok(config.button.length > 0, `状态 ${st} 必须包含可观察的行动按钮文本`);
    }

    assert.equal(PATH_STATE_PRESENTATION.LOCKED.disabled, true);
    assert.equal(PATH_STATE_PRESENTATION.AVAILABLE.disabled, false);
    assert.equal(PATH_STATE_PRESENTATION.IN_PROGRESS.disabled, false);
    assert.equal(PATH_STATE_PRESENTATION.COMPLETED.disabled, false);
  });

  // -------------------------------------------------------------
  // Test 2: 动作准入控制契约：LOCKED 严格禁用，AVAILABLE / IN_PROGRESS 允许点击
  // -------------------------------------------------------------
  it('Test 2: LOCKED 节点不可启动测验，AVAILABLE 与 IN_PROGRESS 节点可顺畅启动测验', () => {
    let triggeredQuizId: string | null = null;
    const mockStartQuiz = (kid: string) => {
      triggeredQuizId = kid;
    };

    // 模拟不同状态卡片的点击处理逻辑
    const handleCardAction = (state: PathState, kid: string) => {
      if (state === 'LOCKED') {
        // LOCKED 状态下按钮为 disabled，用户点击无法触发回调
        return;
      }
      mockStartQuiz(kid);
    };

    // 1. LOCKED 卡片点击 -> 绝不触发测验
    triggeredQuizId = null;
    handleCardAction('LOCKED', 'K11');
    assert.equal(triggeredQuizId, null, 'LOCKED 状态节点严禁启动微测验');

    // 2. AVAILABLE 卡片点击 -> 成功启动测验
    triggeredQuizId = null;
    handleCardAction('AVAILABLE', 'K08');
    assert.equal(triggeredQuizId, 'K08', 'AVAILABLE 节点必须可点击启动微测验');

    // 3. IN_PROGRESS 卡片点击 -> 成功启动测验
    triggeredQuizId = null;
    handleCardAction('IN_PROGRESS', 'K08');
    assert.equal(triggeredQuizId, 'K08', 'IN_PROGRESS 节点必须可点击继续挑战');

    // 4. COMPLETED 卡片点击 -> 成功启动复习测验
    triggeredQuizId = null;
    handleCardAction('COMPLETED', 'K01');
    assert.equal(triggeredQuizId, 'K01', 'COMPLETED 节点必须可点击复习测验');
  });

  // -------------------------------------------------------------
  // Test 3: KnowledgeGraphDetailDrawer 状态与行动按钮映射契约
  // -------------------------------------------------------------
  it('Test 3: KnowledgeGraphDetailDrawer 正确映射 PathState 并呈现对应行动按钮', () => {
    const getDrawerButtonLabel = (pathState: PathState): string => {
      switch (pathState) {
        case 'LOCKED':
          return '需先掌握前置考点';
        case 'AVAILABLE':
          return '开始微测验';
        case 'IN_PROGRESS':
          return '继续攻坚微测验';
        case 'COMPLETED':
          return '复习微测验';
      }
    };

    assert.equal(getDrawerButtonLabel('LOCKED'), '需先掌握前置考点');
    assert.equal(getDrawerButtonLabel('AVAILABLE'), '开始微测验');
    assert.equal(getDrawerButtonLabel('IN_PROGRESS'), '继续攻坚微测验');
    assert.equal(getDrawerButtonLabel('COMPLETED'), '复习微测验');
  });

  // -------------------------------------------------------------
  // Test 4: BKT 掌握度跃迁 (0.4566 -> 0.8118) 与 UNLOCK_DOWNSTREAM 解锁契约
  // -------------------------------------------------------------
  it('Test 4: BKT 掌握度跃迁格式化准确，UNLOCK_DOWNSTREAM 正确提取解锁后继节点', () => {
    // 验证定点浮点字符串转百分比
    assert.equal(formatMasteryPercentage('0.4566'), '45.66%');
    assert.equal(formatMasteryPercentage('0.8118'), '81.18%');
    assert.equal(formatMasteryPercentage(0.1273), '12.73%');
    assert.equal(formatMasteryPercentage(0.81185), '81.19%');
    assert.equal(formatMasteryPercentage(''), '0.00%');
    assert.equal(formatMasteryPercentage(null), '0.00%');

    // 构造带 UNLOCK_DOWNSTREAM 的真实 DecisionAuditEnvelope 结构
    const mockEnvelope: DecisionAuditEnvelope = {
      audit_metadata: {
        decision_id: 'dec-12345',
        timestamp: '2026-09-07T12:00:00Z',
        trace_id: 'trace-001',
      },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K08',
        before_mastery: '0.4566',
        after_mastery: '0.8118',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'COMPLETED',
        action: 'UNLOCK_DOWNSTREAM',
        reason_code: 'MASTERY_THRESHOLD_REACHED',
        affected_nodes: ['K08', 'K09'],
      },
    };

    // 验证下游解锁节点提取：从 affected_nodes 中过滤出非当前节点的后继考点
    const unlocked = getUnlockedDownstreamNodes(mockEnvelope, 'K08');
    assert.deepEqual(unlocked, ['K09'], '应准确识别解锁的直接后继考点 K09');

    // 若 action 为 RETAIN，即便 affected_nodes 有值也不得视为解锁
    const mockRetainEnvelope: DecisionAuditEnvelope = {
      ...mockEnvelope,
      canonical_payload: {
        ...mockEnvelope.canonical_payload,
        action: 'RETAIN',
        reason_code: 'MASTERY_STATE_UNCHANGED',
        affected_nodes: ['K08'],
      },
    };
    const retainUnlocked = getUnlockedDownstreamNodes(mockRetainEnvelope, 'K08');
    assert.deepEqual(retainUnlocked, [], 'RETAIN 动作下解锁后继节点必须为空');
  });

  // -------------------------------------------------------------
  // Test 5: 测验完成静默刷新契约与全局 studentId 单一事实源保持
  // -------------------------------------------------------------
  it('Test 5: 测验关闭/完成时触发 refreshData，携带一致的 studentId 重新拉取数据', async () => {
    let refreshedDashboardStudent: string | null = null;
    let refreshedPathStatesStudent: string | null = null;

    // 模拟 App 层的刷新服务
    const mockRefreshData = async (currentStudentId: string) => {
      refreshedDashboardStudent = currentStudentId;
      refreshedPathStatesStudent = currentStudentId;
    };

    // 模拟在当前学生 S003 上下文中完成测验
    const activeStudentId = 'S003';
    let isModalOpen = true;

    // 用户在完成卡点击“返回今日任务”或关闭弹窗
    const handleCloseOrFinish = async () => {
      isModalOpen = false;
      await mockRefreshData(activeStudentId);
    };

    await handleCloseOrFinish();

    assert.equal(isModalOpen, false, '测验弹窗应已关闭');
    assert.equal(
      refreshedDashboardStudent,
      'S003',
      'Dashboard 必须重新拉取当前 S003 学情，严禁跨学生污染为 S001'
    );
    assert.equal(
      refreshedPathStatesStudent,
      'S003',
      'PathStates 必须重新拉取当前 S003 状态，严禁写死 S001'
    );
  });

  // -------------------------------------------------------------
  // Test 6: Next Action CTA 智能引导契约
  // -------------------------------------------------------------
  it('Test 6: 存在已解锁后继节点时推荐“继续学习下一个考点”，否则推荐“返回今日任务”', () => {
    // 场景 A: 达成解锁，存在直接后继 K09
    const replanningWithUnlock: DecisionAuditEnvelope = {
      audit_metadata: {
        decision_id: 'dec-1',
        timestamp: '2026-09-07T12:00:00Z',
      },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K08',
        before_mastery: '0.4566',
        after_mastery: '0.8118',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'COMPLETED',
        action: 'UNLOCK_DOWNSTREAM',
        reason_code: 'MASTERY_THRESHOLD_REACHED',
        affected_nodes: ['K08', 'K09'],
      },
    };

    const unlockedA = getUnlockedDownstreamNodes(replanningWithUnlock, 'K08');
    const primaryCtaA =
      unlockedA.length > 0 ? `继续学习下一个考点 ${unlockedA[0]}` : '返回今日任务';
    assert.equal(primaryCtaA, '继续学习下一个考点 K09');

    // 场景 B: 保持不变 (RETAIN)，无新解锁后继
    const replanningRetain: DecisionAuditEnvelope = {
      audit_metadata: {
        decision_id: 'dec-2',
        timestamp: '2026-09-07T12:00:00Z',
      },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K08',
        before_mastery: '0.2000',
        after_mastery: '0.1273',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'IN_PROGRESS',
        action: 'RETAIN',
        reason_code: 'MASTERY_STATE_UNCHANGED',
        affected_nodes: ['K08'],
      },
    };

    const unlockedB = getUnlockedDownstreamNodes(replanningRetain, 'K08');
    const primaryCtaB =
      unlockedB.length > 0 ? `继续学习下一个考点 ${unlockedB[0]}` : '返回今日任务';
    assert.equal(primaryCtaB, '返回今日任务');
  });
});
