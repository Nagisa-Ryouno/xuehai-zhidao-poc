import React from 'react';
import { Flame, ArrowRight, CheckCircle2 } from 'lucide-react';
import type { TeacherWeakKnowledgePoint } from '../../types';
import { TeacherEmptyState } from './TeacherEmptyState';

interface TeacherWeakKnowledgeCardProps {
  weakPoints: TeacherWeakKnowledgePoint[];
  isLoading?: boolean;
  onViewAllKnowledge: () => void;
}

export const TeacherWeakKnowledgeCard: React.FC<TeacherWeakKnowledgeCardProps> = ({
  weakPoints,
  isLoading = false,
  onViewAllKnowledge,
}) => {
  return (
    <div
      className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/90 shadow-2xs space-y-5"
      data-testid="teacher-weak-points-ranking"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
            <Flame className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">
              班级重点瓶颈考点关注
            </h3>
            <p className="text-xs text-slate-500">
              基于全班未掌握人数与错误率识别的共性教学卡点
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onViewAllKnowledge}
          className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 cursor-pointer transition-colors"
        >
          查看全部 30 个考点全景
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 animate-pulse">
          {[1, 2, 3].map((i) => (
            <div key={i} className="p-4 rounded-2xl border border-slate-200 bg-slate-50/50 space-y-3">
              <div className="h-4 bg-slate-200 rounded-md w-1/3" />
              <div className="h-5 bg-slate-200 rounded-md w-2/3" />
              <div className="h-2 bg-slate-200 rounded-full w-full" />
            </div>
          ))}
        </div>
      ) : weakPoints.length === 0 ? (
        <TeacherEmptyState
          icon={<CheckCircle2 className="w-5 h-5 text-emerald-500" />}
          title="暂无薄弱考点聚焦记录"
          description="当前全班各考点平均掌握度均在 60% 及以上，暂未识别到共性瓶颈考点。"
          actionLabel="查阅全部 30 个考点"
          onAction={onViewAllKnowledge}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {weakPoints.slice(0, 5).map((wp, idx) => {
            const urgencyMeta = {
              HIGH: {
                label: '优先关注 · 建议集体面授',
                badge: 'bg-rose-50 text-rose-700 border-rose-200',
              },
              MEDIUM: {
                label: '中度预警 · 针对性作业',
                badge: 'bg-amber-50 text-amber-700 border-amber-200',
              },
              LOW: {
                label: '巩固观察',
                badge: 'bg-slate-100 text-slate-600 border-slate-200',
              },
            }[wp.urgency];

            return (
              <div
                key={wp.knowledge_id}
                className="p-4 rounded-2xl border border-slate-200/90 bg-white hover:border-indigo-300 hover:shadow-xs transition-all space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-md bg-slate-900 text-white font-mono text-[10px] font-bold flex items-center justify-center">
                      #{idx + 1}
                    </span>
                    <span className="font-mono text-xs font-bold text-slate-700">
                      {wp.knowledge_id}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${urgencyMeta.badge}`}
                  >
                    {urgencyMeta.label}
                  </span>
                </div>

                <div>
                  <h4 className="text-sm font-bold text-slate-900 leading-snug">
                    {wp.knowledge_name}
                  </h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">{wp.chapter}</p>
                </div>

                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">班级平均掌握度</span>
                    <span className="font-mono font-bold text-slate-800">
                      {(wp.avg_mastery * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-rose-500 h-full rounded-full"
                      style={{ width: `${Math.min(100, wp.avg_mastery * 100)}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-0.5">
                    <span>班级错误率: {wp.error_rate.toFixed(1)}%</span>
                    <span className="text-rose-600 font-semibold">
                      {wp.weak_student_count} 人薄弱
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
