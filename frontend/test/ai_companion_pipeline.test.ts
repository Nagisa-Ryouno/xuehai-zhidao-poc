/**
 * ai_companion_pipeline.test.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-C
 * AI Companion 全链路管线与容灾契约测试 (Test 9 ~ Test 28)
 *
 * 核心验证：
 * 1. 完整链路流转：Context -> Prompt -> MockProvider -> Validator -> GroundedAnswer
 * 2. 事实一致性与全品类幻觉拦截：掌握度、解锁、状态矛盾、回退矛盾、未知考点与统计
 * 3. 故障容灾隔离：超时、致命崩溃、非法结构、空上下文安全防御
 * 4. 确定性与零副作用契约：多次调用幂等一致，AI 故障绝不影响底层学习引擎
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

import { MockAIProvider } from '../src/components/student/mockAIProvider.ts';
import { askLearningCompanion } from '../src/components/student/aiCompanionService.ts';
import { validateAIResponse, createDeterministicFallback } from '../src/components/student/aiResponseValidator.ts';
import type { AIProvider } from '../src/components/student/aiProvider.ts';

// 基础测试 fixture
const mockStudent: StudentBasic = {
  student_id: 'S001',
  student_name: '张小凡',
  major: '经济学',
  grade: '大二',
  learning_goal: '熟练掌握微观弹性分析',
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
    learning_goal: '掌握弹性定义',
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

const mockRetainReplanning: DecisionAuditEnvelope = {
  audit_metadata: {
    decision_id: 'dec-5001',
    timestamp: '2026-09-09T00:00:00Z',
  },
  canonical_payload: {
    rule_version: 'v1.0',
    student_id: 'S001',
    knowledge_id: 'K08',
    before_mastery: '0.4600',
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
    decision_id: 'dec-5002',
    timestamp: '2026-09-09T00:05:00Z',
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

describe('Phase 3 / Sprint 7-C: AI Companion Pipeline Integration & Failure Tests', () => {
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
      explanation: '回答正确但未达标',
      knowledge_id: 'K08',
      question_id: 'Q0801',
      event_id: 'evt-5001',
      replanning: mockRetainReplanning,
    },
  };

  const baseContext = buildLearningContext(baseContextInput);

  // --------------------------------------------------------------------------
  // Test 9 — Full End-to-End Pipeline
  // --------------------------------------------------------------------------
  it('Test 9 — Full End-to-End Pipeline: Context -> Prompt -> MockProvider -> Validator -> GroundedAnswer 链路打通', async () => {
    const provider = new MockAIProvider();
    const result = await askLearningCompanion(baseContext, '我目前的掌握情况怎么样？', provider);

    assert.ok(result.answer);
    assert.equal(result.grounding_status, 'grounded');
    assert.ok(result.answer.includes('需求价格弹性'));
  });

  // --------------------------------------------------------------------------
  // Test 10 — Valid Grounded Answer Flow
  // --------------------------------------------------------------------------
  it('Test 10 — Valid Grounded Answer Flow: 合法回答通过 FactValidator 并保留完整内容', async () => {
    const provider = new MockAIProvider({
      customResponse: {
        answer: '你当前正在学习需求价格弹性，掌握度为 46%，全站掌握目标是 80%，距离达标还有 34% 差距，系统建议继续挑战微测验。',
        referenced_facts: ['current_mastery_percent=46', 'mastery_target_percent=80'],
        grounding_status: 'grounded',
      },
    });

    const result = await askLearningCompanion(baseContext, '查询掌握度', provider);

    assert.equal(result.grounding_status, 'grounded');
    assert.ok(result.answer.includes('掌握度为 46%'));
    assert.ok(result.answer.includes('还有 34% 差距'));
  });

  // --------------------------------------------------------------------------
  // Test 11 — Mastery Hallucination Interception
  // --------------------------------------------------------------------------
  it('Test 11 — Mastery Hallucination Interception: 虚假掌握度被拦截并回退至真实掌握度', async () => {
    const provider = new MockAIProvider({ mode: 'mastery_hallucination' });
    const result = await askLearningCompanion(baseContext, '我掌握了吗？', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'MASTERY_HALLUCINATION');
    assert.ok(result.answer.includes('当前掌握度：46%'));
    assert.ok(result.answer.includes('达标目标：80%'));
    assert.equal(result.answer.includes('表现非常优秀'), false);
  });

  // --------------------------------------------------------------------------
  // Test 12 — Fake Unlock Interception
  // --------------------------------------------------------------------------
  it('Test 12 — Fake Unlock Interception: 未解锁时声称解锁被拦截并回退至 SafeFallback', async () => {
    const provider = new MockAIProvider({ mode: 'fake_unlock' });
    const result = await askLearningCompanion(baseContext, '考点解锁了吗？', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'FAKE_UNLOCK');
    assert.ok(result.answer.includes('当前回答包含系统无法验证的学习事实'));
  });

  // --------------------------------------------------------------------------
  // Test 13 — RETAIN Contradiction Interception
  // --------------------------------------------------------------------------
  it('Test 13 — RETAIN Contradiction Interception: 保持状态下声称晋升下一考点被拦截', async () => {
    const provider = new MockAIProvider({ mode: 'retain_contradiction' });
    const result = await askLearningCompanion(baseContext, '我现在学什么？', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'RETAIN_CONTRADICTION');
    assert.ok(result.answer.includes('当前回答包含系统无法验证的学习事实'));
  });

  // --------------------------------------------------------------------------
  // Test 14 — REGRESS Contradiction Interception
  // --------------------------------------------------------------------------
  it('Test 14 — REGRESS Contradiction Interception: 认知回退决策下声称掌握度提升被拦截', async () => {
    const regressContext = buildLearningContext({
      ...baseContextInput,
      recentQuizFeedback: {
        is_correct: false,
        correct_option: 'A',
        explanation: '回答错误',
        knowledge_id: 'K08',
        question_id: 'Q0801',
        event_id: 'evt-5002',
        replanning: mockRegressReplanning,
      },
    });

    const provider = new MockAIProvider({ mode: 'regress_contradiction' });
    const result = await askLearningCompanion(regressContext, '我刚才答得怎么样？', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'REGRESS_CONTRADICTION');
    assert.ok(result.answer.includes('当前回答包含系统无法验证的学习事实'));
  });

  // --------------------------------------------------------------------------
  // Test 15 — LOCKED Contradiction Interception
  // --------------------------------------------------------------------------
  it('Test 15 — LOCKED Contradiction Interception: 考点被锁定受阻时声称可直接开始学习被拦截', async () => {
    const lockedContext = buildLearningContext({
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: { K08: 'LOCKED' },
      currentFocus: {
        status: 'FOUND',
        focus: {
          knowledgeId: 'K08',
          knowledgeName: '需求价格弹性',
          chapter: '微观经济学基础',
          pathState: 'LOCKED',
          currentMasteryPercent: 0,
          targetMasteryPercent: 80,
          reason: '前置受阻',
          actionLabel: '需先攻坚前置',
          step: mockLearningPath[0],
        },
      },
    });

    const provider = new MockAIProvider({ mode: 'locked_contradiction' });
    const result = await askLearningCompanion(lockedContext, '我可以开始了吗？', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'LOCKED_CONTRADICTION');
  });

  // --------------------------------------------------------------------------
  // Test 16 — Unknown Knowledge Point Interception
  // --------------------------------------------------------------------------
  it('Test 16 — Unknown Knowledge Point Interception: 出现 Context 中不存在的考点代号（如 K99）被拦截', async () => {
    const provider = new MockAIProvider({ mode: 'unknown_knowledge_point' });
    const result = await askLearningCompanion(baseContext, '推荐考点？', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'UNKNOWN_KNOWLEDGE_POINT');
  });

  // --------------------------------------------------------------------------
  // Test 17 — Unknown Numeric Fact Interception
  // --------------------------------------------------------------------------
  it('Test 17 — Unknown Numeric Fact Interception: 编造排名或累计学时被拦截', async () => {
    const provider = new MockAIProvider({ mode: 'unknown_numeric_fact' });
    const result = await askLearningCompanion(baseContext, '我的排名？', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'UNKNOWN_NUMERIC_FACT');
  });

  // --------------------------------------------------------------------------
  // Test 18 — SafeFallback Self-Validation
  // --------------------------------------------------------------------------
  it('Test 18 — SafeFallback Self-Validation: 生成的 SafeFallback 自身必须通过 FactValidator', () => {
    const fallbackResponse = createDeterministicFallback(baseContext, 'MASTERY_HALLUCINATION');
    const checkResult = validateAIResponse(baseContext, fallbackResponse);

    assert.equal(checkResult.status, 'PASS', 'Safe fallback must not contradict itself');
  });

  // --------------------------------------------------------------------------
  // Test 19 — Provider Timeout Handling
  // --------------------------------------------------------------------------
  it('Test 19 — Provider Timeout Handling: 当 Provider 响应超时，Service 自动捕获并安全降级为 Fallback', async () => {
    const timeoutProvider = new MockAIProvider({ mode: 'timeout' });

    const result = await askLearningCompanion(baseContext, '超时测试', timeoutProvider, {
      timeoutMs: 50, // 50ms 触发超时
    });

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'PROVIDER_TIMEOUT');
    assert.ok(result.answer.includes('当前回答包含系统无法验证的学习事实'));
  });

  // --------------------------------------------------------------------------
  // Test 20 — Provider Fatal Exception Handling
  // --------------------------------------------------------------------------
  it('Test 20 — Provider Fatal Exception Handling: Provider 发生致命崩溃时被安全捕获', async () => {
    const crashingProvider: AIProvider = {
      async generate() {
        throw new Error('Network disconnection: 503 Gateway Timeout');
      },
    };

    const result = await askLearningCompanion(baseContext, '崩溃测试', crashingProvider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'PROVIDER_EXCEPTION');
    assert.ok(result.answer.includes('当前掌握度：46%'));
  });

  // --------------------------------------------------------------------------
  // Test 21 — Malformed Non-Object Response Handling
  // --------------------------------------------------------------------------
  it('Test 21 — Malformed Non-Object Response Handling: Provider 返回 null/undefined 时安全捕获', async () => {
    const nullProvider: AIProvider = {
      // @ts-expect-error - testing invalid response handling
      async generate() {
        return null;
      },
    };

    const result = await askLearningCompanion(baseContext, '非法返回测试', nullProvider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'MALFORMED_RESPONSE');
  });

  // --------------------------------------------------------------------------
  // Test 22 — Malformed Missing Answer Field Handling
  // --------------------------------------------------------------------------
  it('Test 22 — Malformed Missing Answer Field Handling: Provider 返回非字符串 answer 时安全捕获', async () => {
    const badFieldProvider: AIProvider = {
      // @ts-expect-error - testing missing string answer field
      async generate() {
        return { answer: 12345, grounding_status: 'grounded' };
      },
    };

    const result = await askLearningCompanion(baseContext, '缺少字段测试', badFieldProvider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'MALFORMED_RESPONSE');
  });

  // --------------------------------------------------------------------------
  // Test 23 — Empty Context Safeguard
  // --------------------------------------------------------------------------
  it('Test 23 — Empty Context Safeguard: 传入无效 Context 时安全收敛为 Fallback 绝不崩溃', async () => {
    // @ts-expect-error - testing invalid context defense
    const result = await askLearningCompanion(null, '无上下文提问');

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'EMPTY_CONTEXT');
  });

  // --------------------------------------------------------------------------
  // Test 24 — User Question Whitespace & Sanitization
  // --------------------------------------------------------------------------
  it('Test 24 — User Question Whitespace & Sanitization: 包含大量空白的提问被正常清洗后处理', async () => {
    const provider = new MockAIProvider();
    const result = await askLearningCompanion(baseContext, '   \n 掌握度如何？ \t  ', provider);

    assert.equal(result.grounding_status, 'grounded');
    assert.ok(result.answer.includes('46%'));
  });

  // --------------------------------------------------------------------------
  // Test 25 — Pipeline Determinism (10 Invocations)
  // --------------------------------------------------------------------------
  it('Test 25 — Pipeline Determinism: 相同输入连续执行 10 次，Pipeline 产出完全一致', async () => {
    const provider = new MockAIProvider();
    const first = await askLearningCompanion(baseContext, '为什么推荐我学这个？', provider);
    const firstJson = JSON.stringify(first);

    for (let i = 0; i < 10; i++) {
      const current = await askLearningCompanion(baseContext, '为什么推荐我学这个？', provider);
      assert.deepEqual(current, first);
      assert.equal(JSON.stringify(current), firstJson);
    }
  });

  // --------------------------------------------------------------------------
  // Test 26 — No Side Effects on Core Learning State
  // --------------------------------------------------------------------------
  it('Test 26 — No Side Effects on Core Learning State: 调用 AI 伴学前后，底层学情上下文绝不受影响', async () => {
    const originalMastery = baseContext.system_facts.current_mastery_percent;
    const originalPathState = baseContext.system_facts.current_path_state;
    const originalNextAction = baseContext.system_facts.next_action;

    const provider = new MockAIProvider({ mode: 'mastery_hallucination' });
    await askLearningCompanion(baseContext, '提问', provider);

    assert.equal(baseContext.system_facts.current_mastery_percent, originalMastery);
    assert.equal(baseContext.system_facts.current_path_state, originalPathState);
    assert.deepEqual(baseContext.system_facts.next_action, originalNextAction);
  });

  // --------------------------------------------------------------------------
  // Test 27 — Failure Isolation / System Resilience
  // --------------------------------------------------------------------------
  it('Test 27 — Failure Isolation / System Resilience: 即使 AI 崩溃或异常，学习系统的核心状态推导与路径逻辑依然健在', async () => {
    const crashingProvider = new MockAIProvider({ mode: 'throw_error' });

    // AI 伴学服务抛出异常并捕获
    const aiResult = await askLearningCompanion(baseContext, '崩溃', crashingProvider);
    assert.equal(aiResult.grounding_status, 'fallback');

    // 核心引擎事实依旧健康完整
    assert.equal(baseContext.system_facts.is_path_completed, false);
    assert.equal(baseContext.system_facts.prerequisites_met, true);
    assert.equal(baseContext.system_facts.next_action.type, 'RETRY');
  });

  // --------------------------------------------------------------------------
  // Test 28 — Safe Fallback Grounding Status Contract
  // --------------------------------------------------------------------------
  it('Test 28 — Safe Fallback Grounding Status Contract: 所有降级回答必须显式标明 fallback 与 reason', async () => {
    const provider = new MockAIProvider({ mode: 'fake_unlock' });
    const result = await askLearningCompanion(baseContext, '已解锁？', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.ok(result.validation_reason);
    assert.equal(typeof result.validation_reason, 'string');
    assert.ok(Array.isArray(result.referenced_facts));
  });
});
