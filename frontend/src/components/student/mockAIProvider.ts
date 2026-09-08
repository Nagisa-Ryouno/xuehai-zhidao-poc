/**
 * mockAIProvider.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-C
 * 确定性 Mock AI Provider
 *
 * 核心架构定位：
 * 1. 纯本地无网络：不发起网络请求、不使用 Math.random()、不使用 Date.now()、不使用 localStorage
 * 2. 100% 确定性输出：相同输入产生对象与 JSON 序列化完全一致的响应
 * 3. 严格输出契约：返回符合 StructuredAIResponse 规范的对象，绝无学习决策字段
 * 4. 故障与幻觉模拟：支持在测试模式下模拟大模型超时、崩溃、幻觉与非法结构
 */

import type { AIProvider } from './aiProvider.ts';
import type { LearningPromptContext } from './learningPromptModel.ts';
import type { StructuredAIResponse } from './aiResponseModel.ts';

export type MockBehaviorMode =
  | 'default'
  | 'mastery_hallucination'
  | 'fake_unlock'
  | 'retain_contradiction'
  | 'regress_contradiction'
  | 'locked_contradiction'
  | 'unknown_knowledge_point'
  | 'unknown_numeric_fact'
  | 'timeout'
  | 'throw_error'
  | 'malformed';

export interface MockAIProviderOptions {
  readonly mode?: MockBehaviorMode;
  readonly delayMs?: number;
  readonly customResponse?: StructuredAIResponse;
}

export class MockAIProvider implements AIProvider {
  private readonly mode: MockBehaviorMode;
  private readonly delayMs: number;
  private readonly customResponse?: StructuredAIResponse;

  constructor(options: MockAIProviderOptions = {}) {
    this.mode = options.mode || 'default';
    this.delayMs = options.delayMs || 0;
    this.customResponse = options.customResponse;
  }

  async generate(promptContext: LearningPromptContext): Promise<StructuredAIResponse> {
    if (this.delayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, this.delayMs));
    }

    if (this.mode === 'throw_error') {
      throw new Error('Simulated upstream AI model inference failure');
    }

    if (this.mode === 'timeout') {
      // 模拟长时间无响应超时 (unref 避免阻塞测试退出)
      return new Promise<StructuredAIResponse>((_, reject) => {
        const timer = setTimeout(() => reject(new Error('Provider timeout error')), 10000);
        if (typeof timer === 'object' && typeof (timer as unknown as { unref: () => void }).unref === 'function') {
          (timer as unknown as { unref: () => void }).unref();
        }
      });
    }

    if (this.mode === 'malformed') {
      // @ts-expect-error - deliberate malformed simulation for boundary testing
      return { invalid_field: 123, answer: null };
    }

    if (this.customResponse) {
      return this.customResponse;
    }

    const sf = promptContext.system_facts;
    const q = promptContext.user_question;

    if (this.mode === 'mastery_hallucination') {
      return {
        answer: `恭喜你！你对${sf.current_knowledge_name}的掌握度达到了 80%，表现非常优秀！`,
        referenced_facts: ['current_mastery_percent=80'],
        suggested_explanation: '已达到全站达标标准。',
        grounding_status: 'grounded',
      };
    }

    if (this.mode === 'fake_unlock') {
      return {
        answer: '太棒了，系统刚才已经为你解锁了下一个考点，现在可以去学习新内容了！',
        referenced_facts: ['unlocked_nodes=K09'],
        suggested_explanation: '新考点准入评估通过。',
        grounding_status: 'grounded',
      };
    }

    if (this.mode === 'retain_contradiction') {
      return {
        answer: '你已经进入下一个知识点收入与交叉弹性的学习。',
        referenced_facts: ['action=RETAIN'],
        suggested_explanation: '跨阶段流转。',
        grounding_status: 'grounded',
      };
    }

    if (this.mode === 'regress_contradiction') {
      return {
        answer: '你在本次测验中掌握度继续提升，请继续保持这种势头！',
        referenced_facts: ['action=DEMOTE_TO_REVIEW'],
        suggested_explanation: '认知稳步上升。',
        grounding_status: 'grounded',
      };
    }

    if (this.mode === 'locked_contradiction') {
      return {
        answer: `对于${sf.current_knowledge_name}，你现在可以直接开始学习这个知识点并参加微测验。`,
        referenced_facts: ['pathState=LOCKED'],
        suggested_explanation: '随时可以开始。',
        grounding_status: 'grounded',
      };
    }

    if (this.mode === 'unknown_knowledge_point') {
      return {
        answer: '建议你先去攻坚知识点 K99（宏观货币传导模型），然后再回来继续学习。',
        referenced_facts: ['knowledge_id=K99'],
        suggested_explanation: '前置补充。',
        grounding_status: 'grounded',
      };
    }

    if (this.mode === 'unknown_numeric_fact') {
      return {
        answer: '你目前在全班排名第 3 名，已累计学习 100 小时，非常勤奋！',
        referenced_facts: ['rank=3', 'hours=100'],
        suggested_explanation: '学情榜单。',
        grounding_status: 'grounded',
      };
    }

    // Default mode: 依据客观系统事实生成 100% 确定性回答
    let answerText = '';
    const referencedFacts: string[] = [
      `current_knowledge_id=${sf.current_knowledge_id}`,
      `current_mastery_percent=${sf.current_mastery_percent}`,
      `mastery_target_percent=${sf.mastery_target_percent}`,
    ];

    if (q.includes('为什么推荐') || q.includes('理由') || q.includes('为什么学')) {
      answerText = `根据你的学情画像，当前推荐考点是「${sf.current_knowledge_name}」(${sf.current_knowledge_id})。当前状态为 ${sf.current_path_state}，优先级为「${sf.path_priority}」。当前掌握度为 ${sf.current_mastery_percent}%，全站掌握目标是 ${sf.mastery_target_percent}%。`;
    } else if (q.includes('掌握度') || q.includes('差多少') || q.includes('目标') || q.includes('情况')) {
      answerText = `你当前正在学习${sf.current_knowledge_name}，掌握度为 ${sf.current_mastery_percent}%，全站掌握目标是 ${sf.mastery_target_percent}%，距离达标还有 ${sf.mastery_gap_percent}% 差距，系统建议继续挑战微测验。`;
    } else if (q.includes('下一步') || q.includes('接下来') || q.includes('做什么')) {
      answerText = `根据自适应学习引擎规划，你接下来的推荐行动是：${sf.next_action.label}。`;
      referencedFacts.push(`next_action=${sf.next_action.type}`);
    } else {
      answerText = `你好，${sf.student_name}！你当前正在攻坚${sf.current_chapter}下的考点「${sf.current_knowledge_name}」。当前掌握度为 ${sf.current_mastery_percent}%，目标为 ${sf.mastery_target_percent}%。系统建议按照推荐路径开展练习。`;
    }

    return {
      answer: answerText,
      referenced_facts: Object.freeze(referencedFacts),
      suggested_explanation: `基于考点 ${sf.current_knowledge_id} 客观系统事实生成的回答。`,
      grounding_status: 'grounded',
    };
  }
}
