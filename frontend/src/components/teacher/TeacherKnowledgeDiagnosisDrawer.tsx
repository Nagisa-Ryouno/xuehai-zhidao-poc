import React, { useState, useEffect, useCallback } from 'react';
import { X, BookOpen, Layers, AlertTriangle, Flame, RotateCcw } from 'lucide-react';
import type { TeacherKnowledgeDiagnosisResponse } from '../../types';
import { getTeacherKnowledgeDiagnosis } from '../../api';
import { TeacherEmptyState } from './TeacherEmptyState';
import { useBodyScrollLock } from '../../utils/useBodyScrollLock';
import { getAvatarInitial } from '../../utils/avatar';

interface TeacherKnowledgeDiagnosisDrawerProps {
  isOpen: boolean;
  knowledgeId: string | null;
  onClose: () => void;
  onSelectStudentForDetail: (studentId: string) => void;
  onEnterStudentView: (studentId: string) => void;
}

export const TeacherKnowledgeDiagnosisDrawer: React.FC<TeacherKnowledgeDiagnosisDrawerProps> = ({
  isOpen,
  knowledgeId,
  onClose,
  onSelectStudentForDetail,
  onEnterStudentView,
}) => {
  useBodyScrollLock(isOpen);
  const [data, setData] = useState<TeacherKnowledgeDiagnosisResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [filterMode, setFilterMode] = useState<'ATTENTION' | 'ALL'>('ATTENTION');

  const fetchDiagnosis = useCallback(async () => {
    if (!knowledgeId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await getTeacherKnowledgeDiagnosis(knowledgeId);
      setData(res);
      // 若该考点无需要进一步关注的学生，默认平滑切换为展示全部学生
      if (res.weak_student_count === 0) {
        setFilterMode('ALL');
      } else {
        setFilterMode('ATTENTION');
      }
    } catch (err) {
      console.error('Failed to fetch knowledge diagnosis:', err);
      setError(err instanceof Error ? err.message : '获取考点学生学情诊断数据失败');
    } finally {
      setIsLoading(false);
    }
  }, [knowledgeId]);

  useEffect(() => {
    if (isOpen && knowledgeId) {
      fetchDiagnosis();
    } else {
      setData(null);
      setError(null);
    }
  }, [isOpen, knowledgeId, fetchDiagnosis]);

  if (!isOpen || !knowledgeId) return null;

  // 严格复用现有确定性规则：weak_student_count 对应 mastery < 0.60
  const displayedStudents = data?.students
    ? filterMode === 'ATTENTION'
      ? data.students.filter((s) => s.mastery < 0.60)
      : data.students
    : [];

  const urgencyMeta = data
    ? {
        HIGH: {
          label: '优先关注',
          class: 'bg-rose-50 text-rose-700 border-rose-200',
        },
        MEDIUM: {
          label: '中度预警',
          class: 'bg-amber-50 text-amber-700 border-amber-200',
        },
        LOW: {
          label: '掌握良好',
          class: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        },
      }[data.urgency]
    : null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden bg-slate-950/40 backdrop-blur-xs animate-in fade-in duration-200 flex justify-end"
      data-testid="teacher-diagnosis-drawer"
    >
      <div className="bg-white w-full max-w-xl h-full shadow-2xl border-l border-slate-200 flex flex-col overflow-hidden animate-in slide-in-from-right duration-300">
        {/* Drawer Header */}
        <div className="p-6 bg-slate-900 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-mono font-bold text-sm">
              {knowledgeId}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">
                  考点学情深度诊断
                </span>
                {urgencyMeta && (
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${urgencyMeta.class}`}
                  >
                    {urgencyMeta.label}
                  </span>
                )}
              </div>
              <h3 className="text-base sm:text-lg font-bold text-white mt-0.5 truncate max-w-sm">
                {data?.knowledge_name || knowledgeId}
              </h3>
              <p className="text-xs text-slate-400">
                {data?.chapter || '考点诊断'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            data-testid="btn-close-diagnosis-drawer"
            title="关闭诊断侧栏"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading ? (
            <div className="py-24 text-center space-y-3">
              <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-slate-500 font-medium">
                正在分析该知识点对应的学生学情……
              </p>
            </div>
          ) : error ? (
            <div className="py-20 text-center space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <h4 className="text-sm font-bold text-slate-900">暂时无法加载该知识点的学生学情</h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">{error}</p>
              <button
                type="button"
                onClick={fetchDiagnosis}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all cursor-pointer shadow-sm inline-flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                重新加载
              </button>
            </div>
          ) : data ? (
            <>
              {/* KP Macro Summary KPI Grid */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/90 space-y-1">
                  <div className="text-[11px] font-semibold text-slate-500 flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5 text-indigo-600" />
                    班级平均掌握度
                  </div>
                  <div className="text-xl font-black text-slate-900 font-mono">
                    {(data.average_mastery * 100).toFixed(1)}%
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-rose-50/60 border border-rose-100 space-y-1">
                  <div className="text-[11px] font-semibold text-rose-700 flex items-center gap-1">
                    <Flame className="w-3.5 h-3.5 text-rose-600" />
                    需要进一步关注
                  </div>
                  <div className="text-xl font-black text-rose-600 font-mono">
                    {data.weak_student_count}{' '}
                    <span className="text-xs text-rose-400 font-normal">/ {data.student_count} 人</span>
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-amber-50/60 border border-amber-100 space-y-1">
                  <div className="text-[11px] font-semibold text-amber-700 flex items-center gap-1">
                    <BookOpen className="w-3.5 h-3.5 text-amber-600" />
                    相关累计错题
                  </div>
                  <div className="text-xl font-black text-amber-700 font-mono">
                    {data.total_mistakes}{' '}
                    <span className="text-xs text-amber-500 font-normal">次</span>
                  </div>
                </div>
              </div>

              {/* View Switcher Pills */}
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl">
                  <button
                    type="button"
                    onClick={() => setFilterMode('ATTENTION')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                      filterMode === 'ATTENTION'
                        ? 'bg-white text-slate-900 shadow-2xs font-bold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                    data-testid="btn-filter-attention"
                  >
                    需要进一步关注 ({data.weak_student_count})
                  </button>
                  <button
                    type="button"
                    onClick={() => setFilterMode('ALL')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                      filterMode === 'ALL'
                        ? 'bg-white text-slate-900 shadow-2xs font-bold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                    data-testid="btn-filter-all"
                  >
                    全部学生 ({data.student_count})
                  </button>
                </div>

                <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
                  按掌握度升序排序
                </span>
              </div>

              {/* Students List */}
              {displayedStudents.length === 0 ? (
                <TeacherEmptyState
                  title="当前没有符合筛选条件的学生"
                  description={
                    filterMode === 'ATTENTION'
                      ? '当前没有学生满足“需要进一步关注”（掌握度 < 60%）的条件。'
                      : '当前班级暂无学生数据。'
                  }
                  actionLabel={filterMode === 'ATTENTION' ? '查看全部学生' : undefined}
                  onAction={() => setFilterMode('ALL')}
                />
              ) : (
                <div className="space-y-3">
                  {displayedStudents.map((st) => {
                    const riskBadge = {
                      HEALTHY: {
                        label: '掌握良好',
                        class: 'bg-emerald-50 text-emerald-700 border-emerald-200',
                      },
                      NORMAL: {
                        label: '学习推进中',
                        class: 'bg-blue-50 text-blue-700 border-blue-200',
                      },
                      ATTENTION: {
                        label: '重点关注',
                        class: 'bg-rose-50 text-rose-700 border-rose-200',
                      },
                    }[st.risk_level] || {
                      label: st.risk_level,
                      class: 'bg-slate-100 text-slate-600 border-slate-200',
                    };

                    const masteryPct = (st.mastery * 100).toFixed(1);

                    return (
                      <div
                        key={st.student_id}
                        className="p-4 rounded-2xl border border-slate-200/90 bg-white hover:border-indigo-300 hover:shadow-xs transition-all space-y-3"
                        data-testid={`diagnosis-student-row-${st.student_id}`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-lg bg-indigo-600/10 text-indigo-700 font-bold flex items-center justify-center shrink-0 overflow-hidden select-none text-xs">
                              {getAvatarInitial(st.student_name)}
                            </div>
                            <div>
                              <div className="font-bold text-slate-900 text-xs sm:text-sm">
                                {st.student_name}
                              </div>
                              <div className="text-[11px] text-slate-400">
                                {st.major} · {st.grade}
                              </div>
                            </div>
                          </div>

                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${riskBadge.class}`}
                          >
                            {riskBadge.label}
                          </span>
                        </div>

                        {/* Mastery & Performance Stats */}
                        <div className="space-y-1.5 pt-1 border-t border-slate-100 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="text-slate-500 text-[11px]">本考点当前掌握度</span>
                            <span className="font-mono font-bold text-slate-800">
                              {masteryPct}%
                            </span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                st.mastery >= 0.8
                                  ? 'bg-emerald-500'
                                  : st.mastery >= 0.6
                                  ? 'bg-indigo-500'
                                  : 'bg-rose-500'
                              }`}
                              style={{ width: `${Math.min(100, st.mastery * 100)}%` }}
                            />
                          </div>
                          <div className="flex items-center justify-between text-[11px] text-slate-400 pt-0.5 font-mono">
                            <span>做题表现: 共练 {st.attempts} 题</span>
                            <span className={st.mistake_count > 0 ? 'text-rose-600 font-semibold' : ''}>
                              错题 {st.mistake_count} 次
                            </span>
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-50">
                          <button
                            type="button"
                            onClick={() => onSelectStudentForDetail(st.student_id)}
                            className="px-3 py-1.5 rounded-xl text-xs font-bold text-indigo-600 hover:bg-indigo-50 transition-colors cursor-pointer"
                            data-testid={`btn-diagnosis-detail-${st.student_id}`}
                          >
                            学情档案
                          </button>
                          <button
                            type="button"
                            onClick={() => onEnterStudentView(st.student_id)}
                            className="px-3 py-1.5 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                            data-testid={`btn-diagnosis-enter-student-${st.student_id}`}
                          >
                            进入视界
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Drawer Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between shrink-0">
          <span className="text-xs text-slate-400 font-mono">
            {knowledgeId} 考点专属下钻 · 确定性只读聚合
          </span>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200/80 transition-colors cursor-pointer"
          >
            完成查看
          </button>
        </div>
      </div>
    </div>
  );
};
