import React, { useRef } from 'react';
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

import { useApp } from '../context/useApp';
import type { StudentListItem, StudentDashboardResponse } from '../types';
import { CalendarCheck, Network, UserCheck, Bot } from 'lucide-react';

interface StudentLayoutProps {
  students: StudentListItem[];
  dashboardData: StudentDashboardResponse | null;
  isLoading: boolean;
  isSwitching: boolean;
  errorMessage: string | null;
  isOnline: boolean;
  onSelectStudent: (studentId: string) => void;
  onRetry: () => void;
}

export const StudentLayout: React.FC<StudentLayoutProps> = ({
  students,
  dashboardData,
  isLoading,
  isSwitching,
  errorMessage,
  isOnline,
  onSelectStudent,
  onRetry,
}) => {
  const { studentId, subRoute, navigate } = useApp();
  const assistantRef = useRef<HTMLDivElement | null>(null);

  const handleJumpToAssistant = () => {
    navigate('/student/assistant');
    if (assistantRef.current) {
      assistantRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

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
      <Header
        students={students}
        currentStudentId={studentId}
        onSelectStudent={onSelectStudent}
        isOnline={isOnline}
        isLoading={isLoading || isSwitching}
      />

      {/* Sub-route Navigation Pill Bar (P0-1 骨架，便于桌面与移动端预览各子路由) */}
      <div className="bg-white border-b border-slate-200/80 sticky top-18 z-20 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center space-x-1 sm:space-x-2 py-2 overflow-x-auto no-scrollbar">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = subRoute === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
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
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
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

                {/* 2. Core Academic Statistics Cards */}
                <StatCards profile={dashboardData.profile.overall_profile} />

                {/* 3. Learning Profile & AI Diagnosis */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
                  <LearningProfile profile={dashboardData.profile.overall_profile} />
                  <AIDiagnosis
                    diagnosis={dashboardData.report.diagnosis}
                    profileDiagnosis={dashboardData.profile.diagnosis}
                  />
                </div>

                {/* 4. Weak Knowledge Points */}
                <WeakKnowledgePoints
                  weakPoints={dashboardData.profile.weak_knowledge_points}
                  prerequisitePoints={dashboardData.profile.prerequisite_knowledge_points}
                />

                {/* 5. AI Knowledge Graph Workbench */}
                <KnowledgeGraph
                  currentStudentId={studentId}
                  studentName={dashboardData.profile.student.student_name}
                  onJumpToAssistant={handleJumpToAssistant}
                />

                {/* 6. AI Generated Learning Path (Core Timeline) */}
                <LearningPath
                  learningPath={dashboardData.learning_path.learning_path}
                  recommendationType={dashboardData.learning_path.recommendation_type}
                  studentName={dashboardData.profile.student.student_name}
                />

                {/* 7. AI Summary & Daily Plan */}
                <AISummary
                  aiSummary={dashboardData.report.ai_summary}
                  dailyPlan={dashboardData.report.daily_learning_plan}
                  optimizationSuggestions={dashboardData.report.optimization_suggestions}
                />

                {/* 8. Interactive AI Learning Assistant */}
                <div ref={assistantRef}>
                  <AIAssistant
                    currentStudentId={studentId}
                    studentName={dashboardData.profile.student.student_name}
                    isOnline={isOnline}
                  />
                </div>
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
                  />
                </div>
              </div>
            )}
          </div>
        ) : null}
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
};
