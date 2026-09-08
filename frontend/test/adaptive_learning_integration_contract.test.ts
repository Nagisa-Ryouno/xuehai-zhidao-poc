/**
 * adaptive_learning_integration_contract.test.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 2.2-D / Sprint 5
 * 自适应学习全闭环集成与真实运行验证契约测试 (Adaptive Learning Closed-Loop Integration Tests)
 *
 * 验证目标 (严密覆盖 Scenario A ~ F 及 React/API 生命周期)：
 * 1. Scenario A — 达标并真实解锁后继 (Mastery Reached & Real Unlock: WEAK->MASTERED, K08->K09, CONTINUE_NEXT, Refresh to K09)
 * 2. Scenario B — 未达标，严禁虚假解锁 (Sub-threshold Mastery: RETAIN, RETRY, No False Downstream)
 * 3. Scenario C — 掌握度持平 (Mastery Retained: Zero Delta, 巩固中, 严禁出现"提升/突破")
 * 4. Scenario D — 掌握度回退 (Mastery Regressed: Delta < 0, 认知回退, 重新攻坚)
 * 5. Scenario E — 终点考点安全收敛 (Terminal Node: 达标无后继, RETURN_TASKS, 杜绝 undefined)
 * 6. Scenario F — 异常/冲突 Decision 载荷防御 (Malformed/Conflicted Payload: 严格双重校验, 零运行时崩溃)
 * 7. Scenario G — 防重复提交保护 (Duplicate Submit Protection: isSubmitting 状态锁与重复点击安全拦截)
 * 8. Scenario H — 异步竞态与请求时序隔离 (Stale Response & Monotonic Request Sequence: 跨学生与同学生乱序丢弃)
 * 9. Scenario I — 全链路数据一致性刷新 (Full Journey State Consistency: 答题->解锁->刷新->焦点移转事实统一)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  LearningPathStep,
  PathState,
  DecisionAuditEnvelope,
  QuizSubmitResponse,
} from '../src/types.ts';

import {
  resolveCurrentFocusTask,
  resolveStepPathState,
} from '../src/components/student/taskFocusModel.ts';

import {
  getLearningProgressionExplanation,
} from '../src/components/student/adaptiveLearningModel.ts';

import {
  initQuizSession,
  setQuestionsLoaded,
  selectOption,
  canSubmitAnswer,
  startSubmittingAnswer,
  buildSubmitPayload,
  setSubmitSuccess,
  getUnlockedDownstreamNodes,
} from '../src/components/student/quizModel.ts';

import { getPathStatePresentation } from '../src/components/student/pathStatePresentation.ts';

describe('Phase 2.2-D Sprint 5: 自适应学习全闭环集成与真实运行验证契约 (Closed-Loop Integration)', () => {
  // 标准真实考点 Fixture
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
      reason: '已掌握基础概念',
    },
    {
      stage: 2,
      knowledge_id: 'K08',
      knowledge_name: '需求价格弹性',
      chapter: '第二章 弹性理论',
      current_accuracy: 45.66,
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
    {
      stage: 4,
      knowledge_id: 'K30',
      knowledge_name: '微观经济学前沿与综合决策',
      chapter: '第十章 总结篇',
      current_accuracy: 75,
      priority: '高',
      priority_score: 90,
      learning_goal: '完成综合微观案例诊断',
      reason: '综合拔高考核点',
    },
  ];

  // -------------------------------------------------------------
  // Scenario A — 达标并真实解锁后继 (Mastery Reached & Real Unlock)
  // -------------------------------------------------------------
  it('Scenario A: 掌握度跨越达标 (45.66% -> 81.18%) 触发真实解锁，下一步指向 K09，刷新后 K09 成为焦点', () => {
    const replanningEnvelope: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-sprint5-a', timestamp: '2026-09-08T10:00:00Z' },
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

    // 1. 五层反馈评估
    const feedback = getLearningProgressionExplanation({
      beforeMastery: '0.4566',
      afterMastery: '0.8118',
      replanning: replanningEnvelope,
      currentKnowledgeId: 'K08',
      currentKnowledgeName: '需求价格弹性',
    });

    assert.equal(feedback.resultType, 'PROGRESS');
    assert.equal(feedback.beforePercentStr, '45.66%');
    assert.equal(feedback.afterPercentStr, '81.18%');
    assert.equal(feedback.isMasteryTargetReached, true);
    assert.equal(feedback.stageChange.before, 'WEAK');
    assert.equal(feedback.stageChange.after, 'MASTERED');
    assert.equal(feedback.pathChange.hasUnlocked, true);
    assert.deepEqual(feedback.pathChange.unlockedNodes, ['K09']);
    assert.equal(feedback.nextAction.type, 'CONTINUE_NEXT');
    assert.equal(feedback.nextAction.knowledgeId, 'K09');
    assert.match(feedback.nextAction.label, /继续学习下一个考点 K09/);

    // 2. 模拟测验完成后 refreshData()：服务端返回持久化后的最新状态字典
    const updatedPathStates: Record<string, PathState> = {
      K01: 'COMPLETED',
      K08: 'COMPLETED',
      K09: 'AVAILABLE',
      K30: 'LOCKED',
    };

    // 3. 验证任务中心重新仲裁的 Focus Task
    const newFocus = resolveCurrentFocusTask(mockPathSteps, updatedPathStates);
    assert.equal(newFocus.status, 'FOUND');
    assert.ok(newFocus.focus);
    assert.equal(newFocus.focus.knowledgeId, 'K09', 'K08 完成后，K09 应成为新的核心焦点');
    assert.equal(newFocus.focus.pathState, 'AVAILABLE');
    assert.equal(newFocus.focus.actionLabel, '开始微测验');

    // 4. 验证 K08 不再错误显示为进行中，K09 正式可用
    assert.equal(resolveStepPathState(mockPathSteps[1], 1, updatedPathStates), 'COMPLETED');
    assert.equal(resolveStepPathState(mockPathSteps[2], 2, updatedPathStates), 'AVAILABLE');
  });

  // -------------------------------------------------------------
  // Scenario B — 未达标，严禁虚假解锁 (Sub-threshold Mastery)
  // -------------------------------------------------------------
  it('Scenario B: 掌握度未达标 (56% -> 63%)，严禁虚假宣称解锁，下一步引导 RETRY', () => {
    const replanningEnvelope: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-sprint5-b', timestamp: '2026-09-08T10:05:00Z' },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K08',
        before_mastery: '0.5600',
        after_mastery: '0.6300',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'IN_PROGRESS',
        action: 'RETAIN',
        reason_code: 'MASTERY_STATE_UNCHANGED',
        affected_nodes: ['K08'],
      },
    };

    const feedback = getLearningProgressionExplanation({
      beforeMastery: '0.5600',
      afterMastery: '0.6300',
      replanning: replanningEnvelope,
      currentKnowledgeId: 'K08',
      currentKnowledgeName: '需求价格弹性',
    });

    assert.equal(feedback.resultType, 'PROGRESS');
    assert.equal(feedback.isMasteryTargetReached, false, '63% 绝不可判定为达成 80% 目标');
    assert.equal(feedback.pathChange.hasUnlocked, false, '未达标绝不能标识 hasUnlocked');
    assert.deepEqual(feedback.pathChange.unlockedNodes, [], '未达标 unlockedNodes 必须为空');
    assert.equal(feedback.nextAction.type, 'RETRY');
    assert.equal(feedback.nextAction.knowledgeId, 'K08');
    assert.match(feedback.nextAction.label, /继续挑战当前考点/);

    // 验证 UI 解释文案中绝对杜绝“已解锁”字眼
    assert.doesNotMatch(feedback.pathChange.title, /新考点已解锁/);
    assert.doesNotMatch(feedback.nextAction.label, /下一个考点/);
  });

  // -------------------------------------------------------------
  // Scenario C — 掌握度持平 (Mastery Retained / Zero Delta)
  // -------------------------------------------------------------
  it('Scenario C: 掌握度完全持平 (56% -> 56%)，语义为巩固，严禁包装为提升或突破', () => {
    const replanningEnvelope: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-sprint5-c', timestamp: '2026-09-08T10:10:00Z' },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K08',
        before_mastery: '0.5600',
        after_mastery: '0.5600',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'IN_PROGRESS',
        action: 'RETAIN',
        reason_code: 'MASTERY_STATE_UNCHANGED',
        affected_nodes: ['K08'],
      },
    };

    const feedback = getLearningProgressionExplanation({
      beforeMastery: '0.5600',
      afterMastery: '0.5600',
      replanning: replanningEnvelope,
      currentKnowledgeId: 'K08',
      currentKnowledgeName: '需求价格弹性',
    });

    assert.equal(feedback.resultType, 'RETAIN');
    assert.equal(feedback.deltaValue, 0);
    assert.equal(feedback.deltaPercentStr, '0.00%');
    assert.match(feedback.stageChange.badgeText, /巩固中/);

    // 严格禁止出现伪造的成功用语
    assert.doesNotMatch(feedback.stageChange.badgeText, /进步|突破|上升/);
    assert.doesNotMatch(feedback.stageChange.message, /重大突破|稳步提升/);
    assert.equal(feedback.nextAction.type, 'RETRY');
  });

  // -------------------------------------------------------------
  // Scenario D — 掌握度回退 (Mastery Regressed)
  // -------------------------------------------------------------
  it('Scenario D: 掌握度发生回退 (81% -> 65%)，真实呈现回退警示与巩固指引', () => {
    const replanningEnvelope: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-sprint5-d', timestamp: '2026-09-08T10:15:00Z' },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K08',
        before_mastery: '0.8118',
        after_mastery: '0.6500',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'IN_PROGRESS',
        action: 'RETAIN',
        reason_code: 'MASTERY_STATE_UNCHANGED',
        affected_nodes: ['K08'],
      },
    };

    const feedback = getLearningProgressionExplanation({
      beforeMastery: '0.8118',
      afterMastery: '0.6500',
      replanning: replanningEnvelope,
      currentKnowledgeId: 'K08',
      currentKnowledgeName: '需求价格弹性',
    });

    assert.equal(feedback.resultType, 'REGRESS');
    assert.ok(feedback.deltaValue < 0);
    assert.match(feedback.deltaPercentStr, /^-16\.18%/);
    assert.equal(feedback.isMasteryTargetReached, false);
    assert.match(feedback.stageChange.badgeText, /回退/);
    assert.match(feedback.stageChange.message, /回退|重点复习/);
    assert.equal(feedback.nextAction.type, 'RETRY');
  });

  // -------------------------------------------------------------
  // Scenario E — 终点考点安全收敛 (Terminal Node Safe Convergence)
  // -------------------------------------------------------------
  it('Scenario E: 终点考点达标无下游后继时，安全导向 RETURN_TASKS，杜绝 undefined', () => {
    const terminalEnvelope: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-sprint5-e', timestamp: '2026-09-08T10:20:00Z' },
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

    const feedback = getLearningProgressionExplanation({
      beforeMastery: '0.7500',
      afterMastery: '0.8500',
      replanning: terminalEnvelope,
      currentKnowledgeId: 'K30',
      currentKnowledgeName: '微观经济学前沿与综合决策',
    });

    assert.equal(feedback.isMasteryTargetReached, true);
    assert.equal(feedback.pathChange.hasUnlocked, false);
    assert.deepEqual(feedback.pathChange.unlockedNodes, []);
    assert.equal(feedback.nextAction.type, 'RETURN_TASKS');
    assert.equal(feedback.nextAction.knowledgeId, undefined);
    assert.equal(feedback.nextAction.label, '返回今日任务');

    // 绝对禁止产生 undefined 字符串
    assert.doesNotMatch(feedback.nextAction.label, /undefined/);
  });

  // -------------------------------------------------------------
  // Scenario F — 异常/残缺 Decision 载荷防御 (Malformed/Conflicted Payload)
  // -------------------------------------------------------------
  it('Scenario F: 残缺/冲突重规划信封防御，纯函数不崩溃且拒绝伪造解锁', () => {
    // Case 1: action 为 UNLOCK_DOWNSTREAM 但 affected_nodes 为空 []
    const envelopeEmptyAffected: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-case1', timestamp: '2026-09-08T10:25:00Z' },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K08',
        before_mastery: '0.7000',
        after_mastery: '0.8200',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'COMPLETED',
        action: 'UNLOCK_DOWNSTREAM',
        reason_code: 'MASTERY_THRESHOLD_REACHED',
        affected_nodes: [],
      },
    };
    const unlockedCase1 = getUnlockedDownstreamNodes(envelopeEmptyAffected, 'K08');
    assert.deepEqual(unlockedCase1, [], 'affected_nodes 为空时返回 []');
    const feedbackCase1 = getLearningProgressionExplanation({
      beforeMastery: '0.7000',
      afterMastery: '0.8200',
      replanning: envelopeEmptyAffected,
      currentKnowledgeId: 'K08',
    });
    assert.equal(feedbackCase1.pathChange.hasUnlocked, false, '无实际后继节点时不应标识 hasUnlocked');
    assert.equal(feedbackCase1.nextAction.type, 'RETURN_TASKS');

    // Case 2: affected_nodes 仅包含当前节点自身 ['K08']
    const envelopeSelfOnly: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-case2', timestamp: '2026-09-08T10:26:00Z' },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K08',
        before_mastery: '0.7000',
        after_mastery: '0.8200',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'COMPLETED',
        action: 'UNLOCK_DOWNSTREAM',
        reason_code: 'MASTERY_THRESHOLD_REACHED',
        affected_nodes: ['K08'],
      },
    };
    const unlockedCase2 = getUnlockedDownstreamNodes(envelopeSelfOnly, 'K08');
    assert.deepEqual(unlockedCase2, [], '自身节点必须被过滤掉');

    // Case 3: 语义冲突——action 为 RETAIN 但 affected_nodes 包含 ['K08', 'K09']
    const envelopeConflicted: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-case3', timestamp: '2026-09-08T10:27:00Z' },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K08',
        before_mastery: '0.5000',
        after_mastery: '0.6000',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'IN_PROGRESS',
        action: 'RETAIN',
        reason_code: 'MASTERY_STATE_UNCHANGED',
        affected_nodes: ['K08', 'K09'],
      },
    };
    const unlockedCase3 = getUnlockedDownstreamNodes(envelopeConflicted, 'K08');
    assert.deepEqual(unlockedCase3, [], '非 UNLOCK_DOWNSTREAM action 绝不返回解锁节点');

    // Case 4: replanning 为残缺对象或 null 时安全降级 (防崩溃测试)
    const unlockedNull = getUnlockedDownstreamNodes(null, 'K08');
    assert.deepEqual(unlockedNull, []);

    const unlockedMalformed = getUnlockedDownstreamNodes({} as unknown as DecisionAuditEnvelope, 'K08');
    assert.deepEqual(unlockedMalformed, []);
  });

  // -------------------------------------------------------------
  // Scenario G — 重复提交状态机保护 (Duplicate Submit Protection)
  // -------------------------------------------------------------
  it('Scenario G: Quiz 状态机具备严格的提交中互斥保护，二次提交被绝对拦截', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, [
      {
        question_id: 'Q01',
        knowledge_id: 'K08',
        stem: '什么是需求价格弹性？',
        options: [
          { key: 'A', text: '价格变动引起的需求量变动程度' },
          { key: 'B', text: '供给变动' },
        ],
        difficulty: 3,
      },
    ]);

    // 未选选项不能提交
    assert.equal(canSubmitAnswer(session), false);

    // 选中选项后可以提交
    session = selectOption(session, 'A');
    assert.equal(canSubmitAnswer(session), true);

    // 触发提交后进入 submitting 状态
    session = startSubmittingAnswer(session);
    assert.equal(session.status, 'submitting');

    // submitting 状态下 canSubmitAnswer 必须为 false (UI 禁用提交按钮)
    assert.equal(canSubmitAnswer(session), false);

    // 模拟快速重复调用 startSubmittingAnswer，会话保持原有状态且不发生崩溃
    const duplicateSession = startSubmittingAnswer(session);
    assert.equal(duplicateSession.status, 'submitting');
  });

  // -------------------------------------------------------------
  // Scenario H — 异步竞态与请求时序隔离 (Stale Response & Race Conditions)
  // -------------------------------------------------------------
  it('Scenario H: 学生切换时丢弃过期请求，且同学生并发刷新保证最新响应生效', async () => {
    // 模拟学生上下文与请求计数器机制
    let activeStudent = 'S001';
    let latestRequestId = 0;
    let committedData: { studentId: string; version: number } | null = null;

    async function mockAsyncFetch(studentId: string, version: number, delayMs: number) {
      const currentReqId = ++latestRequestId;
      await new Promise((resolve) => setTimeout(resolve, delayMs));

      // 仲裁：必须满足当前学生未切换 且 是最新发出的请求
      if (studentId === activeStudent && currentReqId === latestRequestId) {
        committedData = { studentId, version };
      }
    }

    // 1. S001 发起慢请求 (耗时 50ms, 版本 1)
    const p1 = mockAsyncFetch('S001', 1, 50);

    // 2. 用户快速切换至 S003 并发起快请求 (耗时 10ms, 版本 2)
    activeStudent = 'S003';
    const p2 = mockAsyncFetch('S003', 2, 10);

    await Promise.all([p1, p2]);

    // 断言：虽然 S001 的请求较后返回，但因学生已切换为 S003，S001 结果被丢弃，S003 生效
    assert.ok(committedData);
    assert.equal(committedData.studentId, 'S003');
    assert.equal(committedData.version, 2);

    // 3. 同一学生内部并发测试：S003 发起请求 A (50ms) 与 请求 B (10ms)
    const p3 = mockAsyncFetch('S003', 3, 50); // 旧请求，较慢
    const p4 = mockAsyncFetch('S003', 4, 10); // 新请求，较快

    await Promise.all([p3, p4]);

    // 断言：由于请求 4 的 requestId 更大，请求 3 返回时被仲裁抛弃，状态保持为最新请求 4
    assert.equal(committedData.studentId, 'S003');
    assert.equal(committedData.version, 4);
  });

  // -------------------------------------------------------------
  // Scenario I — 全链路数据一致性刷新 (Full Journey State Consistency)
  // -------------------------------------------------------------
  it('Scenario I: 完整答题->判题->BKT->Replanning->Next Action->Tasks Focus 闭环事实严格一致', () => {
    // 1. 初始状态：S001 访问任务中心
    const initialPathStates: Record<string, PathState> = {
      K01: 'COMPLETED',
      K08: 'IN_PROGRESS',
      K09: 'LOCKED',
      K30: 'LOCKED',
    };
    const focus1 = resolveCurrentFocusTask(mockPathSteps, initialPathStates);
    assert.equal(focus1.status, 'FOUND');
    assert.equal(focus1.focus?.knowledgeId, 'K08');
    assert.equal(focus1.focus?.pathState, 'IN_PROGRESS');

    // 2. 启动 K08 微测验并提交正确答案
    const session = setQuestionsLoaded(initQuizSession('K08', '需求价格弹性'), [
      {
        question_id: 'Q_K08_01',
        knowledge_id: 'K08',
        stem: '需求价格弹性测算公式是？',
        options: [{ key: 'A', text: '需求量相对变动 / 价格相对变动' }],
        difficulty: 3,
      },
    ]);
    const answeredSession = selectOption(session, 'A');
    const submitPayload = buildSubmitPayload(answeredSession, 'S001', 1000);
    assert.equal(submitPayload.student_id, 'S001');
    assert.equal(submitPayload.question_id, 'Q_K08_01');

    // 3. 模拟后端返回判题与决策信封
    const mockBackendResponse: QuizSubmitResponse = {
      question_id: 'Q_K08_01',
      is_correct: true,
      correct_option: 'A',
      explanation: '需求价格弹性等于需求变动百分比除以价格变动百分比。',
      learning_state: {
        mastery_level: '已掌握',
        mastery_percent: 81.18,
        consecutive_correct: 2,
        total_attempts: 3,
      },
      replanning: {
        audit_metadata: { decision_id: 'dec-100', timestamp: '2026-09-08T12:00:00Z' },
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
      },
    };

    const completedSession = setSubmitSuccess(answeredSession, mockBackendResponse, 15000);
    assert.equal(completedSession.status, 'feedback');
    assert.ok(completedSession.latestReplanning);

    // 4. 用户查看五层反馈并点击下一步
    const progression = getLearningProgressionExplanation({
      beforeMastery: '0.4566',
      afterMastery: '0.8118',
      replanning: completedSession.latestReplanning,
      currentKnowledgeId: 'K08',
    });
    assert.equal(progression.nextAction.type, 'CONTINUE_NEXT');
    assert.equal(progression.nextAction.knowledgeId, 'K09');

    // 5. 触发 onFinish() / onRefresh()，拉取最新状态
    const refreshedStates: Record<string, PathState> = {
      K01: 'COMPLETED',
      K08: 'COMPLETED',
      K09: 'AVAILABLE',
      K30: 'LOCKED',
    };

    // 6. 验证任务中心重新仲裁的 Focus Task 与时间轴渲染
    const focusAfterRefresh = resolveCurrentFocusTask(mockPathSteps, refreshedStates);
    assert.equal(focusAfterRefresh.status, 'FOUND');
    assert.equal(focusAfterRefresh.focus?.knowledgeId, 'K09');
    assert.equal(focusAfterRefresh.focus?.pathState, 'AVAILABLE');

    // 7. 验证路径状态呈现配置
    const k08Presentation = getPathStatePresentation(refreshedStates['K08']);
    const k09Presentation = getPathStatePresentation(refreshedStates['K09']);
    assert.equal(k08Presentation.badgeText, '✓ 已掌握');
    assert.equal(k09Presentation.badgeText, '🔓 已满足学习条件');
    assert.equal(k09Presentation.actionType, 'START_QUIZ');
  });
});
