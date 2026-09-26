import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Sparkles,
  TrendingUp,
  AlertTriangle,
  Layers,
  BookOpen,
  Users,
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
import { getAvatarInitial } from '../utils/avatar';
import { TeacherStudentDetailModal } from '../components/teacher/TeacherStudentDetailModal';
import { TeacherOverviewTab } from '../components/teacher/TeacherOverviewTab';
import { TeacherKnowledgeTab } from '../components/teacher/TeacherKnowledgeTab';
import { TeacherStudentsTab } from '../components/teacher/TeacherStudentsTab';

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

  // 1. Overview 宏观总览数据状态
  const [overview, setOverview] = useState<TeacherOverviewResponse | null>(null);
  const [isLoadingOverview, setIsLoadingOverview] = useState<boolean>(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  // 2. Knowledge 30 考点全景数据状态
  const [knowledgeData, setKnowledgeData] = useState<TeacherKnowledgeResponse | null>(null);
  const [isLoadingKnowledge, setIsLoadingKnowledge] = useState<boolean>(false);
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null);

  // 3. 学生个人详情下钻弹窗状态
  const [selectedStudentForDetail, setSelectedStudentForDetail] = useState<string | null>(null);

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
              <div className="w-12 h-12 rounded-xl bg-indigo-500 flex items-center justify-center text-white font-bold text-lg shadow-md overflow-hidden shrink-0 select-none">
                {getAvatarInitial(currentStudent?.student_name || '新同学')}
              </div>
              <div>
                <div className="text-xs text-slate-300 font-medium">当前下钻学生上下文</div>
                <div className="text-base font-bold text-white">
                  {currentStudent?.student_name || '新同学'}
                </div>
                <div className="text-xs text-indigo-300 mt-0.5">
                  {currentStudent?.major || '经济学'} · 正确率: {currentStudent ? `${currentStudent.average_accuracy.toFixed(1)}%` : '--'}
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

        {/* TAB 1: 班级总览 (Overview) */}
        {activeTab === 'overview' && (
          <TeacherOverviewTab
            overview={overview}
            isLoading={isLoadingOverview}
            studentsCount={students.length}
            onNavigateToKnowledge={() => navigate('/teacher/knowledge')}
            onNavigateToStudents={() => navigate('/teacher/students')}
          />
        )}

        {/* TAB 2: 知识点全景 (Knowledge) */}
        {activeTab === 'knowledge' && (
          <TeacherKnowledgeTab
            knowledgeData={knowledgeData}
            isLoading={isLoadingKnowledge}
            onSelectStudentForDetail={setSelectedStudentForDetail}
            onEnterStudentView={handleEnterStudentView}
          />
        )}

        {/* TAB 3: 学生学情档案 (Students) */}
        {activeTab === 'students' && (
          <TeacherStudentsTab
            overview={overview}
            isLoading={isLoadingOverview}
            currentStudentId={studentId}
            onSelectStudentForDetail={setSelectedStudentForDetail}
            onEnterStudentView={handleEnterStudentView}
          />
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
