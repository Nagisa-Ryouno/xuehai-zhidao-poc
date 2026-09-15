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
  replanning?: DecisionAuditEnvelope | null;
}

// ============================================================
// 路径执行状态与重规划决策契约 (PathState & Replanning)
// ============================================================

export type PathState = 'LOCKED' | 'AVAILABLE' | 'IN_PROGRESS' | 'COMPLETED';

export interface StudentPathStatesResponse {
  student_id: string;
  states: Record<string, PathState>;
}

export type PathAction =
  | 'UNLOCK_DOWNSTREAM'
  | 'RETAIN'
  | 'DEMOTE_TO_REVIEW'
  | string;

export type ReplanningReasonCode =
  | 'MASTERY_THRESHOLD_REACHED'
  | 'MASTERY_STATE_UNCHANGED'
  | 'PREREQUISITE_NOT_READY'
  | 'REVIEW_REQUIRED_DEMOTION'
  | string;

export interface ReplanningCanonicalPayload {
  rule_version: string;
  student_id: string;
  knowledge_id: string;
  before_mastery: string;
  after_mastery: string;
  before_path_state: PathState;
  after_path_state: PathState;
  action: PathAction;
  reason_code: ReplanningReasonCode;
  affected_nodes: string[];
}

export interface ReplanningAuditMetadata {
  decision_id: string;
  timestamp: string;
  trace_id?: string | null;
}

export interface DecisionAuditEnvelope {
  audit_metadata: ReplanningAuditMetadata;
  canonical_payload: ReplanningCanonicalPayload;
}

// ============================================================
// Phase 3 / Sprint 7: AI Learning Companion Context Boundary
// ============================================================

export interface NextLearningAction {
  type: 'CONTINUE_NEXT' | 'RETRY' | 'RETURN_TASKS';
  knowledgeId?: string;
  knowledgeName?: string;
  label: string;
}

export interface RecentQuizFact {
  readonly question_id: string;
  readonly is_correct: boolean;
  readonly time_spent_ms: number;
  readonly before_mastery_percent: number;
  readonly after_mastery_percent: number;
  readonly delta_percent: number;
  readonly action: PathAction;
  readonly reason_code: ReplanningReasonCode;
  readonly unlocked_nodes: readonly string[];
}

export interface LearningContextSystemFacts {
  readonly student_id: string;
  readonly student_name: string;
  readonly major: string;
  readonly grade: string;
  readonly learning_goal: string;

  readonly current_knowledge_id: string;
  readonly current_knowledge_name: string;
  readonly current_chapter: string;
  readonly current_path_state: PathState;

  readonly current_mastery_percent: number;
  readonly mastery_target_percent: number;
  readonly mastery_target_threshold: number;
  readonly mastery_gap_percent: number;
  readonly is_mastered: boolean;

  readonly prerequisites_met: boolean;
  readonly path_priority: string;
  readonly is_path_completed: boolean;

  readonly recent_quiz?: RecentQuizFact;

  readonly next_action: NextLearningAction;
}

export interface LearningContextDerivedExplanations {
  readonly recommendation_reason: string;
  readonly progression_summary?: string;
  readonly action_guidance: string;
}

export interface LearningContext {
  readonly system_facts: LearningContextSystemFacts;
  readonly derived_explanations: LearningContextDerivedExplanations;
}

/**
 * 预留 AI 标注层：明确与系统事实物理隔离，AI 标注绝不可反向污染系统事实
 */
export interface AIAnnotations {
  readonly suggested_questions?: readonly string[];
  readonly confidence?: number;
}

export interface GroundedAIContext extends LearningContext {
  readonly ai_annotations?: AIAnnotations;
}

/**
 * AI 学习伴学最终呈现回答契约 (Grounded Answer)
 * 严禁包含 next_action, decision, unlock_nodes 等任何学习决策字段
 */
export interface GroundedAnswer {
  readonly answer: string;
  readonly grounding_status: 'grounded' | 'fallback';
  readonly validation_reason?: string;
  readonly referenced_facts?: readonly string[];
  readonly suggested_explanation?: string;
}

/**
 * Sprint 8-B: 极速前测与学情诊断类型契约
 */
export interface DiagnosticOption {
  key: string;
  text: string;
}

export interface DiagnosticQuestionPublic {
  question_id: string;
  knowledge_id: string;
  knowledge_name: string;
  stem: string;
  options: DiagnosticOption[];
  difficulty: number;
}

export interface PretestSession {
  session_id: string;
  student_id: string;
  goal: string;
  questions: DiagnosticQuestionPublic[];
  created_at: string;
  completed: boolean;
}

export interface KnowledgeDiagnostic {
  knowledge_id: string;
  knowledge_name: string;
  question_id: string;
  user_answer: string;
  is_correct: boolean;
  estimated_mastery: number;
  status: string;
  feedback: string;
}

export interface DiagnosticResult {
  session_id: string;
  student_id: string;
  goal: string;
  total_questions: number;
  correct_count: number;
  accuracy: number;
  overall_level: string;
  overall_level_label: string;
  knowledge_diagnostics: KnowledgeDiagnostic[];
  weaknesses: string[];
  strengths: string[];
  summary_text: string;
  recommended_focus_id?: string;
  completed_at: string;
}

/**
 * Sprint 8-B: 动态学习航线类型契约
 */
export interface RouteStep {
  knowledge_id: string;
  knowledge_name: string;
  chapter: string;
  rank: number;
  role: 'CURRENT' | 'NEXT' | 'UPCOMING';
  score: number;
  reason_codes: string[];
  explanation: string;
  mastery: number;
  path_state: string;
  prerequisites: string[];
}

export interface DynamicLearningRoute {
  student_id: string;
  goal: string;
  route_length: number;
  steps: RouteStep[];
  is_fallback: boolean;
  fallback_reason?: string;
  generated_at: string;
}

/**
 * Sprint 8-C: 学习成效沉淀与教师分析类型契约
 */

export interface MasteryTrendPoint {
  timestamp: string;
  overall_mastery: number;
  event_type: string;
  knowledge_id?: string;
}

export interface KnowledgePointMasteryItem {
  knowledge_id: string;
  knowledge_name: string;
  chapter: string;
  mastery: number;
  status: 'MASTERED' | 'DEVELOPING' | 'NEEDS_REINFORCEMENT' | 'UNSTUDIED';
  attempts: number;
  accuracy: number;
}

export interface LearningHistoryItem {
  event_id: string;
  event_type: string;
  timestamp: string;
  knowledge_id?: string;
  knowledge_name?: string;
  is_correct?: boolean;
  details?: string;
}

export interface StudentProgressResponse {
  student_id: string;
  overall_mastery: number;
  mastery_level: string;
  total_practice_count: number;
  total_correct_count: number;
  overall_accuracy: number;
  mastered_count: number;
  developing_count: number;
  weak_count: number;
  unstudied_count: number;
  mastery_trend: MasteryTrendPoint[];
  knowledge_points: KnowledgePointMasteryItem[];
  history_timeline: LearningHistoryItem[];
}

export interface WrongAnswerItem {
  question_id: string;
  knowledge_id: string;
  knowledge_name: string;
  chapter: string;
  question_prompt: string;
  options: Record<string, string>;
  student_answer: string;
  correct_answer: string;
  explanation: string;
  current_mastery: number;
  current_path_state: string;
  mistake_count: number;
  last_error_time: string;
  review_priority: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface WrongAnswerReviewResponse {
  student_id: string;
  total_wrong: number;
  wrong_answers: WrongAnswerItem[];
}

export interface TeacherClassKPIs {
  total_students: number;
  active_students: number;
  class_avg_mastery: number;
  at_risk_students_count: number;
}

export interface TeacherWeakKnowledgePoint {
  knowledge_id: string;
  knowledge_name: string;
  chapter: string;
  avg_mastery: number;
  error_rate: number;
  weak_student_count: number;
  urgency: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface TeacherStudentSummary {
  student_id: string;
  student_name: string;
  major: string;
  grade: string;
  learning_goal: string;
  overall_mastery: number;
  mastered_count: number;
  developing_count: number;
  weak_count: number;
  total_attempts: number;
  total_wrong_count: number;
  accuracy: number;
  last_active_time?: string;
  risk_level: 'HEALTHY' | 'NORMAL' | 'ATTENTION';
  current_focus_node?: string;
  current_focus_name?: string;
}

export interface TeacherOverviewResponse {
  class_kpis: TeacherClassKPIs;
  weak_knowledge_points: TeacherWeakKnowledgePoint[];
  students: TeacherStudentSummary[];
}

export interface TeacherStudentDetailResponse {
  summary: TeacherStudentSummary;
  progress: StudentProgressResponse;
  wrong_answers: WrongAnswerReviewResponse;
  current_route: RouteStep[];
}

// ============================================================
// Phase 5 / Sprint 9-A: AI 学习伙伴 (Companion) 契约类型
// ============================================================

export type CompanionMode =
  | 'concept_explain'
  | 'wrong_answer_review'
  | 'conversation'
  | 'learning_summary';

export interface CompanionSafetyMetadata {
  allow_production_decision: boolean;
  sanitized: boolean;
  offline_mode: boolean;
  context_source: string;
  redactions_applied: string[];
}

export interface CompanionContextMetadata {
  student_id: string;
  knowledge_id?: string;
  knowledge_name?: string;
  chapter?: string;
  mastery?: number;
  mastery_status?: string;
  prerequisites: string[];
  question_id?: string;
  learning_goal?: string;
}

export interface CompanionStudyRequest {
  student_id: string;
  mode: CompanionMode;
  knowledge_id?: string;
  question_id?: string;
  message?: string;
  session_id?: string;
  resource_id?: string;
  resource_context?: Record<string, any>;
}

export interface CompanionStudyResponse {
  session_id: string;
  mode: CompanionMode;
  answer: string;
  context: CompanionContextMetadata;
  safety: CompanionSafetyMetadata;
  suggested_actions: string[];
  provider: string;
  referenced_facts: string[];
  guided_actions?: CompanionSuggestedAction[];
  learning_state?: Record<string, any>;
  quick_check?: QuickCheckQuestion;
}

export interface CompanionChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface CompanionSession {
  session_id: string;
  student_id: string;
  messages: CompanionChatMessage[];
  last_knowledge_id?: string;
  created_at: string;
}

// ============================================================
// Phase 5 / Sprint 9-B: AI 引导学习与行动反思契约类型
// ============================================================

export type ActionType =
  | 'READ_CONCEPT'
  | 'TARGETED_PRACTICE'
  | 'VIEW_PROGRESS'
  | 'REVIEW_WRONG_ANSWERS'
  | 'CONTINUE_DISCUSSION';

export interface CompanionSuggestedAction {
  action_id: string;
  action_type: ActionType;
  title: string;
  description: string;
  target_knowledge_id?: string;
  target_question_id?: string;
  route_destination: string;
  source_reason: string;
  badge?: string;
}

export interface QuickCheckOption {
  id: string;
  text: string;
}

export interface QuickCheckQuestion {
  question_id: string;
  knowledge_id: string;
  stem: string;
  options: QuickCheckOption[];
  concept_summary: string;
}

export interface QuickCheckSubmitRequest {
  student_id: string;
  knowledge_id: string;
  question_id: string;
  selected_option: string;
}

export interface QuickCheckResponse {
  is_correct: boolean;
  correct_option: string;
  explanation: string;
  key_takeaway: string;
  suggested_actions: CompanionSuggestedAction[];
}

export interface LearningActionResultRequest {
  student_id: string;
  action_id: string;
  action_type: ActionType;
  knowledge_id: string;
  question_id?: string;
  is_correct?: boolean;
  score?: number;
}

export interface LearningActionResultResponse {
  session_id: string;
  action_id: string;
  action_type: ActionType;
  knowledge_id: string;
  knowledge_name: string;
  before_mastery: number;
  after_mastery: number;
  mastery_delta: number;
  consecutive_incorrect: number;
  mastery_state_text: string;
  reflection_text: string;
  reflection?: string;
  next_actions: CompanionSuggestedAction[];
  guided_actions?: CompanionSuggestedAction[];
  offline_mode: boolean;
}

// -----------------------------------------------------------------------------
// Phase 5 / Sprint 9-C: Learning Resource Hub & Resource-aware Adaptive Learning
// -----------------------------------------------------------------------------
export type ResourceType = 'CONCEPT_CARD' | 'EXAMPLE' | 'PRACTICE' | 'DOCUMENT' | 'VIDEO';

export interface LearningResource {
  resource_id: string;
  knowledge_id: string;
  resource_type: ResourceType;
  title: string;
  description: string;
  source: string;
  source_url?: string | null;
  estimated_minutes: number;
  difficulty: number;
  summary?: string | null;
  content_ref?: string | null;
  is_external: boolean;
  priority: number;
  metadata?: Record<string, any>;
}

export interface ResourceRecommendation {
  resource: LearningResource;
  rank: number;
  recommended_reason: string;
  reason_category: string;
  suggested_order: number;
}

export interface RecommendedResourcesResponse {
  student_id: string;
  knowledge_id: string;
  mastery: number;
  case_code: string;
  recommendations: ResourceRecommendation[];
  reason_summary: string;
}

export interface ResourceListResponse {
  knowledge_id: string;
  total: number;
  resources: LearningResource[];
}

export interface ResourceEventPayload {
  student_id: string;
  resource_id: string;
  knowledge_id: string;
  event_type: 'RESOURCE_VIEW' | 'RESOURCE_OPEN' | 'RESOURCE_COMPLETE' | 'RESOURCE_EXTERNAL_OPEN';
  duration_seconds?: number;
  metadata?: Record<string, any>;
  client_timestamp?: string;
}

// -----------------------------------------------------------------------------
// Phase 5 / Sprint 9-D: Learning Effectiveness & Adaptive Resource Feedback
// -----------------------------------------------------------------------------
export type SessionStatus = 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED' | 'ABANDONED';
export type EffectivenessStatus = 'STRONG_PROGRESS' | 'MEANINGFUL_PROGRESS' | 'STABLE' | 'NEEDS_MORE_SUPPORT';

export interface LearningSession {
  session_id: string;
  student_id: string;
  knowledge_id: string;
  started_at: string;
  completed_at?: string | null;
  initial_mastery: number;
  final_mastery?: number | null;
  mastery_delta?: number | null;
  resource_ids: string[];
  completed_resource_ids: string[];
  quiz_question_id?: string | null;
  quiz_result?: Record<string, any> | null;
  status: SessionStatus;
  metadata?: Record<string, any>;
}

export interface LearningEffectiveness {
  session_id: string;
  student_id: string;
  knowledge_id: string;
  initial_mastery: number;
  final_mastery: number;
  mastery_delta: number;
  status: EffectivenessStatus;
  status_display: string;
  feedback_title: string;
  feedback_message: string;
  suggested_next_action: string;
  resources_completed_count: number;
  quiz_passed?: boolean | null;
}

export interface ResourceEffectivenessSignal {
  resource_id: string;
  knowledge_id: string;
  sample_size: number;
  avg_mastery_delta: number;
  completion_rate: number;
  effectiveness_score: number;
  confidence_level: 'LOW' | 'MEDIUM' | 'HIGH';
  status_distribution: Record<string, number>;
}

export interface KnowledgeEffectivenessResponse {
  student_id: string;
  knowledge_id: string;
  current_mastery: number;
  latest_session?: LearningSession | null;
  effectiveness?: LearningEffectiveness | null;
  historical_signal?: ResourceEffectivenessSignal | null;
}

export interface SessionCompleteResponse {
  session: LearningSession;
  effectiveness: LearningEffectiveness;
  next_step_summary: string;
}


