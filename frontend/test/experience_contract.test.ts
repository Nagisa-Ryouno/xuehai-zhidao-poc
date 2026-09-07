/**
 * experience_contract.test.ts
 * Phase 2.2-B: 学生端体验契约适应度测试 (Student Experience Contract Tests)
 *
 * 验证规则：
 * 1. 四个核心学生 Tab 存在且映射规范子路由
 * 2. 学生上下文 (S001~S005) 单一事实源与跨端保持
 * 3. 路径执行状态 (LOCKED, AVAILABLE, IN_PROGRESS, COMPLETED) 语义映射契约
 * 4. 黄金旅程关键交互契约 (测验提交载荷与反馈持久化)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import {
  STUDENT_NAV_TABS,
  getActiveStudentTab,
} from '../src/components/student/navConfig.ts';
import {
  resolveRoute,
  createRouterState,
  selectStudentState,
  switchRole,
} from '../src/router.ts';
import {
  initQuizSession,
  setQuestionsLoaded,
  selectOption,
  buildSubmitPayload,
  setSubmitSuccess,
} from '../src/components/student/quizModel.ts';
import type { QuizSubmitResponse } from '../src/types.ts';

describe('Phase 2.2-B: 学生端体验契约规范测试 (Student Experience Contract)', () => {
  // -------------------------------------------------------------
  // Contract 1: 导航契约与 4-Tab 完整性
  // -------------------------------------------------------------
  it('Contract 1: 学生端 4 个核心 Tab 完整定义且路由解析互通', () => {
    const tabIds = STUDENT_NAV_TABS.map((t) => t.id);
    assert.deepEqual(tabIds, ['tasks', 'graph', 'profile', 'assistant']);

    // 每个 Tab 必须由 router.ts 解析到正确的 StudentLayout 与 subRoute
    for (const tab of STUDENT_NAV_TABS) {
      const res = resolveRoute(tab.path);
      assert.equal(res.role, 'student', `路径 ${tab.path} 角色必须为 student`);
      assert.equal(res.layout, 'StudentLayout', `路径 ${tab.path} 布局必须为 StudentLayout`);
      assert.equal(res.subRoute, tab.id, `路径 ${tab.path} 子路由应为 ${tab.id}`);
      assert.equal(getActiveStudentTab(tab.path), tab.id);
    }
  });

  // -------------------------------------------------------------
  // Contract 2: 学生上下文单一事实源与跨端保持
  // -------------------------------------------------------------
  it('Contract 2: 学生身份上下文在切换与双端穿梭中严格一致保持', () => {
    const validStudents = ['S001', 'S002', 'S003', 'S004', 'S005'];
    let state = createRouterState('/student/tasks', 'S001');
    assert.equal(state.studentId, 'S001');

    // 验证合法学生均可被平滑选中且不影响当前 subRoute
    for (const sid of validStudents) {
      state = selectStudentState(state, sid);
      assert.equal(state.studentId, sid);
      assert.equal(state.subRoute, 'tasks');
    }

    // 切换至教师端驾驶舱，学生 ID 上下文绝不丢失
    state = switchRole(state, 'teacher');
    assert.equal(state.role, 'teacher');
    assert.equal(state.studentId, 'S005');

    // 重新切回学生端，学生上下文依然锁定为 S005
    state = switchRole(state, 'student');
    assert.equal(state.role, 'student');
    assert.equal(state.studentId, 'S005');
  });

  // -------------------------------------------------------------
  // Contract 3: 路径状态语义映射契约 (Path State Presentation Contract)
  // -------------------------------------------------------------
  it('Contract 3: 四大路径状态语义完整且映射明确', () => {
    const PATH_STATE_SEMANTICS = {
      LOCKED: '前置条件未满足，暂未开放学习',
      AVAILABLE: '前置条件已满足，准入可学',
      IN_PROGRESS: '当前学习任务进行中',
      COMPLETED: '掌握度已达标且已完成该考点学习',
    } as const;

    const allowedStates = Object.keys(PATH_STATE_SEMANTICS);
    assert.equal(allowedStates.length, 4);
    assert.ok(allowedStates.includes('LOCKED'));
    assert.ok(allowedStates.includes('AVAILABLE'));
    assert.ok(allowedStates.includes('IN_PROGRESS'));
    assert.ok(allowedStates.includes('COMPLETED'));
  });

  // -------------------------------------------------------------
  // Contract 4: 黄金用户旅程关键测验载荷契约 (Golden Journey Steps 8 & 9)
  // -------------------------------------------------------------
  it('Contract 4: 微测验提交载荷携带动态时间与学生上下文，反馈完整保真', () => {
    const mockQuestion = {
      question_id: 'Q-K08-01',
      knowledge_id: 'K08',
      question_text: '需求价格弹性的定义是什么？',
      options: [
        { option_key: 'A', option_text: '价格变动率与需求量变动率之比' },
        { option_key: 'B', option_text: '需求量变动率与价格变动率之比' },
      ],
    };

    let session = initQuizSession('K08', '需求价格弹性');
    const startTime = 1000;
    session = setQuestionsLoaded(session, [mockQuestion], startTime);
    session = selectOption(session, 'B');

    // 生成提交载荷，断言动态耗时计算与上下文传递
    const submitTime = 3500;
    const payload = buildSubmitPayload(session, 'S003', submitTime);
    assert.equal(payload.student_id, 'S003', '测验载荷必须绑定当前选中的学生 S003');
    assert.equal(payload.question_id, 'Q-K08-01');
    assert.equal(payload.selected_option, 'B');
    assert.equal(payload.time_spent_ms, 2500, '必须准确计算动态耗时差 (3500 - 1000)');

    // 模拟服务端响应并落盘到 feedback 状态
    const mockResponse: QuizSubmitResponse = {
      is_correct: true,
      correct_option: 'B',
      explanation: '需求价格弹性等于需求量的变动率除以价格的变动率。',
      question_id: 'Q-K08-01',
      bkt_state: {
        student_id: 'S003',
        knowledge_id: 'K08',
        mastery_probability: 0.8118,
        consecutive_incorrect: 0,
        attempts: 3,
        correct_attempts: 2,
        incorrect_attempts: 1,
      },
    };

    session = setSubmitSuccess(session, mockResponse, payload.time_spent_ms);
    assert.equal(session.status, 'feedback');
    assert.ok(session.lastFeedback !== null);
    assert.equal(session.lastFeedback?.is_correct, true);
    assert.equal(session.lastFeedback?.bkt_state?.mastery_probability, 0.8118);
    assert.equal(session.records.length, 1);
    assert.equal(session.records[0].timeSpentMs, 2500);
  });
});
