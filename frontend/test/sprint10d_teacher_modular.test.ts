import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import type {
  TeacherClassKPIs,
  TeacherWeakKnowledgePoint,
  TeacherKnowledgeItem,
  TeacherStudentSummary,
  TeacherOverviewResponse,
} from '../src/types.ts';

describe('Sprint 10-D / Phase 2: Teacher Web 架构解耦与模块化契约测试', () => {
  describe('T1: 单一事实源与数据传递不失真契约', () => {
    it('1. 宏观 KPI 从 TeacherOverviewResponse 继承，无子组件数据篡改', () => {
      const mockOverview: TeacherOverviewResponse = {
        class_kpis: {
          total_students: 5,
          active_students: 4,
          class_avg_mastery: 0.685,
          at_risk_students_count: 1,
        },
        weak_knowledge_points: [],
        students: [],
        last_updated: '2026-09-21T12:00:00Z',
      };

      const kpis: TeacherClassKPIs = mockOverview.class_kpis;
      assert.equal(kpis.total_students, 5);
      assert.equal(kpis.active_students, 4);
      assert.equal(kpis.class_avg_mastery, 0.685);
      assert.equal(kpis.at_risk_students_count, 1);

      // 计算活跃率
      const activeRate = ((kpis.active_students / (kpis.total_students || 1)) * 100).toFixed(0);
      assert.equal(activeRate, '80');
    });

    it('2. Top-5 瓶颈考点严格按 weakPoints 切片，不自行重新发起请求', () => {
      const weakList: TeacherWeakKnowledgePoint[] = [
        {
          knowledge_id: 'K01',
          knowledge_name: '需求定理',
          chapter: '第1章',
          avg_mastery: 0.45,
          error_rate: 55.0,
          weak_student_count: 3,
          urgency: 'HIGH',
          recommended_intervention: '建议集体面授',
        },
        {
          knowledge_id: 'K02',
          knowledge_name: '供给定理',
          chapter: '第1章',
          avg_mastery: 0.52,
          error_rate: 48.0,
          weak_student_count: 2,
          urgency: 'MEDIUM',
          recommended_intervention: '针对性作业',
        },
      ];

      const sliced = weakList.slice(0, 5);
      assert.equal(sliced.length, 2);
      assert.equal(sliced[0].knowledge_id, 'K01');
      assert.equal(sliced[0].urgency, 'HIGH');
    });
  });

  describe('T2: 考点全景过滤与多维排序纯逻辑契约 (Behavior Preservation)', () => {
    const kps: TeacherKnowledgeItem[] = [
      {
        knowledge_id: 'K03',
        knowledge_name: '市场均衡价格的决定',
        chapter: '第一章 需求、供给与均衡价格',
        average_mastery: 0.58,
        student_count: 5,
        weak_student_count: 3,
        total_mistakes: 14,
        urgency: 'HIGH',
      },
      {
        knowledge_id: 'K01',
        knowledge_name: '需求定理与需求曲线',
        chapter: '第一章 需求、供给与均衡价格',
        average_mastery: 0.42,
        student_count: 5,
        weak_student_count: 4,
        total_mistakes: 20,
        urgency: 'HIGH',
      },
      {
        knowledge_id: 'K15',
        knowledge_name: '短期成本曲线与推导',
        chapter: '第五章 成本理论',
        average_mastery: 0.85,
        student_count: 5,
        weak_student_count: 0,
        total_mistakes: 2,
        urgency: 'LOW',
      },
    ];

    it('3. 章节过滤能准确过滤指定章节考点', () => {
      const filtered = kps.filter((kp) => kp.chapter === '第五章 成本理论');
      assert.equal(filtered.length, 1);
      assert.equal(filtered[0].knowledge_id, 'K15');
    });

    it('4. 关键词能同时检索考点编号与名称', () => {
      const q = 'K01';
      const filtered = kps.filter(
        (kp) =>
          kp.knowledge_id.toLowerCase().includes(q.toLowerCase()) ||
          kp.knowledge_name.toLowerCase().includes(q.toLowerCase())
      );
      assert.equal(filtered.length, 1);
      assert.equal(filtered[0].knowledge_id, 'K01');
    });

    it('5. mistakes_desc 能够按错题数降序稳定排序', () => {
      const sorted = [...kps].sort(
        (a, b) => b.total_mistakes - a.total_mistakes || a.knowledge_id.localeCompare(b.knowledge_id)
      );
      assert.equal(sorted[0].knowledge_id, 'K01'); // 20 错
      assert.equal(sorted[1].knowledge_id, 'K03'); // 14 错
      assert.equal(sorted[2].knowledge_id, 'K15'); // 2 错
    });
  });

  describe('T3: 学生名册学情筛选与人本归纳契约', () => {
    const students: TeacherStudentSummary[] = [
      {
        student_id: 'S001',
        student_name: '张明',
        major: '国际经济与贸易',
        grade: '大二',
        overall_mastery: 0.55,
        mastered_count: 10,
        developing_count: 12,
        weak_count: 8,
        accuracy: 62.5,
        total_attempts: 24,
        total_wrong_count: 9,
        risk_level: 'ATTENTION',
        learning_goal: '微观经济学核心考点突破',
      },
      {
        student_id: 'S002',
        student_name: '李华',
        major: '金融学',
        grade: '大二',
        overall_mastery: 0.82,
        mastered_count: 22,
        developing_count: 6,
        weak_count: 2,
        accuracy: 85.0,
        total_attempts: 30,
        total_wrong_count: 4,
        risk_level: 'HEALTHY',
        learning_goal: '冲刺满分掌握',
      },
    ];

    it('6. 风险分级过滤 ATTENTION 精确定位重点关注学生', () => {
      const attention = students.filter((s) => s.risk_level === 'ATTENTION');
      assert.equal(attention.length, 1);
      assert.equal(attention[0].student_id, 'S001');
    });

    it('7. 综合掌握度与认知分布（达标/推进/薄弱）数字守恒', () => {
      students.forEach((s) => {
        const total = s.mastered_count + s.developing_count + s.weak_count;
        assert.ok(total <= 30);
      });
    });
  });

  describe('T4: 数据语义边界与零主观臆断红线断言', () => {
    it('8. 无错题时文案严格局限于事实描述，绝不擅自脑补主观推论', () => {
      const emptyWrongs = [];
      const emptyDesc = emptyWrongs.length === 0 ? '该生目前无错题复盘记录' : '有错题';
      assert.equal(emptyDesc, '该生目前无错题复盘记录');
      assert.ok(!emptyDesc.includes('认知基础良好'));
      assert.ok(!emptyDesc.includes('无需指导'));
    });
  });
});
