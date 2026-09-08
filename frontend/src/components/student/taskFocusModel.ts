/**
 * taskFocusModel.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 2.2-B / Sprint 2
 * 学生端今日学习任务中心纯模型与决策引擎 (Today's Learning Mission Model & Decision Core)
 *
 * 核心职责：
 * 1. 路径节点状态解析 (resolveStepPathState)
 * 2. 核心焦点任务仲裁 (resolveCurrentFocusTask): IN_PROGRESS > AVAILABLE > others
 * 3. BKT 掌握度跃迁测算与阶段演进判定 (calculateMasteryTransition)
 * 4. 下一步学习行动统一决策引擎 (getNextLearningAction)
 */

import type { LearningPathStep, PathState, DecisionAuditEnvelope } from '../../types.ts';
import { getUnlockedDownstreamNodes } from './quizModel.ts';

/**
 * 全站统一掌握度目标常量基准 (Sprint 4 不变量)
 */
export const MASTERY_TARGET_THRESHOLD = 0.80;
export const MASTERY_TARGET_PERCENT = 80;

export type CurrentFocusStatus = 'FOUND' | 'ALL_COMPLETED' | 'ALL_LOCKED' | 'EMPTY';

export interface CurrentFocusTask {
  knowledgeId: string;
  knowledgeName: string;
  chapter: string;
  pathState: PathState;
  currentMasteryPercent: number;
  targetMasteryPercent: number;
  reason: string;
  actionLabel: string;
  step: LearningPathStep;
}

export interface CurrentFocusResult {
  status: CurrentFocusStatus;
  focus?: CurrentFocusTask;
  message?: string;
}

export type MasteryLevel = 'WEAK' | 'DEVELOPING' | 'MASTERED';

export type MasteryTransitionTag =
  | 'WEAK_TO_DEVELOPING'
  | 'DEVELOPING_TO_MASTERED'
  | 'WEAK_TO_MASTERED'
  | 'MASTERY_RETAINED'
  | 'STILL_WEAK'
  | 'REGRESSED';

export interface MasteryTransitionResult {
  beforePercentStr: string;
  afterPercentStr: string;
  deltaPercentStr: string;
  deltaValue: number;
  beforeLevel: MasteryLevel;
  afterLevel: MasteryLevel;
  transitionTag: MasteryTransitionTag;
  badgeText: string;
  message: string;
}

export interface NextLearningAction {
  type: 'CONTINUE_NEXT' | 'RETRY' | 'RETURN_TASKS';
  knowledgeId?: string;
  knowledgeName?: string;
  label: string;
}

/**
 * 解析知识点路径状态：优先读取真实状态字典，未命中时依据阶段序号与当前正确率推导
 */
export function resolveStepPathState(
  step: LearningPathStep,
  index: number,
  pathStates?: Record<string, PathState>
): PathState {
  if (pathStates && pathStates[step.knowledge_id]) {
    return pathStates[step.knowledge_id];
  }
  if (step.current_accuracy >= MASTERY_TARGET_PERCENT) return 'COMPLETED';
  if (index === 0) return 'IN_PROGRESS';
  return 'AVAILABLE';
}

/**
 * 从学习路径与路径状态中仲裁出当前最值得学生执行的核心焦点任务
 * 优先级规则：IN_PROGRESS > AVAILABLE > others
 */
export function resolveCurrentFocusTask(
  learningPath: LearningPathStep[],
  pathStates?: Record<string, PathState>
): CurrentFocusResult {
  if (!learningPath || learningPath.length === 0) {
    return {
      status: 'EMPTY',
      message: '🎉 当前没有需要立即攻坚的任务\n你的学习路径暂时没有新的可执行任务。',
    };
  }

  // 映射所有步骤的状态
  const mappedSteps = learningPath.map((step, idx) => ({
    step,
    pathState: resolveStepPathState(step, idx, pathStates),
  }));

  // 1. 查找第一个 IN_PROGRESS
  const inProgressMatch = mappedSteps.find((s) => s.pathState === 'IN_PROGRESS');
  if (inProgressMatch) {
    return {
      status: 'FOUND',
      focus: buildFocusTask(inProgressMatch.step, inProgressMatch.pathState, '继续挑战微测验'),
    };
  }

  // 2. 查找第一个 AVAILABLE
  const availableMatch = mappedSteps.find((s) => s.pathState === 'AVAILABLE');
  if (availableMatch) {
    return {
      status: 'FOUND',
      focus: buildFocusTask(availableMatch.step, availableMatch.pathState, '开始微测验'),
    };
  }

  // 3. 检查是否全部已完成
  const allCompleted = mappedSteps.every((s) => s.pathState === 'COMPLETED');
  if (allCompleted) {
    const firstStep = mappedSteps[0]?.step;
    return {
      status: 'ALL_COMPLETED',
      focus: firstStep ? buildFocusTask(firstStep, 'COMPLETED', '复习微测验') : undefined,
      message: '🎉 太棒了！当前学习路径中的考点均已达标掌握。',
    };
  }

  // 4. 检查是否全部被锁定 (LOCKED)
  const allLocked = mappedSteps.every((s) => s.pathState === 'LOCKED');
  if (allLocked) {
    return {
      status: 'ALL_LOCKED',
      message: '当前所有待攻坚考点的前置依赖尚未满足，请先前往知识图谱学习前置考点。',
    };
  }

  // 5. 兜底：选取第一个未完成节点
  const firstUnfinished = mappedSteps.find((s) => s.pathState !== 'COMPLETED') || mappedSteps[0];
  const label =
    firstUnfinished.pathState === 'LOCKED'
      ? '需先掌握前置'
      : firstUnfinished.pathState === 'COMPLETED'
      ? '复习微测验'
      : '开始微测验';

  return {
    status: 'FOUND',
    focus: buildFocusTask(firstUnfinished.step, firstUnfinished.pathState, label),
  };
}

function buildFocusTask(
  step: LearningPathStep,
  pathState: PathState,
  actionLabel: string
): CurrentFocusTask {
  return {
    knowledgeId: step.knowledge_id,
    knowledgeName: step.knowledge_name,
    chapter: step.chapter,
    pathState,
    currentMasteryPercent: Math.round(step.current_accuracy || 0),
    targetMasteryPercent: MASTERY_TARGET_PERCENT,
    reason: step.reason || '这是你当前学习路径中优先级最高的可学习考点。',
    actionLabel,
    step,
  };
}

/**
 * 掌握度数值解析辅助函数 (统一转换为 0~100 百分比数值)
 */
function parseMasteryToPercent(val: number | string | undefined | null): number {
  if (val === undefined || val === null || val === '') return 0;
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return 0;
  if (num <= 1.0) {
    return num * 100;
  }
  return num;
}

/**
 * 判定掌握度等级
 * < 60%: WEAK (薄弱)
 * >= 60% && < 80%: DEVELOPING (发展中)
 * >= 80%: MASTERED (已掌握)
 */
export function getMasteryLevel(percent: number): MasteryLevel {
  if (percent >= MASTERY_TARGET_PERCENT) return 'MASTERED';
  if (percent >= 60) return 'DEVELOPING';
  return 'WEAK';
}

/**
 * 计算 BKT 掌握度跃迁数据与阶段演进结果
 */
export function calculateMasteryTransition(
  beforeMastery: number | string,
  afterMastery: number | string
): MasteryTransitionResult {
  const beforeP = parseMasteryToPercent(beforeMastery);
  const afterP = parseMasteryToPercent(afterMastery);

  const beforePercentStr = `${beforeP.toFixed(2)}%`;
  const afterPercentStr = `${afterP.toFixed(2)}%`;

  const delta = afterP - beforeP;
  const deltaSign = delta >= 0 ? '+' : '';
  const deltaPercentStr = `${deltaSign}${delta.toFixed(2)}%`;

  const beforeLevel = getMasteryLevel(beforeP);
  const afterLevel = getMasteryLevel(afterP);

  let transitionTag: MasteryTransitionTag = 'STILL_WEAK';
  let badgeText = '本次练习已记录';
  let message = '继续练习以提升掌握度。';

  if (delta < 0 && beforeLevel !== 'WEAK' && afterLevel === 'WEAK') {
    transitionTag = 'REGRESSED';
    badgeText = '⚠️ 掌握度有所回退';
    message = '掌握度出现回退，建议针对错题重点复习巩固。';
  } else if (beforeLevel === 'WEAK' && afterLevel === 'DEVELOPING') {
    transitionTag = 'WEAK_TO_DEVELOPING';
    badgeText = '📈 正在进入发展阶段';
    message = '掌握度稳步提升，已脱离薄弱阶段！';
  } else if (beforeLevel === 'DEVELOPING' && afterLevel === 'MASTERED') {
    transitionTag = 'DEVELOPING_TO_MASTERED';
    badgeText = '🎉 已达到掌握目标';
    message = `恭喜！该考点已成功达成 ${MASTERY_TARGET_PERCENT}% 掌握度目标。`;
  } else if (beforeLevel === 'WEAK' && afterLevel === 'MASTERED') {
    transitionTag = 'WEAK_TO_MASTERED';
    badgeText = '🎉 已达到掌握目标';
    message = `重大突破！该考点掌握度跨越达成 ${MASTERY_TARGET_PERCENT}% 目标。`;
  } else if (afterLevel === 'MASTERED') {
    transitionTag = 'MASTERY_RETAINED';
    badgeText = '🎉 持续保持达标';
    message = '该考点持续保持达标掌握状态。';
  } else if (beforeLevel === 'WEAK' && afterLevel === 'WEAK') {
    transitionTag = 'STILL_WEAK';
    badgeText = '📚 巩固中';
    message = '本次练习已记录。当前掌握度仍低于目标，建议继续练习该考点。';
  } else {
    transitionTag = delta >= 0 ? 'WEAK_TO_DEVELOPING' : 'REGRESSED';
    badgeText = delta >= 0 ? '📈 练习有进步' : '⚠️ 掌握度波动';
    message = delta >= 0 ? '继续保持！' : '建议再加把劲。';
  }

  return {
    beforePercentStr,
    afterPercentStr,
    deltaPercentStr,
    deltaValue: delta,
    beforeLevel,
    afterLevel,
    transitionTag,
    badgeText,
    message,
  };
}

/**
 * 统一确定下一步学习行动 (Next Action)
 * 优先级：
 * 1. 存在刚刚解锁的 downstream -> CONTINUE_NEXT (继续学习下一个考点)
 * 2. 当前考点仍未掌握 -> RETRY (继续挑战当前考点)
 * 3. 当前考点已掌握但无 downstream -> RETURN_TASKS (返回今日任务)
 * 4. 无法确定 -> RETURN_TASKS (返回今日任务)
 */
export function getNextLearningAction(params: {
  currentKnowledgeId: string;
  currentKnowledgeName?: string;
  replanning?: DecisionAuditEnvelope | null;
  pathStates?: Record<string, PathState>;
  afterMastery?: number | string | null;
  summaryAccuracy?: number;
}): NextLearningAction {
  const { currentKnowledgeId, replanning, afterMastery, summaryAccuracy } = params;

  // 1. 检查是否存在通过 UNLOCK_DOWNSTREAM 解锁的后继考点
  if (replanning?.canonical_payload?.action === 'UNLOCK_DOWNSTREAM') {
    const unlocked = getUnlockedDownstreamNodes(replanning, currentKnowledgeId);
    if (unlocked.length > 0) {
      const nextId = unlocked[0];
      return {
        type: 'CONTINUE_NEXT',
        knowledgeId: nextId,
        knowledgeName: `考点 ${nextId}`,
        label: `继续学习下一个考点 ${nextId}`,
      };
    }
  }

  // 2. 检查当前考点是否已达成掌握目标 (>= 80% 或 >= 0.80)
  const masteryVal =
    afterMastery !== undefined && afterMastery !== null
      ? parseMasteryToPercent(afterMastery)
      : summaryAccuracy !== undefined
      ? summaryAccuracy
      : null;

  const isMastered = masteryVal !== null && masteryVal >= MASTERY_TARGET_PERCENT;

  if (!isMastered) {
    return {
      type: 'RETRY',
      knowledgeId: currentKnowledgeId,
      knowledgeName: params.currentKnowledgeName,
      label: '继续挑战当前考点',
    };
  }

  // 3. 已掌握但没有明确后继解锁
  return {
    type: 'RETURN_TASKS',
    label: '返回今日任务',
  };
}
