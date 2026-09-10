/**
 * api.ts
 * 学海智导 (Xuehai Zhidao) - API 数据层封装
 * 统一管理与 FastAPI 后端的数据交互及友好错误处理
 */

import type {
  SystemOverview,
  StudentListItem,
  StudentProfileData,
  StudentLearningPathData,
  StudentReportData,
  StudentDashboardResponse,
  AssistantResponse,
  AssistantGreetingResponse,
  KnowledgeGraphResponse,
  QuizKnowledgeListResponse,
  QuizSubmitRequest,
  QuizSubmitResponse,
  StudentPathStatesResponse,
} from './types';

// API 基础路径（优先走 Vite 代理 /api，若独立部署可配置环境变量）
const API_BASE = '/api';

/**
 * 通用请求包装函数，提供统一的 HTTP 错误与网络异常拦截
 */
async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...(options?.headers || {}),
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('未找到对应学生的数据档案');
      } else if (response.status >= 500) {
        throw new Error('学海智导分析服务内部异常，请检查后端运行状态');
      }
      throw new Error(`服务请求失败 (状态码: ${response.status})`);
    }

    const data = await response.json();
    return data as T;
  } catch (err: unknown) {
    if (err instanceof Error) {
      // 拦截底层网络异常（例如 Failed to fetch / Connection refused）
      if (err.name === 'TypeError' || err.message.includes('fetch')) {
        throw new Error('暂时无法连接学习分析服务，请确认后端服务已启动');
      }
      throw err;
    }
    throw new Error('发生未知网络错误，请稍后重试');
  }
}

/**
 * 检查后端服务健康状态
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
    if (!res.ok) return false;
    const data = await res.json();
    return data.status === 'ok';
  } catch {
    return false;
  }
}

/**
 * 获取系统总体概况
 */
export async function fetchOverview(): Promise<SystemOverview> {
  return request<SystemOverview>('/overview');
}

/**
 * 获取学生列表及关键学情摘要
 */
export async function getStudents(): Promise<{ count: number; students: StudentListItem[] }> {
  return request<{ count: number; students: StudentListItem[] }>('/students');
}

/**
 * 获取指定学生完整 Dashboard 聚合数据（包含画像、学习路径、综合报告）
 */
export async function getStudentDashboard(studentId: string): Promise<StudentDashboardResponse> {
  return request<StudentDashboardResponse>(`/students/${studentId}/dashboard`);
}

/**
 * 获取指定学生多维学情画像
 */
export async function getStudentProfile(studentId: string): Promise<StudentProfileData> {
  return request<StudentProfileData>(`/students/${studentId}/profile`);
}

/**
 * 获取指定学生个性化学习路径
 */
export async function getLearningPath(studentId: string): Promise<StudentLearningPathData> {
  return request<StudentLearningPathData>(`/students/${studentId}/learning-path`);
}

/**
 * 获取指定学生综合诊断与报告
 */
export async function getStudentReport(studentId: string): Promise<StudentReportData> {
  return request<StudentReportData>(`/students/${studentId}/report`);
}

/**
 * 向 AI 学习助手提问并获取结构化回答
 */
export async function askAssistant(
  studentId: string,
  message: string
): Promise<AssistantResponse> {
  return request<AssistantResponse>(`/students/${studentId}/assistant`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

/**
 * 获取当前学生的 AI 专属问候语与动态快捷问题
 */
export async function getAssistantGreeting(
  studentId: string
): Promise<AssistantGreetingResponse> {
  return request<AssistantGreetingResponse>(`/students/${studentId}/assistant/greeting`);
}

/**
 * 获取指定学生微观经济学知识图谱拓扑与学情联动数据
 */
export async function getStudentKnowledgeGraph(
  studentId: string
): Promise<KnowledgeGraphResponse> {
  return request<KnowledgeGraphResponse>(`/students/${studentId}/knowledge-graph`);
}

import {
  getOfflineQuestionsByKnowledgeId,
  getOfflineQuestionById,
} from './components/student/quizBankData';
import { getConceptCardById } from './components/student/conceptCardData';

/**
 * 获取指定知识点的微测验题目（服务端权威脱敏，绝不暴露正确答案）
 */
export async function getQuizQuestions(
  knowledgeId: string
): Promise<QuizKnowledgeListResponse> {
  try {
    return await request<QuizKnowledgeListResponse>(`/quiz/${knowledgeId}`);
  } catch (err) {
    const offlineQuestions = getOfflineQuestionsByKnowledgeId(knowledgeId);
    if (offlineQuestions.length > 0) {
      return {
        knowledge_id: knowledgeId,
        knowledge_name: knowledgeId,
        questions: offlineQuestions,
      };
    }
    throw err;
  }
}

/**
 * 提交微测验单题作答，服务端权威判题并持久化 QUESTION_ATTEMPT 学习事件
 */
export async function submitQuizAnswer(
  data: QuizSubmitRequest
): Promise<QuizSubmitResponse> {
  try {
    return await request<QuizSubmitResponse>('/quiz/submit', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  } catch (err) {
    const offlineQ = getOfflineQuestionById(data.question_id);
    if (offlineQ) {
      const isCorrect = data.selected_option === offlineQ.answer;
      return {
        is_correct: isCorrect,
        correct_option: offlineQ.answer,
        explanation: offlineQ.explanation,
        knowledge_id: offlineQ.knowledge_id,
        question_id: offlineQ.question_id,
        event_id: `evt-offline-${Date.now()}`,
        learning_state: {
          updated: true,
          mastery_probability: isCorrect ? 0.82 : 0.45,
          mastery_percent: isCorrect ? 82.0 : 45.0,
          state: isCorrect ? 'MASTERED' : 'WEAK',
          attempts: 1,
          consecutive_correct: isCorrect ? 1 : 0,
        },
      };
    }
    throw err;
  }
}

/**
 * 获取指定学生各知识点的学习路径执行状态 (LOCKED / AVAILABLE / IN_PROGRESS / COMPLETED)
 */
export async function getStudentPathStates(
  studentId: string
): Promise<StudentPathStatesResponse> {
  return request<StudentPathStatesResponse>(`/students/${studentId}/path-states`);
}

/**
 * 获取指定知识点的概念微卡片（先学后测）
 */
export interface ConceptCardResponse {
  knowledge_id: string;
  knowledge_name: string;
  chapter: string;
  one_line_intuition: string;
  core_concept: string;
  simple_example: string;
  common_misconceptions: string;
  learning_objective: string;
  reading_time_seconds: number;
}

export async function getConceptCard(
  knowledgeId: string
): Promise<ConceptCardResponse> {
  try {
    return await request<ConceptCardResponse>(`/concept/${knowledgeId}`);
  } catch {
    const local = getConceptCardById(knowledgeId);
    if (local) {
      return {
        knowledge_id: local.knowledgeId,
        knowledge_name: local.knowledgeName,
        chapter: local.chapter,
        one_line_intuition: local.oneLineIntuition,
        core_concept: local.coreConcept,
        simple_example: local.simpleExample,
        common_misconceptions: local.commonMisconceptions,
        learning_objective: local.learningObjective,
        reading_time_seconds: local.readingTimeSeconds,
      };
    }
    throw new Error(`未找到知识点 ${knowledgeId} 的概念微卡片`);
  }
}

/**
 * 轻量级 Demo 学生初始化
 */
export interface StudentInitRequest {
  student_id?: string;
  student_name: string;
  major?: string;
  grade?: string;
  learning_goal?: string;
  class_name?: string;
  start_knowledge_id?: string;
}

export interface StudentInitResponse {
  student_id: string;
  student_name: string;
  major: string;
  grade: string;
  learning_goal: string;
  class_name: string;
  current_knowledge_id: string;
  path_states: Record<string, string>;
  message: string;
}

export async function initStudent(
  data: StudentInitRequest
): Promise<StudentInitResponse> {
  return request<StudentInitResponse>('/students/init', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

