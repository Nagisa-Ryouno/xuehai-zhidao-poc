/**
 * ai_response_validation.test.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-B
 * AI Response Fact Validator 契约测试 (Test 11 ~ Test 20)
 *
 * 核心验证：
 * 验证 FactValidator 对大模型输出的事实一致性校验与幻觉阻断防御，
 * 杜绝虚假掌握度、虚假阈值、虚假解锁、状态矛盾、未知节点与编造事实，
 * 并保证被阻断时能产出完全基于系统事实的确定性 Safe Fallback。
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
} from '../src/components/student/learningContextModel.ts';

import type { StructuredAIResponse } from '../src/components/student/aiResponseModel.ts';

import {
  validateAIResponse,
  createDeterministicFallback,
} from '../src/components/student/aiResponseValidator.ts';

// 基础测试 fixture
const mockStudent: StudentBasic = {
  student_id: 'S001',
  student_name: '张小凡',
  major: '经济学',
  grade: '大二',
  learning_goal: '掌握微观经济学弹性分析',
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
  {
    stage: 3,
    knowledge_id: 'K11',
    knowledge_name: '弹性与税收归宿',
    chapter: '微观经济学应用',
    current_accuracy: 0.0,
    priority: '高',
    priority_score: 85,
    learning_goal: '综合分析税负归宿',
    reason: '复合后继考点',
  },
];

const mockPathStates: Record<string, PathState> = {
  K08: 'IN_PROGRESS',
  K09: 'AVAILABLE',
  K11: 'LOCKED',
};

const mockRetainReplanning: DecisionAuditEnvelope = {
  audit_metadata: {
    decision_id: 'dec-3001',
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
    decision_id: 'dec-3002',
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

describe('Phase 3 / Sprint 7-B: AI Response Fact Validator Contract Tests', () => {
  // 构建基准 LearningContext（掌握度 46%，目标 80%，状态 IN_PROGRESS，未解锁后继）
  const baseContext = buildLearningContext({
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
      event_id: 'evt-3001',
      replanning: mockRetainReplanning,
    },
  });

  // --------------------------------------------------------------------------
  // Test 11 — Valid Grounded Response PASS
  // --------------------------------------------------------------------------
  it('Test 11 — Valid Grounded Response PASS: 符合客观事实的回答必须通过校验', () => {
    const validResponse: StructuredAIResponse = {
      answer: '你当前正在学习需求价格弹性，掌握度为 46%，全站掌握目标是 80%，距离达标还有 34% 差距，系统建议继续挑战微测验。',
      referenced_facts: ['current_mastery_percent=46', 'mastery_target_percent=80'],
      grounding_status: 'grounded',
    };

    const result = validateAIResponse(baseContext, validResponse);

    assert.equal(result.status, 'PASS');
    if (result.status === 'PASS') {
      assert.equal(result.response.answer, validResponse.answer);
    }
  });

  // --------------------------------------------------------------------------
  // Test 12 — Mastery Hallucination REJECT
  // --------------------------------------------------------------------------
  it('Test 12 — Mastery Hallucination REJECT: 伪造虚假掌握度数值必须被阻断', () => {
    // 真实掌握度为 46%，AI 声称已经掌握了 80%
    const hallucinatedResponse: StructuredAIResponse = {
      answer: '恭喜你！你对需求价格弹性的掌握度达到了 80%，表现非常优秀！',
      referenced_facts: ['current_mastery_percent=80'],
      grounding_status: 'grounded',
    };

    const result = validateAIResponse(baseContext, hallucinatedResponse);

    assert.equal(result.status, 'REJECT');
    if (result.status === 'REJECT') {
      assert.equal(result.reason, 'MASTERY_HALLUCINATION');
      assert.ok(result.fallback.answer.includes('当前掌握度：46%'));
    }
  });

  // --------------------------------------------------------------------------
  // Test 13 — Threshold Hallucination REJECT
  // --------------------------------------------------------------------------
  it('Test 13 — Threshold Hallucination REJECT: 伪造非 80% 的虚假达标线必须被阻断', () => {
    // 真实达标目标为 80%，AI 宣称达标线是 70%
    const hallucinatedResponse: StructuredAIResponse = {
      answer: '你的需求价格弹性掌握度为 46%，只要达到达标线 70% 就可以解锁下一考点。',
      referenced_facts: ['mastery_target_percent=70'],
      grounding_status: 'grounded',
    };

    const result = validateAIResponse(baseContext, hallucinatedResponse);

    assert.equal(result.status, 'REJECT');
    if (result.status === 'REJECT') {
      assert.equal(result.reason, 'THRESHOLD_HALLUCINATION');
      assert.ok(result.fallback.answer.includes('达标目标：80%'));
    }
  });

  // --------------------------------------------------------------------------
  // Test 14 — Fake Unlock REJECT
  // --------------------------------------------------------------------------
  it('Test 14 — Fake Unlock REJECT: 当未发生解锁时声称解锁了下一考点必须被阻断', () => {
    // baseContext 中 recent_quiz action 为 RETAIN，unlocked_nodes 为 []
    const fakeUnlockResponse: StructuredAIResponse = {
      answer: '太棒了，系统刚才已经为你解锁了下一个考点，现在可以去学习新内容了！',
      referenced_facts: ['unlocked_nodes=K09'],
      grounding_status: 'grounded',
    };

    const result = validateAIResponse(baseContext, fakeUnlockResponse);

    assert.equal(result.status, 'REJECT');
    if (result.status === 'REJECT') {
      assert.equal(result.reason, 'FAKE_UNLOCK');
      assert.ok(result.fallback);
    }
  });

  // --------------------------------------------------------------------------
  // Test 15 — RETAIN Contradiction REJECT
  // --------------------------------------------------------------------------
  it('Test 15 — RETAIN Contradiction REJECT: 保持原状态决策下声称已进入下一知识点必须被阻断', () => {
    const retainContradictionResponse: StructuredAIResponse = {
      answer: '你已经进入下一个知识点收入与交叉弹性的学习。',
      referenced_facts: ['action=RETAIN'],
      grounding_status: 'grounded',
    };

    const result = validateAIResponse(baseContext, retainContradictionResponse);

    assert.equal(result.status, 'REJECT');
    if (result.status === 'REJECT') {
      assert.equal(result.reason, 'RETAIN_CONTRADICTION');
    }
  });

  // --------------------------------------------------------------------------
  // Test 16 — REGRESS Contradiction REJECT
  // --------------------------------------------------------------------------
  it('Test 16 — REGRESS Contradiction REJECT: 认知回退决策下声称掌握度提升必须被阻断', () => {
    const regressContext = buildLearningContext({
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
          currentMasteryPercent: 65,
          targetMasteryPercent: 80,
          reason: '核心考点',
          actionLabel: '继续挑战微测验',
          step: mockLearningPath[0],
        },
      },
      recentQuizFeedback: {
        is_correct: false,
        correct_option: 'A',
        explanation: '回答错误',
        knowledge_id: 'K08',
        question_id: 'Q0801',
        event_id: 'evt-3002',
        replanning: mockRegressReplanning,
      },
    });

    const falseProgressResponse: StructuredAIResponse = {
      answer: '你在本次测验中掌握度继续提升，请继续保持这种势头！',
      referenced_facts: ['action=DEMOTE_TO_REVIEW'],
      grounding_status: 'grounded',
    };

    const result = validateAIResponse(regressContext, falseProgressResponse);

    assert.equal(result.status, 'REJECT');
    if (result.status === 'REJECT') {
      assert.equal(result.reason, 'REGRESS_CONTRADICTION');
    }
  });

  // --------------------------------------------------------------------------
  // Test 17 — LOCKED Contradiction REJECT
  // --------------------------------------------------------------------------
  it('Test 17 — LOCKED Contradiction REJECT: 考点被锁定受阻时声称可以直接开始学习必须被阻断', () => {
    const lockedContext = buildLearningContext({
      student: mockStudent,
      learningPath: mockLearningPath,
      pathStates: { K11: 'LOCKED' },
      currentFocus: {
        status: 'FOUND',
        focus: {
          knowledgeId: 'K11',
          knowledgeName: '弹性与税收归宿',
          chapter: '微观经济学应用',
          pathState: 'LOCKED',
          currentMasteryPercent: 0,
          targetMasteryPercent: 80,
          reason: '复合后继',
          actionLabel: '需先掌握前置',
          step: mockLearningPath[2],
        },
      },
    });

    const lockedContradictionResponse: StructuredAIResponse = {
      answer: '对于弹性与税收归宿，你现在可以直接开始学习这个知识点并参加微测验。',
      referenced_facts: ['pathState=LOCKED'],
      grounding_status: 'grounded',
    };

    const result = validateAIResponse(lockedContext, lockedContradictionResponse);

    assert.equal(result.status, 'REJECT');
    if (result.status === 'REJECT') {
      assert.equal(result.reason, 'LOCKED_CONTRADICTION');
    }
  });

  // --------------------------------------------------------------------------
  // Test 18 — Unknown Knowledge Point REJECT
  // --------------------------------------------------------------------------
  it('Test 18 — Unknown Knowledge Point REJECT: 出现 Context 中不存在的幻觉考点（如 K99）必须被阻断', () => {
    const unknownKPResponse: StructuredAIResponse = {
      answer: '建议你先去攻坚知识点 K99（宏观货币传导模型），然后再回来继续学习。',
      referenced_facts: ['knowledge_id=K99'],
      grounding_status: 'grounded',
    };

    const result = validateAIResponse(baseContext, unknownKPResponse);

    assert.equal(result.status, 'REJECT');
    if (result.status === 'REJECT') {
      assert.equal(result.reason, 'UNKNOWN_KNOWLEDGE_POINT');
    }
  });

  // --------------------------------------------------------------------------
  // Test 19 — Unknown Numeric Fact REJECT
  // --------------------------------------------------------------------------
  it('Test 19 — Unknown Numeric Fact REJECT: 编造排名或学习时长等未知事实必须被阻断', () => {
    const fabricatedFactResponse: StructuredAIResponse = {
      answer: '你目前在全班排名第 3 名，已累计学习 100 小时，非常勤奋！',
      referenced_facts: ['rank=3', 'hours=100'],
      grounding_status: 'grounded',
    };

    const result = validateAIResponse(baseContext, fabricatedFactResponse);

    assert.equal(result.status, 'REJECT');
    if (result.status === 'REJECT') {
      assert.equal(result.reason, 'UNKNOWN_NUMERIC_FACT');
    }
  });

  // --------------------------------------------------------------------------
  // Test 20 — Rejected Response Produces Deterministic Fallback
  // --------------------------------------------------------------------------
  it('Test 20 — Rejected Response Produces Deterministic Fallback: 校验失败时生成基于真实 Context 的确定性 Fallback', () => {
    const fallback = createDeterministicFallback(baseContext, 'MASTERY_HALLUCINATION');

    assert.ok(fallback.answer.includes('当前回答包含系统无法验证的学习事实'));
    assert.ok(fallback.answer.includes('需求价格弹性'));
    assert.ok(fallback.answer.includes('当前掌握度：46%'));
    assert.ok(fallback.answer.includes('达标目标：80%'));
    assert.ok(fallback.answer.includes('当前差距：34%'));
    assert.equal(fallback.grounding_status, 'insufficient_context');
    assert.ok(Array.isArray(fallback.referenced_facts));
    assert.ok(fallback.referenced_facts.length > 0);

    // 验证无论调用多少次，生成的 fallback 完全等价
    const fallback2 = createDeterministicFallback(baseContext, 'MASTERY_HALLUCINATION');
    assert.deepEqual(fallback, fallback2);
  });
});
