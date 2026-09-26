import React from 'react';
import type { TeacherStudentSummary } from '../../types';
import { getAvatarInitial } from '../../utils/avatar';
import { getStudentDisplayName } from '../../utils/student';

interface TeacherStudentTableProps {
  students: TeacherStudentSummary[];
  currentStudentId: string;
  isLoading?: boolean;
  onSelectStudentForDetail: (studentId: string) => void;
  onEnterStudentView: (studentId: string) => void;
  onResetFilters?: () => void;
  hasActiveFilters?: boolean;
}

export const TeacherStudentTable: React.FC<TeacherStudentTableProps> = ({
  students,
  currentStudentId,
  isLoading = false,
  onSelectStudentForDetail,
  onEnterStudentView,
  onResetFilters,
  hasActiveFilters = false,
}) => {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200">
      <table className="w-full text-left text-xs min-w-[760px]">
        <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold">
          <tr>
            <th className="py-3 px-4">学生基本信息</th>
            <th className="py-3 px-4">学习目标</th>
            <th className="py-3 px-4">综合掌握度</th>
            <th className="py-3 px-4">认知分布 (达标/推进/薄弱)</th>
            <th className="py-3 px-4">做题表现</th>
            <th className="py-3 px-4">学习状态</th>
            <th className="py-3 px-4 text-right">教学操作</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {isLoading ? (
            <tr>
              <td colSpan={7} className="py-12 text-center text-slate-400">
                <div className="inline-flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                  正在加载全班学生学情数据...
                </div>
              </td>
            </tr>
          ) : students.length === 0 ? (
            <tr>
              <td colSpan={7} className="py-8">
                <div className="text-center text-slate-400 text-xs">
                  无匹配的学生记录
                </div>
                {hasActiveFilters && onResetFilters && (
                  <div className="text-center mt-2">
                    <button
                      type="button"
                      onClick={onResetFilters}
                      className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer transition-colors"
                    >
                      清空搜索与分类筛选
                    </button>
                  </div>
                )}
              </td>
            </tr>
          ) : (
            students.map((st) => {
              const isSelected = st.student_id === currentStudentId;
              const riskBadge = {
                HEALTHY: {
                  label: '掌握良好',
                  class: 'bg-emerald-50 text-emerald-700 border-emerald-200',
                },
                NORMAL: {
                  label: '学习推进中',
                  class: 'bg-blue-50 text-blue-700 border-blue-200',
                },
                ATTENTION: {
                  label: '重点关注',
                  class: 'bg-rose-50 text-rose-700 border-rose-200',
                },
              }[st.risk_level];

              return (
                <tr
                  key={st.student_id}
                  className={`hover:bg-slate-50/80 transition-colors ${
                    isSelected ? 'bg-indigo-50/30' : ''
                  }`}
                  data-testid={`teacher-student-row-${st.student_id}`}
                >
                  {/* 1. 基本信息 */}
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-indigo-600/10 text-indigo-700 font-bold flex items-center justify-center shrink-0 overflow-hidden select-none text-xs">
                        {getAvatarInitial(getStudentDisplayName(st.student_id, st.student_name))}
                      </div>
                      <div>
                        <div className="font-bold text-slate-900">{getStudentDisplayName(st.student_id, st.student_name)}</div>
                        <div className="text-[11px] text-slate-400">
                          {st.major} · {st.grade}
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* 2. 学习目标 */}
                  <td className="py-3.5 px-4 max-w-[180px]">
                    <div className="truncate text-slate-700" title={st.learning_goal}>
                      {st.learning_goal}
                    </div>
                    {st.current_focus_node && (
                      <div className="text-[10px] text-indigo-600 font-mono mt-0.5">
                        焦点: {st.current_focus_node} {st.current_focus_name || ''}
                      </div>
                    )}
                  </td>

                  {/* 3. 综合掌握度 */}
                  <td className="py-3.5 px-4">
                    <div className="space-y-1 w-28">
                      <div className="flex justify-between font-mono font-bold">
                        <span>{(st.overall_mastery * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-indigo-600 h-full rounded-full"
                          style={{
                            width: `${Math.min(100, st.overall_mastery * 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* 4. 认知分布 */}
                  <td className="py-3.5 px-4 font-mono">
                    <div className="flex items-center gap-1.5 text-[11px]">
                      <span className="text-emerald-600 font-bold" title="已达标">
                        {st.mastered_count} 达标
                      </span>
                      <span className="text-slate-300">/</span>
                      <span className="text-indigo-600 font-bold" title="推进中">
                        {st.developing_count} 推进
                      </span>
                      <span className="text-slate-300">/</span>
                      <span className="text-rose-600 font-bold" title="薄弱">
                        {st.weak_count} 薄弱
                      </span>
                    </div>
                  </td>

                  {/* 5. 做题表现 */}
                  <td className="py-3.5 px-4 font-mono">
                    <div>
                      <span className="font-bold text-slate-800">
                        {st.accuracy.toFixed(1)}%
                      </span>
                      <span className="text-slate-400 text-[11px] ml-1">正确率</span>
                    </div>
                    <div className="text-[11px] text-slate-400">
                      共练 {st.total_attempts} 题 / 错 {st.total_wrong_count} 题
                    </div>
                  </td>

                  {/* 6. 风险状态 */}
                  <td className="py-3.5 px-4">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${riskBadge.class}`}
                    >
                      {riskBadge.label}
                    </span>
                  </td>

                  {/* 7. 操作 */}
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        type="button"
                        onClick={() => onSelectStudentForDetail(st.student_id)}
                        className="px-2.5 py-1 rounded-lg text-xs font-bold text-indigo-600 hover:bg-indigo-50 transition-colors cursor-pointer"
                        data-testid={`btn-student-detail-${st.student_id}`}
                      >
                        学情档案
                      </button>
                      <button
                        type="button"
                        onClick={() => onEnterStudentView(st.student_id)}
                        className="px-2.5 py-1 rounded-lg text-xs font-bold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                        title="以该生身份进入学生端"
                        data-testid={`btn-enter-student-${st.student_id}`}
                      >
                        进入视界
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
};
