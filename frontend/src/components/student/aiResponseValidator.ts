/**
 * aiResponseValidator.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-B
 * AI Response Fact Validator & Deterministic Safe Fallback
 *
 * 核心架构定位：
 * 1. 100% 纯函数与确定性：无 React、DOM、网络、localStorage、Date.now、Math.random
 * 2. 事实一致性防御：对大模型输出进行多维校验，杜绝虚假掌握度、虚假阈值、虚假解锁、
 *    状态矛盾、认知回退矛盾、未知考点与编造的统计事实
 * 3. 确定性安全兜底 (Safe Fallback)：校验失败时阻断原始输出，返回基于系统权威事实的兜底回答
 */

import type { LearningContext } from '../../types.ts';
import type { StructuredAIResponse } from './aiResponseModel.ts';

export type AIValidationFailureReason =
  | 'EMPTY_ANSWER'
  | 'MASTERY_HALLUCINATION'
  | 'THRESHOLD_HALLUCINATION'
  | 'FAKE_UNLOCK'
  | 'RETAIN_CONTRADICTION'
  | 'REGRESS_CONTRADICTION'
  | 'LOCKED_CONTRADICTION'
  | 'UNKNOWN_KNOWLEDGE_POINT'
  | 'UNKNOWN_NUMERIC_FACT'
  | 'PROVIDER_TIMEOUT'
  | 'PROVIDER_EXCEPTION'
  | 'MALFORMED_RESPONSE';

export type AIValidationResult =
  | {
      readonly status: 'PASS';
      readonly response: StructuredAIResponse;
    }
  | {
      readonly status: 'REJECT';
      readonly reason: AIValidationFailureReason;
      readonly fallback: StructuredAIResponse;
    };

/**
 * 递归深度冻结对象
 */
function deepFreeze<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }
  Object.freeze(obj);
  for (const key of Object.keys(obj as object)) {
    const prop = (obj as Record<string, unknown>)[key];
    if (prop !== null && typeof prop === 'object' && !Object.isFrozen(prop)) {
      deepFreeze(prop);
    }
  }
  return obj;
}

/**
 * 当 AI 校验未通过时，生成基于 LearningContext 系统权威事实的确定性 Safe Fallback
 */
export function createDeterministicFallback(
  context: LearningContext,
  reason: AIValidationFailureReason
): StructuredAIResponse {
  const sf = context.system_facts;
  const nextActionDesc = sf.next_action?.label || '按照推荐顺序继续学习';

  const answer = [
    '当前回答包含系统无法验证的学习事实，已自动启用基于权威状态的安全回复。',
    '',
    '目前系统确认的学习状态是：',
    `- 当前考点：${sf.current_knowledge_name} (${sf.current_knowledge_id})`,
    `- 当前掌握度：${sf.current_mastery_percent}%`,
    `- 达标目标：${sf.mastery_target_percent}%`,
    `- 当前差距：${sf.mastery_gap_percent}%`,
    `- 状态：${sf.current_path_state}`,
    `- 下一步行动建议：${nextActionDesc}`,
    '',
    '请以学习路径与系统推荐决策为准。',
  ].join('\n');

  const referencedFacts = [
    `current_knowledge_id=${sf.current_knowledge_id}`,
    `current_knowledge_name=${sf.current_knowledge_name}`,
    `current_mastery_percent=${sf.current_mastery_percent}`,
    `mastery_target_percent=${sf.mastery_target_percent}`,
    `mastery_gap_percent=${sf.mastery_gap_percent}`,
    `current_path_state=${sf.current_path_state}`,
    `validation_rejected_reason=${reason}`,
  ];

  return deepFreeze({
    answer,
    referenced_facts: Object.freeze(referencedFacts),
    suggested_explanation: '基于客观系统事实的安全兜底回答。',
    grounding_status: 'insufficient_context',
  });
}

/**
 * 验证大模型响应是否符合系统客观事实
 */
export function validateAIResponse(
  context: LearningContext,
  response: StructuredAIResponse
): AIValidationResult {
  // 0. 结构完整性校验 (MALFORMED_RESPONSE)
  if (!response || typeof response !== 'object' || typeof response.answer !== 'string') {
    return {
      status: 'REJECT',
      reason: 'MALFORMED_RESPONSE',
      fallback: createDeterministicFallback(context, 'MALFORMED_RESPONSE'),
    };
  }

  const sf = context.system_facts;
  const answer = response.answer;
  const facts = Array.isArray(response.referenced_facts) ? response.referenced_facts : [];

  // 1. 空内容检查 (EMPTY_ANSWER)
  if (answer.trim() === '') {
    return {
      status: 'REJECT',
      reason: 'EMPTY_ANSWER',
      fallback: createDeterministicFallback(context, 'EMPTY_ANSWER'),
    };
  }

  // 2. 编造未知统计/数值事实 (UNKNOWN_NUMERIC_FACT)
  // 检查 referenced_facts 是否包含系统不存在的统计维度（如 rank, hours 等）
  const hasUnknownNumericRef = facts.some((f) =>
    /(?:^rank=|^hours=|^study_hours=|^ranking=|^score=)/i.test(f)
  );
  // 检查文本中是否包含排名、学时等未接地指标
  const hasFabricatedRankOrHours =
    /(?:全班|班级|年级|全校|系内|系统)?\s*(?:排名(?:第|\s*)?\s*\d+\s*(?:名|位)?|第\s*\d+\s*名)/.test(answer) ||
    /(?:累计|总共|共计)?\s*学习(?:时长|时间)?\s*\d+\s*(?:小时|分钟|min|h)/i.test(answer) ||
    /(?:累计|总共)?\s*(?:做题|刷题|练习)\s*\d+\s*道/.test(answer) ||
    /(?:战胜|击败|超过)了?\s*\d+(?:\.\d+)?\s*%\s*的(?:同学|学生)/.test(answer);

  if (hasUnknownNumericRef || hasFabricatedRankOrHours) {
    return {
      status: 'REJECT',
      reason: 'UNKNOWN_NUMERIC_FACT',
      fallback: createDeterministicFallback(context, 'UNKNOWN_NUMERIC_FACT'),
    };
  }

  // 3. 编造不存在的知识点 (UNKNOWN_KNOWLEDGE_POINT)
  const validKpIds = new Set<string>();
  if (sf.current_knowledge_id) validKpIds.add(sf.current_knowledge_id);
  if (sf.next_action?.knowledgeId) validKpIds.add(sf.next_action.knowledgeId);
  if (sf.recent_quiz?.unlocked_nodes) {
    for (const id of sf.recent_quiz.unlocked_nodes) {
      validKpIds.add(id);
    }
  }

  // 检查 referenced_facts
  for (const fact of facts) {
    const match = fact.match(/knowledge_id=([A-Za-z0-9_]+)/i);
    if (match && !validKpIds.has(match[1])) {
      return {
        status: 'REJECT',
        reason: 'UNKNOWN_KNOWLEDGE_POINT',
        fallback: createDeterministicFallback(context, 'UNKNOWN_KNOWLEDGE_POINT'),
      };
    }
  }

  // 检查文本中的考点代号 (如 K99)
  const kpMatches = answer.match(/\bK\d{2,3}\b/g);
  if (kpMatches) {
    for (const kp of kpMatches) {
      if (!validKpIds.has(kp)) {
        return {
          status: 'REJECT',
          reason: 'UNKNOWN_KNOWLEDGE_POINT',
          fallback: createDeterministicFallback(context, 'UNKNOWN_KNOWLEDGE_POINT'),
        };
      }
    }
  }

  // 4. 虚假掌握度检测 (MASTERY_HALLUCINATION)
  for (const fact of facts) {
    const match = fact.match(/current_mastery_percent=(\d+(?:\.\d+)?)/i);
    if (match) {
      const val = parseFloat(match[1]);
      if (Math.abs(val - sf.current_mastery_percent) > 0.01) {
        return {
          status: 'REJECT',
          reason: 'MASTERY_HALLUCINATION',
          fallback: createDeterministicFallback(context, 'MASTERY_HALLUCINATION'),
        };
      }
    }
  }

  // 检查回答文本中关于掌握度数值的描述
  // 匹配形如 "掌握度达到了 80%"、"掌握度为 46%"、"掌握程度为 X%"
  // 排除 "掌握目标"、"达标目标" 或 "差距"
  const masteryPattern = /(?<![目达][标])(?:掌握度|掌握程度|已掌握|已经掌握了)(?:达到了?|约为?|为|是)?\s*(\d+(?:\.\d+)?)\s*%/g;
  let mMatch: RegExpExecArray | null;
  while ((mMatch = masteryPattern.exec(answer)) !== null) {
    const val = parseFloat(mMatch[1]);
    if (Math.abs(val - sf.current_mastery_percent) > 0.01) {
      return {
        status: 'REJECT',
        reason: 'MASTERY_HALLUCINATION',
        fallback: createDeterministicFallback(context, 'MASTERY_HALLUCINATION'),
      };
    }
  }

  // 5. 虚假达标阈值检测 (THRESHOLD_HALLUCINATION)
  for (const fact of facts) {
    const match = fact.match(/(?:mastery_target_percent|target_percent|threshold)=(\d+(?:\.\d+)?)/i);
    if (match) {
      const val = parseFloat(match[1]);
      if (Math.abs(val - sf.mastery_target_percent) > 0.01) {
        return {
          status: 'REJECT',
          reason: 'THRESHOLD_HALLUCINATION',
          fallback: createDeterministicFallback(context, 'THRESHOLD_HALLUCINATION'),
        };
      }
    }
  }

  const thresholdPattern = /(?:达标线|掌握目标|目标线|达标标准|达标阈值|目标阈值|门槛)(?:是|为|设为|设定为|达到)?\s*(\d+(?:\.\d+)?)\s*%/g;
  let tMatch: RegExpExecArray | null;
  while ((tMatch = thresholdPattern.exec(answer)) !== null) {
    const val = parseFloat(tMatch[1]);
    if (Math.abs(val - sf.mastery_target_percent) > 0.01) {
      return {
        status: 'REJECT',
        reason: 'THRESHOLD_HALLUCINATION',
        fallback: createDeterministicFallback(context, 'THRESHOLD_HALLUCINATION'),
      };
    }
  }

  // 6. 虚假解锁阻断 (FAKE_UNLOCK)
  const unlockedNodes = sf.recent_quiz?.unlocked_nodes || [];
  const hasUnlockClaim =
    /(?:已经?为你?解锁了?|新知识点已解锁|解锁了下一个?考点|解锁下一考点|为你解锁下一个考点|解锁了新考点|解锁了新知识点|解锁了下一知识点|解锁了后继)/.test(
      answer
    ) ||
    facts.some(
      (f) =>
        f.startsWith('unlocked_nodes=') &&
        f !== 'unlocked_nodes=' &&
        f !== 'unlocked_nodes=[]'
    );

  if (unlockedNodes.length === 0 && hasUnlockClaim) {
    return {
      status: 'REJECT',
      reason: 'FAKE_UNLOCK',
      fallback: createDeterministicFallback(context, 'FAKE_UNLOCK'),
    };
  }

  // 7. RETAIN 状态冲突阻断 (RETAIN_CONTRADICTION)
  // 当系统决策为 RETAIN 时，声称已经进入下一个知识点
  const isRetain = sf.recent_quiz?.action === 'RETAIN';
  const claimsAdvancedNext =
    /(?:已经?进入下(?:一个?|一)(?:个?)(?:知识点|考点)|进入下(?:一个?|一)(?:个?)(?:知识点|考点)|晋升至下(?:一个?|一)(?:个?)(?:知识点|考点))/.test(
      answer
    );

  if (isRetain && claimsAdvancedNext) {
    return {
      status: 'REJECT',
      reason: 'RETAIN_CONTRADICTION',
      fallback: createDeterministicFallback(context, 'RETAIN_CONTRADICTION'),
    };
  }

  // 8. 认知回退冲突阻断 (REGRESS_CONTRADICTION)
  // 当发生认知回退 (DEMOTE_TO_REVIEW / delta < 0) 时，声称掌握度提升
  const isRegress =
    sf.recent_quiz?.action === 'DEMOTE_TO_REVIEW' ||
    sf.recent_quiz?.reason_code === 'REVIEW_REQUIRED_DEMOTION' ||
    (sf.recent_quiz?.delta_percent ?? 0) < 0;

  const claimsProgress =
    /(?:掌握度(?:继续|稳步)?提升|掌握度(?:持续)?上升|取得了提升|成绩有所提高|掌握度有所提升|掌握度继续增加)/.test(
      answer
    );

  if (isRegress && claimsProgress) {
    return {
      status: 'REJECT',
      reason: 'REGRESS_CONTRADICTION',
      fallback: createDeterministicFallback(context, 'REGRESS_CONTRADICTION'),
    };
  }

  // 9. LOCKED 状态冲突阻断 (LOCKED_CONTRADICTION)
  // 当考点为 LOCKED 时，声称可以直接开始学习或测验
  const isLocked = sf.current_path_state === 'LOCKED' || !sf.prerequisites_met;
  const claimsCanDirectlyLearn =
    /(?:可以直接开始学习|可以直接开始测验|现在可以开始学习这个知识点|可以直接开始本考点|可以直接攻坚)/.test(
      answer
    );

  if (isLocked && claimsCanDirectlyLearn) {
    return {
      status: 'REJECT',
      reason: 'LOCKED_CONTRADICTION',
      fallback: createDeterministicFallback(context, 'LOCKED_CONTRADICTION'),
    };
  }

  // 10. 所有校验通过 (PASS)
  return {
    status: 'PASS',
    response,
  };
}
