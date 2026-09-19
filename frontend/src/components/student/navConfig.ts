/**
 * navConfig.ts
 * 学生端移动优先 4-Tab 导航配置与规范常量
 */

export type StudentTabId = 'tasks' | 'resources' | 'graph' | 'profile' | 'assistant';

export interface StudentNavTab {
  id: StudentTabId;
  label: string;
  path: string;
  iconName: string;
  description: string;
}

export const RESOURCE_TAB_INFO: StudentNavTab = {
  id: 'resources',
  label: '学习资源',
  path: '/student/resources',
  iconName: 'BookOpen',
  description: '考点精要微卡、典型例题与针对性练习',
};

export const STUDENT_NAV_TABS: StudentNavTab[] = [
  {
    id: 'tasks',
    label: '今日任务',
    path: '/student/tasks',
    iconName: 'CalendarCheck',
    description: '每日任务清单与推荐学习序列',
  },
  {
    id: 'graph',
    label: '知识图谱',
    path: '/student/graph',
    iconName: 'Network',
    description: '微观经济学认知依赖网络',
  },
  {
    id: 'profile',
    label: '学情档案',
    path: '/student/profile',
    iconName: 'UserCheck',
    description: '个人掌握度、做题耗时与学情雷达',
  },
  {
    id: 'assistant',
    label: 'AI伴学',
    path: '/student/assistant',
    iconName: 'Bot',
    description: '苏格拉底式启发答疑与微课辅导',
  },
];

/**
 * 根据路径解析出当前激活的 Tab
 */
export function getActiveStudentTab(pathname: string): StudentTabId {
  const clean = pathname.length > 1 && pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;

  if (clean === '/student/resources') return 'resources';
  if (clean === '/student/graph') return 'graph';
  if (clean === '/student/profile') return 'profile';
  if (clean === '/student/assistant') return 'assistant';
  // 默认 fallback 为 tasks
  return 'tasks';
}

/**
 * BottomNav 容器与尺寸规范
 */
export const BOTTOM_NAV_CONFIG = {
  // 最小触控靶点（像素）
  minTouchTargetPx: 48,
  // 容器固定定位与暖白毛玻璃背景类
  containerClass:
    'fixed bottom-0 left-0 right-0 z-40 bg-[rgba(251,241,231,.82)] backdrop-blur-xl backdrop-saturate-150 border-t border-white/75 shadow-[0_-6px_20px_rgba(214,150,105,.14)] pb-[env(safe-area-inset-bottom)] md:hidden',
  // 主体内容底部安全预留类（确保不遮挡内容）
  contentPaddingClass: 'pb-24 sm:pb-8',
  // iOS 安全区域适配类
  safeAreaClass: 'pb-[env(safe-area-inset-bottom)]',
} as const;
