import React, { useState } from 'react';
import {
  Target,
  Sparkles,
  Flame,
  CheckCircle2,
  Lock,
  ArrowRight,
  PlayCircle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Bot,
} from 'lucide-react';
import type { CurrentFocusResult } from './taskFocusModel.ts';
import { getPathStatePresentation } from './pathStatePresentation.ts';
import {
  getRecommendationExplanation,
  MASTERY_TARGET_PERCENT,
} from './adaptiveLearningModel.ts';
import type { DynamicLearningRoute } from '../../types';
import { RingProgress } from '../decor/RingProgress';

interface CurrentFocusCardProps {
  focusResult: CurrentFocusResult;
  dynamicRoute?: DynamicLearningRoute | null;
  onStartQuiz: (knowledgeId: string, knowledgeName: string) => void;
  onViewConceptCard?: (knowledgeId: string, knowledgeName: string) => void;
  onAskAI?: (knowledgeId: string, knowledgeName: string) => void;
  onViewGraph?: () => void;
  onViewResources?: (knowledgeId: string) => void;
}

export const CurrentFocusCard: React.FC<CurrentFocusCardProps> = ({
  focusResult,
  dynamicRoute,
  onStartQuiz,
  onViewConceptCard,
  onAskAI,
  onViewGraph,
  onViewResources,
}) => {
  const [isExplanationOpen, setIsExplanationOpen] = useState(false);

  // 1. 全部已完成状态
  if (focusResult.status === 'ALL_COMPLETED') {
    return (
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-500/10 via-white to-teal-500/10 border border-emerald-200 p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-emerald-100 text-emerald-700">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider">
                阶段通关达成
              </span>
              <h3 className="text-lg sm:text-xl font-bold text-slate-900 mt-0.5">
                🎉 太棒了！当前学习路径考点均已达标掌握
              </h3>
              <p className="text-xs sm:text-sm text-slate-600 mt-1">
                所有推荐考点掌握度均已达到 {MASTERY_TARGET_PERCENT}% 以上。你可以前往知识图谱探索拓展考点，或随时复习巩固。
              </p>
            </div>
          </div>
          {onViewGraph && (
            <button
              type="button"
              onClick={onViewGraph}
              className="w-full sm:w-auto py-3 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs sm:text-sm shadow-xs flex items-center justify-center gap-2 transition-all cursor-pointer min-h-[44px] shrink-0"
            >
              <span>查看知识图谱</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    );
  }

  // 2. 全部锁定状态
  if (focusResult.status === 'ALL_LOCKED') {
    return (
      <div className="relative overflow-hidden rounded-2xl bg-amber-50/70 border border-amber-200 p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-amber-100 text-amber-700">
              <Lock className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xs font-bold text-amber-700 uppercase tracking-wider">
                前置条件待满足
              </span>
              <h3 className="text-lg sm:text-xl font-bold text-slate-900 mt-0.5">
                当前待学考点受阻于前置依赖
              </h3>
              <p className="text-xs sm:text-sm text-slate-600 mt-1">
                {focusResult.message || '请先前往知识图谱，点选并攻坚更基础的先修考点。'}
              </p>
            </div>
          </div>
          {onViewGraph && (
            <button
              type="button"
              onClick={onViewGraph}
              className="w-full sm:w-auto py-3 px-5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs sm:text-sm shadow-xs flex items-center justify-center gap-2 transition-all cursor-pointer min-h-[44px] shrink-0"
            >
              <span>前往知识图谱解锁</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    );
  }

  // 3. 空路径状态
  if (focusResult.status === 'EMPTY' || !focusResult.focus) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 text-center space-y-3 shadow-xs">
        <div className="w-12 h-12 mx-auto rounded-xl bg-slate-100 text-slate-400 flex items-center justify-center">
          <Sparkles className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-slate-800">
          🎉 当前没有需要立即攻坚的任务
        </h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          你的学习路径暂时没有新的可执行任务。
        </p>
      </div>
    );
  }

  const { focus } = focusResult;
  const presentation = getPathStatePresentation(focus.pathState);
  const isInProgress = focus.pathState === 'IN_PROGRESS';

  const explanation = getRecommendationExplanation({
    step: focus.step,
    pathState: focus.pathState,
    currentMasteryPercent: focus.currentMasteryPercent,
    targetMasteryPercent: focus.targetMasteryPercent ?? MASTERY_TARGET_PERCENT,
  });

  // 状态徽标与样式 (基于统一 PathStatePresentation 规范)
  const stateBadge = (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${presentation.badgeClass} ${
        isInProgress ? 'animate-pulse' : ''
      }`}
    >
      {focus.pathState === 'IN_PROGRESS' && <Target className="w-3.5 h-3.5 text-indigo-600" />}
      {focus.pathState === 'COMPLETED' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
      {focus.pathState === 'LOCKED' && <Lock className="w-3.5 h-3.5 text-slate-500" />}
      {focus.pathState === 'AVAILABLE' && <Sparkles className="w-3.5 h-3.5 text-sky-600" />}
      <span>{presentation.badgeText}</span>
    </span>
  );

  return (
    <div
      data-testid="current-focus-card"
      className="relative overflow-hidden rounded-3xl glass-card p-5 sm:p-7 transition-all hover:shadow-[0_18px_40px_rgba(214,150,105,.2)]"
    >
      {/* 顶部标签行 */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-600 text-white shadow-xs animate-float">
            <Flame className="w-4 h-4" />
          </div>
          <span className="text-xs font-extrabold uppercase tracking-wider text-indigo-700">
            今日核心重点任务
          </span>
          <span className="text-xs text-slate-400">|</span>
          <span className="text-xs font-medium text-slate-500">{focus.chapter}</span>
          {dynamicRoute && dynamicRoute.steps.length > 0 && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
              <span>🧭 动态自适应航线 (第 1 站 / 共 {dynamicRoute.route_length} 站)</span>
            </span>
          )}
        </div>
        <div>{stateBadge}</div>
      </div>

      {/* 考点标题与核心信息 */}
      <div className="py-4 space-y-4">
        <div>
          <div className="flex items-baseline gap-2.5">
            <span className="font-mono text-base sm:text-lg font-black text-indigo-600">
              {focus.knowledgeId}
            </span>
            <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
              {focus.knowledgeName}
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 mt-2 leading-relaxed max-w-3xl">
            {focus.reason}
          </p>
        </div>

        {/* 掌握度可视化进度对比 */}
        <div className="p-4 glass-card rounded-2xl space-y-2.5">
          {/* 掌握度可视化：环形指示器 + 进度对比 */}
          <div className="flex items-center gap-4">
            <RingProgress percent={focus.currentMasteryPercent} size={72} className="shrink-0" />
            <div className="flex-1 flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                <span>当前掌握度：</span>
                <strong className="font-mono font-black text-slate-900 text-sm">
                  {focus.currentMasteryPercent}%
                </strong>
              </span>
              <span className="font-semibold text-indigo-700 flex items-center gap-1">
                <span>目标掌握度：</span>
                <strong className="font-mono font-black text-indigo-600 text-sm">
                  {focus.targetMasteryPercent}%
                </strong>
              </span>
            </div>
          </div>

          {/* 进度条轨道 */}
          <div className="relative w-full h-3 bg-slate-100 rounded-full overflow-hidden">
            {/* 目标线 (80%) */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-indigo-400/80 z-10"
              style={{ left: `${focus.targetMasteryPercent}%` }}
              title={`掌握度目标线 (${focus.targetMasteryPercent}%)`}
            />
            {/* 当前掌握度进度条 */}
            <div
              className={`h-full rounded-full transition-all duration-1000 ${
                focus.currentMasteryPercent >= MASTERY_TARGET_PERCENT
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-500'
                  : 'progress-shimmer'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, focus.currentMasteryPercent))}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
            <span>0%</span>
            <span className="text-indigo-500 font-semibold">目标阈值 {MASTERY_TARGET_PERCENT}%</span>
            <span>100%</span>
          </div>
        </div>

        {/* 自适应推荐依据折叠面板 */}
        <div className="space-y-2">
          <button
            type="button"
            aria-expanded={isExplanationOpen}
            aria-controls="current-focus-explanation"
            onClick={() => setIsExplanationOpen((prev) => !prev)}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-700 hover:text-indigo-900 bg-indigo-50/90 hover:bg-indigo-100/90 border border-indigo-200/80 px-3.5 py-2 rounded-xl transition-all cursor-pointer min-h-[44px]"
          >
            <HelpCircle className="w-4 h-4 text-indigo-600" />
            <span>{explanation.title}</span>
            {isExplanationOpen ? (
              <ChevronUp className="w-4 h-4 ml-0.5 text-indigo-500" />
            ) : (
              <ChevronDown className="w-4 h-4 ml-0.5 text-indigo-500" />
            )}
          </button>

          {isExplanationOpen && (
            <div
              id="current-focus-explanation"
              role="region"
              aria-live="polite"
              className="p-4 rounded-2xl glass-card space-y-2.5 animate-screen-in"
            >
              <div className="text-xs text-slate-700 leading-relaxed font-medium">
                <strong className="text-indigo-950 font-bold">核心推荐依据：</strong>
                <span>{explanation.reason}</span>
              </div>
              <div className="pt-2 border-t border-slate-100 space-y-1.5">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  推导事实依据（Evidence-Based）：
                </span>
                <ul className="space-y-1.5 text-xs text-slate-600">
                  {explanation.factors.map((factor, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                      <span>{factor}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 底部行动按钮行 */}
      <div className="pt-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-t border-slate-100">
        <div className="text-xs text-slate-500 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span>完成该考点微测验，即可实时更新掌握度并自适应规划后续学习路线</span>
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          {onViewConceptCard && (
            <button
              type="button"
              onClick={() => onViewConceptCard(focus.knowledgeId, focus.knowledgeName)}
              className="flex-1 sm:flex-none py-3.5 px-4 rounded-xl font-bold text-xs sm:text-sm flex items-center justify-center gap-1.5 border border-indigo-200 bg-indigo-50/80 text-indigo-700 hover:bg-indigo-100 hover:text-indigo-900 transition-all cursor-pointer min-h-[44px]"
            >
              <BookOpen className="w-4 h-4 text-indigo-600" />
              <span>📖 考点精要速览</span>
            </button>
          )}

          {onViewResources && (
            <button
              type="button"
              onClick={() => onViewResources(focus.knowledgeId)}
              className="flex-1 sm:flex-none py-3.5 px-4 rounded-xl font-bold text-xs sm:text-sm flex items-center justify-center gap-1.5 border border-amber-200 bg-amber-50/80 text-amber-800 hover:bg-amber-100 hover:text-amber-950 transition-all cursor-pointer min-h-[44px]"
            >
              <Sparkles className="w-4 h-4 text-amber-600" />
              <span>📚 推荐学习材料</span>
            </button>
          )}

          {onAskAI && (
            <button
              type="button"
              onClick={() => onAskAI(focus.knowledgeId, focus.knowledgeName)}
              className="flex-1 sm:flex-none py-3.5 px-4 rounded-xl font-bold text-xs sm:text-sm flex items-center justify-center gap-1.5 border border-purple-200 bg-purple-50/80 text-purple-700 hover:bg-purple-100 hover:text-purple-900 transition-all cursor-pointer min-h-[44px]"
            >
              <Bot className="w-4 h-4 text-purple-600" />
              <span>🤖 问问 AI</span>
            </button>
          )}

          <button
            type="button"
            disabled={presentation.disabled}
            onClick={() => onStartQuiz(focus.knowledgeId, focus.knowledgeName)}
            aria-label={presentation.ariaLabel}
            className={`flex-1 sm:flex-none py-3.5 px-6 rounded-xl font-black text-sm flex items-center justify-center gap-2 shadow-sm transition-all min-h-[44px] ${presentation.buttonClass}`}
          >
            <PlayCircle className="w-4 h-4" />
            <span>{focus.actionLabel || presentation.buttonText}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
