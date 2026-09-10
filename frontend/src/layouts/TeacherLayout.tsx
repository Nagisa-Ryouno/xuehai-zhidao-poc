import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Users,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  Layers,
  Flame,
} from 'lucide-react';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { useApp } from '../context/useApp';
import type { StudentListItem, TeacherOverviewResponse } from '../types';
import { getTeacherOverview } from '../api';
import { TeacherStudentDetailModal } from '../components/teacher/TeacherStudentDetailModal';

interface TeacherLayoutProps {
  students: StudentListItem[];
  isOnline: boolean;
  isLoading: boolean;
  onSelectStudent: (studentId: string) => void;
}

export const TeacherLayout: React.FC<TeacherLayoutProps> = ({
  students,
  isOnline,
  isLoading: isGlobalLoading,
  onSelectStudent,
}) => {
  const { studentId, switchRole } = useApp();
  const [overview, setOverview] = useState<TeacherOverviewResponse | null>(null);
  const [isLoadingOverview, setIsLoadingOverview] = useState<boolean>(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [riskFilter, setRiskFilter] = useState<'ALL' | 'HEALTHY' | 'NORMAL' | 'ATTENTION'>('ALL');
  const [selectedStudentForDetail, setSelectedStudentForDetail] = useState<string | null>(null);

  const fetchOverview = useCallback(async () => {
    setIsLoadingOverview(true);
    setOverviewError(null);
    try {
      const data = await getTeacherOverview();
      setOverview(data);
    } catch (err) {
      console.error('Failed to fetch teacher overview:', err);
      setOverviewError(err instanceof Error ? err.message : '获取教师学情驾驶舱数据失败');
    } finally {
      setIsLoadingOverview(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  const currentStudent = students.find((s) => s.student_id === studentId);

  const kpis = overview?.class_kpis || {
    total_students: overview?.students?.length || students.length || 0,
    active_students: 0,
    class_avg_mastery: 0,
    at_risk_students_count: 0,
  };

  const weakPoints = overview?.weak_knowledge_points || [];

  const filteredStudents = useMemo(() => {
    if (!overview || !overview.students) return [];
    let list = overview.students;

    if (riskFilter !== 'ALL') {
      list = list.filter((s) => s.risk_level === riskFilter);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (s) =>
          s.student_id.toLowerCase().includes(q) ||
          s.student_name.toLowerCase().includes(q) ||
          s.major.toLowerCase().includes(q)
      );
    }

    return list;
  }, [overview, riskFilter, searchQuery]);

  const handleEnterStudentView = (sid: string) => {
    onSelectStudent(sid);
    switchRole('student');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-100/80 text-slate-900 selection:bg-indigo-100 selection:text-indigo-800" data-testid="teacher-cockpit">
      {/* Teacher Cockpit Top Header */}
      <Header
        students={students}
        currentStudentId={studentId}
        onSelectStudent={onSelectStudent}
        isOnline={isOnline}
        isLoading={isGlobalLoading || isLoadingOverview}
      />

      {/* Main Cockpit Content (Wide Desktop Layout) */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Cockpit Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl shadow-slate-900/10 border border-slate-800 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-400/30 text-indigo-300 text-xs font-semibold">
                <Sparkles className="w-3.5 h-3.5" />
                教师学情决策驾驶舱 · 智能数据中台
              </div>
              <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
                班级学情全景监控与成效分析
              </h1>
              <p className="text-sm text-slate-300 max-w-2xl">
                基于图谱拓扑与 BKT 认知追踪算法，宏观掌握班级掌握度分布、精准定位薄弱考点瓶颈、支持一键下钻学生个体档案。
              </p>
            </div>

            {/* Current Monitored Student Context Pill */}
            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 border border-white/15 flex items-center gap-4 shrink-0">
              <div className="w-12 h-12 rounded-xl bg-indigo-500 flex items-center justify-center text-white font-bold text-lg shadow-md">
                {studentId}
              </div>
              <div>
                <div className="text-xs text-slate-300 font-medium">当前下钻学生上下文</div>
                <div className="text-base font-bold text-white">
                  {currentStudent?.student_name || studentId} ({currentStudent?.major || '经济学'})
                </div>
                <div className="text-xs text-indigo-300 mt-0.5">
                  正确率: {currentStudent ? `${currentStudent.average_accuracy.toFixed(1)}%` : '--'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 异常错误展示与重试卡片 */}
        {overviewError && (
          <div className="bg-white rounded-3xl p-8 border border-rose-200 text-center space-y-4 shadow-sm" data-testid="teacher-error-state">
            <div className="w-12 h-12 rounded-2xl bg-rose-100 text-rose-600 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">学情看板加载异常</h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto">{overviewError}</p>
            <button
              type="button"
              onClick={fetchOverview}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all cursor-pointer shadow-sm"
            >
              重新加载看板
            </button>
          </div>
        )}

        {/* 4 大核心班级全景统计 KPI 卡片 */}
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
            <p className="text-[11px] text-slate-400">已完整建立 BKT 认知基线</p>
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
              活跃率 {((kpis.active_students / (kpis.total_students || 1)) * 100).toFixed(0)}%
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
              <span className="text-xs text-slate-400">BKT 均值</span>
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

        {/* 班级薄弱瓶颈考点 Top-5 排行 */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/90 shadow-2xs space-y-5" data-testid="teacher-weak-points-ranking">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                <Flame className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  班级共性薄弱瓶颈考点 Top-5 排行
                </h3>
                <p className="text-xs text-slate-500">
                  按班级未掌握人数与错误率加权识别的群体认知卡点
                </p>
              </div>
            </div>
            <span className="text-xs text-slate-400">
              数据源: 全量学生真实答题与 BKT 状态投影
            </span>
          </div>

          {weakPoints.length === 0 ? (
            <div className="py-8 text-center text-slate-400 text-xs">
              班级整体掌握良好，暂无显著共性瓶颈考点。
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {weakPoints.slice(0, 5).map((wp, idx) => {
                const urgencyMeta = {
                  HIGH: { label: '高危卡点 · 建议集体面授', badge: 'bg-rose-50 text-rose-700 border-rose-200' },
                  MEDIUM: { label: '中度预警 · 针对性作业', badge: 'bg-amber-50 text-amber-700 border-amber-200' },
                  LOW: { label: '巩固观察', badge: 'bg-slate-100 text-slate-600 border-slate-200' },
                }[wp.urgency];

                return (
                  <div
                    key={wp.knowledge_id}
                    className="p-4 rounded-2xl border border-slate-200/90 bg-white hover:border-indigo-300 hover:shadow-xs transition-all space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 rounded-md bg-slate-900 text-white font-mono text-[10px] font-bold flex items-center justify-center">
                          #{idx + 1}
                        </span>
                        <span className="font-mono text-xs font-bold text-slate-700">
                          {wp.knowledge_id}
                        </span>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${urgencyMeta.badge}`}
                      >
                        {urgencyMeta.label}
                      </span>
                    </div>

                    <div>
                      <h4 className="text-sm font-bold text-slate-900 leading-snug">
                        {wp.knowledge_name}
                      </h4>
                      <p className="text-[11px] text-slate-400 mt-0.5">{wp.chapter}</p>
                    </div>

                    <div className="space-y-1.5 pt-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-500">班级平均掌握度</span>
                        <span className="font-mono font-bold text-slate-800">
                          {(wp.avg_mastery * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-rose-500 h-full rounded-full"
                          style={{ width: `${Math.min(100, wp.avg_mastery * 100)}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-0.5">
                        <span>班级错误率: {wp.error_rate.toFixed(1)}%</span>
                        <span className="text-rose-600 font-semibold">
                          {wp.weak_student_count} 人薄弱
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 班级学生全览表与快速下钻 */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/90 shadow-2xs space-y-5" data-testid="teacher-student-roster">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">班级学生学情全览表</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                支持按姓名/学号检索及风险筛选，点击单行可即时调阅全维学情
              </p>
            </div>

            <div className="flex items-center gap-3 flex-wrap">
              {/* Risk Filter */}
              <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
                {(
                  [
                    { id: 'ALL', label: '全部' },
                    { id: 'ATTENTION', label: '重点关注' },
                    { id: 'NORMAL', label: '正常' },
                    { id: 'HEALTHY', label: '健康' },
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
              <div className="w-48 sm:w-60">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索学号 / 姓名 / 专业..."
                  className="w-full px-3.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 transition-all"
                />
              </div>
            </div>
          </div>

          {/* Student Table */}
          <div className="overflow-x-auto rounded-2xl border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold">
                <tr>
                  <th className="py-3 px-4">学生基本信息</th>
                  <th className="py-3 px-4">学习目标</th>
                  <th className="py-3 px-4">综合掌握度</th>
                  <th className="py-3 px-4">认知分布 (达标/进行/薄弱)</th>
                  <th className="py-3 px-4">做题表现</th>
                  <th className="py-3 px-4">风险状态</th>
                  <th className="py-3 px-4 text-right">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredStudents.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-400">
                      无匹配的学生记录
                    </td>
                  </tr>
                ) : (
                  filteredStudents.map((st) => {
                    const isSelected = st.student_id === studentId;
                    const riskBadge = {
                      HEALTHY: { label: '健康', class: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
                      NORMAL: { label: '良好', class: 'bg-blue-50 text-blue-700 border-blue-200' },
                      ATTENTION: { label: '需关注', class: 'bg-rose-50 text-rose-700 border-rose-200' },
                    }[st.risk_level];

                    return (
                      <tr
                        key={st.student_id}
                        className={`hover:bg-slate-50/80 transition-colors ${
                          isSelected ? 'bg-indigo-50/30' : ''
                        }`}
                      >
                        {/* 1. 基本信息 */}
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-lg bg-indigo-600/10 text-indigo-700 font-mono font-bold flex items-center justify-center shrink-0">
                              {st.student_id}
                            </div>
                            <div>
                              <div className="font-bold text-slate-900">{st.student_name}</div>
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
                                style={{ width: `${Math.min(100, st.overall_mastery * 100)}%` }}
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
                            <span className="text-indigo-600 font-bold" title="发展中">
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
                              onClick={() => setSelectedStudentForDetail(st.student_id)}
                              className="px-2.5 py-1 rounded-lg text-xs font-bold text-indigo-600 hover:bg-indigo-50 transition-colors cursor-pointer"
                            >
                              学情档案
                            </button>
                            <button
                              type="button"
                              onClick={() => handleEnterStudentView(st.student_id)}
                              className="px-2.5 py-1 rounded-lg text-xs font-bold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                              title="以该生身份进入学生端"
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
        </div>

        {/* Quick Switcher Callout */}
        <div className="bg-indigo-50/60 border border-indigo-100 rounded-2xl p-5 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-600 text-white flex items-center justify-center shrink-0">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-indigo-950">
                当前处于教师驾驶舱 (Teacher View)
              </h4>
              <p className="text-xs text-indigo-700">
                若需体验学生端移动优先 4-Tab 学习任务与知识图谱，可随时通过顶栏切换。
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => switchRole('student')}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-sm shrink-0 cursor-pointer"
          >
            返回学生视图
          </button>
        </div>
      </main>

      {/* Student Detail Modal */}
      <TeacherStudentDetailModal
        isOpen={!!selectedStudentForDetail}
        studentId={selectedStudentForDetail}
        onClose={() => setSelectedStudentForDetail(null)}
        onEnterStudentView={handleEnterStudentView}
      />

      <Footer />
    </div>
  );
};
