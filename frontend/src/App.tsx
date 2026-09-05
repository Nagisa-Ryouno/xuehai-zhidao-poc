import React, { useState, useEffect, useCallback } from 'react';
import { AppProvider } from './context/AppContext';
import { useApp } from './context/useApp';
import { StudentLayout } from './layouts/StudentLayout';
import { TeacherLayout } from './layouts/TeacherLayout';
import { getStudents, getStudentDashboard, checkHealth } from './api';
import type { StudentListItem, StudentDashboardResponse } from './types';

const AppContent: React.FC = () => {
  const { role, studentId, selectStudent } = useApp();
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [dashboardData, setDashboardData] = useState<StudentDashboardResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSwitching, setIsSwitching] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(true);

  // 初始化加载学生列表与初始学生学情
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

      // 若当前 studentId 未加载，默认使用首个学生或 S001
      const targetId = studentId || studentsRes.students[0]?.student_id || 'S001';
      selectStudent(targetId);

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
  }, [studentId, selectStudent]);

  useEffect(() => {
    initData();
  }, [initData]);

  // 学生切换处理
  const handleSelectStudent = async (targetStudentId: string) => {
    if (targetStudentId === studentId && dashboardData) return;

    selectStudent(targetStudentId);
    setIsSwitching(true);
    setErrorMessage(null);

    try {
      const dashboard = await getStudentDashboard(targetStudentId);
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

  // 严格根据当前激活角色渲染对应的独立 Layout
  if (role === 'teacher') {
    return (
      <TeacherLayout
        students={students}
        isOnline={isOnline}
        isLoading={isLoading || isSwitching}
        onSelectStudent={handleSelectStudent}
      />
    );
  }

  return (
    <StudentLayout
      students={students}
      dashboardData={dashboardData}
      isLoading={isLoading}
      isSwitching={isSwitching}
      errorMessage={errorMessage}
      isOnline={isOnline}
      onSelectStudent={handleSelectStudent}
      onRetry={initData}
    />
  );
};

export const App: React.FC = () => {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
};

export default App;
