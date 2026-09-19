import React from 'react';
import {
  BookOpen,
  FileText,
  CheckCircle,
  Video,
  Lightbulb,
  Clock,
  Flame,
  Bot,
  ArrowRight,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import type { LearningResource, ResourceType } from '../../types';

interface ResourceCardProps {
  resource: LearningResource;
  recommendedReason?: string;
  suggestedOrder?: number;
  onOpenResource: (resource: LearningResource) => void;
  onAskAI?: (resource: LearningResource) => void;
}

const TYPE_CONFIG: Record<
  ResourceType,
  {
    label: string;
    badgeBg: string;
    badgeText: string;
    borderAccent: string;
    actionLabel: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  CONCEPT_CARD: {
    label: '考点微卡',
    badgeBg: 'bg-indigo-50',
    badgeText: 'text-indigo-700',
    borderAccent: 'border-indigo-100 hover:border-indigo-300',
    actionLabel: '查看微卡',
    icon: BookOpen,
  },
  EXAMPLE: {
    label: '典型例题',
    badgeBg: 'bg-amber-50',
    badgeText: 'text-amber-700',
    borderAccent: 'border-amber-100 hover:border-amber-300',
    actionLabel: '研读例题',
    icon: Lightbulb,
  },
  PRACTICE: {
    label: '靶向微练',
    badgeBg: 'bg-emerald-50',
    badgeText: 'text-emerald-700',
    borderAccent: 'border-emerald-100 hover:border-emerald-300',
    actionLabel: '开始微练',
    icon: CheckCircle,
  },
  DOCUMENT: {
    label: '精讲讲义',
    badgeBg: 'bg-blue-50',
    badgeText: 'text-blue-700',
    borderAccent: 'border-blue-100 hover:border-blue-300',
    actionLabel: '精读讲义',
    icon: FileText,
  },
  VIDEO: {
    label: '导学视频',
    badgeBg: 'bg-purple-50',
    badgeText: 'text-purple-700',
    borderAccent: 'border-purple-100 hover:border-purple-300',
    actionLabel: '观看导学',
    icon: Video,
  },
};

export const ResourceCard: React.FC<ResourceCardProps> = ({
  resource,
  recommendedReason,
  suggestedOrder,
  onOpenResource,
  onAskAI,
}) => {
  const config = TYPE_CONFIG[resource.resource_type] || TYPE_CONFIG.CONCEPT_CARD;
  const IconComponent = config.icon;
  const isMooc = resource.is_external && resource.source === 'china_mooc';
  const borderClass = isMooc ? 'border-blue-200 hover:border-blue-400' : config.borderAccent;

  return (
    <div
      className={`relative flex flex-col justify-between bg-white rounded-2xl border p-5 transition-all duration-200 hover:shadow-md ${borderClass}`}
    >
      <div>
        {/* 顶部标签栏 */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex flex-wrap items-center gap-2">
            {isMooc ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200/80">
                <ExternalLink className="w-3.5 h-3.5" />
                <span>中国大学MOOC</span>
              </span>
            ) : (
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold ${config.badgeBg} ${config.badgeText}`}
              >
                <IconComponent className="w-3.5 h-3.5" />
                <span>{config.label}</span>
              </span>
            )}
            {suggestedOrder && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600">
                步骤 {suggestedOrder}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-600">
            <span className="inline-flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              <span>{resource.estimated_minutes} 分钟</span>
            </span>
            <span className="inline-flex items-center gap-1">
              <Flame className="w-3.5 h-3.5 text-amber-500" />
              <span>难度 {resource.difficulty.toFixed(1)}</span>
            </span>
          </div>
        </div>

        {/* 标题 */}
        <h4 className="text-base font-bold text-slate-900 line-clamp-1 mb-1">
          {resource.title}
        </h4>

        {/* MOOC 院校及主讲教师信息 */}
        {isMooc && (resource.metadata?.university || resource.metadata?.instructor) && (
          <div className="flex flex-wrap items-center gap-1.5 mb-2 text-xs">
            {resource.metadata.university && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium">
                {resource.metadata.university}
              </span>
            )}
            {resource.metadata.instructor && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">
                {resource.metadata.instructor}
              </span>
            )}
          </div>
        )}

        {/* 描述 */}
        <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed mb-3">
          {resource.description}
        </p>

        {/* 自适应推荐理由（若有） */}
        {recommendedReason && (
          <div className="mb-4 rounded-xl bg-amber-500/10 border border-amber-200/60 p-2.5 flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <p className="text-xs text-amber-900 leading-snug font-medium">
              {recommendedReason}
            </p>
          </div>
        )}

        {/* 摘要速记（若有） */}
        {resource.summary && !recommendedReason && (
          <div className="mb-4 rounded-xl bg-slate-50 border border-slate-100 p-2.5 text-xs text-slate-600 line-clamp-2 font-mono leading-relaxed">
            {resource.summary}
          </div>
        )}
      </div>

      {/* 底部操作区 */}
      <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
        {onAskAI && (
          <button
            type="button"
            onClick={() => onAskAI(resource)}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-indigo-600 hover:bg-indigo-50/60 transition-colors cursor-pointer"
            title="向 AI 伴学提问此资源"
          >
            <Bot className="w-4 h-4" />
            <span>问伴学</span>
          </button>
        )}

        <button
          type="button"
          onClick={() => onOpenResource(resource)}
          className={`flex-1 inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white transition-all duration-150 cursor-pointer shadow-xs ${
            isMooc
              ? 'bg-blue-600 hover:bg-blue-700'
              : resource.resource_type === 'PRACTICE'
              ? 'bg-emerald-600 hover:bg-emerald-700'
              : resource.resource_type === 'EXAMPLE'
              ? 'bg-amber-600 hover:bg-amber-700'
              : 'bg-indigo-600 hover:bg-indigo-700'
          }`}
        >
          <span>{isMooc ? '前往慕课学习' : config.actionLabel}</span>
          {isMooc ? (
            <ExternalLink className="w-3.5 h-3.5" />
          ) : (
            <ArrowRight className="w-3.5 h-3.5" />
          )}
        </button>
      </div>
    </div>
  );
};
