/**
 * quizModel.ts
 * 学海智导 (Xuehai Zhidao) V2 学生端微测验状态机与契约模型
 * 
 * 纯函数与状态模型设计：
 * 1. 严格管控题库脱敏、答题耗时统计 (time_spent_ms)、选项切换、提交防重
 * 2. 状态完整流转：idle -> loading -> answering -> submitting -> feedback -> (next -> answering) -> completed
 * 3. 统计指标纯函数精准测算：正确率、均题耗时、总耗时
 */

import type {
  QuizQuestionPublic,
  QuizSubmitRequest,
  QuizSubmitResponse,
  DecisionAuditEnvelope,
} from '../../types';

export type QuizStatus =
  | 'idle'
  | 'loading'
  | 'answering'
  | 'submitting'
  | 'feedback'
  | 'completed'
  | 'error';

export interface QuestionRecord {
  questionId: string;
  selectedOption: string;
  isCorrect: boolean;
  correctOption: string;
  explanation: string;
  timeSpentMs: number;
}

export interface QuizSessionState {
  status: QuizStatus;
  knowledgeId: string;
  knowledgeName: string;
  questions: QuizQuestionPublic[];
  currentIndex: number;
  selectedOption: string | null;
  questionStartTime: number | null;
  lastFeedback: QuizSubmitResponse | null;
  latestReplanning?: DecisionAuditEnvelope | null;
  records: QuestionRecord[];
  errorMessage: string | null;
}

export interface QuizSummary {
  totalQuestions: number;
  correctCount: number;
  wrongCount: number;
  accuracyPercent: number;
  totalTimeMs: number;
  averageTimeMs: number;
  averageTimeSeconds: number;
}

/**
 * 初始化测验会话，状态为 idle
 */
export function initQuizSession(
  knowledgeId: string,
  knowledgeName: string = ''
): QuizSessionState {
  return {
    status: 'idle',
    knowledgeId,
    knowledgeName,
    questions: [],
    currentIndex: 0,
    selectedOption: null,
    questionStartTime: null,
    lastFeedback: null,
    latestReplanning: null,
    records: [],
    errorMessage: null,
  };
}

/**
 * 进入题目加载状态
 */
export function startLoadingQuestions(state: QuizSessionState): QuizSessionState {
  return {
    ...state,
    status: 'loading',
    errorMessage: null,
  };
}

/**
 * 成功载入题目，初始化第 1 题
 */
export function setQuestionsLoaded(
  state: QuizSessionState,
  questions: QuizQuestionPublic[],
  startTime?: number
): QuizSessionState {
  if (!questions || questions.length === 0) {
    return {
      ...state,
      status: 'error',
      questions: [],
      errorMessage: '该知识点暂无可用微测验题目',
    };
  }

  const effectiveStartTime =
    startTime !== undefined
      ? startTime
      : typeof performance !== 'undefined'
      ? performance.now()
      : Date.now();

  return {
    ...state,
    status: 'answering',
    questions,
    currentIndex: 0,
    selectedOption: null,
    questionStartTime: effectiveStartTime,
    lastFeedback: null,
    records: [],
    errorMessage: null,
  };
}

/**
 * 题目加载失败
 */
export function setQuestionsLoadError(
  state: QuizSessionState,
  errorMsg: string
): QuizSessionState {
  return {
    ...state,
    status: 'error',
    errorMessage: errorMsg,
  };
}

/**
 * 选中作答选项
 */
export function selectOption(
  state: QuizSessionState,
  optionKey: string
): QuizSessionState {
  if (state.status !== 'answering') {
    return state;
  }
  return {
    ...state,
    selectedOption: optionKey,
  };
}

/**
 * 是否允许提交当前作答
 */
export function canSubmitAnswer(state: QuizSessionState): boolean {
  return state.status === 'answering' && !!state.selectedOption;
}

/**
 * 启动提交中状态（防重点击保护）
 */
export function startSubmittingAnswer(state: QuizSessionState): QuizSessionState {
  if (state.status !== 'answering' || !state.selectedOption) {
    return state;
  }
  return {
    ...state,
    status: 'submitting',
    errorMessage: null,
  };
}

/**
 * 组装符合 API 契约的提交载荷
 */
export function buildSubmitPayload(
  state: QuizSessionState,
  studentId: string,
  nowTime?: number
): QuizSubmitRequest {
  const currentQ = state.questions[state.currentIndex];
  if (!currentQ || !state.selectedOption) {
    throw new Error('当前未处于可提交题目的有效状态');
  }

  const effectiveNow =
    nowTime !== undefined
      ? nowTime
      : typeof performance !== 'undefined'
      ? performance.now()
      : Date.now();

  const startTime = state.questionStartTime ?? effectiveNow;
  const timeSpentMs = Math.max(0, Math.round(effectiveNow - startTime));

  return {
    student_id: studentId,
    question_id: currentQ.question_id,
    selected_option: state.selectedOption,
    time_spent_ms: timeSpentMs,
  };
}

/**
 * 服务端判题成功，流转至 feedback 状态并归档记录
 */
export function setSubmitSuccess(
  state: QuizSessionState,
  response: QuizSubmitResponse,
  timeSpentMs: number
): QuizSessionState {
  const currentQ = state.questions[state.currentIndex];
  const newRecord: QuestionRecord = {
    questionId: currentQ ? currentQ.question_id : response.question_id,
    selectedOption: state.selectedOption || '',
    isCorrect: response.is_correct,
    correctOption: response.correct_option,
    explanation: response.explanation,
    timeSpentMs,
  };

  return {
    ...state,
    status: 'feedback',
    lastFeedback: response,
    latestReplanning: response.replanning ?? state.latestReplanning ?? null,
    records: [...state.records, newRecord],
    errorMessage: null,
  };
}

/**
 * 判题请求异常，回退至 answering 允许重试
 */
export function setSubmitError(
  state: QuizSessionState,
  errorMsg: string
): QuizSessionState {
  return {
    ...state,
    status: 'answering',
    errorMessage: errorMsg,
  };
}

/**
 * 切换至下一题或完成测验
 */
export function goToNextQuestion(
  state: QuizSessionState,
  nextStartTime?: number
): QuizSessionState {
  if (state.currentIndex + 1 < state.questions.length) {
    const effectiveStartTime =
      nextStartTime !== undefined
        ? nextStartTime
        : typeof performance !== 'undefined'
        ? performance.now()
        : Date.now();

    return {
      ...state,
      status: 'answering',
      currentIndex: state.currentIndex + 1,
      selectedOption: null,
      lastFeedback: null,
      questionStartTime: effectiveStartTime,
      errorMessage: null,
    };
  }

  return {
    ...state,
    status: 'completed',
    lastFeedback: null,
    errorMessage: null,
  };
}

/**
 * 计算微测验结算指标
 */
export function calculateQuizSummary(records: QuestionRecord[]): QuizSummary {
  const totalQuestions = records.length;
  const correctCount = records.filter((r) => r.isCorrect).length;
  const wrongCount = totalQuestions - correctCount;
  const accuracyPercent =
    totalQuestions > 0 ? Math.round((correctCount / totalQuestions) * 100) : 0;
  const totalTimeMs = records.reduce((sum, r) => sum + r.timeSpentMs, 0);
  const averageTimeMs =
    totalQuestions > 0 ? Math.round(totalTimeMs / totalQuestions) : 0;
  const averageTimeSeconds = parseFloat((averageTimeMs / 1000).toFixed(1));

  return {
    totalQuestions,
    correctCount,
    wrongCount,
    accuracyPercent,
    totalTimeMs,
    averageTimeMs,
    averageTimeSeconds,
  };
}

/**
 * 重置测验会话回退至 idle 初始态
 */
export function resetQuizSession(state: QuizSessionState): QuizSessionState {
  return initQuizSession(state.knowledgeId, state.knowledgeName);
}

/**
 * 耗时格式化友好展示
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * 认知掌握度数值格式化为规范百分比字符串 (如 0.4566 -> 45.66%)
 */
export function formatMasteryPercentage(
  val: string | number | undefined | null
): string {
  if (val === undefined || val === null || val === '') return '0.00%';
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return '0.00%';
  if (num <= 1.0) {
    return `${(num * 100).toFixed(2)}%`;
  }
  return `${num.toFixed(2)}%`;
}

/**
 * 从重规划决策结果中提取本次真正解锁的下游知识点列表
 */
export function getUnlockedDownstreamNodes(
  replanning?: DecisionAuditEnvelope | null,
  currentKnowledgeId?: string
): string[] {
  if (!replanning || replanning.canonical_payload.action !== 'UNLOCK_DOWNSTREAM') {
    return [];
  }
  const affected = replanning.canonical_payload.affected_nodes || [];
  const curr = currentKnowledgeId || replanning.canonical_payload.knowledge_id;
  return affected.filter((id) => id !== curr);
}

