import React, { useState } from 'react';
import {
  BookOpen,
  AlertCircle,
  RotateCcw,
  Sparkles,
  CheckCircle,
  XCircle,
  Clock,
  Filter,
  Bot,
} from 'lucide-react';
import type { WrongAnswerReviewResponse } from '../../types';

interface WrongAnswerReviewProps {
  wrongAnswerData: WrongAnswerReviewResponse | null;
  isLoading: boolean;
  onViewConceptCard: (knowledgeId: string, knowledgeName: string) => void;
  onStartQuiz: (knowledgeId: string, knowledgeName: string) => void;
  onAskAI?: (questionId: string, knowledgeId: string) => void;
}

type PriorityFilter = 'ALL' | 'HIGH' | 'MEDIUM' | 'LOW';

export const WrongAnswerReview: React.FC<WrongAnswerReviewProps> = ({
  wrongAnswerData,
  isLoading,
  onViewConceptCard,
  onStartQuiz,
  onAskAI,
}) => {
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>('ALL');

  if (isLoading) {
    return (
      <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-xs animate-pulse space-y-6">
        <div className="h-8 bg-slate-200 rounded-lg w-1/3" />
        <div className="h-32 bg-slate-100 rounded-2xl" />
        <div className="h-48 bg-slate-100 rounded-2xl" />
      </div>
    );
  }

  const items = wrongAnswerData?.wrong_answers || [];
  const totalWrong = wrongAnswerData?.total_wrong || 0;

  const filteredItems = items.filter((item) => {
    if (priorityFilter === 'ALL') return true;
    return item.review_priority === priorityFilter;
  });

  return (
    <div className="space-y-6" data-testid="student-wrong-answers">
      {/* 错题本 Header Banner */}
      <div className="bg-gradient-to-br from-rose-950 via-slate-900 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl shadow-rose-950/20 border border-slate-800 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-rose-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/20 border border-rose-400/30 text-rose-300 text-xs font-semibold">
              <AlertCircle className="w-3.5 h-3.5" />
              错题复盘本 · 认知查漏补缺
            </div>
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
              错误试题归纳与强化再练
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 max-w-xl leading-relaxed">
              系统根据真实做题流水自动汇总错题。建议“先研读概念微卡，再启动专项微测验”，实现知识闭环。
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-md rounded-2xl p-5 border border-white/15 flex items-center gap-4 shrink-0">
            <div className="w-16 h-16 rounded-2xl bg-rose-500/20 border border-rose-400/40 text-rose-300 flex flex-col items-center justify-center font-mono">
              <span className="text-2xl font-black">{totalWrong}</span>
              <span className="text-[10px] uppercase font-semibold">道错题</span>
            </div>
            <div>
              <div className="text-xs text-slate-300">复盘状态</div>
              <div className="text-base font-bold text-white mt-0.5">
                {totalWrong === 0 ? '全盘清空 · 状态极佳' : '有待强化突破'}
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">
                优先级算法智能排序
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 错题为空时的友好鼓励状态 */}
      {totalWrong === 0 ? (
        <div
          data-testid="wrong-answers-empty-state"
          className="bg-white rounded-3xl p-12 text-center border border-slate-200 shadow-2xs space-y-4"
        >
          <div className="w-16 h-16 rounded-3xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto shadow-inner">
            <CheckCircle className="w-8 h-8" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-900">
              太棒了！目前没有需要复盘的错题
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              你的所有练习均已达成正确或尚未产生错题。可前往「今日任务」继续推进学习航线。
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* 优先级过滤栏 */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-xs text-slate-500 font-semibold mr-1">复盘紧迫度:</span>
              {(
                [
                  { id: 'ALL', label: `全部 (${items.length})` },
                  { id: 'HIGH', label: '高优紧迫' },
                  { id: 'MEDIUM', label: '中等' },
                  { id: 'LOW', label: '已达标回顾' },
                ] as const
              ).map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setPriorityFilter(f.id)}
                  className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                    priorityFilter === f.id
                      ? 'bg-rose-600 text-white shadow-2xs'
                      : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <span className="text-xs text-slate-400">
              显示 {filteredItems.length} 道错题
            </span>
          </div>

          {/* 错题卡片列表 */}
          <div className="space-y-4">
            {filteredItems.map((item) => {
              const priorityBadge = {
                HIGH: { label: '高危卡点 · 优先复盘', class: 'bg-rose-50 text-rose-700 border-rose-200' },
                MEDIUM: { label: '巩固推进', class: 'bg-amber-50 text-amber-700 border-amber-200' },
                LOW: { label: '已达标回顾', class: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
              }[item.review_priority];

              const isMastered = item.current_mastery >= 0.80;

              return (
                <div
                  key={item.question_id}
                  className="bg-white rounded-3xl p-6 border border-slate-200 shadow-2xs hover:border-slate-300 transition-all space-y-4"
                  data-testid={`wrong-answer-card-${item.question_id}`}
                >
                  {/* 考点与优先级 Header */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 font-mono text-xs font-bold border border-indigo-200">
                        {item.knowledge_id}
                      </span>
                      <span className="text-sm font-bold text-slate-900">
                        {item.knowledge_name}
                      </span>
                      <span className="text-xs text-slate-400">· {item.chapter}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${priorityBadge.class}`}
                      >
                        {priorityBadge.label}
                      </span>
                      <span
                        className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded-md ${
                          isMastered
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-amber-50 text-amber-700'
                        }`}
                      >
                        当前掌握度: {(item.current_mastery * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* 题目题干 */}
                  <div className="space-y-2">
                    <div className="flex items-start gap-2">
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-xs font-bold">
                        {item.question_id}
                      </span>
                      <p className="text-sm font-semibold text-slate-900 leading-relaxed">
                        {item.question_prompt}
                      </p>
                    </div>

                    {/* 选项比对 */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                      {Object.entries(item.options).map(([key, val]) => {
                        const isStudent = key === item.student_answer;
                        const isCorrect = key === item.correct_answer;

                        let optionStyle = 'bg-slate-50 border-slate-200 text-slate-700';
                        if (isCorrect) {
                          optionStyle = 'bg-emerald-50/70 border-emerald-300 text-emerald-900 font-semibold';
                        } else if (isStudent) {
                          optionStyle = 'bg-rose-50/70 border-rose-300 text-rose-900 font-semibold';
                        }

                        return (
                          <div
                            key={key}
                            className={`p-3 rounded-xl border text-xs flex items-start gap-2 ${optionStyle}`}
                          >
                            <span className="font-bold font-mono shrink-0">{key}.</span>
                            <span className="flex-1">{val}</span>
                            {isCorrect && (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-100/70 px-1.5 py-0.5 rounded shrink-0">
                                <CheckCircle className="w-3 h-3" /> 正确答案
                              </span>
                            )}
                            {isStudent && !isCorrect && (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-700 bg-rose-100/70 px-1.5 py-0.5 rounded shrink-0">
                                <XCircle className="w-3 h-3" /> 你的错误选择
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* 解析说明 */}
                  <div className="p-4 rounded-2xl bg-amber-50/60 border border-amber-200/70 text-xs text-amber-900 space-y-1">
                    <div className="font-bold flex items-center gap-1.5 text-amber-950">
                      <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                      官方试题详解
                    </div>
                    <p className="leading-relaxed text-amber-900/90">{item.explanation}</p>
                  </div>

                  {/* Footer 元信息与两项核心行动 CTA */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
                    <div className="flex items-center gap-3 text-xs text-slate-400">
                      <span>累计做错 {item.mistake_count} 次</span>
                      <span>·</span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        最近出错: {item.last_error_time.replace('T', ' ').slice(5, 16)}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* AI 错题剖析行动 */}
                      {onAskAI && (
                        <button
                          type="button"
                          onClick={() => onAskAI(item.question_id, item.knowledge_id)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200/80 transition-colors cursor-pointer"
                        >
                          <Bot className="w-3.5 h-3.5 text-purple-600" />
                          🤖 AI 帮我分析
                        </button>
                      )}

                      {/* 关键行动 1: 重新学习 (ConceptCard) */}
                      <button
                        type="button"
                        onClick={() => onViewConceptCard(item.knowledge_id, item.knowledge_name)}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200/80 transition-colors cursor-pointer"
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        📖 重新学习微卡
                      </button>

                      {/* 关键行动 2: 再次练习 (MicroQuiz) */}
                      <button
                        type="button"
                        onClick={() => onStartQuiz(item.knowledge_id, item.knowledge_name)}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-2xs transition-all cursor-pointer"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        ✏️ 再次练习突破
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
