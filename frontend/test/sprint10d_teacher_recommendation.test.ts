import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type {
  StudentRecommendationItem,
  StudentRecommendationsResponse,
  TodayActionType,
} from '../src/types.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('Sprint 10-D / Phase 4-E: Student Teacher Recommendation (Student Home Auxiliary Integration) 契约与规范测试', () => {
  const cardPath = path.resolve(
    __dirname,
    '../src/components/student/TeacherRecommendationCard.tsx'
  );
  const homePath = path.resolve(
    __dirname,
    '../src/components/student/StudentHome.tsx'
  );
  const layoutPath = path.resolve(
    __dirname,
    '../src/layouts/StudentLayout.tsx'
  );

  const cardContent = fs.readFileSync(cardPath, 'utf-8');
  const homeContent = fs.readFileSync(homePath, 'utf-8');
  const layoutContent = fs.readFileSync(layoutPath, 'utf-8');

  // ============================================================================
  // R001: Student Home 出现「老师建议」区域
  // ============================================================================
  it('R001: Student Home 出现「老师建议」区域', () => {
    assert.ok(
      homeContent.includes('TeacherRecommendationCard'),
      'StudentHome 必须挂载 TeacherRecommendationCard 组件'
    );
    assert.ok(
      homeContent.includes('aria-label="老师建议"'),
      'StudentHome 必须包含 aria-label="老师建议" 的专用区域'
    );
    assert.ok(
      cardContent.includes('老师建议'),
      'TeacherRecommendationCard 必须展示区域标题「老师建议」'
    );
    assert.ok(
      cardContent.includes('data-testid="teacher-recommendation-card"'),
      'TeacherRecommendationCard 必须提供 data-testid="teacher-recommendation-card"'
    );
  });

  // ============================================================================
  // R002: 调用正确的 student teacher-action recommendation API
  // ============================================================================
  it('R002: 调用正确的 student teacher-action recommendation API', () => {
    assert.ok(
      layoutContent.includes('getStudentRecommendations'),
      'StudentLayout 必须引入并调用已有的 getStudentRecommendations API'
    );
    assert.ok(
      layoutContent.includes('getStudentRecommendations(studentId)'),
      '必须使用当前 studentId 调用 getStudentRecommendations'
    );
  });

  // ============================================================================
  // R003: 正常展示 recommendation
  // ============================================================================
  it('R003: 正常展示 recommendation', () => {
    assert.ok(
      cardContent.includes('data-testid="teacher-recommendation-item"'),
      '必须为每条推荐卡片提供 data-testid="teacher-recommendation-item"'
    );
    assert.ok(
      cardContent.includes('displayItems.map'),
      '必须遍历渲染 displayItems 建议列表'
    );
  });

  // ============================================================================
  // R004: 正确显示知识点名称
  // ============================================================================
  it('R004: 正确显示知识点名称', () => {
    assert.ok(
      cardContent.includes('item.knowledge_name || item.knowledge_id'),
      '必须直接优先展示服务端注入的 knowledge_name，不重新在前端反查'
    );
  });

  // ============================================================================
  // R005: REVIEW_CONCEPT 显示："建议复习该考点"
  // ============================================================================
  it('R005: REVIEW_CONCEPT 显示："建议复习该考点"', () => {
    assert.ok(
      cardContent.includes('建议复习该考点'),
      'REVIEW_CONCEPT 动作文案必须为「建议复习该考点」'
    );
    assert.ok(
      cardContent.includes('去复习'),
      'REVIEW_CONCEPT CTA 按钮文案必须为「去复习」'
    );
  });

  // ============================================================================
  // R006: RETRY_PRACTICE 显示："建议重新练习"
  // ============================================================================
  it('R006: RETRY_PRACTICE 显示："建议重新练习"', () => {
    assert.ok(
      cardContent.includes('建议重新练习'),
      'RETRY_PRACTICE 动作文案必须为「建议重新练习」'
    );
    assert.ok(
      cardContent.includes('去练习'),
      'RETRY_PRACTICE CTA 按钮文案必须为「去练习」'
    );
  });

  // ============================================================================
  // R007: 最多显示 3 条
  // ============================================================================
  it('R007: 最多显示 3 条', () => {
    assert.ok(
      cardContent.includes('.slice(0, 3)'),
      'TeacherRecommendationCard 前端必须防御性截取最多 3 条展示'
    );

    // 纯数据逻辑断言：超过 3 条时切片必须严格为 3
    const mockList: StudentRecommendationItem[] = [
      { action_id: '1', knowledge_id: 'K01', knowledge_name: '需求定理', action_type: 'REVIEW_CONCEPT', created_at: '2026-09-22T10:00:00Z' },
      { action_id: '2', knowledge_id: 'K02', knowledge_name: '供给定理', action_type: 'RETRY_PRACTICE', created_at: '2026-09-22T09:00:00Z' },
      { action_id: '3', knowledge_id: 'K03', knowledge_name: '弹性分析', action_type: 'REVIEW_CONCEPT', created_at: '2026-09-22T08:00:00Z' },
      { action_id: '4', knowledge_id: 'K04', knowledge_name: '均衡价格', action_type: 'RETRY_PRACTICE', created_at: '2026-09-22T07:00:00Z' },
    ];
    const sliced = mockList.slice(0, 3);
    assert.equal(sliced.length, 3);
  });

  // ============================================================================
  // R008: 保持 created_at DESC 语义
  // ============================================================================
  it('R008: 保持 created_at DESC 语义', () => {
    assert.ok(
      cardContent.includes('new Date(b.created_at).getTime() - new Date(a.created_at).getTime()'),
      '前端必须确保按 created_at 降序排序'
    );

    const unordered: StudentRecommendationItem[] = [
      { action_id: '1', knowledge_id: 'K01', knowledge_name: '需求定理', action_type: 'REVIEW_CONCEPT', created_at: '2026-09-20T10:00:00Z' },
      { action_id: '2', knowledge_id: 'K02', knowledge_name: '供给定理', action_type: 'RETRY_PRACTICE', created_at: '2026-09-22T10:00:00Z' },
    ];
    const sorted = [...unordered].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
    assert.equal(sorted[0].action_id, '2', '时间较新的应排在第一位');
    assert.equal(sorted[1].action_id, '1', '时间较旧的应排在第二位');
  });

  // ============================================================================
  // R009: MARK_FOLLOWED 不出现在学生 recommendation 中
  // ============================================================================
  it('R009: MARK_FOLLOWED 不出现在学生 recommendation 中', () => {
    // 检查过滤逻辑中显式排除了非 actionable 类型
    assert.ok(
      cardContent.includes("r.action_type === 'REVIEW_CONCEPT' || r.action_type === 'RETRY_PRACTICE'"),
      '前端卡片展示列表严格只允许 REVIEW_CONCEPT 与 RETRY_PRACTICE'
    );
    assert.equal(
      cardContent.includes('MARK_FOLLOWED'),
      false,
      'TeacherRecommendationCard 绝不包含 MARK_FOLLOWED 分支或展示'
    );
  });

  // ============================================================================
  // R010: 点击 REVIEW_CONCEPT 进入已有学习流程
  // ============================================================================
  it('R010: 点击 REVIEW_CONCEPT 进入已有学习流程', () => {
    assert.ok(
      cardContent.includes("item.action_type === 'REVIEW_CONCEPT'"),
      '必须识别 REVIEW_CONCEPT 动作'
    );
    assert.ok(
      cardContent.includes('onViewConceptCard(item.knowledge_id'),
      'REVIEW_CONCEPT 必须调用已有的 onViewConceptCard 进入考点速览学习会话'
    );
  });

  // ============================================================================
  // R011: 点击 RETRY_PRACTICE 进入已有学习流程
  // ============================================================================
  it('R011: 点击 RETRY_PRACTICE 进入已有学习流程', () => {
    assert.ok(
      cardContent.includes("item.action_type === 'RETRY_PRACTICE'"),
      '必须识别 RETRY_PRACTICE 动作'
    );
    assert.ok(
      cardContent.includes('onStartQuiz(item.knowledge_id'),
      'RETRY_PRACTICE 必须调用已有的 onStartQuiz 进入微测验突破学习会话'
    );
  });

  // ============================================================================
  // R012: 点击 recommendation 不产生新的 TodayAction
  // ============================================================================
  it('R012: 点击 recommendation 不产生新的 TodayAction', () => {
    assert.equal(
      cardContent.includes('onExecuteTodayAction'),
      false,
      'TeacherRecommendationCard 绝对不能调用 onExecuteTodayAction'
    );
    assert.equal(
      cardContent.includes('handleTodayActionCTA'),
      false,
      'TeacherRecommendationCard 绝对不能绑定 handleTodayActionCTA'
    );
  });

  // ============================================================================
  // R013: 点击 recommendation 不修改学习 authoritative state
  // ============================================================================
  it('R013: 点击 recommendation 不修改学习 authoritative state', () => {
    // 推荐卡片只是纯只读导航入口，绝对不直接写任何事件或算法
    assert.equal(
      cardContent.includes('postLearningActionResult'),
      false,
      'TeacherRecommendationCard 绝对不能直接调用 postLearningActionResult'
    );
    assert.equal(
      cardContent.includes('recordResourceEvent'),
      false,
      'TeacherRecommendationCard 绝对不能直接记录资源事件'
    );
  });

  // ============================================================================
  // R014: 无 recommendation 时正确显示轻量 empty state / 隐藏
  // ============================================================================
  it('R014: 无 recommendation 时正确显示轻量 empty state / 隐藏', () => {
    assert.ok(
      cardContent.includes('暂无老师建议'),
      '空状态必须展示温和文案「暂无老师建议」'
    );
    assert.ok(
      cardContent.includes('!recommendations || recommendations.length === 0'),
      '必须精确判断空数组状态'
    );
  });

  // ============================================================================
  // R015: API error 不影响 Student Home 其它模块
  // ============================================================================
  it('R015: API error 不影响 Student Home 其它模块', () => {
    assert.ok(
      cardContent.includes('暂时无法加载老师建议'),
      'Error 状态必须展示友善提示「暂时无法加载老师建议」'
    );
    assert.ok(
      cardContent.includes('onRetry'),
      'Error 状态必须提供可选的 onRetry 重试入口'
    );
    // StudentLayout 中单独捕获异常并赋独立 recommendationsError，不向外抛出导致崩溃
    assert.ok(
      layoutContent.includes("setRecommendationsError('暂时无法加载老师建议')"),
      'StudentLayout 捕获 recommendations 请求失败时不影响其他数据流'
    );
  });

  // ============================================================================
  // R016: loading 状态正确
  // ============================================================================
  it('R016: loading 状态正确', () => {
    assert.ok(
      cardContent.includes('if (loading)'),
      '必须处理 loading 骨架态'
    );
    assert.ok(
      cardContent.includes('animate-pulse'),
      'loading 状态必须包含 animate-pulse 骨架屏'
    );
  });

  // ============================================================================
  // R017: UI 不展示 teacher_id / action_id / 内部枚举等内部字段
  // ============================================================================
  it('R017: UI 不展示 teacher_id / action_id / 内部枚举等内部字段', () => {
    assert.equal(
      cardContent.includes('T001'),
      false,
      'TeacherRecommendationCard 严禁出现 T001 内部教师编号'
    );
    assert.equal(
      cardContent.includes('>{item.action_id}<') || cardContent.includes('<span>{item.action_id}'),
      false,
      'UI 文本中严禁渲染 action_id'
    );
    assert.equal(
      cardContent.includes('{item.action_type}'),
      false,
      'UI 文本中严禁直接渲染未经映射的 action_type 原始枚举'
    );
    assert.equal(
      cardContent.includes('teacher_id'),
      false,
      'UI 中严禁引用或渲染 teacher_id'
    );
  });

  // ============================================================================
  // R018: 不存在 completed / consumed / read / dismissed 等生命周期 UI
  // ============================================================================
  it('R018: 不存在 completed / consumed / read / dismissed 等生命周期 UI', () => {
    const forbiddenLifecycleWords = [
      '完成建议',
      '忽略建议',
      '删除建议',
      '标记已读',
      '关闭建议',
      'dismiss',
      'consumed',
      'is_read',
    ];
    for (const word of forbiddenLifecycleWords) {
      assert.equal(
        cardContent.toLowerCase().includes(word.toLowerCase()),
        false,
        `TeacherRecommendationCard 严禁包含生命周期业务操作: ${word}`
      );
    }
  });

  // ============================================================================
  // R019: 原有 TodayAction / CurrentFocus / RecentProgress 行为不受影响
  // ============================================================================
  it('R019: 原有 TodayAction / CurrentFocus / RecentProgress 行为不受影响且层级严格遵循规范', () => {
    assert.ok(
      homeContent.includes('TodayActionCard'),
      'StudentHome 必须包含 TodayActionCard'
    );
    assert.ok(
      homeContent.includes('CurrentFocusCard'),
      'StudentHome 必须包含 CurrentFocusCard'
    );
    assert.ok(
      homeContent.includes('RecentProgressCard'),
      'StudentHome 必须包含 RecentProgressCard'
    );

    // 检查三者优先级排布顺序：TodayAction Hero -> CurrentFocus Context -> TeacherRecommendation Auxiliary -> RecentProgress
    const todayActionIndex = homeContent.indexOf('TodayActionCard');
    const focusIndex = homeContent.indexOf('CurrentFocusCard');
    const recommendationIndex = homeContent.indexOf('TeacherRecommendationCard');
    const progressIndex = homeContent.indexOf('RecentProgressCard');

    assert.ok(
      todayActionIndex < focusIndex,
      'TodayAction 必须位于 CurrentFocus 之前'
    );
    assert.ok(
      focusIndex < recommendationIndex,
      'CurrentFocus 必须位于 TeacherRecommendation 之前'
    );
    assert.ok(
      recommendationIndex < progressIndex,
      'TeacherRecommendation 必须位于 RecentProgress 之前'
    );
  });

  // ============================================================================
  // R020: Student Home 不新增新的“学习决策类型”
  // ============================================================================
  it('R020: Student Home 不新增新的“学习决策类型”', () => {
    const typesPath = path.resolve(__dirname, '../src/types.ts');
    const typesContent = fs.readFileSync(typesPath, 'utf-8');

    // 检查 TodayActionType 枚举未被篡改
    const match = typesContent.match(/export type TodayActionType =\s*([^;]+);/);
    assert.ok(match, '必须存在 TodayActionType 枚举定义');
    const typeDef = match[1];

    assert.ok(typeDef.includes("'REVIEW_RETENTION'"));
    assert.ok(typeDef.includes("'CONTINUE_LEARNING'"));
    assert.ok(typeDef.includes("'PRACTICE'"));
    assert.ok(typeDef.includes("'VIEW_PROGRESS'"));
    assert.ok(typeDef.includes("'NONE'"));

    // 确保绝对没有引入 TEACHER_RECOMMENDATION 作为 TodayActionType
    assert.equal(
      typeDef.includes('TEACHER_RECOMMENDATION'),
      false,
      '严禁将 TEACHER_RECOMMENDATION 混入 TodayActionType 生产决策体系'
    );
  });
});
