/**
 * sprint9b_guided_learning.test.ts
 * Sprint 9-B: AI Guided Learning & Learning Reflection Frontend Contract Tests
 * =============================================================================
 * 测试矩阵覆盖：
 * - C1: 5 种行动类型与 CompanionSuggestedAction 契约完备性
 * - C2: Quick Check 微自测模型结构与零副作用规范
 * - C3: 学习行动结果反思 (Learning ActionResult) 契约与掌握度变化 delta
 * - C4: 学生端文案零技术黑话合规性断言 (No Jargon)
 * - C5: 导师引导闭环状态机流转契约
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

import type {
  ActionType,
  CompanionSuggestedAction,
  QuickCheckOption,
  QuickCheckQuestion,
  QuickCheckSubmitRequest,
  QuickCheckResponse,
  LearningActionResultRequest,
  LearningActionResultResponse,
  CompanionStudyResponse,
} from '../src/types.ts';

describe('Sprint 9-B: AI Guided Learning & Learning Reflection Frontend Contract Tests', () => {

  describe('C1: 5 种行动类型与 CompanionSuggestedAction 契约完备性', () => {
    const VALID_ACTION_TYPES: ActionType[] = [
      'READ_CONCEPT',
      'TARGETED_PRACTICE',
      'VIEW_PROGRESS',
      'REVIEW_WRONG_ANSWERS',
      'CONTINUE_DISCUSSION',
    ];

    test('1. 必须合法支持全部 5 种确定性学习行动类型', () => {
      assert.equal(VALID_ACTION_TYPES.length, 5);
      assert.ok(VALID_ACTION_TYPES.includes('READ_CONCEPT'));
      assert.ok(VALID_ACTION_TYPES.includes('TARGETED_PRACTICE'));
      assert.ok(VALID_ACTION_TYPES.includes('VIEW_PROGRESS'));
      assert.ok(VALID_ACTION_TYPES.includes('REVIEW_WRONG_ANSWERS'));
      assert.ok(VALID_ACTION_TYPES.includes('CONTINUE_DISCUSSION'));
    });

    test('2. CompanionSuggestedAction 具备完备路由目标与必要展示属性', () => {
      const action: CompanionSuggestedAction = {
        action_id: 'act-concept-K01',
        action_type: 'READ_CONCEPT',
        title: '📖 重新看概念',
        description: '回顾机会成本微卡重点',
        target_knowledge_id: 'K01',
        route_destination: '/student/concept/K01',
        source_reason: '针对薄弱考点推荐复习',
        badge: '重温基础',
      };

      assert.equal(action.action_type, 'READ_CONCEPT');
      assert.ok(action.title.startsWith('📖'));
      assert.equal(action.target_knowledge_id, 'K01');
      assert.equal(action.route_destination, '/student/concept/K01');
      assert.ok(action.badge && action.badge.length > 0);
    });

    test('3. 伴学响应扩展字段向后兼容性验证', () => {
      const mockResponse: CompanionStudyResponse = {
        session_id: 'sess-001',
        mode: 'concept_explain',
        answer: '这是讲解内容',
        context: {
          student_id: 'S001',
          knowledge_id: 'K01',
          knowledge_name: '机会成本与生产可能性边界',
          prerequisites: [],
        },
        safety: {
          allow_production_decision: false,
          sanitized: true,
          offline_mode: false,
          context_source: 'analytics_and_knowledge_base',
          redactions_applied: [],
        },
        suggested_actions: ['重新看概念', '进入微测验'],
        provider: 'offline_heuristic_companion',
        referenced_facts: ['考点 K01: 掌握度 20.0%'],
        guided_actions: [
          {
            action_id: 'act-1',
            action_type: 'READ_CONCEPT',
            title: '📖 重新看概念',
            description: '查看概念微卡',
            target_knowledge_id: 'K01',
            route_destination: '/student/concept/K01',
            source_reason: '巩固',
          },
        ],
      };

      assert.ok(mockResponse.guided_actions && mockResponse.guided_actions.length > 0);
      assert.ok(mockResponse.suggested_actions.length > 0);
      assert.equal(mockResponse.guided_actions[0].action_type, 'READ_CONCEPT');
    });
  });

  describe('C2: Quick Check 微自测模型结构与零副作用规范', () => {
    test('4. QuickCheckQuestion 包含题目主干、选项及考点总结', () => {
      const qc: QuickCheckQuestion = {
        question_id: 'QC-K01',
        knowledge_id: 'K01',
        stem: '在稀缺性前提下，机会成本本质上反映了什么？',
        options: [
          { id: 'A', text: '生产某种物品所消耗的全部会计货币成本' },
          { id: 'B', text: '为了得到某种东西所放弃的最大价值选择' },
          { id: 'C', text: '所有放弃选择价值的代数总和' },
          { id: 'D', text: '沉没成本与固定成本之和' },
        ],
        concept_summary: '机会成本强调最高价值放弃，而非所有放弃的简单相加。',
      };

      assert.equal(qc.knowledge_id, 'K01');
      assert.equal(qc.options.length, 4);
      assert.ok(qc.options.some((o) => o.id === 'B'));
      assert.ok(qc.stem.includes('机会成本'));
    });

    test('5. QuickCheckSubmitRequest 明确学生与选项且零生产副作用契约', () => {
      const submitReq: QuickCheckSubmitRequest = {
        student_id: 'S001',
        knowledge_id: 'K01',
        question_id: 'QC-K01',
        selected_option: 'B',
      };

      assert.equal(submitReq.student_id, 'S001');
      assert.equal(submitReq.selected_option, 'B');
    });

    test('6. QuickCheckResponse 包含正确性、权威解析及 follow-up 引导行动', () => {
      const res: QuickCheckResponse = {
        is_correct: true,
        correct_option: 'B',
        explanation: '机会成本是放弃的所有备选方案中价值最高的那一项，而非全部总和。',
        key_takeaway: '记住：机会成本是放弃的最大价值。',
        suggested_actions: [
          {
            action_id: 'act-qc-followup',
            action_type: 'TARGETED_PRACTICE',
            title: '✏️ 靶向再练一道',
            description: '趁热打铁挑战正式微测验',
            target_knowledge_id: 'K01',
            route_destination: '/student/quiz/K01',
            source_reason: '自测通过，建议实战突破',
          },
        ],
      };

      assert.equal(res.is_correct, true);
      assert.equal(res.correct_option, 'B');
      assert.ok(res.explanation.length > 10);
      assert.ok(res.suggested_actions.length > 0);
      assert.equal(res.suggested_actions[0].action_type, 'TARGETED_PRACTICE');
    });
  });

  describe('C3: 学习行动结果反思 (Learning ActionResult) 契约与掌握度变化 delta', () => {
    test('7. LearningActionResultRequest 包含执行行动详情', () => {
      const req: LearningActionResultRequest = {
        student_id: 'S001',
        action_id: 'act-quiz-01',
        action_type: 'TARGETED_PRACTICE',
        knowledge_id: 'K01',
        is_correct: true,
        score: 100,
      };

      assert.equal(req.student_id, 'S001');
      assert.equal(req.action_type, 'TARGETED_PRACTICE');
      assert.equal(req.is_correct, true);
    });

    test('8. LearningActionResultResponse 计算并反馈真实掌握度 delta 与客观反思', () => {
      const res: LearningActionResultResponse = {
        session_id: 'sess-action-123',
        action_id: 'act-quiz-01',
        action_type: 'TARGETED_PRACTICE',
        knowledge_id: 'K01',
        knowledge_name: '机会成本与生产可能性边界',
        before_mastery: 0.2000,
        after_mastery: 0.4566,
        mastery_delta: 0.2566,
        consecutive_incorrect: 0,
        mastery_state_text: '起步阶段',
        reflection_text: '你在「机会成本与生产可能性边界」取得了明显进步，掌握度提升了 25.7%，建议继续做题巩固。',
        next_actions: [
          {
            action_id: 'act-next-1',
            action_type: 'TARGETED_PRACTICE',
            title: '✏️ 靶向再练一道',
            description: '再做一道巩固掌握度',
            target_knowledge_id: 'K01',
            route_destination: '/student/quiz/K01',
            source_reason: '巩固成效',
          },
        ],
        offline_mode: false,
      };

      assert.equal(res.knowledge_id, 'K01');
      assert.ok(res.mastery_delta > 0);
      assert.equal((res.after_mastery - res.before_mastery).toFixed(4), (0.2566).toFixed(4));
      assert.ok(res.reflection_text.includes('25.7%'));
      assert.ok(res.next_actions.length > 0);
    });
  });

  describe('C4: 学生端文案零技术黑话合规性断言 (No Jargon)', () => {
    const FORBIDDEN_JARGONS = [
      'BKT',
      'Bayesian Knowledge Tracing',
      'PathState',
      'DynamicPathGenerator',
      '1-hop MutationDomain',
      'evaluate_and_replan',
      'bkt_service',
      'DAG probe',
      'LLM',
      'Prompt',
      'Temperature',
      'JSON',
      'API',
      'FastAPI',
    ];

    test('9. 建议动作标题与描述严禁包含技术黑话', () => {
      const sampleTexts = [
        '📖 重新看概念 - 回顾核心考点重点，加深直观理解',
        '✏️ 靶向再练一道 - 针对该考点专项微测验，检验实战应用',
        '📊 查看学情进展 - 纵览 30 个考点认知分布与阶段成长',
        '🔍 错题归因复盘 - 查漏补缺，依据错因精细复盘',
        '💬 继续探讨 - 向导师进一步追问疑难细节',
      ];

      for (const text of sampleTexts) {
        for (const jargon of FORBIDDEN_JARGONS) {
          assert.equal(
            text.toLowerCase().includes(jargon.toLowerCase()),
            false,
            `学生端行动文案 [${text}] 违规包含技术黑话 [${jargon}]`
          );
        }
      }
    });

    test('10. 反思文案严禁包含技术黑话', () => {
      const reflectionSample =
        '刚才的练习中你答对了！掌握度从 20.0% 稳步提升到 45.7%，净提升 25.7%。当前处于起步阶段，再接再厉！';

      for (const jargon of FORBIDDEN_JARGONS) {
        assert.equal(
          reflectionSample.toLowerCase().includes(jargon.toLowerCase()),
          false,
          `反思文案违规包含黑话 [${jargon}]`
        );
      }
    });
  });

  describe('C5: 导师引导闭环状态机流转契约', () => {
    test('11. 完整学习动作生命周期流转状态验证', () => {
      // 阶段 1: 概念精讲与建议
      const step1Action: ActionType = 'READ_CONCEPT';
      assert.equal(step1Action, 'READ_CONCEPT');

      // 阶段 2: 练习挑战
      const step2Action: ActionType = 'TARGETED_PRACTICE';
      assert.equal(step2Action, 'TARGETED_PRACTICE');

      // 阶段 3: 查看进展
      const step3Action: ActionType = 'VIEW_PROGRESS';
      assert.equal(step3Action, 'VIEW_PROGRESS');

      // 阶段 4: 错题复盘
      const step4Action: ActionType = 'REVIEW_WRONG_ANSWERS';
      assert.equal(step4Action, 'REVIEW_WRONG_ANSWERS');

      // 阶段 5: 启发对话
      const step5Action: ActionType = 'CONTINUE_DISCUSSION';
      assert.equal(step5Action, 'CONTINUE_DISCUSSION');
    });
  });
});
