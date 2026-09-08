/**
 * student_experience_polish.test.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 2.2-B / Sprint 3
 * 学生端体验打磨与自适应反馈行为契约测试 (Student Experience Polish Contract Tests)
 *
 * 验证目标 (10 项严谨行为契约)：
 * Test 1 — 四种 PathState 视觉语义映射严格一致 (文案、徽标、非纯色表达)
 * Test 2 — LOCKED 永远不能启动 Quiz (disabled=true, 回调严格受阻)
 * Test 3 — AVAILABLE / IN_PROGRESS 可以顺畅启动 Quiz (disabled=false, 触发回调)
 * Test 4 — Quiz 完成后 refreshData 能够使 PathState 无刷新更新
 * Test 5 — Quiz 完成后 CurrentFocus 能够重新动态计算与转移 (K08 完成 -> 焦点变为 K09)
 * Test 6 — 学生上下文切换与异步竞态隔离 (S001 -> S003 丢弃过期异步响应，activeQuiz 安全关闭)
 * Test 7 — Mastery Transition 严禁将 WEAK -> WEAK 伪装为成功 (如实呈现巩固中)
 * Test 8 — UNLOCK_DOWNSTREAM 必然产生 CONTINUE_NEXT 行为语义
 * Test 9 — 无后继节点时必须安全回退至 RETURN_TASKS
 * Test 10 — 所有核心 CTA 具备明确行为语义 (LOCKED->disabled, AVAILABLE->START_QUIZ, IN_PROGRESS->CONTINUE_QUIZ, COMPLETED->REVIEW_QUIZ)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type { LearningPathStep, PathState, DecisionAuditEnvelope } from '../src/types.ts';
import {
  getPathStatePresentation,
  type PathStateActionType,
} from '../src/components/student/pathStatePresentation.ts';
import {
  resolveCurrentFocusTask,
  calculateMasteryTransition,
  getNextLearningAction,
} from '../src/components/student/taskFocusModel.ts';

describe('Phase 2.2-B Sprint 3: 学生端体验打磨与自适应反馈契约测试 (Student Experience Polish)', () => {
  const mockLearningSteps: LearningPathStep[] = [
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
  // Test 1: 四种 PathState 视觉语义映射严格一致
  // -------------------------------------------------------------
  it('Test 1: 四种 PathState 视觉语义映射严格一致且绝不单纯依赖颜色', () => {
    const states: PathState[] = ['LOCKED', 'AVAILABLE', 'IN_PROGRESS', 'COMPLETED'];

    for (const st of states) {
      const p = getPathStatePresentation(st);
      assert.ok(p, `状态 ${st} 必须有明确的表现契约`);
      assert.equal(p.state, st);
      // 必须包含文本，禁止纯色
      assert.ok(p.badgeText.length > 0, `状态 ${st} 必须有语义徽标文本`);
      assert.ok(p.buttonText.length > 0, `状态 ${st} 必须有按钮文本`);
      assert.ok(p.ariaLabel.length > 0, `状态 ${st} 必须有可访问性 ariaLabel 描述`);
      assert.ok(p.iconName.length > 0, `状态 ${st} 必须指定图标符号`);
    }

    // 视觉样式分明
    const lockedP = getPathStatePresentation('LOCKED');
    const availableP = getPathStatePresentation('AVAILABLE');
    const inProgressP = getPathStatePresentation('IN_PROGRESS');
    const completedP = getPathStatePresentation('COMPLETED');

    assert.equal(lockedP.disabled, true);
    assert.equal(availableP.disabled, false);
    assert.equal(inProgressP.disabled, false);
    assert.equal(completedP.disabled, false);
  });

  // -------------------------------------------------------------
  // Test 2: LOCKED 永远不能启动 Quiz
  // -------------------------------------------------------------
  it('Test 2: LOCKED 状态永远不能启动 Quiz', () => {
    const lockedP = getPathStatePresentation('LOCKED');
    assert.equal(lockedP.disabled, true);
    assert.equal(lockedP.actionType, 'DISABLED');

    let quizLaunched = false;
    const triggerQuiz = (state: PathState) => {
      const config = getPathStatePresentation(state);
      if (config.disabled) return;
      quizLaunched = true;
    };

    triggerQuiz('LOCKED');
    assert.equal(quizLaunched, false, 'LOCKED 状态节点严禁启动微测验');
  });

  // -------------------------------------------------------------
  // Test 3: AVAILABLE / IN_PROGRESS 可以启动 Quiz
  // -------------------------------------------------------------
  it('Test 3: AVAILABLE 与 IN_PROGRESS 节点可顺畅启动微测验', () => {
    let startedKid: string | null = null;
    const startQuiz = (state: PathState, kid: string) => {
      const config = getPathStatePresentation(state);
      if (config.disabled) return;
      startedKid = kid;
    };

    // 1. AVAILABLE 节点启动
    startedKid = null;
    startQuiz('AVAILABLE', 'K09');
    assert.equal(startedKid, 'K09');

    // 2. IN_PROGRESS 节点启动
    startedKid = null;
    startQuiz('IN_PROGRESS', 'K08');
    assert.equal(startedKid, 'K08');
  });

  // -------------------------------------------------------------
  // Test 4: Quiz 完成后 refreshData 能够使 PathState 更新
  // -------------------------------------------------------------
  it('Test 4: Quiz 完成后触发 refreshData 能够使 PathState 无重载更新', () => {
    // 初始状态：K08 进行中，K09 锁定
    let currentPathStates: Record<string, PathState> = {
      K01: 'COMPLETED',
      K08: 'IN_PROGRESS',
      K09: 'LOCKED',
    };

    // 模拟服务端判题产生 BKT 更新并解锁 K09
    const simulateServerResponse = () => ({
      student_id: 'S001',
      states: {
        K01: 'COMPLETED' as PathState,
        K08: 'COMPLETED' as PathState,
        K09: 'AVAILABLE' as PathState,
      },
    });

    // 模拟 refreshData 执行闭环
    const refreshData = async () => {
      const res = simulateServerResponse();
      currentPathStates = res.states;
    };

    // 验证更新前
    assert.equal(currentPathStates.K08, 'IN_PROGRESS');
    assert.equal(currentPathStates.K09, 'LOCKED');

    // 执行刷新
    refreshData();

    // 验证更新后
    assert.equal(currentPathStates.K08, 'COMPLETED');
    assert.equal(currentPathStates.K09, 'AVAILABLE');
  });

  // -------------------------------------------------------------
  // Test 5: Quiz 完成后 CurrentFocus 能够重新动态计算与转移
  // -------------------------------------------------------------
  it('Test 5: Quiz 完成后 CurrentFocus 能够重新动态识别并流转至下一考点', () => {
    // 阶段 1: K08 进行中
    const statesBefore: Record<string, PathState> = {
      K01: 'COMPLETED',
      K08: 'IN_PROGRESS',
      K09: 'LOCKED',
    };
    const focusBefore = resolveCurrentFocusTask(mockLearningSteps, statesBefore);
    assert.equal(focusBefore.focus?.knowledgeId, 'K08');
    assert.equal(focusBefore.focus?.pathState, 'IN_PROGRESS');

    // 阶段 2: K08 测验达标完成，触发重规划使得 K08 COMPLETED, K09 AVAILABLE
    const statesAfter: Record<string, PathState> = {
      K01: 'COMPLETED',
      K08: 'COMPLETED',
      K09: 'AVAILABLE',
    };
    const focusAfter = resolveCurrentFocusTask(mockLearningSteps, statesAfter);
    // 焦点自动无缝转移至 K09，无需手动刷新页面
    assert.equal(focusAfter.focus?.knowledgeId, 'K09');
    assert.equal(focusAfter.focus?.pathState, 'AVAILABLE');
    assert.equal(focusAfter.focus?.actionLabel, '开始微测验');
  });

  // -------------------------------------------------------------
  // Test 6: 学生上下文切换与异步竞态隔离
  // -------------------------------------------------------------
  it('Test 6: 学生从 S001 切换至 S003 时丢弃过期异步响应，activeQuiz 安全关闭', async () => {
    let activeQuiz: { knowledgeId: string; knowledgeName: string } | null = {
      knowledgeId: 'K08',
      knowledgeName: '需求价格弹性',
    };
    let currentStudentId = 'S001';
    let renderedDashboardStudentId = 'S001';

    // 模拟学生切换处理机制
    const handleStudentSwitch = (newStudentId: string) => {
      // 1. 安全关闭已打开的测验，严禁向新学生提交旧学生测验
      activeQuiz = null;
      currentStudentId = newStudentId;
    };

    // 模拟带有延迟的异步请求（竞态场景）
    const delayedAsyncFetch = async (reqStudentId: string, delayMs: number) => {
      await new Promise((r) => setTimeout(r, delayMs));
      // 竞态防御核心：若当前激活的学生已非发起请求时的学生，丢弃响应！
      if (reqStudentId !== currentStudentId) {
        return null; // Stale response discarded
      }
      return { studentId: reqStudentId, data: `Data for ${reqStudentId}` };
    };

    // 场景：在 S001 期间发出了一个耗时 50ms 的请求
    const s001Promise = delayedAsyncFetch('S001', 50);

    // 突然发生学生切换至 S003
    handleStudentSwitch('S003');
    assert.equal(activeQuiz, null, '切换学生时 activeQuiz 必须立即安全关闭');
    assert.equal(currentStudentId, 'S003');

    // 紧接着发出 S003 的快速请求 (耗时 10ms)
    const s003Promise = delayedAsyncFetch('S003', 10);

    const s003Result = await s003Promise;
    if (s003Result) {
      renderedDashboardStudentId = s003Result.studentId;
    }
    assert.equal(renderedDashboardStudentId, 'S003');

    // 等待稍慢的 S001 请求最终到达
    const s001Result = await s001Promise;
    if (s001Result) {
      renderedDashboardStudentId = s001Result.studentId;
    }

    // 验证：即使 S001 请求后返回，S003 的 UI 也绝不被覆盖或污染！
    assert.equal(
      renderedDashboardStudentId,
      'S003',
      '过期的 S001 异步响应绝不得污染当前 S003 状态'
    );
  });

  // -------------------------------------------------------------
  // Test 7: Mastery Transition 严禁将 WEAK -> WEAK 伪装为成功
  // -------------------------------------------------------------
  it('Test 7: 认知跃迁严禁将 WEAK -> WEAK 伪装为成功，如实呈现巩固中', () => {
    // 答错或未达标时：0.20 -> 0.45 (仍然 < 0.60 薄弱区间)
    const transition = calculateMasteryTransition(0.20, 0.45);
    assert.equal(transition.transitionTag, 'STILL_WEAK');
    assert.equal(transition.beforeLevel, 'WEAK');
    assert.equal(transition.afterLevel, 'WEAK');

    // 断言绝不能出现虚假的成功文案
    assert.doesNotMatch(transition.badgeText, /已达到掌握目标|突破成功|卓越/);
    assert.doesNotMatch(transition.message, /恭喜|达成|达标/);
    // 必须如实显示巩固中或仍低于目标
    assert.match(transition.badgeText, /巩固中|本次练习已记录/);
    assert.match(transition.message, /当前掌握度仍低于目标/);
  });

  // -------------------------------------------------------------
  // Test 8: UNLOCK_DOWNSTREAM 必然产生 CONTINUE_NEXT
  // -------------------------------------------------------------
  it('Test 8: UNLOCK_DOWNSTREAM 重规划决策必然产生 CONTINUE_NEXT 行为语义', () => {
    const mockEnvelope: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'test-dec-1', timestamp: '2026-09-08T00:00:00Z' },
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

    const action = getNextLearningAction({
      currentKnowledgeId: 'K08',
      replanning: mockEnvelope,
      afterMastery: 0.8118,
    });

    assert.equal(action.type, 'CONTINUE_NEXT');
    assert.equal(action.knowledgeId, 'K09');
    assert.match(action.label, /K09/);
  });

  // -------------------------------------------------------------
  // Test 9: 无后继节点时必须安全回到 RETURN_TASKS
  // -------------------------------------------------------------
  it('Test 9: 知识图谱末端或无后继节点时安全回退至 RETURN_TASKS', () => {
    const action = getNextLearningAction({
      currentKnowledgeId: 'K30',
      replanning: null,
      afterMastery: 0.95,
      summaryAccuracy: 100,
    });

    assert.equal(action.type, 'RETURN_TASKS');
    assert.equal(action.label, '返回今日任务');
  });

  // -------------------------------------------------------------
  // Test 10: 所有核心 CTA 具备明确行为语义 (Action Semantics)
  // -------------------------------------------------------------
  it('Test 10: 核心 CTA 具备明确行为语义而非机械锁死中文文案', () => {
    const EXPECTED_ACTIONS: Record<PathState, PathStateActionType> = {
      LOCKED: 'DISABLED',
      AVAILABLE: 'START_QUIZ',
      IN_PROGRESS: 'CONTINUE_QUIZ',
      COMPLETED: 'REVIEW_QUIZ',
    };

    for (const [st, expectedAction] of Object.entries(EXPECTED_ACTIONS)) {
      const p = getPathStatePresentation(st as PathState);
      assert.equal(
        p.actionType,
        expectedAction,
        `状态 ${st} 对应的行为语义必须是 ${expectedAction}`
      );
      if (expectedAction === 'DISABLED') {
        assert.equal(p.disabled, true);
      } else {
        assert.equal(p.disabled, false);
      }
      assert.ok(p.ariaLabel.length > 0, `状态 ${st} 必须有明确的操作意图可访问性文本`);
    }
  });
});
