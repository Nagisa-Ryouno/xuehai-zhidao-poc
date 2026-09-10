import React, { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from '../components/Header';
import { HeroBanner } from '../components/HeroBanner';
import { StatCards } from '../components/StatCards';
import { LearningProfile } from '../components/LearningProfile';
import { AIDiagnosis } from '../components/AIDiagnosis';
import { WeakKnowledgePoints } from '../components/WeakKnowledgePoints';
import { KnowledgeGraph } from '../components/KnowledgeGraph';
import { LearningPath } from '../components/LearningPath';
import { AISummary } from '../components/AISummary';
import { AIAssistant } from '../components/AIAssistant';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorState } from '../components/ErrorState';
import { Footer } from '../components/Footer';
import { BottomSheet } from '../components/common/BottomSheet';
import { KnowledgePointQuiz } from '../components/student/KnowledgePointQuiz';
import { CurrentFocusCard } from '../components/student/CurrentFocusCard';
import { TasksQuickNav } from '../components/student/TasksQuickNav';
import { resolveCurrentFocusTask } from '../components/student/taskFocusModel';
import { buildLearningContext } from '../components/student/learningContextModel';

import { useApp } from '../context/useApp';
import type { StudentListItem, StudentDashboardResponse, PathState, DynamicLearningRoute } from '../types';
import { CalendarCheck, Network, UserCheck, Bot } from 'lucide-react';
import { BottomNav } from '../components/student/BottomNav';
import { MobileContainer } from '../components/student/MobileContainer';
import { ConceptCardModal } from '../components/student/ConceptCardModal';
import { StudentInitModal } from '../components/student/StudentInitModal';
import { PretestModal } from '../components/student/PretestModal';
import { getConceptCardById, type ConceptCardData } from '../components/student/conceptCardData';
import { initStudent, getDynamicPath, type StudentInitRequest } from '../api';

interface StudentLayoutProps {
  students: StudentListItem[];
  dashboardData: StudentDashboardResponse | null;
  pathStates?: Record<string, PathState>;
  isLoading: boolean;
  isSwitching: boolean;
  errorMessage: string | null;
  isOnline: boolean;
  onSelectStudent: (studentId: string) => void;
  onRetry: () => void;
  onRefresh?: () => Promise<void>;
}

export const StudentLayout: React.FC<StudentLayoutProps> = ({
  students,
  dashboardData,
  pathStates,
  isLoading,
  isSwitching,
  errorMessage,
  isOnline,
  onSelectStudent,
  onRetry,
  onRefresh,
}) => {
  const { studentId, subRoute, navigate } = useApp();
  const assistantRef = useRef<HTMLDivElement | null>(null);

  // 全局统一微测验状态提升 (Step 3: 统一测验启动入口)
  const [activeQuiz, setActiveQuiz] = useState<{
    knowledgeId: string;
    knowledgeName: string;
  } | null>(null);

  // 考点精要速览微卡片状态 (先学后测)
  const [activeConceptCard, setActiveConceptCard] = useState<ConceptCardData | null>(null);

  // 学习目标设定与新学生模态框状态
  const [isInitModalOpen, setIsInitModalOpen] = useState<boolean>(false);

  // 3题极速前测与自适应动态航线状态 (Sprint 8-B)
  const [isPretestModalOpen, setIsPretestModalOpen] = useState<boolean>(false);
  const [dynamicRoute, setDynamicRoute] = useState<DynamicLearningRoute | null>(null);

  const fetchDynamicRoute = useCallback(async () => {
    try {
      const goal = dashboardData?.profile?.student?.learning_goal;
      const route = await getDynamicPath(studentId, goal);
      setDynamicRoute(route);
    } catch {
      setDynamicRoute(null);
    }
  }, [studentId, dashboardData]);

  useEffect(() => {
    fetchDynamicRoute();
  }, [fetchDynamicRoute]);

  // 学生上下文切换时安全关闭微测验与速览卡片，杜绝上下文污染 (Sprint 3 契约约束)
  useEffect(() => {
    setActiveQuiz(null);
    setActiveConceptCard(null);
  }, [studentId]);

  const handleStartQuiz = useCallback(
    (knowledgeId: string, knowledgeName: string) => {
      setActiveQuiz({ knowledgeId, knowledgeName });
    },
    []
  );

  const handleViewConceptCard = useCallback(
    (knowledgeId: string, _knowledgeName: string) => {
      const card = getConceptCardById(knowledgeId);
      if (card) {
        setActiveConceptCard(card);
      }
    },
    []
  );

  const handleCloseConceptCard = useCallback(() => {
    setActiveConceptCard(null);
  }, []);

  const handleInitStudentSubmit = useCallback(
    async (data: StudentInitRequest) => {
      try {
        const res = await initStudent(data);
        if (res && res.student_id) {
          onSelectStudent(res.student_id);
          if (onRefresh) {
            await onRefresh();
          }
        }
      } catch (err) {
        console.error('Failed to init student:', err);
      }
    },
    [onSelectStudent, onRefresh]
  );

  const handleCloseQuiz = useCallback(() => {
    setActiveQuiz(null);
    fetchDynamicRoute();
    if (onRefresh) {
      onRefresh();
    }
  }, [onRefresh, fetchDynamicRoute]);

  const handleNextKnowledgePoint = useCallback(
    (nextKnowledgeId: string, nextKnowledgeName: string) => {
      setActiveQuiz({
        knowledgeId: nextKnowledgeId,
        knowledgeName: nextKnowledgeName,
      });
      fetchDynamicRoute();
      if (onRefresh) {
        onRefresh();
      }
    },
    [onRefresh, fetchDynamicRoute]
  );

  const handleJumpToAssistant = () => {
    navigate('/student/assistant');
    if (assistantRef.current) {
      assistantRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const focusResult = useMemo(
    () =>
      resolveCurrentFocusTask(
        dashboardData?.learning_path?.learning_path || [],
        pathStates
      ),
    [dashboardData, pathStates]
  );

  const learningContext = useMemo(() => {
    if (!dashboardData) return undefined;
    return buildLearningContext({
      student: dashboardData.profile.student,
      learningPath: dashboardData.learning_path?.learning_path || [],
      pathStates,
      currentFocus: focusResult,
    });
  }, [dashboardData, pathStates, focusResult]);

  // 4 个核心 Tab 定义（为后续 P0-2 Mobile First 4-Tab 准备好的路由骨架）
  const tabs = [
    { id: 'tasks', label: '今日任务', path: '/student/tasks', icon: CalendarCheck },
    { id: 'graph', label: '知识图谱', path: '/student/graph', icon: Network },
    { id: 'profile', label: '学情档案', path: '/student/profile', icon: UserCheck },
    { id: 'assistant', label: 'AI伴学', path: '/student/assistant', icon: Bot },
  ] as const;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 selection:bg-indigo-100 selection:text-indigo-800">
      {/* Top Header */}
      {/* Top Header */}
      <Header
        students={students}
        currentStudentId={studentId}
        onSelectStudent={onSelectStudent}
        isOnline={isOnline}
        isLoading={isLoading || isSwitching}
        onOpenInitModal={() => setIsInitModalOpen(true)}
        onOpenPretestModal={() => setIsPretestModalOpen(true)}
      />

      {/* Sub-route Navigation Pill Bar (仅在平板与桌面端展示，移动端由底部 BottomNav 承载) */}
      <div className="hidden md:block bg-white border-b border-slate-200/80 sticky top-18 z-20 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav aria-label="学生端桌面主导航" className="flex items-center space-x-1 sm:space-x-2 py-2 overflow-x-auto no-scrollbar">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = subRoute === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  aria-current={isActive ? 'page' : undefined}
                  onClick={() => navigate(tab.path)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs sm:text-sm font-semibold transition-all shrink-0 cursor-pointer ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main Content Area with MobileContainer */}
      <main className="flex-1 w-full py-4 sm:py-8">
        <MobileContainer>
        {isLoading ? (
          <LoadingSkeleton />
        ) : errorMessage ? (
          <ErrorState message={errorMessage} onRetry={onRetry} isRetrying={isLoading} />
        ) : dashboardData ? (
          <div
            className={`space-y-8 transition-opacity duration-300 ${
              isSwitching ? 'opacity-40 pointer-events-none' : 'opacity-100'
            }`}
          >
            {/* 根据当前子路由进行渲染 */}
            {subRoute === 'tasks' && (
              <>
                {/* 1. Hero Welcome & Personalized Goal */}
                <HeroBanner
                  student={dashboardData.profile.student}
                  recommendationType={dashboardData.learning_path.recommendation_type}
                />

                {/* 2. Today's Learning Mission: Current Focus Task (Sprint 2 Core) */}
                <CurrentFocusCard
                  focusResult={focusResult}
                  dynamicRoute={dynamicRoute}
                  onStartQuiz={handleStartQuiz}
                  onViewConceptCard={handleViewConceptCard}
                  onViewGraph={() => navigate('/student/graph')}
                />

                {/* 3. AI Generated Learning Path (Core Timeline) */}
                <LearningPath
                  learningPath={dashboardData.learning_path.learning_path}
                  recommendationType={dashboardData.learning_path.recommendation_type}
                  studentName={dashboardData.profile.student.student_name}
                  pathStates={pathStates}
                  focusedKnowledgeId={focusResult.focus?.knowledgeId}
                  onStartQuiz={handleStartQuiz}
                />

                {/* 4. Lightweight Auxiliary Navigation Cards */}
                <TasksQuickNav onNavigate={(path) => navigate(path)} />
              </>
            )}

            {subRoute === 'graph' && (
              <div className="space-y-6">
                <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs">
                  <h2 className="text-xl font-bold text-slate-900">知识图谱全景视图</h2>
                  <p className="text-xs text-slate-500 mt-1">
                    当前展示 {dashboardData.profile.student.student_name} 的微观经济学认知知识网络。
                  </p>
                </div>
                <KnowledgeGraph
                  currentStudentId={studentId}
                  studentName={dashboardData.profile.student.student_name}
                  pathStates={pathStates}
                  activeRoute={dynamicRoute}
                  onStartQuiz={handleStartQuiz}
                  onJumpToAssistant={handleJumpToAssistant}
                />
              </div>
            )}

            {subRoute === 'profile' && (
              <div className="space-y-6">
                <HeroBanner
                  student={dashboardData.profile.student}
                  recommendationType={dashboardData.learning_path.recommendation_type}
                />
                <StatCards profile={dashboardData.profile.overall_profile} />
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
                  <LearningProfile profile={dashboardData.profile.overall_profile} />
                  <AIDiagnosis
                    diagnosis={dashboardData.report.diagnosis}
                    profileDiagnosis={dashboardData.profile.diagnosis}
                  />
                </div>
                <WeakKnowledgePoints
                  weakPoints={dashboardData.profile.weak_knowledge_points}
                  prerequisitePoints={dashboardData.profile.prerequisite_knowledge_points}
                  onStartQuiz={handleStartQuiz}
                />
                <AISummary
                  aiSummary={dashboardData.report.ai_summary}
                  dailyPlan={dashboardData.report.daily_learning_plan}
                  optimizationSuggestions={dashboardData.report.optimization_suggestions}
                />
              </div>
            )}

            {subRoute === 'assistant' && (
              <div className="space-y-6">
                <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs">
                  <h2 className="text-xl font-bold text-slate-900">AI 学习伴学助手</h2>
                  <p className="text-xs text-slate-500 mt-1">
                    实时针对 {dashboardData.profile.student.student_name} 的学情进行苏格拉底式答疑与个性化辅导。
                  </p>
                </div>
                <div ref={assistantRef}>
                  <AIAssistant
                    currentStudentId={studentId}
                    studentName={dashboardData.profile.student.student_name}
                    isOnline={isOnline}
                    learningContext={learningContext}
                  />
                </div>
              </div>
            )}
          </div>
        ) : null}
        </MobileContainer>
      </main>

      {/* Footer */}
      <Footer />

      {/* 全局统一微测验模态抽屉 (Step 3: 打通全链路闭环) */}
      <BottomSheet
        open={!!activeQuiz}
        onClose={handleCloseQuiz}
        title={
          activeQuiz
            ? `${activeQuiz.knowledgeId} · ${activeQuiz.knowledgeName} 微测验突破`
            : '知识点微测验'
        }
      >
        {activeQuiz && (
          <KnowledgePointQuiz
            knowledgeId={activeQuiz.knowledgeId}
            knowledgeName={activeQuiz.knowledgeName}
            studentId={studentId}
            onBackToDetail={() => setActiveQuiz(null)}
            onFinish={handleCloseQuiz}
            onNextKnowledgePoint={handleNextKnowledgePoint}
          />
        )}
      </BottomSheet>

      {/* 考点精要速览微卡片模态框 (先学后测) */}
      <ConceptCardModal
        isOpen={!!activeConceptCard}
        card={activeConceptCard}
        onClose={handleCloseConceptCard}
        onStartQuiz={handleStartQuiz}
      />

      {/* 学习目标与新学生初始化模态框 */}
      <StudentInitModal
        isOpen={isInitModalOpen}
        onClose={() => setIsInitModalOpen(false)}
        onSubmit={handleInitStudentSubmit}
        onSelectPresetStudent={onSelectStudent}
      />

      {/* 3题极速前测与自适应学情诊断模态框 */}
      <PretestModal
        isOpen={isPretestModalOpen}
        onClose={() => setIsPretestModalOpen(false)}
        studentId={studentId}
        learningGoal={dashboardData?.profile?.student?.learning_goal}
        onRouteGenerated={(route) => {
          setDynamicRoute(route);
        }}
        onSelectFocus={(kid) => {
          handleViewConceptCard(kid, kid);
        }}
      />

      {/* Mobile Bottom Navigation (仅在移动端展示) */}
      <BottomNav />
    </div>
  );
};
