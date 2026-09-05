import React from 'react';
import {
  Sparkles,
  CalendarCheck,
  CheckCircle2,
  Clock,
  HelpCircle,
  TrendingUp,
} from 'lucide-react';
import type { DailyLearningPlan } from '../types';

interface AISummaryProps {
  aiSummary: string;
  dailyPlan: DailyLearningPlan;
  optimizationSuggestions: string[];
}

export const AISummary: React.FC<AISummaryProps> = ({
  aiSummary,
  dailyPlan,
  optimizationSuggestions,
}) => {
  return (
    <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200/80 shadow-xs space-y-6">
      {/* Section Header */}
      <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
        <div className="p-2 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-500/20">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-900">
            AI 学习建议与行动方案
          </h2>
          <p className="text-xs text-slate-500">
            综合学情诊断推导的个性化提分策略与日常学习节奏建议
          </p>
        </div>
      </div>

      {/* Main AI Summary Block */}
      <div className="rounded-2xl bg-gradient-to-r from-indigo-50/70 via-violet-50/40 to-slate-50 border border-indigo-100/90 p-5 sm:p-6 shadow-2xs">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-xl bg-white text-indigo-600 shadow-2xs shrink-0 mt-0.5">
            <Sparkles className="w-4 h-4" />
          </div>
          <div className="space-y-1.5">
            <span className="text-xs font-bold text-indigo-900 tracking-wider uppercase">
              AI 专家综合学情评语
            </span>
            <p className="text-sm text-slate-700 leading-relaxed font-medium">
              {aiSummary}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Daily Plan Card */}
        <div className="bg-slate-50/80 rounded-xl p-5 border border-slate-200/80 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3 text-indigo-700 font-bold text-xs">
              <CalendarCheck className="w-4 h-4" />
              <span>今日推荐学习节奏</span>
            </div>

            <div className="space-y-3 my-2">
              <div className="bg-white rounded-lg p-3 border border-slate-200/60 flex items-center justify-between">
                <span className="text-xs text-slate-500 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  建议专注投入
                </span>
                <span className="text-sm font-extrabold text-slate-900">
                  {dailyPlan.recommended_minutes} 分钟/天
                </span>
              </div>

              <div className="bg-white rounded-lg p-3 border border-slate-200/60 flex items-center justify-between">
                <span className="text-xs text-slate-500 flex items-center gap-1.5">
                  <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
                  精选习题量
                </span>
                <span className="text-sm font-extrabold text-slate-900">
                  {dailyPlan.recommended_questions} 道题/天
                </span>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-slate-200/70 text-xs">
            <span className="text-slate-400 block text-[11px] mb-0.5">突破重心</span>
            <span className="font-bold text-indigo-900 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200/60 inline-block">
              {dailyPlan.focus}
            </span>
          </div>
        </div>

        {/* Dynamic Optimization Suggestions */}
        <div className="lg:col-span-2 bg-slate-50/80 rounded-xl p-5 border border-slate-200/80">
          <div className="flex items-center gap-2 mb-3 text-slate-800 font-bold text-xs">
            <TrendingUp className="w-4 h-4 text-emerald-600" />
            <span>下一步精准提分与复习指南</span>
          </div>

          <div className="space-y-2.5">
            {optimizationSuggestions && optimizationSuggestions.length > 0 ? (
              optimizationSuggestions.map((sug, idx) => (
                <div
                  key={idx}
                  className="bg-white rounded-lg p-3 border border-slate-200/70 flex items-start gap-2.5 shadow-2xs"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                  <p className="text-xs text-slate-700 leading-relaxed font-medium">
                    {sug}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500">
                暂无进一步的优化建议，请按照当前学习路径循序渐进。
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
