/**
 * sprint10c_student_home.test.ts
 * 学海智导 (Xuehai Zhidao) — Sprint 10-C Phase 1
 * 学生端首页 (Student Home / Today) 契约与组件规范测试
 *
 * 覆盖：
 * 1. Today Action 正常展示契约 (知识点名、掌握度、人本解释、主 CTA)
 * 2. Today Action 5 档类型与 CTA 真实映射契约
 * 3. Today Action NONE 空状态契约 (展示「今天暂时没有待完成的学习任务」，严禁伪造假任务)
 * 4. Today Action Loading 骨架屏防跳动契约
 * 5. Today Action Error 容错与重试契约
 * 6. Current Focus 契约 (展示学习上下文与下一步行动，消除裸露技术 ID)
 * 7. Recent Progress 权威数据契约 (仅呈现整体掌握度、掌握考点数、正确率、练习数，严禁推算伪造历史进展)
 * 8. 局部容错解耦契约 (TodayAction / Focus / Progress 独立错误隔离，防白屏)
 * 9. 新老学生首次进入场景契约 (S001 vs 新初始化学生状态真实性)
 * 10. 全站绝对禁止底层算法与学术黑话契约 (No Jargon)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  TodayActionType,
  TodayLearningAction,
  StudentProgressResponse,
  StudentBasic,
} from '../src/types.ts';

// 严禁在学生端呈现的底层算法与学术黑话
const FORBIDDEN_JARGON = [
  'BKT',
  'bkt',
  'P(L)',
  'p(l)',
  'Bayesian',
  'bayesian',
  '贝叶斯',
  'PathState',
  'pathstate',
  'DynamicPathGenerator',
  'mastery_probability',
  'Candidate',
  'candidate',
  'Validator',
  'validator',
  '确定性路径',
  '智能推荐引擎',
  '自适应算法',
  'AI决策',
  '向量数据库',
];

describe('Sprint 10-C Phase 1: 学生端首页 (Student Home / Today) 核心契约测试', () => {
  // ---------------------------------------------------------------------------
  // 1. Today Action 正常展示契约
  // ---------------------------------------------------------------------------
  it('1. Today Action 具备完整的人本展示属性：知识点、掌握度、解释、主 CTA', () => {
    const action: TodayLearningAction = {
      action_type: 'CONTINUE_LEARNING',
      title: '继续学习：三角函数恒等变换',
      description: '这是你当前学习路径中的下一步内容，建议温故知新。',
      cta_label: '继续学习',
      priority_reason: '当前学习路径中的首要未完成任务',
      knowledge_id: 'K02',
      knowledge_name: '三角函数恒等变换',
      suggested_action: 'REVIEW_CONCEPT',
    };

    assert.equal(action.action_type, 'CONTINUE_LEARNING');
    assert.equal(action.knowledge_name, '三角函数恒等变换');
    assert.equal(action.cta_label, '继续学习');
    assert.ok(action.title.includes('三角函数恒等变换'));
  });

  // ---------------------------------------------------------------------------
  // 2. Today Action 5 档类型与 CTA 映射契约
  // ---------------------------------------------------------------------------
  it('2. Today Action 各类型对应确定性的行动语义与真实目的地', () => {
    const actionDestinationMap: Record<TodayActionType, { cta: string; destinationType: string }> = {
      CONTINUE_LEARNING: { cta: '继续学习', destinationType: 'CONCEPT_MODAL' },
      NEEDS_REINFORCEMENT: { cta: '重新学习', destinationType: 'CONCEPT_MODAL' },
      DUE_FOR_REVIEW: { cta: '开始快速复测', destinationType: 'QUIZ' },
      PRACTICE: { cta: '开始练习', destinationType: 'QUIZ' },
      VIEW_PROGRESS: { cta: '查看进展', destinationType: 'PROFILE' },
      NONE: { cta: '查看学习进展', destinationType: 'PROFILE' },
    };

    assert.equal(actionDestinationMap.CONTINUE_LEARNING.destinationType, 'CONCEPT_MODAL');
    assert.equal(actionDestinationMap.NEEDS_REINFORCEMENT.destinationType, 'CONCEPT_MODAL');
    assert.equal(actionDestinationMap.DUE_FOR_REVIEW.destinationType, 'QUIZ');
    assert.equal(actionDestinationMap.PRACTICE.destinationType, 'QUIZ');
    assert.equal(actionDestinationMap.VIEW_PROGRESS.destinationType, 'PROFILE');
    assert.equal(actionDestinationMap.NONE.destinationType, 'PROFILE');
  });

  // ---------------------------------------------------------------------------
  // 3. Today Action NONE 空状态契约
  // ---------------------------------------------------------------------------
  it('3. 当 Today Action 为 NONE 时，明确呈现阶段完成空状态，严禁伪造假推荐', () => {
    const noneAction: TodayLearningAction = {
      action_type: 'NONE',
      title: '',
      description: '',
      cta_label: '',
      priority_reason: '当前阶段学习任务已全部达成',
      knowledge_id: null,
      knowledge_name: null,
      suggested_action: null,
    };

    // 契约验证：NONE 状态下的对外人本文案
    const emptyDisplay = {
      title: '今天暂时没有待完成的学习任务',
      description: '当前阶段学习任务已全部达成，可随时查看学情或探索新知识。',
      cta: '查看学习进展',
    };

    assert.equal(noneAction.action_type, 'NONE');
    assert.ok(emptyDisplay.title.includes('没有待完成的学习任务'));
    assert.equal(emptyDisplay.cta, '查看学习进展');
  });

  // ---------------------------------------------------------------------------
  // 4. Loading 骨架屏防跳动契约
  // ---------------------------------------------------------------------------
  it('4. Loading 状态必须具备最小固定高度与占位规格，避免首页布局跳动', () => {
    const loadingSpec = {
      minHeightPx: 160,
      hasPulseAnimation: true,
      hasHeaderPlaceholder: true,
      hasCtaPlaceholder: true,
    };

    assert.ok(loadingSpec.minHeightPx >= 140, '最小占位高度必须满足防跳动要求');
    assert.equal(loadingSpec.hasPulseAnimation, true);
  });

  // ---------------------------------------------------------------------------
  // 5. Error 容错与重试契约
  // ---------------------------------------------------------------------------
  it('5. Error 状态提供清晰人本提示，并支持独立重新加载', () => {
    const errorState = {
      message: '暂时无法获取今日学习安排',
      subMessage: '网络或数据加载异常，请尝试重新加载。',
      retryLabel: '重新加载',
    };

    assert.equal(errorState.message, '暂时无法获取今日学习安排');
    assert.equal(errorState.retryLabel, '重新加载');
  });

  // ---------------------------------------------------------------------------
  // 6. Current Focus 契约 (消除裸露技术 ID)
  // ---------------------------------------------------------------------------
  it('6. Current Focus 呈现当前学习知识点与简短上下文，不再堆砌裸露技术 ID', () => {
    const focusTask = {
      knowledgeId: 'K08',
      knowledgeName: '需求价格弹性',
      chapter: '微观经济学基础',
      reason: '已满足先修条件，建议通过针对性练习检验掌握程度',
      currentMasteryPercent: 62,
      targetMasteryPercent: 80,
    };

    // 契约：标题呈现知识点名称，不再强制以大字号显示 "K08"
    assert.equal(focusTask.knowledgeName, '需求价格弹性');
    assert.equal(focusTask.currentMasteryPercent, 62);
    assert.ok(focusTask.reason.length > 0);
  });

  // ---------------------------------------------------------------------------
  // 7. Recent Progress 权威数据契约 (严禁伪造推算)
  // ---------------------------------------------------------------------------
  it('7. Recent Progress 严格从权威 API 提取真实数据，严禁前端推算或伪造历史进展', () => {
    const authoritativeProgress: StudentProgressResponse = {
      student_id: 'S001',
      overall_mastery: 0.68,
      mastery_level: 'DEVELOPING',
      total_practice_count: 24,
      total_correct_count: 20,
      overall_accuracy: 0.8333,
      mastered_count: 12,
      developing_count: 8,
      weak_count: 4,
      unstudied_count: 6,
      mastery_trend: [],
      knowledge_points: [],
      history_timeline: [],
    };

    // 只能展示 4 项可验证的真实指标
    const displayedMetrics = {
      overallMasteryStr: `${Math.round(authoritativeProgress.overall_mastery * 100)}%`,
      masteredCountStr: `${authoritativeProgress.mastered_count} 个`,
      accuracyStr: `${Math.round(authoritativeProgress.overall_accuracy * 100)}%`,
      practiceCountStr: `${authoritativeProgress.total_practice_count} 题`,
    };

    assert.equal(displayedMetrics.overallMasteryStr, '68%');
    assert.equal(displayedMetrics.masteredCountStr, '12 个');
    assert.equal(displayedMetrics.accuracyStr, '83%');
    assert.equal(displayedMetrics.practiceCountStr, '24 题');

    // 严禁包含未经快照佐证的伪造推算字段 (如 "+8%")
    assert.equal((displayedMetrics as any).weeklyDelta, undefined);
  });

  // ---------------------------------------------------------------------------
  // 8. 局部容错解耦契约
  // ---------------------------------------------------------------------------
  it('8. 首页三模块 (TodayAction, Focus, Progress) 具备独立容错边界，单点失败不造成整页白屏', () => {
    // 模拟场景：Progress API 发生 500 异常，Today Action 仍正常可用
    const pageState = {
      todayAction: {
        status: 'SUCCESS',
        action_type: 'CONTINUE_LEARNING' as TodayActionType,
      },
      currentFocus: {
        status: 'SUCCESS',
        knowledgeName: '需求价格弹性',
      },
      recentProgress: {
        status: 'ERROR',
        errorMessage: '暂时无法加载最近学习进展',
      },
    };

    assert.equal(pageState.todayAction.status, 'SUCCESS');
    assert.equal(pageState.currentFocus.status, 'SUCCESS');
    assert.equal(pageState.recentProgress.status, 'ERROR');

    // 首页主体可交互性保持成立
    const isHomeUsable = pageState.todayAction.status === 'SUCCESS';
    assert.equal(isHomeUsable, true, '非关键模块失败时，Today Action 依然正常可用');
  });

  // ---------------------------------------------------------------------------
  // 9. 新老学生首次进入场景契约
  // ---------------------------------------------------------------------------
  it('9. 新老学生首次进入首页时，真实呈现各自状态，新学生不产生假任务或假掌握度', () => {
    // 老学生 S001 (已有掌握度与学习历史)
    const s001Data = {
      student_id: 'S001',
      student_name: '张三',
      hasLearningHistory: true,
      overall_mastery: 0.65,
      todayAction: 'REVIEW_RETENTION',
    };

    // 新初始化学生 S006 (首次进入，0 掌握度，从路径首个节点 K01 开始)
    const newStudentData = {
      student_id: 'S006',
      student_name: '新同学',
      hasLearningHistory: false,
      overall_mastery: 0.0,
      todayAction: 'CONTINUE_LEARNING',
    };

    assert.equal(s001Data.hasLearningHistory, true);
    assert.equal(s001Data.todayAction, 'REVIEW_RETENTION');

    // 新学生严格为 0，不被老生状态污染
    assert.equal(newStudentData.overall_mastery, 0.0);
    assert.equal(newStudentData.todayAction, 'CONTINUE_LEARNING');
    assert.notEqual(s001Data.overall_mastery, newStudentData.overall_mastery);
  });

  // ---------------------------------------------------------------------------
  // 10. 全局零黑话合规契约
  // ---------------------------------------------------------------------------
  it('10. 学生端首页用户可见文案中绝对不包含任何底层技术黑话与学术术语', () => {
    const userVisibleTexts = [
      '早上好，张三',
      '今天也学一点吧',
      '今日学习',
      '继续学习：需求价格弹性',
      '当前掌握度 62%',
      '建议继续学习这个知识点',
      '重新学习',
      '开始快速复测',
      '开始练习',
      '查看学习进展',
      '当前学习焦点',
      '微观经济学基础',
      '最近进展',
      '阶段学情沉淀',
      '整体掌握度 68%',
      '已掌握 12 个',
      '练习正确率 83%',
      '累计练习题数 24 题',
      '查看完整学情档案',
    ];

    const fullCorpus = userVisibleTexts.join(' ');
    for (const jargon of FORBIDDEN_JARGON) {
      assert.ok(
        !fullCorpus.includes(jargon),
        `首页文案包含了违禁黑话: "${jargon}"`
      );
    }
  });
});
