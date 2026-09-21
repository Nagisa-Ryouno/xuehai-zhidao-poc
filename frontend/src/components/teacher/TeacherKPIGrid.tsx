import React from 'react';
import { Users, TrendingUp, Layers, AlertTriangle } from 'lucide-react';
import type { TeacherClassKPIs } from '../../types';

interface TeacherKPIGridProps {
  kpis: TeacherClassKPIs;
  isLoading?: boolean;
}

export const TeacherKPIGrid: React.FC<TeacherKPIGridProps> = ({ kpis, isLoading = false }) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" data-testid="teacher-kpi-cards">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-2xs space-y-3 animate-pulse"
          >
            <div className="h-4 bg-slate-200 rounded-md w-24" />
            <div className="h-8 bg-slate-200 rounded-md w-16" />
            <div className="h-3 bg-slate-100 rounded-md w-32" />
          </div>
        ))}
      </div>
    );
  }

  const activeRate = ((kpis.active_students / (kpis.total_students || 1)) * 100).toFixed(0);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" data-testid="teacher-kpi-cards">
      {/* KPI 1: 班级总学生数 */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-2xs space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500">班级建档学生数</span>
          <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Users className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-black text-slate-900 font-mono">
            {kpis.total_students}
          </span>
          <span className="text-xs text-slate-400">名注册学子</span>
        </div>
        <p className="text-[11px] text-slate-400">已完整建立认知状态基线</p>
      </div>

      {/* KPI 2: 近7天活跃学子 */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-2xs space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500">近 7 天活跃学生</span>
          <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <TrendingUp className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-black text-emerald-600 font-mono">
            {kpis.active_students}
          </span>
          <span className="text-xs text-slate-400">名有练习记录</span>
        </div>
        <p className="text-[11px] text-slate-400">
          活跃率 {activeRate}%
        </p>
      </div>

      {/* KPI 3: 全班平均掌握度 */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-2xs space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500">全班平均掌握度</span>
          <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <Layers className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-black text-indigo-700 font-mono">
            {(kpis.class_avg_mastery * 100).toFixed(1)}%
          </span>
          <span className="text-xs text-slate-400">全班均值</span>
        </div>
        <p className="text-[11px] text-slate-400">全站统一达标门槛 80%</p>
      </div>

      {/* KPI 4: 重点关注学生数 */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/90 shadow-2xs space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500">重点关注学生数</span>
          <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
            <AlertTriangle className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-black text-rose-600 font-mono">
            {kpis.at_risk_students_count}
          </span>
          <span className="text-xs text-slate-400">名需干预</span>
        </div>
        <p className="text-[11px] text-rose-500 font-medium">掌握度 &lt; 60% 或低正确率</p>
      </div>
    </div>
  );
};
