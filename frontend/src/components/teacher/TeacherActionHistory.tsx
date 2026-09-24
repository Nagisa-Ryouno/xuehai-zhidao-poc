import React, { useEffect, useState } from 'react';
import { BookmarkCheck, AlertCircle, Loader2 } from 'lucide-react';
import type { TeacherActionItem, TeacherActionType } from '../../types';
import { getTeacherActionHistory } from '../../api';

export interface TeacherActionHistoryProps {
  studentId: string;
  refreshTrigger?: number;
}

export const TEACHER_ACTION_LABEL_MAP: Record<TeacherActionType, string> = {
  REVIEW_CONCEPT: '建议复习该考点',
  RETRY_PRACTICE: '建议重新练习',
  MARK_FOLLOWED: '标记为已关注',
};

export const TEACHER_ACTION_BADGE_STYLE: Record<TeacherActionType, string> = {
  REVIEW_CONCEPT: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  RETRY_PRACTICE: 'bg-blue-50 text-blue-700 border-blue-200',
  MARK_FOLLOWED: 'bg-slate-100 text-slate-700 border-slate-200',
};

function formatActionTime(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return isoStr;
  }
}

export const TeacherActionHistory: React.FC<TeacherActionHistoryProps> = ({
  studentId,
  refreshTrigger = 0,
}) => {
  const [actions, setActions] = useState<TeacherActionItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = () => {
    setIsLoading(true);
    setError(null);

    getTeacherActionHistory(studentId)
      .then((res) => {
        // 服务端权威返回已按 created_at 倒序排列，前端保持权威顺序
        const sorted = (res.actions || []).slice().sort((a, b) => {
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
        setActions(sorted);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : '教学动作记录暂时无法加载');
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    loadHistory();
  }, [studentId, refreshTrigger]);

  if (isLoading && actions.length === 0) {
    return (
      <div
        className="py-16 flex flex-col items-center justify-center text-slate-400 text-xs gap-2.5"
        data-testid="teacher-action-history-loading"
      >
        <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
        <span>加载教学动作记录中...</span>
      </div>
    );
  }

  if (error && !isLoading && actions.length === 0) {
    return (
      <div
        className="py-12 flex flex-col items-center justify-center text-center gap-2 p-6 rounded-2xl bg-rose-50/50 border border-rose-100"
        data-testid="teacher-action-history-error"
      >
        <AlertCircle className="w-6 h-6 text-rose-500" />
        <p className="text-xs font-bold text-slate-800">教学动作记录暂时无法加载</p>
        <p className="text-[11px] text-slate-500 max-w-sm leading-relaxed">{error}</p>
        <button
          type="button"
          onClick={loadHistory}
          className="mt-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 transition-colors border border-indigo-200 cursor-pointer"
          data-testid="btn-retry-action-history"
        >
          重新加载
        </button>
      </div>
    );
  }

  if (!isLoading && !error && actions.length === 0) {
    return (
      <div
        className="py-14 flex flex-col items-center justify-center text-center gap-2.5 p-6 rounded-2xl bg-slate-50 border border-slate-200/80"
        data-testid="teacher-action-history-empty"
      >
        <div className="w-10 h-10 rounded-2xl bg-slate-200/70 flex items-center justify-center text-slate-400">
          <BookmarkCheck className="w-5 h-5" />
        </div>
        <p className="text-xs font-bold text-slate-800">暂时还没有教学动作记录</p>
        <p className="text-[11px] text-slate-500 max-w-xs leading-relaxed">
          当你在学生详情中记录教学动作后，相关记录会显示在这里。
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="teacher-action-history-list">
      {/* Scope Disclaimer */}
      <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-[11px] text-slate-500 flex items-center justify-between">
        <span>
          本流水为教师历史教学关注记录，用于教学反思与观察，不直接代表学生客观学习状态。
        </span>
        <span className="font-mono font-semibold text-slate-700">共 {actions.length} 条记录</span>
      </div>

      {/* History Items List (created_at DESC) */}
      <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
        {actions.map((item) => {
          const actionLabel = TEACHER_ACTION_LABEL_MAP[item.action_type] || item.action_type;
          const badgeStyle =
            TEACHER_ACTION_BADGE_STYLE[item.action_type] ||
            'bg-slate-100 text-slate-700 border-slate-200';

          return (
            <div
              key={item.action_id}
              className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-colors space-y-2 text-xs"
              data-testid={`action-history-item-${item.action_id}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${badgeStyle}`}
                  >
                    {actionLabel}
                  </span>
                  <span className="font-mono text-slate-400 text-[11px]">
                    {formatActionTime(item.created_at)}
                  </span>
                </div>
                <span className="text-[11px] font-semibold text-slate-400">经办：任课教师</span>
              </div>

              <div className="flex items-center justify-between pt-0.5">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono font-bold text-indigo-700">{item.knowledge_id}</span>
                  <span className="font-bold text-slate-900">{item.knowledge_name}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
