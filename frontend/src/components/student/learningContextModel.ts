/**
 * learningContextModel.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-A
 * AI 学习伴学上下文纯函数模型 (Grounded Learning Context Model & Boundary)
 *
 * 核心架构定位：
 * 1. 100% 纯函数边界层：无 React、无 DOM、无 fetch、无网络 IO、无 localStorage、无随机数、无 Date.now()、无全局状态、无副作用
 * 2. 单向事实流转：只从已有系统事实 (Profile、Path、PathState、Focus、Quiz) 投影出只读结构化 Context，不赋予 AI 任何决策权
 * 3. 严格复用现有业务基线：全站复用 MASTERY_TARGET_THRESHOLD/PERCENT，禁止散落第二套掌握度阈值
 * 4. 深度冻结 (Deep Freeze)：返回只读对象，杜绝外部或 AI 标注反向污染系统事实
 */

import type {
  StudentBasic,
  LearningPathStep,
  PathState,
  QuizSubmitResponse,
  PathAction,
  ReplanningReasonCode,
  LearningContext,
  LearningContextSystemFacts,
  LearningContextDerivedExplanations,
  RecentQuizFact,
  NextLearningAction,
} from '../../types.ts';

import {
  MASTERY_TARGET_THRESHOLD,
  MASTERY_TARGET_PERCENT,
  resolveStepPathState,
  resolveCurrentFocusTask,
  getNextLearningAction,
  type CurrentFocusResult,
} from './taskFocusModel.ts';

import {
  getRecommendationExplanation,
  getLearningProgressionExplanation,
} from './adaptiveLearningModel.ts';

import { getUnlockedDownstreamNodes } from './quizModel.ts';

// 统一重导出全站唯一掌握度基准常量
export {
  MASTERY_TARGET_THRESHOLD,
  MASTERY_TARGET_PERCENT,
};

export interface LearningContextInput {
  readonly student: StudentBasic;
  readonly learningPath?: readonly LearningPathStep[];
  readonly pathStates?: Readonly<Record<string, PathState>>;
  readonly currentFocus?: CurrentFocusResult;
  readonly recentQuizFeedback?: (QuizSubmitResponse & { time_spent_ms?: number }) | null;
  readonly activeKnowledgeId?: string;
  readonly activeKnowledgeName?: string;
}

/**
 * 递归冻结对象，确保 Context 返回后为完全不可变的数据边界 (Immutable Boundary)
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
 * 安全解析数值为 0~100 百分比数值
 */
function parseToPercentNumber(val: number | string | undefined | null): number {
  if (val === undefined || val === null || val === '') return 0;
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return 0;
  if (num <= 1.0) {
    return Number((num * 100).toFixed(2));
  }
  return Number(num.toFixed(2));
}

/**
 * 构建严格只读、事实对齐的 LearningContext
 */
export function buildLearningContext(input: LearningContextInput): LearningContext {
  const {
    student,
    learningPath = [],
    pathStates = {},
    currentFocus,
    recentQuizFeedback,
  } = input;

  // 1. 仲裁当前焦点任务 (如未提供则依据 learningPath 与 pathStates 纯推导)
  const resolvedFocusResult =
    currentFocus || resolveCurrentFocusTask(learningPath as LearningPathStep[], pathStates);

  // 2. 提取当前考点与路径状态事实
  let knowledgeId = '';
  let knowledgeName = '';
  let chapter = '';
  let pathState: PathState = 'LOCKED';
  let currentMasteryPercent = 0;
  let pathPriority = '中';

  const firstStep = learningPath[0];

  if (resolvedFocusResult.focus) {
    const f = resolvedFocusResult.focus;
    knowledgeId = f.knowledgeId;
    knowledgeName = f.knowledgeName;
    chapter = f.chapter;
    pathState = f.pathState;
    currentMasteryPercent = f.currentMasteryPercent;
    pathPriority = f.step?.priority || '中';
  } else if (resolvedFocusResult.status === 'ALL_COMPLETED') {
    knowledgeId = firstStep?.knowledge_id || 'COMPLETED_STAGE';
    knowledgeName = firstStep?.knowledge_name || '所有阶段考点已达标掌握';
    chapter = firstStep?.chapter || '微观经济学';
    pathState = 'COMPLETED';
    currentMasteryPercent = firstStep ? parseToPercentNumber(firstStep.current_accuracy) : 100;
    pathPriority = '已达成';
  } else if (resolvedFocusResult.status === 'ALL_LOCKED') {
    knowledgeId = firstStep?.knowledge_id || 'LOCKED_STAGE';
    knowledgeName = firstStep?.knowledge_name || '前置考点待攻坚';
    chapter = firstStep?.chapter || '微观经济学';
    pathState = 'LOCKED';
    currentMasteryPercent = firstStep ? parseToPercentNumber(firstStep.current_accuracy) : 0;
    pathPriority = '高';
  } else {
    // EMPTY 状态
    knowledgeId = 'NO_TASK';
    knowledgeName = '暂无待攻坚任务';
    chapter = '学习规划';
    pathState = 'AVAILABLE';
    currentMasteryPercent = 0;
    pathPriority = '低';
  }

  // 兜底防御：杜绝产生 undefined、null 或 "undefined" 节点名
  if (!knowledgeId || knowledgeId === 'undefined' || knowledgeId === 'null') {
    knowledgeId = 'STAGE_OVERVIEW';
  }
  if (!knowledgeName || knowledgeName === 'undefined' || knowledgeName === 'null') {
    knowledgeName = '学习路径总览';
  }

  // 3. 掌握度目标与差距分析 (严格复用 MASTERY_TARGET 常量，禁止散落硬编码)
  const masteryTargetPercent = MASTERY_TARGET_PERCENT;
  const masteryTargetThreshold = MASTERY_TARGET_THRESHOLD;
  const masteryGapPercent = Math.max(0, Number((masteryTargetPercent - currentMasteryPercent).toFixed(2)));
  const isMastered = currentMasteryPercent >= masteryTargetPercent;

  // 4. 前置条件就绪事实 (依据真实 PathState：LOCKED 即未满足)
  const prerequisitesMet = pathState !== 'LOCKED';

  // 5. 路径完成判定
  const isPathCompleted =
    resolvedFocusResult.status === 'ALL_COMPLETED' ||
    (learningPath.length > 0 &&
      learningPath.every(
        (s, idx) => resolveStepPathState(s, idx, pathStates) === 'COMPLETED'
      ));

  // 6. 提取最近一次测验判题事实 (Recent Quiz Facts)
  let recentQuizFact: RecentQuizFact | undefined;

  if (recentQuizFeedback) {
    const fb = recentQuizFeedback;
    const payload = fb.replanning?.canonical_payload;

    const action: PathAction = (payload?.action || 'RETAIN') as PathAction;
    const reasonCode: ReplanningReasonCode = (payload?.reason_code || 'MASTERY_STATE_UNCHANGED') as ReplanningReasonCode;

    // 掌握度变化数值解析
    let beforeMasteryPercent = 0;
    let afterMasteryPercent = currentMasteryPercent;

    if (payload?.before_mastery) {
      beforeMasteryPercent = parseToPercentNumber(payload.before_mastery);
    } else if (fb.learning_state?.mastery_percent) {
      beforeMasteryPercent = Number(fb.learning_state.mastery_percent.toFixed(2));
    }

    if (payload?.after_mastery) {
      afterMasteryPercent = parseToPercentNumber(payload.after_mastery);
    } else if (fb.learning_state?.mastery_percent) {
      afterMasteryPercent = Number(fb.learning_state.mastery_percent.toFixed(2));
    }

    const deltaPercent = Number((afterMasteryPercent - beforeMasteryPercent).toFixed(2));

    // 严格解锁守则：只有 UNLOCK_DOWNSTREAM 时才能有 unlocked_nodes，RETAIN 时严格为空数组
    let unlockedNodes: string[] = [];
    if (action === 'UNLOCK_DOWNSTREAM' && fb.replanning) {
      unlockedNodes = getUnlockedDownstreamNodes(fb.replanning, knowledgeId);
    }

    recentQuizFact = {
      question_id: fb.question_id || '',
      is_correct: Boolean(fb.is_correct),
      time_spent_ms: typeof fb.time_spent_ms === 'number' ? fb.time_spent_ms : 0,
      before_mastery_percent: beforeMasteryPercent,
      after_mastery_percent: afterMasteryPercent,
      delta_percent: deltaPercent,
      action,
      reason_code: reasonCode,
      unlocked_nodes: Object.freeze(unlockedNodes),
    };
  }

  // 7. 系统下一步行动仲裁 (严格调用确定性决策模型，禁止 AI 决策篡改)
  const nextAction: NextLearningAction = getNextLearningAction({
    currentKnowledgeId: knowledgeId,
    currentKnowledgeName: knowledgeName,
    replanning: recentQuizFeedback?.replanning,
    afterMastery: recentQuizFact ? recentQuizFact.after_mastery_percent / 100 : currentMasteryPercent / 100,
  });

  // 8. 提炼基于事实的纯函数解释 (Derived Explanations)
  let recommendationReason = '基于当前学情画像推荐的基础学习任务。';
  if (resolvedFocusResult.focus) {
    const recExp = getRecommendationExplanation({
      step: resolvedFocusResult.focus.step,
      pathState,
      currentMasteryPercent,
      targetMasteryPercent: masteryTargetPercent,
    });
    recommendationReason = recExp.reason;
  }

  let progressionSummary: string | undefined;
  if (recentQuizFeedback) {
    const progExp = getLearningProgressionExplanation({
      beforeMastery: recentQuizFact?.before_mastery_percent ?? 0,
      afterMastery: recentQuizFact?.after_mastery_percent ?? currentMasteryPercent,
      replanning: recentQuizFeedback.replanning,
      currentKnowledgeId: knowledgeId,
      currentKnowledgeName: knowledgeName,
    });
    progressionSummary = `${progExp.stageChange.badgeText}：${progExp.stageChange.message}`;
  }

  let actionGuidance = '继续按照推荐顺序开展日常学习。';
  if (nextAction.type === 'CONTINUE_NEXT') {
    actionGuidance = `已达成阶段掌握目标，建议继续攻坚下一个考点：${nextAction.knowledgeName || nextAction.knowledgeId}。`;
  } else if (nextAction.type === 'RETRY') {
    actionGuidance = `当前考点掌握度尚未达到 ${masteryTargetPercent}% 目标，建议继续挑战该微测验进行巩固。`;
  } else if (nextAction.type === 'RETURN_TASKS') {
    actionGuidance = '当前阶段推荐考点已全部达标，可以前往今日任务中心或知识图谱查看拓展内容。';
  }

  // 9. 构造精简的系统事实白名单投影 (过滤未授权的敏感/冗余私有字段)
  const systemFacts: LearningContextSystemFacts = {
    student_id: String(student.student_id || ''),
    student_name: String(student.student_name || ''),
    major: String(student.major || ''),
    grade: String(student.grade || ''),
    learning_goal: String(student.learning_goal || ''),

    current_knowledge_id: knowledgeId,
    current_knowledge_name: knowledgeName,
    current_chapter: chapter,
    current_path_state: pathState,

    current_mastery_percent: currentMasteryPercent,
    mastery_target_percent: masteryTargetPercent,
    mastery_target_threshold: masteryTargetThreshold,
    mastery_gap_percent: masteryGapPercent,
    is_mastered: isMastered,

    prerequisites_met: prerequisitesMet,
    path_priority: pathPriority,
    is_path_completed: isPathCompleted,

    recent_quiz: recentQuizFact,

    next_action: nextAction,
  };

  const derivedExplanations: LearningContextDerivedExplanations = {
    recommendation_reason: recommendationReason,
    progression_summary: progressionSummary,
    action_guidance: actionGuidance,
  };

  // 10. 深度冻结并返回
  const context: LearningContext = {
    system_facts: systemFacts,
    derived_explanations: derivedExplanations,
  };

  return deepFreeze(context);
}
