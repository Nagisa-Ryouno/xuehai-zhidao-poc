/**
 * aiGatewayProvider.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
 * Backend Secure AI Gateway 前端适配器实现
 *
 * 核心架构定位：
 * 1. 严格实现 AIProvider 接口：无缝平滑替换本地 Mock
 * 2. 安全 HTTP 传输：通过相对路径 /api/ai/companion 与服务端 AI Gateway 通信
 * 3. 严格输入边界：仅接收 LearningPromptContext 白名单投影数据
 * 4. 严格响应结构硬校验：验证 StructuredAIResponse 必需字段，防范空结构与畸形 JSON
 * 5. 客户端决策权限硬防御 (Defense in Depth)：严格检测并拒绝 decision、unlock_nodes 等越权字段
 * 6. 异常与超时透明转换：将网络、HTTP 状态码 (502/503/504) 与解析错误转换为受控 Provider 错误，
 *    由上层 aiCompanionService 安全收敛至确定性 SafeFallback，绝对保护 UI 稳定
 */

import type { AIProvider } from './aiProvider.ts';
import type { LearningPromptContext } from './learningPromptModel.ts';
import type { StructuredAIResponse } from './aiResponseModel.ts';

export interface AIGatewayProviderOptions {
  readonly endpoint?: string;
  readonly timeoutMs?: number;
  readonly customFetch?: typeof fetch;
}

const DEFAULT_GATEWAY_ENDPOINT = '/api/ai/companion';
const DEFAULT_GATEWAY_TIMEOUT_MS = 8000;

export class AIGatewayProvider implements AIProvider {
  readonly endpoint: string;
  readonly timeoutMs: number;
  private readonly customFetch?: typeof fetch;

  constructor(options: AIGatewayProviderOptions = {}) {
    this.endpoint = options.endpoint || DEFAULT_GATEWAY_ENDPOINT;
    this.timeoutMs = options.timeoutMs || DEFAULT_GATEWAY_TIMEOUT_MS;
    this.customFetch = options.customFetch;
  }

  async generate(
    promptContext: LearningPromptContext
  ): Promise<StructuredAIResponse> {
    // 1. 严格校验输入上下文基础完整性
    if (!promptContext || !promptContext.system_facts) {
      throw new Error('Invalid promptContext: missing system_facts');
    }

    // 2. 白名单载荷构造：严禁透传未经白名单清洗的原始前端状态或数据库实体
    const payload = {
      promptContext: {
        user_question: promptContext.user_question,
        system_facts: promptContext.system_facts,
        grounding_rules: promptContext.grounding_rules || [],
      },
      question: promptContext.user_question,
    };

    // 3. 配置超时控制器与网络调用
    const controller = new AbortController();
    const timer = setTimeout(() => {
      controller.abort();
    }, this.timeoutMs);
    if (typeof timer === 'object' && typeof (timer as unknown as { unref: () => void }).unref === 'function') {
      (timer as unknown as { unref: () => void }).unref();
    }

    const fetcher = this.customFetch || fetch;

    let response: Response;
    try {
      response = await fetcher(this.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        throw new Error(`Gateway request timed out after ${this.timeoutMs}ms`);
      }
      throw new Error(
        `Network failure calling AI Gateway: ${err instanceof Error ? err.message : String(err)}`
      );
    } finally {
      clearTimeout(timer);
    }

    // 4. HTTP 状态码校验 (502 / 503 / 504 / 422 等统一映射为受控异常)
    if (!response.ok) {
      let errorDetail = '';
      try {
        const errorJson = await response.json();
        errorDetail = errorJson.detail || errorJson.error || '';
      } catch {
        // 非 JSON 响应忽略错误体解析
      }
      throw new Error(
        `Gateway returned HTTP ${response.status}${errorDetail ? `: ${errorDetail}` : ''}`
      );
    }

    // 5. 解析 JSON 并防范非 JSON 畸形文本
    let data: unknown;
    try {
      data = await response.json();
    } catch {
      throw new Error('Malformed JSON received from AI Gateway');
    }

    // 6. 运行时结构有效性硬校验 (StructuredAIResponse 契约规范)
    if (
      !data ||
      typeof data !== 'object' ||
      typeof (data as Record<string, unknown>).answer !== 'string' ||
      !Array.isArray((data as Record<string, unknown>).referenced_facts)
    ) {
      throw new Error(
        'Invalid StructuredAIResponse received from AI Gateway: missing required fields'
      );
    }

    // 7. 客户端决策权限硬防御 (Defense in Depth: 拒绝包含任何学习控制字段)
    const rawObj = data as Record<string, unknown>;
    const forbiddenDecisionKeys = [
      'decision',
      'unlock_nodes',
      'state_transition',
      'mutate_path',
      'modify_mastery',
      'set_mastery',
      'next_action_command',
      'change_path',
    ];
    for (const key of forbiddenDecisionKeys) {
      if (key in rawObj) {
        throw new Error(
          `Gateway response contains forbidden decision field: ${key}`
        );
      }
    }

    return {
      answer: String(rawObj.answer),
      referenced_facts: (rawObj.referenced_facts as unknown[]).map(String),
      suggested_explanation:
        typeof rawObj.suggested_explanation === 'string'
          ? rawObj.suggested_explanation
          : undefined,
      grounding_status:
        rawObj.grounding_status === 'insufficient_context'
          ? 'insufficient_context'
          : 'grounded',
    };
  }
}
