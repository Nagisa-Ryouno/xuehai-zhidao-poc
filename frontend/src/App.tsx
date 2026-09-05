import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Header } from './components/Header';
import { HeroBanner } from './components/HeroBanner';
import { StatCards } from './components/StatCards';
import { LearningProfile } from './components/LearningProfile';
import { AIDiagnosis } from './components/AIDiagnosis';
import { WeakKnowledgePoints } from './components/WeakKnowledgePoints';
import { KnowledgeGraph } from './components/KnowledgeGraph';
import { LearningPath } from './components/LearningPath';
import { AISummary } from './components/AISummary';
import { AIAssistant } from './components/AIAssistant';
import { LoadingSkeleton } from './components/LoadingSkeleton';
import { ErrorState } from './components/ErrorState';
import { Footer } from './components/Footer';

import { getStudents, getStudentDashboard, checkHealth } from './api';
import type { StudentListItem, StudentDashboardResponse } from './types';

export const App: React.FC = () => {
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [currentStudentId, setCurrentStudentId] = useState<string>('S001');
  const [dashboardData, setDashboardData] = useState<StudentDashboardResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSwitching, setIsSwitching] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(true);

  // Load students list and the initial student dashboard
  const initData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [online, studentsRes] = await Promise.all([
        checkHealth(),
        getStudents(),
      ]);

      setIsOnline(online);
      setStudents(studentsRes.students);

      const targetId = studentsRes.students[0]?.student_id || 'S001';
      setCurrentStudentId(targetId);

      const dashboard = await getStudentDashboard(targetId);
      setDashboardData(dashboard);
    } catch (err: unknown) {
      setIsOnline(false);
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('无法加载学情数据，请确认后端 API 服务是否正常启动。');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    initData();
  }, [initData]);

  // Handle student switching with a smooth transition
  const handleSelectStudent = async (studentId: string) => {
    if (studentId === currentStudentId) return;

    setCurrentStudentId(studentId);
    setIsSwitching(true);
    setErrorMessage(null);

    try {
      const dashboard = await getStudentDashboard(studentId);
      setDashboardData(dashboard);
      setIsOnline(true);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('切换学生数据失败，请重试。');
      }
    } finally {
      setIsSwitching(false);
    }
  };

  const assistantRef = useRef<HTMLDivElement | null>(null);

  const handleJumpToAssistant = () => {
    if (assistantRef.current) {
      assistantRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 selection:bg-indigo-100 selection:text-indigo-800">
      {/* Top Header */}
      <Header
        students={students}
        currentStudentId={currentStudentId}
        onSelectStudent={handleSelectStudent}
        isOnline={isOnline}
        isLoading={isLoading || isSwitching}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {isLoading ? (
          <LoadingSkeleton />
        ) : errorMessage ? (
          <ErrorState
            message={errorMessage}
            onRetry={initData}
            isRetrying={isLoading}
          />
        ) : dashboardData ? (
          <div
            className={`space-y-8 transition-opacity duration-300 ${
              isSwitching ? 'opacity-40 pointer-events-none' : 'opacity-100'
            }`}
          >
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
              currentStudentId={currentStudentId}
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
                currentStudentId={currentStudentId}
                studentName={dashboardData.profile.student.student_name}
                isOnline={isOnline}
              />
            </div>
          </div>
        ) : null}
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default App;
