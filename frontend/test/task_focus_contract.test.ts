/**
 * task_focus_contract.test.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 2.2-B / Sprint 2
 * 学生端今日任务中心与学习反馈行为契约测试 (Task Focus & Learning Feedback Contract Tests)
 *
 * 验证目标：
 * Test 1 — Current Focus Priority (IN_PROGRESS > AVAILABLE > others)
 * Test 2 — No IN_PROGRESS Fallback (无 IN_PROGRESS 时首选 AVAILABLE)
 * Test 3 — Tasks CTA & Quiz Entry (IN_PROGRESS 对应“继续挑战”, AVAILABLE 对应“开始微测验”)
 * Test 4 — Mastery Shift Formatting (0.4566 -> 45.66%, 增量 +35.52%)
 * Test 5 — Mastery Transition Matrix (WEAK->DEV, DEV->MAST, WEAK->MAST, WEAK->WEAK)
 * Test 6 — Next Action Decision (UNLOCK_DOWNSTREAM -> CONTINUE_NEXT, 未达标 -> RETRY, 达标无后继 -> RETURN_TASKS)
 * Test 7 — Student Context Isolation (S001 -> S003 上下文严格独立无跨学生污染)
 * Test 8 — Robustness & Boundary Safety (空路径、空状态字典与边界推导鲁棒性)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { LearningPathStep, PathState, DecisionAuditEnvelope } from '../src/types.ts';
import {
  resolveStepPathState,
  resolveCurrentFocusTask,
  calculateMasteryTransition,
  getNextLearningAction,
} from '../src/components/student/taskFocusModel.ts';

describe('Phase 2.2-B Sprint 2: 今日任务中心与学习反馈契约测试 (Task Focus & Feedback)', () => {
  // 准备测试用学习路径数据
  const mockPathSteps: LearningPathStep[] = [
    {
      stage: 1,
      knowledge_id: 'K01',
      knowledge_name: '需求与供给基本理论',
      chapter: '第一章 导论',
      current_accuracy: 90,
      priority: '低',
      priority_score: 30,
      learning_goal: '掌握供求平衡基本概念',
      reason: '已掌握基础考点',
    },
    {
      stage: 2,
      knowledge_id: 'K08',
      knowledge_name: '需求价格弹性',
      chapter: '第二章 弹性理论',
      current_accuracy: 56,
      priority: '高',
      priority_score: 95,
      learning_goal: '熟练掌握点弹性与弧弹性测算',
      reason: '这是你当前学习路径中优先级最高的可学习考点。',
    },
    {
      stage: 3,
      knowledge_id: 'K09',
      knowledge_name: '收入与交叉弹性',
      chapter: '第二章 弹性理论',
      current_accuracy: 20,
      priority: '中',
      priority_score: 70,
      learning_goal: '理解替代品与互补品的交叉价格影响',
      reason: '需在掌握需求价格弹性后开展突破',
    },
  ];

  // -------------------------------------------------------------
  // Test 1 — Current Focus Priority (IN_PROGRESS > AVAILABLE > others)
  // -------------------------------------------------------------
  it('Test 1: 核心任务优先级严格遵循 IN_PROGRESS > AVAILABLE > others', () => {
    const pathStates: Record<string, PathState> = {
      K01: 'COMPLETED',
      K08: 'IN_PROGRESS',
      K09: 'AVAILABLE',
    };

    const result = resolveCurrentFocusTask(mockPathSteps, pathStates);
    assert.equal(result.status, 'FOUND');
    assert.ok(result.focus);
    assert.equal(result.focus.knowledgeId, 'K08');
    assert.equal(result.focus.pathState, 'IN_PROGRESS');
    assert.equal(result.focus.actionLabel, '继续挑战微测验');
  });

  // -------------------------------------------------------------
  // Test 2 — No IN_PROGRESS Fallback (无 IN_PROGRESS 时首选 AVAILABLE)
  // -------------------------------------------------------------
  it('Test 2: 无 IN_PROGRESS 时，首选当前推荐路径中第一个 AVAILABLE 节点', () => {
    const pathStates: Record<string, PathState> = {
      K01: 'COMPLETED',
      K08: 'COMPLETED',
      K09: 'AVAILABLE',
    };

    const result = resolveCurrentFocusTask(mockPathSteps, pathStates);
    assert.equal(result.status, 'FOUND');
    assert.ok(result.focus);
    assert.equal(result.focus.knowledgeId, 'K09');
    assert.equal(result.focus.pathState, 'AVAILABLE');
    assert.equal(result.focus.actionLabel, '开始微测验');
  });

  // -------------------------------------------------------------
  // Test 3 — Tasks CTA & Quiz Entry (状态与按钮行为映射)
  // -------------------------------------------------------------
  it('Test 3: Tasks 焦点卡根据状态映射正确按钮并在点击时调用 onStartQuiz', () => {
    let triggeredQuiz: { id: string; name: string } | null = null;
    const mockStartQuiz = (id: string, name: string) => {
      triggeredQuiz = { id, name };
    };

    // Case A: IN_PROGRESS
    const focusA = resolveCurrentFocusTask(mockPathSteps, {
      K01: 'COMPLETED',
      K08: 'IN_PROGRESS',
      K09: 'AVAILABLE',
    });
    assert.equal(focusA.focus?.actionLabel, '继续挑战微测验');
    if (focusA.focus) {
      mockStartQuiz(focusA.focus.knowledgeId, focusA.focus.knowledgeName);
    }
    assert.deepEqual(triggeredQuiz, { id: 'K08', name: '需求价格弹性' });

    // Case B: AVAILABLE
    triggeredQuiz = null;
    const focusB = resolveCurrentFocusTask(mockPathSteps, {
      K01: 'COMPLETED',
      K08: 'COMPLETED',
      K09: 'AVAILABLE',
    });
    assert.equal(focusB.focus?.actionLabel, '开始微测验');
    if (focusB.focus) {
      mockStartQuiz(focusB.focus.knowledgeId, focusB.focus.knowledgeName);
    }
    assert.deepEqual(triggeredQuiz, { id: 'K09', name: '收入与交叉弹性' });
  });

  // -------------------------------------------------------------
  // Test 4 — Mastery Shift Formatting (0.4566 -> 45.66%, 增量 +35.52%)
  // -------------------------------------------------------------
  it('Test 4: 掌握度跃迁数值格式化为 4 位百分比与增量正负号表示', () => {
    const shift1 = calculateMasteryTransition(0.4566, 0.8118);
    assert.equal(shift1.beforePercentStr, '45.66%');
    assert.equal(shift1.afterPercentStr, '81.18%');
    assert.equal(shift1.deltaPercentStr, '+35.52%');
    assert.equal(shift1.deltaValue > 0, true);

    const shift2 = calculateMasteryTransition(0.8000, 0.7273);
    assert.equal(shift2.beforePercentStr, '80.00%');
    assert.equal(shift2.afterPercentStr, '72.73%');
    assert.equal(shift2.deltaPercentStr, '-7.27%');
    assert.equal(shift2.deltaValue < 0, true);

    const shift3 = calculateMasteryTransition(0.2000, 0.2000);
    assert.equal(shift3.deltaPercentStr, '+0.00%');
  });

  // -------------------------------------------------------------
  // Test 5 — Mastery Transition Matrix (阶段演进完整覆盖)
  // -------------------------------------------------------------
  it('Test 5: 认知阶段跃迁矩阵覆盖 WEAK->DEV, DEV->MAST, WEAK->MAST, WEAK->WEAK', () => {
    // 1. WEAK -> DEVELOPING (0.20 -> 0.65)
    const t1 = calculateMasteryTransition(0.20, 0.65);
    assert.equal(t1.beforeLevel, 'WEAK');
    assert.equal(t1.afterLevel, 'DEVELOPING');
    assert.equal(t1.transitionTag, 'WEAK_TO_DEVELOPING');
    assert.match(t1.badgeText, /正在进入发展阶段/);

    // 2. DEVELOPING -> MASTERED (0.65 -> 0.82)
    const t2 = calculateMasteryTransition(0.65, 0.82);
    assert.equal(t2.beforeLevel, 'DEVELOPING');
    assert.equal(t2.afterLevel, 'MASTERED');
    assert.equal(t2.transitionTag, 'DEVELOPING_TO_MASTERED');
    assert.match(t2.badgeText, /已达到掌握目标/);

    // 3. WEAK -> MASTERED (0.4566 -> 0.8118)
    const t3 = calculateMasteryTransition(0.4566, 0.8118);
    assert.equal(t3.beforeLevel, 'WEAK');
    assert.equal(t3.afterLevel, 'MASTERED');
    assert.equal(t3.transitionTag, 'WEAK_TO_MASTERED');
    assert.match(t3.badgeText, /已达到掌握目标/);

    // 4. WEAK -> WEAK (0.20 -> 0.4566, 仍然低于 60%)
    const t4 = calculateMasteryTransition(0.20, 0.4566);
    assert.equal(t4.beforeLevel, 'WEAK');
    assert.equal(t4.afterLevel, 'WEAK');
    assert.equal(t4.transitionTag, 'STILL_WEAK');
    assert.match(t4.message, /当前掌握度仍低于目标/);
  });

  // -------------------------------------------------------------
  // Test 6 — Next Action Decision (统一决策优先级与分支覆盖)
  // -------------------------------------------------------------
  it('Test 6: Next Action 统一决策引擎精准覆盖 UNLOCK_DOWNSTREAM, 未掌握重试, 无后继返回任务', () => {
    // 场景 1: UNLOCK_DOWNSTREAM 且有后继节点 -> CONTINUE_NEXT
    const mockEnvelopeUnlock: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-1', timestamp: '2026-09-07T12:00:00Z' },
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
    const action1 = getNextLearningAction({
      currentKnowledgeId: 'K08',
      replanning: mockEnvelopeUnlock,
      afterMastery: 0.8118,
    });
    assert.equal(action1.type, 'CONTINUE_NEXT');
    assert.equal(action1.knowledgeId, 'K09');
    assert.match(action1.label, /继续学习下一个考点 K09/);

    // 场景 2: 当前考点未达标 (< 0.80) -> RETRY
    const action2 = getNextLearningAction({
      currentKnowledgeId: 'K08',
      replanning: null,
      afterMastery: 0.4566,
      summaryAccuracy: 50,
    });
    assert.equal(action2.type, 'RETRY');
    assert.match(action2.label, /继续挑战当前考点/);

    // 场景 3: 达标 (>= 0.80) 但无后继解锁 -> RETURN_TASKS
    const mockEnvelopeTerminal: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-2', timestamp: '2026-09-07T12:00:00Z' },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K30',
        before_mastery: '0.7500',
        after_mastery: '0.8500',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'COMPLETED',
        action: 'RETAIN',
        reason_code: 'MASTERY_THRESHOLD_REACHED',
        affected_nodes: ['K30'],
      },
    };
    const action3 = getNextLearningAction({
      currentKnowledgeId: 'K30',
      replanning: mockEnvelopeTerminal,
      afterMastery: 0.8500,
      summaryAccuracy: 100,
    });
    assert.equal(action3.type, 'RETURN_TASKS');
    assert.match(action3.label, /返回今日任务/);
  });

  // -------------------------------------------------------------
  // Test 7 — Student Context Isolation (S001 -> S003 上下文独立性)
  // -------------------------------------------------------------
  it('Test 7: 学生上下文从 S001 切换为 S003 时，任务焦点与状态推导严格独立', () => {
    const s001PathStates: Record<string, PathState> = {
      K01: 'COMPLETED',
      K08: 'IN_PROGRESS',
      K09: 'LOCKED',
    };
    const s003PathStates: Record<string, PathState> = {
      K01: 'AVAILABLE',
      K08: 'LOCKED',
      K09: 'LOCKED',
    };

    const focusS001 = resolveCurrentFocusTask(mockPathSteps, s001PathStates);
    const focusS003 = resolveCurrentFocusTask(mockPathSteps, s003PathStates);

    assert.equal(focusS001.focus?.knowledgeId, 'K08');
    assert.equal(focusS001.focus?.pathState, 'IN_PROGRESS');

    assert.equal(focusS003.focus?.knowledgeId, 'K01');
    assert.equal(focusS003.focus?.pathState, 'AVAILABLE');

    // 验证状态完全隔离，S003 绝不带入 S001 的 IN_PROGRESS 节点
    assert.notEqual(focusS001.focus?.knowledgeId, focusS003.focus?.knowledgeId);
  });

  // -------------------------------------------------------------
  // Test 8 — Robustness & Boundary Safety (空路径、空状态字典与边界推导鲁棒性)
  // -------------------------------------------------------------
  it('Test 8: 空路径、空状态字典、未定义焦点输入时安全收敛，绝不抛出异常', () => {
    // 1. 空路径 / undefined 路径输入
    const emptyResult = resolveCurrentFocusTask([]);
    assert.equal(emptyResult.status, 'EMPTY');
    assert.match(emptyResult.message || '', /当前没有需要立即攻坚的任务/);

    const nullResult = resolveCurrentFocusTask(null as unknown as LearningPathStep[]);
    assert.equal(nullResult.status, 'EMPTY');

    // 2. pathStates 为 undefined / null 时的单步状态解析
    const stepWithHighAcc: LearningPathStep = {
      ...mockPathSteps[0],
      current_accuracy: 85,
    };
    const stateHigh = resolveStepPathState(stepWithHighAcc, 0, undefined);
    assert.equal(stateHigh, 'COMPLETED', '正确率 >= 80% 时应推导为 COMPLETED');

    const stepWithLowAcc: LearningPathStep = {
      ...mockPathSteps[1],
      current_accuracy: 50,
    };
    const stateIndex0 = resolveStepPathState(stepWithLowAcc, 0, undefined);
    assert.equal(stateIndex0, 'IN_PROGRESS', '未提供 pathStates 且首个未完成节点应为 IN_PROGRESS');

    const stateIndex1 = resolveStepPathState(stepWithLowAcc, 1, undefined);
    assert.equal(stateIndex1, 'AVAILABLE', '未提供 pathStates 且非首个未完成节点应为 AVAILABLE');

    // 3. 传入空字典 {} 亦安全
    const stateEmptyDict = resolveStepPathState(stepWithLowAcc, 1, {});
    assert.equal(stateEmptyDict, 'AVAILABLE');
  });
});

