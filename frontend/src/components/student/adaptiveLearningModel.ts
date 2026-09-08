/**
 * adaptiveLearningModel.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 2.2-C / Sprint 4
 * 自适应学习智能化解释模型 (Adaptive Learning Explanation & Presentation Model)
 *
 * 核心架构定位：
 * 1. 100% 纯函数模型层：无 React、无 DOM、无 Router、无 Context、无网络 IO、无全局副作用
 * 2. 单向解释性：只负责将已有事实 (BKT、PathState、Replanning) 转换为人类可理解的确定性语义，不创造事实
 * 3. 证据驱动 (Evidence-Based)：推荐原因与跃迁解释必须 100% 对应输入事实，严禁生成虚假解锁或空洞话术
 */

import type {
  LearningPathStep,
  PathState,
  DecisionAuditEnvelope,
} from '../../types.ts';
import {
  MASTERY_TARGET_THRESHOLD,
  MASTERY_TARGET_PERCENT,
  getMasteryLevel,
  getNextLearningAction,
  type MasteryLevel,
  type NextLearningAction,
} from './taskFocusModel.ts';
import { getUnlockedDownstreamNodes } from './quizModel.ts';

// 统一重导出全站掌握度唯一基准常量与类型
export {
  MASTERY_TARGET_THRESHOLD,
  MASTERY_TARGET_PERCENT,
  type MasteryLevel,
  type NextLearningAction,
};

/**
 * 判定掌握度是否达到达标目标阈值 (0.80 / 80%)
 */
export function isMasteryGoalReached(
  val: number | string | undefined | null
): boolean {
  if (val === undefined || val === null || val === '') return false;
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return false;
  if (num <= 1.0) {
    return num >= MASTERY_TARGET_THRESHOLD;
  }
  return num >= MASTERY_TARGET_PERCENT;
}

/**
 * 辅助：将掌握度统一转换为 0~1 区间的小数
 */
function parseMasteryFraction(val: number | string | undefined | null): number {
  if (val === undefined || val === null || val === '') return 0;
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return 0;
  if (num > 1.0) {
    return Number((num / 100).toFixed(4));
  }
  return Number(num.toFixed(4));
}

// ============================================================
// 一、推荐解释模型 (Recommendation Explanation)
// ============================================================

export interface RecommendationExplanation {
  title: string;
  reason: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  factors: string[];
}

/**
 * 根据考点步骤与当前状态，推导基于证据的推荐解释
 */
export function getRecommendationExplanation(params: {
  step: LearningPathStep;
  pathState: PathState;
  currentMasteryPercent: number;
  targetMasteryPercent: number;
}): RecommendationExplanation {
  const { step, pathState, currentMasteryPercent, targetMasteryPercent } = params;

  // 1. 推导优先级 (严格遵循系统焦点规则)
  let priority: 'HIGH' | 'MEDIUM' | 'LOW' = 'MEDIUM';
  if (pathState === 'IN_PROGRESS') {
    priority = 'HIGH';
  } else if (pathState === 'AVAILABLE') {
    if (step.priority === '高') {
      priority = 'HIGH';
    } else if (step.priority === '低') {
      priority = 'LOW';
    } else {
      priority = 'MEDIUM';
    }
  } else {
    priority = 'LOW';
  }

  // 2. 真实事实依据提取 (Evidence-Based Factors)
  const factors: string[] = [];

  // 事实 1: 当前考点路径状态
  if (pathState === 'IN_PROGRESS') {
    factors.push('当前考点正在进行中（核心主线攻坚任务）');
  } else if (pathState === 'AVAILABLE') {
    factors.push('当前考点已满足先修前置条件，处于就绪可学状态');
  } else if (pathState === 'COMPLETED') {
    factors.push(`当前考点已达标掌握（掌握度已达到 ${targetMasteryPercent}% 目标）`);
  } else {
    factors.push('当前考点需先掌握前置先修考点');
  }

  // 事实 2: 掌握度现状与目标差距
  if (currentMasteryPercent >= targetMasteryPercent) {
    factors.push(`当前掌握度 ${currentMasteryPercent}%，已达到 ${targetMasteryPercent}% 掌握目标`);
  } else {
    const gap = targetMasteryPercent - currentMasteryPercent;
    factors.push(`当前掌握度 ${currentMasteryPercent}%，距离目标 ${targetMasteryPercent}% 仍有 ${gap}% 差距`);
  }

  // 事实 3: 学习路径规划位置与章节归属
  factors.push(`属于当前推荐学习主线（第 ${step.stage} 阶段 · ${step.chapter}）`);

  // 事实 4: 优先级与阶段目标
  if (step.priority) {
    factors.push(`路径推荐优先级：${step.priority}${step.priority_score ? `（综合评估分 ${step.priority_score.toFixed(0)}）` : ''}`);
  }
  if (step.learning_goal) {
    factors.push(`阶段学习目标：${step.learning_goal}`);
  }

  return {
    title: '为什么推荐？',
    reason: step.reason || '该考点处于当前学习路径的关键位置，且掌握度尚未达到目标。',
    priority,
    factors,
  };
}

// ============================================================
// 二、学习进展解释模型 (Learning Progression Explanation)
// ============================================================

export interface LearningProgressionExplanation {
  resultType: 'PROGRESS' | 'RETAIN' | 'REGRESS';

  beforePercentStr: string;
  afterPercentStr: string;
  deltaPercentStr: string;
  deltaValue: number;

  isMasteryTargetReached: boolean;

  stageChange: {
    before: MasteryLevel;
    after: MasteryLevel;
    badgeText: string;
    message: string;
  };

  pathChange: {
    title: string;
    detail: string;
    unlockedNodes: string[];
    hasUnlocked: boolean;
  };

  nextAction: NextLearningAction;
}

/**
 * 统一将作答结果、掌握度跃迁与重规划决策转换为可解释的学习反馈
 */
export function getLearningProgressionExplanation(params: {
  beforeMastery: number | string;
  afterMastery: number | string;
  replanning?: DecisionAuditEnvelope | null;
  currentKnowledgeId: string;
  currentKnowledgeName?: string;
}): LearningProgressionExplanation {
  const { beforeMastery, afterMastery, replanning, currentKnowledgeId, currentKnowledgeName } = params;

  // 1. 规范化掌握度数值 (0~1 小数)
  const rawBefore = parseMasteryFraction(beforeMastery);
  const rawAfter = parseMasteryFraction(afterMastery);

  // 计算增量 (四位定点精度)
  const rawDelta = Number((rawAfter - rawBefore).toFixed(4));
  const deltaValue = rawDelta;

  const beforePercentStr = `${(rawBefore * 100).toFixed(2)}%`;
  const afterPercentStr = `${(rawAfter * 100).toFixed(2)}%`;
  const deltaSign = rawDelta > 0 ? '+' : '';
  const deltaPercentStr = `${deltaSign}${(rawDelta * 100).toFixed(2)}%`;

  // 2. 判定结果类型 (PROGRESS | RETAIN | REGRESS)
  let resultType: 'PROGRESS' | 'RETAIN' | 'REGRESS' = 'RETAIN';
  if (rawDelta > 0.00005) {
    resultType = 'PROGRESS';
  } else if (rawDelta < -0.00005) {
    resultType = 'REGRESS';
  } else {
    resultType = 'RETAIN';
  }

  // 3. 掌握度目标判定
  const isMasteryTargetReached = isMasteryGoalReached(rawAfter);

  // 4. 认知阶段与文案判定
  const beforeLevel = getMasteryLevel(rawBefore * 100);
  const afterLevel = getMasteryLevel(rawAfter * 100);

  let stageBadgeText = '本次练习已记录';
  let stageMessage = '继续练习以提升掌握度。';

  if (resultType === 'REGRESS') {
    stageBadgeText = '⚠️ 掌握度有所回退';
    stageMessage = '掌握度出现回退，建议针对错题重点复习巩固。';
  } else if (resultType === 'RETAIN') {
    stageBadgeText = '📚 巩固中';
    stageMessage = '本次练习已记录。当前掌握度仍需继续巩固，建议继续练习该考点。';
  } else if (afterLevel === 'MASTERED') {
    stageBadgeText = '🎉 已达到掌握目标';
    stageMessage = beforeLevel === 'WEAK'
      ? `重大突破！该考点掌握度跨越达成 ${MASTERY_TARGET_PERCENT}% 目标。`
      : `恭喜！该考点已成功达成 ${MASTERY_TARGET_PERCENT}% 掌握度目标。`;
  } else if (beforeLevel === 'WEAK' && afterLevel === 'DEVELOPING') {
    stageBadgeText = '📈 正在进入发展阶段';
    stageMessage = '掌握度稳步提升，已脱离薄弱阶段！';
  } else {
    stageBadgeText = '📈 练习有进步';
    stageMessage = '掌握度有所提升，继续保持！';
  }

  // 5. 路径解锁与重规划解释 (严格防御虚假解锁)
  const unlocked = getUnlockedDownstreamNodes(replanning, currentKnowledgeId);
  const isUnlockAction = replanning?.canonical_payload?.action === 'UNLOCK_DOWNSTREAM';
  const hasUnlocked = isUnlockAction && unlocked.length > 0;

  let pathTitle = '📚 考点继续巩固';
  let pathDetail = '当前考点掌握度保持当前阶段，建议继续练习以满足前置要求。';

  if (hasUnlocked) {
    pathTitle = '🎉 掌握度达标！新考点已解锁';
    pathDetail = `当前考点已达到掌握目标，已满足前置要求，成功解锁：${unlocked.join('、')}。下一步可以继续学习 ${unlocked[0]}。`;
  } else if (isMasteryTargetReached) {
    pathTitle = '🎉 已达到掌握目标';
    pathDetail = '当前考点已达到掌握目标，认知网络评估已达标。';
  }

  // 6. 下一步行动统一决策 (复用既有 getNextLearningAction)
  const nextAction = getNextLearningAction({
    currentKnowledgeId,
    currentKnowledgeName,
    replanning,
    afterMastery: rawAfter,
  });

  return {
    resultType,
    beforePercentStr,
    afterPercentStr,
    deltaPercentStr,
    deltaValue,
    isMasteryTargetReached,
    stageChange: {
      before: beforeLevel,
      after: afterLevel,
      badgeText: stageBadgeText,
      message: stageMessage,
    },
    pathChange: {
      title: pathTitle,
      detail: pathDetail,
      unlockedNodes: hasUnlocked ? unlocked : [],
      hasUnlocked,
    },
    nextAction,
  };
}
