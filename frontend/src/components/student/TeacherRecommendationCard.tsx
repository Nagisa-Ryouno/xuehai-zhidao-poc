import React from 'react';
import {
  GraduationCap,
  BookOpen,
  RotateCcw,
  ArrowRight,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import type { StudentRecommendationItem } from '../../types';

export interface TeacherRecommendationCardProps {
  recommendations?: StudentRecommendationItem[];
  loading?: boolean;
  error?: string | null;
  onViewConceptCard: (knowledgeId: string, knowledgeName: string) => void;
  onStartQuiz: (knowledgeId: string, knowledgeName: string) => void;
  onRetry?: () => void;
}

const ACTION_CONFIG = {
  REVIEW_CONCEPT: {
    badgeText: '建议复习该考点',
    ctaText: '去复习',
    icon: BookOpen,
    badgeClass: 'bg-amber-50 text-amber-800 border-amber-200/80',
    btnClass:
      'bg-amber-50 hover:bg-amber-100/80 text-amber-900 border border-amber-200/80 shadow-2xs',
  },
  RETRY_PRACTICE: {
    badgeText: '建议重新练习',
    ctaText: '去练习',
    icon: RotateCcw,
    badgeClass: 'bg-blue-50 text-blue-800 border-blue-200/80',
    btnClass:
      'bg-blue-50 hover:bg-blue-100/80 text-blue-900 border border-blue-200/80 shadow-2xs',
  },
} as const;

function formatRelativeTime(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return '';
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffHours < 1) return '刚刚';
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays === 1) return '昨天';
    if (diffDays < 7) return `${diffDays}天前`;
    return `${d.getMonth() + 1}月${d.getDate()}日`;
  } catch {
    return '';
  }
}

export const TeacherRecommendationCard: React.FC<TeacherRecommendationCardProps> = ({
  recommendations = [],
  loading = false,
  error = null,
  onViewConceptCard,
  onStartQuiz,
  onRetry,
}) => {
  // 1. Loading 状态：轻量骨架屏
  if (loading) {
    return (
      <div
        data-testid="teacher-recommendation-card"
        className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5 shadow-2xs animate-pulse space-y-3"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-slate-200 rounded-md" />
            <div className="h-5 w-20 bg-slate-200 rounded-md" />
          </div>
          <div className="h-4 w-32 bg-slate-100 rounded-md" />
        </div>
        <div className="space-y-2 pt-1">
          <div className="h-14 bg-slate-100 rounded-xl" />
          <div className="h-14 bg-slate-100 rounded-xl" />
        </div>
      </div>
    );
  }

  // 2. Error 状态：容错提示与轻量重试入口，绝不崩溃
  if (error) {
    return (
      <div
        data-testid="teacher-recommendation-card"
        className="rounded-2xl border border-amber-200/70 bg-amber-50/40 p-4 shadow-2xs flex items-center justify-between gap-3"
      >
        <div className="flex items-center gap-2 min-w-0">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
          <span className="text-xs sm:text-sm text-amber-900 font-medium truncate">
            {error || '暂时无法加载老师建议'}
          </span>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white text-amber-800 border border-amber-300 hover:bg-amber-50 shadow-2xs cursor-pointer shrink-0 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            重试
          </button>
        )}
      </div>
    );
  }

  // 3. Empty 状态：轻量不抢焦点的单行提示，不霸占首页核心空间
  if (!recommendations || recommendations.length === 0) {
    return (
      <div
        data-testid="teacher-recommendation-card"
        className="rounded-2xl border border-slate-200/70 bg-white/70 px-4 sm:px-5 py-3 shadow-2xs flex items-center justify-between"
      >
        <div className="flex items-center gap-2 text-xs sm:text-sm text-slate-500">
          <GraduationCap className="w-4 h-4 text-slate-400 shrink-0" />
          <span className="font-semibold text-slate-700">老师建议</span>
          <span className="text-slate-300">·</span>
          <span>暂无老师建议</span>
        </div>
        <span className="text-xs text-slate-400 hidden sm:inline">
          来自任课教师的学习建议
        </span>
      </div>
    );
  }

  // 4. 有建议状态：最多展示 3 条，严格按 created_at 排序
  const displayItems = [...recommendations]
    .filter((r) => r.action_type === 'REVIEW_CONCEPT' || r.action_type === 'RETRY_PRACTICE')
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 3);

  return (
    <div
      data-testid="teacher-recommendation-card"
      className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5 shadow-2xs space-y-3"
    >
      {/* 区域标题 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center">
            <GraduationCap className="w-4 h-4 text-indigo-600" />
          </div>
          <h2 className="text-base font-bold text-slate-900 tracking-tight">老师建议</h2>
        </div>
        <span className="text-xs text-slate-400 font-normal">来自任课教师的学习建议</span>
      </div>

      {/* 建议列表 */}
      <div className="space-y-2.5">
        {displayItems.map((item) => {
          const config = ACTION_CONFIG[item.action_type];
          const ActionIcon = config.icon;
          const displayKnowledgeName = item.knowledge_name || item.knowledge_id;
          const timeText = formatRelativeTime(item.created_at);

          const handleActionClick = () => {
            if (item.action_type === 'REVIEW_CONCEPT') {
              onViewConceptCard(item.knowledge_id, displayKnowledgeName);
            } else if (item.action_type === 'RETRY_PRACTICE') {
              onStartQuiz(item.knowledge_id, displayKnowledgeName);
            }
          };

          return (
            <div
              key={item.action_id}
              data-testid="teacher-recommendation-item"
              className="group flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 sm:p-3.5 rounded-xl border border-slate-100 hover:border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-all"
            >
              {/* 考点与建议信息 */}
              <div className="space-y-1.5 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-slate-800 group-hover:text-indigo-600 transition-colors">
                    {displayKnowledgeName}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${config.badgeClass}`}
                  >
                    <ActionIcon className="w-3 h-3" />
                    {config.badgeText}
                  </span>
                </div>
                {timeText && (
                  <div className="text-xs text-slate-400 font-normal">
                    {timeText}
                  </div>
                )}
              </div>

              {/* 行动 CTA 按钮：直接接入已有学习流程 */}
              <button
                type="button"
                onClick={handleActionClick}
                className={`inline-flex items-center justify-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold cursor-pointer shrink-0 transition-all ${config.btnClass}`}
              >
                <span>{config.ctaText}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
