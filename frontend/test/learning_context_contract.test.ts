/**
 * learning_context_contract.test.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-A
 * AI Learning Companion Context Boundary & Grounding 契约测试 (Test 1 ~ Test 16)
 *
 * 核心设计目标：
 * 验证 Deterministic Adaptive Learning Engine -> Learning Context -> AI Companion
 * 之间单向、只读、防篡改、无幻觉的事实边界 (Context Boundary)。
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  StudentBasic,
  LearningPathStep,
  PathState,
  DecisionAuditEnvelope,
  QuizSubmitResponse,
} from '../src/types.ts';

import {
  MASTERY_TARGET_THRESHOLD,
  MASTERY_TARGET_PERCENT,
  type CurrentFocusResult,
} from '../src/components/student/taskFocusModel.ts';

import {
  buildLearningContext,
  type LearningContextInput,
} from '../src/components/student/learningContextModel.ts';

// ----------------------------------------------------------------------------
// 模拟测试基础数据 (Mock Test Ground Truth)
// ----------------------------------------------------------------------------

const mockStudent: StudentBasic = {
  student_id: 'S001',
  student_name: '张小凡',
  major: '经济学',
  grade: '大二',
  learning_goal: '掌握微观经济学弹性理论并能熟练分析市场供求均衡',
};

const mockLearningPath: LearningPathStep[] = [
  {
    stage: 1,
    knowledge_id: 'K08',
    knowledge_name: '需求价格弹性',
    chapter: '微观经济学基础',
    current_accuracy: 45.66,
    priority: '高',
    priority_score: 95,
    learning_goal: '理解需求价格弹性的定义及影响因素',
    reason: '核心基础考点，后续弹性应用前置依赖',
  },
  {
    stage: 2,
    knowledge_id: 'K09',
    knowledge_name: '收入与交叉弹性',
    chapter: '微观经济学基础',
    current_accuracy: 20.0,
    priority: '中',
    priority_score: 75,
    learning_goal: '掌握收入弹性与交叉弹性的计算与品类区分',
    reason: 'K08 的直接后继考点',
  },
  {
    stage: 3,
    knowledge_id: 'K11',
    knowledge_name: '弹性与税收归宿',
    chapter: '微观经济学应用',
    current_accuracy: 0.0,
    priority: '高',
    priority_score: 85,
    learning_goal: '综合应用弹性分析税负在买卖双方间的分配',
    reason: '复合后继考点',
  },
];

const mockPathStates: Record<string, PathState> = {
  K08: 'IN_PROGRESS',
  K09: 'AVAILABLE',
  K11: 'LOCKED',
};

const mockCurrentFocus: CurrentFocusResult = {
  status: 'FOUND',
  focus: {
    knowledgeId: 'K08',
    knowledgeName: '需求价格弹性',
    chapter: '微观经济学基础',
    pathState: 'IN_PROGRESS',
    currentMasteryPercent: 46,
    targetMasteryPercent: 80,
    reason: '核心基础考点，后续弹性应用前置依赖',
    actionLabel: '继续挑战微测验',
    step: mockLearningPath[0],
  },
};

const mockUnlockReplanning: DecisionAuditEnvelope = {
  audit_metadata: {
    decision_id: 'dec-1001',
    timestamp: '2026-09-08T12:00:00Z',
    trace_id: 'trace-1001',
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

const mockRetainReplanning: DecisionAuditEnvelope = {
  audit_metadata: {
    decision_id: 'dec-1002',
    timestamp: '2026-09-08T12:05:00Z',
    trace_id: 'trace-1002',
  },
  canonical_payload: {
    rule_version: 'v1.0',
    student_id: 'S001',
    knowledge_id: 'K08',
    before_mastery: '0.4566',
    after_mastery: '0.5600',
    before_path_state: 'IN_PROGRESS',
    after_path_state: 'IN_PROGRESS',
    action: 'RETAIN',
    reason_code: 'MASTERY_STATE_UNCHANGED',
    affected_nodes: ['K08'],
  },
};

const mockRegressReplanning: DecisionAuditEnvelope = {
  audit_metadata: {
    decision_id: 'dec-1003',
    timestamp: '2026-09-08T12:10:00Z',
    trace_id: 'trace-1003',
  },
  canonical_payload: {
    rule_version: 'v1.0',
    student_id: 'S001',
    knowledge_id: 'K08',
    before_mastery: '0.8118',
    after_mastery: '0.6500',
    before_path_state: 'COMPLETED',
    after_path_state: 'IN_PROGRESS',
    action: 'DEMOTE_TO_REVIEW',
    reason_code: 'REVIEW_REQUIRED_DEMOTION',
    affected_nodes: ['K08'],
  },
};

describe('Phase 3 / Sprint 7-A: AI Learning Companion Context Boundary Contract Tests', () => {
  // --------------------------------------------------------------------------
  // Test 1 — Real State Grounding
  // --------------------------------------------------------------------------
  it('Test 1 — Real State Grounding: Context 必须完全由真实已有状态构建，禁止编造事实', () => {
    const input: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: mockPathStates,
      currentFocus: mockCurrentFocus,
    };

    const context = buildLearningContext(input);

    assert.equal(context.system_facts.student_id, 'S001');
    assert.equal(context.system_facts.student_name, '张小凡');
    assert.equal(context.system_facts.major, '经济学');
    assert.equal(context.system_facts.grade, '大二');
    assert.equal(context.system_facts.current_knowledge_id, 'K08');
    assert.equal(context.system_facts.current_knowledge_name, '需求价格弹性');
    assert.equal(context.system_facts.current_path_state, 'IN_PROGRESS');
  });

  // --------------------------------------------------------------------------
  // Test 2 — Real Mastery
  // --------------------------------------------------------------------------
  it('Test 2 — Real Mastery: 掌握度与差距必须严格来自真实系统数据与计算', () => {
    const input: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: mockPathStates,
      currentFocus: mockCurrentFocus,
    };

    const context = buildLearningContext(input);

    assert.equal(context.system_facts.current_mastery_percent, 46);
    assert.equal(context.system_facts.mastery_gap_percent, 34); // 80 - 46 = 34
    assert.equal(context.system_facts.is_mastered, false);
  });

  // --------------------------------------------------------------------------
  // Test 3 — Single Target Threshold
  // --------------------------------------------------------------------------
  it('Test 3 — Single Target Threshold: 必须严格等于全站统一常量 0.80 / 80，禁止出现第二套阈值', () => {
    const input: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: mockPathStates,
      currentFocus: mockCurrentFocus,
    };

    const context = buildLearningContext(input);

    assert.equal(context.system_facts.mastery_target_threshold, MASTERY_TARGET_THRESHOLD);
    assert.equal(context.system_facts.mastery_target_percent, MASTERY_TARGET_PERCENT);
    assert.equal(context.system_facts.mastery_target_threshold, 0.80);
    assert.equal(context.system_facts.mastery_target_percent, 80);
  });

  // --------------------------------------------------------------------------
  // Test 4 — Real PathState
  // --------------------------------------------------------------------------
  it('Test 4 — Real PathState: 严格保持 LOCKED, AVAILABLE, IN_PROGRESS, COMPLETED 四态枚举', () => {
    const states: PathState[] = ['LOCKED', 'AVAILABLE', 'IN_PROGRESS', 'COMPLETED'];

    for (const state of states) {
      const input: LearningContextInput = {
        student: mockStudent,
        learningPath: mockLearningPath,
        pathStates: { K08: state },
        currentFocus: {
          status: 'FOUND',
          focus: {
            ...mockCurrentFocus.focus!,
            pathState: state,
          },
        },
      };
      const context = buildLearningContext(input);
      assert.equal(context.system_facts.current_path_state, state);
    }
  });

  // --------------------------------------------------------------------------
  // Test 5 — Prerequisite Alignment
  // --------------------------------------------------------------------------
  it('Test 5 — Prerequisite Alignment: 前置就绪状态必须与已有路径事实严格一致', () => {
    // 场景 A: 节点状态为 LOCKED -> prerequisites_met 必为 false
    const lockedInput: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: { K11: 'LOCKED' },
      currentFocus: {
        status: 'FOUND',
        focus: {
          ...mockCurrentFocus.focus!,
          knowledgeId: 'K11',
          pathState: 'LOCKED',
        },
      },
    };
    const lockedContext = buildLearningContext(lockedInput);
    assert.equal(lockedContext.system_facts.prerequisites_met, false);

    // 场景 B: 节点状态为 AVAILABLE 或 IN_PROGRESS -> prerequisites_met 必为 true
    const availableInput: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: { K08: 'IN_PROGRESS' },
      currentFocus: mockCurrentFocus,
    };
    const availableContext = buildLearningContext(availableInput);
    assert.equal(availableContext.system_facts.prerequisites_met, true);
  });

  // --------------------------------------------------------------------------
  // Test 6 — Immutable Decision Action
  // --------------------------------------------------------------------------
  it('Test 6 — Immutable Decision Action: Decision Core 返回的 action 与 reason_code 不得被篡改', () => {
    const quizResponse: QuizSubmitResponse = {
      is_correct: true,
      correct_option: 'B',
      explanation: '正确，需求弹性计算符合定义',
      knowledge_id: 'K08',
      question_id: 'Q0801',
      event_id: 'evt-1001',
      replanning: mockUnlockReplanning,
    };

    const input: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: mockPathStates,
      currentFocus: mockCurrentFocus,
      recentQuizFeedback: quizResponse,
    };

    const context = buildLearningContext(input);
    assert.ok(context.system_facts.recent_quiz);
    assert.equal(context.system_facts.recent_quiz.action, 'UNLOCK_DOWNSTREAM');
    assert.equal(context.system_facts.recent_quiz.reason_code, 'MASTERY_THRESHOLD_REACHED');
    assert.equal(context.system_facts.recent_quiz.question_id, 'Q0801');
    assert.equal(context.system_facts.recent_quiz.is_correct, true);
  });

  // --------------------------------------------------------------------------
  // Test 7 — Truthful Unlock
  // --------------------------------------------------------------------------
  it('Test 7 — Truthful Unlock: 只有 UNLOCK_DOWNSTREAM 时才能在 Context 中表达真实解锁', () => {
    const quizResponse: QuizSubmitResponse = {
      is_correct: true,
      correct_option: 'B',
      explanation: '回答正确',
      knowledge_id: 'K08',
      question_id: 'Q0801',
      event_id: 'evt-1001',
      replanning: mockUnlockReplanning,
    };

    const input: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: mockPathStates,
      currentFocus: mockCurrentFocus,
      recentQuizFeedback: quizResponse,
    };

    const context = buildLearningContext(input);
    assert.ok(context.system_facts.recent_quiz);
    assert.deepEqual(context.system_facts.recent_quiz.unlocked_nodes, ['K09']);
    assert.ok(!context.system_facts.recent_quiz.unlocked_nodes.includes('K08'));
    assert.equal(context.system_facts.next_action.type, 'CONTINUE_NEXT');
  });

  // --------------------------------------------------------------------------
  // Test 8 — Retain Without Unlock
  // --------------------------------------------------------------------------
  it('Test 8 — Retain Without Unlock: RETAIN 决策时 unlocked_nodes 必须严格为空数组', () => {
    const quizResponse: QuizSubmitResponse = {
      is_correct: true,
      correct_option: 'B',
      explanation: '回答正确但未达标',
      knowledge_id: 'K08',
      question_id: 'Q0801',
      event_id: 'evt-1002',
      replanning: mockRetainReplanning,
    };

    const input: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: mockPathStates,
      currentFocus: mockCurrentFocus,
      recentQuizFeedback: quizResponse,
    };

    const context = buildLearningContext(input);
    assert.ok(context.system_facts.recent_quiz);
    assert.equal(context.system_facts.recent_quiz.action, 'RETAIN');
    assert.deepEqual(context.system_facts.recent_quiz.unlocked_nodes, []);
    assert.equal(context.system_facts.next_action.type, 'RETRY');
  });

  // --------------------------------------------------------------------------
  // Test 9 — Regression Preserved
  // --------------------------------------------------------------------------
  it('Test 9 — Regression Preserved: 认知回退时必须保留真实负向 delta 与回退事实', () => {
    const quizResponse: QuizSubmitResponse = {
      is_correct: false,
      correct_option: 'A',
      explanation: '回答错误',
      knowledge_id: 'K08',
      question_id: 'Q0801',
      event_id: 'evt-1003',
      replanning: mockRegressReplanning,
    };

    const input: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: mockPathStates,
      currentFocus: mockCurrentFocus,
      recentQuizFeedback: quizResponse,
    };

    const context = buildLearningContext(input);
    assert.ok(context.system_facts.recent_quiz);
    assert.equal(context.system_facts.recent_quiz.action, 'DEMOTE_TO_REVIEW');
    assert.ok(context.system_facts.recent_quiz.delta_percent < 0);
    assert.equal(context.system_facts.recent_quiz.before_mastery_percent, 81.18);
    assert.equal(context.system_facts.recent_quiz.after_mastery_percent, 65.0);
    assert.ok(context.derived_explanations.progression_summary?.includes('回退') || context.derived_explanations.action_guidance.includes('巩固'));
  });

  // --------------------------------------------------------------------------
  // Test 10 — Safe Terminal Fallback
  // --------------------------------------------------------------------------
  it('Test 10 — Safe Terminal Fallback: 路径终点或全完成时不得产生 undefined 或 null 节点名称', () => {
    const completedInput: LearningContextInput = {
      student: mockStudent,
      learningPath: [
        {
          stage: 1,
          knowledge_id: 'K30',
          knowledge_name: '博弈论与策略行为',
          chapter: '博弈论',
          current_accuracy: 95.0,
          priority: '中',
          priority_score: 70,
          learning_goal: '掌握纳什均衡',
          reason: '终点考点',
        },
      ],
      pathStates: { K30: 'COMPLETED' },
      currentFocus: {
        status: 'ALL_COMPLETED',
        message: '全部已完成',
      },
    };

    const context = buildLearningContext(completedInput);
    assert.notEqual(context.system_facts.current_knowledge_name, undefined);
    assert.notEqual(context.system_facts.current_knowledge_name, null);
    assert.notEqual(context.system_facts.current_knowledge_name, 'undefined');
    assert.notEqual(context.system_facts.current_knowledge_name, 'null');
    assert.equal(context.system_facts.is_path_completed, true);
    assert.equal(context.system_facts.next_action.type, 'RETURN_TASKS');
    assert.ok(context.system_facts.next_action.label.length > 0);
  });

  // --------------------------------------------------------------------------
  // Test 11 — Determinism
  // --------------------------------------------------------------------------
  it('Test 11 — Determinism: 相同输入连续构建 10 次，返回的 Context 必须深层等同且序列化一致', () => {
    const input: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: mockPathStates,
      currentFocus: mockCurrentFocus,
      recentQuizFeedback: {
        is_correct: true,
        correct_option: 'B',
        explanation: '回答正确',
        knowledge_id: 'K08',
        question_id: 'Q0801',
        event_id: 'evt-1001',
        replanning: mockUnlockReplanning,
      },
    };

    const first = buildLearningContext(input);
    const firstJson = JSON.stringify(first);

    for (let i = 0; i < 10; i++) {
      const current = buildLearningContext(input);
      assert.deepEqual(current, first);
      assert.equal(JSON.stringify(current), firstJson);
    }
  });

  // --------------------------------------------------------------------------
  // Test 12 — No Randomness
  // --------------------------------------------------------------------------
  it('Test 12 — No Randomness: Context 构建纯函数零随机性，禁止调用 Math.random 和 Date.now', () => {
    let randomCalled = false;
    let dateNowCalled = false;

    const originalRandom = Math.random;
    const originalDateNow = Date.now;

    Math.random = () => {
      randomCalled = true;
      return 0.5;
    };
    Date.now = () => {
      dateNowCalled = true;
      return 1773000000000;
    };

    try {
      const input: LearningContextInput = {
        student: mockStudent,
        learningPath: mockLearningPath,
        pathStates: mockPathStates,
        currentFocus: mockCurrentFocus,
      };

      buildLearningContext(input);

      assert.equal(randomCalled, false, 'Math.random must not be called during context build');
      assert.equal(dateNowCalled, false, 'Date.now must not be called during context build');
    } finally {
      Math.random = originalRandom;
      Date.now = originalDateNow;
    }
  });

  // --------------------------------------------------------------------------
  // Test 13 — AI Cannot Mutate Facts
  // --------------------------------------------------------------------------
  it('Test 13 — AI Cannot Mutate Facts: Context 必须为只读冻结结构，试图篡改系统事实将被阻止', () => {
    const input: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: mockPathStates,
      currentFocus: mockCurrentFocus,
    };

    const context = buildLearningContext(input);

    // 验证严格模式或运行时不可写
    assert.throws(() => {
      // @ts-expect-error - testing immutability contract
      context.system_facts.current_mastery_percent = 99;
    }, /TypeError|Cannot assign to read only property/);

    assert.throws(() => {
      // @ts-expect-error - testing immutability contract
      context.system_facts.current_knowledge_id = 'K99';
    }, /TypeError|Cannot assign to read only property/);
  });

  // --------------------------------------------------------------------------
  // Test 14 — No Decision Authority Leakage
  // --------------------------------------------------------------------------
  it('Test 14 — No Decision Authority Leakage: AI 解释层不得作为决策源，系统 next_action 独立且不可篡改', () => {
    const input: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: mockPathStates,
      currentFocus: mockCurrentFocus,
    };

    const context = buildLearningContext(input);

    // next_action 必须是标准 NextLearningAction 结构
    assert.ok(context.system_facts.next_action);
    assert.ok(['CONTINUE_NEXT', 'RETRY', 'RETURN_TASKS'].includes(context.system_facts.next_action.type));

    // derived_explanations 仅为解释文本，不得包含替代 next_action 的控制字段
    assert.equal(typeof context.derived_explanations.recommendation_reason, 'string');
    assert.equal(typeof context.derived_explanations.action_guidance, 'string');
    // @ts-expect-error - verify no rogue decision fields exist
    assert.equal(context.derived_explanations.next_action, undefined);
  });

  // --------------------------------------------------------------------------
  // Test 15 — Context Projection Completeness
  // --------------------------------------------------------------------------
  it('Test 15 — Context Projection Completeness: 所有输入关键字段完整投影至 Context', () => {
    const quizResponse: QuizSubmitResponse = {
      is_correct: true,
      correct_option: 'C',
      explanation: '解析内容',
      knowledge_id: 'K08',
      question_id: 'Q0801',
      event_id: 'evt-1001',
      replanning: mockUnlockReplanning,
    };

    const input: LearningContextInput = {
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: mockPathStates,
      currentFocus: mockCurrentFocus,
      recentQuizFeedback: quizResponse,
    };

    const context = buildLearningContext(input);

    // 检查 17 个关键系统事实完整性
    const sf = context.system_facts;
    assert.ok(sf.student_id);
    assert.ok(sf.student_name);
    assert.ok(sf.major);
    assert.ok(sf.grade);
    assert.ok(sf.learning_goal);
    assert.ok(sf.current_knowledge_id);
    assert.ok(sf.current_knowledge_name);
    assert.ok(sf.current_chapter);
    assert.ok(sf.current_path_state);
    assert.equal(typeof sf.current_mastery_percent, 'number');
    assert.equal(typeof sf.mastery_target_percent, 'number');
    assert.equal(typeof sf.mastery_target_threshold, 'number');
    assert.equal(typeof sf.mastery_gap_percent, 'number');
    assert.equal(typeof sf.is_mastered, 'boolean');
    assert.equal(typeof sf.prerequisites_met, 'boolean');
    assert.ok(sf.path_priority);
    assert.equal(typeof sf.is_path_completed, 'boolean');
    assert.ok(sf.recent_quiz);
    assert.ok(sf.next_action);
  });

  // --------------------------------------------------------------------------
  // Test 16 — Minimal Context Boundary
  // --------------------------------------------------------------------------
  it('Test 16 — Minimal Context Boundary: 不得将整个原始 raw 对象无筛选地透传进 Boundary', () => {
    const rawContaminatedStudent = {
      ...mockStudent,
      _raw_db_credentials: 'secret_token_12345',
      _internal_memory_pointer: 0xdeadbeef,
    };

    const input: LearningContextInput = {
      student: rawContaminatedStudent as StudentBasic,
      learningPath: mockLearningPath,
      pathStates: mockPathStates,
      currentFocus: mockCurrentFocus,
    };

    const context = buildLearningContext(input);

    // 验证内部非白名单字段被严格阻断在 Boundary 之外
    // @ts-expect-error - checking boundary filtering
    assert.equal(context.system_facts._raw_db_credentials, undefined);
    // @ts-expect-error - checking boundary filtering
    assert.equal(context.system_facts._internal_memory_pointer, undefined);
  });
});
