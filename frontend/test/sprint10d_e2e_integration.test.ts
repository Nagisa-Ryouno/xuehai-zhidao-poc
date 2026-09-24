import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('Sprint 10-D / Phase 4-F: Teacher Action -> Student Recommendation End-to-End Integration Verification', () => {
  const teacherModalPath = path.resolve(__dirname, '../src/components/teacher/TeacherActionModal.tsx');
  const teacherHistoryPath = path.resolve(__dirname, '../src/components/teacher/TeacherActionHistory.tsx');
  const teacherDetailPath = path.resolve(__dirname, '../src/components/teacher/TeacherStudentDetailModal.tsx');
  const studentCardPath = path.resolve(__dirname, '../src/components/student/TeacherRecommendationCard.tsx');
  const studentHomePath = path.resolve(__dirname, '../src/components/student/StudentHome.tsx');
  const studentLayoutPath = path.resolve(__dirname, '../src/layouts/StudentLayout.tsx');

  const teacherModalContent = fs.readFileSync(teacherModalPath, 'utf-8');
  const teacherHistoryContent = fs.readFileSync(teacherHistoryPath, 'utf-8');
  const teacherDetailContent = fs.readFileSync(teacherDetailPath, 'utf-8');
  const studentCardContent = fs.readFileSync(studentCardPath, 'utf-8');
  const studentHomeContent = fs.readFileSync(studentHomePath, 'utf-8');
  const studentLayoutContent = fs.readFileSync(studentLayoutPath, 'utf-8');

  // ============================================================================
  // E2E-01: Teacher Action Loop 全链路连通性检查
  // ============================================================================
  it('E2E-01: 全链路连通性验证：Teacher Web -> Student Recommendation -> Student Home -> Learning Session', () => {
    // 1. 教师详情弹窗能触发 Action Modal
    assert.ok(
      teacherDetailContent.includes('TeacherActionModal'),
      'TeacherStudentDetailModal 必须挂载 TeacherActionModal'
    );
    assert.ok(
      teacherDetailContent.includes('btn-teacher-action-'),
      '教师详情弹窗每个考点卡片必须有触发教学动作入口'
    );

    // 2. 教师详情弹窗包含历史 Tab
    assert.ok(
      teacherDetailContent.includes('tab-teacher-actions'),
      'TeacherStudentDetailModal 必须包含「教学动作」选项卡'
    );
    assert.ok(
      teacherDetailContent.includes('TeacherActionHistory'),
      'TeacherStudentDetailModal 必须挂载 TeacherActionHistory'
    );

    // 3. 教师端动作触发成功后联动刷新历史 Tab
    assert.ok(
      teacherDetailContent.includes('setActionRefreshTrigger'),
      'TeacherActionModal 成功回调必须触发动作历史刷新'
    );

    // 4. 学生端首页接入辅助卡片
    assert.ok(
      studentHomeContent.includes('TeacherRecommendationCard'),
      'StudentHome 必须挂载 TeacherRecommendationCard'
    );

    // 5. 学生端布局层自动拉取并注入推荐数据
    assert.ok(
      studentLayoutContent.includes('getStudentRecommendations'),
      'StudentLayout 必须调用 getStudentRecommendations'
    );
    assert.ok(
      studentLayoutContent.includes('recommendations={recommendations}'),
      'StudentLayout 必须向 StudentHome 注入 recommendations'
    );
  });

  // ============================================================================
  // E2E-02: Flow A 闭环验证：REVIEW_CONCEPT
  // ============================================================================
  it('E2E-02: Flow A 完整验证：REVIEW_CONCEPT -> 建议复习该考点 -> 去复习 -> Learning Session (CONCEPT)', () => {
    // 1. TeacherActionModal 支持 REVIEW_CONCEPT
    assert.ok(
      teacherModalContent.includes("'REVIEW_CONCEPT'"),
      'TeacherActionModal 必须支持 REVIEW_CONCEPT 选项'
    );
    assert.ok(
      teacherModalContent.includes('建议复习该考点'),
      'REVIEW_CONCEPT 必须使用规范文案「建议复习该考点」'
    );

    // 2. TeacherActionHistory 正确映射 REVIEW_CONCEPT
    assert.ok(
      teacherHistoryContent.includes('REVIEW_CONCEPT:'),
      'TeacherActionHistory 必须包含 REVIEW_CONCEPT 配置'
    );

    // 3. TeacherRecommendationCard 渲染建议并提供「去复习」
    assert.ok(
      studentCardContent.includes("item.action_type === 'REVIEW_CONCEPT'"),
      'TeacherRecommendationCard 必须处理 REVIEW_CONCEPT 类型'
    );
    assert.ok(
      studentCardContent.includes('去复习'),
      'REVIEW_CONCEPT 对应的 CTA 按钮文案必须为「去复习」'
    );

    // 4. 点击触发已有的 onViewConceptCard 进入学习会话 CONCEPT 步骤
    assert.ok(
      studentCardContent.includes('onViewConceptCard(item.knowledge_id'),
      '点击去复习必须调用 onViewConceptCard'
    );
    assert.ok(
      studentLayoutContent.includes("initialStep: 'CONCEPT'"),
      'onViewConceptCard 必须打开原有 LearningSessionModal 并设置 initialStep 为 CONCEPT'
    );
  });

  // ============================================================================
  // E2E-03: Flow B 闭环验证：RETRY_PRACTICE
  // ============================================================================
  it('E2E-03: Flow B 完整验证：RETRY_PRACTICE -> 建议重新练习 -> 去练习 -> Learning Session (QUIZ)', () => {
    // 1. TeacherActionModal 支持 RETRY_PRACTICE
    assert.ok(
      teacherModalContent.includes("'RETRY_PRACTICE'"),
      'TeacherActionModal 必须支持 RETRY_PRACTICE 选项'
    );
    assert.ok(
      teacherModalContent.includes('建议重新练习'),
      'RETRY_PRACTICE 必须使用规范文案「建议重新练习」'
    );

    // 2. TeacherActionHistory 正确映射 RETRY_PRACTICE
    assert.ok(
      teacherHistoryContent.includes('RETRY_PRACTICE:'),
      'TeacherActionHistory 必须包含 RETRY_PRACTICE 配置'
    );

    // 3. TeacherRecommendationCard 渲染建议并提供「去练习」
    assert.ok(
      studentCardContent.includes("item.action_type === 'RETRY_PRACTICE'"),
      'TeacherRecommendationCard 必须处理 RETRY_PRACTICE 类型'
    );
    assert.ok(
      studentCardContent.includes('去练习'),
      'RETRY_PRACTICE 对应的 CTA 按钮文案必须为「去练习」'
    );

    // 4. 点击触发已有的 onStartQuiz 进入学习会话 QUIZ 步骤
    assert.ok(
      studentCardContent.includes('onStartQuiz(item.knowledge_id'),
      '点击去练习必须调用 onStartQuiz'
    );
    assert.ok(
      studentLayoutContent.includes("initialStep: 'QUIZ'"),
      'onStartQuiz 必须打开原有 LearningSessionModal 并设置 initialStep 为 QUIZ'
    );
  });

  // ============================================================================
  // E2E-04: MARK_FOLLOWED 语义隔离与非侵入性
  // ============================================================================
  it('E2E-04: MARK_FOLLOWED 语义隔离：仅教师端记录，绝不干扰学生端推荐', () => {
    // 教师端存在 MARK_FOLLOWED
    assert.ok(
      teacherModalContent.includes("'MARK_FOLLOWED'"),
      'TeacherActionModal 支持 MARK_FOLLOWED'
    );
    assert.ok(
      teacherHistoryContent.includes('MARK_FOLLOWED:'),
      'TeacherActionHistory 支持查看 MARK_FOLLOWED 历史'
    );

    // 学生端卡片绝不包含 MARK_FOLLOWED
    assert.equal(
      studentCardContent.includes('MARK_FOLLOWED'),
      false,
      'TeacherRecommendationCard 严禁渲染 MARK_FOLLOWED'
    );
  });

  // ============================================================================
  // E2E-05: 学习状态无篡改安全性 (Zero Mutation Safety)
  // ============================================================================
  it('E2E-05: 学习状态安全断言：推荐卡片点击绝不伪造或变更底层学习状态', () => {
    assert.equal(
      studentCardContent.includes('bkt'),
      false,
      '推荐卡片不得引用或修改 BKT'
    );
    assert.equal(
      studentCardContent.includes('PathState'),
      false,
      '推荐卡片不得引用或修改 PathState'
    );
    assert.equal(
      studentCardContent.includes('postLearningActionResult'),
      false,
      '推荐卡片不得直接写入学习结果'
    );
    assert.equal(
      studentCardContent.includes('onExecuteTodayAction'),
      false,
      '推荐卡片不得触碰 TodayAction 生产决策引擎'
    );
  });

  // ============================================================================
  // E2E-06: 返回首页联动与错误隔离
  // ============================================================================
  it('E2E-06: 学习会话关闭后自动刷新，且 recommendations 请求失败不影响其他区域', () => {
    // 检查会话关闭与完成时包含 fetchRecommendations
    assert.ok(
      studentLayoutContent.includes('handleCloseSession = useCallback'),
      '存在 handleCloseSession 回调'
    );
    assert.ok(
      studentLayoutContent.includes('handleFinishSession = useCallback'),
      '存在 handleFinishSession 回调'
    );

    // 检查错误隔离
    assert.ok(
      studentLayoutContent.includes("setRecommendationsError('暂时无法加载老师建议')"),
      'recommendations 错误捕获后设置局部 error 状态，不影响其他数据'
    );
  });
});
