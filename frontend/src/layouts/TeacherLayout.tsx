import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Users,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  Layers,
  Flame,
  BookOpen,
  Search,
  ArrowUpDown,
  CheckCircle2,
  Filter,
  ArrowRight,
  RotateCcw,
} from 'lucide-react';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { useApp } from '../context/useApp';
import type {
  StudentListItem,
  TeacherOverviewResponse,
  TeacherKnowledgeResponse,
} from '../types';
import { getTeacherOverview, getTeacherKnowledge } from '../api';
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
  const { studentId, subRoute, navigate, switchRole } = useApp();

  // 1. Overview 数据状态
  const [overview, setOverview] = useState<TeacherOverviewResponse | null>(null);
  const [isLoadingOverview, setIsLoadingOverview] = useState<boolean>(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  // 2. Knowledge 30 考点全景数据状态
  const [knowledgeData, setKnowledgeData] = useState<TeacherKnowledgeResponse | null>(null);
  const [isLoadingKnowledge, setIsLoadingKnowledge] = useState<boolean>(false);
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null);

  // 3. 交互筛选状态
  // 学生 Tab 筛选
  const [studentSearchQuery, setStudentSearchQuery] = useState<string>('');
  const [riskFilter, setRiskFilter] = useState<'ALL' | 'HEALTHY' | 'NORMAL' | 'ATTENTION'>('ALL');
  const [selectedStudentForDetail, setSelectedStudentForDetail] = useState<string | null>(null);

  // 知识点 Tab 筛选与排序
  const [knowledgeSearchQuery, setKnowledgeSearchQuery] = useState<string>('');
  const [selectedChapter, setSelectedChapter] = useState<string>('ALL');
  const [knowledgeSortBy, setKnowledgeSortBy] = useState<
    'id' | 'mastery_asc' | 'mastery_desc' | 'weak_desc' | 'mistakes_desc'
  >('id');

  // 计算当前激活的主 Tab（映射自路由 subRoute）
  const activeTab: 'overview' | 'knowledge' | 'students' = useMemo(() => {
    if (subRoute === 'knowledge') return 'knowledge';
    if (subRoute === 'students') return 'students';
    return 'overview';
  }, [subRoute]);

  // 加载班级宏观看板数据
  const fetchOverview = useCallback(async () => {
    setIsLoadingOverview(true);
    setOverviewError(null);
    try {
      const data = await getTeacherOverview();
      setOverview(data);
    } catch (err) {
      console.error('Failed to fetch teacher overview:', err);
      setOverviewError(err instanceof Error ? err.message : '获取教师学情总览数据失败');
    } finally {
      setIsLoadingOverview(false);
    }
  }, []);

  // 加载 30 个考点全景聚合数据
  const fetchKnowledge = useCallback(async () => {
    setIsLoadingKnowledge(true);
    setKnowledgeError(null);
    try {
      const data = await getTeacherKnowledge();
      setKnowledgeData(data);
    } catch (err) {
      console.error('Failed to fetch teacher knowledge points:', err);
      setKnowledgeError(err instanceof Error ? err.message : '获取知识点全景聚合数据失败');
    } finally {
      setIsLoadingKnowledge(false);
    }
  }, []);

  // 挂载时并发预取数据
  useEffect(() => {
    fetchOverview();
    fetchKnowledge();
  }, [fetchOverview, fetchKnowledge]);

  const currentStudent = students.find((s) => s.student_id === studentId);

  // 班级 KPI 计算
  const kpis = overview?.class_kpis || {
    total_students: overview?.students?.length || students.length || 0,
    active_students: 0,
    class_avg_mastery: 0,
    at_risk_students_count: 0,
  };

  const weakPoints = overview?.weak_knowledge_points || [];

  // 学生列表过滤（零排名、人本归纳）
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
          s.major.toLowerCase().includes(q)
      );
    }

    return list;
  }, [overview, riskFilter, studentSearchQuery]);

  // 知识点列表章节去重列表
  const chapters = useMemo(() => {
    if (!knowledgeData?.knowledge_points) return [];
    const set = new Set<string>();
    knowledgeData.knowledge_points.forEach((kp) => {
      if (kp.chapter) set.add(kp.chapter);
    });
    return Array.from(set);
  }, [knowledgeData]);

  // 知识点全景列表过滤与排序
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

  const handleEnterStudentView = (sid: string) => {
    onSelectStudent(sid);
    switchRole('student');
  };

  return (
    <div
      className="min-h-screen flex flex-col bg-slate-100/80 text-slate-900 selection:bg-indigo-100 selection:text-indigo-800"
      data-testid="teacher-cockpit"
    >
      {/* Teacher Cockpit Top Header */}
      <Header
        students={students}
        currentStudentId={studentId}
        onSelectStudent={onSelectStudent}
        isOnline={isOnline}
        isLoading={isGlobalLoading || isLoadingOverview || isLoadingKnowledge}
      />

      {/* Main Cockpit Content (Wide Desktop Layout) */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Cockpit Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl shadow-slate-900/10 border border-slate-800 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-400/30 text-indigo-300 text-xs font-semibold">
                <Sparkles className="w-3.5 h-3.5" />
                教师学情中台 · 宏观教学决策辅助
              </div>
              <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
                班级学情全景监控与成效分析
              </h1>
              <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
                基于知识图谱拓扑与认知状态追踪，客观呈现班级认知分布与薄弱考点瓶颈。本数据仅供教师决策参考，系统不自动替教师做出生产性决策。
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

        {/* 3-Tab Desktop Navigation Pills */}
        <div
          className="flex items-center justify-between border-b border-slate-200/90 pb-3 gap-4 overflow-x-auto"
          data-testid="teacher-tabs"
        >
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => navigate('/teacher/overview')}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition-all cursor-pointer ${
                activeTab === 'overview'
                  ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/70'
              }`}
              data-testid="tab-teacher-overview"
            >
              <Layers className="w-4 h-4" />
              班级总览
            </button>

            <button
              type="button"
              onClick={() => navigate('/teacher/knowledge')}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition-all cursor-pointer ${
                activeTab === 'knowledge'
                  ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/70'
              }`}
              data-testid="tab-teacher-knowledge"
            >
              <BookOpen className="w-4 h-4" />
              知识点全景
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-mono ${
                  activeTab === 'knowledge'
                    ? 'bg-white/20 text-white'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                {knowledgeData?.total_count ?? 30}
              </span>
            </button>

            <button
              type="button"
              onClick={() => navigate('/teacher/students')}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition-all cursor-pointer ${
                activeTab === 'students'
                  ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/70'
              }`}
              data-testid="tab-teacher-students"
            >
              <Users className="w-4 h-4" />
              学生学情档案
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-mono ${
                  activeTab === 'students'
                    ? 'bg-white/20 text-white'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                {overview?.students?.length ?? students.length}
              </span>
            </button>
          </div>

          <div className="text-xs text-slate-400 shrink-0 hidden sm:block">
            桌面优先分析视图 · 100% 确定性客观聚合
          </div>
        </div>

        {/* 异常错误全局卡片 */}
        {(overviewError || knowledgeError) && (
          <div
            className="bg-white rounded-3xl p-8 border border-rose-200 text-center space-y-4 shadow-sm"
            data-testid="teacher-error-state"
          >
            <div className="w-12 h-12 rounded-2xl bg-rose-100 text-rose-600 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">学情看板加载异常</h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto">
              {overviewError || knowledgeError}
            </p>
            <button
              type="button"
              onClick={() => {
                fetchOverview();
                fetchKnowledge();
              }}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all cursor-pointer shadow-sm inline-flex items-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              重新加载数据
            </button>
          </div>
        )}

        {/* ============================================================ */}
        {/* TAB 1: 班级总览 (Overview) */}
        {/* ============================================================ */}
        {activeTab === 'overview' && (
          <div className="space-y-6" data-testid="teacher-overview-section">
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

            {/* 班级重点瓶颈考点关注 */}
            <div
              className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/90 shadow-2xs space-y-5"
              data-testid="teacher-weak-points-ranking"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                    <Flame className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">
                      班级重点瓶颈考点关注
                    </h3>
                    <p className="text-xs text-slate-500">
                      基于全班未掌握人数与错误率识别的共性教学卡点
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => navigate('/teacher/knowledge')}
                  className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 cursor-pointer transition-colors"
                >
                  查看全部 30 个考点全景
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {weakPoints.length === 0 ? (
                <div className="py-8 text-center text-slate-400 text-xs">
                  班级整体掌握良好，暂无显著共性瓶颈考点。
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
                  {weakPoints.slice(0, 5).map((wp, idx) => {
                    const urgencyMeta = {
                      HIGH: {
                        label: '优先关注 · 建议集体面授',
                        badge: 'bg-rose-50 text-rose-700 border-rose-200',
                      },
                      MEDIUM: {
                        label: '中度预警 · 针对性作业',
                        badge: 'bg-amber-50 text-amber-700 border-amber-200',
                      },
                      LOW: {
                        label: '巩固观察',
                        badge: 'bg-slate-100 text-slate-600 border-slate-200',
                      },
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
                    onClick={() => navigate('/teacher/knowledge')}
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
                    onClick={() => navigate('/teacher/students')}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all cursor-pointer inline-flex items-center gap-1.5"
                  >
                    调阅学生花名册
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* TAB 2: 知识点全景 (Knowledge - 全部 30 个考点) */}
        {/* ============================================================ */}
        {activeTab === 'knowledge' && (
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
                    className="w-full pl-9 pr-3.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 transition-all"
                    data-testid="teacher-knowledge-search"
                  />
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
                </div>
              </div>
            </div>

            {/* Knowledge Points Table */}
            <div className="bg-white rounded-3xl border border-slate-200/90 shadow-2xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs" data-testid="teacher-knowledge-table">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold">
                    <tr>
                      <th className="py-3.5 px-4 w-20">考点编号</th>
                      <th className="py-3.5 px-4">考点名称</th>
                      <th className="py-3.5 px-4">所属知识章节</th>
                      <th className="py-3.5 px-4 w-44">班级平均掌握度</th>
                      <th className="py-3.5 px-4 w-28">薄弱学子数</th>
                      <th className="py-3.5 px-4 w-24">累计错题</th>
                      <th className="py-3.5 px-4 w-32 text-right">教学建议等级</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {isLoadingKnowledge ? (
                      <tr>
                        <td colSpan={7} className="py-12 text-center text-slate-400">
                          正在加载 30 个考点认知聚合数据...
                        </td>
                      </tr>
                    ) : filteredKnowledgePoints.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-12 text-center text-slate-400">
                          无匹配的考点记录
                        </td>
                      </tr>
                    ) : (
                      filteredKnowledgePoints.map((kp) => {
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
          </div>
        )}

        {/* ============================================================ */}
        {/* TAB 3: 学生学情档案 (Students Roster & Detail Drilldown) */}
        {/* ============================================================ */}
        {activeTab === 'students' && (
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
                  <div className="w-48 sm:w-60">
                    <input
                      type="text"
                      value={studentSearchQuery}
                      onChange={(e) => setStudentSearchQuery(e.target.value)}
                      placeholder="搜索学号 / 姓名 / 专业..."
                      className="w-full px-3.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 transition-all"
                      data-testid="teacher-student-search"
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
                      <th className="py-3 px-4">认知分布 (达标/推进/薄弱)</th>
                      <th className="py-3 px-4">做题表现</th>
                      <th className="py-3 px-4">学习状态</th>
                      <th className="py-3 px-4 text-right">教学操作</th>
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
                                  onClick={() => setSelectedStudentForDetail(st.student_id)}
                                  className="px-2.5 py-1 rounded-lg text-xs font-bold text-indigo-600 hover:bg-indigo-50 transition-colors cursor-pointer"
                                  data-testid={`btn-student-detail-${st.student_id}`}
                                >
                                  学情档案
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleEnterStudentView(st.student_id)}
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
            </div>
          </div>
        )}

        {/* Quick Switcher Callout */}
        <div className="bg-indigo-50/60 border border-indigo-100 rounded-2xl p-5 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-600 text-white flex items-center justify-center shrink-0">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-indigo-950">
                当前处于教师学情驾驶舱 (Teacher View)
              </h4>
              <p className="text-xs text-indigo-700">
                若需体验学生端移动优先学习闭环与知识图谱，可随时通过按钮或顶栏切换。
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => switchRole('student')}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all shadow-sm shrink-0 cursor-pointer"
          >
            返回学生端视图
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
