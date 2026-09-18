import React, { useState, useMemo } from 'react';
import {
  Award,
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  BookOpen,
  Sparkles,
  HelpCircle,
  Calendar,
  Bot,
} from 'lucide-react';
import type { StudentProgressResponse } from '../../types';

interface ProgressOverviewProps {
  progressData: StudentProgressResponse | null;
  isLoading: boolean;
  onViewConceptCard?: (knowledgeId: string, knowledgeName: string) => void;
  onStartQuiz?: (knowledgeId: string, knowledgeName: string) => void;
  onAskAISummary?: () => void;
}

type FilterTab = 'ALL' | 'MASTERED' | 'DEVELOPING' | 'NEEDS_REINFORCEMENT' | 'UNSTUDIED';

export const ProgressOverview: React.FC<ProgressOverviewProps> = ({
  progressData,
  isLoading,
  onViewConceptCard,
  onStartQuiz,
  onAskAISummary,
}) => {
  const [activeTab, setActiveTab] = useState<FilterTab>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredPoints = useMemo(() => {
    if (!progressData || !progressData.knowledge_points) return [];
    let list = progressData.knowledge_points;

    if (activeTab !== 'ALL') {
      list = list.filter((kp) => kp.status === activeTab);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (kp) =>
          kp.knowledge_id.toLowerCase().includes(q) ||
          kp.knowledge_name.toLowerCase().includes(q) ||
          kp.chapter.toLowerCase().includes(q)
      );
    }

    return list;
  }, [progressData, activeTab, searchQuery]);

  if (isLoading) {
    return (
      <div className="glass-card rounded-3xl p-8 animate-pulse space-y-6">
        <div className="h-8 bg-slate-200 rounded-lg w-1/3" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="h-24 bg-slate-100 rounded-2xl" />
          <div className="h-24 bg-slate-100 rounded-2xl" />
          <div className="h-24 bg-slate-100 rounded-2xl" />
          <div className="h-24 bg-slate-100 rounded-2xl" />
        </div>
        <div className="h-64 bg-slate-100 rounded-2xl" />
      </div>
    );
  }

  if (!progressData) {
    return (
      <div className="glass-card rounded-3xl p-12 text-center">
        <HelpCircle className="w-12 h-12 text-slate-300 mx-auto mb-3" />
        <p className="text-slate-600 font-medium">暂无掌握度成效数据</p>
      </div>
    );
  }

  const {
    overall_mastery,
    mastery_level,
    total_practice_count,
    total_correct_count,
    overall_accuracy,
    mastered_count,
    developing_count,
    weak_count,
    unstudied_count,
    mastery_trend,
    history_timeline,
  } = progressData;

  const isMastered = overall_mastery >= 0.80;

  return (
    <div className="space-y-6" data-testid="student-progress-overview">
      {/* 总体成效总览 Hero Banner */}
      <div className="hero-navy rounded-3xl p-6 sm:p-8 text-white shadow-xl shadow-slate-900/20 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-400/30 text-indigo-300 text-xs font-semibold">
              <Award className="w-3.5 h-3.5" />
              认知掌握图谱 · 学习成效沉淀
            </div>
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
              全图谱 30 考点掌握度总览
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 max-w-xl leading-relaxed">
              基于认知掌握自适应追踪模型动态量化认知表现。统一标准：掌握度 ≥ 80% 判定为达标已掌握。
            </p>
            {onAskAISummary && (
              <div className="pt-2">
                <button
                  type="button"
                  onClick={onAskAISummary}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-white/20 hover:bg-white/30 text-white border border-white/30 backdrop-blur-sm transition-all cursor-pointer shadow-xs"
                >
                  <Bot className="w-4 h-4 text-purple-300" />
                  <span>🤖 总结我的学习情况</span>
                </button>
              </div>
            )}
          </div>

          {/* 核心总体掌握度大卡 */}
          <div className="bg-white/10 backdrop-blur-md rounded-2xl p-5 border border-white/15 flex items-center gap-5 shrink-0">
            <div className="relative flex items-center justify-center">
              <div
                className={`w-20 h-20 rounded-2xl flex flex-col items-center justify-center shadow-lg transition-all ${
                  isMastered
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/40'
                    : 'bg-indigo-500/20 text-indigo-300 border border-indigo-400/40'
                }`}
              >
                <span className="text-2xl font-black font-mono">
                  {(overall_mastery * 100).toFixed(1)}%
                </span>
                <span className="text-[10px] font-semibold tracking-wider uppercase mt-0.5">
                  综合掌握度
                </span>
              </div>
            </div>

            <div className="space-y-1">
              <div className="text-xs text-slate-300">认知阶段评级</div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-white">{mastery_level}</span>
                <span
                  className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                    isMastered
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/30'
                      : 'bg-amber-500/20 text-amber-300 border border-amber-400/30'
                  }`}
                >
                  {isMastered ? '认知达标' : '持续精进中'}
                </span>
              </div>
              <div className="text-[11px] text-slate-400">
                答题正确率: {overall_accuracy.toFixed(1)}% ({total_correct_count}/{total_practice_count})
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 4 维考点分类统计卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. 已达标 */}
        <div className="glass-card rounded-2xl p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500">已达标考点 (≥80%)</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-black text-slate-900 font-mono">
              {mastered_count}
            </span>
            <span className="text-xs text-slate-400">/ 30 考点</span>
          </div>
          <div className="mt-2 w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-emerald-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${(mastered_count / 30) * 100}%` }}
            />
          </div>
        </div>

        {/* 2. 发展中 */}
        <div className="glass-card rounded-2xl p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500">发展中 (60%~79%)</span>
            <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-black text-slate-900 font-mono">
              {developing_count}
            </span>
            <span className="text-xs text-slate-400">/ 30 考点</span>
          </div>
          <div className="mt-2 w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-indigo-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${(developing_count / 30) * 100}%` }}
            />
          </div>
        </div>

        {/* 3. 需巩固 */}
        <div className="glass-card rounded-2xl p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500">需重点巩固 (&lt;60%)</span>
            <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-black text-rose-600 font-mono">
              {weak_count}
            </span>
            <span className="text-xs text-slate-400">/ 30 考点</span>
          </div>
          <div className="mt-2 w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-rose-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${(weak_count / 30) * 100}%` }}
            />
          </div>
        </div>

        {/* 4. 未学习 */}
        <div className="glass-card rounded-2xl p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500">待解锁探索</span>
            <div className="w-8 h-8 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center">
              <BookOpen className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-black text-slate-700 font-mono">
              {unstudied_count}
            </span>
            <span className="text-xs text-slate-400">/ 30 考点</span>
          </div>
          <div className="mt-2 w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-slate-300 h-full rounded-full transition-all duration-500"
              style={{ width: `${(unstudied_count / 30) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* 掌握度变动历史趋势 (真实事件序列呈现) */}
      <div className="glass-card rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600">
              <TrendingUp className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">掌握度动态演化轨迹</h3>
              <p className="text-xs text-slate-500">
                记录历次答题与前测驱动的真实掌握度跃迁时序
              </p>
            </div>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {mastery_trend.length} 次关键变动节点
          </span>
        </div>

        {mastery_trend.length === 0 ? (
          <div className="py-8 text-center bg-slate-50/70 rounded-2xl border border-slate-100">
            <Sparkles className="w-8 h-8 text-indigo-300 mx-auto mb-2" />
            <p className="text-xs text-slate-500 font-medium">
              暂无历史变动记录。完成今日微测验或极速前测后，将在此生成演化曲线。
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2 overflow-x-auto pb-2 pt-1 no-scrollbar">
              {mastery_trend.map((pt, idx) => (
                <div
                  key={`${pt.timestamp}-${idx}`}
                  className="flex flex-col items-center min-w-[90px] p-3 rounded-2xl glass-chip shrink-0 hover:bg-white/70 transition-colors"
                >
                  <span className="text-[11px] text-slate-400 font-mono">#{idx + 1}</span>
                  <span className="text-sm font-black text-indigo-700 font-mono my-1">
                    {(pt.overall_mastery * 100).toFixed(1)}%
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-white text-slate-600 border border-slate-200 font-medium truncate max-w-[80px]">
                    {pt.knowledge_id || pt.event_type}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 30 考点掌握度矩阵与分类浏览 */}
      <div className="glass-card rounded-3xl p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-900">30 考点认知矩阵全览</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              点击考点可快速阅读精要速览微卡或开启针对性专项巩固
            </p>
          </div>

          {/* 搜索框 */}
          <div className="w-full sm:w-64">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索考点编号/名称/章节..."
              className="w-full px-3.5 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 transition-all"
            />
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar border-b border-slate-100">
          {(
            [
              { id: 'ALL', label: `全部 (${progressData.knowledge_points.length})` },
              { id: 'MASTERED', label: `已达标 (${mastered_count})` },
              { id: 'DEVELOPING', label: `发展中 (${developing_count})` },
              { id: 'NEEDS_REINFORCEMENT', label: `需巩固 (${weak_count})` },
              { id: 'UNSTUDIED', label: `未学习 (${unstudied_count})` },
            ] as const
          ).map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* 考点网格列表 */}
        {filteredPoints.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            无匹配的考点记录
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {filteredPoints.map((item) => {
              const statusMeta = {
                MASTERED: { label: '已达标', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200', bar: 'bg-emerald-500' },
                DEVELOPING: { label: '发展中', badge: 'bg-indigo-50 text-indigo-700 border-indigo-200', bar: 'bg-indigo-500' },
                NEEDS_REINFORCEMENT: { label: '需巩固', badge: 'bg-rose-50 text-rose-700 border-rose-200', bar: 'bg-rose-500' },
                UNSTUDIED: { label: '未学习', badge: 'bg-slate-100 text-slate-600 border-slate-200', bar: 'bg-slate-300' },
              }[item.status];

              return (
                <div
                  key={item.knowledge_id}
                  className="p-4 rounded-2xl glass-card hover:shadow-[0_18px_40px_rgba(214,150,105,.2)] transition-all duration-300 space-y-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded-md bg-slate-100 font-mono text-xs font-bold text-slate-700">
                        {item.knowledge_id}
                      </span>
                      <span className="text-[11px] text-slate-400">{item.chapter}</span>
                    </div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusMeta.badge}`}
                    >
                      {statusMeta.label}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-sm font-bold text-slate-900 leading-snug">
                      {item.knowledge_name}
                    </h4>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-500">掌握度</span>
                      <span className="font-mono font-bold text-slate-900">
                        {(item.mastery * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${statusMeta.bar}`}
                        style={{ width: `${Math.min(100, item.mastery * 100)}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-0.5">
                      <span>练习 {item.attempts} 次</span>
                      <span>正确率 {item.accuracy.toFixed(0)}%</span>
                    </div>
                  </div>

                  {/* 行动入口 */}
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-end gap-2">
                    {onViewConceptCard && (
                      <button
                        type="button"
                        onClick={() => onViewConceptCard(item.knowledge_id, item.knowledge_name)}
                        className="px-2.5 py-1 text-xs font-semibold text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors cursor-pointer"
                      >
                        速览微卡
                      </button>
                    )}
                    {onStartQuiz && item.status !== 'MASTERED' && (
                      <button
                        type="button"
                        onClick={() => onStartQuiz(item.knowledge_id, item.knowledge_name)}
                        className="px-2.5 py-1 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors cursor-pointer"
                      >
                        测验巩固
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 最近真实学习流水时间轴 */}
      <div className="glass-card rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-blue-50 text-blue-600">
              <Calendar className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">真实学习活动时间轴</h3>
              <p className="text-xs text-slate-500">
                可追溯记录（微测验、概念微卡学习、极速诊断）
              </p>
            </div>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {history_timeline.length} 条真实流水
          </span>
        </div>

        {history_timeline.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-xs">
            暂无学习活动记录，快去完成今日任务吧！
          </div>
        ) : (
          <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            {history_timeline.slice(0, 15).map((evt, idx) => {
              const isQuiz = evt.event_type === 'QUESTION_ATTEMPT';
              const isCard = evt.event_type === 'CONCEPT_VIEW';
              const isPretest = evt.event_type === 'PRETEST_SUBMIT';

              let dotColor = 'bg-slate-400';
              let badgeText = '学习行为';
              let badgeClass = 'bg-slate-100 text-slate-600 border-slate-200';

              if (isQuiz) {
                if (evt.is_correct) {
                  dotColor = 'bg-emerald-500';
                  badgeText = '答题正确';
                  badgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
                } else {
                  dotColor = 'bg-rose-500';
                  badgeText = '答题错误';
                  badgeClass = 'bg-rose-50 text-rose-700 border-rose-200';
                }
              } else if (isCard) {
                dotColor = 'bg-indigo-500';
                badgeText = '微卡研读';
                badgeClass = 'bg-indigo-50 text-indigo-700 border-indigo-200';
              } else if (isPretest) {
                dotColor = 'bg-violet-500';
                badgeText = '极速诊断';
                badgeClass = 'bg-violet-50 text-violet-700 border-violet-200';
              }

              return (
                <div key={`${evt.event_id}-${idx}`} className="relative flex items-start justify-between gap-4">
                  <div
                    className={`absolute -left-[19px] top-1.5 w-2.5 h-2.5 rounded-full ring-4 ring-white ${dotColor}`}
                  />
                  <div className="space-y-0.5 min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${badgeClass}`}>
                        {badgeText}
                      </span>
                      {evt.knowledge_id && (
                        <span className="text-xs font-bold text-slate-800">
                          {evt.knowledge_id} {evt.knowledge_name || ''}
                        </span>
                      )}
                    </div>
                    {evt.details && (
                      <p className="text-xs text-slate-500">{evt.details}</p>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-400 whitespace-nowrap font-mono shrink-0">
                    {evt.timestamp.replace('T', ' ').slice(5, 16)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
