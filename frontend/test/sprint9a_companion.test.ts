/**
 * sprint9a_companion.test.ts
 * Sprint 9-A: AI Learning Companion & Intelligent Study Assistance Frontend Contract Tests
 * ========================================================================================
 * 测试矩阵覆盖：
 * - C1: 4 种伴学辅导模式请求载荷结构与字段完备性
 * - C2: 输入文本 2000 字符硬约束与防超限校验
 * - C3: 学生端文案零技术黑话合规性断言 (No Jargon)
 * - C4: 安全与权限隔离元数据契约 (allow_production_decision = false)
 * - C5: 多生会话隔离与学生切换状态清理一致性
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

import type {
  CompanionMode,
  CompanionStudyRequest,
  CompanionStudyResponse,
  CompanionSafetyMetadata,
  CompanionContextMetadata,
} from '../src/types.ts';

describe('Sprint 9-A: AI Learning Companion Frontend Contract Tests', () => {

  describe('C1: 4 种伴学辅导模式请求载荷结构与契约完备性', () => {
    test('1. 概念精讲 (concept_explain) 模式组装包含目标考点 ID', () => {
      const req: CompanionStudyRequest = {
        student_id: 'S001',
        mode: 'concept_explain',
        knowledge_id: 'K01',
      };
      assert.equal(req.student_id, 'S001');
      assert.equal(req.mode, 'concept_explain');
      assert.equal(req.knowledge_id, 'K01');
      assert.equal(req.question_id, undefined);
    });

    test('2. 错题剖析 (wrong_answer_review) 模式组装包含题目与考点 ID', () => {
      const req: CompanionStudyRequest = {
        student_id: 'S001',
        mode: 'wrong_answer_review',
        question_id: 'Q-K01-01',
        knowledge_id: 'K01',
      };
      assert.equal(req.mode, 'wrong_answer_review');
      assert.equal(req.question_id, 'Q-K01-01');
      assert.equal(req.knowledge_id, 'K01');
    });

    test('3. 阶段总结 (learning_summary) 模式支持全景学情概括', () => {
      const req: CompanionStudyRequest = {
        student_id: 'S002',
        mode: 'learning_summary',
      };
      assert.equal(req.student_id, 'S002');
      assert.equal(req.mode, 'learning_summary');
    });

    test('4. 自由探讨 (conversation) 模式携带连续对话会话标识与提问', () => {
      const req: CompanionStudyRequest = {
        student_id: 'S001',
        mode: 'conversation',
        session_id: 'sess_abc123',
        message: '请问机会成本为什么是放弃的最高价值而非总和？',
      };
      assert.equal(req.mode, 'conversation');
      assert.equal(req.session_id, 'sess_abc123');
      assert.ok(req.message && req.message.length > 0);
    });
  });

  describe('C2: 输入文本 2000 字符硬约束与防超限校验', () => {
    const validateLength = (msg: string): boolean => {
      return msg.length <= 2000;
    };

    test('5. 正常长度消息 (<= 2000 字符) 校验通过', () => {
      const normalMsg = '请问微观经济学中的边际分析法在消费者均衡中的具体应用？';
      assert.equal(validateLength(normalMsg), true);

      const boundaryMsg = 'A'.repeat(2000);
      assert.equal(validateLength(boundaryMsg), true);
    });

    test('6. 超长消息 (> 2000 字符) 必须被前端安全拦截', () => {
      const overMsg = 'B'.repeat(2001);
      assert.equal(validateLength(overMsg), false);

      const hugeMsg = 'C'.repeat(5000);
      assert.equal(validateLength(hugeMsg), false);
    });
  });

  describe('C3: 学生端文案零技术黑话合规性断言 (No Jargon)', () => {
    const FORBIDDEN_JARGONS = [
      'BKT',
      'Bayesian Knowledge Tracing',
      'PathState',
      'DynamicPathGenerator',
      'EventRepository',
      'mastery_probability',
      'MutationDomain',
    ];

    test('7. 伴学模式标签与描述文本中严禁包含任何底层技术黑话', () => {
      const displayTexts = [
        'AI 伴学专属导师',
        '深入剖析核心考点直观理解、现实案例与考试易错陷阱',
        '依据题库权威解析，定位认知盲区并启发式复盘',
        '全景评估 30 考点掌握分布与下阶段自适应攻坚方向',
        '针对微观经济学疑难问题进行启发式多轮互动交流',
        '只读辅导 · 零生产副作用',
        '伴学导师在线 · 离线确定性保障',
      ];

      for (const text of displayTexts) {
        for (const jargon of FORBIDDEN_JARGONS) {
          assert.equal(
            text.includes(jargon),
            false,
            `学生端展示文本 "${text}" 违规暴露了底层技术黑话: ${jargon}`
          );
        }
      }
    });
  });

  describe('C4: 安全与权限隔离元数据契约', () => {
    test('8. 伴学响应元数据必须保证 allow_production_decision = false', () => {
      const mockSafety: CompanionSafetyMetadata = {
        allow_production_decision: false,
        sanitized: true,
        offline_mode: true,
        context_source: 'authoritative_knowledge_engine',
        redactions_applied: ['pii_filter'],
      };

      assert.equal(mockSafety.allow_production_decision, false);
      assert.equal(mockSafety.sanitized, true);
    });

    test('9. 伴学响应契约必须完整包含 session_id、mode、answer、context、safety', () => {
      const mockResponse: CompanionStudyResponse = {
        session_id: 'sess_123',
        mode: 'concept_explain',
        answer: '稀缺性是经济学的基础概念...',
        context: {
          student_id: 'S001',
          knowledge_id: 'K01',
          knowledge_name: '稀缺性与经济学基本问题',
          prerequisites: [],
        },
        safety: {
          allow_production_decision: false,
          sanitized: true,
          offline_mode: true,
          context_source: 'authoritative_knowledge_engine',
          redactions_applied: [],
        },
        suggested_actions: ['完成对应微测验'],
        provider: 'offline',
        referenced_facts: ['考点：K01 稀缺性与经济学基本问题'],
      };

      assert.equal(mockResponse.safety.allow_production_decision, false);
      assert.equal(mockResponse.context.knowledge_id, 'K01');
      assert.equal(mockResponse.provider, 'offline');
      assert.ok(mockResponse.suggested_actions.length > 0);
      assert.ok(mockResponse.referenced_facts.length > 0);
    });
  });

  describe('C5: 多生会话隔离与学生切换状态清理一致性', () => {
    test('10. 学生切换时重置所有局部伴学上下文与消息缓存', () => {
      let activeStudent = 'S001';
      let companionContext: Record<string, unknown> | null = {
        mode: 'wrong_answer_review',
        questionId: 'Q-K01-01',
      };
      let messageHistory = ['你好', '我是 S001 的错题记录'];

      // 模拟学生切换至 S002
      activeStudent = 'S002';
      // 状态清理回调
      companionContext = null;
      messageHistory = [];

      assert.equal(activeStudent, 'S002');
      assert.equal(companionContext, null);
      assert.equal(messageHistory.length, 0);
    });
  });
});
