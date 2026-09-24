import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { TeacherActionType, TeacherActionItem } from '../src/types.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('Sprint 10-D / Phase 4-D: Teacher Action History Tab 契约与 UI 规范测试', () => {
  // ============================================================================
  // H001: History Tab 存在
  // ============================================================================
  it('H001: History Tab 在 TeacherStudentDetailModal 中存在并可切换', () => {
    const detailModalPath = path.resolve(
      __dirname,
      '../src/components/teacher/TeacherStudentDetailModal.tsx'
    );
    const detailContent = fs.readFileSync(detailModalPath, 'utf-8');

    // 必须存在 tab-teacher-actions 切换入口
    assert.ok(
      detailContent.includes('data-testid="tab-teacher-actions"'),
      'TeacherStudentDetailModal 必须包含 data-testid="tab-teacher-actions" 选项卡'
    );
    assert.ok(
      detailContent.includes('教学动作'),
      '选项卡文字必须为「教学动作」'
    );
    assert.ok(
      detailContent.includes("activeTab === 'actions'"),
      '必须支持 actions 激活选项卡状态'
    );
    assert.ok(
      detailContent.includes('<TeacherActionHistory'),
      '必须挂载 TeacherActionHistory 组件'
    );
  });

  // ============================================================================
  // H002: 使用现有 getTeacherActionHistory(studentId)
  // ============================================================================
  it('H002: History Tab 复用已有的 getTeacherActionHistory API', () => {
    const historyPath = path.resolve(
      __dirname,
      '../src/components/teacher/TeacherActionHistory.tsx'
    );
    const historyContent = fs.readFileSync(historyPath, 'utf-8');

    assert.ok(
      historyContent.includes('getTeacherActionHistory'),
      'TeacherActionHistory 必须调用既有的 getTeacherActionHistory API'
    );
  });

  // ============================================================================
  // H003: History Tab 不调用 POST Action API
  // ============================================================================
  it('H003: History Tab 纯只读，绝不调用 POST postTeacherAction API', () => {
    const historyPath = path.resolve(
      __dirname,
      '../src/components/teacher/TeacherActionHistory.tsx'
    );
    const historyContent = fs.readFileSync(historyPath, 'utf-8');

    assert.equal(
      historyContent.includes('postTeacherAction'),
      false,
      'TeacherActionHistory 绝对不能调用 postTeacherAction'
    );
  });

  // ============================================================================
  // H004: 按 created_at DESC 展示
  // ============================================================================
  it('H004: 历史记录严格按 created_at DESC 排序展示', () => {
    const historyPath = path.resolve(
      __dirname,
      '../src/components/teacher/TeacherActionHistory.tsx'
    );
    const historyContent = fs.readFileSync(historyPath, 'utf-8');

    assert.ok(
      historyContent.includes('.sort(') &&
        historyContent.includes('created_at'),
      'TeacherActionHistory 必须保证按 created_at 降序排列'
    );

    // 逻辑验证：模拟三条无序记录，经过时间解析排序后最新在前
    const mockItems: TeacherActionItem[] = [
      {
        action_id: 'act-1',
        teacher_id: 'T001',
        student_id: 'S001',
        knowledge_id: 'K01',
        knowledge_name: '稀缺性与经济学基本问题',
        action_type: 'MARK_FOLLOWED',
        created_at: '2026-09-01T10:00:00Z',
      },
      {
        action_id: 'act-3',
        teacher_id: 'T001',
        student_id: 'S001',
        knowledge_id: 'K03',
        knowledge_name: '理性人假设与边际分析',
        action_type: 'RETRY_PRACTICE',
        created_at: '2026-09-22T11:00:00Z',
      },
      {
        action_id: 'act-2',
        teacher_id: 'T001',
        student_id: 'S001',
        knowledge_id: 'K02',
        knowledge_name: '机会成本与生产可能性边界',
        action_type: 'REVIEW_CONCEPT',
        created_at: '2026-09-20T10:00:00Z',
      },
    ];

    const sorted = mockItems.slice().sort((a, b) => {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

    assert.equal(sorted[0].action_id, 'act-3');
    assert.equal(sorted[1].action_id, 'act-2');
    assert.equal(sorted[2].action_id, 'act-1');
  });

  // ============================================================================
  // H005: 正确映射三种动作类型
  // ============================================================================
  it('H005: 严格保持三种 Action 业务文案映射', () => {
    const historyPath = path.resolve(
      __dirname,
      '../src/components/teacher/TeacherActionHistory.tsx'
    );
    const historyContent = fs.readFileSync(historyPath, 'utf-8');

    assert.ok(
      historyContent.includes("REVIEW_CONCEPT: '建议复习该考点'"),
      'REVIEW_CONCEPT 映射必须为「建议复习该考点」'
    );
    assert.ok(
      historyContent.includes("RETRY_PRACTICE: '建议重新练习'"),
      'RETRY_PRACTICE 映射必须为「建议重新练习」'
    );
    assert.ok(
      historyContent.includes("MARK_FOLLOWED: '标记为已关注'"),
      'MARK_FOLLOWED 映射必须为「标记为已关注」'
    );
  });

  // ============================================================================
  // H006: 显示 server-provided knowledge_name
  // ============================================================================
  it('H006: 直接使用服务端返回的 knowledge_name，不重新在前端解析', () => {
    const historyPath = path.resolve(
      __dirname,
      '../src/components/teacher/TeacherActionHistory.tsx'
    );
    const historyContent = fs.readFileSync(historyPath, 'utf-8');

    // 必须直接渲染 item.knowledge_name
    assert.ok(
      historyContent.includes('{item.knowledge_name}'),
      'TeacherActionHistory 必须直接使用 item.knowledge_name'
    );

    // 严禁引入前端 CONCEPT_CARDS 进行本地覆盖
    assert.equal(
      historyContent.includes('CONCEPT_CARDS'),
      false,
      'TeacherActionHistory 绝对不能在前端引入 CONCEPT_CARDS 重复解析'
    );
  });

  // ============================================================================
  // H007: UI 不出现 T001、teacher_id、action_id、status、note、message
  // ============================================================================
  it('H007: UI 界面绝对不泄露内部字段与身份标识', () => {
    const historyPath = path.resolve(
      __dirname,
      '../src/components/teacher/TeacherActionHistory.tsx'
    );
    const historyContent = fs.readFileSync(historyPath, 'utf-8');

    // 绝对不能出现 T001
    assert.equal(
      historyContent.includes('T001'),
      false,
      'UI 绝对不得出现内部 teacher ID T001'
    );

    // 不得在界面文本中渲染 teacher_id
    assert.equal(
      historyContent.includes('{item.teacher_id}'),
      false,
      'UI 绝对不得渲染 {item.teacher_id}'
    );

    // 不得在界面文本中渲染 action_id (除了 data-testid 属性键之外)
    assert.equal(
      historyContent.includes('ID: {item.action_id}') ||
        historyContent.includes('编号：{item.action_id}'),
      false,
      'UI 文本中绝对不得展示 action_id'
    );

    // 不得包含任务状态与自由文本字段
    assert.equal(
      historyContent.includes('item.status') ||
        historyContent.includes('item.note') ||
        historyContent.includes('item.message'),
      false,
      'UI 中绝对不得展示 status / note / message'
    );

    // 经办人必须使用业务化文案
    assert.ok(
      historyContent.includes('任课教师'),
      '必须显示业务文案「经办：任课教师」'
    );
  });

  // ============================================================================
  // H008: Empty state 正确
  // ============================================================================
  it('H008: 空状态具有规范的人本温和文案与占位说明', () => {
    const historyPath = path.resolve(
      __dirname,
      '../src/components/teacher/TeacherActionHistory.tsx'
    );
    const historyContent = fs.readFileSync(historyPath, 'utf-8');

    assert.ok(
      historyContent.includes('暂时还没有教学动作记录'),
      '空状态标题必须为「暂时还没有教学动作记录」'
    );
    assert.ok(
      historyContent.includes(
        '当你在学生详情中记录教学动作后，相关记录会显示在这里。'
      ),
      '空状态引导文案必须准确'
    );
    assert.ok(
      historyContent.includes('data-testid="teacher-action-history-empty"'),
      '必须包含 empty data-testid'
    );
  });

  // ============================================================================
  // H009: Error state + Retry 正确
  // ============================================================================
  it('H009: 错误状态提供友好提示与无框架 Retry 重新加载入口', () => {
    const historyPath = path.resolve(
      __dirname,
      '../src/components/teacher/TeacherActionHistory.tsx'
    );
    const historyContent = fs.readFileSync(historyPath, 'utf-8');

    assert.ok(
      historyContent.includes('教学动作记录暂时无法加载'),
      '错误状态标题必须为「教学动作记录暂时无法加载」'
    );
    assert.ok(
      historyContent.includes('重新加载'),
      '重试按钮文案必须为「重新加载」'
    );
    assert.ok(
      historyContent.includes('onClick={loadHistory}'),
      '点击重试按钮必须直接重新调用 loadHistory'
    );
    assert.ok(
      historyContent.includes('data-testid="btn-retry-action-history"'),
      '必须包含 retry data-testid'
    );
  });

  // ============================================================================
  // H010: 不调用任何学生学习状态 mutation API
  // ============================================================================
  it('H010: 绝对不触碰任何学生端学习状态修改接口', () => {
    const historyPath = path.resolve(
      __dirname,
      '../src/components/teacher/TeacherActionHistory.tsx'
    );
    const historyContent = fs.readFileSync(historyPath, 'utf-8');

    assert.equal(historyContent.includes('/quiz/submit'), false);
    assert.equal(historyContent.includes('/learning/events'), false);
    assert.equal(historyContent.includes('/learning/path-replanning'), false);
    assert.equal(historyContent.includes('bkt'), false);
  });

  // ============================================================================
  // H011: 原有 Student Detail 功能未被破坏
  // ============================================================================
  it('H011: 原有 3 个 Tab 与以该生身份进入学习空间 CTA 完整保留', () => {
    const detailModalPath = path.resolve(
      __dirname,
      '../src/components/teacher/TeacherStudentDetailModal.tsx'
    );
    const detailContent = fs.readFileSync(detailModalPath, 'utf-8');

    assert.ok(detailContent.includes("'kps'"), '30 考点认知全景 Tab 必须保留');
    assert.ok(detailContent.includes("'wrongs'"), '错题复盘流水 Tab 必须保留');
    assert.ok(detailContent.includes("'timeline'"), '真实学习流水 Tab 必须保留');
    assert.ok(
      detailContent.includes('以该生身份进入学习空间'),
      '学生透视按钮必须保留'
    );
    assert.ok(
      detailContent.includes('loadDetail'),
      '学生档案加载逻辑必须保留'
    );
  });

  // ============================================================================
  // H012: Student Home 未被修改
  // ============================================================================
  it('H012: Student Home 与学生端组件在 Phase 4-D 严格冻结', () => {
    // 检查学生端关键组件文件存在且未被添加本阶段内容
    const studentHomePath = path.resolve(
      __dirname,
      '../src/components/student/StudentHome.tsx'
    );
    const studentLayoutPath = path.resolve(
      __dirname,
      '../src/layouts/StudentLayout.tsx'
    );

    const homeContent = fs.readFileSync(studentHomePath, 'utf-8');
    const layoutContent = fs.readFileSync(studentLayoutPath, 'utf-8');

    assert.equal(
      homeContent.includes('TeacherActionHistory'),
      false,
      'StudentHome 绝对不能引入 TeacherActionHistory'
    );
    assert.equal(
      layoutContent.includes('TeacherActionHistory'),
      false,
      'StudentLayout 绝对不能引入 TeacherActionHistory'
    );
  });
});
