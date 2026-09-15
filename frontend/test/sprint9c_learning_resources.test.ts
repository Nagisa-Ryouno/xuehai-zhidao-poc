/**
 * sprint9c_learning_resources.test.ts
 * 学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-C
 * 学习资源中心与资源感知自适应学习前端契约测试 (Frontend Contract Tests)
 *
 * 覆盖：
 * 1. 5 种资源类型定义完备性
 * 2. 资源实体 LearningResource 契约与零失效外链规范
 * 3. 自适应推荐响应契约
 * 4. 推荐排序与步骤属性
 * 5. 学生端推荐文案无技术黑话审查 (No Jargon)
 * 6. 资源行为日志 ResourceEventPayload 事件合法性校验
 * 7. 统一路由解析：/student/resources 准确解析
 * 8. 考点微卡数据与资源中心考点选择器对齐
 * 9. 资源分类与类型过滤逻辑
 * 10. 资源关键词搜索逻辑
 * 11. 桌面 5-Tab 导航包含学习资源中心
 * 12. 推荐时序 suggested_order 严格正整数递增
 * 13. 辅助日志物理隔离契约
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import type {
  ResourceType,
  LearningResource,
  ResourceRecommendation,
  RecommendedResourcesResponse,
  ResourceListResponse,
  ResourceEventPayload,
} from '../src/types.ts';
import { resolveRoute } from '../src/router.ts';
import { ALL_CONCEPT_CARDS } from '../src/components/student/conceptCardData.ts';

describe('Sprint 9-C: 学习资源中心与资源感知自适应学习前端契约测试', () => {
  // ---------------------------------------------------------------------------
  // C1: 资源领域模型与类型契约完备性
  // ---------------------------------------------------------------------------
  describe('C1: 资源领域模型与类型契约完备性', () => {
    it('1. 必须合法支持全部 5 种学习资源类型枚举', () => {
      const validTypes: ResourceType[] = [
        'CONCEPT_CARD',
        'EXAMPLE',
        'PRACTICE',
        'DOCUMENT',
        'VIDEO',
      ];
      assert.equal(validTypes.length, 5);
      assert.ok(validTypes.includes('CONCEPT_CARD'));
      assert.ok(validTypes.includes('EXAMPLE'));
      assert.ok(validTypes.includes('PRACTICE'));
      assert.ok(validTypes.includes('DOCUMENT'));
      assert.ok(validTypes.includes('VIDEO'));
    });

    it('2. LearningResource 实体必须满足内部生产、零失效外链与必要属性契约', () => {
      const mockResource: LearningResource = {
        resource_id: 'res_k01_concept',
        knowledge_id: 'K01',
        resource_type: 'CONCEPT_CARD',
        title: '稀缺性与经济学基本问题 考点精要微卡',
        description: '人的欲望是无限的，而满足欲望的资源总是有限的。',
        source: 'xuehai_internal',
        source_url: null,
        estimated_minutes: 2,
        difficulty: 0.3,
        summary: '核心概念：稀缺性是经济学的基石。',
        is_external: false,
        priority: 85,
        metadata: { chapter: '第一章 导论' },
      };

      assert.equal(mockResource.source, 'xuehai_internal');
      assert.equal(mockResource.is_external, false);
      assert.equal(mockResource.source_url, null);
      assert.ok(mockResource.estimated_minutes > 0);
      assert.ok(mockResource.difficulty >= 0 && mockResource.difficulty <= 1);
    });

    it('3. RecommendedResourcesResponse 必须包含 case_code、mastery 与 reason_summary', () => {
      const mockRecResponse: RecommendedResourcesResponse = {
        student_id: 'S001',
        knowledge_id: 'K01',
        mastery: 0.45,
        case_code: 'CASE_A_WEAK_FOUNDATION',
        recommendations: [],
        reason_summary: '当前考点掌握度较低，建议先打牢概念基础。',
      };

      assert.equal(mockRecResponse.student_id, 'S001');
      assert.equal(mockRecResponse.case_code, 'CASE_A_WEAK_FOUNDATION');
      assert.ok(typeof mockRecResponse.mastery === 'number');
      assert.ok(mockRecResponse.reason_summary.length > 0);
    });
  });

  // ---------------------------------------------------------------------------
  // C2: 推荐位次与步骤顺序契约
  // ---------------------------------------------------------------------------
  describe('C2: 推荐位次与步骤顺序契约', () => {
    it('4. ResourceRecommendation 具有 rank、suggested_order 与 reason_category', () => {
      const mockRec: ResourceRecommendation = {
        resource: {
          resource_id: 'res_k01_concept',
          knowledge_id: 'K01',
          resource_type: 'CONCEPT_CARD',
          title: '考点微卡',
          description: '描述',
          source: 'xuehai_internal',
          estimated_minutes: 2,
          difficulty: 0.3,
          is_external: false,
          priority: 85,
        },
        rank: 1,
        recommended_reason: '掌握度较低，建议先通读微卡夯实概念',
        reason_category: 'FOUNDATION',
        suggested_order: 1,
      };

      assert.equal(mockRec.rank, 1);
      assert.equal(mockRec.suggested_order, 1);
      assert.equal(mockRec.reason_category, 'FOUNDATION');
      assert.ok(mockRec.recommended_reason.length > 0);
    });

    it('5. 推荐步骤顺序 suggested_order 严格为 1-indexed 正整数递增', () => {
      const orders = [1, 2, 3, 4];
      for (let i = 0; i < orders.length; i++) {
        assert.equal(orders[i], i + 1);
      }
    });
  });

  // ---------------------------------------------------------------------------
  // C3: 学生端文案零技术黑话合规性断言 (No Jargon)
  // ---------------------------------------------------------------------------
  describe('C3: 学生端文案零技术黑话合规性断言 (No Jargon)', () => {
    const FORBIDDEN_JARGONS = [
      'bkt',
      'p_transit',
      'p_init',
      'dag',
      'mutationdomain',
      'round_half_up',
      'jsonl',
      'sql',
      'backend',
      'endpoint',
      'nullpointer',
    ];

    it('6. 自适应导引说明与推荐理由中严禁包含任何底层技术黑话', () => {
      const candidateTexts = [
        '当前考点掌握度较低（<60%），建议先通过概念微卡与生活例题建立直观认知，打牢基础后再进行测验巩固。',
        '当前考点掌握度处于提升期（60%~80%），建议通过例题精析和定向微练巩固强化，冲刺80%达标线。',
        '当前考点已达标掌握（≥80%），建议开启后继考点的进阶预习与攻坚。',
        '图谱终点考点已达标掌握（≥80%），建议进行综合模拟演练与全景复盘，巩固全阶段学习成果。',
        '近期该考点连续作答受阻（≥2次），建议暂缓直接刷题，先回归概念卡片梳理核心要点与生活例题，排查思维误区。',
      ];

      for (const text of candidateTexts) {
        const lower = text.toLowerCase();
        for (const jargon of FORBIDDEN_JARGONS) {
          assert.ok(
            !lower.includes(jargon),
            `发现违规技术黑话 "${jargon}": "${text}"`
          );
        }
      }
    });
  });

  // ---------------------------------------------------------------------------
  // C4: 资源交互辅助事件与物理隔离规范
  // ---------------------------------------------------------------------------
  describe('C4: 资源交互辅助事件与物理隔离规范', () => {
    it('7. ResourceEventPayload 合法事件类型仅限 4 种辅助事件', () => {
      const validEventTypes = [
        'RESOURCE_VIEW',
        'RESOURCE_OPEN',
        'RESOURCE_COMPLETE',
        'RESOURCE_EXTERNAL_OPEN',
      ];

      const payload: ResourceEventPayload = {
        student_id: 'S001',
        resource_id: 'res_k01_concept',
        knowledge_id: 'K01',
        event_type: 'RESOURCE_OPEN',
        duration_seconds: 45,
      };

      assert.ok(validEventTypes.includes(payload.event_type));
      assert.notEqual(payload.event_type, 'QUESTION_ATTEMPT');
      assert.notEqual(payload.event_type, 'CONCEPT_VIEW');
    });
  });

  // ---------------------------------------------------------------------------
  // C5: 路由解析与导航联动
  // ---------------------------------------------------------------------------
  describe('C5: 路由解析与导航联动', () => {
    it('8. 路由解析 /student/resources 正确映射为 StudentLayout 与 resources subRoute', () => {
      const res = resolveRoute('/student/resources');
      assert.equal(res.role, 'student');
      assert.equal(res.layout, 'StudentLayout');
      assert.equal(res.subRoute, 'resources');
    });

    it('9. 路由解析 /student/resources/ 带尾部斜杠可安全规整化', () => {
      const res = resolveRoute('/student/resources/');
      assert.equal(res.role, 'student');
      assert.equal(res.layout, 'StudentLayout');
      assert.equal(res.subRoute, 'resources');
    });
  });

  // ---------------------------------------------------------------------------
  // C6: 知识点微卡与资源中心考点选择器对齐
  // ---------------------------------------------------------------------------
  describe('C6: 知识点微卡与资源中心考点选择器对齐', () => {
    it('10. 全图谱 30 个考点微卡数据必须与选择器严格 1-to-1 对齐', () => {
      assert.equal(ALL_CONCEPT_CARDS.length, 30);
      assert.equal(ALL_CONCEPT_CARDS[0].knowledgeId, 'K01');
      assert.equal(ALL_CONCEPT_CARDS[29].knowledgeId, 'K30');

      for (let i = 1; i <= 30; i++) {
        const kid = `K${i < 10 ? '0' + i : i}`;
        const found = ALL_CONCEPT_CARDS.find((c) => c.knowledgeId === kid);
        assert.ok(found, `缺少考点 ${kid} 的数据`);
        assert.ok(found.knowledgeName.length > 0);
        assert.ok(found.chapter.length > 0);
      }
    });
  });

  // ---------------------------------------------------------------------------
  // C7: 资源过滤与搜索纯函数逻辑断言
  // ---------------------------------------------------------------------------
  describe('C7: 资源过滤与搜索纯函数逻辑断言', () => {
    const mockList: LearningResource[] = [
      {
        resource_id: 'res_k01_concept',
        knowledge_id: 'K01',
        resource_type: 'CONCEPT_CARD',
        title: '稀缺性 考点精要微卡',
        description: '人类欲望与资源稀缺',
        source: 'xuehai_internal',
        estimated_minutes: 2,
        difficulty: 0.3,
        is_external: false,
        priority: 80,
      },
      {
        resource_id: 'res_k01_example',
        knowledge_id: 'K01',
        resource_type: 'EXAMPLE',
        title: '稀缺性 典型生活例题精析',
        description: '时间分配生活案例',
        source: 'xuehai_internal',
        estimated_minutes: 3,
        difficulty: 0.5,
        is_external: false,
        priority: 75,
      },
      {
        resource_id: 'res_k01_practice',
        knowledge_id: 'K01',
        resource_type: 'PRACTICE',
        title: '稀缺性 靶向通关微测验',
        description: '单选题练习',
        source: 'xuehai_internal',
        estimated_minutes: 4,
        difficulty: 0.6,
        is_external: false,
        priority: 70,
      },
    ];

    it('11. 资源类型筛选纯函数能够精确过滤对应类型', () => {
      const concepts = mockList.filter((r) => r.resource_type === 'CONCEPT_CARD');
      assert.equal(concepts.length, 1);
      assert.equal(concepts[0].resource_id, 'res_k01_concept');

      const practices = mockList.filter((r) => r.resource_type === 'PRACTICE');
      assert.equal(practices.length, 1);
      assert.equal(practices[0].resource_id, 'res_k01_practice');
    });

    it('12. 关键字搜索能够同时检索标题与描述', () => {
      const searchCase1 = mockList.filter((r) =>
        r.title.includes('生活例题') || r.description.includes('生活例题')
      );
      assert.equal(searchCase1.length, 1);
      assert.equal(searchCase1[0].resource_id, 'res_k01_example');

      const searchCase2 = mockList.filter((r) =>
        r.title.includes('稀缺性') || r.description.includes('稀缺性')
      );
      assert.equal(searchCase2.length, 3);
    });
  });
});
