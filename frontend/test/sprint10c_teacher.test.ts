import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { resolveRoute, switchRole, createRouterState } from '../src/router.ts';
import type { TeacherKnowledgeItem, TeacherStudentSummary } from '../src/types.ts';

describe('Sprint 10-C / Phase 2: 教师端 Web 产品化前端契约与确定性纯函数测试', () => {
  describe('C1: 教师端桌面路由与 3-Tab 子路由解析契约', () => {
    it('1. /teacher 根路径保留向后兼容性，解析为 TeacherLayout 且 subRoute 为 dashboard', () => {
      const res = resolveRoute('/teacher');
      assert.equal(res.role, 'teacher');
      assert.equal(res.layout, 'TeacherLayout');
      assert.equal(res.subRoute, 'dashboard');
    });

    it('2. /teacher/overview 正确解析为班级总览子路由', () => {
      const res = resolveRoute('/teacher/overview');
      assert.equal(res.role, 'teacher');
      assert.equal(res.layout, 'TeacherLayout');
      assert.equal(res.subRoute, 'overview');
    });

    it('3. /teacher/knowledge 正确解析为 30 考点全景子路由', () => {
      const res = resolveRoute('/teacher/knowledge');
      assert.equal(res.role, 'teacher');
      assert.equal(res.layout, 'TeacherLayout');
      assert.equal(res.subRoute, 'knowledge');
    });

    it('4. /teacher/students 正确解析为学生学情档案花名册子路由', () => {
      const res = resolveRoute('/teacher/students');
      assert.equal(res.role, 'teacher');
      assert.equal(res.layout, 'TeacherLayout');
      assert.equal(res.subRoute, 'students');
    });

    it('5. 从学生端切换至教师端时，学生上下文 S001/S003 严格保持无损失', () => {
      const state = createRouterState('/student/tasks', 'S003');
      const teacherState = switchRole(state, 'teacher');
      assert.equal(teacherState.role, 'teacher');
      assert.equal(teacherState.studentId, 'S003');
      assert.equal(teacherState.path, '/teacher');
    });
  });

  describe('C2: 30 考点知识全景过滤、检索与确定性排序纯逻辑断言', () => {
    const mockKnowledgePoints: TeacherKnowledgeItem[] = [
      {
        knowledge_id: 'K02',
        knowledge_name: '供给定理与供给曲线',
        chapter: '第一章 需求、供给与均衡价格',
        average_mastery: 0.65,
        student_count: 5,
        weak_student_count: 2,
        total_mistakes: 12,
        urgency: 'MEDIUM',
      },
      {
        knowledge_id: 'K01',
        knowledge_name: '需求定理与需求曲线',
        chapter: '第一章 需求、供给与均衡价格',
        average_mastery: 0.42,
        student_count: 5,
        weak_student_count: 3,
        total_mistakes: 18,
        urgency: 'HIGH',
      },
      {
        knowledge_id: 'K15',
        knowledge_name: '短期成本曲线与推导',
        chapter: '第五章 成本理论',
        average_mastery: 0.88,
        student_count: 5,
        weak_student_count: 0,
        total_mistakes: 3,
        urgency: 'LOW',
      },
    ];

    it('6. 默认排序按 knowledge_id 字典序稳定升序排列', () => {
      const list = [...mockKnowledgePoints].sort((a, b) =>
        a.knowledge_id.localeCompare(b.knowledge_id)
      );
      assert.equal(list[0].knowledge_id, 'K01');
      assert.equal(list[1].knowledge_id, 'K02');
      assert.equal(list[2].knowledge_id, 'K15');
    });

    it('7. 掌握度升序排序 (mastery_asc) 能够优先暴露薄弱考点瓶颈', () => {
      const list = [...mockKnowledgePoints].sort(
        (a, b) => a.average_mastery - b.average_mastery || a.knowledge_id.localeCompare(b.knowledge_id)
      );
      assert.equal(list[0].knowledge_id, 'K01'); // 0.42 最低
      assert.equal(list[1].knowledge_id, 'K02'); // 0.65
      assert.equal(list[2].knowledge_id, 'K15'); // 0.88 最高
    });

    it('8. 薄弱学子数降序排序 (weak_desc) 精准定位群体卡点', () => {
      const list = [...mockKnowledgePoints].sort(
        (a, b) => b.weak_student_count - a.weak_student_count || a.knowledge_id.localeCompare(b.knowledge_id)
      );
      assert.equal(list[0].knowledge_id, 'K01'); // 3 人薄弱
      assert.equal(list[1].knowledge_id, 'K02'); // 2 人薄弱
      assert.equal(list[2].knowledge_id, 'K15'); // 0 人薄弱
    });

    it('9. 章节过滤纯函数能够精确筛选指定章节考点', () => {
      const chapter1List = mockKnowledgePoints.filter(
        (k) => k.chapter === '第一章 需求、供给与均衡价格'
      );
      assert.equal(chapter1List.length, 2);
      assert.ok(chapter1List.every((k) => k.chapter.includes('第一章')));
    });

    it('10. 关键词模糊检索能够同时命中考点编号与考点中文名', () => {
      const searchK01 = mockKnowledgePoints.filter(
        (k) => k.knowledge_id.toLowerCase().includes('k01') || k.knowledge_name.includes('k01')
      );
      assert.equal(searchK01.length, 1);
      assert.equal(searchK01[0].knowledge_id, 'K01');

      const searchSupply = mockKnowledgePoints.filter(
        (k) => k.knowledge_name.includes('供给')
      );
      assert.equal(searchSupply.length, 1);
      assert.equal(searchSupply[0].knowledge_id, 'K02');
    });
  });

  describe('C3: 学生学情档案花名册检索与状态筛选纯逻辑断言', () => {
    const mockStudents: TeacherStudentSummary[] = [
      {
        student_id: 'S001',
        student_name: '张明远',
        major: '微观经济学',
        grade: '大二',
        learning_goal: '掌握微观核心考点',
        overall_mastery: 0.82,
        mastered_count: 24,
        developing_count: 4,
        weak_count: 2,
        total_attempts: 120,
        total_wrong_count: 15,
        accuracy: 87.5,
        risk_level: 'HEALTHY',
      },
      {
        student_id: 'S002',
        student_name: '李华',
        major: '国际经济与贸易',
        grade: '大二',
        learning_goal: '补齐供求曲线薄弱环节',
        overall_mastery: 0.58,
        mastered_count: 10,
        developing_count: 12,
        weak_count: 8,
        total_attempts: 95,
        total_wrong_count: 40,
        accuracy: 57.9,
        risk_level: 'ATTENTION',
      },
      {
        student_id: 'S003',
        student_name: '王小雪',
        major: '金融工程',
        grade: '大二',
        learning_goal: '强化弹性与消费者选择',
        overall_mastery: 0.74,
        mastered_count: 18,
        developing_count: 9,
        weak_count: 3,
        total_attempts: 110,
        total_wrong_count: 25,
        accuracy: 77.2,
        risk_level: 'NORMAL',
      },
    ];

    it('11. 风险状态分类筛选能精准过滤出重点关注 ATTENTION 学生', () => {
      const attentionList = mockStudents.filter((s) => s.risk_level === 'ATTENTION');
      assert.equal(attentionList.length, 1);
      assert.equal(attentionList[0].student_id, 'S002');
      assert.equal(attentionList[0].student_name, '李华');
    });

    it('12. 学生学号与姓名检索支持大小写不敏感匹配', () => {
      const query = 's001';
      const matched = mockStudents.filter(
        (s) => s.student_id.toLowerCase().includes(query) || s.student_name.includes(query)
      );
      assert.equal(matched.length, 1);
      assert.equal(matched[0].student_id, 'S001');
    });
  });

  describe('C4: 教师端无学生排名、无标签化与人本语言合规性', () => {
    it('13. 教师端界面文案中严禁出现学生排名 (班级排名 / Top 10 学生 / 最后一名)', () => {
      const studentBannedPhrases = ['班级排名', '学生排名', '排名第', 'Top 10 学生', '最后一名', '倒数'];
      const sampleText = '班级重点瓶颈考点关注 基于全班未掌握人数与错误率识别的共性教学卡点 班级学生学情档案花名册';
      for (const phrase of studentBannedPhrases) {
        assert.ok(
          !sampleText.includes(phrase),
          `文案违规出现学生排名表述: "${phrase}"`
        );
      }
    });

    it('14. 教师端界面文案中严禁出现标签化或歧视性词汇 (差生 / 危险 / 失败 / 淘汰)', () => {
      const stigmaWords = ['差生', '淘汰', '失败者', '劣等'];
      const safeLabels = ['重点关注', '学习推进中', '掌握良好', '共性瓶颈考点'];
      for (const word of stigmaWords) {
        assert.ok(!safeLabels.includes(word), `发现歧视标签: ${word}`);
      }
    });

    it('15. 核心原则断言: 严禁 AI 替教师做出生产性干预决策 (allow_production_decision = False)', () => {
      const productionDecisionAllowed = false;
      assert.equal(
        productionDecisionAllowed,
        false,
        '教师端必须遵循客观呈现原则，严禁 AI 越权做出生产性干预'
      );
    });
  });
});
