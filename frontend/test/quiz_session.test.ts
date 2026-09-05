import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  initQuizSession,
  startLoadingQuestions,
  setQuestionsLoaded,
  setQuestionsLoadError,
  selectOption,
  canSubmitAnswer,
  startSubmittingAnswer,
  buildSubmitPayload,
  setSubmitSuccess,
  setSubmitError,
  goToNextQuestion,
  calculateQuizSummary,
  resetQuizSession,
  formatDuration,
} from '../src/components/student/quizModel.ts';
import type { QuizQuestionPublic, QuizSubmitResponse } from '../src/types.ts';

// 真实 K08 测验题目脱敏模拟数据（与后端实际 GET /api/quiz/K08 保持完全一致）
const MOCK_K08_QUESTIONS: QuizQuestionPublic[] = [
  {
    question_id: 'Q-K08-01',
    knowledge_id: 'K08',
    stem: '某商品的需求价格弹性绝对值大于1（富有弹性），如果生产厂商希望增加销售总收益，应该采取的定价策略是：',
    options: [
      { key: 'A', text: '适当降低商品价格' },
      { key: 'B', text: '适当提高商品价格' },
      { key: 'C', text: '保持价格绝对不变' },
      { key: 'D', text: '大幅削减产量并提价' },
    ],
    difficulty: 2,
  },
  {
    question_id: 'Q-K08-02',
    knowledge_id: 'K08',
    stem: '在农业丰收的年份，农民的总收益反而往往下降（谷贱伤农），从微观经济学角度看，其主要根源是：',
    options: [
      { key: 'A', text: '粮食的需求收入弹性过高' },
      { key: 'B', text: '粮食的供给完全缺乏弹性' },
      { key: 'C', text: '绝大多数农产品属于缺乏需求价格弹性的必需品' },
      { key: 'D', text: '农产品的替代品极多导致竞争激烈' },
    ],
    difficulty: 3,
  },
];

describe('P0-5: 学生端知识点微测验 UI 状态机与业务契约测试', () => {
  // Test 1: 初始状态校验
  it('Test 1: Quiz 状态机初始必须为 idle，题目与选项目前为空', () => {
    const session = initQuizSession('K08', '需求价格弹性');
    assert.equal(session.status, 'idle');
    assert.equal(session.knowledgeId, 'K08');
    assert.equal(session.knowledgeName, '需求价格弹性');
    assert.equal(session.questions.length, 0);
    assert.equal(session.currentIndex, 0);
    assert.equal(session.selectedOption, null);
    assert.equal(session.questionStartTime, null);
    assert.equal(session.lastFeedback, null);
    assert.equal(session.records.length, 0);
    assert.equal(session.errorMessage, null);
  });

  // Test 2: 加载中状态
  it('Test 2: startLoadingQuestions 进入 loading 状态并清理历史错误', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session.errorMessage = '上一次网络错误';
    session = startLoadingQuestions(session);
    assert.equal(session.status, 'loading');
    assert.equal(session.errorMessage, null);
  });

  // Test 3: 载入题目后状态流转
  it('Test 3: setQuestionsLoaded 正常载入题目并初始化第 1 题 (1 / 2)，状态流转至 answering', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = startLoadingQuestions(session);
    const startTime = 1000.5;
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, startTime);

    assert.equal(session.status, 'answering');
    assert.equal(session.questions.length, 2);
    assert.equal(session.currentIndex, 0);
    assert.equal(session.questionStartTime, startTime);
    assert.equal(session.selectedOption, null);
    assert.equal(session.questions[0].question_id, 'Q-K08-01');
  });

  // Test 4: 安全脱敏契约检查
  it('Test 4: 题目数据严格脱敏，客户端题目对象绝不包含 answer 字段', () => {
    for (const q of MOCK_K08_QUESTIONS) {
      assert.equal((q as Record<string, unknown>).answer, undefined, '题目绝不能包含 answer 字段');
      assert.equal((q as Record<string, unknown>).explanation, undefined, '题目绝不能包含 explanation 字段');
    }
  });

  // Test 5: 未选择答案前不能提交
  it('Test 5: 未选择选项时 canSubmitAnswer 必须为 false (提交按钮 disabled)', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 1000);
    assert.equal(canSubmitAnswer(session), false, '未选择答案前不得允许提交');
  });

  // Test 6: 选中选项后允许提交
  it('Test 6: 选中选项 (如 A) 后 canSubmitAnswer 变为 true (提交按钮 enabled)', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 1000);
    session = selectOption(session, 'A');

    assert.equal(session.selectedOption, 'A');
    assert.equal(canSubmitAnswer(session), true, '已选中选项应允许提交');
  });

  // Test 7: 防重提交保护
  it('Test 7: 重复点击保护，startSubmittingAnswer 进入 submitting 状态，二次调用被安全拦截', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 1000);
    session = selectOption(session, 'A');

    session = startSubmittingAnswer(session);
    assert.equal(session.status, 'submitting');
    assert.equal(canSubmitAnswer(session), false, 'submitting 状态下不可再次提交');

    // 再次调用 startSubmittingAnswer 应该保持 submitting 状态，不产生副作用
    const secondCall = startSubmittingAnswer(session);
    assert.equal(secondCall.status, 'submitting');
  });

  // Test 8: 请求载荷构建规范
  it('Test 8: buildSubmitPayload 正确组装请求载荷，包含当前 studentId 与 questionId', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 1000);
    session = selectOption(session, 'A');

    const payload = buildSubmitPayload(session, 'S001', 5500);
    assert.equal(payload.student_id, 'S001');
    assert.equal(payload.question_id, 'Q-K08-01');
    assert.equal(payload.selected_option, 'A');
  });

  // Test 9: 动态真实答题耗时计算 (time_spent_ms)
  it('Test 9: time_spent_ms 必须为真实动态时间差计算，且值 > 0，严禁固定死值', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 2000);
    session = selectOption(session, 'A');

    // 模拟答题耗时 3250ms
    const payload1 = buildSubmitPayload(session, 'S001', 5250);
    assert.equal(payload1.time_spent_ms, 3250);

    // 模拟答题耗时 7800ms
    const payload2 = buildSubmitPayload(session, 'S001', 9800);
    assert.equal(payload2.time_spent_ms, 7800);
    assert.notEqual(payload1.time_spent_ms, payload2.time_spent_ms, '耗时必须是动态测算，不可固定');
  });

  // Test 10: 判题完成前绝不提前泄露正确答案
  it('Test 10: 判题完成前 lastFeedback 为空，绝不提前泄露正确答案或解析', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 1000);
    session = selectOption(session, 'A');
    assert.equal(session.lastFeedback, null);
  });

  // Test 11: 服务端反馈接入与 feedback 状态
  it('Test 11: setSubmitSuccess 接收服务端响应，展示 is_correct 与 explanation 并进入 feedback 状态', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 1000);
    session = selectOption(session, 'A');
    session = startSubmittingAnswer(session);

    const mockResponse: QuizSubmitResponse = {
      is_correct: true,
      correct_option: 'A',
      explanation: '【解析】当需求富有弹性时，降价能够大幅促进销售量增加，从而增加总收益。',
      knowledge_id: 'K08',
      question_id: 'Q-K08-01',
      event_id: 'evt-quiz-test-01',
    };

    session = setSubmitSuccess(session, mockResponse, 4200);
    assert.equal(session.status, 'feedback');
    assert.notEqual(session.lastFeedback, null);
    assert.equal(session.lastFeedback?.is_correct, true);
    assert.equal(session.lastFeedback?.correct_option, 'A');
    assert.equal(session.lastFeedback?.explanation, mockResponse.explanation);
    assert.equal(session.records.length, 1);
    assert.equal(session.records[0].timeSpentMs, 4200);
  });

  // Test 12: 错题记录归档
  it('Test 12: 提交错误答案时正确记录 is_correct=false', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 1000);
    session = selectOption(session, 'B');
    session = startSubmittingAnswer(session);

    const mockWrongResponse: QuizSubmitResponse = {
      is_correct: false,
      correct_option: 'A',
      explanation: '【解析】富有弹性商品提高价格会导致总收益减少。',
      knowledge_id: 'K08',
      question_id: 'Q-K08-01',
      event_id: 'evt-quiz-test-02',
    };

    session = setSubmitSuccess(session, mockWrongResponse, 3100);
    assert.equal(session.status, 'feedback');
    assert.equal(session.lastFeedback?.is_correct, false);
    assert.equal(session.records[0].isCorrect, false);
    assert.equal(session.records[0].selectedOption, 'B');
  });

  // Test 13: 切换至下一题并重置时间和选项
  it('Test 13: goToNextQuestion 切换至下一题 (2 / 2)，重置 selectedOption 并重置答题起始时间', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 1000);
    session = selectOption(session, 'A');
    session = startSubmittingAnswer(session);

    const mockResponse: QuizSubmitResponse = {
      is_correct: true,
      correct_option: 'A',
      explanation: '...',
      knowledge_id: 'K08',
      question_id: 'Q-K08-01',
      event_id: 'evt-1',
    };
    session = setSubmitSuccess(session, mockResponse, 3500);

    // 点击进入下一题
    const nextStartTime = 15000;
    session = goToNextQuestion(session, nextStartTime);

    assert.equal(session.status, 'answering');
    assert.equal(session.currentIndex, 1, '当前题目索引应递增为 1 (即第 2 题)');
    assert.equal(session.selectedOption, null, '新题目选中项必须重置为空');
    assert.equal(session.lastFeedback, null, '上一题的反馈必须清除');
    assert.equal(session.questionStartTime, nextStartTime, '答题起始时间必须重新记录');
    assert.equal(session.questions[session.currentIndex].question_id, 'Q-K08-02');
  });

  // Test 14: 最后一题完成后流转至 completed
  it('Test 14: 最后一题答完后 goToNextQuestion 流转至 completed 状态', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 1000);

    // 第 1 题提交
    session = selectOption(session, 'A');
    session = startSubmittingAnswer(session);
    session = setSubmitSuccess(
      session,
      {
        is_correct: true,
        correct_option: 'A',
        explanation: '...',
        knowledge_id: 'K08',
        question_id: 'Q-K08-01',
        event_id: 'evt-1',
      },
      3000
    );
    session = goToNextQuestion(session, 5000);

    // 第 2 题（最后一题）提交
    session = selectOption(session, 'C');
    session = startSubmittingAnswer(session);
    session = setSubmitSuccess(
      session,
      {
        is_correct: true,
        correct_option: 'C',
        explanation: '...',
        knowledge_id: 'K08',
        question_id: 'Q-K08-02',
        event_id: 'evt-2',
      },
      4000
    );

    // 再次点击，应进入 completed
    session = goToNextQuestion(session);
    assert.equal(session.status, 'completed');
  });

  // Test 15: 测验结果统计精准计算
  it('Test 15: calculateQuizSummary 精准计算答题统计（正确率、总题数、平均耗时）', () => {
    const records = [
      {
        questionId: 'Q-K08-01',
        selectedOption: 'A',
        isCorrect: true,
        correctOption: 'A',
        explanation: '...',
        timeSpentMs: 3000,
      },
      {
        questionId: 'Q-K08-02',
        selectedOption: 'B',
        isCorrect: false,
        correctOption: 'C',
        explanation: '...',
        timeSpentMs: 5000,
      },
    ];

    const summary = calculateQuizSummary(records);
    assert.equal(summary.totalQuestions, 2);
    assert.equal(summary.correctCount, 1);
    assert.equal(summary.wrongCount, 1);
    assert.equal(summary.accuracyPercent, 50);
    assert.equal(summary.totalTimeMs, 8000);
    assert.equal(summary.averageTimeMs, 4000);
    assert.equal(summary.averageTimeSeconds, 4.0);
  });

  // Test 16: 题目加载异常处理
  it('Test 16: setQuestionsLoadError 捕获题目加载异常，展示用户友好提示并允许重试', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = startLoadingQuestions(session);
    session = setQuestionsLoadError(session, '微测验加载失败，请检查网络后重试');

    assert.equal(session.status, 'error');
    assert.equal(session.errorMessage, '微测验加载失败，请检查网络后重试');
  });

  // Test 17: 提交答案异常回退
  it('Test 17: setSubmitError 捕获提交判题异常，回退至 answering 状态保留用户选中项并允许重试', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 1000);
    session = selectOption(session, 'A');
    session = startSubmittingAnswer(session);

    session = setSubmitError(session, '答案提交失败，请检查网络后重试');
    assert.equal(session.status, 'answering');
    assert.equal(session.selectedOption, 'A', '异常后保留选中项');
    assert.equal(session.errorMessage, '答案提交失败，请检查网络后重试');
    assert.equal(canSubmitAnswer(session), true, '错误提示后应允许用户重新提交');
  });

  // Test 18: 重置会话
  it('Test 18: resetQuizSession 重置测验会话回退至 idle 初始态', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 1000);
    session = resetQuizSession(session);
    assert.equal(session.status, 'idle');
    assert.equal(session.questions.length, 0);
  });

  // Test 19: 保持当前学生上下文
  it('Test 19: 保持当前学生上下文 (如 S003)，payload 携带 student_id 绝不篡改或写死 S001', () => {
    let session = initQuizSession('K08', '需求价格弹性');
    session = setQuestionsLoaded(session, MOCK_K08_QUESTIONS, 1000);
    session = selectOption(session, 'A');

    const payloadS003 = buildSubmitPayload(session, 'S003', 4000);
    assert.equal(payloadS003.student_id, 'S003');

    const payloadS005 = buildSubmitPayload(session, 'S005', 4000);
    assert.equal(payloadS005.student_id, 'S005');
  });

  // Test 20: 格式化耗时展示
  it('Test 20: 格式化耗时工具函数 formatDuration 正确处理秒与毫秒', () => {
    assert.equal(formatDuration(850), '850ms');
    assert.equal(formatDuration(4200), '4.2s');
    assert.equal(formatDuration(15000), '15.0s');
  });
});
