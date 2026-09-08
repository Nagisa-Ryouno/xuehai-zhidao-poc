import React, { useState, useEffect, useCallback, useRef } from 'react';
import { AppProvider } from './context/AppContext';
import { useApp } from './context/useApp';
import { StudentLayout } from './layouts/StudentLayout';
import { TeacherLayout } from './layouts/TeacherLayout';
import { getStudents, getStudentDashboard, checkHealth, getStudentPathStates } from './api';
import type { StudentListItem, StudentDashboardResponse, PathState } from './types';

const AppContent: React.FC = () => {
  const { role, studentId, selectStudent } = useApp();
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [dashboardData, setDashboardData] = useState<StudentDashboardResponse | null>(null);
  const [pathStates, setPathStates] = useState<Record<string, PathState>>({});

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSwitching, setIsSwitching] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isOnline, setIsOnline] = useState<boolean>(true);

  // 异步竞态隔离 Ref：保证任何过期响应绝不污染最新选中的学生状态 (Sprint 3/5 约束)
  const activeStudentRef = useRef<string>(studentId);
  const requestIdRef = useRef<number>(0);
  useEffect(() => {
    activeStudentRef.current = studentId;
  }, [studentId]);

  // 初始化加载学生列表与初始学生学情
  const initData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    const reqId = ++requestIdRef.current;
    try {
      const [online, studentsRes] = await Promise.all([
        checkHealth(),
        getStudents(),
      ]);

      setIsOnline(online);
      setStudents(studentsRes.students);

      // 若当前 studentId 未加载，默认使用首个学生或 S001
      const targetId = studentId || studentsRes.students[0]?.student_id || 'S001';
      activeStudentRef.current = targetId;
      selectStudent(targetId);

      const [dashboard, pathStatesRes] = await Promise.all([
        getStudentDashboard(targetId),
        getStudentPathStates(targetId).catch(() => ({ student_id: targetId, states: {} as Record<string, PathState> })),
      ]);

      // 防御异步竞态：如果当前目标学生已被切换或已有新请求，丢弃过期响应
      if (activeStudentRef.current !== targetId || reqId !== requestIdRef.current) return;

      setDashboardData(dashboard);
      setPathStates(pathStatesRes.states || {});
    } catch (err: unknown) {
      if (reqId !== requestIdRef.current) return;
      setIsOnline(false);
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('无法加载学情数据，请确认后端 API 服务是否正常启动。');
      }
    } finally {
      if (reqId === requestIdRef.current) {
        setIsLoading(false);
      }
    }
  }, [studentId, selectStudent]);

  useEffect(() => {
    initData();
  }, [initData]);

  // 静默刷新当前学生的学情与路径状态 (无页面重载，闭环自适应体验)
  const handleRefreshData = useCallback(async () => {
    if (!studentId) return;
    const reqStudentId = studentId;
    const reqId = ++requestIdRef.current;
    try {
      const [dashboard, pathStatesRes] = await Promise.all([
        getStudentDashboard(reqStudentId),
        getStudentPathStates(reqStudentId).catch(() => ({ student_id: reqStudentId, states: {} as Record<string, PathState> })),
      ]);

      // 防御异步竞态：如果当前目标学生已被切换或已有新请求，丢弃过期刷新响应
      if (activeStudentRef.current !== reqStudentId || reqId !== requestIdRef.current) return;

      setDashboardData(dashboard);
      setPathStates(pathStatesRes.states || {});
      setIsOnline(true);
    } catch {
      // 静默刷新失败不打断当前 UI
    }
  }, [studentId]);

  // 学生切换处理 (具备严格的异步竞态防御与上下文隔离)
  const handleSelectStudent = async (targetStudentId: string) => {
    if (targetStudentId === studentId && dashboardData) return;

    activeStudentRef.current = targetStudentId;
    const reqId = ++requestIdRef.current;
    selectStudent(targetStudentId);
    setIsSwitching(true);
    setErrorMessage(null);

    try {
      const [dashboard, pathStatesRes] = await Promise.all([
        getStudentDashboard(targetStudentId),
        getStudentPathStates(targetStudentId).catch(() => ({ student_id: targetStudentId, states: {} as Record<string, PathState> })),
      ]);

      // 防御异步竞态：如果用户快速连续切换或已有更新请求，丢弃旧响应
      if (activeStudentRef.current !== targetStudentId || reqId !== requestIdRef.current) return;

      setDashboardData(dashboard);
      setPathStates(pathStatesRes.states || {});
      setIsOnline(true);
    } catch (err: unknown) {
      if (activeStudentRef.current !== targetStudentId || reqId !== requestIdRef.current) return;
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('切换学生数据失败，请重试。');
      }
    } finally {
      if (activeStudentRef.current === targetStudentId && reqId === requestIdRef.current) {
        setIsSwitching(false);
      }
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
      pathStates={pathStates}
      isLoading={isLoading}
      isSwitching={isSwitching}
      errorMessage={errorMessage}
      isOnline={isOnline}
      onSelectStudent={handleSelectStudent}
      onRetry={initData}
      onRefresh={handleRefreshData}
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
