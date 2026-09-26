import React, { useState, useEffect, useCallback, type ReactNode } from 'react';
import {
  type AppRole,
  type RouterState,
  createRouterState,
  switchRole as routerSwitchRole,
  navigateState,
  selectStudentState,
} from '../router';
import { AppContext } from './AppContextObject';
import type { AppContextValue } from './types';

const DEMO_STUDENT_STORAGE_KEY = 'xuehai_demo_student_id';

export interface AppProviderProps {
  children: ReactNode;
  initialPath?: string;
  initialStudentId?: string;
}

export const AppProvider: React.FC<AppProviderProps> = ({
  children,
  initialPath,
  initialStudentId,
}) => {
  const getInitialPath = (): string => {
    if (initialPath) return initialPath;
    if (typeof window !== 'undefined' && window.location.pathname) {
      return window.location.pathname;
    }
    return '/student/tasks';
  };

  const getInitialStudentId = (): string => {
    if (initialStudentId) return initialStudentId;
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(DEMO_STUDENT_STORAGE_KEY);
      if (saved) return saved;
    }
    return '';
  };

  const [routerState, setRouterState] = useState<RouterState>(() =>
    createRouterState(getInitialPath(), getInitialStudentId())
  );

  // 同步浏览器 URL
  const syncBrowserUrl = useCallback((path: string, replace = false) => {
    if (typeof window !== 'undefined' && window.location.pathname !== path) {
      if (replace) {
        window.history.replaceState({ path }, '', path);
      } else {
        window.history.pushState({ path }, '', path);
      }
    }
  }, []);

  // 初始化时若需要重定向（例如 / -> /student/tasks），执行 replaceState
  useEffect(() => {
    syncBrowserUrl(routerState.path, true);
  }, [routerState.path, syncBrowserUrl]);

  // 监听浏览器前进/后退
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handlePopState = () => {
      const currentPath = window.location.pathname;
      setRouterState((prev) => navigateState(prev, currentPath));
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = useCallback((newPath: string) => {
    setRouterState((prev) => {
      const next = navigateState(prev, newPath);
      syncBrowserUrl(next.path);
      return next;
    });
  }, [syncBrowserUrl]);

  const switchRole = useCallback((targetRole: AppRole) => {
    setRouterState((prev) => {
      const next = routerSwitchRole(prev, targetRole);
      syncBrowserUrl(next.path);
      return next;
    });
  }, [syncBrowserUrl]);

  const selectStudent = useCallback((newStudentId: string) => {
    if (typeof window !== 'undefined' && newStudentId) {
      localStorage.setItem(DEMO_STUDENT_STORAGE_KEY, newStudentId);
    }
    setRouterState((prev) => selectStudentState(prev, newStudentId));
  }, []);

  const value: AppContextValue = {
    role: routerState.role,
    path: routerState.path,
    subRoute: routerState.subRoute,
    studentId: routerState.studentId,
    navigate,
    switchRole,
    selectStudent,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};
