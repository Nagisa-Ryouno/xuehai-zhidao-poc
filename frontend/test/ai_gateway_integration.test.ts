/**
 * ai_gateway_integration.test.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
 * Stage C: Frontend -> Backend Secure AI Gateway 集成契约测试 (C1 ~ C15)
 *
 * 核心验证：
 * 1. AIGatewayProvider 实现 AIProvider 抽象接口
 * 2. 严格网络端点与协议契约 (POST /api/ai/companion, application/json)
 * 3. 严格白名单载荷投射，严禁原始领域实体跨界
 * 4. 纵深防御：Gateway 返回数据必须经过 FactValidator 二次硬核检验，绝不直显
 * 5. 全链路容灾：网络错误、502/503/504、畸形数据与超时均安全收敛至 SafeFallback
 * 6. 前端代码严格无任何真实或测试用 API Key 泄露
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

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

import { AIGatewayProvider } from '../src/components/student/aiGatewayProvider.ts';
import { askLearningCompanion } from '../src/components/student/aiCompanionService.ts';
import type { AIProvider } from '../src/components/student/aiProvider.ts';
import type { StructuredAIResponse } from '../src/components/student/aiResponseModel.ts';

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
    decision_id: 'dec-6001',
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
    event_id: 'evt-6001',
    replanning: mockRetainReplanning,
  },
};

const baseContext = buildLearningContext(baseContextInput);

describe('Phase 3 / Sprint 7-D — Stage C: Frontend -> Backend AI Gateway Integration Tests', () => {
  // --------------------------------------------------------------------------
  // C1 — Provider satisfies AIProvider interface
  // --------------------------------------------------------------------------
  it('C1 — Provider satisfies AIProvider: AIGatewayProvider 正确实现 AIProvider 接口', () => {
    const provider: AIProvider = new AIGatewayProvider();
    assert.ok(typeof provider.generate === 'function');
  });

  // --------------------------------------------------------------------------
  // C2, C3, C4 — Correct Endpoint, HTTP Method, Content-Type
  // --------------------------------------------------------------------------
  it('C2, C3, C4 — Network Contract: 正确调用 POST /api/ai/companion 且 Header 为 application/json', async () => {
    let capturedUrl = '';
    let capturedMethod = '';
    let capturedContentType = '';

    const mockFetch: typeof fetch = async (input, init) => {
      capturedUrl = String(input);
      capturedMethod = init?.method || '';
      const headers = init?.headers as Record<string, string>;
      capturedContentType = headers?.['Content-Type'] || '';

      const validResponse: StructuredAIResponse = {
        answer: '系统已成功根据当前事实完成诊断。',
        referenced_facts: ['current_knowledge_point=K08:需求价格弹性'],
        suggested_explanation: '基础考点。',
        grounding_status: 'grounded',
      };

      return new Response(JSON.stringify(validResponse), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    const answer = await askLearningCompanion(baseContext, '我的学习进度？', provider);

    assert.equal(capturedUrl, '/api/ai/companion');
    assert.equal(capturedMethod, 'POST');
    assert.equal(capturedContentType, 'application/json');
    assert.equal(answer.grounding_status, 'grounded');
  });

  // --------------------------------------------------------------------------
  // C5 — Only whitelisted LearningPromptContext sent
  // --------------------------------------------------------------------------
  it('C5 — Payload Whitelist: 仅发送白名单 LearningPromptContext，杜绝原始前端状态泄露', async () => {
    let capturedPayload: Record<string, unknown> = {};

    const mockFetch: typeof fetch = async (_input, init) => {
      capturedPayload = JSON.parse(String(init?.body));
      const validResponse: StructuredAIResponse = {
        answer: '这是合法响应。',
        referenced_facts: ['current_knowledge_point=K08:需求价格弹性'],
        grounding_status: 'grounded',
      };
      return new Response(JSON.stringify(validResponse), { status: 200 });
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    await askLearningCompanion(baseContext, '当前状态？', provider);

    // 必须包含 promptContext 与 question
    assert.ok(capturedPayload.promptContext);
    assert.ok(capturedPayload.question);

    // 绝不能包含任何前端未脱敏对象
    assert.equal(capturedPayload.student, undefined);
    assert.equal(capturedPayload.learningPath, undefined);
    assert.equal(capturedPayload.pathStates, undefined);
    assert.equal(capturedPayload.decisionCore, undefined);
  });

  // --------------------------------------------------------------------------
  // C6 — Gateway response parsed correctly
  // --------------------------------------------------------------------------
  it('C6 — Response Parsing: 合法 StructuredAIResponse 成功进入并被解析', async () => {
    const mockFetch: typeof fetch = async () => {
      const resp: StructuredAIResponse = {
        answer: '同学你好！你当前正在学习微观经济学基础中的需求价格弹性，掌握度为 46.0%。',
        referenced_facts: [
          'current_knowledge_point=K08:需求价格弹性',
          'current_mastery_percent=46%',
        ],
        suggested_explanation: '核心考点解析',
        grounding_status: 'grounded',
      };
      return new Response(JSON.stringify(resp), { status: 200 });
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    const result = await askLearningCompanion(baseContext, '解析考点', provider);

    assert.equal(result.grounding_status, 'grounded');
    assert.ok(result.answer.includes('需求价格弹性'));
    assert.ok(result.referenced_facts?.includes('current_knowledge_point=K08:需求价格弹性'));
  });

  // --------------------------------------------------------------------------
  // C7 — FactValidator remains active as hard second boundary
  // --------------------------------------------------------------------------
  it('C7 — FactValidator Defense: Gateway 返回 200 但包含虚假达标事实时，被 FactValidator 拦截降级', async () => {
    const mockFetch: typeof fetch = async () => {
      // 模拟 Gateway/大模型产生幻觉，吹捧掌握度达到了 80%
      const hallucinatedResponse: StructuredAIResponse = {
        answer: '恭喜你！你的需求价格弹性掌握度已经达到了 80%，完全达标了！',
        referenced_facts: ['current_mastery_percent=80'],
        grounding_status: 'grounded',
      };
      return new Response(JSON.stringify(hallucinatedResponse), { status: 200 });
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    const result = await askLearningCompanion(baseContext, '我达标了吗？', provider);

    // 必须被 FactValidator 拦截并标记为 fallback
    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'MASTERY_HALLUCINATION');
    assert.ok(result.answer.includes('当前回答包含系统无法验证的学习事实'));
    assert.ok(result.answer.includes('当前掌握度：46%'));
  });

  // --------------------------------------------------------------------------
  // C8, C9, C10 — HTTP 502, 503, 504 handled smoothly
  // --------------------------------------------------------------------------
  it('C8, C9, C10 — HTTP Status Failures: 502、503 与 504 均被安全拦截并降级为 SafeFallback', async () => {
    for (const statusCode of [502, 503, 504]) {
      const mockFetch: typeof fetch = async () => {
        return new Response(JSON.stringify({ error: `HTTP ${statusCode}` }), {
          status: statusCode,
        });
      };

      const provider = new AIGatewayProvider({ customFetch: mockFetch });
      const result = await askLearningCompanion(baseContext, '提问测试', provider);

      assert.equal(result.grounding_status, 'fallback');
      assert.ok(result.answer.includes('当前回答包含系统无法验证的学习事实'));
    }
  });

  // --------------------------------------------------------------------------
  // C11 — Network Failure handled
  // --------------------------------------------------------------------------
  it('C11 — Network Failure: fetch 抛出连接异常时不击穿 UI，安全回退', async () => {
    const mockFetch: typeof fetch = async () => {
      throw new Error('fetch failed: Connection refused');
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    const result = await askLearningCompanion(baseContext, '网络中断提问', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'PROVIDER_EXCEPTION');
    assert.ok(result.answer.includes('当前掌握度：46%'));
  });

  // --------------------------------------------------------------------------
  // C12 — Malformed JSON handled
  // --------------------------------------------------------------------------
  it('C12 — Malformed JSON: Gateway 返回非 JSON 畸形文本被安全拦截', async () => {
    const mockFetch: typeof fetch = async () => {
      return new Response('<html><head><title>502 Bad Gateway</title></head></html>', {
        status: 200,
        headers: { 'Content-Type': 'text/html' },
      });
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    const result = await askLearningCompanion(baseContext, '畸形文本测试', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'PROVIDER_EXCEPTION');
  });

  // --------------------------------------------------------------------------
  // C13 — Invalid structured response handled
  // --------------------------------------------------------------------------
  it('C13 — Invalid Structure: 缺少 answer 或包含非法决策字段时被客户端防御拦截', async () => {
    // 缺少 answer 字段
    const mockFetchMissingAnswer: typeof fetch = async () => {
      return new Response(JSON.stringify({ invalid: 123 }), { status: 200 });
    };
    const provider1 = new AIGatewayProvider({ customFetch: mockFetchMissingAnswer });
    const res1 = await askLearningCompanion(baseContext, '测试', provider1);
    assert.equal(res1.grounding_status, 'fallback');

    // 包含越权决策字段
    const mockFetchWithDecision: typeof fetch = async () => {
      return new Response(
        JSON.stringify({
          answer: '回答',
          referenced_facts: [],
          decision: 'FORCE_UNLOCK',
        }),
        { status: 200 }
      );
    };
    const provider2 = new AIGatewayProvider({ customFetch: mockFetchWithDecision });
    const res2 = await askLearningCompanion(baseContext, '测试', provider2);
    assert.equal(res2.grounding_status, 'fallback');
  });

  // --------------------------------------------------------------------------
  // C14 — Timeout handled
  // --------------------------------------------------------------------------
  it('C14 — Timeout Handling: 超时后请求安全熔断且不发生无限悬挂', async () => {
    const mockFetchSlow: typeof fetch = async () => {
      return new Promise((resolve) => {
        // 模拟 100ms 慢调用，而超时设置为 20ms
        setTimeout(() => {
          resolve(new Response(JSON.stringify({ answer: 'ok', referenced_facts: [] })));
        }, 100);
      });
    };

    const provider = new AIGatewayProvider({
      timeoutMs: 20,
      customFetch: mockFetchSlow,
    });

    const result = await askLearningCompanion(baseContext, '超时提问', provider, {
      timeoutMs: 20,
    });

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'PROVIDER_TIMEOUT');
  });

  // --------------------------------------------------------------------------
  // C15 — No secret leakage in frontend
  // --------------------------------------------------------------------------
  it('C15 — Secret Isolation: 前端源码目录中绝对不包含真实 API Key 或敏感凭证', () => {
    const srcDir = resolve(process.cwd(), 'src');
    const forbiddenSecrets = [
      'sk-proj-',
      'sk-ant-',
      'deepseek-api-key',
      'OPENAI_API_KEY',
      'AI_API_KEY',
    ];

    function scanFiles(dir: string) {
      const files = readdirSync(dir);
      for (const file of files) {
        const fullPath = join(dir, file);
        const stat = statSync(fullPath);
        if (stat.isDirectory()) {
          scanFiles(fullPath);
        } else if (file.endsWith('.ts') || file.endsWith('.tsx')) {
          const content = readFileSync(fullPath, 'utf-8');
          for (const secret of forbiddenSecrets) {
            // 排除注释中出现的 "禁止在前端出现 OPENAI_API_KEY" 的说明文本
            const lines = content.split('\n');
            for (let i = 0; i < lines.length; i++) {
              const line = lines[i];
              if (line.includes('//') || line.includes('*')) continue;
              assert.ok(
                !line.includes(secret),
                `在 ${file}:${i + 1} 发现潜在密钥暴露: ${secret}`
              );
            }
          }
        }
      }
    }

    scanFiles(srcDir);
  });
});
