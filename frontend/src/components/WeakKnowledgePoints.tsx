import React, { useState } from 'react';
import {
  AlertTriangle,
  Clock,
  Award,
  GitFork,
  ChevronDown,
  ChevronUp,
  CheckCircle,
} from 'lucide-react';
import type {
  WeakKnowledgePoint,
  PrerequisiteKnowledgePoint,
} from '../types';

interface WeakKnowledgePointsProps {
  weakPoints: WeakKnowledgePoint[];
  prerequisitePoints: PrerequisiteKnowledgePoint[];
}

export const WeakKnowledgePoints: React.FC<WeakKnowledgePointsProps> = ({
  weakPoints,
  prerequisitePoints,
}) => {
  const [showAll, setShowAll] = useState(false);

  // Risk classification helper
  const getRiskLevel = (accuracy: number) => {
    if (accuracy < 60) {
      return {
        label: '高风险',
        badgeClass: 'bg-rose-50 text-rose-700 border-rose-200',
        barColor: 'bg-rose-500',
        textColor: 'text-rose-600',
      };
    }
    if (accuracy <= 70) {
      return {
        label: '需要加强',
        badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
        barColor: 'bg-amber-500',
        textColor: 'text-amber-600',
      };
    }
    return {
      label: '基本掌握',
      badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      barColor: 'bg-emerald-500',
      textColor: 'text-emerald-600',
    };
  };

  const visiblePoints = showAll ? weakPoints : weakPoints.slice(0, 6);

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-rose-50 text-rose-600">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">需要重点关注</h2>
            <p className="text-xs text-slate-500">
              当前识别出 {weakPoints.length} 个薄弱知识模块与 {prerequisitePoints.length} 项关联前置依赖
            </p>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1 text-slate-600">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
            &lt;60% 高风险
          </span>
          <span className="flex items-center gap-1 text-slate-600">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            60~70% 需加强
          </span>
          <span className="flex items-center gap-1 text-slate-600">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            &ge;70% 基本掌握
          </span>
        </div>
      </div>

      {/* Weak Points Card List */}
      {weakPoints.length === 0 ? (
        <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-6 text-center space-y-2">
          <div className="w-12 h-12 mx-auto rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
            <CheckCircle className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-emerald-900">
            太棒了！当前没有明显薄弱知识点
          </h3>
          <p className="text-xs text-emerald-700 max-w-md mx-auto">
            系统未检测到正确率低于 60% 的基础知识点，所有模块均保持在优良水平。建议直接推进综合能力拔高训练！
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {visiblePoints.map((item) => {
            const risk = getRiskLevel(item.accuracy);
            return (
              <div
                key={item.knowledge_id}
                className="bg-slate-50/60 hover:bg-white rounded-xl p-4 border border-slate-200/80 hover:border-slate-300 hover:shadow-sm transition-all flex flex-col justify-between"
              >
                <div>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <span className="text-[10px] font-mono font-bold text-slate-400">
                        {item.knowledge_id}
                      </span>
                      <h4 className="text-sm font-bold text-slate-800 leading-snug">
                        {item.knowledge_name}
                      </h4>
                    </div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-md border shrink-0 ${risk.badgeClass}`}
                    >
                      {risk.label}
                    </span>
                  </div>

                  {/* Accuracy Bar */}
                  <div className="space-y-1.5 my-3">
                    <div className="flex justify-between items-baseline text-xs">
                      <span className="text-slate-500 font-medium">答题正确率</span>
                      <span className={`font-black text-sm ${risk.textColor}`}>
                        {item.accuracy.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-200/80 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${risk.barColor}`}
                        style={{ width: `${Math.min(100, Math.max(5, item.accuracy))}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Card Meta & Prereqs */}
                <div className="pt-3 border-t border-slate-200/60 space-y-2">
                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span className="flex items-center gap-1">
                      <Award className="w-3.5 h-3.5 text-slate-400" />
                      测验分: {item.assessment_score.toFixed(0)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      均耗: {item.average_time_seconds.toFixed(0)}秒
                    </span>
                    <span className="text-slate-400">
                      难度: {'★'.repeat(item.difficulty)}
                    </span>
                  </div>

                  {item.prerequisite && item.prerequisite.length > 0 && (
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                      <GitFork className="w-3 h-3 text-indigo-500 shrink-0" />
                      <span className="shrink-0 text-slate-400">前置依托:</span>
                      <div className="flex flex-wrap gap-1">
                        {item.prerequisite.map((preId) => (
                          <span
                            key={preId}
                            className="px-1.5 py-0.2 rounded bg-indigo-50 text-indigo-700 text-[10px] font-mono font-semibold"
                          >
                            {preId}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Show More Button if > 6 items */}
      {weakPoints.length > 6 && (
        <div className="text-center pt-2">
          <button
            onClick={() => setShowAll(!showAll)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100/80 px-4 py-1.5 rounded-lg transition-colors cursor-pointer"
          >
            {showAll ? (
              <>
                收起部分薄弱点 <ChevronUp className="w-4 h-4" />
              </>
            ) : (
              <>
                查看全部 {weakPoints.length} 个薄弱知识点 <ChevronDown className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      )}

      {/* Prerequisite Knowledge Dependency Block */}
      {prerequisitePoints && prerequisitePoints.length > 0 && (
        <div className="bg-slate-50/70 rounded-xl p-4 border border-slate-200/80">
          <div className="flex items-center gap-2 mb-3">
            <GitFork className="w-4 h-4 text-indigo-600" />
            <h4 className="text-xs font-bold text-slate-800">
              知识链路追溯 —— 关键前置知识诊断
            </h4>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {prerequisitePoints.map((pre, idx) => (
              <div
                key={idx}
                className="bg-white rounded-lg p-2.5 border border-slate-200 text-xs flex flex-col justify-between"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-[10px] font-bold text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                      {pre.knowledge_id}
                    </span>
                    <span className="font-bold text-slate-800">
                      {pre.knowledge_name}
                    </span>
                  </div>
                  <span className="text-[11px] font-semibold text-slate-500">
                    当前掌握度：
                    {pre.accuracy !== null ? (
                      <strong className="text-indigo-600">
                        {pre.accuracy.toFixed(1)}%
                      </strong>
                    ) : (
                      <span className="text-amber-600">尚无学习记录</span>
                    )}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 leading-snug">
                  {pre.reason}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
