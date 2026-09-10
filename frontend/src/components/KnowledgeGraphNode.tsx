import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Sparkles, AlertTriangle, CheckCircle, HelpCircle, Star, ArrowRight } from 'lucide-react';
import type { KnowledgeGraphNodeData } from '../types';

export const KnowledgeGraphNode: React.FC<NodeProps> = memo(({ data, selected }) => {
  const nodeData = data as unknown as KnowledgeGraphNodeData;

  const {
    knowledge_id,
    knowledge_name,
    chapter,
    difficulty,
    accuracy,
    status,
    is_prerequisite,
    is_recommended,
    path_stage,
    downstream_count,
    isFilteredOut,
    isSearched,
    is_on_route,
    route_role,
    route_rank,
  } = nodeData as KnowledgeGraphNodeData & {
    isFilteredOut?: boolean;
    isSearched?: boolean;
    is_on_route?: boolean;
    route_role?: string;
    route_rank?: number;
    route_badge?: string;
  };

  // 状态颜色与徽章设计
  let borderColor = 'border-slate-200';
  let bgColor = 'bg-white';
  let badgeColor = 'bg-slate-100 text-slate-600 border-slate-200';
  let badgeText = '尚无学习记录';
  let BadgeIcon = HelpCircle;

  if (status === 'WEAK') {
    borderColor = 'border-rose-300';
    bgColor = 'bg-rose-50/40';
    badgeColor = 'bg-rose-100 text-rose-700 border-rose-200';
    badgeText = `${accuracy !== null ? accuracy.toFixed(0) : ''}% 薄弱`;
    BadgeIcon = AlertTriangle;
  } else if (status === 'NEED_REVIEW') {
    borderColor = 'border-amber-300';
    bgColor = 'bg-amber-50/40';
    badgeColor = 'bg-amber-100 text-amber-700 border-amber-200';
    badgeText = `${accuracy !== null ? accuracy.toFixed(0) : ''}% 待巩固`;
    BadgeIcon = AlertTriangle;
  } else if (status === 'MASTERED') {
    borderColor = 'border-emerald-300';
    bgColor = 'bg-emerald-50/40';
    badgeColor = 'bg-emerald-100 text-emerald-700 border-emerald-200';
    badgeText = `${accuracy !== null ? accuracy.toFixed(0) : ''}% 掌握`;
    BadgeIcon = CheckCircle;
  } else {
    // UNSTUDIED / null
    borderColor = 'border-slate-200';
    bgColor = 'bg-slate-50/60';
    badgeColor = 'bg-slate-200/80 text-slate-600 border-slate-300';
    badgeText = '尚无学习记录';
    BadgeIcon = HelpCircle;
  }

  // 推荐路径高亮重载
  const isSpecialHighlight = is_recommended && path_stage === 1;

  return (
    <div
      className={`relative w-64 rounded-xl border-2 transition-all duration-200 shadow-sm hover:shadow-md cursor-pointer select-none ${bgColor} ${borderColor} ${
        selected ? 'ring-4 ring-indigo-500/30 border-indigo-600 scale-[1.03] shadow-lg' : ''
      } ${
        is_on_route && route_role === 'CURRENT'
          ? 'ring-4 ring-emerald-500/60 border-emerald-500 scale-[1.03] shadow-emerald-100 shadow-xl'
          : is_on_route && route_role === 'NEXT'
          ? 'ring-3 ring-amber-400/50 border-amber-400 shadow-amber-100 shadow-md'
          : is_on_route && route_role === 'UPCOMING'
          ? 'ring-2 ring-purple-400/40 border-purple-400'
          : isSpecialHighlight
          ? 'ring-2 ring-indigo-400 shadow-indigo-100 shadow-md'
          : ''
      } ${
        isSearched ? 'ring-4 ring-amber-400 border-amber-500 scale-[1.04]' : ''
      } ${
        isFilteredOut ? 'opacity-25 grayscale-[60%] pointer-events-none' : 'opacity-100'
      }`}
    >
      {/* Target Handle (Left: 接收前置依赖) */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 !bg-slate-400 !border-2 !border-white rounded-full transition-colors hover:!bg-indigo-600"
      />

      {/* 顶部标签条 */}
      <div className="px-3.5 pt-3 pb-1 flex items-center justify-between gap-1 text-xs">
        <span className="font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
          {knowledge_id}
        </span>
        <span className="text-[11px] text-slate-500 truncate max-w-[130px]" title={chapter}>
          {chapter.replace(/第.+?章\s*/, '')}
        </span>
      </div>

      {/* 知识点主标题 */}
      <div className="px-3.5 py-1.5">
        <h4 className="font-semibold text-sm text-slate-800 leading-snug line-clamp-2">
          {knowledge_name}
        </h4>
      </div>

      {/* 动态徽章行 */}
      <div className="px-3.5 pb-2.5 flex flex-wrap items-center gap-1.5">
        {/* 动态航线专属徽章 */}
        {is_on_route && (
          <span
            className={`inline-flex items-center gap-1 text-[11px] px-2.5 py-0.5 rounded-full font-bold shadow-xs ${
              route_role === 'CURRENT'
                ? 'bg-emerald-600 text-white animate-pulse'
                : route_role === 'NEXT'
                ? 'bg-amber-500 text-white'
                : 'bg-purple-600 text-white'
            }`}
          >
            <span>
              第 {route_rank} 站 ·{' '}
              {route_role === 'CURRENT' ? '当前焦点' : route_role === 'NEXT' ? '紧接学习' : '进阶延伸'}
            </span>
          </span>
        )}

        {/* 正确率或未学状态 */}
        <span className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border font-medium ${badgeColor}`}>
          <BadgeIcon className="w-3 h-3" />
          <span>{badgeText}</span>
        </span>

        {/* 学习路径 Stage 徽章 */}
        {!is_on_route && is_recommended && path_stage !== null && (
          <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-indigo-600 text-white font-semibold shadow-xs">
            <Sparkles className="w-3 h-3 text-amber-300" />
            <span>Stage {path_stage}</span>
          </span>
        )}

        {/* 前置基石徽章 */}
        {is_prerequisite && (
          <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-300 font-medium">
            前置基石
          </span>
        )}
      </div>

      {/* 卡片底栏：难度与下游拓扑辐射数 */}
      <div className="px-3.5 py-2 border-t border-slate-100 bg-white/60 rounded-b-xl flex items-center justify-between text-[11px] text-slate-500">
        <div className="flex items-center gap-0.5" title={`难度等级: ${difficulty} / 3`}>
          <span className="text-slate-400 mr-0.5">难度</span>
          {Array.from({ length: 3 }).map((_, i) => (
            <Star
              key={i}
              className={`w-3 h-3 ${
                i < difficulty ? 'text-amber-400 fill-amber-400' : 'text-slate-200 fill-slate-200'
              }`}
            />
          ))}
        </div>

        <div className="flex items-center gap-1 text-slate-500" title={`该知识点是 ${downstream_count} 个后续知识点的前置`}>
          <span>影响</span>
          <span className="font-semibold text-slate-700">{downstream_count}</span>
          <span>节点</span>
          <ArrowRight className="w-3 h-3 text-slate-400" />
        </div>
      </div>

      {/* Source Handle (Right: 输送后续依赖) */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 !bg-slate-400 !border-2 !border-white rounded-full transition-colors hover:!bg-indigo-600"
      />
    </div>
  );
});

KnowledgeGraphNode.displayName = 'KnowledgeGraphNode';
