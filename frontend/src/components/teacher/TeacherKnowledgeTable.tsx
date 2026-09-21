import React from 'react';
import type { TeacherKnowledgeItem } from '../../types';

interface TeacherKnowledgeTableProps {
  knowledgePoints: TeacherKnowledgeItem[];
  isLoading: boolean;
  onResetFilters?: () => void;
  hasActiveFilters?: boolean;
}

export const TeacherKnowledgeTable: React.FC<TeacherKnowledgeTableProps> = ({
  knowledgePoints,
  isLoading,
  onResetFilters,
  hasActiveFilters = false,
}) => {
  return (
    <div className="bg-white rounded-3xl border border-slate-200/90 shadow-2xs overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs min-w-[700px]" data-testid="teacher-knowledge-table">
          <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold">
            <tr>
              <th className="py-3.5 px-4 w-20">考点编号</th>
              <th className="py-3.5 px-4 min-w-[140px]">考点名称</th>
              <th className="py-3.5 px-4 min-w-[150px]">所属知识章节</th>
              <th className="py-3.5 px-4 w-44">班级平均掌握度</th>
              <th className="py-3.5 px-4 w-28">薄弱学子数</th>
              <th className="py-3.5 px-4 w-24">累计错题</th>
              <th className="py-3.5 px-4 w-32 text-right">教学建议等级</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-400">
                  <div className="inline-flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                    正在加载 30 个考点认知聚合数据...
                  </div>
                </td>
              </tr>
            ) : knowledgePoints.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8">
                  <div className="text-center text-slate-400 text-xs">
                    无匹配的考点记录
                  </div>
                  {hasActiveFilters && onResetFilters && (
                    <div className="text-center mt-2">
                      <button
                        type="button"
                        onClick={onResetFilters}
                        className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer transition-colors"
                      >
                        清空搜索与筛选条件
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ) : (
              knowledgePoints.map((kp) => {
                const urgencyBadge = {
                  HIGH: {
                    label: '优先关注',
                    class: 'bg-rose-50 text-rose-700 border-rose-200',
                  },
                  MEDIUM: {
                    label: '中度预警',
                    class: 'bg-amber-50 text-amber-700 border-amber-200',
                  },
                  LOW: {
                    label: '掌握良好',
                    class: 'bg-emerald-50 text-emerald-700 border-emerald-200',
                  },
                }[kp.urgency];

                const masteryPct = (kp.average_mastery * 100).toFixed(1);

                return (
                  <tr
                    key={kp.knowledge_id}
                    className="hover:bg-slate-50/80 transition-colors"
                    data-testid={`teacher-knowledge-row-${kp.knowledge_id}`}
                  >
                    {/* 1. 编号 */}
                    <td className="py-3 px-4 font-mono font-bold text-slate-700">
                      {kp.knowledge_id}
                    </td>

                    {/* 2. 名称 */}
                    <td className="py-3 px-4 font-bold text-slate-900">
                      {kp.knowledge_name}
                    </td>

                    {/* 3. 章节 */}
                    <td className="py-3 px-4 text-slate-500">
                      {kp.chapter}
                    </td>

                    {/* 4. 平均掌握度 */}
                    <td className="py-3 px-4">
                      <div className="space-y-1">
                        <div className="flex justify-between font-mono font-bold">
                          <span>{masteryPct}%</span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              kp.average_mastery >= 0.8
                                ? 'bg-emerald-500'
                                : kp.average_mastery >= 0.6
                                ? 'bg-indigo-500'
                                : 'bg-rose-500'
                            }`}
                            style={{ width: `${Math.min(100, kp.average_mastery * 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    {/* 5. 薄弱学子数 */}
                    <td className="py-3 px-4 font-mono">
                      <span
                        className={
                          kp.weak_student_count > 0
                            ? 'text-rose-600 font-bold'
                            : 'text-slate-400'
                        }
                      >
                        {kp.weak_student_count} 人
                      </span>
                      <span className="text-[10px] text-slate-400 ml-1">
                        / {kp.student_count}
                      </span>
                    </td>

                    {/* 6. 累计错题 */}
                    <td className="py-3 px-4 font-mono text-slate-700">
                      {kp.total_mistakes} 次
                    </td>

                    {/* 7. 教学关注等级 */}
                    <td className="py-3 px-4 text-right">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${urgencyBadge.class}`}
                      >
                        {urgencyBadge.label}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
