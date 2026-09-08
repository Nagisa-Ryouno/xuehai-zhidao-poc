/**
 * ai_provider_contract.test.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-C
 * AI Provider 抽象层契约测试 (Test 1 ~ Test 8)
 *
 * 核心验证：
 * 验证 AI Provider 抽象层的入参白名单限制、MockProvider 的结构化契约、
 * 确定性输出、输入不可变性、异常隔离、非法结构兜底与拒识隔离。
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
  type LearningPromptContext,
} from '../src/components/student/learningPromptModel.ts';

import type { AIProvider } from '../src/components/student/aiProvider.ts';
import { MockAIProvider } from '../src/components/student/mockAIProvider.ts';
import { askLearningCompanion } from '../src/components/student/aiCompanionService.ts';

// 基础测试 fixture
const mockStudent: StudentBasic = {
  student_id: 'S001',
  student_name: '张小凡',
  major: '经济学',
  grade: '大二',
  learning_goal: '掌握弹性理论',
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
    learning_goal: '理解弹性定义',
    reason: '核心基础考点',
  },
];

const mockPathStates: Record<string, PathState> = {
  K08: 'IN_PROGRESS',
};

const mockReplanning: DecisionAuditEnvelope = {
  audit_metadata: {
    decision_id: 'dec-4001',
    timestamp: '2026-09-09T00:00:00Z',
  },
  canonical_payload: {
    rule_version: 'v1.0',
    student_id: 'S001',
    knowledge_id: 'K08',
    before_mastery: '0.4600',
    after_mastery: '0.4600',
    before_path_state: 'IN_PROGRESS',
    after_path_state: 'IN_PROGRESS',
    action: 'RETAIN',
    reason_code: 'MASTERY_STATE_UNCHANGED',
    affected_nodes: ['K08'],
  },
};

describe('Phase 3 / Sprint 7-C: AI Provider Contract Tests', () => {
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
      event_id: 'evt-4001',
      replanning: mockReplanning,
    },
  };

  const learningContext = buildLearningContext(baseContextInput);
  const promptContext = buildLearningPromptContext(learningContext, '我目前的掌握度如何？');

  // --------------------------------------------------------------------------
  // Test 1 — Provider Context Boundary
  // --------------------------------------------------------------------------
  it('Test 1 — Provider Context Boundary: Provider 接口只能消费 LearningPromptContext 白名单', async () => {
    let capturedKeys: string[] = [];

    const inspectingProvider: AIProvider = {
      async generate(ctx: LearningPromptContext) {
        capturedKeys = Object.keys(ctx);
        return {
          answer: '验证输入参数结构',
          referenced_facts: ['test=1'],
          grounding_status: 'grounded',
        };
      },
    };

    await inspectingProvider.generate(promptContext);

    assert.ok(capturedKeys.includes('user_question'));
    assert.ok(capturedKeys.includes('system_facts'));
    assert.ok(capturedKeys.includes('grounding_rules'));

    // 严禁包含 raw 业务对象 (如 student, learningPath, pathStates, Decision Core)
    assert.equal(capturedKeys.includes('student'), false);
    assert.equal(capturedKeys.includes('learningPath'), false);
    assert.equal(capturedKeys.includes('pathStates'), false);
    assert.equal(capturedKeys.includes('decision_core'), false);
  });

  // --------------------------------------------------------------------------
  // Test 2 — Mock Provider Structured Response
  // --------------------------------------------------------------------------
  it('Test 2 — Mock Provider Structured Response: Mock Provider 输出结构完全符合 StructuredAIResponse', async () => {
    const provider = new MockAIProvider();
    const res = await provider.generate(promptContext);

    assert.equal(typeof res.answer, 'string');
    assert.ok(res.answer.length > 0);
    assert.ok(Array.isArray(res.referenced_facts));
    assert.equal(res.grounding_status, 'grounded');
  });

  // --------------------------------------------------------------------------
  // Test 3 — Zero Decision Authority
  // --------------------------------------------------------------------------
  it('Test 3 — Zero Decision Authority: Provider 返回对象绝无 next_action、decision、unlock_nodes 等决策字段', async () => {
    const provider = new MockAIProvider();
    const res = await provider.generate(promptContext);

    // @ts-expect-error - verifying no decision mutation keys exist
    assert.equal(res.next_action, undefined);
    // @ts-expect-error - verifying no decision mutation keys exist
    assert.equal(res.decision, undefined);
    // @ts-expect-error - verifying no decision mutation keys exist
    assert.equal(res.unlock_nodes, undefined);
    // @ts-expect-error - verifying no decision mutation keys exist
    assert.equal(res.mutate_path_state, undefined);
  });

  // --------------------------------------------------------------------------
  // Test 4 — Deterministic Output
  // --------------------------------------------------------------------------
  it('Test 4 — Deterministic Output: 相同输入连续调用 10 次，Mock Provider 产出完全一致', async () => {
    const provider = new MockAIProvider();
    const first = await provider.generate(promptContext);
    const firstJson = JSON.stringify(first);

    for (let i = 0; i < 10; i++) {
      const current = await provider.generate(promptContext);
      assert.deepEqual(current, first);
      assert.equal(JSON.stringify(current), firstJson);
    }
  });

  // --------------------------------------------------------------------------
  // Test 5 — Immutable Input
  // --------------------------------------------------------------------------
  it('Test 5 — Immutable Input: Provider 执行期间不得修改传入的 PromptContext', async () => {
    const provider = new MockAIProvider();
    const contextSnapshot = JSON.stringify(promptContext);

    await provider.generate(promptContext);

    assert.equal(JSON.stringify(promptContext), contextSnapshot);
  });

  // --------------------------------------------------------------------------
  // Test 6 — Provider Exception Containment
  // --------------------------------------------------------------------------
  it('Test 6 — Provider Exception Containment: Provider 抛出异常被 Service 安全隔离并降级为 SafeFallback', async () => {
    const crashingProvider = new MockAIProvider({ mode: 'throw_error' });

    const groundedAnswer = await askLearningCompanion(
      learningContext,
      '我的掌握度如何？',
      crashingProvider
    );

    assert.equal(groundedAnswer.grounding_status, 'fallback');
    assert.equal(groundedAnswer.validation_reason, 'PROVIDER_EXCEPTION');
    assert.ok(groundedAnswer.answer.includes('当前回答包含系统无法验证的学习事实'));
    assert.ok(groundedAnswer.answer.includes('当前掌握度：46%'));
  });

  // --------------------------------------------------------------------------
  // Test 7 — Malformed Response Containment
  // --------------------------------------------------------------------------
  it('Test 7 — Malformed Response Containment: Provider 返回非法/畸形结构时被安全拦截并进入 SafeFallback', async () => {
    const malformedProvider = new MockAIProvider({ mode: 'malformed' });

    const groundedAnswer = await askLearningCompanion(
      learningContext,
      '我的掌握度如何？',
      malformedProvider
    );

    assert.equal(groundedAnswer.grounding_status, 'fallback');
    assert.equal(groundedAnswer.validation_reason, 'MALFORMED_RESPONSE');
    assert.ok(groundedAnswer.answer.includes('当前回答包含系统无法验证的学习事实'));
  });

  // --------------------------------------------------------------------------
  // Test 8 — Rejected Response Isolation
  // --------------------------------------------------------------------------
  it('Test 8 — Rejected Response Isolation: Validator REJECT 后原始 AI 幻觉内容绝对不得进入最终 GroundedAnswer', async () => {
    // 模拟编造掌握度 80% 的模型
    const hallucinatingProvider = new MockAIProvider({ mode: 'mastery_hallucination' });

    const groundedAnswer = await askLearningCompanion(
      learningContext,
      '我的掌握度如何？',
      hallucinatingProvider
    );

    // 最终输出绝不得包含原始幻觉吹捧文案
    assert.equal(groundedAnswer.grounding_status, 'fallback');
    assert.equal(groundedAnswer.validation_reason, 'MASTERY_HALLUCINATION');
    assert.equal(groundedAnswer.answer.includes('表现非常优秀'), false);
    // 必须包含真实系统客观事实 46%
    assert.ok(groundedAnswer.answer.includes('当前掌握度：46%'));
  });
});
