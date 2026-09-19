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
  onExecuteCTA: (action: TodayLearningAction) => void;
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
    accentBorder: '',
    accentBg: '',
  },
};

export const TodayActionCard: React.FC<TodayActionCardProps> = ({
  action,
  loading = false,
  onExecuteCTA,
}) => {
  // 当行动类型为 NONE 或空时，遵循静默原则，不渲染任何卡片
  if (!action || action.action_type === 'NONE') {
    return null;
  }

  const config = ACTION_TYPE_CONFIG[action.action_type] || ACTION_TYPE_CONFIG.NONE;
  const ActionIcon = config.icon;

  return (
    <div
      data-testid="today-action-card"
      className={`relative overflow-hidden rounded-2xl border bg-gradient-to-br ${config.accentBg} ${config.accentBorder} p-5 sm:p-6 shadow-sm transition-all duration-200 hover:shadow-md max-w-full`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* 左侧内容区 */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* 标签栏 */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-600 text-white shadow-xs">
              <Sparkles className="w-3.5 h-3.5 text-blue-200" />
              今日学习
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
              <span className="text-xs text-slate-500 font-medium truncate max-w-[200px]">
                {action.knowledge_name}
              </span>
            )}
          </div>

          {/* 标题 */}
          <h3 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight leading-snug">
            {action.title}
          </h3>

          {/* 人本描述文案 */}
          <p className="text-sm text-slate-600 leading-relaxed break-words">
            {action.description}
          </p>

          {/* 优先级理由（纯人本无黑话） */}
          {action.priority_reason && (
            <div className="pt-1 flex items-center gap-1.5 text-xs text-slate-500 font-medium">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-400" />
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
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm text-white bg-blue-600 hover:bg-blue-700 active:scale-[0.98] transition-all shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <span>{action.cta_label || '开始学习'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
