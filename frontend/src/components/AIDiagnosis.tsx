import React from 'react';
import {
  Brain,
  Sparkles,
  AlertCircle,
  Lightbulb,
  CheckCircle2,
  Bot,
} from 'lucide-react';
import type { ReportDiagnosis } from '../types';

interface AIDiagnosisProps {
  diagnosis: ReportDiagnosis;
  profileDiagnosis: string[];
}

export const AIDiagnosis: React.FC<AIDiagnosisProps> = ({
  diagnosis,
  profileDiagnosis,
}) => {
  return (
    <div className="glass-card rounded-2xl p-6 relative overflow-hidden flex flex-col justify-between h-full">
      {/* Decorative subtle ambient light */}
      <div className="absolute top-0 right-0 w-36 h-36 bg-gradient-to-bl from-indigo-500/10 to-transparent rounded-bl-full pointer-events-none" />

      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-[#F2764A] to-[#E2573F] text-white shadow-sm shadow-indigo-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h2 className="text-base font-bold text-slate-900">AI 学情智能诊断</h2>
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-violet-500"></span>
                </span>
              </div>
              <p className="text-xs text-slate-500">基于多轮知识图谱与错因归因分析</p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/70">
            <Sparkles className="w-3 h-3 text-indigo-500" />
            智能诊断就绪
          </span>
        </div>

        {/* Core Diagnosis Narrative */}
        <div className="space-y-3 mb-5">
          {/* Mastery Evaluation */}
          <div className="glass-card rounded-xl p-3.5">
            <div className="flex items-start gap-2.5">
              <Brain className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
              <div>
                <span className="text-xs font-bold text-slate-800">掌握评价：</span>
                <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                  {diagnosis.mastery_description}
                </p>
              </div>
            </div>
          </div>

          {/* Behavior Pattern */}
          <div className="glass-card rounded-xl p-3.5">
            <div className="flex items-start gap-2.5">
              <Lightbulb className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <span className="text-xs font-bold text-slate-800">学习行为：</span>
                <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                  {diagnosis.behavior_description}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Diagnosis Bullets / Problems */}
        <div>
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-2">
            核心诊断发现
          </span>
          <div className="space-y-1.5">
            {profileDiagnosis && profileDiagnosis.length > 0 ? (
              profileDiagnosis.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2 text-xs text-slate-700 bg-white/60 px-2.5 py-1.5 rounded-lg border border-slate-100"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-indigo-500 shrink-0 mt-0.5" />
                  <span className="leading-normal">{item}</span>
                </div>
              ))
            ) : (
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span>学习状态保持良好，无系统性薄弱项</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottlenecks Stats Footer */}
      <div className="pt-4 mt-4 border-t border-indigo-100/80 flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5 text-slate-600">
          <AlertCircle className="w-4 h-4 text-rose-500" />
          <span>重点突破薄弱点：</span>
          <strong className="text-rose-600 font-bold">
            {diagnosis.weak_knowledge_count} 个
          </strong>
        </div>
        <div className="text-slate-500 text-[11px]">
          关联前置链：
          <span className="font-semibold text-slate-700">
            {diagnosis.prerequisite_knowledge_count} 项知识
          </span>
        </div>
      </div>
    </div>
  );
};
