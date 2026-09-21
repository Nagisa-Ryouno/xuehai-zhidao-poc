import React from 'react';
import { CheckCircle2, Users, ArrowRight } from 'lucide-react';
import type { TeacherOverviewResponse } from '../../types';
import { TeacherKPIGrid } from './TeacherKPIGrid';
import { TeacherWeakKnowledgeCard } from './TeacherWeakKnowledgeCard';

interface TeacherOverviewTabProps {
  overview: TeacherOverviewResponse | null;
  isLoading: boolean;
  studentsCount: number;
  onNavigateToKnowledge: () => void;
  onNavigateToStudents: () => void;
}

export const TeacherOverviewTab: React.FC<TeacherOverviewTabProps> = ({
  overview,
  isLoading,
  studentsCount,
  onNavigateToKnowledge,
  onNavigateToStudents,
}) => {
  const kpis = overview?.class_kpis || {
    total_students: overview?.students?.length || studentsCount || 0,
    active_students: 0,
    class_avg_mastery: 0,
    at_risk_students_count: 0,
  };

  const weakPoints = overview?.weak_knowledge_points || [];

  return (
    <div className="space-y-6" data-testid="teacher-overview-section">
      {/* 4 大核心班级全景统计 KPI 卡片 */}
      <TeacherKPIGrid kpis={kpis} isLoading={isLoading && !overview} />

      {/* 班级重点瓶颈考点关注 */}
      <TeacherWeakKnowledgeCard
        weakPoints={weakPoints}
        isLoading={isLoading && !overview}
        onViewAllKnowledge={onNavigateToKnowledge}
      />

      {/* 教学决策参考导向卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gradient-to-br from-indigo-50/70 to-blue-50/50 rounded-2xl p-6 border border-indigo-100 space-y-3">
          <div className="flex items-center gap-2 text-indigo-900 font-bold text-sm">
            <CheckCircle2 className="w-4 h-4 text-indigo-600" />
            教学行动建议引导
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            当前班级在「需求价格弹性」及「供求均衡」考点有较集中的错误反馈，建议安排针对性例题精讲或布置专题微练。
          </p>
          <div className="pt-2">
            <button
              type="button"
              onClick={onNavigateToKnowledge}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all cursor-pointer inline-flex items-center gap-1.5"
            >
              查看 30 考点明细
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="bg-gradient-to-br from-emerald-50/70 to-teal-50/50 rounded-2xl p-6 border border-emerald-100 space-y-3">
          <div className="flex items-center gap-2 text-emerald-900 font-bold text-sm">
            <Users className="w-4 h-4 text-emerald-600" />
            学生个体学情关怀
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            已有 {kpis.total_students - kpis.at_risk_students_count} 名学子处于掌握良好或稳步推进区间。建议对重点关注学子进行个体档案下钻分析。
          </p>
          <div className="pt-2">
            <button
              type="button"
              onClick={onNavigateToStudents}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all cursor-pointer inline-flex items-center gap-1.5"
            >
              调阅学生花名册
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
