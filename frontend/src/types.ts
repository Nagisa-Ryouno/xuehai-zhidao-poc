/**
 * types.ts
 * 学海智导 (Xuehai Zhidao) - 前端核心数据类型定义
 * 严格按照 04_api.py 与 output/*.json 实际结构定义
 */

export interface StudentBasic {
  student_id: string;
  student_name: string;
  major: string;
  grade: string;
  learning_goal: string;
}

export interface StudentListItem extends StudentBasic {
  average_accuracy: number;
  mastery_level: string;
  activity_level: string;
  completion_level: string;
}

export interface OverallProfile {
  average_accuracy: number;
  average_assessment_score: number;
  total_learning_time_minutes: number;
  total_practice_count: number;
  total_interaction_count: number;
  average_completion_rate: number;
  average_answer_time_seconds: number;
  mastery_level: string;
  speed_status: string;
  activity_level: string;
  completion_level: string;
}

export interface WeakKnowledgePoint {
  knowledge_id: string;
  knowledge_name: string;
  accuracy: number;
  assessment_score: number;
  average_time_seconds: number;
  difficulty: number;
  prerequisite: string[];
}

export interface PrerequisiteKnowledgePoint {
  knowledge_id: string;
  knowledge_name: string;
  accuracy: number | null;
  reason: string;
}

export interface ProfileSummary {
  mastery_level: string;
  average_accuracy: number;
  average_assessment_score: number;
  speed_status: string;
  activity_level: string;
  completion_level: string;
}

export interface LearningPathStep {
  stage: number;
  knowledge_id: string;
  knowledge_name: string;
  chapter: string;
  current_accuracy: number;
  priority: string;
  priority_score: number;
  source?: string;
  learning_goal: string;
  reason: string;
  difficulty?: number;
  description?: string;
}

export interface DailyLearningPlan {
  recommended_minutes: number;
  recommended_questions: number;
  focus: string;
}

export interface ReportDiagnosis {
  mastery_description: string;
  behavior_description: string;
  main_problems: string[];
  weak_knowledge_count: number;
  prerequisite_knowledge_count: number;
}

export interface PersonalizedStrategy {
  recommendation_type: string;
  strategy_description: string;
}

export interface StudentProfileData {
  student: StudentBasic;
  overall_profile: OverallProfile;
  weak_knowledge_points: WeakKnowledgePoint[];
  prerequisite_knowledge_points: PrerequisiteKnowledgePoint[];
  diagnosis: string[];
}

export interface StudentLearningPathData {
  student: StudentBasic;
  profile_summary: ProfileSummary;
  recommendation_type: string;
  learning_path: LearningPathStep[];
  optimization_suggestion: string[];
}

export interface StudentReportData {
  student_id: string;
  student: StudentBasic;
  learning_overview: OverallProfile;
  diagnosis: ReportDiagnosis;
  personalized_strategy: PersonalizedStrategy;
  learning_path: LearningPathStep[];
  daily_learning_plan: DailyLearningPlan;
  optimization_suggestions: string[];
  ai_summary: string;
}

export interface StudentDashboardResponse {
  student_id: string;
  profile: StudentProfileData;
  learning_path: StudentLearningPathData;
  report: StudentReportData;
}

export interface SystemOverview {
  student_count: number;
  profile_count: number;
  learning_path_count: number;
  report_count: number;
  students: {
    student_id: string;
    student_name: string;
  }[];
}

export interface AssistantRequest {
  message: string;
}

export interface AssistantRelatedKnowledgePoint {
  knowledge_id: string;
  knowledge_name: string;
  accuracy: number | null;
  priority: string;
  reason: string;
  chapter?: string;
  learning_goal?: string;
  source?: string;
}

export interface AssistantResponse {
  student_id: string;
  message: string;
  answer: string;
  related_knowledge_points: AssistantRelatedKnowledgePoint[];
  suggested_actions: string[];
}

export interface AssistantGreetingResponse {
  student_id: string;
  student_name: string;
  greeting: string;
  quick_prompts: string[];
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
  related_knowledge_points?: AssistantRelatedKnowledgePoint[];
  suggested_actions?: string[];
}

// ============================================================
// 知识图谱相关类型定义
// ============================================================

export type KnowledgeNodeStatus = 'WEAK' | 'NEED_REVIEW' | 'MASTERED' | 'UNSTUDIED';

export interface KnowledgeGraphNodeData {
  knowledge_id: string;
  knowledge_name: string;
  chapter: string;
  description: string;
  difficulty: number;
  accuracy: number | null;
  assessment_score: number | null;
  practice_count: number | null;
  average_time_seconds: number | null;
  status: KnowledgeNodeStatus;
  is_weak: boolean;
  is_prerequisite: boolean;
  prerequisite_reason: string | null;
  prerequisite_for: string[];
  is_recommended: boolean;
  path_stage: number | null;
  priority: string | null;
  learning_goal: string | null;
  recommend_reason: string | null;
  upstream_prerequisites: string[];
  downstream_knowledge: string[];
  upstream_count: number;
  downstream_count: number;
  [key: string]: unknown;
}

export interface KnowledgeGraphNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: KnowledgeGraphNodeData;
}

export interface KnowledgeGraphEdgeData {
  prerequisite_reason?: string;
  is_active_path?: boolean;
  source_name?: string;
  target_name?: string;
  [key: string]: unknown;
}

export interface KnowledgeGraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  animated?: boolean;
  data?: KnowledgeGraphEdgeData;
}

export interface KnowledgeGraphStats {
  total_nodes: number;
  total_edges: number;
  studied_count: number;
  unstudied_count: number;
  weak_count: number;
  recommended_count: number;
  average_accuracy: number;
  mastery_level: string;
}

export interface KnowledgeGraphResponse {
  student_id: string;
  student_name: string;
  stats: KnowledgeGraphStats;
  ai_insight: string;
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
}

export type GraphFilterType = 'all' | 'weak' | 'recommended' | 'prerequisite';

// ============================================================
// P0-4/P0-5 分知识点微测验相关类型契约
// ============================================================

export interface QuizOption {
  key: string;
  text: string;
}

export interface QuizQuestionPublic {
  question_id: string;
  knowledge_id: string;
  stem: string;
  options: QuizOption[];
  difficulty: number;
}

export interface QuizKnowledgeListResponse {
  knowledge_id: string;
  knowledge_name: string;
  questions: QuizQuestionPublic[];
}

export interface QuizSubmitRequest {
  student_id: string;
  question_id: string;
  selected_option: string;
  time_spent_ms?: number;
}

export interface LearningStateSnapshot {
  updated: boolean;
  mastery_probability?: number | null;
  mastery_percent?: number | null;
  state?: 'WEAK' | 'DEVELOPING' | 'MASTERED' | string;
  attempts?: number;
  consecutive_correct?: number;
  reason?: string;
}

export interface QuizSubmitResponse {
  is_correct: boolean;
  correct_option: string;
  explanation: string;
  knowledge_id: string;
  question_id: string;
  event_id: string;
  learning_state?: LearningStateSnapshot | null;
}
