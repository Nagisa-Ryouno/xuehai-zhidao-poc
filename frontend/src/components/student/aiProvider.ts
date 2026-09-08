/**
 * aiProvider.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-C
 * AI Provider 抽象层接口与规范
 *
 * 核心架构定位：
 * 1. 隔离外部模型：建立可替换、可测试、可失败、不可越权的 Provider 接口
 * 2. 严格输入边界：Provider 只能接收 LearningPromptContext，不得直接接收 Student、
 *    LearningPath、PathStates、后端原始响应或任何学习决策对象
 * 3. 严格输出边界：Provider 只能输出 StructuredAIResponse，不得输出任何学习决策字段
 * 4. 不得修改输入 Context
 */

import type { LearningPromptContext } from './learningPromptModel.ts';
import type { StructuredAIResponse } from './aiResponseModel.ts';

export interface AIProvider {
  /**
   * 依据给定的 PromptContext 生成结构化 AI 响应
   * @param promptContext 只读的白名单 Prompt 上下文
   */
  generate(
    promptContext: LearningPromptContext
  ): Promise<StructuredAIResponse>;
}
