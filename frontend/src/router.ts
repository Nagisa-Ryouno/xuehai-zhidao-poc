/**
 * router.ts
 * 学海智导 (Xuehai Zhidao) V2 统一路由解析与状态管理核心
 *
 * 职责：
 * 1. 纯函数路由解析：映射 URL 路径至角色 (student / teacher) 与对应布局
 * 2. 状态机迁移：支持角色平滑切换并严格保持学生上下文 (如 S001)
 * 3. 0 依赖，完全兼容标准 HTML5 History 与 Node 运行时测试
 */

export type AppRole = 'student' | 'teacher';

export type StudentSubRoute = 'tasks' | 'resources' | 'graph' | 'profile' | 'assistant';

export type TeacherSubRoute = 'dashboard' | 'overview' | 'knowledge' | 'students';

export interface RouteResolution {
  role: AppRole;
  layout: 'StudentLayout' | 'TeacherLayout';
  subRoute: StudentSubRoute | TeacherSubRoute;
  redirect?: string;
}

export interface RouterState {
  path: string;
  role: AppRole;
  subRoute: StudentSubRoute | TeacherSubRoute;
  studentId: string;
}

/**
 * 纯函数：解析当前路径并匹配对应角色、布局及子路由
 */
export function resolveRoute(pathname: string): RouteResolution {
  // 规整化路径：去除末尾斜杠（除根路径外）
  const cleanPath = pathname.length > 1 && pathname.endsWith('/')
    ? pathname.slice(0, -1)
    : pathname;

  // 1. 根路径重定向至 /student/tasks
  if (cleanPath === '' || cleanPath === '/') {
    return {
      role: 'student',
      layout: 'StudentLayout',
      subRoute: 'tasks',
      redirect: '/student/tasks',
    };
  }

  // 2. 教师端路由：/teacher 及子路径
  if (cleanPath === '/teacher') {
    return {
      role: 'teacher',
      layout: 'TeacherLayout',
      subRoute: 'dashboard',
    };
  }

  if (cleanPath.startsWith('/teacher/')) {
    const sub = cleanPath.replace('/teacher/', '').split('/')[0];
    let matchedSub: TeacherSubRoute = 'dashboard';
    if (sub === 'overview') matchedSub = 'overview';
    else if (sub === 'knowledge') matchedSub = 'knowledge';
    else if (sub === 'students') matchedSub = 'students';

    return {
      role: 'teacher',
      layout: 'TeacherLayout',
      subRoute: matchedSub,
    };
  }

  // 3. 学生端路由：/student 及各子 Tab
  if (cleanPath === '/student') {
    return {
      role: 'student',
      layout: 'StudentLayout',
      subRoute: 'tasks',
    };
  }

  if (cleanPath.startsWith('/student/')) {
    const sub = cleanPath.replace('/student/', '').split('/')[0];
    let matchedSub: StudentSubRoute = 'tasks';
    if (sub === 'resources') matchedSub = 'resources';
    else if (sub === 'graph') matchedSub = 'graph';
    else if (sub === 'profile') matchedSub = 'profile';
    else if (sub === 'assistant') matchedSub = 'assistant';
    else matchedSub = 'tasks';

    return {
      role: 'student',
      layout: 'StudentLayout',
      subRoute: matchedSub,
    };
  }

  // 4. 默认兜底：重定向至 /student/tasks
  return {
    role: 'student',
    layout: 'StudentLayout',
    subRoute: 'tasks',
    redirect: '/student/tasks',
  };
}

/**
 * 创建初始路由器状态
 */
export function createRouterState(
  initialPath = '/student/tasks',
  initialStudentId = 'S001',
): RouterState {
  const resolution = resolveRoute(initialPath);
  return {
    path: resolution.redirect || initialPath,
    role: resolution.role,
    subRoute: resolution.subRoute,
    studentId: initialStudentId,
  };
}

/**
 * 切换角色（学生视图 <-> 教师驾驶舱），严格保留当前 studentId 上下文
 */
export function switchRole(state: RouterState, targetRole: AppRole): RouterState {
  if (state.role === targetRole) return state;

  const targetPath = targetRole === 'teacher' ? '/teacher' : '/student/tasks';
  const resolution = resolveRoute(targetPath);

  return {
    ...state,
    path: targetPath,
    role: targetRole,
    subRoute: resolution.subRoute,
    // 关键契约：严格保留当前学生 ID 上下文
    studentId: state.studentId,
  };
}

/**
 * 路径导航跳转
 */
export function navigateState(state: RouterState, newPath: string): RouterState {
  const resolution = resolveRoute(newPath);
  return {
    ...state,
    path: resolution.redirect || newPath,
    role: resolution.role,
    subRoute: resolution.subRoute,
    studentId: state.studentId,
  };
}

/**
 * 切换当前选中的学生
 */
export function selectStudentState(state: RouterState, studentId: string): RouterState {
  return {
    ...state,
    studentId,
  };
}
