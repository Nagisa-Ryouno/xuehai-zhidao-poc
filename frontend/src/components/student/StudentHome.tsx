import React from 'react';
import { BookOpen } from 'lucide-react';
import { TodayActionCard } from './TodayActionCard';
import { CurrentFocusCard } from './CurrentFocusCard';
import { TeacherRecommendationCard } from './TeacherRecommendationCard';
import { RecentProgressCard } from './RecentProgressCard';
import type {
  StudentBasic,
  TodayLearningAction,
  StudentProgressResponse,
  DynamicLearningRoute,
  StudentRecommendationItem,
} from '../../types';
import type { CurrentFocusResult } from './taskFocusModel';

export interface StudentHomeProps {
  student: StudentBasic;
  todayAction: TodayLearningAction | null;
  isTodayActionLoading: boolean;
  todayActionError?: string | null;
  currentMasteryPercent?: number | null;
  focusResult: CurrentFocusResult;
  isFocusLoading?: boolean;
  focusError?: string | null;
  dynamicRoute?: DynamicLearningRoute | null;
  progressData: StudentProgressResponse | null;
  isAnalyticsLoading?: boolean;
  analyticsError?: string | null;
  recommendations?: StudentRecommendationItem[];
  isRecommendationsLoading?: boolean;
  recommendationsError?: string | null;
  onRetryRecommendations?: () => void;
  onExecuteTodayAction: (action: TodayLearningAction) => void;
  onStartQuiz: (knowledgeId: string, knowledgeName: string) => void;
  onViewConceptCard: (knowledgeId: string, knowledgeName: string) => void;
  onAskAI?: (knowledgeId: string, knowledgeName: string) => void;
  onViewGraph?: () => void;
  onViewResources?: (knowledgeId: string) => void;
  onNavigate: (path: string) => void;
  onRetryTodayAction?: () => void;
  onRetryFocus?: () => void;
  onRetryAnalytics?: () => void;
}

export const StudentHome: React.FC<StudentHomeProps> = ({
  student,
  todayAction,
  isTodayActionLoading,
  todayActionError = null,
  currentMasteryPercent = null,
  focusResult,
  isFocusLoading = false,
  focusError = null,
  dynamicRoute,
  progressData,
  isAnalyticsLoading = false,
  analyticsError = null,
  recommendations = [],
  isRecommendationsLoading = false,
  recommendationsError = null,
  onRetryRecommendations,
  onExecuteTodayAction,
  onStartQuiz,
  onViewConceptCard,
  onAskAI,
  onViewGraph,
  onViewResources,
  onNavigate,
  onRetryTodayAction,
  onRetryFocus,
  onRetryAnalytics,
}) => {
  // 根据真实本地时段给出自然的问候语
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return '早上好';
    if (hour < 18) return '下午好';
    return '晚上好';
  };

  const greeting = getGreeting();

  return (
    <div data-testid="student-home" className="space-y-6 max-w-4xl mx-auto w-full">
      {/* 1. Greeting 模块 */}
      <section data-testid="student-greeting" className="space-y-1.5 pt-1 sm:pt-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200/80">
            <BookOpen className="w-3 h-3 text-slate-400" />
            {student.major} · {student.grade}
          </span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          {greeting}，{student.student_name} <span className="inline-block animate-wave">👋</span>
        </h1>
        <p className="text-sm sm:text-base text-slate-600 font-medium leading-relaxed">
          今天也学一点吧
        </p>
      </section>

      {/* 2. Today Action 模块（首页主任务） */}
      <section aria-label="今日学习行动" className="space-y-2">
        <TodayActionCard
          action={todayAction}
          loading={isTodayActionLoading}
          error={todayActionError}
          currentMasteryPercent={currentMasteryPercent}
          onExecuteCTA={onExecuteTodayAction}
          onRetry={onRetryTodayAction}
        />
      </section>

      {/* 3. Current Focus 模块（学习上下文与下一步行动） */}
      <section aria-label="当前学习焦点" className="space-y-2">
        <CurrentFocusCard
          focusResult={focusResult}
          loading={isFocusLoading}
          error={focusError}
          dynamicRoute={dynamicRoute}
          onStartQuiz={onStartQuiz}
          onViewConceptCard={onViewConceptCard}
          onAskAI={onAskAI}
          onViewGraph={onViewGraph}
          onViewResources={onViewResources}
          onRetry={onRetryFocus}
        />
      </section>

      {/* 4. Teacher Recommendation 模块（老师建议，辅助层） */}
      <section aria-label="老师建议" className="space-y-2">
        <TeacherRecommendationCard
          recommendations={recommendations}
          loading={isRecommendationsLoading}
          error={recommendationsError}
          onRetry={onRetryRecommendations}
          onViewConceptCard={onViewConceptCard}
          onStartQuiz={onStartQuiz}
        />
      </section>

      {/* 5. Recent Progress 模块（阶段学情沉淀） */}
      <section aria-label="最近学习进展" className="space-y-2">
        <RecentProgressCard
          progress={progressData}
          loading={isAnalyticsLoading}
          error={analyticsError}
          onRetry={onRetryAnalytics}
          onViewProfile={() => onNavigate('/student/profile')}
        />
      </section>
    </div>
  );
};
