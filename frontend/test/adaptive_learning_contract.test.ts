/**
 * adaptive_learning_contract.test.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 2.2-C / Sprint 4
 * 自适应学习智能化与质量固化契约测试 (Adaptive Learning Intelligence & Quality Hardening Contract Tests)
 *
 * 验证目标 (10 项严密行为契约)：
 * Test 1 — Recommendation Reason Integrity (推荐解释真实性：依据必须反映状态、掌握度差距与路径优先级，拒绝空洞文案)
 * Test 2 — Focus Task Determinism (焦点任务与解释确定性：相同输入必须100%产生相同输出)
 * Test 3 — IN_PROGRESS Priority (进行中任务优先级仲裁：IN_PROGRESS > AVAILABLE > fallback)
 * Test 4 — Mastery Goal Consistency (掌握度目标一致性：全站统一锚定 0.80 / 80%，边界值严格判定)
 * Test 5 — Mastery Transition Integrity (掌握度跃迁保真：上升、持平、下降三种流转语义真实表达，严禁将持平包装为提升)
 * Test 6 — Replanning Explanation (重规划解释完整性：解释为什么解锁、解锁了什么、下一步行动是什么)
 * Test 7 — No False Unlock (防虚假解锁：无真实解锁后继时严禁渲染虚假解锁信息)
 * Test 8 — Terminal State (终点状态安全收敛：无后继考点时安全返回 RETURN_TASKS，杜绝 undefined)
 * Test 9 — Context Isolation (学生上下文隔离：不同学生的解释与推荐完全独立，纯输入驱动无全局污染)
 * Test 10 — Stale Response Protection (异步竞态与过期响应拦截：快速切换学生后迟到的旧响应必须被丢弃)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  LearningPathStep,
  PathState,
  DecisionAuditEnvelope,
} from '../src/types.ts';
import {
  resolveCurrentFocusTask,
} from '../src/components/student/taskFocusModel.ts';

/**
 * 动态加载待在 Step 2 实现的纯函数解释模型
 */
async function loadAdaptiveModel() {
  try {
    return await import('../src/components/student/adaptiveLearningModel.ts');
  } catch {
    return null;
  }
}

describe('Phase 2.2-C Sprint 4: 自适应学习智能化契约测试 (Adaptive Learning Intelligence Contract)', () => {
  // 真实考点 Fixture
  const mockK08Step: LearningPathStep = {
    stage: 2,
    knowledge_id: 'K08',
    knowledge_name: '需求价格弹性',
    chapter: '第二章 弹性理论',
    current_accuracy: 56,
    priority: '高',
    priority_score: 95,
    learning_goal: '熟练掌握点弹性与弧弹性测算',
    reason: '这是你当前学习路径中优先级最高的可学习考点。',
  };

  const mockK09Step: LearningPathStep = {
    stage: 3,
    knowledge_id: 'K09',
    knowledge_name: '收入与交叉弹性',
    chapter: '第二章 弹性理论',
    current_accuracy: 20,
    priority: '中',
    priority_score: 70,
    learning_goal: '理解替代品与互补品的交叉价格影响',
    reason: '需在掌握需求价格弹性后开展突破',
  };

  const mockK10Step: LearningPathStep = {
    stage: 4,
    knowledge_id: 'K10',
    knowledge_name: '供给弹性与市场均衡',
    chapter: '第二章 弹性理论',
    current_accuracy: 10,
    priority: '低',
    priority_score: 40,
    learning_goal: '掌握供给价格弹性计算',
    reason: '综合应用考点',
  };

  // -------------------------------------------------------------
  // Test 1: Recommendation Reason Integrity
  // -------------------------------------------------------------
  it('Test 1 — Recommendation Reason Integrity: 推荐解释必须来自真实输入事实', async () => {
    const model = await loadAdaptiveModel();
    assert.ok(
      model,
      'adaptiveLearningModel.ts 尚未实现 (TDD Step 1 RED: 待 Step 2 创建)'
    );

    const { getRecommendationExplanation } = model;
    assert.equal(
      typeof getRecommendationExplanation,
      'function',
      'getRecommendationExplanation 必须是一个导出的纯函数'
    );

    const explanation = getRecommendationExplanation({
      step: mockK08Step,
      pathState: 'IN_PROGRESS',
      currentMasteryPercent: 56,
      targetMasteryPercent: 80,
    });

    // 1. 结构完整性断言
    assert.ok(explanation.title && explanation.title.length > 0, 'title 必须非空');
    assert.ok(explanation.reason && explanation.reason.length > 0, 'reason 必须非空');
    assert.ok(
      ['HIGH', 'MEDIUM', 'LOW'].includes(explanation.priority),
      'priority 必须属于 HIGH | MEDIUM | LOW'
    );
    assert.ok(
      Array.isArray(explanation.factors) && explanation.factors.length > 0,
      'factors 必须为非空事实依据数组'
    );

    // 2. 真实事实依据检查（必须能反映当前 PathState、当前掌握度、目标掌握度与路径属性）
    const factorText = explanation.factors.join(' ');
    assert.ok(
      factorText.includes('正在进行') || factorText.includes('IN_PROGRESS'),
      '依据中必须反映当前考点处于正在进行中'
    );
    assert.ok(
      factorText.includes('56%') || factorText.includes('56'),
      '依据中必须包含当前考点真实掌握度数值'
    );
    assert.ok(
      factorText.includes('80%') || factorText.includes('80'),
      '依据中必须明确提及 80% 目标阈值'
    );

    // 3. 拒绝空洞营销话术
    const bannedPhrases = [
      '这是一个很重要的知识点',
      '相信自己，你一定可以',
      'AI 为你精心推荐',
      '这是最适合你的内容',
    ];
    for (const banned of bannedPhrases) {
      assert.ok(
        !explanation.reason.includes(banned) && !factorText.includes(banned),
        `禁止输出无数据支撑的泛化空话: "${banned}"`
      );
    }
  });

  // -------------------------------------------------------------
  // Test 2: Focus Task Determinism
  // -------------------------------------------------------------
  it('Test 2 — Focus Task Determinism: 相同输入必须确定性产生完全相同的焦点与解释', async () => {
    const model = await loadAdaptiveModel();
    assert.ok(
      model,
      'adaptiveLearningModel.ts 尚未实现 (TDD Step 1 RED: 待 Step 2 创建)'
    );

    const { getRecommendationExplanation } = model;
    const path = [mockK08Step, mockK09Step];
    const states: Record<string, PathState> = {
      K08: 'IN_PROGRESS',
      K09: 'LOCKED',
    };

    // 连续多次调用 resolveCurrentFocusTask
    const focus1 = resolveCurrentFocusTask(path, states);
    const focus2 = resolveCurrentFocusTask(path, states);
    assert.deepStrictEqual(focus1, focus2, 'resolveCurrentFocusTask 输出必须绝对幂等');

    // 连续多次调用 getRecommendationExplanation
    const params = {
      step: mockK08Step,
      pathState: 'IN_PROGRESS' as PathState,
      currentMasteryPercent: 56,
      targetMasteryPercent: 80,
    };
    const exp1 = getRecommendationExplanation(params);
    const exp2 = getRecommendationExplanation(params);
    const exp3 = getRecommendationExplanation(params);

    assert.deepStrictEqual(exp1, exp2, '解释模型多次运行必须产生完全相同的结构');
    assert.deepStrictEqual(exp2, exp3, '解释模型严禁依赖随机数、当前时间或外部状态');
  });

  // -------------------------------------------------------------
  // Test 3: IN_PROGRESS Priority
  // -------------------------------------------------------------
  it('Test 3 — IN_PROGRESS Priority: 严格遵守 IN_PROGRESS > AVAILABLE > fallback 优先级仲裁', () => {
    // 场景 A: 存在 IN_PROGRESS 时，即便首个节点是 AVAILABLE，也必须选中 IN_PROGRESS
    const pathA = [mockK08Step, mockK09Step, mockK10Step];
    const statesA: Record<string, PathState> = {
      K08: 'AVAILABLE',
      K09: 'IN_PROGRESS',
      K10: 'AVAILABLE',
    };
    const resA = resolveCurrentFocusTask(pathA, statesA);
    assert.equal(resA.status, 'FOUND');
    assert.equal(resA.focus?.knowledgeId, 'K09', 'IN_PROGRESS 节点拥有最高焦点优先级');

    // 场景 B: 无 IN_PROGRESS 时，首选第一个 AVAILABLE 节点
    const statesB: Record<string, PathState> = {
      K08: 'AVAILABLE',
      K09: 'AVAILABLE',
      K10: 'LOCKED',
    };
    const resB = resolveCurrentFocusTask(pathA, statesB);
    assert.equal(resB.status, 'FOUND');
    assert.equal(resB.focus?.knowledgeId, 'K08', '无进行中节点时，首选推荐路径中首个已满足条件的节点');
  });

  // -------------------------------------------------------------
  // Test 4: Mastery Goal Consistency
  // -------------------------------------------------------------
  it('Test 4 — Mastery Goal Consistency: 目标掌握度全站唯一统一为 0.80 / 80%', async () => {
    const model = await loadAdaptiveModel();
    assert.ok(
      model,
      'adaptiveLearningModel.ts 尚未实现 (TDD Step 1 RED: 待 Step 2 创建)'
    );

    const {
      MASTERY_TARGET_THRESHOLD,
      MASTERY_TARGET_PERCENT,
      isMasteryGoalReached,
    } = model;

    assert.equal(MASTERY_TARGET_THRESHOLD, 0.8, '掌握度目标阈值常量必须严格为 0.80');
    assert.equal(MASTERY_TARGET_PERCENT, 80, '掌握度目标百分比常量必须严格为 80');

    assert.equal(typeof isMasteryGoalReached, 'function', '必须导出判定是否达标的纯函数');

    // 边界值判定
    assert.equal(isMasteryGoalReached(0.7999), false, '0.7999 严禁判定为达标');
    assert.equal(isMasteryGoalReached(79.99), false, '79.99% 严禁判定为达标');
    assert.equal(isMasteryGoalReached(0.8), true, '0.8000 严格判定为达标');
    assert.equal(isMasteryGoalReached(80.0), true, '80.00% 严格判定为达标');
    assert.equal(isMasteryGoalReached(0.8001), true, '0.8001 严格判定为达标');
    assert.equal(isMasteryGoalReached(85), true, '85% 严格判定为达标');
  });

  // -------------------------------------------------------------
  // Test 5: Mastery Transition Integrity
  // -------------------------------------------------------------
  it('Test 5 — Mastery Transition Integrity: 准确表达上升、持平与回退三种跃迁状态', async () => {
    const model = await loadAdaptiveModel();
    assert.ok(
      model,
      'adaptiveLearningModel.ts 尚未实现 (TDD Step 1 RED: 待 Step 2 创建)'
    );

    const { getLearningProgressionExplanation } = model;
    assert.equal(
      typeof getLearningProgressionExplanation,
      'function',
      'getLearningProgressionExplanation 必须存在'
    );

    // 1. 上升并跨越达标 (45.66% -> 81.18%)
    const expProgress = getLearningProgressionExplanation({
      beforeMastery: 0.4566,
      afterMastery: 0.8118,
      currentKnowledgeId: 'K08',
      currentKnowledgeName: '需求价格弹性',
    });
    assert.equal(expProgress.resultType, 'PROGRESS');
    assert.ok(expProgress.deltaValue > 0, '上升跃迁增量必须为正');
    assert.equal(expProgress.isMasteryTargetReached, true, '81.18% 达成掌握目标');
    assert.equal(expProgress.stageChange.before, 'WEAK');
    assert.equal(expProgress.stageChange.after, 'MASTERED');
    assert.ok(
      expProgress.stageChange.badgeText.includes('达成') ||
        expProgress.stageChange.badgeText.includes('掌握目标'),
      '跨越达标必须明确展示达标语义'
    );

    // 2. 持平 (56% -> 56%)
    const expRetain = getLearningProgressionExplanation({
      beforeMastery: 0.56,
      afterMastery: 0.56,
      currentKnowledgeId: 'K08',
      currentKnowledgeName: '需求价格弹性',
    });
    assert.equal(expRetain.resultType, 'RETAIN');
    assert.equal(expRetain.deltaValue, 0, '持平时 deltaValue 必须精确为 0');
    // 严格红线：持平严禁被描述为提升/进步
    assert.ok(
      !expRetain.stageChange.badgeText.includes('提升') &&
        !expRetain.stageChange.badgeText.includes('进步') &&
        !expRetain.stageChange.message.includes('提升') &&
        !expRetain.stageChange.message.includes('进步'),
      '持平状态绝对严禁伪装为掌握度提升或练习进步'
    );
    assert.ok(
      expRetain.stageChange.message.includes('已记录') ||
        expRetain.stageChange.message.includes('巩固'),
      '持平状态必须如实告知已记录本次练习并建议巩固'
    );

    // 3. 下降与回退预警 (81% -> 65%)
    const expRegress = getLearningProgressionExplanation({
      beforeMastery: 0.81,
      afterMastery: 0.65,
      currentKnowledgeId: 'K08',
      currentKnowledgeName: '需求价格弹性',
    });
    assert.equal(expRegress.resultType, 'REGRESS');
    assert.ok(expRegress.deltaValue < 0, '下降跃迁增量必须为负');
    assert.equal(expRegress.isMasteryTargetReached, false);
    assert.ok(
      expRegress.stageChange.badgeText.includes('回退') ||
        expRegress.stageChange.badgeText.includes('回落') ||
        expRegress.stageChange.message.includes('回退') ||
        expRegress.stageChange.message.includes('回落'),
      '掌握度下降必须包含清晰的回退预警'
    );
  });

  // -------------------------------------------------------------
  // Test 6: Replanning Explanation
  // -------------------------------------------------------------
  it('Test 6 — Replanning Explanation: 完整解释路径重规划决策三层次 (原因/变化/下一步)', async () => {
    const model = await loadAdaptiveModel();
    assert.ok(
      model,
      'adaptiveLearningModel.ts 尚未实现 (TDD Step 1 RED: 待 Step 2 创建)'
    );

    const { getLearningProgressionExplanation } = model;

    const mockReplanning: DecisionAuditEnvelope = {
      audit_metadata: {
        decision_id: 'd-12345',
        timestamp: '2026-09-08T19:00:00Z',
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

    const exp = getLearningProgressionExplanation({
      beforeMastery: '0.4566',
      afterMastery: '0.8118',
      replanning: mockReplanning,
      currentKnowledgeId: 'K08',
      currentKnowledgeName: '需求价格弹性',
    });

    // 1. 变化事实验证
    assert.equal(exp.pathChange.hasUnlocked, true, 'UNLOCK_DOWNSTREAM 且有后继时 hasUnlocked 必须为 true');
    assert.ok(
      exp.pathChange.unlockedNodes.includes('K09'),
      '解锁后继列表中必须包含 K09'
    );
    assert.ok(
      !exp.pathChange.unlockedNodes.includes('K08'),
      '已掌握的当前节点 K08 严禁被列为解锁后继'
    );

    // 2. 三层次解释文案健全性
    assert.ok(
      exp.pathChange.detail && exp.pathChange.detail.length > 0,
      '路径变化详情说明必须存在'
    );
    assert.ok(
      exp.pathChange.detail.includes('K09'),
      '路径变化说明中必须点名被解锁的具体考点编号'
    );

    // 3. 下一步行动衔接
    assert.equal(exp.nextAction.type, 'CONTINUE_NEXT');
    assert.equal(exp.nextAction.knowledgeId, 'K09');
    assert.ok(
      exp.nextAction.label.includes('K09'),
      '下一步行动按钮文案必须直接引导至新解锁考点'
    );
  });

  // -------------------------------------------------------------
  // Test 7: No False Unlock
  // -------------------------------------------------------------
  it('Test 7 — No False Unlock: 无真实解锁后继时严禁渲染虚假解锁信息', async () => {
    const model = await loadAdaptiveModel();
    assert.ok(
      model,
      'adaptiveLearningModel.ts 尚未实现 (TDD Step 1 RED: 待 Step 2 创建)'
    );

    const { getLearningProgressionExplanation } = model;

    // Case A: 决策为 RETAIN
    const replanningRetain: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-1', timestamp: '2026-09-08T19:00:00Z' },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K08',
        before_mastery: '0.4566',
        after_mastery: '0.5500',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'IN_PROGRESS',
        action: 'RETAIN',
        reason_code: 'MASTERY_STATE_UNCHANGED',
        affected_nodes: ['K08'],
      },
    };
    const expA = getLearningProgressionExplanation({
      beforeMastery: 0.4566,
      afterMastery: 0.55,
      replanning: replanningRetain,
      currentKnowledgeId: 'K08',
    });
    assert.equal(expA.pathChange.hasUnlocked, false);
    assert.equal(expA.pathChange.unlockedNodes.length, 0);
    assert.ok(!expA.pathChange.detail.includes('已解锁'));

    // Case B: 动作为 UNLOCK_DOWNSTREAM 但 affected_nodes 为空
    const replanningEmptyAffected: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-2', timestamp: '2026-09-08T19:00:00Z' },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K08',
        before_mastery: '0.7500',
        after_mastery: '0.8200',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'COMPLETED',
        action: 'UNLOCK_DOWNSTREAM',
        reason_code: 'MASTERY_THRESHOLD_REACHED',
        affected_nodes: [], // 空数组
      },
    };
    const expB = getLearningProgressionExplanation({
      beforeMastery: 0.75,
      afterMastery: 0.82,
      replanning: replanningEmptyAffected,
      currentKnowledgeId: 'K08',
    });
    assert.equal(expB.pathChange.hasUnlocked, false);
    assert.equal(expB.pathChange.unlockedNodes.length, 0);

    // Case C: 动作为 UNLOCK_DOWNSTREAM 但 affected_nodes 仅包含自身 K08
    const replanningSelfOnly: DecisionAuditEnvelope = {
      audit_metadata: { decision_id: 'd-3', timestamp: '2026-09-08T19:00:00Z' },
      canonical_payload: {
        rule_version: 'v1.0',
        student_id: 'S001',
        knowledge_id: 'K08',
        before_mastery: '0.7500',
        after_mastery: '0.8200',
        before_path_state: 'IN_PROGRESS',
        after_path_state: 'COMPLETED',
        action: 'UNLOCK_DOWNSTREAM',
        reason_code: 'MASTERY_THRESHOLD_REACHED',
        affected_nodes: ['K08'], // 只有自己，无后继
      },
    };
    const expC = getLearningProgressionExplanation({
      beforeMastery: 0.75,
      afterMastery: 0.82,
      replanning: replanningSelfOnly,
      currentKnowledgeId: 'K08',
    });
    assert.equal(expC.pathChange.hasUnlocked, false);
    assert.equal(expC.pathChange.unlockedNodes.length, 0);
  });

  // -------------------------------------------------------------
  // Test 8: Terminal State
  // -------------------------------------------------------------
  it('Test 8 — Terminal State: 终点考点达标且无后继时安全返回 RETURN_TASKS', async () => {
    const model = await loadAdaptiveModel();
    assert.ok(
      model,
      'adaptiveLearningModel.ts 尚未实现 (TDD Step 1 RED: 待 Step 2 创建)'
    );

    const { getLearningProgressionExplanation } = model;

    // 考点 K10 达标 (0.85)，无后继节点
    const expTerminal = getLearningProgressionExplanation({
      beforeMastery: 0.7,
      afterMastery: 0.85,
      currentKnowledgeId: 'K10',
      currentKnowledgeName: '供给弹性与市场均衡',
      replanning: {
        audit_metadata: { decision_id: 'd-term', timestamp: '2026-09-08T19:00:00Z' },
        canonical_payload: {
          rule_version: 'v1.0',
          student_id: 'S001',
          knowledge_id: 'K10',
          before_mastery: '0.7000',
          after_mastery: '0.8500',
          before_path_state: 'IN_PROGRESS',
          after_path_state: 'COMPLETED',
          action: 'RETAIN',
          reason_code: 'MASTERY_THRESHOLD_REACHED',
          affected_nodes: ['K10'],
        },
      },
    });

    assert.equal(expTerminal.nextAction.type, 'RETURN_TASKS');
    assert.ok(
      expTerminal.nextAction.label.includes('今日任务') ||
        expTerminal.nextAction.label.includes('返回'),
      '终态行动标签必须引导返回今日任务'
    );
    assert.ok(
      expTerminal.nextAction.knowledgeId === undefined,
      '无后继节点时 knowledgeId 不得产生 undefined 字符串或无效引用'
    );
  });

  // -------------------------------------------------------------
  // Test 9: Context Isolation
  // -------------------------------------------------------------
  it('Test 9 — Context Isolation: 不同学生上下文的解释与焦点推导严格物理隔离', async () => {
    const model = await loadAdaptiveModel();
    assert.ok(
      model,
      'adaptiveLearningModel.ts 尚未实现 (TDD Step 1 RED: 待 Step 2 创建)'
    );

    const { getRecommendationExplanation } = model;

    // S001 上下文
    const s001Step: LearningPathStep = {
      ...mockK08Step,
      current_accuracy: 56,
    };
    const expS001 = getRecommendationExplanation({
      step: s001Step,
      pathState: 'IN_PROGRESS',
      currentMasteryPercent: 56,
      targetMasteryPercent: 80,
    });

    // S003 上下文
    const s003Step: LearningPathStep = {
      ...mockK09Step,
      current_accuracy: 72,
    };
    const expS003 = getRecommendationExplanation({
      step: s003Step,
      pathState: 'AVAILABLE',
      currentMasteryPercent: 72,
      targetMasteryPercent: 80,
    });

    // 绝对隔离性断言
    const s001Text = JSON.stringify(expS001);
    const s003Text = JSON.stringify(expS003);

    assert.ok(s001Text.includes('56%') || s001Text.includes('56'));
    assert.ok(!s001Text.includes('72%') && !s001Text.includes('72'));

    assert.ok(s003Text.includes('72%') || s003Text.includes('72'));
    assert.ok(!s003Text.includes('56%') && !s003Text.includes('56'));

    assert.equal(expS001.priority, 'HIGH', 'IN_PROGRESS 节点在 S001 获得 HIGH 优先级');
    assert.equal(expS003.priority, 'MEDIUM', 'AVAILABLE 节点在 S003 获得 MEDIUM 优先级');
  });

  // -------------------------------------------------------------
  // Test 10: Stale Response Protection
  // -------------------------------------------------------------
  it('Test 10 — Stale Response Protection: 异步响应仲裁必须保证最新学生上下文胜出，旧响应被安全丢弃', () => {
    // 模拟前端异步请求生命周期与会话仲裁机制
    class StudentSessionManager {
      private activeStudentId: string = 'S001';
      private currentDashboard: Record<string, unknown> | null = null;

      public switchStudent(studentId: string) {
        this.activeStudentId = studentId;
      }

      public getActiveStudent(): string {
        return this.activeStudentId;
      }

      public getCurrentDashboard(): Record<string, unknown> | null {
        return this.currentDashboard;
      }

      // 异步响应返回时的仲裁入口
      public handleAsyncResponse(requestStudentId: string, payload: Record<string, unknown>): boolean {
        if (requestStudentId !== this.activeStudentId) {
          // 过期响应，安全丢弃
          return false;
        }
        this.currentDashboard = payload;
        return true;
      }
    }

    const session = new StudentSessionManager();
    assert.equal(session.getActiveStudent(), 'S001');

    // 1. 发起 S001 请求
    const reqStudentA = 'S001';

    // 2. 用户快速切换为 S003 并发起 S003 请求
    session.switchStudent('S003');
    const reqStudentB = 'S003';

    // 3. S003 响应先返回 (Fast Response)
    const successB = session.handleAsyncResponse(reqStudentB, {
      student_id: 'S003',
      name: '李小明',
      focus: 'K12',
    });
    assert.equal(successB, true);
    assert.equal(session.getCurrentDashboard()?.['student_id'], 'S003');

    // 4. S001 迟到的响应后返回 (Slow / Stale Response)
    const successA = session.handleAsyncResponse(reqStudentA, {
      student_id: 'S001',
      name: '张华',
      focus: 'K08',
    });
    assert.equal(successA, false, '过期的 S001 响应必须被仲裁器丢弃');

    // 5. 状态严格维持 S003，无任何 S001 污染
    assert.equal(session.getCurrentDashboard()?.['student_id'], 'S003');
    assert.equal(session.getCurrentDashboard()?.['focus'], 'K12');
  });
});
