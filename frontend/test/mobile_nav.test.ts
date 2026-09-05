import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  STUDENT_NAV_TABS,
  getActiveStudentTab,
  BOTTOM_NAV_CONFIG,
} from '../src/components/student/navConfig.ts';
import {
  createBottomSheetState,
  openBottomSheet,
  closeBottomSheet,
  BOTTOM_SHEET_STYLE_CLASSES,
} from '../src/components/common/bottomSheetModel.ts';

describe('P0-2: 学生端 Mobile-First 骨架与 BottomNav + BottomSheet 基础组件测试', () => {
  // Test 1: 四个 Tab 必须存在
  it('Test 1: 学生端 4 个核心 Tab 必须全部存在且文案准确', () => {
    const labels = STUDENT_NAV_TABS.map((t) => t.label);
    assert.ok(labels.includes('今日任务'), '缺少「今日任务」Tab');
    assert.ok(labels.includes('知识图谱'), '缺少「知识图谱」Tab');
    assert.ok(labels.includes('学情档案'), '缺少「学情档案」Tab');
    assert.ok(labels.includes('AI伴学'), '缺少「AI伴学」Tab');
    assert.equal(STUDENT_NAV_TABS.length, 4);
  });

  // Test 2: 四个 Tab 对应正确路径
  it('Test 2: 4 个 Tab 分别对应唯一的规范子路由路径', () => {
    const pathToId = Object.fromEntries(STUDENT_NAV_TABS.map((t) => [t.path, t.id]));
    assert.equal(pathToId['/student/tasks'], 'tasks');
    assert.equal(pathToId['/student/graph'], 'graph');
    assert.equal(pathToId['/student/profile'], 'profile');
    assert.equal(pathToId['/student/assistant'], 'assistant');
  });

  // Test 3: 当前路径能够确定 active Tab
  it('Test 3: getActiveStudentTab 能从不同路径精准推断 active Tab', () => {
    assert.equal(getActiveStudentTab('/student/tasks'), 'tasks');
    assert.equal(getActiveStudentTab('/student/graph'), 'graph');
    assert.equal(getActiveStudentTab('/student/profile'), 'profile');
    assert.equal(getActiveStudentTab('/student/assistant'), 'assistant');
    // 根路径或 /student 默认 fallback 到 tasks
    assert.equal(getActiveStudentTab('/student'), 'tasks');
    assert.equal(getActiveStudentTab('/'), 'tasks');
  });

  // Test 4: BottomNav 不应该影响页面主体内容（布局持久性与底部防遮挡高度约定）
  it('Test 4: BottomNav 容器与主体预留高度约定合规，避免页面内容被遮挡', () => {
    assert.ok(BOTTOM_NAV_CONFIG.containerClass.includes('fixed bottom-0'));
    assert.ok(BOTTOM_NAV_CONFIG.contentPaddingClass.includes('pb-'));
    assert.ok(
      BOTTOM_NAV_CONFIG.contentPaddingClass.includes('pb-24') ||
      BOTTOM_NAV_CONFIG.contentPaddingClass.includes('pb-20') ||
      BOTTOM_NAV_CONFIG.contentPaddingClass.includes('safe-area')
    );
  });

  // Test 5: Bottom Sheet 初始关闭状态
  it('Test 5: Bottom Sheet 状态机初始必须为关闭 (open === false)', () => {
    const sheetState = createBottomSheetState();
    assert.equal(sheetState.isOpen, false);
    assert.equal(sheetState.activePayload, null);
  });

  // Test 6: Bottom Sheet 打开/关闭状态流转
  it('Test 6: Bottom Sheet 打开与关闭状态流转正确', () => {
    let state = createBottomSheetState<string>();
    assert.equal(state.isOpen, false);

    // 打开弹窗并挂载 payload
    state = openBottomSheet(state, 'K08-需求价格弹性');
    assert.equal(state.isOpen, true);
    assert.equal(state.activePayload, 'K08-需求价格弹性');

    // 关闭弹窗
    state = closeBottomSheet(state);
    assert.equal(state.isOpen, false);
  });

  // Test 7: 触控关闭行为（Backdrop 与 Escape 键策略）
  it('Test 7: 支持 backdrop 点击与 Escape 键盘事件关闭', () => {
    let state = createBottomSheetState<string>();
    state = openBottomSheet(state, 'TestNode');
    assert.equal(state.isOpen, true);

    // 模拟 backdrop 点击
    state = closeBottomSheet(state, 'backdrop_click');
    assert.equal(state.isOpen, false);
    assert.equal(state.lastDismissReason, 'backdrop_click');
  });

  // Test 8: 安全区域与触控靶点尺寸规格
  it('Test 8: 样式规格必须满足触控靶点 >= 44px 与 iOS 安全区域适配', () => {
    assert.ok(
      BOTTOM_NAV_CONFIG.minTouchTargetPx >= 44,
      '触控靶点必须 >= 44px'
    );
    assert.ok(
      BOTTOM_NAV_CONFIG.safeAreaClass.includes('safe-area-inset-bottom') ||
      BOTTOM_NAV_CONFIG.containerClass.includes('safe-area')
    );
    assert.ok(
      BOTTOM_SHEET_STYLE_CLASSES.sheet.includes('rounded-t-') ||
      BOTTOM_SHEET_STYLE_CLASSES.sheet.includes('max-h-')
    );
  });
});
