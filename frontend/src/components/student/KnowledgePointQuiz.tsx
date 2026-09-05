import React, { useState, useEffect, useMemo } from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  Award,
  ArrowRight,
  RotateCcw,
  Loader2,
  AlertCircle,
  Sparkles,
  HelpCircle,
  ChevronLeft,
} from 'lucide-react';
import {
  initQuizSession,
  startLoadingQuestions,
  setQuestionsLoaded,
  setQuestionsLoadError,
  selectOption,
  canSubmitAnswer,
  startSubmittingAnswer,
  buildSubmitPayload,
  setSubmitSuccess,
  setSubmitError,
  goToNextQuestion,
  calculateQuizSummary,
  resetQuizSession,
  formatDuration,
  type QuizSessionState,
} from './quizModel';
import { getQuizQuestions, submitQuizAnswer } from '../../api';

export interface KnowledgePointQuizProps {
  knowledgeId: string;
  knowledgeName: string;
  studentId: string;
  onBackToDetail?: () => void;
  onFinish?: () => void;
}

export const KnowledgePointQuiz: React.FC<KnowledgePointQuizProps> = ({
  knowledgeId,
  knowledgeName,
  studentId,
  onBackToDetail,
  onFinish,
}) => {
  const [session, setSession] = useState<QuizSessionState>(() =>
    initQuizSession(knowledgeId, knowledgeName)
  );

  // 挂载时通过真实 API 获取脱敏题目
  useEffect(() => {
    let isMounted = true;
    async function loadQuestions() {
      setSession((s) => startLoadingQuestions(s));
      try {
        const res = await getQuizQuestions(knowledgeId);
        if (!isMounted) return;
        setSession((s) => setQuestionsLoaded(s, res.questions));
      } catch (err: unknown) {
        if (!isMounted) return;
        const msg =
          err instanceof Error
            ? err.message
            : '微测验加载失败，请检查网络后重试';
        setSession((s) => setQuestionsLoadError(s, msg));
      }
    }

    loadQuestions();
    return () => {
      isMounted = false;
    };
  }, [knowledgeId, knowledgeName]);

  // 处理选中选项
  const handleSelectOption = (optionKey: string) => {
    if (session.status !== 'answering') return;
    setSession((s) => selectOption(s, optionKey));
  };

  // 提交作答并执行服务端权威判题
  const handleSubmitAnswer = async () => {
    if (!canSubmitAnswer(session)) return;

    const effectiveNow =
      typeof performance !== 'undefined' ? performance.now() : Date.now();
    let payload;
    try {
      payload = buildSubmitPayload(session, studentId, effectiveNow);
    } catch {
      return;
    }

    const timeSpentMs = payload.time_spent_ms ?? 0;
    setSession((s) => startSubmittingAnswer(s));

    try {
      const res = await submitQuizAnswer(payload);
      setSession((s) => setSubmitSuccess(s, res, timeSpentMs));
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : '答案提交失败，请检查网络后重试';
      setSession((s) => setSubmitError(s, msg));
    }
  };

  // 下一题或完成
  const handleNext = () => {
    setSession((s) => goToNextQuestion(s));
  };

  // 重新测验
  const handleRestart = async () => {
    setSession(resetQuizSession(session));
    setSession((s) => startLoadingQuestions(s));
    try {
      const res = await getQuizQuestions(knowledgeId);
      setSession((s) => setQuestionsLoaded(s, res.questions));
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : '微测验重新加载失败，请稍后重试';
      setSession((s) => setQuestionsLoadError(s, msg));
    }
  };

  // 计算结算统计指标
  const summary = useMemo(() => {
    if (session.status !== 'completed') return null;
    return calculateQuizSummary(session.records);
  }, [session.status, session.records]);

  // -------------------------------------------------------------
  // 状态 B: 加载中
  // -------------------------------------------------------------
  if (session.status === 'loading') {
    return (
      <div className="py-12 px-4 flex flex-col items-center justify-center text-center space-y-3">
        <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center animate-pulse">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
        <div>
          <h4 className="text-sm font-bold text-slate-800">
            正在加载微测验题目
          </h4>
          <p className="text-xs text-slate-500 mt-1">
            正在获取「{knowledgeName}」专项微测验，请稍候...
          </p>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // 异常状态: 题目加载失败
  // -------------------------------------------------------------
  if (session.status === 'error') {
    return (
      <div className="py-8 px-4 flex flex-col items-center justify-center text-center space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center">
          <AlertCircle className="w-6 h-6" />
        </div>
        <div className="space-y-1 max-w-sm">
          <h4 className="text-sm font-bold text-slate-900">
            微测验加载未就绪
          </h4>
          <p className="text-xs text-rose-600 leading-relaxed">
            {session.errorMessage || '无法加载当前知识点测验'}
          </p>
        </div>
        <div className="flex gap-2.5">
          {onBackToDetail && (
            <button
              type="button"
              onClick={onBackToDetail}
              className="py-2.5 px-4 rounded-xl border border-slate-200 text-slate-700 font-semibold text-xs hover:bg-slate-50 transition-colors cursor-pointer"
            >
              返回学情详情
            </button>
          )}
          <button
            type="button"
            onClick={handleRestart}
            className="py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-xs transition-colors cursor-pointer"
          >
            重试加载
          </button>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // 状态 G & H: 测验完成与结果结算
  // -------------------------------------------------------------
  if (session.status === 'completed' && summary) {
    const isPerfect = summary.accuracyPercent === 100;
    const isPassing = summary.accuracyPercent >= 60;

    return (
      <div className="space-y-5 py-2">
        {/* 顶部荣誉卡 */}
        <div
          className={`p-5 rounded-2xl border text-center space-y-2 ${
            isPerfect
              ? 'bg-emerald-50/80 border-emerald-200 text-emerald-950'
              : isPassing
              ? 'bg-indigo-50/80 border-indigo-200 text-indigo-950'
              : 'bg-amber-50/80 border-amber-200 text-amber-950'
          }`}
        >
          <div
            className={`w-12 h-12 mx-auto rounded-2xl flex items-center justify-center ${
              isPerfect
                ? 'bg-emerald-100 text-emerald-600'
                : isPassing
                ? 'bg-indigo-100 text-indigo-600'
                : 'bg-amber-100 text-amber-600'
            }`}
          >
            {isPerfect ? (
              <Sparkles className="w-6 h-6" />
            ) : isPassing ? (
              <Award className="w-6 h-6" />
            ) : (
              <HelpCircle className="w-6 h-6" />
            )}
          </div>
          <div>
            <h4 className="text-base font-bold">微测验突破完成</h4>
            <p className="text-xs opacity-80 mt-0.5">
              已完成「{knowledgeId} · {knowledgeName}」专项微测验评估
            </p>
          </div>
        </div>

        {/* 动态计算结果指标网格 */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
            <div className="text-[11px] text-slate-500 font-medium">本次正确率</div>
            <div
              className={`text-lg font-black mt-0.5 ${
                isPassing ? 'text-emerald-600' : 'text-rose-600'
              }`}
            >
              {summary.accuracyPercent}%
            </div>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
            <div className="text-[11px] text-slate-500 font-medium">答对题数</div>
            <div className="text-lg font-black text-slate-800 mt-0.5">
              {summary.correctCount} / {summary.totalQuestions}
            </div>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
            <div className="text-[11px] text-slate-500 font-medium">均题耗时</div>
            <div className="text-lg font-black text-slate-800 mt-0.5">
              {formatDuration(summary.averageTimeMs)}
            </div>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
            <div className="text-[11px] text-slate-500 font-medium">总计耗时</div>
            <div className="text-lg font-black text-slate-800 mt-0.5">
              {formatDuration(summary.totalTimeMs)}
            </div>
          </div>
        </div>

        {/* 答题明细回顾 */}
        <div className="space-y-2">
          <div className="text-xs font-bold text-slate-800 flex items-center justify-between">
            <span>作答回顾明细</span>
            <span className="text-slate-400 font-normal">
              共 {summary.totalQuestions} 题
            </span>
          </div>
          <div className="space-y-2">
            {session.records.map((rec, idx) => (
              <div
                key={rec.questionId}
                className="p-3 bg-white rounded-xl border border-slate-200/80 flex items-start justify-between gap-3 text-xs"
              >
                <div className="flex items-start gap-2">
                  <span className="mt-0.5">
                    {rec.isCorrect ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
                    )}
                  </span>
                  <div>
                    <div className="font-semibold text-slate-800">
                      第 {idx + 1} 题 ({rec.questionId})
                    </div>
                    <div className="text-slate-500 text-[11px] mt-0.5">
                      你的作答: <span className="font-bold">{rec.selectedOption}</span>
                      {!rec.isCorrect && (
                        <span className="ml-2 text-rose-600 font-semibold">
                          正确答案: {rec.correctOption}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1 text-[11px] text-slate-400 shrink-0">
                  <Clock className="w-3 h-3" />
                  <span>{formatDuration(rec.timeSpentMs)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 底部操作栏 */}
        <div className="pt-2 flex flex-col sm:flex-row items-center gap-2.5">
          <button
            type="button"
            onClick={handleRestart}
            className="w-full sm:w-auto flex-1 py-3 px-4 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer min-h-[44px]"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>重新测验</span>
          </button>
          <button
            type="button"
            onClick={onFinish}
            className="w-full sm:w-auto flex-1 py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer min-h-[44px]"
          >
            <span>返回学习</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // 状态 C, D, E, F: 题目作答与判题反馈
  // -------------------------------------------------------------
  const currentQ = session.questions[session.currentIndex];
  if (!currentQ) return null;

  const isAnswering = session.status === 'answering';
  const isSubmitting = session.status === 'submitting';
  const isFeedback = session.status === 'feedback';
  const isLastQuestion = session.currentIndex === session.questions.length - 1;

  return (
    <div className="space-y-4">
      {/* 测验顶栏: 题目序号与微进度 */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
        <div className="flex items-center gap-2">
          {onBackToDetail && isAnswering && session.currentIndex === 0 && (
            <button
              type="button"
              onClick={onBackToDetail}
              className="p-1.5 -ml-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
              title="返回知识点学情"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
          <div>
            <span className="text-[11px] font-bold text-indigo-600 uppercase tracking-wider">
              第 {session.currentIndex + 1} / {session.questions.length} 题
            </span>
            <h4 className="text-xs font-bold text-slate-800 leading-tight">
              {knowledgeId} · {knowledgeName}
            </h4>
          </div>
        </div>

        <div className="flex items-center gap-1 text-[11px] text-slate-400 font-mono">
          <span>难度</span>
          <span className="text-amber-500">{'★'.repeat(currentQ.difficulty)}</span>
        </div>
      </div>

      {/* 题干内容 */}
      <div className="p-3.5 bg-slate-50/90 rounded-2xl border border-slate-200/80">
        <div className="text-xs font-semibold text-slate-500 mb-1 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
          <span>选择题</span>
        </div>
        <p className="text-sm font-semibold text-slate-900 leading-relaxed whitespace-pre-line">
          {currentQ.stem}
        </p>
      </div>

      {/* 选项列表 (Mobile-First 交互，单手无障碍触控) */}
      <div className="space-y-2.5">
        {currentQ.options.map((option) => {
          const isSelected = session.selectedOption === option.key;

          // Feedback 状态下的智能高亮（只有服务端返回后才展示）
          let optionStyle =
            'bg-white border-slate-200 text-slate-800 hover:border-indigo-300 hover:bg-slate-50/60';

          if (isFeedback && session.lastFeedback) {
            const isCorrectAnswer = session.lastFeedback.correct_option === option.key;
            if (isCorrectAnswer) {
              optionStyle =
                'bg-emerald-50/90 border-emerald-500 text-emerald-950 font-bold ring-2 ring-emerald-200';
            } else if (isSelected && !session.lastFeedback.is_correct) {
              optionStyle =
                'bg-rose-50/90 border-rose-500 text-rose-950 line-through opacity-80';
            } else {
              optionStyle = 'bg-white border-slate-200 text-slate-400 opacity-60';
            }
          } else if (isSelected) {
            optionStyle =
              'bg-indigo-50 border-indigo-600 text-indigo-950 font-bold ring-2 ring-indigo-200 shadow-xs';
          }

          return (
            <button
              key={option.key}
              type="button"
              disabled={!isAnswering}
              onClick={() => handleSelectOption(option.key)}
              className={`w-full text-left p-3.5 rounded-xl border transition-all flex items-start gap-3 min-h-[48px] cursor-pointer disabled:cursor-default ${optionStyle}`}
            >
              <div
                className={`w-6 h-6 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 transition-colors ${
                  isSelected
                    ? isFeedback && session.lastFeedback?.correct_option === option.key
                      ? 'bg-emerald-600 text-white'
                      : isFeedback && !session.lastFeedback?.is_correct
                      ? 'bg-rose-600 text-white'
                      : 'bg-indigo-600 text-white'
                    : isFeedback && session.lastFeedback?.correct_option === option.key
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-100 text-slate-600'
                }`}
              >
                {option.key}
              </div>
              <div className="text-xs leading-relaxed flex-1 mt-0.5">
                {option.text}
              </div>
            </button>
          );
        })}
      </div>

      {/* 提交后服务端解析反馈区 (状态 E) */}
      {isFeedback && session.lastFeedback && (
        <div
          className={`p-4 rounded-2xl border space-y-2 animate-in fade-in slide-in-from-top-2 duration-300 ${
            session.lastFeedback.is_correct
              ? 'bg-emerald-50/60 border-emerald-200'
              : 'bg-rose-50/60 border-rose-200'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {session.lastFeedback.is_correct ? (
                <>
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  <span className="text-xs font-black text-emerald-900">
                    回答正确！掌握到位
                  </span>
                </>
              ) : (
                <>
                  <XCircle className="w-5 h-5 text-rose-600" />
                  <span className="text-xs font-black text-rose-900">
                    回答错误
                  </span>
                </>
              )}
            </div>
            <div className="text-xs font-bold text-slate-700">
              正确答案：
              <span className="text-emerald-700 font-black">
                {session.lastFeedback.correct_option}
              </span>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-200/50 text-xs text-slate-700 leading-relaxed">
            <span className="font-bold text-slate-900">【解析详解】</span>
            <p className="mt-1 whitespace-pre-line">
              {session.lastFeedback.explanation}
            </p>
          </div>
        </div>
      )}

      {/* 提交报错提示 */}
      {session.errorMessage && (
        <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{session.errorMessage}</span>
        </div>
      )}

      {/* 底部交互控制按钮 (防重提交与切换) */}
      <div className="pt-2">
        {isFeedback ? (
          <button
            type="button"
            onClick={handleNext}
            className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer min-h-[48px]"
          >
            <span>{isLastQuestion ? '查看本次测验结果' : '下一题'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            type="button"
            disabled={!canSubmitAnswer(session) || isSubmitting}
            onClick={handleSubmitAnswer}
            className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed text-white font-bold text-xs shadow-xs flex items-center justify-center gap-2 transition-all cursor-pointer min-h-[48px]"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>正在权威判题中...</span>
              </>
            ) : (
              <span>提交答案</span>
            )}
          </button>
        )}
      </div>
    </div>
  );
};
