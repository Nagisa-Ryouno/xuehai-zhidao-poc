/**
 * aiCompanionService.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-C
 * AI Companion Service Pipeline
 *
 * 核心架构数据流：
 * LearningContext
 *     ↓
 * buildLearningPromptContext(context, question)
 *     ↓
 * AIProvider.generate(promptContext) (with timeout protection)
 *     ↓
 * validateAIResponse(context, rawResponse)
 *     ↓
 * PASS → GroundedAnswer (grounded)
 * REJECT → SafeFallback (fallback)
 *
 * 故障隔离 (Failure Isolation)：
 * 无论 Provider 发生超时、网络失败、未决议、异常崩溃或返回非法格式，
 * 均绝不冒泡到 UI，自动降级为基于 LearningContext 权威系统事实的确定性 Safe Fallback。
 */

import type { LearningContext, GroundedAnswer } from '../../types.ts';
import type { AIProvider } from './aiProvider.ts';
import { MockAIProvider } from './mockAIProvider.ts';
import { buildLearningPromptContext } from './learningPromptModel.ts';
import {
  validateAIResponse,
  createDeterministicFallback,
  type AIValidationFailureReason,
} from './aiResponseValidator.ts';

export interface AskCompanionOptions {
  readonly timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 5000;

// 全局默认使用确定性本地 MockAIProvider
const defaultProvider = new MockAIProvider();

/**
 * 辅助超时包装函数
 */
async function executeWithTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number
): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new Error(`AI Provider timed out after ${timeoutMs}ms`));
    }, timeoutMs);
    if (typeof timer === 'object' && typeof (timer as unknown as { unref: () => void }).unref === 'function') {
      (timer as unknown as { unref: () => void }).unref();
    }
  });

  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    if (timer) {
      clearTimeout(timer);
    }
  }
}

/**
 * 学生端向 AI 伴学助手提问的主入口服务函数
 *
 * @param context 权威系统学情上下文 LearningContext
 * @param question 学习者提问文本
 * @param provider AI 提供商实现，默认为本地 MockAIProvider
 * @param options 可选配置（超时时限等）
 */
export async function askLearningCompanion(
  context: LearningContext,
  question: string,
  provider: AIProvider = defaultProvider,
  options: AskCompanionOptions = {}
): Promise<GroundedAnswer> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  // 1. 基础上下文防御：若 Context 无效，安全返回最小系统兜底
  if (!context || !context.system_facts) {
    return {
      answer: '抱歉，当前暂无可用学情上下文，请刷新页面或选择考点后再试。',
      grounding_status: 'fallback',
      validation_reason: 'EMPTY_CONTEXT',
    };
  }

  // 2. 将系统真实上下文通过白名单投影为结构化 PromptContext
  const promptContext = buildLearningPromptContext(context, question);

  // 3. 调用 AIProvider 生成结构化响应，具备全链路故障捕获与超时防御
  let rawResponse;
  try {
    rawResponse = await executeWithTimeout(
      provider.generate(promptContext),
      timeoutMs
    );
  } catch (err: unknown) {
    const isTimeout =
      err instanceof Error &&
      (err.message.includes('timed out') || err.message.includes('timeout'));

    const failureReason: AIValidationFailureReason = isTimeout
      ? 'PROVIDER_TIMEOUT'
      : 'PROVIDER_EXCEPTION';

    const fallback = createDeterministicFallback(context, failureReason);

    return {
      answer: fallback.answer,
      grounding_status: 'fallback',
      validation_reason: failureReason,
      referenced_facts: fallback.referenced_facts,
      suggested_explanation: fallback.suggested_explanation,
    };
  }

  // 4. 对大模型原始输出执行 FactValidator 硬性事实一致性校验
  const validation = validateAIResponse(context, rawResponse);

  // 5. 根据校验结果输出 GroundedAnswer，绝对阻断原始幻觉输出
  if (validation.status === 'PASS') {
    return {
      answer: validation.response.answer,
      grounding_status: 'grounded',
      referenced_facts: validation.response.referenced_facts,
      suggested_explanation: validation.response.suggested_explanation,
    };
  }

  // 校验未通过：返回 Safe Fallback
  return {
    answer: validation.fallback.answer,
    grounding_status: 'fallback',
    validation_reason: validation.reason,
    referenced_facts: validation.fallback.referenced_facts,
    suggested_explanation: validation.fallback.suggested_explanation,
  };
}
