/**
 * pathStatePresentation.ts
 * 学海智导 (Xuehai Zhidao) V2 - Phase 2.2-B / Sprint 3
 * 学生端路径状态视觉与行为语义统一规范 (Unified PathState Presentation Specification)
 *
 * 规范原则：
 * 1. 严格四态收敛：LOCKED, AVAILABLE, IN_PROGRESS, COMPLETED
 * 2. 状态表达双重指示：语义文本 + 符号图标 + 颜色搭配，绝不单纯依赖颜色
 * 3. 行为语义规范：
 *    - LOCKED -> DISABLED (禁用测验，清晰展示前置阻塞)
 *    - AVAILABLE -> START_QUIZ (开始微测验)
 *    - IN_PROGRESS -> CONTINUE_QUIZ (继续挑战微测验，最高视觉优先级)
 *    - COMPLETED -> REVIEW_QUIZ (复习微测验)
 */

import type { PathState } from '../../types.ts';

export type PathStateActionType =
  | 'DISABLED'
  | 'START_QUIZ'
  | 'CONTINUE_QUIZ'
  | 'REVIEW_QUIZ';

export interface PathStatePresentation {
  state: PathState;
  badgeText: string;
  badgeClass: string;
  buttonText: string;
  buttonClass: string;
  disabled: boolean;
  ariaLabel: string;
  iconName: 'Lock' | 'Sparkles' | 'Target' | 'CheckCircle2';
  actionType: PathStateActionType;
  description: string;
}

const PATH_STATE_CONFIGS: Record<PathState, PathStatePresentation> = {
  LOCKED: {
    state: 'LOCKED',
    badgeText: '🔒 需先掌握前置',
    badgeClass: 'bg-slate-100 text-slate-600 border-slate-300',
    buttonText: '需先掌握前置',
    buttonClass: 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed opacity-70',
    disabled: true,
    ariaLabel: '前置条件未满足，暂未开放学习',
    iconName: 'Lock',
    actionType: 'DISABLED',
    description: '前置考点尚未满足掌握标准，需先攻坚前置依赖考点',
  },
  AVAILABLE: {
    state: 'AVAILABLE',
    badgeText: '🔓 已满足学习条件',
    badgeClass: 'bg-sky-50 text-sky-700 border-sky-200',
    buttonText: '开始微测验',
    buttonClass: 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs cursor-pointer',
    disabled: false,
    ariaLabel: '已满足前置学习条件，点击开始微测验',
    iconName: 'Sparkles',
    actionType: 'START_QUIZ',
    description: '已满足全部前置先修条件，可以开始微测验攻坚',
  },
  IN_PROGRESS: {
    state: 'IN_PROGRESS',
    badgeText: '🎯 正在进行',
    badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200 ring-2 ring-indigo-400/30',
    buttonText: '继续挑战微测验',
    buttonClass: 'bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white shadow-sm cursor-pointer ring-2 ring-indigo-400/40',
    disabled: false,
    ariaLabel: '当前进行中主线任务，点击继续挑战微测验',
    iconName: 'Target',
    actionType: 'CONTINUE_QUIZ',
    description: '当前正在攻坚的核心任务，具有最高学习优先级',
  },
  COMPLETED: {
    state: 'COMPLETED',
    badgeText: '✓ 已掌握',
    badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    buttonText: '复习微测验',
    buttonClass: 'bg-white hover:bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-2xs cursor-pointer',
    disabled: false,
    ariaLabel: '该考点已达标掌握，点击进入复习微测验',
    iconName: 'CheckCircle2',
    actionType: 'REVIEW_QUIZ',
    description: '认知掌握度已达到 80% 目标阈值，考点已达标掌握',
  },
};

/**
 * 获取统一规范的 PathState 展示与操作契约配置
 */
export function getPathStatePresentation(state: PathState): PathStatePresentation {
  return PATH_STATE_CONFIGS[state] || PATH_STATE_CONFIGS.LOCKED;
}
