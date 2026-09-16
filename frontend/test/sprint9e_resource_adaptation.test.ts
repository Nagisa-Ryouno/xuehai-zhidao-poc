/**
 * sprint9e_resource_adaptation.test.ts
 * 学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-E
 * 学习保持度验证与资源策略自适应 Lite 前端契约测试 (Frontend Contract Tests)
 *
 * 覆盖：
 * 1. 历史资源效果等级枚举合法性 (HistoricalEffectiveness)
 * 2. 资源推荐实体扩展字段契约 (ResourceRecommendation: historical_effectiveness, why_recommended, score_adjustment)
 * 3. 资源效果档案与查询响应实体契约 (ResourceEffectivenessProfile & EffectivenessProfileResponse)
 * 4. 确定性微调分值映射 (+2, +1, 0, -1, 0)
 * 5. 确定性重排序算法模拟与稳定性断言 (final_score DESC, original_order ASC)
 * 6. 人本解释文案契约与无技术黑话合规性 (No Jargon: 严禁 BKT, 贝叶斯, 向量, 算法分值泄露)
 * 7. 优雅降级与样本不足默认回退契约 (INSUFFICIENT_DATA 零伪造历史标签)
 * 8. 多学生上下文隔离性断言
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  HistoricalEffectiveness,
  ResourceEffectivenessProfile,
  EffectivenessProfileResponse,
  ResourceRecommendation,
  LearningResource,
} from '../src/types.ts';

// 严禁暴露的底层黑话与算法名词白名单
const FORBIDDEN_JARGON = [
  'BKT',
  'bkt',
  'Bayesian',
  'bayesian',
  '贝叶斯',
  '先验',
  '后验',
  '参数',
  '算法分',
  'score_adjustment',
  'final_score',
  '向量数据库',
  '大模型',
  '冷启动',
  '探索率',
  '强化学习',
];

describe('Sprint 9-E: 学习保持度验证与资源策略自适应 Lite 前端契约测试', () => {
  // ---------------------------------------------------------------------------
  // C1: 历史效果等级与自适应推荐契约
  // ---------------------------------------------------------------------------
  describe('C1: 历史效果等级与自适应推荐契约', () => {
    it('1. HistoricalEffectiveness 5 档枚举值合法且完备', () => {
      const validLevels: HistoricalEffectiveness[] = [
        'VERY_EFFECTIVE',
        'EFFECTIVE',
        'NEUTRAL',
        'INEFFECTIVE',
        'INSUFFICIENT_DATA',
      ];
      assert.equal(validLevels.length, 5);
      assert.ok(validLevels.includes('VERY_EFFECTIVE'));
      assert.ok(validLevels.includes('EFFECTIVE'));
      assert.ok(validLevels.includes('NEUTRAL'));
      assert.ok(validLevels.includes('INEFFECTIVE'));
      assert.ok(validLevels.includes('INSUFFICIENT_DATA'));
    });

    it('2. ResourceRecommendation 实体包含 Sprint 9-E 自适应微调与解释字段', () => {
      const mockResource: LearningResource = {
        resource_id: 'res_k08_example_01',
        knowledge_id: 'K08',
        resource_type: 'EXAMPLE',
        title: '需求价格弹性 典型生活与商业实例精析',
        description: '剖析奢侈品与生活必需品的弹性差异',
        source: '内部教研精编',
        estimated_minutes: 5,
        difficulty: 3,
        is_external: false,
        priority: 1,
      };

      const mockRec: ResourceRecommendation = {
        resource: mockResource,
        rank: 1,
        recommended_reason: '当前阶段重点突破例题分析',
        reason_category: 'PRACTICE_BEFORE_QUIZ',
        suggested_order: 1,
        historical_effectiveness: 'VERY_EFFECTIVE',
        why_recommended: '你之前用这种学习方式时，掌握情况有过比较明显的提升。',
        score_adjustment: 2,
      };

      assert.equal(mockRec.rank, 1);
      assert.equal(mockRec.suggested_order, 1);
      assert.equal(mockRec.historical_effectiveness, 'VERY_EFFECTIVE');
      assert.equal(mockRec.score_adjustment, 2);
      assert.ok(mockRec.why_recommended?.includes('比较明显的提升'));
    });

    it('3. ResourceEffectivenessProfile 与 EffectivenessProfileResponse 结构完整', () => {
      const profile: ResourceEffectivenessProfile = {
        student_id: 'S001',
        knowledge_id: 'K08',
        resource_type: 'EXAMPLE',
        usage_count: 3,
        average_delta: 0.15,
        last_delta: 0.18,
        effectiveness: 'VERY_EFFECTIVE',
      };

      const response: EffectivenessProfileResponse = {
        student_id: 'S001',
        knowledge_id: 'K08',
        profiles: [profile],
      };

      assert.equal(response.student_id, 'S001');
      assert.equal(response.knowledge_id, 'K08');
      assert.equal(response.profiles.length, 1);
      assert.equal(response.profiles[0].usage_count, 3);
      assert.equal(response.profiles[0].average_delta, 0.15);
      assert.equal(response.profiles[0].effectiveness, 'VERY_EFFECTIVE');
    });
  });

  // ---------------------------------------------------------------------------
  // C2: 确定性微调分值与稳定重排序纯函数逻辑
  // ---------------------------------------------------------------------------
  describe('C2: 确定性微调分值与稳定重排序纯函数逻辑', () => {
    it('4. 确定性微调分值映射契约 (+2, +1, 0, -1, 0)', () => {
      const adjustmentMap: Record<HistoricalEffectiveness, number> = {
        VERY_EFFECTIVE: 2,
        EFFECTIVE: 1,
        NEUTRAL: 0,
        INEFFECTIVE: -1,
        INSUFFICIENT_DATA: 0,
      };

      assert.equal(adjustmentMap.VERY_EFFECTIVE, 2);
      assert.equal(adjustmentMap.EFFECTIVE, 1);
      assert.equal(adjustmentMap.NEUTRAL, 0);
      assert.equal(adjustmentMap.INEFFECTIVE, -1);
      assert.equal(adjustmentMap.INSUFFICIENT_DATA, 0);
    });

    it('5. 候选资源二次排序遵循 (final_score 降序, original_order 升序) 稳定仲裁', () => {
      interface CandidateItem {
        id: string;
        original_order: number;
        base_score: number;
        adjustment: number;
        final_score: number;
      }

      // 模拟标准场景：初始 A(1), B(2), C(3)
      // A: +1, B: +2, C: 0
      const candidates: CandidateItem[] = [
        { id: 'A', original_order: 1, base_score: 100.0, adjustment: 1, final_score: 100.0 + 1 * 10.0 }, // 110
        { id: 'B', original_order: 2, base_score: 95.0, adjustment: 2, final_score: 95.0 + 2 * 10.0 },   // 115
        { id: 'C', original_order: 3, base_score: 90.0, adjustment: 0, final_score: 90.0 + 0 * 10.0 },   // 90
      ];

      // 稳定排序算法
      const sorted = [...candidates].sort((x, y) => {
        if (y.final_score !== x.final_score) {
          return y.final_score - x.final_score;
        }
        return x.original_order - y.original_order;
      });

      // 期望排序为 B -> A -> C
      assert.equal(sorted[0].id, 'B');
      assert.equal(sorted[1].id, 'A');
      assert.equal(sorted[2].id, 'C');

      // 平局仲裁测试：同分时严格保持 original_order
      const tieCandidates: CandidateItem[] = [
        { id: 'T1', original_order: 1, base_score: 100.0, adjustment: 0, final_score: 100.0 },
        { id: 'T2', original_order: 2, base_score: 95.0, adjustment: 0.5, final_score: 100.0 },
      ];
      const sortedTies = [...tieCandidates].sort((x, y) => {
        if (y.final_score !== x.final_score) {
          return y.final_score - x.final_score;
        }
        return x.original_order - y.original_order;
      });
      assert.equal(sortedTies[0].id, 'T1');
      assert.equal(sortedTies[1].id, 'T2');
    });

    it('6. 样本不足 (INSUFFICIENT_DATA) 或无历史数据时微调为 0，原有顺序零扰动', () => {
      const candidates = [
        { id: 'res_1', original_order: 1, eff: 'INSUFFICIENT_DATA', adj: 0 },
        { id: 'res_2', original_order: 2, eff: 'INSUFFICIENT_DATA', adj: 0 },
        { id: 'res_3', original_order: 3, eff: 'INSUFFICIENT_DATA', adj: 0 },
      ];

      const scored = candidates.map((c) => ({
        ...c,
        final_score: 100.0 - (c.original_order - 1) * 5.0 + c.adj * 10.0,
      }));

      scored.sort((x, y) => {
        if (y.final_score !== x.final_score) {
          return y.final_score - x.final_score;
        }
        return x.original_order - y.original_order;
      });

      assert.equal(scored[0].id, 'res_1');
      assert.equal(scored[1].id, 'res_2');
      assert.equal(scored[2].id, 'res_3');
    });
  });

  // ---------------------------------------------------------------------------
  // C3: 推荐理由人本叙事与零技术黑话合规性
  // ---------------------------------------------------------------------------
  describe('C3: 推荐理由人本叙事与零技术黑话合规性', () => {
    it('7. 确定性文案模板准确映射且无底层技术黑话', () => {
      const templates: Record<HistoricalEffectiveness, string> = {
        VERY_EFFECTIVE: '你之前用这种学习方式时，掌握情况有过比较明显的提升。',
        EFFECTIVE: '你之前用这种学习方式时，掌握情况有过稳定提升。',
        NEUTRAL: '这是当前学习阶段适合你的学习方式。',
        INEFFECTIVE: '你之前用这种学习方式时，提升比较有限，这次换一种方式试试。',
        INSUFFICIENT_DATA: '这是当前学习阶段适合你的学习方式。',
      };

      // 验证各档文案
      assert.ok(templates.VERY_EFFECTIVE.includes('比较明显的提升'));
      assert.ok(templates.EFFECTIVE.includes('稳定提升'));
      assert.ok(templates.INEFFECTIVE.includes('这次换一种方式试试'));
      assert.ok(templates.NEUTRAL.includes('适合你的学习方式'));
      assert.ok(templates.INSUFFICIENT_DATA.includes('适合你的学习方式'));

      // 验证无任何技术黑话
      for (const [key, text] of Object.entries(templates)) {
        for (const jargon of FORBIDDEN_JARGON) {
          assert.ok(
            !text.includes(jargon),
            '发现违规技术黑话: ' + jargon + ' in template for ' + key + ': ' + text
          );
        }
      }
    });

    it('8. 多学生切换时，自适应推荐状态与微调标签独立隔离', () => {
      let activeStudent = 'S001';
      const studentRecommendations: Record<string, ResourceRecommendation[]> = {
        S001: [
          {
            resource: {
              resource_id: 'res_k08_example',
              knowledge_id: 'K08',
              resource_type: 'EXAMPLE',
              title: '典型例题',
              description: '',
              source: '',
              estimated_minutes: 5,
              difficulty: 3,
              is_external: false,
              priority: 1,
            },
            rank: 1,
            recommended_reason: '成效优选',
            reason_category: 'PRACTICE_BEFORE_QUIZ',
            suggested_order: 1,
            historical_effectiveness: 'VERY_EFFECTIVE',
            why_recommended: '你之前用这种学习方式时，掌握情况有过比较明显的提升。',
            score_adjustment: 2,
          },
        ],
        S002: [
          {
            resource: {
              resource_id: 'res_k08_concept',
              knowledge_id: 'K08',
              resource_type: 'CONCEPT_CARD',
              title: '考点微卡',
              description: '',
              source: '',
              estimated_minutes: 3,
              difficulty: 2,
              is_external: false,
              priority: 1,
            },
            rank: 1,
            recommended_reason: '基础筑基',
            reason_category: 'WEAK_FOUNDATION',
            suggested_order: 1,
            historical_effectiveness: 'INSUFFICIENT_DATA',
            why_recommended: '这是当前学习阶段适合你的学习方式。',
            score_adjustment: 0,
          },
        ],
      };

      // 验证 S001 为成效优选 (+2)
      activeStudent = 'S001';
      assert.equal(studentRecommendations[activeStudent][0].historical_effectiveness, 'VERY_EFFECTIVE');
      assert.equal(studentRecommendations[activeStudent][0].score_adjustment, 2);

      // 切换至 S002
      activeStudent = 'S002';
      assert.equal(studentRecommendations[activeStudent][0].historical_effectiveness, 'INSUFFICIENT_DATA');
      assert.equal(studentRecommendations[activeStudent][0].score_adjustment, 0);
    });
  });
});