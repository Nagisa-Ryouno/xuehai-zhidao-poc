import React, { useState, useMemo } from 'react';
import { BookOpen, Search, Filter, ArrowUpDown, X } from 'lucide-react';
import type { TeacherKnowledgeResponse } from '../../types';
import { TeacherKnowledgeTable } from './TeacherKnowledgeTable';
import { TeacherKnowledgeDiagnosisDrawer } from './TeacherKnowledgeDiagnosisDrawer';

interface TeacherKnowledgeTabProps {
  knowledgeData: TeacherKnowledgeResponse | null;
  isLoading: boolean;
  onSelectStudentForDetail: (studentId: string) => void;
  onEnterStudentView: (studentId: string) => void;
}

export const TeacherKnowledgeTab: React.FC<TeacherKnowledgeTabProps> = ({
  knowledgeData,
  isLoading,
  onSelectStudentForDetail,
  onEnterStudentView,
}) => {
  // 筛选与排序本地状态
  const [knowledgeSearchQuery, setKnowledgeSearchQuery] = useState<string>('');
  const [selectedChapter, setSelectedChapter] = useState<string>('ALL');
  const [knowledgeSortBy, setKnowledgeSortBy] = useState<
    'id' | 'mastery_asc' | 'mastery_desc' | 'weak_desc' | 'mistakes_desc'
  >('id');

  // 诊断抽屉选中考点 ID
  const [selectedKnowledgeIdForDiagnosis, setSelectedKnowledgeIdForDiagnosis] = useState<string | null>(null);

  // 提取章节去重列表
  const chapters = useMemo(() => {
    if (!knowledgeData?.knowledge_points) return [];
    const set = new Set<string>();
    knowledgeData.knowledge_points.forEach((kp) => {
      if (kp.chapter) set.add(kp.chapter);
    });
    return Array.from(set);
  }, [knowledgeData]);

  // 严格保持现有过滤与排序逻辑（Behavior Preservation）
  const filteredKnowledgePoints = useMemo(() => {
    if (!knowledgeData?.knowledge_points) return [];
    let list = [...knowledgeData.knowledge_points];

    if (selectedChapter !== 'ALL') {
      list = list.filter((kp) => kp.chapter === selectedChapter);
    }

    if (knowledgeSearchQuery.trim()) {
      const q = knowledgeSearchQuery.toLowerCase().trim();
      list = list.filter(
        (kp) =>
          kp.knowledge_id.toLowerCase().includes(q) ||
          kp.knowledge_name.toLowerCase().includes(q) ||
          kp.chapter.toLowerCase().includes(q)
      );
    }

    // 稳定确定性排序
    list.sort((a, b) => {
      switch (knowledgeSortBy) {
        case 'mastery_asc':
          return a.average_mastery - b.average_mastery || a.knowledge_id.localeCompare(b.knowledge_id);
        case 'mastery_desc':
          return b.average_mastery - a.average_mastery || a.knowledge_id.localeCompare(b.knowledge_id);
        case 'weak_desc':
          return b.weak_student_count - a.weak_student_count || a.knowledge_id.localeCompare(b.knowledge_id);
        case 'mistakes_desc':
          return b.total_mistakes - a.total_mistakes || a.knowledge_id.localeCompare(b.knowledge_id);
        case 'id':
        default:
          return a.knowledge_id.localeCompare(b.knowledge_id);
      }
    });

    return list;
  }, [knowledgeData, selectedChapter, knowledgeSearchQuery, knowledgeSortBy]);

  const hasActiveFilters = selectedChapter !== 'ALL' || knowledgeSearchQuery.trim().length > 0;

  const handleResetFilters = () => {
    setSelectedChapter('ALL');
    setKnowledgeSearchQuery('');
  };

  return (
    <div className="space-y-6" data-testid="teacher-knowledge-overview">
      {/* Knowledge Summary & Filter Bar */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-2xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-indigo-600" />
              微观经济学核心考点全景表
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              共收录 30 个核心考点，涵盖 7 大知识模块，支持按掌握度/薄弱人数/错题量多维检索
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-semibold text-slate-600">
            <span className="px-3 py-1.5 bg-slate-100 rounded-xl">
              已加载考点: {knowledgeData?.total_count ?? 0} 个
            </span>
          </div>
        </div>

        {/* 筛选与检索控件栏 */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pt-2 border-t border-slate-100">
          {/* Search */}
          <div className="relative w-full md:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={knowledgeSearchQuery}
              onChange={(e) => setKnowledgeSearchQuery(e.target.value)}
              placeholder="搜索考点编号 / 名称 / 章节..."
              className="w-full pl-9 pr-8 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 transition-all"
              data-testid="teacher-knowledge-search"
            />
            {knowledgeSearchQuery && (
              <button
                type="button"
                onClick={() => setKnowledgeSearchQuery('')}
                className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-600 cursor-pointer"
                title="清除搜索"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Chapter Filter */}
            <div className="flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={selectedChapter}
                onChange={(e) => setSelectedChapter(e.target.value)}
                className="px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 text-slate-700"
                data-testid="teacher-knowledge-chapter-filter"
              >
                <option value="ALL">全部章节 ({chapters.length})</option>
                {chapters.map((ch) => (
                  <option key={ch} value={ch}>
                    {ch}
                  </option>
                ))}
              </select>
            </div>

            {/* Sort Selector */}
            <div className="flex items-center gap-1.5">
              <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={knowledgeSortBy}
                onChange={(e) =>
                  setKnowledgeSortBy(
                    e.target.value as
                      | 'id'
                      | 'mastery_asc'
                      | 'mastery_desc'
                      | 'weak_desc'
                      | 'mistakes_desc'
                  )
                }
                className="px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 text-slate-700"
                data-testid="teacher-knowledge-sort"
              >
                <option value="id">按考点编号 (K01-K30)</option>
                <option value="mastery_asc">掌握度升序 (优先薄弱)</option>
                <option value="mastery_desc">掌握度降序 (掌握最好)</option>
                <option value="weak_desc">薄弱学生数 (从多到少)</option>
                <option value="mistakes_desc">累计错题数 (从多到少)</option>
              </select>
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
      </div>

      {/* 知识点表格呈现 */}
      <TeacherKnowledgeTable
        knowledgePoints={filteredKnowledgePoints}
        isLoading={isLoading}
        onSelectKnowledgeForDiagnosis={setSelectedKnowledgeIdForDiagnosis}
        onResetFilters={handleResetFilters}
        hasActiveFilters={hasActiveFilters}
      />

      {/* 考点学生学情诊断抽屉 (Drawer) */}
      <TeacherKnowledgeDiagnosisDrawer
        isOpen={!!selectedKnowledgeIdForDiagnosis}
        knowledgeId={selectedKnowledgeIdForDiagnosis}
        onClose={() => setSelectedKnowledgeIdForDiagnosis(null)}
        onSelectStudentForDetail={onSelectStudentForDetail}
        onEnterStudentView={onEnterStudentView}
      />
    </div>
  );
};
