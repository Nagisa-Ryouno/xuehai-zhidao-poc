import React from 'react';
import {
  Flame,
  Sparkles,
  Trophy,
  Target,
  Compass,
  Clock,
  BookMarked,
} from 'lucide-react';
import type { LearningPathStep } from '../types';

interface LearningPathProps {
  learningPath: LearningPathStep[];
  recommendationType: string;
  studentName: string;
}

export const LearningPath: React.FC<LearningPathProps> = ({
  learningPath,
  recommendationType,
  studentName,
}) => {
  // Priority badge styling helper
  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case '高':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case '中':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case '低':
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  // Source badge styling helper
  const getSourceStyle = (source?: string) => {
    if (source === '前置知识') {
      return 'bg-amber-50 text-amber-700 border-amber-200';
    }
    return 'bg-blue-50 text-blue-700 border-blue-200';
  };

  return (
    <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200/80 shadow-xs space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-5 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 text-white shadow-md shadow-indigo-500/20">
            <Compass className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-slate-900">
                AI 为你生成的学习路径
              </h2>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                {recommendationType}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              根据你的知识掌握情况与知识依赖关系动态生成最优攻坚时序
            </p>
          </div>
        </div>

        {learningPath.length > 0 && (
          <div className="flex items-center gap-2 text-xs font-medium text-slate-500 self-start sm:self-auto bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
            <Flame className="w-4 h-4 text-amber-500" />
            <span>规划共推进</span>
            <strong className="text-indigo-600 font-bold">
              {learningPath.length} 个知识节点
            </strong>
          </div>
        )}
      </div>

      {/* S004 Special Case: Empty Path with High Mastery */}
      {learningPath.length === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-emerald-200 bg-gradient-to-b from-emerald-50/40 via-white to-indigo-50/20 p-8 sm:p-10 text-center space-y-6">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-white flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Trophy className="w-8 h-8" />
          </div>

          <div className="max-w-xl mx-auto space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 bg-emerald-100/60 px-3 py-1 rounded-full">
              卓越学情评估
            </span>
            <h3 className="text-2xl font-black text-slate-900">
              🎉 当前没有明显薄弱知识点
            </h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              {studentName}同学的基础概念掌握非常扎实，当前无需进行零散的基础概念补差。
              系统建议进入「<strong className="text-indigo-600 font-bold">综合能力提升阶段</strong>」，聚焦解题速度与高阶迁移突破！
            </p>
          </div>

          {/* Advancement Training Direction Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-left max-w-4xl mx-auto pt-2">
            <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition-all">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center mb-2.5">
                <Target className="w-4 h-4" />
              </div>
              <h4 className="text-xs font-bold text-slate-800 mb-1">
                1. 综合应用题演练
              </h4>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                强化弹性与福利、税收归宿交叉大题的多步计算推导。
              </p>
            </div>

            <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition-all">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center mb-2.5">
                <Sparkles className="w-4 h-4" />
              </div>
              <h4 className="text-xs font-bold text-slate-800 mb-1">
                2. 跨知识点综合训练
              </h4>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                打通供求理论与消费者最优均衡，训练宏微观联动思考。
              </p>
            </div>

            <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition-all">
              <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center mb-2.5">
                <Clock className="w-4 h-4" />
              </div>
              <h4 className="text-xs font-bold text-slate-800 mb-1">
                3. 限时模拟提速
              </h4>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                针对目前答题耗时 168 秒的特征，进行高强度限时模拟训练。
              </p>
            </div>

            <div className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-2xs hover:border-emerald-300 hover:shadow-xs transition-all">
              <div className="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center mb-2.5">
                <BookMarked className="w-4 h-4" />
              </div>
              <h4 className="text-xs font-bold text-slate-800 mb-1">
                4. 高难度知识挑战
              </h4>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                挑战完全竞争与垄断市场的长期均衡推导等深度拔高考点。
              </p>
            </div>
          </div>
        </div>
      ) : (
        /* Timeline Roadmap View */
        <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 sm:before:left-4 before:top-4 before:bottom-4 before:w-0.5 before:bg-gradient-to-b before:from-indigo-500 before:via-violet-400 before:to-slate-200">
          {learningPath.map((step) => {
            const isHighPriority = step.priority === '高';
            return (
              <div key={step.stage} className="relative group">
                {/* Step Circle Marker */}
                <div
                  className={`absolute -left-6 sm:-left-8 top-1.5 w-6 h-6 sm:w-8 sm:h-8 rounded-full flex items-center justify-center font-mono font-bold text-xs shadow-sm transition-transform group-hover:scale-110 ${
                    isHighPriority
                      ? 'bg-gradient-to-tr from-rose-500 to-indigo-600 text-white ring-4 ring-rose-50'
                      : 'bg-indigo-600 text-white ring-4 ring-indigo-50'
                  }`}
                >
                  {String(step.stage).padStart(2, '0')}
                </div>

                {/* Step Card */}
                <div className="bg-slate-50/70 hover:bg-white rounded-2xl p-5 border border-slate-200/90 hover:border-indigo-300 hover:shadow-md transition-all">
                  {/* Step Card Header */}
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md border border-indigo-200/50">
                        {step.knowledge_id}
                      </span>
                      <h3 className="text-base font-bold text-slate-900">
                        {step.knowledge_name}
                      </h3>
                      <span className="text-xs text-slate-400">
                        · {step.chapter}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      {step.source && (
                        <span
                          className={`text-[11px] font-semibold px-2 py-0.5 rounded-md border ${getSourceStyle(
                            step.source
                          )}`}
                        >
                          {step.source}
                        </span>
                      )}
                      <span
                        className={`text-[11px] font-bold px-2 py-0.5 rounded-md border ${getPriorityStyle(
                          step.priority
                        )}`}
                      >
                        优先级：{step.priority} ({step.priority_score.toFixed(1)}分)
                      </span>
                    </div>
                  </div>

                  {/* Accuracy & Learning Goal */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-3">
                    <div className="bg-white/80 rounded-xl p-2.5 border border-slate-200/70">
                      <span className="text-[11px] text-slate-500 block">
                        当前掌握正确率
                      </span>
                      <span
                        className={`text-lg font-black ${
                          step.current_accuracy < 60
                            ? 'text-rose-600'
                            : 'text-amber-600'
                        }`}
                      >
                        {step.current_accuracy.toFixed(1)}%
                      </span>
                    </div>

                    <div className="md:col-span-2 bg-white/80 rounded-xl p-2.5 border border-slate-200/70 flex items-center gap-2">
                      <Target className="w-4 h-4 text-indigo-500 shrink-0" />
                      <div>
                        <span className="text-[11px] text-slate-500 block">
                          阶段学习目标
                        </span>
                        <span className="text-xs font-semibold text-slate-800">
                          {step.learning_goal}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* AI Recommendation Reason */}
                  <div className="bg-indigo-50/40 rounded-xl p-3 border border-indigo-100/70 text-xs">
                    <div className="flex items-start gap-2">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-600 shrink-0 mt-0.5" />
                      <div className="text-slate-700 leading-relaxed">
                        <strong className="text-indigo-900 font-bold">
                          AI推荐依据：
                        </strong>
                        {step.reason}
                      </div>
                    </div>
                    {step.description && (
                      <p className="text-[11px] text-slate-500 mt-1 pl-5.5">
                        重点考核内容：{step.description}
                      </p>
                    )}
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
