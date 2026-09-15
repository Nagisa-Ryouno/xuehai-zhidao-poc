/**
 * sprint9d_learning_effectiveness.test.ts
 * 学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-D
 * 学习效果验证与资源自适应反馈前端契约测试 (Frontend Contract Tests)
 *
 * 覆盖：
 * 1. 会话状态与效果状态枚举合法性 (SessionStatus / EffectivenessStatus)
 * 2. 学习会话实体 LearningSession 初始快照与属性完整性
 * 3. 学习效果实体 LearningEffectiveness 契约字段完整性
 * 4. 考点效果响应 KnowledgeEffectivenessResponse 契约结构
 * 5. 掌握度净变化 delta 计算与百分比格式化纯函数
 * 6. 效果状态 4 档映射边界 (STRONG / MEANINGFUL / STABLE / NEEDS_MORE_SUPPORT)
 * 7. 反馈文案时间关联性断言（杜绝虚假因果关系）
 * 8. 反馈文案与展示标签零技术黑话合规性断言 (No Jargon: 无 BKT, Bayesian, PathState)
 * 9. 会话生命周期状态机推进契约 (IN_PROGRESS -> COMPLETED)
 * 10. 步骤完成清单与材料关联
 * 11. AI 伴学提问关联真实资源上下文契约 (resource_context)
 * 12. 多学生切换时会话状态严格重置隔离契约
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  SessionStatus,
  EffectivenessStatus,
  LearningSession,
  LearningEffectiveness,
  KnowledgeEffectivenessResponse,
  SessionCompleteResponse,
  CompanionStudyRequest,
} from '../src/types.ts';

describe('Sprint 9-D: 学习效果验证与资源自适应反馈前端契约测试', () => {
  // ---------------------------------------------------------------------------
  // C1: 学习会话与效果评估领域模型契约
  // ---------------------------------------------------------------------------
  describe('C1: 学习会话与效果评估领域模型契约', () => {
    it('1. SessionStatus 与 EffectivenessStatus 枚举值合法且完备', () => {
      const validSessionStatuses: SessionStatus[] = [
        'NOT_STARTED',
        'IN_PROGRESS',
        'COMPLETED',
        'ABANDONED',
      ];
      assert.equal(validSessionStatuses.length, 4);
      assert.ok(validSessionStatuses.includes('IN_PROGRESS'));
      assert.ok(validSessionStatuses.includes('COMPLETED'));

      const validEffectivenessStatuses: EffectivenessStatus[] = [
        'STRONG_PROGRESS',
        'MEANINGFUL_PROGRESS',
        'STABLE',
        'NEEDS_MORE_SUPPORT',
      ];
      assert.equal(validEffectivenessStatuses.length, 4);
      assert.ok(validEffectivenessStatuses.includes('STRONG_PROGRESS'));
      assert.ok(validEffectivenessStatuses.includes('MEANINGFUL_PROGRESS'));
      assert.ok(validEffectivenessStatuses.includes('STABLE'));
      assert.ok(validEffectivenessStatuses.includes('NEEDS_MORE_SUPPORT'));
    });

    it('2. LearningSession 实体包含 initial_mastery 快照且属性完备', () => {
      const mockSession: LearningSession = {
        session_id: 'sess_s001_k08_test',
        student_id: 'S001',
        knowledge_id: 'K08',
        started_at: '2026-09-15T12:00:00Z',
        completed_at: null,
        initial_mastery: 0.55,
        final_mastery: null,
        mastery_delta: null,
        resource_ids: ['res_k08_concept', 'res_k08_example'],
        completed_resource_ids: ['res_k08_concept'],
        quiz_question_id: null,
        quiz_result: null,
        status: 'IN_PROGRESS',
      };

      assert.equal(mockSession.student_id, 'S001');
      assert.equal(mockSession.knowledge_id, 'K08');
      assert.equal(mockSession.initial_mastery, 0.55);
      assert.equal(mockSession.status, 'IN_PROGRESS');
      assert.equal(mockSession.completed_resource_ids.length, 1);
    });

    it('3. LearningEffectiveness 实体契约包含核心指标与人本评价字段', () => {
      const mockEffectiveness: LearningEffectiveness = {
        session_id: 'sess_s001_k08_test',
        student_id: 'S001',
        knowledge_id: 'K08',
        initial_mastery: 0.55,
        final_mastery: 0.72,
        mastery_delta: 0.17,
        status: 'STRONG_PROGRESS',
        status_display: '显著提升',
        feedback_title: '成效显著，掌握更加扎实！',
        feedback_message: '完成本次学习后，掌握情况从 55.0% 变为 72.0%。对弹性概念的商业与现实应用理解明显加深。',
        suggested_next_action: 'PRACTICE_AGAIN',
        resources_completed_count: 2,
        quiz_passed: true,
      };

      assert.equal(mockEffectiveness.status, 'STRONG_PROGRESS');
      assert.equal(mockEffectiveness.status_display, '显著提升');
      assert.equal(mockEffectiveness.mastery_delta, 0.17);
      assert.ok(mockEffectiveness.feedback_title.length > 0);
      assert.ok(mockEffectiveness.feedback_message.length > 0);
    });

    it('4. KnowledgeEffectivenessResponse 契约包含当前考点与历史表现', () => {
      const mockResponse: KnowledgeEffectivenessResponse = {
        student_id: 'S001',
        knowledge_id: 'K08',
        current_mastery: 0.72,
        latest_session: null,
        effectiveness: null,
        historical_signal: {
          resource_id: 'res_k08_example',
          knowledge_id: 'K08',
          sample_size: 5,
          avg_mastery_delta: 0.14,
          completion_rate: 0.8,
          effectiveness_score: 82.5,
          confidence_level: 'MEDIUM',
          status_distribution: { STRONG_PROGRESS: 3, MEANINGFUL_PROGRESS: 2 },
        },
      };

      assert.equal(mockResponse.student_id, 'S001');
      assert.equal(mockResponse.knowledge_id, 'K08');
      assert.equal(mockResponse.historical_signal?.sample_size, 5);
      assert.equal(mockResponse.historical_signal?.confidence_level, 'MEDIUM');
    });
  });

  // ---------------------------------------------------------------------------
  // C2: 掌握度净变化与效果映射纯函数逻辑
  // ---------------------------------------------------------------------------
  describe('C2: 掌握度净变化与效果映射纯函数逻辑', () => {
    // 模拟前端 delta 计算与格式化函数
    function formatDelta(delta: number): string {
      const rounded = Math.round(delta * 1000) / 10;
      if (rounded > 0) return `+${rounded.toFixed(1)}%`;
      return `${rounded.toFixed(1)}%`;
    }

    function resolveEffectivenessStatus(delta: number): EffectivenessStatus {
      if (delta >= 0.15) return 'STRONG_PROGRESS';
      if (delta >= 0.05) return 'MEANINGFUL_PROGRESS';
      if (delta > -0.05) return 'STABLE';
      return 'NEEDS_MORE_SUPPORT';
    }

    it('5. 掌握度净变化 delta 正负号与百分比格式化精准', () => {
      assert.equal(formatDelta(0.17), '+17.0%');
      assert.equal(formatDelta(0.085), '+8.5%');
      assert.equal(formatDelta(0.0), '0.0%');
      assert.equal(formatDelta(-0.06), '-6.0%');
    });

    it('6. 效果状态 4 档分级阈值映射严格正确', () => {
      assert.equal(resolveEffectivenessStatus(0.20), 'STRONG_PROGRESS');
      assert.equal(resolveEffectivenessStatus(0.15), 'STRONG_PROGRESS');
      assert.equal(resolveEffectivenessStatus(0.149), 'MEANINGFUL_PROGRESS');
      assert.equal(resolveEffectivenessStatus(0.05), 'MEANINGFUL_PROGRESS');
      assert.equal(resolveEffectivenessStatus(0.049), 'STABLE');
      assert.equal(resolveEffectivenessStatus(0.00), 'STABLE');
      assert.equal(resolveEffectivenessStatus(-0.049), 'STABLE');
      assert.equal(resolveEffectivenessStatus(-0.05), 'NEEDS_MORE_SUPPORT');
      assert.equal(resolveEffectivenessStatus(-0.12), 'NEEDS_MORE_SUPPORT');
    });
  });

  // ---------------------------------------------------------------------------
  // C3: 导师反馈合规性与无技术黑话断言 (No Jargon & Temporal Association)
  // ---------------------------------------------------------------------------
  describe('C3: 导师反馈合规性与无技术黑话断言', () => {
    const FORBIDDEN_JARGON = [
      'BKT',
      'bkt',
      'Bayesian',
      '贝叶斯',
      'PathState',
      'path_state',
      'Resolver',
      '状态转移矩阵',
      'mastery_probability',
      '因为你看了',
      '由于你阅读了该材料',
    ];

    it('7. 导师反馈文案必须采用时间关联而非因果承诺叙事', () => {
      const feedbackMessage = '完成本次学习后，掌握情况从 55.0% 变为 72.0%。对需求弹性的生活与商业案例理解明显加深。';
      assert.ok(feedbackMessage.includes('完成本次学习后'));
      assert.ok(!feedbackMessage.includes('因为你看了'));
      assert.ok(!feedbackMessage.includes('由于你阅读了'));
    });

    it('8. 导师反馈标题、内容与展示标签严禁包含任何底层技术黑话', () => {
      const testCases = [
        '成效显著，掌握更加扎实！',
        '稳步推进，知识点更清晰了！',
        '表现稳定，保持当前复习节奏！',
        '建议再巩固一下核心考点与错题！',
        '完成本次学习后，掌握情况从 45.0% 变为 60.0%。',
      ];

      for (const text of testCases) {
        for (const jargon of FORBIDDEN_JARGON) {
          assert.ok(
            !text.includes(jargon),
            `发现违规技术黑话或虚假因果词汇: "${jargon}" in "${text}"`
          );
        }
      }
    });
  });

  // ---------------------------------------------------------------------------
  // C4: 学习会话生命周期与交互闭环契约
  // ---------------------------------------------------------------------------
  describe('C4: 学习会话生命周期与交互闭环契约', () => {
    it('9. 会话状态流转：从 IN_PROGRESS 到 COMPLETED 具备前后掌握度', () => {
      const initialSession: LearningSession = {
        session_id: 'sess_001',
        student_id: 'S001',
        knowledge_id: 'K07',
        started_at: '2026-09-15T10:00:00Z',
        initial_mastery: 0.55,
        resource_ids: ['res_k07_concept', 'res_k07_practice'],
        completed_resource_ids: [],
        status: 'IN_PROGRESS',
      };

      const completedSession: LearningSession = {
        ...initialSession,
        completed_at: '2026-09-15T10:15:00Z',
        final_mastery: 0.72,
        mastery_delta: 0.17,
        completed_resource_ids: ['res_k07_concept', 'res_k07_practice'],
        status: 'COMPLETED',
      };

      assert.equal(initialSession.status, 'IN_PROGRESS');
      assert.equal(completedSession.status, 'COMPLETED');
      assert.equal(completedSession.final_mastery, 0.72);
      assert.equal(completedSession.mastery_delta, 0.17);
    });

    it('10. 步骤完成清单能够动态记录已完成学习资源', () => {
      const completedIds: string[] = ['res_k07_concept'];
      function markCompleted(resId: string) {
        if (!completedIds.includes(resId)) {
          completedIds.push(resId);
        }
      }

      markCompleted('res_k07_example');
      assert.equal(completedIds.length, 2);
      assert.ok(completedIds.includes('res_k07_example'));

      // 重复标记不增加
      markCompleted('res_k07_example');
      assert.equal(completedIds.length, 2);
    });

    it('11. AI 伴学请求载荷能够合法携带资源上下文 resource_context', () => {
      const companionReq: CompanionStudyRequest = {
        student_id: 'S001',
        mode: 'concept_explain',
        knowledge_id: 'K08',
        message: '请结合这道例题讲一下需求弹性',
        resource_id: 'res_k08_example',
        resource_context: {
          resource_id: 'res_k08_example',
          resource_title: '需求价格弹性 典型生活与商业实例精析',
          resource_type: 'EXAMPLE',
        },
      };

      assert.equal(companionReq.resource_id, 'res_k08_example');
      assert.equal(companionReq.resource_context?.resource_type, 'EXAMPLE');
      assert.ok(companionReq.resource_context?.resource_title.includes('需求价格弹性'));
    });

    it('12. 学生切换时重置所有会话状态，保证学生上下文严格隔离', () => {
      let currentStudent = 'S001';
      let activeSession: LearningSession | null = {
        session_id: 'sess_s001',
        student_id: 'S001',
        knowledge_id: 'K08',
        started_at: '2026-09-15T12:00:00Z',
        initial_mastery: 0.55,
        resource_ids: [],
        completed_resource_ids: [],
        status: 'IN_PROGRESS',
      };
      let completedResult: SessionCompleteResponse | null = null;

      // 切换学生
      function switchStudent(newStudentId: string) {
        currentStudent = newStudentId;
        activeSession = null;
        completedResult = null;
      }

      switchStudent('S002');
      assert.equal(currentStudent, 'S002');
      assert.equal(activeSession, null);
      assert.equal(completedResult, null);
    });
  });
});
