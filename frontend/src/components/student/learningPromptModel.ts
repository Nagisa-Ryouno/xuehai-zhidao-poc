/**
 * learningPromptModel.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-B
 * Prompt Context Formatter & Grounding Boundary
 *
 * 核心架构定位：
 * 1. 100% 纯函数边界：无 React、DOM、网络、localStorage、Date.now、Math.random 与全局副作用
 * 2. 白名单投影 (Whitelist Projection)：仅暴露 AI 伴学所需的最小事实集，彻底剔除内部私有与敏感字段
 * 3. 严格规则注入：固定注入 10 项 Grounding Rules，约束 AI 角色与行为红线
 * 4. 确定性与不可变性：相同输入产出完全等价对象，返回深度冻结的不可变结构
 */

import type {
  PathState,
  NextLearningAction,
  LearningContext,
} from '../../types.ts';

/**
 * AI 伴学 10 项客观事实接地约束规则 (Grounding Rules)
 */
export const GROUNDING_RULES = [
  '1. Only use supplied system facts.',
  '2. Never invent mastery values.',
  '3. Never invent knowledge points.',
  '4. Never invent unlock events.',
  '5. Never modify next_action.',
  '6. Never modify PathState.',
  '7. Never claim an action was executed unless supplied as a system fact.',
  '8. If the context does not contain an answer, explicitly state that the system does not currently provide that fact.',
  '9. Explain decisions instead of replacing them.',
  '10. The AI has no authority over learning progression.',
] as const;

export interface LearningPromptSystemFacts {
  readonly student_id: string;
  readonly student_name: string;
  readonly major: string;
  readonly grade: string;
  readonly learning_goal: string;

  readonly current_knowledge_id: string;
  readonly current_knowledge_name: string;
  readonly current_chapter: string;
  readonly current_path_state: PathState;

  readonly current_mastery_percent: number;
  readonly mastery_target_percent: number;
  readonly mastery_gap_percent: number;
  readonly is_mastered: boolean;

  readonly prerequisites_met: boolean;
  readonly path_priority: string;
  readonly is_path_completed: boolean;

  readonly recent_quiz?: LearningContext['system_facts']['recent_quiz'];

  readonly next_action: NextLearningAction;
}

export interface LearningPromptContext {
  readonly user_question: string;
  readonly system_facts: LearningPromptSystemFacts;
  readonly grounding_rules: readonly string[];
}

/**
 * 递归冻结对象，确保 PromptContext 构建完成后深度不可变
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
 * 将 LearningContext 投影为结构化且安全隔离的 LearningPromptContext
 * 纯函数：不调用 Math.random() 与 Date.now()
 */
export function buildLearningPromptContext(
  learningContext: LearningContext,
  userQuestion: string
): LearningPromptContext {
  const sf = learningContext.system_facts;

  // 1. 清理用户输入文本，去除首尾空白
  const trimmedQuestion = (userQuestion || '').trim();

  // 2. 白名单投影 system_facts，严格排除私有字段与决策后门
  let projectedRecentQuiz: LearningContext['system_facts']['recent_quiz'] | undefined;
  if (sf.recent_quiz) {
    projectedRecentQuiz = Object.freeze({
      question_id: String(sf.recent_quiz.question_id || ''),
      is_correct: Boolean(sf.recent_quiz.is_correct),
      time_spent_ms: Number(sf.recent_quiz.time_spent_ms || 0),
      before_mastery_percent: Number(sf.recent_quiz.before_mastery_percent || 0),
      after_mastery_percent: Number(sf.recent_quiz.after_mastery_percent || 0),
      delta_percent: Number(sf.recent_quiz.delta_percent || 0),
      action: sf.recent_quiz.action,
      reason_code: sf.recent_quiz.reason_code,
      unlocked_nodes: Object.freeze([...(sf.recent_quiz.unlocked_nodes || [])]),
    });
  }

  const projectedNextAction: NextLearningAction = Object.freeze({
    type: sf.next_action.type,
    ...(sf.next_action.knowledgeId ? { knowledgeId: sf.next_action.knowledgeId } : {}),
    ...(sf.next_action.knowledgeName ? { knowledgeName: sf.next_action.knowledgeName } : {}),
    label: sf.next_action.label,
  });

  const projectedFacts: LearningPromptSystemFacts = Object.freeze({
    student_id: String(sf.student_id || ''),
    student_name: String(sf.student_name || ''),
    major: String(sf.major || ''),
    grade: String(sf.grade || ''),
    learning_goal: String(sf.learning_goal || ''),

    current_knowledge_id: String(sf.current_knowledge_id || ''),
    current_knowledge_name: String(sf.current_knowledge_name || ''),
    current_chapter: String(sf.current_chapter || ''),
    current_path_state: sf.current_path_state,

    current_mastery_percent: sf.current_mastery_percent,
    mastery_target_percent: sf.mastery_target_percent,
    mastery_gap_percent: sf.mastery_gap_percent,
    is_mastered: sf.is_mastered,

    prerequisites_met: sf.prerequisites_met,
    path_priority: sf.path_priority,
    is_path_completed: sf.is_path_completed,

    recent_quiz: projectedRecentQuiz,
    next_action: projectedNextAction,
  });

  // 3. 组装 PromptContext 并深度冻结
  const promptContext: LearningPromptContext = {
    user_question: trimmedQuestion,
    system_facts: projectedFacts,
    grounding_rules: Object.freeze([...GROUNDING_RULES]),
  };

  return deepFreeze(promptContext);
}
