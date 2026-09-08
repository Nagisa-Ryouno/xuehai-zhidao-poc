/**
 * learning_prompt_contract.test.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-B
 * Prompt Context Formatter 契约测试 (Test 1 ~ Test 10)
 *
 * 核心验证：
 * 验证 LearningContext -> PromptContext 的白名单投影、确定性格式化、
 * 规则完整注入与私有/多余字段严格剔除。
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  StudentBasic,
  LearningPathStep,
  PathState,
  DecisionAuditEnvelope,
} from '../src/types.ts';

import {
  buildLearningContext,
  type LearningContextInput,
} from '../src/components/student/learningContextModel.ts';

import {
  buildLearningPromptContext,
  GROUNDING_RULES,
} from '../src/components/student/learningPromptModel.ts';

// 基础测试数据 fixture
const mockStudent: StudentBasic = {
  student_id: 'S001',
  student_name: '张小凡',
  major: '经济学',
  grade: '大二',
  learning_goal: '熟练掌握弹性理论',
};

const mockLearningPath: LearningPathStep[] = [
  {
    stage: 1,
    knowledge_id: 'K08',
    knowledge_name: '需求价格弹性',
    chapter: '微观经济学基础',
    current_accuracy: 46.0,
    priority: '高',
    priority_score: 95,
    learning_goal: '理解需求价格弹性定义',
    reason: '核心基础考点',
  },
  {
    stage: 2,
    knowledge_id: 'K09',
    knowledge_name: '收入与交叉弹性',
    chapter: '微观经济学基础',
    current_accuracy: 20.0,
    priority: '中',
    priority_score: 75,
    learning_goal: '掌握交叉弹性',
    reason: '后继考点',
  },
];

const mockPathStates: Record<string, PathState> = {
  K08: 'IN_PROGRESS',
  K09: 'AVAILABLE',
};

const mockReplanning: DecisionAuditEnvelope = {
  audit_metadata: {
    decision_id: 'dec-2001',
    timestamp: '2026-09-09T00:00:00Z',
    trace_id: 'trace-2001',
  },
  canonical_payload: {
    rule_version: 'v1.0',
    student_id: 'S001',
    knowledge_id: 'K08',
    before_mastery: '0.4600',
    after_mastery: '0.8118',
    before_path_state: 'IN_PROGRESS',
    after_path_state: 'COMPLETED',
    action: 'UNLOCK_DOWNSTREAM',
    reason_code: 'MASTERY_THRESHOLD_REACHED',
    affected_nodes: ['K08', 'K09'],
  },
};

describe('Phase 3 / Sprint 7-B: Prompt Context Formatter Contract Tests', () => {
  const baseContextInput: LearningContextInput = {
    student: mockStudent,
    learningPath: mockLearningPath,
    pathStates: mockPathStates,
    currentFocus: {
      status: 'FOUND',
      focus: {
        knowledgeId: 'K08',
        knowledgeName: '需求价格弹性',
        chapter: '微观经济学基础',
        pathState: 'IN_PROGRESS',
        currentMasteryPercent: 46,
        targetMasteryPercent: 80,
        reason: '核心基础考点',
        actionLabel: '继续挑战微测验',
        step: mockLearningPath[0],
      },
    },
    recentQuizFeedback: {
      is_correct: true,
      correct_option: 'B',
      explanation: '回答正确',
      knowledge_id: 'K08',
      question_id: 'Q0801',
      event_id: 'evt-2001',
      replanning: mockReplanning,
    },
  };

  const learningContext = buildLearningContext(baseContextInput);

  // --------------------------------------------------------------------------
  // Test 1 — Context Whitelist
  // --------------------------------------------------------------------------
  it('Test 1 — Context Whitelist: PromptContext 必须只包含白名单字段', () => {
    const promptContext = buildLearningPromptContext(
      learningContext,
      '我目前的学习情况怎么样？'
    );

    assert.ok(promptContext.user_question);
    assert.ok(promptContext.system_facts);
    assert.ok(Array.isArray(promptContext.grounding_rules));
    assert.equal(promptContext.grounding_rules.length, 10);
    assert.deepEqual(promptContext.grounding_rules, GROUNDING_RULES);
  });

  // --------------------------------------------------------------------------
  // Test 2 — Private Field Exclusion
  // --------------------------------------------------------------------------
  it('Test 2 — Private Field Exclusion: 外部私有或敏感字段被严格剔除在 Prompt 之外', () => {
    // 构造混入杂质的 LearningContext
    const taintedContext = {
      ...learningContext,
      system_facts: {
        ...learningContext.system_facts,
        _internal_token: 'secret_jwt_xyz',
        _debug_sql_query: 'SELECT * FROM users',
      },
    };

    // @ts-expect-error - testing boundary exclusion
    const promptContext = buildLearningPromptContext(taintedContext, '测试问题');

    // @ts-expect-error - assert private fields not leaked
    assert.equal(promptContext.system_facts._internal_token, undefined);
    // @ts-expect-error - assert private fields not leaked
    assert.equal(promptContext.system_facts._debug_sql_query, undefined);
  });

  // --------------------------------------------------------------------------
  // Test 3 — Deterministic Formatting
  // --------------------------------------------------------------------------
  it('Test 3 — Deterministic Formatting: 相同输入 10 次调用生成的 PromptContext 深度一致且 JSON 完全等同', () => {
    const first = buildLearningPromptContext(learningContext, '为什么推荐我学这个？');
    const firstJson = JSON.stringify(first);

    for (let i = 0; i < 10; i++) {
      const curr = buildLearningPromptContext(learningContext, '为什么推荐我学这个？');
      assert.deepEqual(curr, first);
      assert.equal(JSON.stringify(curr), firstJson);
    }
  });

  // --------------------------------------------------------------------------
  // Test 4 — User Question Preserved
  // --------------------------------------------------------------------------
  it('Test 4 — User Question Preserved: 用户提问文本完整保留并去除首尾空白', () => {
    const rawQuestion = '  我现在的掌握度距离目标还差多少？ \n ';
    const promptContext = buildLearningPromptContext(learningContext, rawQuestion);

    assert.equal(promptContext.user_question, '我现在的掌握度距离目标还差多少？');
  });

  // --------------------------------------------------------------------------
  // Test 5 — Mastery Preserved
  // --------------------------------------------------------------------------
  it('Test 5 — Mastery Preserved: 当前掌握度与差距百分比严格与系统事实一致', () => {
    const promptContext = buildLearningPromptContext(learningContext, '查询掌握度');

    assert.equal(promptContext.system_facts.current_mastery_percent, 46);
    assert.equal(promptContext.system_facts.mastery_gap_percent, 34);
    assert.equal(promptContext.system_facts.is_mastered, false);
  });

  // --------------------------------------------------------------------------
  // Test 6 — Threshold Preserved
  // --------------------------------------------------------------------------
  it('Test 6 — Threshold Preserved: 达标阈值严格保留为全站统一常量 80', () => {
    const promptContext = buildLearningPromptContext(learningContext, '达标标准是什么？');

    assert.equal(promptContext.system_facts.mastery_target_percent, 80);
  });

  // --------------------------------------------------------------------------
  // Test 7 — PathState Preserved
  // --------------------------------------------------------------------------
  it('Test 7 — PathState Preserved: 当前考点路径状态与前置就绪事实严格保留', () => {
    const promptContext = buildLearningPromptContext(learningContext, '当前状态？');

    assert.equal(promptContext.system_facts.current_path_state, 'IN_PROGRESS');
    assert.equal(promptContext.system_facts.prerequisites_met, true);
  });

  // --------------------------------------------------------------------------
  // Test 8 — NextAction Preserved
  // --------------------------------------------------------------------------
  it('Test 8 — NextAction Preserved: 系统确定的下一步行动严格保留', () => {
    const promptContext = buildLearningPromptContext(learningContext, '下一步做什么？');

    assert.ok(promptContext.system_facts.next_action);
    assert.equal(promptContext.system_facts.next_action.type, 'CONTINUE_NEXT');
    assert.equal(promptContext.system_facts.next_action.knowledgeId, 'K09');
  });

  // --------------------------------------------------------------------------
  // Test 9 — No Hidden Decision Fields
  // --------------------------------------------------------------------------
  it('Test 9 — No Hidden Decision Fields: PromptContext 绝不包含任何让 AI 逆向决策的隐式控制字段', () => {
    const promptContext = buildLearningPromptContext(learningContext, '提问');

    // @ts-expect-error - verifying no backdoor execution keys exist
    assert.equal(promptContext.mutate_path_state, undefined);
    // @ts-expect-error - verifying no backdoor execution keys exist
    assert.equal(promptContext.allow_override_action, undefined);
  });

  // --------------------------------------------------------------------------
  // Test 10 — No Randomness
  // --------------------------------------------------------------------------
  it('Test 10 — No Randomness: Prompt 格式化纯函数禁止调用 Math.random 和 Date.now', () => {
    let randomCalled = false;
    let dateNowCalled = false;

    const originalRandom = Math.random;
    const originalDateNow = Date.now;

    Math.random = () => {
      randomCalled = true;
      return 0.123;
    };
    Date.now = () => {
      dateNowCalled = true;
      return 1773000000000;
    };

    try {
      buildLearningPromptContext(learningContext, '纯函数测试');
      assert.equal(randomCalled, false, 'Math.random must not be called');
      assert.equal(dateNowCalled, false, 'Date.now must not be called');
    } finally {
      Math.random = originalRandom;
      Date.now = originalDateNow;
    }
  });
});
