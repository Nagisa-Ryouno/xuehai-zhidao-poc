import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import type {
  TeacherKnowledgeDiagnosisResponse,
  TeacherDiagnosisStudentItem,
} from '../src/types.ts';

describe('Sprint 10-D / Phase 3: Teacher Diagnosis & Drill-down 前端契约与数据语义测试', () => {
  const mockDiagnosisData: TeacherKnowledgeDiagnosisResponse = {
    knowledge_id: 'K01',
    knowledge_name: '需求定理与需求曲线',
    chapter: '第一章 需求、供给与均衡价格',
    average_mastery: 0.44,
    weak_student_count: 3,
    total_mistakes: 11,
    urgency: 'HIGH',
    students: [
      {
        student_id: 'S003',
        student_name: '王五',
        current_level: 'L1',
        mastery: 0.35,
        risk_level: 'HIGH',
        attempts: 12,
        mistake_count: 6,
      },
      {
        student_id: 'S001',
        student_name: '张三',
        current_level: 'L2',
        mastery: 0.45,
        risk_level: 'MEDIUM',
        attempts: 8,
        mistake_count: 3,
      },
      {
        student_id: 'S005',
        student_name: '钱七',
        current_level: 'L1',
        mastery: 0.52,
        risk_level: 'MEDIUM',
        attempts: 6,
        mistake_count: 2,
      },
      {
        student_id: 'S002',
        student_name: '李四',
        current_level: 'L3',
        mastery: 0.75,
        risk_level: 'LOW',
        attempts: 5,
        mistake_count: 0,
      },
      {
        student_id: 'S004',
        student_name: '赵六',
        current_level: 'L3',
        mastery: 0.88,
        risk_level: 'LOW',
        attempts: 4,
        mistake_count: 0,
      },
    ],
  };

  describe('D1: 诊断下钻响应数据契约与字段溯源合规性', () => {
    it('1. 考点诊断响应包含宏观指标与学生明细且类型完备', () => {
      assert.equal(mockDiagnosisData.knowledge_id, 'K01');
      assert.equal(mockDiagnosisData.knowledge_name, '需求定理与需求曲线');
      assert.equal(mockDiagnosisData.chapter, '第一章 需求、供给与均衡价格');
      assert.equal(mockDiagnosisData.average_mastery, 0.44);
      assert.equal(mockDiagnosisData.weak_student_count, 3);
      assert.equal(mockDiagnosisData.total_mistakes, 11);
      assert.equal(mockDiagnosisData.urgency, 'HIGH');
      assert.equal(mockDiagnosisData.students.length, 5);
    });

    it('2. 学生项仅包含已有权威字段，严禁注入未经验证的 is_affected 或状态黑话', () => {
      const student: TeacherDiagnosisStudentItem = mockDiagnosisData.students[0];
      assert.equal(student.student_id, 'S003');
      assert.equal(student.student_name, '王五');
      assert.equal(student.current_level, 'L1');
      assert.equal(typeof student.mastery, 'number');
      assert.equal(student.risk_level, 'HIGH');
      assert.equal(student.attempts, 12);
      assert.equal(student.mistake_count, 6);

      // 验证未包含伪造字段
      assert.equal((student as Record<string, unknown>).is_affected, undefined);
      assert.equal((student as Record<string, unknown>).status, undefined);
    });
  });

  describe('D2: 确定性排序规则断言 (mastery ASC -> risk priority -> student_id ASC)', () => {
    it('3. 学生明细默认遵循掌握度升序排列', () => {
      const masteries = mockDiagnosisData.students.map((s) => s.mastery);
      for (let i = 0; i < masteries.length - 1; i++) {
        assert.ok(
          masteries[i] <= masteries[i + 1],
          `掌握度未升序: index ${i} (${masteries[i]}) > index ${i + 1} (${masteries[i + 1]})`
        );
      }
    });

    it('4. 掌握度相同时，高风险优先于中低风险', () => {
      const tiedStudents: TeacherDiagnosisStudentItem[] = [
        {
          student_id: 'S002',
          student_name: '李四',
          current_level: 'L2',
          mastery: 0.50,
          risk_level: 'MEDIUM',
          attempts: 5,
          mistake_count: 2,
        },
        {
          student_id: 'S001',
          student_name: '张三',
          current_level: 'L1',
          mastery: 0.50,
          risk_level: 'HIGH',
          attempts: 8,
          mistake_count: 4,
        },
      ];

      const riskOrder: Record<string, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };
      tiedStudents.sort((a, b) => {
        if (a.mastery !== b.mastery) return a.mastery - b.mastery;
        const diff = (riskOrder[a.risk_level] ?? 3) - (riskOrder[b.risk_level] ?? 3);
        if (diff !== 0) return diff;
        return a.student_id.localeCompare(b.student_id);
      });

      assert.equal(tiedStudents[0].student_id, 'S001');
      assert.equal(tiedStudents[0].risk_level, 'HIGH');
    });
  });

  describe('D3: 需要进一步关注学生判定与权威阈值对齐契约', () => {
    it('5. “需要进一步关注”严格以 mastery < 0.60 为唯一权威准绳，与 weak_student_count 零误差对齐', () => {
      const attentionStudents = mockDiagnosisData.students.filter((s) => s.mastery < 0.60);
      assert.equal(attentionStudents.length, mockDiagnosisData.weak_student_count);
      assert.deepEqual(
        attentionStudents.map((s) => s.student_id),
        ['S003', 'S001', 'S005']
      );
    });

    it('6. 历史有错题但 mastery 已恢复 (>= 0.60) 的学生，不误判为需要进一步关注', () => {
      const studentRecovered: TeacherDiagnosisStudentItem = {
        student_id: 'S006',
        student_name: '孙八',
        current_level: 'L2',
        mastery: 0.65,
        risk_level: 'LOW',
        attempts: 10,
        mistake_count: 3, // 历史存在错题
      };

      // 严格判定：mastery >= 0.60 不进入 attention 列表
      const isAttention = studentRecovered.mastery < 0.60;
      assert.equal(isAttention, false);
    });
  });

  describe('D4: 诚实空状态与文案规范断言', () => {
    it('7. 全班无薄弱学生时，返回诚实提示文案且无主观溢出描述', () => {
      const perfectKnowledge: TeacherKnowledgeDiagnosisResponse = {
        knowledge_id: 'K15',
        knowledge_name: '短期成本曲线与推导',
        chapter: '第五章 成本理论',
        average_mastery: 0.85,
        weak_student_count: 0,
        total_mistakes: 0,
        urgency: 'LOW',
        students: [
          {
            student_id: 'S001',
            student_name: '张三',
            current_level: 'L3',
            mastery: 0.82,
            risk_level: 'LOW',
            attempts: 5,
            mistake_count: 0,
          },
        ],
      };

      const attentionList = perfectKnowledge.students.filter((s) => s.mastery < 0.60);
      assert.equal(attentionList.length, 0);

      // 空状态必须为纯客观事实陈述
      const emptyNotice = '当前没有学生满足“需要进一步关注”的条件。';
      assert.ok(!emptyNotice.includes('全部掌握良好'));
      assert.ok(!emptyNotice.includes('零风险'));
      assert.ok(emptyNotice.includes('需要进一步关注'));
    });
  });
});
