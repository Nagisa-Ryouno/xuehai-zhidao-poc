import React, { useState, useMemo } from 'react';
import { Users, X } from 'lucide-react';
import type { TeacherOverviewResponse } from '../../types';
import { TeacherStudentTable } from './TeacherStudentTable';
import { getStudentDisplayName } from '../../utils/student';

interface TeacherStudentsTabProps {
  overview: TeacherOverviewResponse | null;
  isLoading: boolean;
  currentStudentId: string;
  onSelectStudentForDetail: (studentId: string) => void;
  onEnterStudentView: (studentId: string) => void;
}

export const TeacherStudentsTab: React.FC<TeacherStudentsTabProps> = ({
  overview,
  isLoading,
  currentStudentId,
  onSelectStudentForDetail,
  onEnterStudentView,
}) => {
  // 学生 Tab 本地筛选状态
  const [studentSearchQuery, setStudentSearchQuery] = useState<string>('');
  const [riskFilter, setRiskFilter] = useState<'ALL' | 'HEALTHY' | 'NORMAL' | 'ATTENTION'>('ALL');

  // 学生列表过滤（零排名、人本归纳，严格保持现有行为）
  const filteredStudents = useMemo(() => {
    if (!overview || !overview.students) return [];
    let list = overview.students;

    if (riskFilter !== 'ALL') {
      list = list.filter((s) => s.risk_level === riskFilter);
    }

    if (studentSearchQuery.trim()) {
      const q = studentSearchQuery.toLowerCase().trim();
      list = list.filter(
        (s) =>
          s.student_id.toLowerCase().includes(q) ||
          s.student_name.toLowerCase().includes(q) ||
          getStudentDisplayName(s.student_id, s.student_name).toLowerCase().includes(q) ||
          s.major.toLowerCase().includes(q)
      );
    }

    return list;
  }, [overview, riskFilter, studentSearchQuery]);

  const hasActiveFilters = riskFilter !== 'ALL' || studentSearchQuery.trim().length > 0;

  const handleResetFilters = () => {
    setRiskFilter('ALL');
    setStudentSearchQuery('');
  };

  return (
    <div className="space-y-6" data-testid="teacher-students-section">
      {/* 班级学生全览表与快速下钻 */}
      <div
        className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/90 shadow-2xs space-y-5"
        data-testid="teacher-student-roster"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-600" />
              班级学生学情档案花名册
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              基于客观答题与认知状态追踪，支持按学号/姓名检索及学情分类，坚持客观呈现与个体关怀
            </p>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {/* Risk Filter */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
              {(
                [
                  { id: 'ALL', label: '全部' },
                  { id: 'ATTENTION', label: '重点关注' },
                  { id: 'NORMAL', label: '学习推进中' },
                  { id: 'HEALTHY', label: '掌握良好' },
                ] as const
              ).map((rf) => (
                <button
                  key={rf.id}
                  type="button"
                  onClick={() => setRiskFilter(rf.id)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    riskFilter === rf.id
                      ? 'bg-white text-slate-900 shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {rf.label}
                </button>
              ))}
            </div>

            {/* Search Box */}
            <div className="relative w-48 sm:w-60">
              <input
                type="text"
                value={studentSearchQuery}
                onChange={(e) => setStudentSearchQuery(e.target.value)}
                placeholder="搜索学号 / 姓名 / 专业..."
                className="w-full pl-3.5 pr-8 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 transition-all"
                data-testid="teacher-student-search"
              />
              {studentSearchQuery && (
                <button
                  type="button"
                  onClick={() => setStudentSearchQuery('')}
                  className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-600 cursor-pointer"
                  title="清除搜索"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {hasActiveFilters && (
              <button
                type="button"
                onClick={handleResetFilters}
                className="px-2.5 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl font-medium transition-colors cursor-pointer"
              >
                重置筛选
              </button>
            )}
          </div>
        </div>

        {/* 学生表格 */}
        <TeacherStudentTable
          students={filteredStudents}
          currentStudentId={currentStudentId}
          isLoading={isLoading && !overview}
          onSelectStudentForDetail={onSelectStudentForDetail}
          onEnterStudentView={onEnterStudentView}
          onResetFilters={handleResetFilters}
          hasActiveFilters={hasActiveFilters}
        />
      </div>
    </div>
  );
};
