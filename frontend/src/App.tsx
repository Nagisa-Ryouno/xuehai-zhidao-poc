import React, { useState, useEffect, useCallback, useRef } from 'react';
import { AppProvider } from './context/AppContext';
import { useApp } from './context/useApp';
import { StudentLayout } from './layouts/StudentLayout';
import { TeacherLayout } from './layouts/TeacherLayout';
import { getStudents, getStudentDashboard, checkHealth, getStudentPathStates, initStudent } from './api';
import type { StudentListItem, StudentDashboardResponse, PathState } from './types';

const DEMO_STUDENT_STORAGE_KEY = 'xuehai_demo_student_id';

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
      let studentList = [...studentsRes.students];

      // 读取持久化的 Demo 学生 ID
      let targetId = studentId;
      if (!targetId && typeof window !== 'undefined') {
        targetId = localStorage.getItem(DEMO_STUDENT_STORAGE_KEY) || '';
      }

      // 如果当前是教师端角色，且 targetId 不是预设学生，优先使用 S001 展现班级宏观数据
      if (role === 'teacher' && (!targetId || targetId.startsWith('DEMO_'))) {
        targetId = 'S001';
      }

      // 学生端首次进入：如果没有任何已保存的学生 ID，创建全新的 Demo 学生
      if (role === 'student' && !targetId) {
        try {
          const initRes = await initStudent({
            student_name: '新同学01',
            major: '经济学',
            grade: '大一',
            learning_goal: '微观经济学基础入门',
            start_knowledge_id: 'K01',
          });
          if (initRes && initRes.student_id) {
            targetId = initRes.student_id;
            if (typeof window !== 'undefined') {
              localStorage.setItem(DEMO_STUDENT_STORAGE_KEY, targetId);
              localStorage.setItem('xuehai_is_new_demo', 'true');
            }
          }
        } catch (e) {
          console.warn('Failed to auto-init demo student, falling back to S001:', e);
          targetId = 'S001';
        }
      }

      // 兜底防御
      if (!targetId) {
        targetId = studentsRes.students[0]?.student_id || 'S001';
      }

      activeStudentRef.current = targetId;
      selectStudent(targetId);

      const [dashboard, pathStatesRes] = await Promise.all([
        getStudentDashboard(targetId),
        getStudentPathStates(targetId).catch(() => ({ student_id: targetId, states: {} as Record<string, PathState> })),
      ]);

      // 防御异步竞态：如果当前目标学生已被切换或已有新请求，丢弃过期响应
      if (activeStudentRef.current !== targetId || reqId !== requestIdRef.current) return;

      // 如果当前学生是 Demo 学生且不在 students 列表中，将其动态加入下拉列表中展示
      if (dashboard?.profile?.student) {
        const exists = studentList.some((s) => s.student_id === targetId);
        if (!exists) {
          studentList = [
            {
              student_id: targetId,
              student_name: dashboard.profile.student.student_name,
              major: dashboard.profile.student.major,
              grade: dashboard.profile.student.grade,
              learning_goal: dashboard.profile.student.learning_goal,
              average_accuracy: dashboard.profile.overall_profile.average_accuracy || 0,
              mastery_level: dashboard.profile.overall_profile.mastery_level || '薄弱',
              activity_level: 'active',
              completion_level: 'in_progress',
            },
            ...studentList,
          ];
        }
      }

      setStudents(studentList);
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
      setIsLoading(false);
    }
  }, [selectStudent]);

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

  // 监听浏览器原生 online / offline 事件，动态更新网络状态
  // 红线硬约束：网络恢复 (online) 最多只能触发只读静默刷新，绝对禁止自动补发任何写操作或重放学习状态
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      handleRefreshData();
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [handleRefreshData]);

  // 学生切换处理 (具备严格的异步竞态防御与上下文隔离)
  const handleSelectStudent = async (targetStudentId: string) => {
    if (typeof window !== 'undefined' && targetStudentId) {
      localStorage.setItem(DEMO_STUDENT_STORAGE_KEY, targetStudentId);
    }
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
      setIsSwitching(false);
      setIsLoading(false);
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
