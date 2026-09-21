import React from 'react';
import {
  Sparkles,
  RotateCcw,
  BookOpen,
  ArrowRight,
  TrendingUp,
  Target,
  Zap,
} from 'lucide-react';
import type { TodayLearningAction, TodayActionType } from '../../types';

export interface TodayActionCardProps {
  action: TodayLearningAction | null;
  loading?: boolean;
  error?: string | null;
  currentMasteryPercent?: number | null;
  onExecuteCTA: (action: TodayLearningAction) => void;
  onRetry?: () => void;
}

const ACTION_TYPE_CONFIG: Record<
  TodayActionType,
  {
    badgeLabel: string;
    badgeClass: string;
    icon: React.ComponentType<{ className?: string }>;
    accentBorder: string;
    accentBg: string;
  }
> = {
  REVIEW_RETENTION: {
    badgeLabel: '复习提醒',
    badgeClass: 'bg-amber-100 text-amber-800 border-amber-200',
    icon: RotateCcw,
    accentBorder: 'border-amber-200 hover:border-amber-300',
    accentBg: 'from-amber-50/70 via-orange-50/40 to-amber-50/20',
  },
  CONTINUE_LEARNING: {
    badgeLabel: '继续学习',
    badgeClass: 'bg-blue-100 text-blue-800 border-blue-200',
    icon: BookOpen,
    accentBorder: 'border-blue-200 hover:border-blue-300',
    accentBg: 'from-blue-50/70 via-indigo-50/40 to-sky-50/20',
  },
  PRACTICE: {
    badgeLabel: '推荐练习',
    badgeClass: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    icon: Zap,
    accentBorder: 'border-emerald-200 hover:border-emerald-300',
    accentBg: 'from-emerald-50/70 via-teal-50/40 to-green-50/20',
  },
  VIEW_PROGRESS: {
    badgeLabel: '学情进展',
    badgeClass: 'bg-purple-100 text-purple-800 border-purple-200',
    icon: TrendingUp,
    accentBorder: 'border-purple-200 hover:border-purple-300',
    accentBg: 'from-purple-50/70 via-fuchsia-50/40 to-pink-50/20',
  },
  NONE: {
    badgeLabel: '',
    badgeClass: '',
    icon: Target,
    accentBorder: 'border-slate-200',
    accentBg: 'from-slate-50 to-white',
  },
};

export const TodayActionCard: React.FC<TodayActionCardProps> = ({
  action,
  loading = false,
  error = null,
  currentMasteryPercent = null,
  onExecuteCTA,
  onRetry,
}) => {
  // 1. Loading 骨架态：防布局跳动，维持最小高度与结构占位
  if (loading) {
    return (
      <div
        data-testid="today-action-card"
        className="min-h-[160px] rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-xs animate-pulse flex flex-col justify-between space-y-4"
      >
        <div className="flex items-center gap-2">
          <div className="h-5 w-20 bg-slate-200 rounded-full" />
          <div className="h-5 w-24 bg-slate-200 rounded-full" />
        </div>
        <div className="space-y-2">
          <div className="h-6 w-3/5 bg-slate-200 rounded-lg" />
          <div className="h-4 w-4/5 bg-slate-200 rounded-lg" />
        </div>
        <div className="h-10 w-32 bg-slate-200 rounded-xl self-end" />
      </div>
    );
  }

  // 2. Error 容错态：人本提示与独立重试能力
  if (error) {
    return (
      <div
        data-testid="today-action-card"
        className="min-h-[140px] rounded-2xl border border-rose-200 bg-rose-50/50 p-5 sm:p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
      >
        <div className="space-y-1">
          <h3 className="text-base font-bold text-rose-900">
            暂时无法获取今日学习安排
          </h3>
          <p className="text-xs sm:text-sm text-rose-700">
            {error || '网络或数据加载异常，请尝试重新加载。'}
          </p>
        </div>
        {onRetry && (
          <button
            type="button"
            data-testid="today-action-retry-btn"
            onClick={onRetry}
            className="px-4 py-2 rounded-xl text-xs sm:text-sm font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-xs transition-colors cursor-pointer shrink-0"
          >
            重新加载
          </button>
        )}
      </div>
    );
  }

  // 3. Empty 空状态 (NONE)：真诚提示阶段完成，不伪造假任务
  if (!action || action.action_type === 'NONE') {
    return (
      <div
        data-testid="today-action-card"
        className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
      >
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
              <Sparkles className="w-3.5 h-3.5 text-slate-500" />
              今日学习
            </span>
          </div>
          <h3 className="text-base sm:text-lg font-bold text-slate-900">
            今天暂时没有待完成的学习任务
          </h3>
          <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
            当前阶段学习任务已全部达成，可随时查看学情或探索新知识。
          </p>
        </div>
        <button
          type="button"
          data-testid="today-action-cta-btn"
          onClick={() =>
            onExecuteCTA({
              action_type: 'VIEW_PROGRESS',
              title: '看看最近的学习进展',
              description: '查看学情进展',
              cta_label: '查看学习进展',
              priority_reason: action?.priority_reason || '当前阶段学习任务已全部达成',
            })
          }
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors cursor-pointer shrink-0"
        >
          <span>查看学习进展</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    );
  }

  // 4. 正常展示态
  const config = ACTION_TYPE_CONFIG[action.action_type] || ACTION_TYPE_CONFIG.NONE;
  const ActionIcon = config.icon;

  return (
    <div
      data-testid="today-action-card"
      className={`relative overflow-hidden rounded-2xl border bg-gradient-to-br ${config.accentBg} ${config.accentBorder} p-5 sm:p-6 shadow-xs transition-all duration-200 hover:shadow-sm max-w-full`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* 左侧内容区 */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* 标签栏 */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-600 text-white shadow-2xs">
              <Sparkles className="w-3.5 h-3.5 text-blue-200" />
              今日学习 · 建议首选完成
            </span>

            {config.badgeLabel && (
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.badgeClass}`}
              >
                <ActionIcon className="w-3 h-3" />
                {config.badgeLabel}
              </span>
            )}

            {action.knowledge_name && (
              <span className="text-xs text-slate-600 font-semibold truncate max-w-[220px]">
                {action.knowledge_name}
              </span>
            )}

            {currentMasteryPercent !== null && currentMasteryPercent !== undefined && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-indigo-100/80 text-indigo-800 border border-indigo-200/80">
                当前掌握度 {Math.round(currentMasteryPercent)}%
              </span>
            )}
          </div>

          {/* 标题 */}
          <h3 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight leading-snug break-words">
            {action.title}
          </h3>

          {/* 人本描述文案 */}
          <p className="text-sm text-slate-600 leading-relaxed break-words">
            {action.description}
          </p>

          {/* 优先级理由（人本无黑话） */}
          {action.priority_reason && (
            <div className="pt-1 flex items-center gap-1.5 text-xs text-slate-500 font-medium break-words">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-400 shrink-0" />
              <span>{action.priority_reason}</span>
            </div>
          )}
        </div>

        {/* 右侧 CTA 按钮 */}
        <div className="sm:self-center shrink-0 pt-2 sm:pt-0">
          <button
            type="button"
            data-testid="today-action-cta-btn"
            disabled={loading}
            onClick={() => onExecuteCTA(action)}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 min-h-[48px] rounded-xl font-bold text-sm text-white bg-blue-600 hover:bg-blue-700 active:scale-[0.98] transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <span>{action.cta_label || '开始学习'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
