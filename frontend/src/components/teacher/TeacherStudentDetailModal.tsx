import React, { useEffect, useState } from 'react';
import { X, ExternalLink } from 'lucide-react';
import type { TeacherStudentDetailResponse } from '../../types';
import { getTeacherStudentDetail } from '../../api';

interface TeacherStudentDetailModalProps {
  isOpen: boolean;
  studentId: string | null;
  onClose: () => void;
  onEnterStudentView?: (studentId: string) => void;
}

export const TeacherStudentDetailModal: React.FC<TeacherStudentDetailModalProps> = ({
  isOpen,
  studentId,
  onClose,
  onEnterStudentView,
}) => {
  const [detail, setDetail] = useState<TeacherStudentDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'kps' | 'wrongs' | 'timeline'>('kps');

  useEffect(() => {
    if (isOpen && studentId) {
      setIsLoading(true);
      getTeacherStudentDetail(studentId)
        .then((res) => setDetail(res))
        .catch((err) => console.error('Failed to load student detail for teacher:', err))
        .finally(() => setIsLoading(false));
    } else {
      setDetail(null);
    }
  }, [isOpen, studentId]);

  if (!isOpen || !studentId) return null;

  const summary = detail?.summary;
  const progress = detail?.progress;
  const wrongs = detail?.wrong_answers?.wrong_answers || [];
  const timeline = detail?.progress?.history_timeline || [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-950/60 backdrop-blur-xs animate-in fade-in duration-200"
      data-testid="teacher-student-detail-modal"
    >
      <div className="bg-white w-full max-w-4xl max-h-[90vh] rounded-3xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden">
        {/* Modal Top Header */}
        <div className="p-6 bg-slate-900 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-mono font-bold text-sm">
              {studentId}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base sm:text-lg font-bold text-white">
                  {summary?.student_name || studentId} · 学情全维档案
                </h3>
                {summary && (
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      summary.risk_level === 'HEALTHY'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/30'
                        : summary.risk_level === 'ATTENTION'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-400/30'
                        : 'bg-blue-500/20 text-blue-300 border border-blue-400/30'
                    }`}
                  >
                    {summary.risk_level === 'HEALTHY'
                      ? '学情健康'
                      : summary.risk_level === 'ATTENTION'
                      ? '重点关注'
                      : '平稳推进'}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {summary?.major} · {summary?.grade} · 学习目标: {summary?.learning_goal}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading ? (
            <div className="py-20 text-center space-y-3">
              <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-slate-500 font-medium">正在调阅该生学情档案...</p>
            </div>
          ) : detail ? (
            <>
              {/* Summary Metric Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-4 rounded-2xl bg-indigo-50/70 border border-indigo-100">
                  <div className="text-[11px] font-semibold text-indigo-900">综合掌握度</div>
                  <div className="text-2xl font-black text-indigo-700 font-mono mt-1">
                    {(summary ? summary.overall_mastery * 100 : 0).toFixed(1)}%
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-100">
                  <div className="text-[11px] font-semibold text-emerald-900">达标考点数</div>
                  <div className="text-2xl font-black text-emerald-700 font-mono mt-1">
                    {summary?.mastered_count || 0}{' '}
                    <span className="text-xs text-emerald-600 font-normal">/ 30</span>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-rose-50/70 border border-rose-100">
                  <div className="text-[11px] font-semibold text-rose-900">薄弱考点数</div>
                  <div className="text-2xl font-black text-rose-700 font-mono mt-1">
                    {summary?.weak_count || 0}{' '}
                    <span className="text-xs text-rose-600 font-normal">个</span>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-blue-50/70 border border-blue-100">
                  <div className="text-[11px] font-semibold text-blue-900">答题正确率</div>
                  <div className="text-2xl font-black text-blue-700 font-mono mt-1">
                    {(summary?.accuracy || 0).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* Sub-tab Switcher */}
              <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
                <button
                  type="button"
                  onClick={() => setActiveTab('kps')}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    activeTab === 'kps'
                      ? 'bg-indigo-600 text-white shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  30 考点认知全景
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('wrongs')}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                    activeTab === 'wrongs'
                      ? 'bg-rose-600 text-white shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <span>错题复盘流水</span>
                  <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-white/20">
                    {wrongs.length}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('timeline')}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    activeTab === 'timeline'
                      ? 'bg-indigo-600 text-white shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  真实学习流水 ({timeline.length})
                </button>
              </div>

              {/* Tab Content 1: Knowledge Points */}
              {activeTab === 'kps' && progress && (
                <div className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-96 overflow-y-auto pr-1">
                    {progress.knowledge_points.map((kp) => (
                      <div
                        key={kp.knowledge_id}
                        className="p-3 rounded-xl border border-slate-200 bg-white space-y-1.5 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-slate-700">
                            {kp.knowledge_id}
                          </span>
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                              kp.status === 'MASTERED'
                                ? 'bg-emerald-50 text-emerald-700'
                                : kp.status === 'NEEDS_REINFORCEMENT'
                                ? 'bg-rose-50 text-rose-700'
                                : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {(kp.mastery * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="font-bold text-slate-900 truncate">
                          {kp.knowledge_name}
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-1 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              kp.status === 'MASTERED' ? 'bg-emerald-500' : 'bg-indigo-500'
                            }`}
                            style={{ width: `${Math.min(100, kp.mastery * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tab Content 2: Wrongs */}
              {activeTab === 'wrongs' && (
                <div className="space-y-3">
                  {wrongs.length === 0 ? (
                    <div className="py-12 text-center text-slate-400 text-xs">
                      该生目前无错题复盘记录
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                      {wrongs.map((w) => (
                        <div
                          key={w.question_id}
                          className="p-4 rounded-2xl border border-slate-200 bg-slate-50/50 space-y-2 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-900">
                              {w.knowledge_id} {w.knowledge_name}
                            </span>
                            <span className="text-[11px] font-bold text-rose-600">
                              累计出错 {w.mistake_count} 次
                            </span>
                          </div>
                          <p className="text-slate-700">{w.question_prompt}</p>
                          <div className="flex items-center gap-4 text-[11px]">
                            <span className="text-rose-600 font-semibold">
                              学生作答: {w.student_answer}
                            </span>
                            <span className="text-emerald-600 font-semibold">
                              正确答案: {w.correct_answer}
                            </span>
                          </div>
                          <div className="p-2.5 rounded-xl bg-amber-50 text-amber-900 text-[11px]">
                            解析: {w.explanation}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab Content 3: Timeline */}
              {activeTab === 'timeline' && (
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {timeline.length === 0 ? (
                    <div className="py-12 text-center text-slate-400 text-xs">
                      暂无历史活动事件
                    </div>
                  ) : (
                    timeline.map((evt, idx) => (
                      <div
                        key={`${evt.event_id}-${idx}`}
                        className="p-3 rounded-xl border border-slate-100 bg-white flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-slate-100 font-bold text-[10px] text-slate-600">
                            {evt.event_type}
                          </span>
                          <span className="font-semibold text-slate-800">
                            {evt.knowledge_id} {evt.knowledge_name || ''}
                          </span>
                          {evt.is_correct !== undefined && (
                            <span
                              className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                evt.is_correct
                                  ? 'bg-emerald-50 text-emerald-700'
                                  : 'bg-rose-50 text-rose-700'
                              }`}
                            >
                              {evt.is_correct ? '正确' : '错误'}
                            </span>
                          )}
                        </div>
                        <span className="text-slate-400 font-mono text-[11px]">
                          {evt.timestamp.replace('T', ' ').slice(5, 16)}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="py-12 text-center text-slate-400 text-xs">
              未能获取到学生档案
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between shrink-0">
          <span className="text-xs text-slate-400 font-mono">
            {detail?.progress?.knowledge_points.length || 30} 考点覆盖 · 真实学情投影
          </span>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200/80 transition-colors cursor-pointer"
            >
              关闭
            </button>
            {onEnterStudentView && (
              <button
                type="button"
                onClick={() => onEnterStudentView(studentId)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-2xs transition-all cursor-pointer"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                以该生身份进入学习空间
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
