import React, { useEffect, useState } from 'react';
import { X, ExternalLink } from 'lucide-react';
import type { TeacherStudentDetailResponse } from '../../types';
import { getTeacherStudentDetail } from '../../api';
import { TeacherActionModal } from './TeacherActionModal';
import { TeacherActionHistory } from './TeacherActionHistory';
import { useBodyScrollLock } from '../../utils/useBodyScrollLock';

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
  useBodyScrollLock(isOpen && !!studentId);

  const [detail, setDetail] = useState<TeacherStudentDetailResponse | any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'kps' | 'wrongs' | 'timeline' | 'actions'>('kps');
  const [error, setError] = useState<string | null>(null);
  const [selectedKnowledgeForAction, setSelectedKnowledgeForAction] = useState<{
    knowledge_id: string;
    knowledge_name: string;
  } | null>(null);
  const [actionSuccessToast, setActionSuccessToast] = useState<string | null>(null);
  const [actionRefreshTrigger, setActionRefreshTrigger] = useState<number>(0);

  const loadDetail = () => {
    if (!studentId) return;
    setIsLoading(true);
    setError(null);
    getTeacherStudentDetail(studentId)
      .then((res) => {
        setDetail(res);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : '获取该生学情档案失败');
      })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    if (isOpen && studentId) {
      loadDetail();
    } else {
      setDetail(null);
      setError(null);
    }
  }, [isOpen, studentId]);

  if (!isOpen || !studentId) return null;

  // 防御性统一读取（兼容平铺与嵌套模型）
  const studentName = detail?.student_name ?? detail?.summary?.student_name ?? studentId;
  const major = detail?.major ?? detail?.summary?.major ?? '经济学';
  const grade = detail?.grade ?? detail?.summary?.grade ?? '大二';
  const learningGoal = detail?.learning_goal ?? detail?.summary?.learning_goal ?? '微观经济学核心概念掌握';
  const overallMastery = detail?.overall_mastery ?? detail?.summary?.overall_mastery ?? 0;
  const accuracy = detail?.accuracy ?? detail?.summary?.accuracy ?? 0;
  const riskLevel = detail?.risk_level ?? detail?.summary?.risk_level ?? 'HEALTHY';

  const kps: any[] = detail?.knowledge_point_masteries || detail?.progress?.knowledge_points || [];
  const masteredCount =
    detail?.summary?.mastered_count ??
    detail?.progress?.mastered_count ??
    kps.filter((k: any) => k.status === 'MASTERED').length;
  const weakCount =
    detail?.summary?.weak_count ??
    detail?.progress?.weak_count ??
    kps.filter((k: any) => k.status === 'NEEDS_REINFORCEMENT' || (k.mastery !== undefined && k.mastery < 0.60)).length;

  const rawWrongs = detail?.wrong_answers;
  const wrongs: any[] = Array.isArray(rawWrongs)
    ? rawWrongs
    : (rawWrongs as any)?.wrong_answers || [];

  const rawTimeline = detail?.recent_events || detail?.progress?.history_timeline;
  const timeline: any[] = Array.isArray(rawTimeline) ? rawTimeline : [];

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
                  {studentName} · 学情全维档案
                </h3>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    riskLevel === 'HEALTHY'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/30'
                      : riskLevel === 'ATTENTION'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-400/30'
                      : 'bg-blue-500/20 text-blue-300 border border-blue-400/30'
                  }`}
                >
                  {riskLevel === 'HEALTHY'
                    ? '学情健康'
                    : riskLevel === 'ATTENTION'
                    ? '重点关注'
                    : '平稳推进'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {major} · {grade} · 学习目标: {learningGoal}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            data-testid="btn-close-student-detail-modal"
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
          ) : error ? (
            <div className="py-20 text-center space-y-4">
              <div className="text-rose-500 text-sm font-semibold">{error}</div>
              <button
                type="button"
                onClick={loadDetail}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all cursor-pointer shadow-sm"
              >
                重试调阅
              </button>
            </div>
          ) : detail ? (
            <>
              {/* Summary Metric Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-4 rounded-2xl bg-indigo-50/70 border border-indigo-100">
                  <div className="text-[11px] font-semibold text-indigo-900">综合掌握度</div>
                  <div className="text-2xl font-black text-indigo-700 font-mono mt-1">
                    {(overallMastery * 100).toFixed(1)}%
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-100">
                  <div className="text-[11px] font-semibold text-emerald-900">达标考点数</div>
                  <div className="text-2xl font-black text-emerald-700 font-mono mt-1">
                    {masteredCount}{' '}
                    <span className="text-xs text-emerald-600 font-normal">/ 30</span>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-rose-50/70 border border-rose-100">
                  <div className="text-[11px] font-semibold text-rose-900">薄弱考点数</div>
                  <div className="text-2xl font-black text-rose-700 font-mono mt-1">
                    {weakCount}{' '}
                    <span className="text-xs text-rose-600 font-normal">个</span>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-blue-50/70 border border-blue-100">
                  <div className="text-[11px] font-semibold text-blue-900">答题正确率</div>
                  <div className="text-2xl font-black text-blue-700 font-mono mt-1">
                    {accuracy.toFixed(1)}%
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
                <button
                  type="button"
                  onClick={() => setActiveTab('actions')}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    activeTab === 'actions'
                      ? 'bg-indigo-600 text-white shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                  data-testid="tab-teacher-actions"
                >
                  教学动作
                </button>
              </div>

              {/* Tab Content 1: Knowledge Points */}
              {activeTab === 'kps' && (
                <div className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-96 overflow-y-auto pr-1">
                    {kps.map((kp: any) => (
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
                        <button
                          type="button"
                          onClick={() =>
                            setSelectedKnowledgeForAction({
                              knowledge_id: kp.knowledge_id,
                              knowledge_name: kp.knowledge_name,
                            })
                          }
                          className="w-full mt-1.5 py-1 px-2 rounded-lg text-[11px] font-semibold text-indigo-600 bg-indigo-50/70 hover:bg-indigo-100 hover:text-indigo-700 transition-colors border border-indigo-100 cursor-pointer flex items-center justify-center gap-1"
                          data-testid={`btn-teacher-action-${kp.knowledge_id}`}
                        >
                          教学动作
                        </button>
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

              {/* Tab Content 4: Teacher Action History (Sprint 10-D Phase 4-D) */}
              {activeTab === 'actions' && (
                <TeacherActionHistory
                  studentId={studentId}
                  refreshTrigger={actionRefreshTrigger}
                />
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
            {kps.length || 30} 考点覆盖 · 真实学情投影
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

        {/* Phase 4-C: Teacher Action Modal */}
        {selectedKnowledgeForAction && (
          <TeacherActionModal
            isOpen={!!selectedKnowledgeForAction}
            studentId={studentId}
            studentName={studentName}
            knowledgeId={selectedKnowledgeForAction.knowledge_id}
            knowledgeName={selectedKnowledgeForAction.knowledge_name}
            onClose={() => setSelectedKnowledgeForAction(null)}
            onSuccess={(action) => {
              setSelectedKnowledgeForAction(null);
              setActionSuccessToast(`已针对 ${action.knowledge_name} 成功记录教学动作`);
              setActionRefreshTrigger((prev) => prev + 1);
              setTimeout(() => setActionSuccessToast(null), 3000);
            }}
          />
        )}

        {/* Action Feedback Toast */}
        {actionSuccessToast && (
          <div
            className="absolute bottom-16 left-1/2 -translate-x-1/2 z-50 px-4 py-2 bg-slate-900 text-white text-xs font-semibold rounded-full shadow-lg border border-slate-700 animate-in fade-in flex items-center gap-2"
            data-testid="student-detail-action-toast"
          >
            <div className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>{actionSuccessToast}</span>
          </div>
        )}
      </div>
    </div>
  );
};
