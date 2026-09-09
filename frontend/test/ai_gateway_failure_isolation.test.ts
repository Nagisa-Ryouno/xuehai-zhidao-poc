/**
 * ai_gateway_failure_isolation.test.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
 * Stage D: Gateway Failure Isolation Contracts (前端极端故障隔离契约测试)
 *
 * 核心验证体系 (Invariants D1 ~ D12):
 * D1: HTTP 502 Bad Gateway 降级隔离 (无崩溃、无 Traceback)
 * D2: HTTP 503 Service Unavailable 降级隔离
 * D3: HTTP 504 Gateway Timeout 降级隔离 (标记 PROVIDER_TIMEOUT，无 hang)
 * D4: Network Failure 网络中断隔离 (fetch reject / 连接拒绝)
 * D5: Malformed JSON 畸形文本/HTML 隔离
 * D6: Invalid StructuredAIResponse 结构缺失拦截
 * D7: 越权决策字段注入防御 (Defense-in-depth: decision, mutate_path 等)
 * D8: FactValidator 事实幻觉硬阻断 (虚假掌握度/虚假解锁二次拦截)
 * D9: 敏感堆栈与文件路径零泄漏 + 确定性学习引擎状态零污染 (State Immutability)
 * D10: 毫秒级超时快速熔断 (无无限挂起)
 * D11: 服务端内部异常信息零暴露
 * D12: 敏感凭证 (API Secret) 零泄露隔离
 * D13: SafeFallback 纯函数与确定性一致
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  StudentBasic,
  LearningPathStep,
  PathState,
  DecisionAuditEnvelope,
  LearningContext,
} from '../src/types.ts';

import {
  buildLearningContext,
  type LearningContextInput,
} from '../src/components/student/learningContextModel.ts';

import { AIGatewayProvider } from '../src/components/student/aiGatewayProvider.ts';
import { askLearningCompanion } from '../src/components/student/aiCompanionService.ts';
import type { StructuredAIResponse } from '../src/components/student/aiResponseModel.ts';

// 基础测试 Fixture
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
    decision_id: 'dec-7001',
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
    event_id: 'evt-7001',
    replanning: mockRetainReplanning,
  },
};

function cloneDeep<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

describe('Phase 3 / Sprint 7-D — Stage D: Gateway Failure Isolation Contracts', () => {
  // --------------------------------------------------------------------------
  // D1: HTTP 502 Bad Gateway Isolation
  // --------------------------------------------------------------------------
  it('D1 — HTTP 502 Bad Gateway: 安全降级至 SafeFallback，学生端不崩溃，不包含 Traceback', async () => {
    const context = buildLearningContext(baseContextInput);
    const mockFetch: typeof fetch = async () => {
      return new Response(
        JSON.stringify({
          error: 'BAD_GATEWAY',
          detail: 'AI 服务商暂时不可用，已安全拦截。',
        }),
        {
          status: 502,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    const result = await askLearningCompanion(context, '为什么还没达标？', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'PROVIDER_EXCEPTION');
    assert.ok(result.answer.includes('当前掌握度：46%'));
    assert.ok(!result.answer.includes('Traceback'));
    assert.ok(!result.answer.includes('HTTP 502'));
  });

  // --------------------------------------------------------------------------
  // D2: HTTP 503 Service Unavailable Isolation
  // --------------------------------------------------------------------------
  it('D2 — HTTP 503 Service Unavailable: 安全降级至 SafeFallback，无未捕获异常', async () => {
    const context = buildLearningContext(baseContextInput);
    const mockFetch: typeof fetch = async () => {
      return new Response(
        JSON.stringify({
          error: 'SERVICE_UNAVAILABLE',
          detail: 'Gateway overloaded',
        }),
        {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    const result = await askLearningCompanion(context, '系统状态？', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'PROVIDER_EXCEPTION');
    assert.ok(result.answer.includes('当前掌握度：46%'));
  });

  // --------------------------------------------------------------------------
  // D3: HTTP 504 Gateway Timeout Isolation
  // --------------------------------------------------------------------------
  it('D3 — HTTP 504 Gateway Timeout: 安全降级至 SafeFallback，准确标记 PROVIDER_TIMEOUT，无挂起', async () => {
    const context = buildLearningContext(baseContextInput);
    const mockFetch: typeof fetch = async () => {
      return new Response(
        JSON.stringify({
          error: 'GATEWAY_TIMEOUT',
          detail: 'AI 伴学服务响应超时，请稍后重试。',
        }),
        {
          status: 504,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    const result = await askLearningCompanion(context, '分析考点', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'PROVIDER_TIMEOUT');
    assert.ok(result.answer.includes('当前掌握度：46%'));
  });

  // --------------------------------------------------------------------------
  // D4: Network Failure Isolation
  // --------------------------------------------------------------------------
  it('D4 — Network Failure: fetch 抛出连接拒绝或断网异常时平滑降级，Promise 正常 resolve', async () => {
    const context = buildLearningContext(baseContextInput);
    const mockFetch: typeof fetch = async () => {
      throw new TypeError('fetch failed: ECONNREFUSED 127.0.0.1:8000');
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    const result = await askLearningCompanion(context, '网络断开提问', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'PROVIDER_EXCEPTION');
    assert.ok(result.answer.includes('当前掌握度：46%'));
  });

  // --------------------------------------------------------------------------
  // D5: Malformed JSON Isolation
  // --------------------------------------------------------------------------
  it('D5 — Malformed JSON: 网关返回 HTML 502 页面或非法 JSON 文本时平滑降级', async () => {
    const context = buildLearningContext(baseContextInput);
    const mockFetch: typeof fetch = async () => {
      return new Response(
        '<html><body><h1>502 Bad Gateway</h1><p>nginx/1.24.0</p></body></html>',
        {
          status: 200,
          headers: { 'Content-Type': 'text/html' },
        }
      );
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    const result = await askLearningCompanion(context, '畸形响应测试', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'PROVIDER_EXCEPTION');
  });

  // --------------------------------------------------------------------------
  // D6: Invalid StructuredAIResponse Isolation
  // --------------------------------------------------------------------------
  it('D6 — Invalid StructuredAIResponse: 缺少 answer 或非数组 referenced_facts 时被客户端防御拦截', async () => {
    const context = buildLearningContext(baseContextInput);

    // 缺少 answer 字段
    const mockFetch1: typeof fetch = async () => {
      return new Response(
        JSON.stringify({
          referenced_facts: ['K08'],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    };
    const provider1 = new AIGatewayProvider({ customFetch: mockFetch1 });
    const res1 = await askLearningCompanion(context, '缺少answer测试', provider1);
    assert.equal(res1.grounding_status, 'fallback');
    assert.equal(res1.validation_reason, 'PROVIDER_EXCEPTION');

    // referenced_facts 不是数组
    const mockFetch2: typeof fetch = async () => {
      return new Response(
        JSON.stringify({
          answer: '这是回答',
          referenced_facts: 'not_an_array',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    };
    const provider2 = new AIGatewayProvider({ customFetch: mockFetch2 });
    const res2 = await askLearningCompanion(context, '非数组facts测试', provider2);
    assert.equal(res2.grounding_status, 'fallback');
    assert.equal(res2.validation_reason, 'PROVIDER_EXCEPTION');
  });

  // --------------------------------------------------------------------------
  // D7: Defense-in-depth: Decision Authority Rejection
  // --------------------------------------------------------------------------
  it('D7 — Zero Decision Authority: 响应中包含任何非法决策控制字段时立即被 AIGatewayProvider 拦截', async () => {
    const context = buildLearningContext(baseContextInput);

    const illicitFields = [
      { decision: 'FORCE_UNLOCK' },
      { unlock_nodes: ['K09', 'K10'] },
      { state_transition: 'COMPLETED' },
      { mutate_path: true },
      { modify_mastery: 0.99 },
      { set_mastery: 0.85 },
      { next_state: 'COMPLETED' },
      { learning_path_update: {} },
      { next_action_command: 'SKIP' },
      { change_path: true },
      { path_mutation: 'PREREQ_OVERRIDE' },
    ];

    for (const illicit of illicitFields) {
      const mockFetch: typeof fetch = async () => {
        return new Response(
          JSON.stringify({
            answer: '恶意注入响应',
            referenced_facts: [],
            ...illicit,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        );
      };

      const provider = new AIGatewayProvider({ customFetch: mockFetch });
      const res = await askLearningCompanion(context, '越权注入测试', provider);

      assert.equal(
        res.grounding_status,
        'fallback',
        `包含非法字段 ${Object.keys(illicit)[0]} 未被拦截`
      );
      assert.equal(res.validation_reason, 'PROVIDER_EXCEPTION');
    }
  });

  // --------------------------------------------------------------------------
  // D8: FactValidator Second Boundary (Mastery Hallucination Defense)
  // --------------------------------------------------------------------------
  it('D8 — FactValidator Defense: 网关返回 200 且格式完整，但出现事实幻觉时被 FactValidator 拦截降级', async () => {
    const context = buildLearningContext(baseContextInput);

    // 掌握度幻觉：虚构掌握度 80% (实际只有 46%)
    const mockFetchMastery: typeof fetch = async () => {
      const resp: StructuredAIResponse = {
        answer: '祝贺你！你的需求价格弹性掌握度已经达到 80% 并成功达标！',
        referenced_facts: ['current_mastery_percent=80'],
        grounding_status: 'grounded',
      };
      return new Response(JSON.stringify(resp), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    };

    const providerMastery = new AIGatewayProvider({ customFetch: mockFetchMastery });
    const resMastery = await askLearningCompanion(context, '达标检查', providerMastery);

    assert.equal(resMastery.grounding_status, 'fallback');
    assert.equal(resMastery.validation_reason, 'MASTERY_HALLUCINATION');
    assert.ok(resMastery.answer.includes('当前回答包含系统无法验证的学习事实'));

    // 虚假解锁幻觉：声称系统已解锁新考点 (实际 unlocked_nodes 为空)
    const mockFetchUnlock: typeof fetch = async () => {
      const resp: StructuredAIResponse = {
        answer: '系统已经为你解锁了新考点！继续努力！',
        referenced_facts: ['current_knowledge_point=K08:需求价格弹性'],
        grounding_status: 'grounded',
      };
      return new Response(JSON.stringify(resp), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    };

    const providerUnlock = new AIGatewayProvider({ customFetch: mockFetchUnlock });
    const resUnlock = await askLearningCompanion(context, '解锁检查', providerUnlock);

    assert.equal(resUnlock.grounding_status, 'fallback');
    assert.equal(resUnlock.validation_reason, 'FAKE_UNLOCK');
  });

  // --------------------------------------------------------------------------
  // D9: Zero Leakage of Traceback & File Paths + State Immutability
  // --------------------------------------------------------------------------
  it('D9 — Traceback Isolation & State Immutability: 内部堆栈绝对不泄露，且故障期间确定性学习引擎状态零修改', async () => {
    const originalContext = buildLearningContext(baseContextInput);
    const contextSnapshotBefore = cloneDeep(originalContext);

    // 模拟网关返回包含 Python 堆栈和绝对路径的错误体
    const mockFetchWithTraceback: typeof fetch = async () => {
      return new Response(
        JSON.stringify({
          error: 'INTERNAL_ERROR',
          detail:
            'Traceback (most recent call last):\n  File "C:\\xuehai\\gateway\\api.py", line 68, in dispatch\n    raise RuntimeError("Secret DB crash")',
        }),
        {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetchWithTraceback });
    const result = await askLearningCompanion(originalContext, '堆栈泄露测试', provider);

    // 1. 学生端回答绝对不包含堆栈或内部路径
    assert.equal(result.grounding_status, 'fallback');
    assert.ok(!result.answer.includes('Traceback'));
    assert.ok(!result.answer.includes('api.py'));
    assert.ok(!result.answer.includes('C:\\xuehai'));
    assert.ok(!result.answer.includes('Secret DB crash'));

    // 2. 状态零污染断言 (Deterministic Engine Invariant): 原始上下文对象保持 100% 深度等价
    assert.deepEqual(
      originalContext,
      contextSnapshotBefore,
      'AI 故障处理过程篡改了 LearningContext 确定性上下文'
    );
  });

  // --------------------------------------------------------------------------
  // D10: Short Timeout Isolation
  // --------------------------------------------------------------------------
  it('D10 — Abort & Short Timeout Isolation: 短时限调用能够快速中断且不导致进程挂起', async () => {
    const context = buildLearningContext(baseContextInput);

    const mockFetchHanging: typeof fetch = async () => {
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve(
            new Response(
              JSON.stringify({
                answer: '迟到的回答',
                referenced_facts: [],
              })
            )
          );
        }, 150);
      });
    };

    const provider = new AIGatewayProvider({
      timeoutMs: 25,
      customFetch: mockFetchHanging,
    });

    const startTime = Date.now();
    const result = await askLearningCompanion(context, '短时限超时提问', provider, {
      timeoutMs: 25,
    });
    const elapsed = Date.now() - startTime;

    assert.equal(result.grounding_status, 'fallback');
    assert.equal(result.validation_reason, 'PROVIDER_TIMEOUT');
    assert.ok(elapsed < 120, `调用耗时 ${elapsed}ms 超出容忍范围，可能发生了无限挂起`);
  });

  // --------------------------------------------------------------------------
  // D11: Provider Exception Detail Isolation
  // --------------------------------------------------------------------------
  it('D11 — Provider Exception Message Isolation: 服务端底层异常消息不泄露至回答中', async () => {
    const context = buildLearningContext(baseContextInput);
    const sensitiveMsg = 'CRITICAL_INTERNAL_DB_FAILURE_CODE_0xDEADBEEF';

    const mockFetch: typeof fetch = async () => {
      return new Response(
        JSON.stringify({
          error: 'BAD_GATEWAY',
          detail: sensitiveMsg,
        }),
        { status: 502, headers: { 'Content-Type': 'application/json' } }
      );
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    const result = await askLearningCompanion(context, '敏感异常测试', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.ok(!result.answer.includes(sensitiveMsg));
    assert.ok(!result.suggested_explanation?.includes(sensitiveMsg));
  });

  // --------------------------------------------------------------------------
  // D12: Secret Token Isolation
  // --------------------------------------------------------------------------
  it('D12 — Secret Token Isolation: 敏感凭证 (API Secret) 绝对不在降级结果或事实引用中出现', async () => {
    const context = buildLearningContext(baseContextInput);
    const testSecret = 'TEST_SECRET_DO_NOT_USE_998877';

    const mockFetch: typeof fetch = async () => {
      return new Response(
        JSON.stringify({
          error: 'BAD_GATEWAY',
          detail: `Upstream error with token ${testSecret}`,
        }),
        {
          status: 502,
          headers: {
            'Content-Type': 'application/json',
            'X-Debug-Key': testSecret,
          },
        }
      );
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });
    const result = await askLearningCompanion(context, '密钥隔离提问', provider);

    assert.equal(result.grounding_status, 'fallback');
    assert.ok(!result.answer.includes(testSecret));
    assert.ok(!result.suggested_explanation?.includes(testSecret));
    if (result.referenced_facts) {
      for (const fact of result.referenced_facts) {
        assert.ok(!fact.includes(testSecret));
      }
    }
  });

  // --------------------------------------------------------------------------
  // D13: Deterministic Safe Fallback
  // --------------------------------------------------------------------------
  it('D13 — Fallback Determinism: 相同上下文与故障原因多次调用产生完全一致的 SafeFallback 结构', async () => {
    const context = buildLearningContext(baseContextInput);
    const mockFetch: typeof fetch = async () => {
      return new Response('Gateway Error', { status: 502 });
    };

    const provider = new AIGatewayProvider({ customFetch: mockFetch });

    const result1 = await askLearningCompanion(context, '确定性测试', provider);
    const result2 = await askLearningCompanion(context, '确定性测试', provider);

    assert.deepEqual(result1, result2, '相同上下文下的 SafeFallback 输出不一致');
  });
});
