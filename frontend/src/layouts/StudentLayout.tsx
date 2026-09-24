import React, { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from '../components/Header';
import { HeroBanner } from '../components/HeroBanner';
import { StatCards } from '../components/StatCards';
import { LearningProfile } from '../components/LearningProfile';
import { AIDiagnosis } from '../components/AIDiagnosis';
import { WeakKnowledgePoints } from '../components/WeakKnowledgePoints';
import { KnowledgeGraph } from '../components/KnowledgeGraph';
import { AISummary } from '../components/AISummary';
import { AIAssistant } from '../components/AIAssistant';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorState } from '../components/ErrorState';
import { Footer } from '../components/Footer';
import { BottomSheet } from '../components/common/BottomSheet';
import { KnowledgePointQuiz } from '../components/student/KnowledgePointQuiz';
// 核心首页子组件由 StudentHome 统一封装渲染 (包含 TodayActionCard 与 CurrentFocusCard)
import { resolveCurrentFocusTask } from '../components/student/taskFocusModel';
import { buildLearningContext } from '../components/student/learningContextModel';

import { useApp } from '../context/useApp';
import type {
  StudentListItem,
  StudentDashboardResponse,
  PathState,
  DynamicLearningRoute,
  StudentProgressResponse,
  WrongAnswerReviewResponse,
  CompanionMode,
  LearningActionResultResponse,
  TodayLearningAction,
  StudentRecommendationItem,
} from '../types';
import { CalendarCheck, BookOpen, Network, UserCheck, Bot } from 'lucide-react';
import { BottomNav } from '../components/student/BottomNav';
import { MobileContainer } from '../components/student/MobileContainer';
import { ConceptCardModal } from '../components/student/ConceptCardModal';
import { StudentInitModal } from '../components/student/StudentInitModal';
import { PretestModal } from '../components/student/PretestModal';
import { ProgressOverview } from '../components/student/ProgressOverview';
import { WrongAnswerReview } from '../components/student/WrongAnswerReview';
import { ResourceHub } from '../components/student/ResourceHub';
import { StudentHome } from '../components/student/StudentHome';
import { LearningSessionModal, type SessionStep } from '../components/student/LearningSessionModal';
import { type ConceptCardData } from '../components/student/conceptCardData';
import {
  initStudent,
  getDynamicPath,
  getStudentProgress,
  getStudentWrongAnswers,
  postLearningActionResult,
  getTodayLearningAction,
  getStudentRecommendations,
  type StudentInitRequest,
} from '../api';

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

  // 全链路学习会话状态 (Sprint 10-C Phase 2)
  const [learningSession, setLearningSession] = useState<{
    isOpen: boolean;
    action: TodayLearningAction | null;
    knowledgeId: string;
    knowledgeName: string;
    initialStep?: SessionStep;
  } | null>(null);

  // 页面切换时重置页面滚动位置到顶部
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, [subRoute]);

  // 学习目标设定与新学生模态框状态
  const [isInitModalOpen, setIsInitModalOpen] = useState<boolean>(false);

  // 3题极速前测与自适应动态航线状态 (Sprint 8-B)
  const [isPretestModalOpen, setIsPretestModalOpen] = useState<boolean>(false);
  const [dynamicRoute, setDynamicRoute] = useState<DynamicLearningRoute | null>(null);

  // 学情成效沉淀与错题复盘状态 (Sprint 8-C)
  const [profileSubTab, setProfileSubTab] = useState<'progress' | 'wrong_answers' | 'radar'>('progress');
  const [progressData, setProgressData] = useState<StudentProgressResponse | null>(null);
  const [wrongAnswerData, setWrongAnswerData] = useState<WrongAnswerReviewResponse | null>(null);
  const [isAnalyticsLoading, setIsAnalyticsLoading] = useState<boolean>(false);

  // AI 伴学上下文直通状态 (Sprint 9-A)
  const [activeCompanionContext, setActiveCompanionContext] = useState<{
    mode?: CompanionMode;
    knowledgeId?: string;
    questionId?: string;
    message?: string;
    resourceContext?: Record<string, any>;
  } | null>(null);

  // 学习行动完成与反思通知状态 (Sprint 9-B)
  const [latestActionResult, setLatestActionResult] = useState<LearningActionResultResponse | null>(null);

  // 今日学习行动状态 (Sprint 9-G / Sprint 10-C Phase 1)
  const [todayAction, setTodayAction] = useState<TodayLearningAction | null>(null);
  const [isTodayActionLoading, setIsTodayActionLoading] = useState<boolean>(false);
  const [todayActionError, setTodayActionError] = useState<string | null>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  // 老师建议状态 (Sprint 10-D Phase 4-E)
  const [recommendations, setRecommendations] = useState<StudentRecommendationItem[]>([]);
  const [isRecommendationsLoading, setIsRecommendationsLoading] = useState<boolean>(false);
  const [recommendationsError, setRecommendationsError] = useState<string | null>(null);

  const fetchDynamicRoute = useCallback(async () => {
    try {
      const goal = dashboardData?.profile?.student?.learning_goal;
      const route = await getDynamicPath(studentId, goal);
      setDynamicRoute(route);
    } catch {
      setDynamicRoute(null);
    }
  }, [studentId, dashboardData]);

  const fetchAnalyticsData = useCallback(async () => {
    setIsAnalyticsLoading(true);
    setAnalyticsError(null);
    const reqStudentId = studentId;
    try {
      const [pData, wData] = await Promise.all([
        getStudentProgress(studentId),
        getStudentWrongAnswers(studentId),
      ]);
      if (reqStudentId === studentId) {
        setProgressData(pData);
        setWrongAnswerData(wData);
      }
    } catch (err) {
      console.error('Failed to fetch analytics data:', err);
      if (reqStudentId === studentId) {
        setAnalyticsError('暂时无法加载学习成效数据，请稍后重试');
      }
    } finally {
      if (reqStudentId === studentId) {
        setIsAnalyticsLoading(false);
      }
    }
  }, [studentId]);

  const fetchTodayAction = useCallback(async () => {
    if (!studentId) return;
    setIsTodayActionLoading(true);
    setTodayActionError(null);
    const reqStudentId = studentId;
    try {
      const res = await getTodayLearningAction(studentId);
      if (reqStudentId === studentId) {
        setTodayAction(res.action);
      }
    } catch (err) {
      console.warn('Failed to fetch today learning action:', err);
      if (reqStudentId === studentId) {
        setTodayAction(null);
        setTodayActionError('暂时无法获取今日学习安排，请稍后重试');
      }
    } finally {
      if (reqStudentId === studentId) {
        setIsTodayActionLoading(false);
      }
    }
  }, [studentId]);

  const fetchRecommendations = useCallback(async () => {
    if (!studentId) return;
    setIsRecommendationsLoading(true);
    setRecommendationsError(null);
    const reqStudentId = studentId;
    try {
      const res = await getStudentRecommendations(studentId);
      if (reqStudentId === studentId) {
        setRecommendations(res.recommendations || []);
      }
    } catch (err) {
      console.warn('Failed to fetch teacher recommendations:', err);
      if (reqStudentId === studentId) {
        setRecommendations([]);
        setRecommendationsError('暂时无法加载老师建议');
      }
    } finally {
      if (reqStudentId === studentId) {
        setIsRecommendationsLoading(false);
      }
    }
  }, [studentId]);

  useEffect(() => {
    fetchDynamicRoute();
    fetchAnalyticsData();
    fetchTodayAction();
    fetchRecommendations();
  }, [fetchDynamicRoute, fetchAnalyticsData, fetchTodayAction, fetchRecommendations]);

  // 学生上下文切换时安全关闭微测验与速览卡片，立即清空旧生状态，杜绝上下文污染 (Sprint 3 / Sprint 9-G 契约约束)
  useEffect(() => {
    setActiveQuiz(null);
    setActiveConceptCard(null);
    setProgressData(null);
    setWrongAnswerData(null);
    setDynamicRoute(null);
    setActiveCompanionContext(null);
    setLatestActionResult(null);
    setTodayAction(null);
    setTodayActionError(null);
    setAnalyticsError(null);
    setRecommendations([]);
    setRecommendationsError(null);
  }, [studentId]);

  const handleCloseSession = useCallback(() => {
    setLearningSession(null);
    fetchDynamicRoute();
    fetchAnalyticsData();
    fetchTodayAction();
    fetchRecommendations();
    if (onRefresh) {
      onRefresh();
    }
  }, [fetchDynamicRoute, fetchAnalyticsData, fetchTodayAction, fetchRecommendations, onRefresh]);

  const handleFinishSession = useCallback(
    (nextKnowledgeId?: string, nextKnowledgeName?: string) => {
      fetchDynamicRoute();
      fetchAnalyticsData();
      fetchTodayAction();
      fetchRecommendations();
      if (onRefresh) {
        onRefresh();
      }
      if (nextKnowledgeId) {
        setLearningSession({
          isOpen: true,
          action: null,
          knowledgeId: nextKnowledgeId,
          knowledgeName: nextKnowledgeName || `考点 ${nextKnowledgeId}`,
          initialStep: 'ENTRY',
        });
      } else {
        setLearningSession(null);
      }
    },
    [fetchDynamicRoute, fetchAnalyticsData, fetchTodayAction, fetchRecommendations, onRefresh]
  );

  const handleStartQuiz = useCallback(
    (knowledgeId: string, knowledgeName: string) => {
      setLearningSession({
        isOpen: true,
        action: null,
        knowledgeId,
        knowledgeName: knowledgeName || '微观经济学考点',
        initialStep: 'QUIZ',
      });
    },
    []
  );

  const handleViewConceptCard = useCallback(
    (knowledgeId: string, knowledgeName: string) => {
      setLearningSession({
        isOpen: true,
        action: null,
        knowledgeId,
        knowledgeName: knowledgeName || '微观经济学考点',
        initialStep: 'CONCEPT',
      });
    },
    []
  );

  const handleCloseConceptCard = useCallback(() => {
    if (activeConceptCard) {
      postLearningActionResult({
        student_id: studentId,
        action_id: `act-concept-${Date.now()}`,
        action_type: 'READ_CONCEPT',
        knowledge_id: activeConceptCard.knowledgeId,
      })
        .then((res) => {
          setLatestActionResult(res);
        })
        .catch((err) => console.warn('Companion reflection notification error:', err));
    }
    setActiveConceptCard(null);
    fetchAnalyticsData();
    fetchTodayAction();
  }, [activeConceptCard, studentId, fetchAnalyticsData, fetchTodayAction]);

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
    if (activeQuiz) {
      postLearningActionResult({
        student_id: studentId,
        action_id: `act-quiz-${Date.now()}`,
        action_type: 'TARGETED_PRACTICE',
        knowledge_id: activeQuiz.knowledgeId,
      })
        .then((res) => {
          setLatestActionResult(res);
        })
        .catch((err) => console.warn('Companion reflection notification error:', err));
    }
    setActiveQuiz(null);
    fetchDynamicRoute();
    fetchAnalyticsData();
    fetchTodayAction();
    if (onRefresh) {
      onRefresh();
    }
  }, [activeQuiz, studentId, onRefresh, fetchDynamicRoute, fetchAnalyticsData, fetchTodayAction]);

  const handleNextKnowledgePoint = useCallback(
    (nextKnowledgeId: string, nextKnowledgeName: string) => {
      setActiveQuiz({
        knowledgeId: nextKnowledgeId,
        knowledgeName: nextKnowledgeName,
      });
      fetchDynamicRoute();
      fetchAnalyticsData();
      fetchTodayAction();
      if (onRefresh) {
        onRefresh();
      }
    },
    [onRefresh, fetchDynamicRoute, fetchAnalyticsData, fetchTodayAction]
  );

  const handleTodayActionCTA = useCallback(
    (action: TodayLearningAction) => {
      if (action.action_type === 'VIEW_PROGRESS' || action.action_type === 'NONE') {
        navigate('/student/profile');
        return;
      }
      const kid = action.knowledge_id || 'K01';
      const kname = action.knowledge_name || '微观经济学核心考点';

      // 所有学习类行动统一进入 Learning Session 的 ENTRY 步骤，实现统一导引与权威掌握度呈现
      setLearningSession({
        isOpen: true,
        action,
        knowledgeId: kid,
        knowledgeName: kname,
        initialStep: 'ENTRY',
      });
    },
    [navigate]
  );

  const handleJumpToAssistant = () => {
    setActiveCompanionContext(null);
    navigate('/student/assistant');
    if (assistantRef.current) {
      assistantRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleJumpToAssistantWithContext = useCallback(
    (ctx: {
      mode?: CompanionMode;
      knowledgeId?: string;
      questionId?: string;
      message?: string;
      resourceContext?: Record<string, any>;
    }) => {
      setActiveCompanionContext(ctx);
      navigate('/student/assistant');
      if (assistantRef.current) {
        assistantRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    },
    [navigate]
  );

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

  const currentMasteryPercent = useMemo(() => {
    const targetKid = todayAction?.knowledge_id || focusResult.focus?.knowledgeId;
    if (!targetKid) return null;
    const foundKp = progressData?.knowledge_points?.find((k) => k.knowledge_id === targetKid);
    if (foundKp) return Math.round(foundKp.mastery * 100);
    if (focusResult.focus?.currentMasteryPercent !== undefined) {
      return Math.round(focusResult.focus.currentMasteryPercent);
    }
    return null;
  }, [todayAction, focusResult, progressData]);

  // 5 个核心 Tab 定义（包含 Sprint 9-C 学习资源中心）
  const tabs = [
    { id: 'tasks', label: '今日任务', path: '/student/tasks', icon: CalendarCheck },
    { id: 'resources', label: '学习资源', path: '/student/resources', icon: BookOpen },
    { id: 'graph', label: '知识图谱', path: '/student/graph', icon: Network },
    { id: 'profile', label: '学情档案', path: '/student/profile', icon: UserCheck },
    { id: 'assistant', label: 'AI伴学', path: '/student/assistant', icon: Bot },
  ] as const;

  return (
    <div
      data-testid="student-layout"
      className="min-h-screen flex flex-col bg-slate-50 text-slate-900 selection:bg-indigo-100 selection:text-indigo-800 overflow-x-hidden w-full max-w-full"
    >
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
          {/* 离线状态人本提示 (绝不伪造离线同步) */}
          {!isOnline && (
            <div
              data-testid="pwa-offline-notice"
              className="mb-4 p-3.5 rounded-2xl bg-amber-50/90 border border-amber-200 text-amber-900 text-xs flex items-center justify-between gap-3 shadow-2xs"
            >
              <div className="flex items-center gap-2">
                <span className="text-base shrink-0">📡</span>
                <span className="leading-relaxed">
                  <strong>当前处于离线模式：</strong>已缓存的基础页面与内容可继续查看；涉及实时学情同步、微测验评分与 AI 伴学需恢复网络后使用。
                </span>
              </div>
              <button
                type="button"
                onClick={onRetry}
                className="shrink-0 px-3 py-1.5 rounded-xl bg-amber-200/80 hover:bg-amber-300 text-amber-950 font-bold text-xs transition-colors cursor-pointer"
              >
                重试连接
              </button>
            </div>
          )}

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
              <StudentHome
                student={dashboardData.profile.student}
                todayAction={todayAction}
                isTodayActionLoading={isTodayActionLoading}
                todayActionError={todayActionError}
                currentMasteryPercent={currentMasteryPercent}
                focusResult={focusResult}
                dynamicRoute={dynamicRoute}
                progressData={progressData}
                isAnalyticsLoading={isAnalyticsLoading}
                analyticsError={analyticsError}
                recommendations={recommendations}
                isRecommendationsLoading={isRecommendationsLoading}
                recommendationsError={recommendationsError}
                onRetryRecommendations={fetchRecommendations}
                onExecuteTodayAction={handleTodayActionCTA}
                onStartQuiz={handleStartQuiz}
                onViewConceptCard={handleViewConceptCard}
                onAskAI={(kid, kname) =>
                  handleJumpToAssistantWithContext({
                    mode: 'concept_explain',
                    knowledgeId: kid,
                    message: `请老师精讲考点【${kid} ${kname}】`,
                  })
                }
                onViewGraph={() => navigate('/student/graph')}
                onViewResources={(kid) =>
                  navigate(`/student/resources?focus=recommended${kid ? `&kid=${kid}` : ''}`)
                }
                onNavigate={navigate}
                onRetryTodayAction={fetchTodayAction}
                onRetryAnalytics={fetchAnalyticsData}
              />
            )}

            {subRoute === 'resources' && (
              <ResourceHub
                studentId={studentId}
                initialKnowledgeId={focusResult.focus?.knowledgeId || 'K01'}
                onOpenConceptCard={handleViewConceptCard}
                onStartQuiz={handleStartQuiz}
                onAskAI={(kid, kname, prefill, resourceContext) => {
                  handleJumpToAssistantWithContext({
                    mode: 'concept_explain',
                    knowledgeId: kid,
                    message: prefill || `请老师精讲考点【${kid} ${kname}】`,
                    resourceContext,
                  });
                }}
              />
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

                {/* Profile Sub-view Navigation Pill Bar */}
                <div className="flex items-center gap-2 p-1.5 bg-slate-200/70 rounded-2xl w-fit max-w-full overflow-x-auto no-scrollbar">
                  <button
                    type="button"
                    onClick={() => setProfileSubTab('progress')}
                    className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
                      profileSubTab === 'progress'
                        ? 'bg-white text-indigo-700 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <span>📊 30考点掌握度全览</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setProfileSubTab('wrong_answers')}
                    className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
                      profileSubTab === 'wrong_answers'
                        ? 'bg-white text-rose-700 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <span>📕 错题复盘本</span>
                    {wrongAnswerData && wrongAnswerData.total_wrong > 0 && (
                      <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-rose-100 text-rose-700">
                        {wrongAnswerData.total_wrong}
                      </span>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => setProfileSubTab('radar')}
                    className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
                      profileSubTab === 'radar'
                        ? 'bg-white text-slate-900 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <span>🧭 综合能力画像</span>
                  </button>
                </div>

                {profileSubTab === 'progress' && (
                  <ProgressOverview
                    progressData={progressData}
                    isLoading={isAnalyticsLoading}
                    onViewConceptCard={handleViewConceptCard}
                    onStartQuiz={handleStartQuiz}
                    onAskAISummary={() =>
                      handleJumpToAssistantWithContext({
                        mode: 'learning_summary',
                        message: '请老师为我生成当前的阶段学习成效全景总结',
                      })
                    }
                  />
                )}

                {profileSubTab === 'wrong_answers' && (
                  <WrongAnswerReview
                    wrongAnswerData={wrongAnswerData}
                    isLoading={isAnalyticsLoading}
                    onViewConceptCard={handleViewConceptCard}
                    onStartQuiz={handleStartQuiz}
                    onAskAI={(qid, kid) =>
                      handleJumpToAssistantWithContext({
                        mode: 'wrong_answer_review',
                        questionId: qid,
                        knowledgeId: kid,
                        message: `请老师帮我详细剖析错题【${qid}】`,
                      })
                    }
                  />
                )}

                {profileSubTab === 'radar' && (
                  <div className="space-y-6">
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
                    initialContext={activeCompanionContext}
                    latestActionResult={latestActionResult}
                    onNavigateToQuiz={(kid) => {
                      const kpName =
                        dashboardData.profile.weak_knowledge_points.find(
                          (w) => w.knowledge_id === kid
                        )?.knowledge_name || kid;
                      handleStartQuiz(kid, kpName);
                    }}
                    onNavigateToConcept={(kid) => {
                      const kpName =
                        dashboardData.profile.weak_knowledge_points.find(
                          (w) => w.knowledge_id === kid
                        )?.knowledge_name || kid;
                      handleViewConceptCard(kid, kpName);
                    }}
                    onNavigateToProgress={() => {
                      navigate('/student/profile');
                      setProfileSubTab('progress');
                    }}
                    onNavigateToWrongAnswers={() => {
                      navigate('/student/profile');
                      setProfileSubTab('wrong_answers');
                    }}
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

      {/* 全链路自适应学习会话模态框 (Sprint 10-C Phase 2) */}
      {learningSession && (
        <LearningSessionModal
          isOpen={learningSession.isOpen}
          studentId={studentId}
          action={learningSession.action}
          knowledgeId={learningSession.knowledgeId}
          knowledgeName={learningSession.knowledgeName}
          initialStep={learningSession.initialStep}
          currentMasteryPercent={currentMasteryPercent}
          onClose={handleCloseSession}
          onFinishSession={handleFinishSession}
          onNavigateToTasks={() => {
            navigate('/student/tasks');
            handleCloseSession();
          }}
        />
      )}

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
