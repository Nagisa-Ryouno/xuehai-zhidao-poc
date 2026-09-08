/**
 * aiResponseModel.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-B
 * Structured AI Response Contract
 *
 * 核心架构定位：
 * 1. 结构化大模型输出契约：仅定义回答内容、引用的系统事实与接地状态
 * 2. 绝对决策权隔离：严禁在此包含 next_action、decision、unlock_nodes 等决策字段
 * 3. 强类型只读保护：所有字段均为 readonly
 */

export interface StructuredAIResponse {
  readonly answer: string;

  readonly referenced_facts: readonly string[];

  readonly suggested_explanation?: string;

  readonly grounding_status: 'grounded' | 'insufficient_context';
}
