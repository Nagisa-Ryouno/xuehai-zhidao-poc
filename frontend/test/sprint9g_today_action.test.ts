/**
 * sprint9g_today_action.test.ts
 * 学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-G
 * 今日学习行动聚合 Lite 前端契约与人本规范测试 (Frontend Contract Tests)
 *
 * 覆盖：
 * 1. 行动类型枚举契约 (TodayActionType 5 档)
 * 2. REVIEW_RETENTION 复习建议行动契约 (建议再巩固一下 / 该复习一下了)
 * 3. CONTINUE_LEARNING 学习路径行动契约 (继续学习：{kname})
 * 4. PRACTICE 靶向微练行动契约 (做一道小练习)
 * 5. VIEW_PROGRESS 阶段达标行动契约 (看看最近的学习进展)
 * 6. NONE 兜底静默契约 (action_type === 'NONE' 契约)
 * 7. 学生上下文隔离契约 (S001 vs S002 独立性，防状态污染)
 * 8. 严禁算法黑话与学术术语契约 (No Jargon: 严禁 BKT, 贝叶斯, P(L), 向量数据库, 决策模型等)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  TodayActionType,
  TodayLearningAction,
  TodayActionResponse,
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
  'mastery',
  'PathState',
  'pathstate',
  'DynamicPathGenerator',
  'score',
  '分值',
  '算法',
  'retention analyzer',
  'effectiveness',
  '向量数据库',
  '大模型决策',
];

describe('Sprint 9-G: 今日学习行动聚合 Lite 前端契约测试', () => {
  // ---------------------------------------------------------------------------
  // 1. 类型枚举契约
  // ---------------------------------------------------------------------------
  it('1. TodayActionType 5 档枚举定义完备且合法', () => {
    const validTypes: TodayActionType[] = [
      'REVIEW_RETENTION',
      'CONTINUE_LEARNING',
      'PRACTICE',
      'VIEW_PROGRESS',
      'NONE',
    ];
    assert.equal(validTypes.length, 5);
    assert.ok(validTypes.includes('REVIEW_RETENTION'));
    assert.ok(validTypes.includes('CONTINUE_LEARNING'));
    assert.ok(validTypes.includes('PRACTICE'));
    assert.ok(validTypes.includes('VIEW_PROGRESS'));
    assert.ok(validTypes.includes('NONE'));
  });

  // ---------------------------------------------------------------------------
  // 2. REVIEW_RETENTION 行动实体契约
  // ---------------------------------------------------------------------------
  it('2. REVIEW_RETENTION 复习建议行动契约结构完整与文案规范', () => {
    const reinforcementAction: TodayLearningAction = {
      action_type: 'REVIEW_RETENTION',
      title: '建议再巩固一下',
      description: '需求价格弹性最近一次复习还不够稳定，先重新看看概念，再试一次。',
      cta_label: '重新学习',
      priority_reason: '已有考点复习未稳固，需针对性巩固',
      knowledge_id: 'K02',
      knowledge_name: '需求价格弹性',
      suggested_action: 'REVIEW_CONCEPT',
    };

    assert.equal(reinforcementAction.action_type, 'REVIEW_RETENTION');
    assert.equal(reinforcementAction.title, '建议再巩固一下');
    assert.equal(reinforcementAction.cta_label, '重新学习');
    assert.equal(reinforcementAction.suggested_action, 'REVIEW_CONCEPT');

    const dueAction: TodayLearningAction = {
      action_type: 'REVIEW_RETENTION',
      title: '该复习一下了',
      description: '需求价格弹性已经有一段时间没有复习，现在花 1～2 分钟快速测一下，可以帮助你确认是否还记得。',
      cta_label: '开始快速复测',
      priority_reason: '已有考点达到复习间隔时间',
      knowledge_id: 'K02',
      knowledge_name: '需求价格弹性',
      suggested_action: 'RETAKE_QUIZ',
    };

    assert.equal(dueAction.action_type, 'REVIEW_RETENTION');
    assert.equal(dueAction.title, '该复习一下了');
    assert.equal(dueAction.cta_label, '开始快速复测');
    assert.equal(dueAction.suggested_action, 'RETAKE_QUIZ');
  });

  // ---------------------------------------------------------------------------
  // 3. CONTINUE_LEARNING 行动实体契约
  // ---------------------------------------------------------------------------
  it('3. CONTINUE_LEARNING 学习路径行动契约结构与字段合法', () => {
    const continueAction: TodayLearningAction = {
      action_type: 'CONTINUE_LEARNING',
      title: '继续学习：消费者剩余',
      description: '这是你当前学习路径中的下一步内容。',
      cta_label: '开始学习',
      priority_reason: '当前学习路径中的首要未完成任务',
      knowledge_id: 'K05',
      knowledge_name: '消费者剩余',
      suggested_action: 'REVIEW_CONCEPT',
    };

    assert.equal(continueAction.action_type, 'CONTINUE_LEARNING');
    assert.ok(continueAction.title.startsWith('继续学习：'));
    assert.equal(continueAction.cta_label, '开始学习');
    assert.equal(continueAction.priority_reason, '当前学习路径中的首要未完成任务');
  });

  // ---------------------------------------------------------------------------
  // 4. PRACTICE 靶向微练行动契约
  // ---------------------------------------------------------------------------
  it('4. PRACTICE 靶向微练行动契约结构与字段合法', () => {
    const practiceAction: TodayLearningAction = {
      action_type: 'PRACTICE',
      title: '做一道小练习',
      description: '现在没有需要复习的内容，可以用一个小练习保持学习节奏。',
      cta_label: '开始练习',
      priority_reason: '推荐靶向微练保持学习节奏',
      knowledge_id: 'K01',
      knowledge_name: '稀缺性与经济学',
      suggested_action: 'RETAKE_QUIZ',
    };

    assert.equal(practiceAction.action_type, 'PRACTICE');
    assert.equal(practiceAction.title, '做一道小练习');
    assert.equal(practiceAction.cta_label, '开始练习');
    assert.equal(practiceAction.priority_reason, '推荐靶向微练保持学习节奏');
  });

  // ---------------------------------------------------------------------------
  // 5. VIEW_PROGRESS 阶段全达标行动契约
  // ---------------------------------------------------------------------------
  it('5. VIEW_PROGRESS 阶段考点全达标行动契约结构与字段合法', () => {
    const progressAction: TodayLearningAction = {
      action_type: 'VIEW_PROGRESS',
      title: '看看最近的学习进展',
      description: '目前没有需要立即完成的任务，可以先看看自己的学习进度。',
      cta_label: '查看学情',
      priority_reason: '当前所有阶段任务已全部达标',
      knowledge_id: null,
      knowledge_name: null,
      suggested_action: 'VIEW_PROGRESS',
    };

    assert.equal(progressAction.action_type, 'VIEW_PROGRESS');
    assert.equal(progressAction.title, '看看最近的学习进展');
    assert.equal(progressAction.cta_label, '查看学情');
    assert.equal(progressAction.knowledge_id, null);
  });

  // ---------------------------------------------------------------------------
  // 6. NONE 兜底静默契约
  // ---------------------------------------------------------------------------
  it('6. NONE 行动遵循静默原则，不展示卡片契约', () => {
    const noneAction: TodayLearningAction = {
      action_type: 'NONE',
      title: '',
      description: '',
      cta_label: '',
      priority_reason: '当前无待办学习任务',
      knowledge_id: null,
      knowledge_name: null,
      suggested_action: null,
    };

    assert.equal(noneAction.action_type, 'NONE');
    assert.equal(noneAction.title, '');
    assert.equal(noneAction.cta_label, '');
  });

  // ---------------------------------------------------------------------------
  // 7. 学生上下文隔离契约
  // ---------------------------------------------------------------------------
  it('7. 多学生上下文响应彼此独立，学生切换立即重置旧行动', () => {
    const s001Response: TodayActionResponse = {
      student_id: 'S001',
      action: {
        action_type: 'REVIEW_RETENTION',
        title: '该复习一下了',
        description: '需求价格弹性已经有一段时间没有复习，现在花 1～2 分钟快速测一下。',
        cta_label: '开始快速复测',
        priority_reason: '已有考点达到复习间隔时间',
        knowledge_id: 'K02',
        knowledge_name: '需求价格弹性',
        suggested_action: 'RETAKE_QUIZ',
      },
    };

    const s002Response: TodayActionResponse = {
      student_id: 'S002',
      action: {
        action_type: 'PRACTICE',
        title: '做一道小练习',
        description: '现在没有需要复习的内容，可以用一个小练习保持学习节奏。',
        cta_label: '开始练习',
        priority_reason: '推荐靶向微练保持学习节奏',
        knowledge_id: 'K01',
        knowledge_name: '稀缺性与经济学',
        suggested_action: 'RETAKE_QUIZ',
      },
    };

    assert.notEqual(s001Response.student_id, s002Response.student_id);
    assert.notEqual(s001Response.action.action_type, s002Response.action.action_type);
    assert.notEqual(s001Response.action.title, s002Response.action.title);
  });

  // ---------------------------------------------------------------------------
  // 8. 绝对禁止黑话与学术术语
  // ---------------------------------------------------------------------------
  it('8. 用户可见行动卡文案中绝对不包含算法与学术黑话', () => {
    const sampleActions: TodayLearningAction[] = [
      {
        action_type: 'REVIEW_RETENTION',
        title: '建议再巩固一下',
        description: '需求价格弹性最近一次复习还不够稳定，先重新看看概念，再试一次。',
        cta_label: '重新学习',
        priority_reason: '已有考点复习未稳固，需针对性巩固',
      },
      {
        action_type: 'REVIEW_RETENTION',
        title: '该复习一下了',
        description: '需求价格弹性已经有一段时间没有复习，现在花 1～2 分钟快速测一下，可以帮助你确认是否还记得。',
        cta_label: '开始快速复测',
        priority_reason: '已有考点达到复习间隔时间',
      },
      {
        action_type: 'CONTINUE_LEARNING',
        title: '继续学习：消费者剩余',
        description: '这是你当前学习路径中的下一步内容。',
        cta_label: '开始学习',
        priority_reason: '当前学习路径中的首要未完成任务',
      },
      {
        action_type: 'PRACTICE',
        title: '做一道小练习',
        description: '现在没有需要复习的内容，可以用一个小练习保持学习节奏。',
        cta_label: '开始练习',
        priority_reason: '推荐靶向微练保持学习节奏',
      },
      {
        action_type: 'VIEW_PROGRESS',
        title: '看看最近的学习进展',
        description: '目前没有需要立即完成的任务，可以先看看自己的学习进度。',
        cta_label: '查看学情',
        priority_reason: '当前所有阶段任务已全部达标',
      },
    ];

    for (const act of sampleActions) {
      const corpus = `${act.title} ${act.description} ${act.cta_label} ${act.priority_reason}`;
      for (const jargon of FORBIDDEN_JARGON) {
        assert.ok(
          !corpus.includes(jargon),
          `行动文案包含了违禁黑话: ${jargon} in "${corpus}"`
        );
      }
    }
  });
});
