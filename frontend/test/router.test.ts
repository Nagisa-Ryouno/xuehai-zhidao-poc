import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  resolveRoute,
  createRouterState,
  switchRole,
} from '../src/router.ts';

describe('P0-1: 前端双端路由隔离与导航骨架测试', () => {
  // Requirement 1: /student 可以进入学生端入口
  it('1. /student 应正确解析为学生端入口，并匹配 student 角色与 StudentLayout', () => {
    const route = resolveRoute('/student');
    assert.equal(route.role, 'student');
    assert.equal(route.layout, 'StudentLayout');
    assert.equal(route.subRoute, 'tasks'); // 默认进入今日任务子路由
  });

  // Requirement 2: /teacher 可以进入教师端入口
  it('2. /teacher 应正确解析为教师端入口，并匹配 teacher 角色与 TeacherLayout', () => {
    const route = resolveRoute('/teacher');
    assert.equal(route.role, 'teacher');
    assert.equal(route.layout, 'TeacherLayout');
    assert.equal(route.subRoute, 'dashboard');
  });

  // Requirement 3: / 默认重定向至 /student
  it('3. / 根路由应默认重定向至 /student/tasks', () => {
    const route = resolveRoute('/');
    assert.equal(route.redirect, '/student/tasks');
    assert.equal(route.role, 'student');
    assert.equal(route.layout, 'StudentLayout');
  });

  // Requirement 4: 学生端和教师端使用不同的 Layout
  it('4. 学生端和教师端必须使用不同的 Layout 标识', () => {
    const studentRoute = resolveRoute('/student/tasks');
    const teacherRoute = resolveRoute('/teacher');
    assert.notEqual(studentRoute.layout, teacherRoute.layout);
    assert.equal(studentRoute.layout, 'StudentLayout');
    assert.equal(teacherRoute.layout, 'TeacherLayout');
  });

  // Requirement 5: RoleSwitcher 能够在 Student / Teacher 两种视图之间切换
  it('5. RoleSwitcher 能够在 Student / Teacher 两种视图之间进行平滑切换', () => {
    let state = createRouterState('/student/tasks', 'S001');
    assert.equal(state.role, 'student');

    // 切换到教师驾驶舱
    state = switchRole(state, 'teacher');
    assert.equal(state.role, 'teacher');
    assert.equal(state.path, '/teacher');

    // 再次切换回学生视图
    state = switchRole(state, 'student');
    assert.equal(state.role, 'student');
    assert.equal(state.path, '/student/tasks');
  });

  // Requirement 6: 切换角色后 URL 与当前视图保持一致
  it('6. 切换角色后 URL 路径与当前视图角色严格保持一致', () => {
    const stateStudent = createRouterState('/student/graph', 'S001');
    const stateTeacher = switchRole(stateStudent, 'teacher');
    assert.match(stateTeacher.path, /^\/teacher/);
    assert.equal(stateTeacher.role, 'teacher');

    const stateBack = switchRole(stateTeacher, 'student');
    assert.match(stateBack.path, /^\/student/);
    assert.equal(stateBack.role, 'student');
  });

  // Requirement 7: 默认学生上下文为 S001
  it('7. 默认学生上下文必须初始化为 S001', () => {
    const state = createRouterState('/student/tasks');
    assert.equal(state.studentId, 'S001');
  });

  // Requirement 8: 不允许因为角色切换导致学生上下文丢失
  it('8. 在学生端与教师端之间切换时，选中的学生上下文 (如 S003) 绝不丢失', () => {
    let state = createRouterState('/student/profile', 'S003');
    assert.equal(state.studentId, 'S003');

    // 切换至教师端
    state = switchRole(state, 'teacher');
    assert.equal(state.studentId, 'S003'); // 上下文保留

    // 切换回学生端
    state = switchRole(state, 'student');
    assert.equal(state.studentId, 'S003'); // 上下文依然保留
  });

  // 扩展验证: 学生端 4-Tab 预留子路由解析
  it('扩展: 正确解析 /student 预留的 4-Tab 子路由 (tasks, graph, profile, assistant)', () => {
    assert.equal(resolveRoute('/student/tasks').subRoute, 'tasks');
    assert.equal(resolveRoute('/student/graph').subRoute, 'graph');
    assert.equal(resolveRoute('/student/profile').subRoute, 'profile');
    assert.equal(resolveRoute('/student/assistant').subRoute, 'assistant');
  });
});
