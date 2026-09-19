import React, { useState, useEffect } from 'react';
import {
  createPretestSession,
  submitPretest,
} from '../../api';
import type {
  PretestSession,
  DiagnosticResult,
  DynamicLearningRoute,
} from '../../types';

interface PretestModalProps {
  isOpen: boolean;
  onClose: () => void;
  studentId: string;
  learningGoal?: string;
  onRouteGenerated?: (route: DynamicLearningRoute) => void;
  onSelectFocus?: (knowledgeId: string) => void;
}

export const PretestModal: React.FC<PretestModalProps> = ({
  isOpen,
  onClose,
  studentId,
  learningGoal,
  onRouteGenerated,
  onSelectFocus,
}) => {
  const [session, setSession] = useState<PretestSession | null>(null);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [result, setResult] = useState<{
    diagnostic: DiagnosticResult;
    dynamic_route: DynamicLearningRoute;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 打开弹窗时初始化前测会话
  useEffect(() => {
    if (isOpen) {
      setResult(null);
      setCurrentIndex(0);
      setAnswers({});
      setError(null);
      setLoading(true);
      createPretestSession(studentId, learningGoal)
        .then((sess) => {
          setSession(sess);
          setLoading(false);
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : '创建前测失败');
          setLoading(false);
        });
    }
  }, [isOpen, studentId, learningGoal]);

  if (!isOpen) return null;

  const questions = session?.questions || [];
  const currentQuestion = questions[currentIndex];
  const isLastQuestion = currentIndex === questions.length - 1;
  const currentSelectedOption = currentQuestion ? answers[currentQuestion.question_id] : '';

  const handleSelectOption = (key: string) => {
    if (!currentQuestion) return;
    setAnswers((prev) => ({
      ...prev,
      [currentQuestion.question_id]: key,
    }));
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((prev) => prev + 1);
    }
  };

  const handleSubmit = async () => {
    if (!session) return;
    setAnalyzing(true);
    setError(null);
    try {
      const res = await submitPretest(session.session_id, answers);
      setResult(res);
      setAnalyzing(false);
      if (onRouteGenerated) {
        onRouteGenerated(res.dynamic_route);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交前测失败');
      setAnalyzing(false);
    }
  };

  const handleStartFocus = () => {
    if (result && result.dynamic_route.steps.length > 0) {
      const firstKid = result.dynamic_route.steps[0].knowledge_id;
      if (onSelectFocus) {
        onSelectFocus(firstKid);
      }
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-100 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-blue-50/50 via-indigo-50/30 to-purple-50/50">
          <div className="flex items-center space-x-2">
            <span className="text-xl">🎯</span>
            <div>
              <h3 className="text-lg font-bold text-slate-900">
                3题极速前测 · 学情诊断与动态航线
              </h3>
              <p className="text-xs text-slate-500">
                跨越先修拓扑链路，精确定位认知基线与盲区
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 rounded-lg p-1.5 hover:bg-slate-100 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex-1">
          {error && (
            <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-lg flex items-center space-x-2">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {loading && (
            <div className="py-12 flex flex-col items-center justify-center space-y-3">
              <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-slate-500">正在生成前测诊断题目...</p>
            </div>
          )}

          {analyzing && (
            <div className="py-12 flex flex-col items-center justify-center space-y-4">
              <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <div className="text-center">
                <p className="text-base font-semibold text-slate-800">
                  正在对标知识图谱进行多维学情诊断...
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  依据认知追踪模型与拓扑依赖重新规划自适应攻坚路线
                </p>
              </div>
            </div>
          )}

          {/* 阶段 1: 测验答题界面 */}
          {!loading && !analyzing && !result && currentQuestion && (
            <div className="space-y-6">
              {/* 进度指示 */}
              <div>
                <div className="flex justify-between items-center text-xs font-semibold text-slate-500 mb-2">
                  <span>
                    第 <span className="text-indigo-600 font-bold">{currentIndex + 1}</span> 题 / 共 {questions.length} 题
                  </span>
                  <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full border border-indigo-100 text-xs">
                    考点: {currentQuestion.knowledge_name} ({currentQuestion.knowledge_id})
                  </span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-600 transition-all duration-300 rounded-full"
                    style={{
                      width: `${((currentIndex + 1) / questions.length) * 100}%`,
                    }}
                  />
                </div>
              </div>

              {/* 题干 */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                <p className="text-base font-medium text-slate-900 leading-relaxed">
                  {currentQuestion.stem}
                </p>
              </div>

              {/* 选项列表 */}
              <div className="space-y-3">
                {currentQuestion.options.map((option) => {
                  const isSelected = currentSelectedOption === option.key;
                  return (
                    <button
                      key={option.key}
                      onClick={() => handleSelectOption(option.key)}
                      className={`w-full text-left p-4 rounded-xl border transition-all flex items-start space-x-3 ${
                        isSelected
                          ? 'border-indigo-600 bg-indigo-50/50 shadow-sm ring-1 ring-indigo-500'
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/80'
                      }`}
                    >
                      <span
                        className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                          isSelected
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-200 text-slate-700'
                        }`}
                      >
                        {option.key}
                      </span>
                      <span className="text-sm text-slate-800 leading-snug">
                        {option.text}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* 底部按钮 */}
              <div className="pt-2 flex justify-end space-x-3">
                {currentIndex > 0 && (
                  <button
                    onClick={() => setCurrentIndex((prev) => prev - 1)}
                    className="px-4 py-2 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
                  >
                    上一题
                  </button>
                )}
                {isLastQuestion ? (
                  <button
                    onClick={handleSubmit}
                    disabled={!currentSelectedOption}
                    className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-xl shadow-sm transition-colors"
                  >
                    提交并生成诊断报告
                  </button>
                ) : (
                  <button
                    onClick={handleNext}
                    disabled={!currentSelectedOption}
                    className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-xl shadow-sm transition-colors"
                  >
                    下一题
                  </button>
                )}
              </div>
            </div>
          )}

          {/* 阶段 2: 诊断报告与动态路线展示 */}
          {!loading && !analyzing && result && (
            <div className="space-y-6">
              {/* 诊断卡片 */}
              <div className="p-5 bg-gradient-to-br from-indigo-50/60 via-purple-50/40 to-blue-50/60 rounded-2xl border border-indigo-100">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-2xl">
                      {result.diagnostic.overall_level === 'SOLID_FOUNDATION'
                        ? '🌟'
                        : result.diagnostic.overall_level === 'PARTIAL_FOUNDATION'
                        ? '💡'
                        : '🌱'}
                    </span>
                    <div>
                      <h4 className="font-bold text-slate-900 text-base">
                        诊断结论：{result.diagnostic.overall_level_label}
                      </h4>
                      <p className="text-xs text-slate-500">
                        前测得分: {result.diagnostic.correct_count} / {result.diagnostic.total_questions} (正确率 {Math.round(result.diagnostic.accuracy * 100)}%)
                      </p>
                    </div>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold ${
                      result.diagnostic.overall_level === 'SOLID_FOUNDATION'
                        ? 'bg-emerald-100 text-emerald-800'
                        : result.diagnostic.overall_level === 'PARTIAL_FOUNDATION'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    {result.diagnostic.overall_level_label}
                  </span>
                </div>
                <p className="text-sm text-slate-700 leading-relaxed">
                  {result.diagnostic.summary_text}
                </p>

                {/* 盲区提示 */}
                {result.diagnostic.weaknesses.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-indigo-100/60 flex items-center space-x-2 text-xs">
                    <span className="font-semibold text-rose-700">待强化盲区:</span>
                    <div className="flex flex-wrap gap-1">
                      {result.diagnostic.weaknesses.map((w) => (
                        <span key={w} className="px-2 py-0.5 bg-rose-50 border border-rose-200 text-rose-700 rounded text-xs">
                          {w}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* 动态路线卡片 (Top-3) */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">🗺️</span>
                    <h4 className="font-bold text-slate-900 text-sm">
                      自适应攻坚航线 (Top-{result.dynamic_route.route_length})
                    </h4>
                  </div>
                  <span className="text-xs text-slate-400">
                    严格前置拓扑优先 · 动态重规划
                  </span>
                </div>

                <div className="space-y-3">
                  {result.dynamic_route.steps.map((step) => {
                    const isCurrent = step.role === 'CURRENT';
                    const isNext = step.role === 'NEXT';
                    return (
                      <div
                        key={step.knowledge_id}
                        className={`p-4 rounded-xl border transition-all ${
                          isCurrent
                            ? 'bg-emerald-50/40 border-emerald-300 ring-1 ring-emerald-200'
                            : isNext
                            ? 'bg-amber-50/30 border-amber-200'
                            : 'bg-slate-50/60 border-slate-200'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center space-x-2">
                            <span
                              className={`px-2 py-0.5 rounded text-xs font-bold ${
                                isCurrent
                                  ? 'bg-emerald-600 text-white'
                                  : isNext
                                  ? 'bg-amber-500 text-white'
                                  : 'bg-purple-600 text-white'
                              }`}
                            >
                              第 {step.rank} 站 ·{' '}
                              {isCurrent ? '当前焦点' : isNext ? '紧接学习' : '进阶延伸'}
                            </span>
                            <span className="font-bold text-slate-900 text-sm">
                              {step.knowledge_name}
                            </span>
                            <span className="text-xs text-slate-400">
                              ({step.knowledge_id})
                            </span>
                          </div>
                          <span className="text-xs font-medium text-slate-500">
                            当前掌握度: {(step.mastery * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed">
                          {step.explanation}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 底部行动 CTA */}
              <div className="pt-2 flex justify-end space-x-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  稍后学习
                </button>
                <button
                  onClick={handleStartFocus}
                  className="px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white text-sm font-bold rounded-xl shadow-md transition-all flex items-center space-x-1.5"
                >
                  <span>🚀 立即攻坚首站任务</span>
                  {result.dynamic_route.steps.length > 0 && (
                    <span>({result.dynamic_route.steps[0].knowledge_id})</span>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
