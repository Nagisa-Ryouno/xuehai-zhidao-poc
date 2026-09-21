import React from 'react';
import { TrendingUp, Award, CheckCircle, Target, ArrowRight } from 'lucide-react';
import type { StudentProgressResponse } from '../../types';

export interface RecentProgressCardProps {
  progress: StudentProgressResponse | null;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onViewProfile: () => void;
}

export const RecentProgressCard: React.FC<RecentProgressCardProps> = ({
  progress,
  loading = false,
  error = null,
  onRetry,
  onViewProfile,
}) => {
  // 1. Loading 骨架态
  if (loading) {
    return (
      <div
        data-testid="recent-progress-card"
        className="min-h-[140px] rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-xs animate-pulse flex flex-col justify-between space-y-4"
      >
        <div className="flex items-center gap-2">
          <div className="h-5 w-24 bg-slate-200 rounded-full" />
          <div className="h-5 w-32 bg-slate-200 rounded-full" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 bg-slate-100 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  // 2. Error 容错态
  if (error) {
    return (
      <div
        data-testid="recent-progress-card"
        className="min-h-[120px] rounded-2xl border border-rose-200 bg-rose-50/50 p-5 sm:p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
      >
        <div className="space-y-1">
          <h3 className="text-base font-bold text-rose-900">
            暂时无法加载最近学习进展
          </h3>
          <p className="text-xs sm:text-sm text-rose-700">
            {error || '网络或数据加载异常，请尝试重新加载。'}
          </p>
        </div>
        {onRetry && (
          <button
            type="button"
            data-testid="recent-progress-retry-btn"
            onClick={onRetry}
            className="px-4 py-2 rounded-xl text-xs sm:text-sm font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-xs transition-colors cursor-pointer shrink-0"
          >
            重新加载
          </button>
        )}
      </div>
    );
  }

  // 3. 无数据兜底（空状态）
  if (!progress) {
    return null;
  }

  const overallMasteryPct = Math.round((progress.overall_mastery || 0) * 100);
  const rawAcc = progress.overall_accuracy || 0;
  const accuracyPct = rawAcc > 1 ? Math.round(rawAcc) : Math.round(rawAcc * 100);
  const masteredCount = progress.mastered_count || 0;
  const practiceCount = progress.total_practice_count || 0;

  const statItems = [
    {
      label: '整体掌握度',
      value: `${overallMasteryPct}%`,
      icon: TrendingUp,
      color: 'text-indigo-600 bg-indigo-50 border-indigo-100',
    },
    {
      label: '已掌握考点',
      value: `${masteredCount} 个`,
      icon: Award,
      color: 'text-emerald-600 bg-emerald-50 border-emerald-100',
    },
    {
      label: '练习正确率',
      value: `${accuracyPct}%`,
      icon: CheckCircle,
      color: 'text-blue-600 bg-blue-50 border-blue-100',
    },
    {
      label: '累计练习题数',
      value: `${practiceCount} 题`,
      icon: Target,
      color: 'text-purple-600 bg-purple-50 border-purple-100',
    },
  ];

  return (
    <div
      data-testid="recent-progress-card"
      className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-xs space-y-4 max-w-full"
    >
      {/* 头部标题与学情链接 */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100">
            <TrendingUp className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">最近进展</h3>
          <span className="text-xs text-slate-400">|</span>
          <span className="text-xs text-slate-500">阶段学情沉淀</span>
        </div>

        <button
          type="button"
          data-testid="recent-progress-link"
          onClick={onViewProfile}
          className="inline-flex items-center gap-1 px-2.5 py-1.5 min-h-[44px] rounded-lg text-xs font-bold text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50/60 transition-colors cursor-pointer"
        >
          <span>查看完整学情档案</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 4 项真实指标网格 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {statItems.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div
              key={idx}
              className="p-3 rounded-xl bg-slate-50/70 border border-slate-100 flex items-center gap-2.5"
            >
              <div className={`p-2 rounded-lg border shrink-0 ${item.color}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <span className="text-[11px] font-medium text-slate-500 block truncate">
                  {item.label}
                </span>
                <span className="text-sm sm:text-base font-extrabold text-slate-900 tracking-tight block">
                  {item.value}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
