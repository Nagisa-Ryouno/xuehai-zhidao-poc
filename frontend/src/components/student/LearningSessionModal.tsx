import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  X,
  BookOpen,
  Sparkles,
  Lightbulb,
  AlertTriangle,
  Target,
  ArrowRight,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Loader2,
  AlertCircle,
  ExternalLink,
  Layers,
  Award,
  ChevronLeft,
} from 'lucide-react';
import type {
  TodayLearningAction,
  LearningResource,
  QuizQuestionPublic,
  QuizSubmitResponse,
  PersonalizedRecommendation,
} from '../../types';
import {
  getQuizQuestions,
  submitQuizAnswer,
  getConceptCard,
  getResourcesByKnowledge,
  getStudentProgress,
  recordResourceEvent,
  getPersonalizedRecommendations,
  getResourceItem,
  type ConceptCardResponse,
} from '../../api';
import { getConceptCardById, type ConceptCardData } from './conceptCardData';
import { ExternalRedirectModal } from './ExternalRedirectModal';
import { openExternalMoocUrl } from '../../utils/externalResource';

export type SessionStep = 'ENTRY' | 'CONCEPT' | 'RESOURCE' | 'QUIZ' | 'RESULT';

export interface LearningSessionModalProps {
  isOpen: boolean;
  studentId: string;
  action?: TodayLearningAction | null;
  knowledgeId: string;
  knowledgeName: string;
  initialStep?: SessionStep;
  currentMasteryPercent?: number | null;
  onClose: () => void;
  onFinishSession?: (nextKnowledgeId?: string, nextKnowledgeName?: string) => void;
  onNavigateToTasks?: () => void;
}

export const LearningSessionModal: React.FC<LearningSessionModalProps> = ({
  isOpen,
  studentId,
  action = null,
  knowledgeId,
  knowledgeName: initialKnowledgeName,
  initialStep = 'ENTRY',
  currentMasteryPercent = null,
  onClose,
  onFinishSession,
  onNavigateToTasks,
}) => {
  // 1. Session UI 步骤管理 (严格限定为轻量 UI 步骤，绝不建立业务学习状态机)
  const [currentStep, setCurrentStep] = useState<SessionStep>(initialStep);

  // 考点上下文
  const [activeKid, setActiveKid] = useState<string>(knowledgeId);
  const [activeKname, setActiveKname] = useState<string>(initialKnowledgeName);

  // 当外部传入的 knowledgeId 或 initialStep 发生变化时同步
  useEffect(() => {
    setActiveKid(knowledgeId);
    setActiveKname(initialKnowledgeName);
    setCurrentStep(initialStep);
  }, [knowledgeId, initialKnowledgeName, initialStep]);

  // ---------------------------------------------------------------------------
  // 2. Concept 概念数据状态与加载
  // ---------------------------------------------------------------------------
  const [conceptData, setConceptData] = useState<ConceptCardResponse | ConceptCardData | null>(null);
  const [isConceptLoading, setIsConceptLoading] = useState<boolean>(false);
  const [conceptError, setConceptError] = useState<string | null>(null);

  const loadConcept = useCallback(async (kid: string) => {
    setIsConceptLoading(true);
    setConceptError(null);
    try {
      const res = await getConceptCard(kid);
      setConceptData(res);
      if (res.knowledge_name) {
        setActiveKname(res.knowledge_name);
      }
    } catch {
      // 本地离线备选
      const local = getConceptCardById(kid);
      if (local) {
        setConceptData(local);
        if (local.knowledgeName) {
          setActiveKname(local.knowledgeName);
        }
      } else {
        setConceptError('暂时无法加载学习内容，请尝试重新加载');
      }
    } finally {
      setIsConceptLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen && activeKid) {
      loadConcept(activeKid);
    }
  }, [isOpen, activeKid, loadConcept]);

  // ---------------------------------------------------------------------------
  // 3. Resource 资源数据状态与加载 (可选分支，500 异常绝不阻断 Concept/Quiz 主链)
  // ---------------------------------------------------------------------------
  const [resources, setResources] = useState<LearningResource[]>([]);
  const [isResourceLoading, setIsResourceLoading] = useState<boolean>(false);
  const [resourceError, setResourceError] = useState<string | null>(null);
  const [activeMoocResource, setActiveMoocResource] = useState<LearningResource | null>(null);

  // Sprint 10-C Phase 3: AI 个性化推荐状态 (纯辅助候选列表，永无生产学习决策权)
  const [personalRecommendations, setPersonalRecommendations] = useState<PersonalizedRecommendation[]>([]);
  const [isPersonalRecLoading, setIsPersonalRecLoading] = useState<boolean>(false);
  const [personalRecError, setPersonalRecError] = useState<string | null>(null);
  const fetchedRecKidRef = useRef<string | null>(null);

  // 当 studentId 或 activeKid 变更时，严格重置推荐状态，保障多学生/跨考点隔离
  useEffect(() => {
    setPersonalRecommendations([]);
    setPersonalRecError(null);
    setIsPersonalRecLoading(false);
    fetchedRecKidRef.current = null;
  }, [studentId, activeKid]);

  const loadResources = useCallback(async (kid: string) => {
    setIsResourceLoading(true);
    setResourceError(null);
    try {
      const res = await getResourcesByKnowledge(kid);
      setResources(res.resources || []);
    } catch {
      setResourceError('暂时无法加载学习资源');
    } finally {
      setIsResourceLoading(false);
    }
  }, []);

  // 严格约束：kid 必须来自权威会话上下文 activeKid，绝对禁止外部用户篡改或随意指定
  const loadPersonalRecommendations = useCallback(
    async (kid: string) => {
      setIsPersonalRecLoading(true);
      setPersonalRecError(null);
      try {
        const resp = await getPersonalizedRecommendations(studentId, 3, kid);
        setPersonalRecommendations(resp.recommendations || []);
      } catch (err) {
        console.warn('AI personalized recommendation unavailable, degrading gracefully:', err);
        setPersonalRecommendations([]);
        setPersonalRecError('暂时无法生成个性化推荐');
      } finally {
        setIsPersonalRecLoading(false);
      }
    },
    [studentId]
  );

  const handleOpenResourceStep = () => {
    setCurrentStep('RESOURCE');
    if (resources.length === 0 && !resourceError) {
      loadResources(activeKid);
    }
    if (fetchedRecKidRef.current !== activeKid) {
      fetchedRecKidRef.current = activeKid;
      loadPersonalRecommendations(activeKid);
    }
  };

  // 若以 RESOURCE 步直接进入，自动异步触发加载
  useEffect(() => {
    if (isOpen && currentStep === 'RESOURCE' && activeKid) {
      if (resources.length === 0 && !resourceError && !isResourceLoading) {
        loadResources(activeKid);
      }
      if (fetchedRecKidRef.current !== activeKid) {
        fetchedRecKidRef.current = activeKid;
        loadPersonalRecommendations(activeKid);
      }
    }
  }, [isOpen, currentStep, activeKid, loadResources, loadPersonalRecommendations, resources.length, resourceError, isResourceLoading]);

  // 纯 UI 展示去重策略 (Strictly UI-level deduplication)：
  // 1. 精选资源首屏保持原确定性顺序，不改变、不删除
  const baselineTopResources = useMemo(() => resources.slice(0, 3), [resources]);
  const baselineTopIds = useMemo(
    () => new Set(baselineTopResources.map((r) => r.resource_id)),
    [baselineTopResources]
  );

  // 2. 为你推荐仅展示 AI 推荐结果中不在当前精选资源首屏列表中的候选
  const deduplicatedPersonalRecs = useMemo(() => {
    return personalRecommendations.filter((rec) => !baselineTopIds.has(rec.resource_id));
  }, [personalRecommendations, baselineTopIds]);

  // 打开 AI 推荐资源：安全分流，中国大学 MOOC 严格调起 ExternalRedirectModal
  const handleOpenRecommendedResource = async (rec: PersonalizedRecommendation) => {
    let target = resources.find((r) => r.resource_id === rec.resource_id);
    if (!target) {
      try {
        target = await getResourceItem(rec.resource_id);
      } catch {
        target = {
          resource_id: rec.resource_id,
          knowledge_id: rec.knowledge_id,
          resource_type: (rec.resource_type || 'DOCUMENT') as any,
          title: rec.title,
          description: rec.reason,
          source: rec.source,
          source_url: rec.source === 'china_mooc' ? 'https://www.icourse163.org' : null,
          estimated_minutes: 10,
          difficulty: 0.5,
          is_external: rec.source === 'china_mooc',
          priority: 50,
        };
      }
    }

    if (target) {
      if (target.is_external || target.source === 'china_mooc') {
        setActiveMoocResource(target);
      } else {
        recordResourceEvent({
          student_id: studentId,
          resource_id: target.resource_id,
          knowledge_id: activeKid,
          event_type: 'RESOURCE_OPEN',
        }).catch(() => {});
      }
    }
  };

  // ---------------------------------------------------------------------------
  // 4. Quiz 测验数据状态与交互 (防双击提交、权威判题、无技术黑话)
  // ---------------------------------------------------------------------------
  const [quizQuestions, setQuizQuestions] = useState<QuizQuestionPublic[]>([]);
  const [isQuizLoading, setIsQuizLoading] = useState<boolean>(false);
  const [quizLoadError, setQuizLoadError] = useState<string | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [currentFeedback, setCurrentFeedback] = useState<QuizSubmitResponse | null>(null);

  // 提交作答记录，用于成果结算
  const [quizRecords, setQuizRecords] = useState<
    Array<{
      questionId: string;
      selectedOption: string;
      correctOption: string;
      isCorrect: boolean;
      explanation: string;
    }>
  >([]);

  // 同步锁：用于同步拦截浏览器的连击 (Double / Triple Click)
  const isSubmittingLock = useRef<boolean>(false);

  const loadQuiz = useCallback(async (kid: string) => {
    setIsQuizLoading(true);
    setQuizLoadError(null);
    setCurrentQuestionIndex(0);
    setSelectedOption(null);
    setCurrentFeedback(null);
    setQuizRecords([]);
    try {
      const res = await getQuizQuestions(kid);
      setQuizQuestions(res.questions || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '小测验暂时无法加载';
      setQuizLoadError(msg);
    } finally {
      setIsQuizLoading(false);
    }
  }, []);

  const handleStartQuizStep = () => {
    setCurrentStep('QUIZ');
    loadQuiz(activeKid);
  };

  const handleOptionSelect = (key: string) => {
    if (currentFeedback || isSubmitting) return;
    setSelectedOption(key);
  };

  const handleSubmitAnswer = async () => {
    if (isSubmittingLock.current || !selectedOption) return;
    const currentQ = quizQuestions[currentQuestionIndex];
    if (!currentQ) return;

    // 加上同步锁并设置按钮 disabled 状态
    isSubmittingLock.current = true;
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const payload = {
        student_id: studentId,
        question_id: currentQ.question_id,
        selected_option: selectedOption,
        time_spent_ms: 3000,
      };

      const res = await submitQuizAnswer(payload);
      setCurrentFeedback(res);

      setQuizRecords((prev) => [
        ...prev,
        {
          questionId: currentQ.question_id,
          selectedOption: selectedOption,
          correctOption: res.correct_option,
          isCorrect: res.is_correct,
          explanation: res.explanation,
        },
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '提交作答失败，请检查网络后重试';
      setSubmitError(msg);
    } finally {
      // 关键：发生异常或处理完成后释放同步锁，使按钮能够恢复重试
      isSubmittingLock.current = false;
      setIsSubmitting(false);
    }
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < quizQuestions.length - 1) {
      setCurrentQuestionIndex((prev) => prev + 1);
      setSelectedOption(null);
      setCurrentFeedback(null);
      setSubmitError(null);
    } else {
      // 最后一题作答完毕，进入结算成果阶段
      handleEnterResultStep();
    }
  };

  // ---------------------------------------------------------------------------
  // 5. Result 结果与权威掌握度重新读取 (严禁前端推算)
  // ---------------------------------------------------------------------------
  const [authoritativeMastery, setAuthoritativeMastery] = useState<number | null>(null);
  const [isMasteryReading, setIsMasteryReading] = useState<boolean>(false);
  const [masteryReadError, setMasteryReadError] = useState<string | null>(null);

  const fetchAuthoritativeMastery = useCallback(async (stuId: string, kid: string) => {
    setIsMasteryReading(true);
    setMasteryReadError(null);
    try {
      const progress = await getStudentProgress(stuId);
      const kp = progress.knowledge_points.find((k) => k.knowledge_id === kid);
      if (kp && typeof kp.mastery === 'number') {
        const pct = kp.mastery > 1 ? Math.round(kp.mastery) : Math.round(kp.mastery * 100);
        setAuthoritativeMastery(pct);
      } else if (typeof progress.overall_mastery === 'number') {
        const pct = progress.overall_mastery > 1 ? Math.round(progress.overall_mastery) : Math.round(progress.overall_mastery * 100);
        setAuthoritativeMastery(pct);
      }
    } catch {
      setMasteryReadError('本次练习已经完成，但暂时无法获取最新学习进展。');
    } finally {
      setIsMasteryReading(false);
    }
  }, []);

  const handleEnterResultStep = () => {
    setCurrentStep('RESULT');
    // 优先使用当前最新一题判题响应中的权威 snapshot
    if (currentFeedback?.learning_state?.mastery_percent != null) {
      setAuthoritativeMastery(Math.round(currentFeedback.learning_state.mastery_percent));
    }
    // 异步重新调用 authoritative progress 接口核实权威掌握度
    fetchAuthoritativeMastery(studentId, activeKid);
  };

  const correctCount = useMemo(() => {
    return quizRecords.filter((r) => r.isCorrect).length;
  }, [quizRecords]);

  const totalQuestions = quizQuestions.length || quizRecords.length || 3;
  const accuracyPercent = totalQuestions > 0 ? Math.round((correctCount / totalQuestions) * 100) : 0;

  // ---------------------------------------------------------------------------
  // 6. Navigation 阶段跳转与退出
  // ---------------------------------------------------------------------------
  const handleNextKnowledgeSession = () => {
    // 从重规划中获取下一节点
    const nextKid = currentFeedback?.replanning?.canonical_payload?.affected_nodes?.[0] || null;
    if (nextKid && onFinishSession) {
      onFinishSession(nextKid, `考点 ${nextKid}`);
      setActiveKid(nextKid);
      setActiveKname(`考点 ${nextKid}`);
      setCurrentStep('ENTRY');
    } else if (onNavigateToTasks) {
      onNavigateToTasks();
      onClose();
    } else {
      onClose();
    }
  };

  const handleBackHome = () => {
    if (onNavigateToTasks) {
      onNavigateToTasks();
    }
    onClose();
  };

  if (!isOpen) return null;

  // 人本考点名称 (去除任何 K01 等生硬技术前缀)
  const displayKpName = (
    (conceptData && 'knowledge_name' in conceptData ? conceptData.knowledge_name : '') ||
    (conceptData && 'knowledgeName' in conceptData ? conceptData.knowledgeName : '') ||
    activeKname ||
    '微观经济学核心考点'
  ).replace(/^K\d+[\s·_-]*/i, '');

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid="learning-session-modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150"
    >
      <div className="bg-white rounded-3xl max-w-2xl w-full max-h-[92vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden animate-in zoom-in-95 duration-200">
        {/* ================================================================= */}
        {/* 顶部 Header：考点人本标题与轻量步骤指示 (非后台强流程) */}
        {/* ================================================================= */}
        <div className="px-5 sm:px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-indigo-50/60 via-white to-violet-50/60">
          <div className="space-y-0.5 max-w-[80%]">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 text-[11px] font-bold text-indigo-700 bg-indigo-100/80 px-2.5 py-0.5 rounded-full">
                <Sparkles className="w-3 h-3 text-indigo-600" />
                {currentStep === 'ENTRY' && '学习导引'}
                {currentStep === 'CONCEPT' && '考点精要'}
                {currentStep === 'RESOURCE' && '学习资源'}
                {currentStep === 'QUIZ' && '随堂微测'}
                {currentStep === 'RESULT' && '成果结算'}
              </span>
              <span className="text-xs text-slate-500 font-medium truncate">
                学海智导 · 伴学工作台
              </span>
            </div>
            <h2 className="text-base sm:text-lg font-black text-slate-900 tracking-tight truncate">
              {displayKpName}
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="关闭学习会话"
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* ================================================================= */}
        {/* 主体内容滚动区 */}
        {/* ================================================================= */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] text-slate-700 text-sm">
          {/* --------------------------------------------------------------- */}
          {/* STEP 1: ENTRY 导引步骤 */}
          {/* --------------------------------------------------------------- */}
          {currentStep === 'ENTRY' && (
            <div data-testid="session-step-entry" className="space-y-5 animate-in fade-in duration-200">
              {/* 考点与目标 */}
              <div className="p-5 rounded-2xl bg-gradient-to-br from-indigo-50/90 via-white to-violet-50/70 border border-indigo-100/80 shadow-2xs space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-indigo-700 uppercase tracking-wider">
                  <BookOpen className="w-4 h-4" />
                  <span>当前学习考点</span>
                </div>
                <h3 className="text-xl font-black text-slate-900 leading-snug">
                  {displayKpName}
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                  {action?.priority_reason ||
                    '这是你当前自适应学习路径中的关键考点，先理解核心机制，再通过 3 道微练习巩固，5-10 分钟即可完成一次有效闭环。'}
                </p>
              </div>

              {/* 为什么现在学 & 掌握度起点 */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
                    <Target className="w-4 h-4 text-indigo-600" />
                    <span>为什么现在学习</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {action?.action_type === 'REVIEW_RETENTION'
                      ? '根据记忆遗忘曲线规律，该考点已到达建议温故时间，快速微测能加深长效掌握。'
                      : action?.action_type === 'PRACTICE'
                      ? '通过靶向微练强化解题思路，巩固薄弱概念。'
                      : '自适应学习路径首要推进节点，掌握它将解锁后续高阶关联考点。'}
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
                    <Award className="w-4 h-4 text-amber-600" />
                    <span>当前掌握度起点</span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-black text-indigo-600">
                      {currentMasteryPercent != null ? `${currentMasteryPercent}%` : '暂未开始'}
                    </span>
                    <span className="text-xs text-slate-500">
                      {currentMasteryPercent != null ? '已具备基础认知' : '即将开启首次学习'}
                    </span>
                  </div>
                </div>
              </div>

              {/* 步骤 CTA 控制 */}
              <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
                <button
                  type="button"
                  data-testid="session-entry-start-concept-btn"
                  onClick={() => setCurrentStep('CONCEPT')}
                  className="w-full sm:flex-1 py-3.5 px-5 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm shadow-md shadow-indigo-500/20 flex items-center justify-center gap-2 transition-all cursor-pointer min-h-[44px]"
                >
                  <span>开始概念精读 (推荐)</span>
                  <ArrowRight className="w-4 h-4" />
                </button>

                <button
                  type="button"
                  data-testid="session-entry-direct-quiz-btn"
                  onClick={handleStartQuizStep}
                  className="w-full sm:w-auto py-3.5 px-4 rounded-2xl border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs sm:text-sm transition-colors cursor-pointer min-h-[44px]"
                >
                  <span>直接开始小测验</span>
                </button>
              </div>
            </div>
          )}

          {/* --------------------------------------------------------------- */}
          {/* STEP 2: CONCEPT 概念微卡步骤 */}
          {/* --------------------------------------------------------------- */}
          {currentStep === 'CONCEPT' && (
            <div data-testid="session-step-concept" className="space-y-4 animate-in fade-in duration-200">
              {isConceptLoading ? (
                <div className="py-12 flex flex-col items-center justify-center text-center space-y-3">
                  <Loader2 className="w-7 h-7 animate-spin text-indigo-600" />
                  <p className="text-xs font-semibold text-slate-500">正在获取考点概念微卡...</p>
                </div>
              ) : conceptError ? (
                <div className="py-8 px-4 flex flex-col items-center justify-center text-center space-y-3.5">
                  <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center">
                    <AlertCircle className="w-6 h-6" />
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-sm font-bold text-slate-900">暂时无法加载学习内容</h4>
                    <p className="text-xs text-rose-600 leading-relaxed">{conceptError}</p>
                  </div>
                  <div className="flex gap-2.5">
                    <button
                      type="button"
                      data-testid="concept-retry-btn"
                      onClick={() => loadConcept(activeKid)}
                      className="py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-xs transition-colors cursor-pointer min-h-[44px]"
                    >
                      重新加载
                    </button>
                    <button
                      type="button"
                      onClick={handleStartQuizStep}
                      className="py-2.5 px-4 rounded-xl border border-slate-200 text-slate-700 font-semibold text-xs hover:bg-slate-50 transition-colors cursor-pointer min-h-[44px]"
                    >
                      直接开始小测验
                    </button>
                  </div>
                </div>
              ) : conceptData ? (
                <>
                  {/* 一句话直觉导引 */}
                  {'one_line_intuition' in conceptData && conceptData.one_line_intuition ? (
                    <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50/90 to-violet-50/90 border border-indigo-100 text-indigo-950 shadow-2xs">
                      <div className="flex items-center gap-1.5 text-xs font-black uppercase tracking-wider text-indigo-700 mb-1">
                        <Sparkles className="w-4 h-4 text-indigo-600" />
                        <span>一句话直觉顿悟</span>
                      </div>
                      <p className="text-xs sm:text-sm font-semibold leading-relaxed text-indigo-900">
                        “{conceptData.one_line_intuition}”
                      </p>
                    </div>
                  ) : 'oneLineIntuition' in conceptData && conceptData.oneLineIntuition ? (
                    <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50/90 to-violet-50/90 border border-indigo-100 text-indigo-950 shadow-2xs">
                      <div className="flex items-center gap-1.5 text-xs font-black uppercase tracking-wider text-indigo-700 mb-1">
                        <Sparkles className="w-4 h-4 text-indigo-600" />
                        <span>一句话直觉顿悟</span>
                      </div>
                      <p className="text-xs sm:text-sm font-semibold leading-relaxed text-indigo-900">
                        “{(conceptData as ConceptCardData).oneLineIntuition}”
                      </p>
                    </div>
                  ) : null}

                  {/* 核心概念 */}
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1.5">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700 uppercase tracking-wider">
                      <BookOpen className="w-4 h-4 text-slate-600" />
                      <span>核心机制与关键原理</span>
                    </div>
                    <p className="text-xs sm:text-sm text-slate-700 leading-relaxed whitespace-pre-line">
                      {'core_concept' in conceptData
                        ? conceptData.core_concept
                        : (conceptData as ConceptCardData).coreConcept}
                    </p>
                  </div>

                  {/* 鲜活案例 */}
                  <div className="p-4 rounded-xl bg-amber-50/60 border border-amber-200/70 space-y-1.5">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-amber-800 uppercase tracking-wider">
                      <Lightbulb className="w-4 h-4 text-amber-600" />
                      <span>鲜活现实案例</span>
                    </div>
                    <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
                      {'simple_example' in conceptData
                        ? conceptData.simple_example
                        : (conceptData as ConceptCardData).simpleExample}
                    </p>
                  </div>

                  {/* 避坑指南 */}
                  <div className="p-4 rounded-xl bg-rose-50/60 border border-rose-200/70 space-y-1.5">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-rose-700 uppercase tracking-wider">
                      <AlertTriangle className="w-4 h-4 text-rose-600" />
                      <span>考试易错陷阱避坑</span>
                    </div>
                    <p className="text-xs sm:text-sm text-rose-900 leading-relaxed">
                      {'common_misconceptions' in conceptData
                        ? conceptData.common_misconceptions
                        : (conceptData as ConceptCardData).commonMisconceptions}
                    </p>
                  </div>

                  {/* 掌握度标准 */}
                  <div className="p-3.5 rounded-xl bg-emerald-50/60 border border-emerald-200/70 flex items-start gap-2 text-xs text-emerald-900">
                    <Target className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                    <div>
                      <span className="font-bold">掌握度达成标准：</span>
                      <span>
                        {'learning_objective' in conceptData
                          ? conceptData.learning_objective
                          : (conceptData as ConceptCardData).learningObjective}
                      </span>
                    </div>
                  </div>

                  {/* 步骤控制：主 CTA 为开始小测验，次 CTA 为看看学习资源 */}
                  <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3">
                    <button
                      type="button"
                      data-testid="concept-view-resources-btn"
                      onClick={handleOpenResourceStep}
                      className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs sm:text-sm font-semibold transition-colors cursor-pointer min-h-[44px]"
                    >
                      <Layers className="w-4 h-4 text-slate-500" />
                      <span>看看学习资源 (可选)</span>
                    </button>

                    <div className="flex items-center gap-2.5 w-full sm:w-auto">
                      <button
                        type="button"
                        onClick={() => setCurrentStep('ENTRY')}
                        className="px-3 py-2.5 rounded-xl text-slate-500 hover:bg-slate-100 text-xs font-medium transition-colors cursor-pointer min-h-[44px]"
                      >
                        返回导引
                      </button>
                      <button
                        type="button"
                        data-testid="concept-start-quiz-btn"
                        onClick={handleStartQuizStep}
                        className="flex-1 sm:flex-none px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white text-xs sm:text-sm font-bold shadow-md shadow-indigo-500/20 flex items-center justify-center gap-2 transition-all cursor-pointer min-h-[44px]"
                      >
                        <span>开始小测验</span>
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </>
              ) : null}
            </div>
          )}

          {/* --------------------------------------------------------------- */}
          {/* STEP 3: RESOURCE 学习资源步骤 (可选增强路径) */}
          {/* --------------------------------------------------------------- */}
          {currentStep === 'RESOURCE' && (
            <div data-testid="session-step-resource" className="space-y-4 animate-in fade-in duration-200">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <div>
                  <h4 className="text-sm font-bold text-slate-900">学习资源</h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    挑选适合你的材料深入阅读或观看（可选增强，可随时开始小测验）。
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setCurrentStep('CONCEPT')}
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 cursor-pointer"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>返回概念微卡</span>
                </button>
              </div>

              {/* A. 为你推荐 (AI Recommendation, 可选增强能力) */}
              <div
                data-testid="personalized-rec-section"
                className="p-4 rounded-2xl bg-gradient-to-br from-indigo-50/70 via-white to-purple-50/40 border border-indigo-100 space-y-3"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-xl bg-indigo-600 text-white shadow-2xs shrink-0">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h5 data-testid="personalized-rec-title" className="text-xs sm:text-sm font-bold text-slate-900">
                      为你推荐
                    </h5>
                    <p data-testid="personalized-rec-subtitle" className="text-[11px] sm:text-xs text-slate-600">
                      根据你当前的学习情况，为你挑选了几份可能有帮助的材料。
                    </p>
                  </div>
                </div>

                {isPersonalRecLoading ? (
                  <div
                    data-testid="personalized-rec-loading"
                    className="py-4 px-3 flex items-center justify-center gap-2 text-xs text-slate-500 bg-white/80 rounded-xl border border-indigo-50"
                  >
                    <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                    <span>正在为你挑选学习材料…</span>
                  </div>
                ) : personalRecError ? (
                  <div
                    data-testid="personalized-rec-error"
                    className="py-3 px-3.5 rounded-xl bg-slate-50/80 border border-slate-200 text-xs text-slate-500 text-center"
                  >
                    <span>暂时无法生成个性化推荐，你仍然可以使用下方的精选学习资源。</span>
                  </div>
                ) : deduplicatedPersonalRecs.length === 0 ? (
                  <div
                    data-testid="personalized-rec-empty"
                    className="py-3 px-3.5 rounded-xl bg-slate-50/80 border border-slate-200 text-xs text-slate-500 text-center"
                  >
                    <span>暂时没有找到额外的个性化推荐，下方是该考点的精选学习资源。</span>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {deduplicatedPersonalRecs.map((rec) => {
                      const isMooc = rec.source === 'china_mooc';
                      return (
                        <div
                          key={rec.resource_id}
                          data-testid="personalized-rec-card"
                          className="flex flex-col justify-between bg-white rounded-xl border border-indigo-100 p-3 shadow-2xs hover:shadow-xs transition-shadow space-y-2.5"
                        >
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between gap-1.5">
                              <span
                                data-testid="rec-type-badge"
                                className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-100"
                              >
                                {rec.resource_type === 'VIDEO'
                                  ? '导学视频'
                                  : rec.resource_type === 'DOCUMENT'
                                  ? '精讲讲义'
                                  : rec.resource_type === 'CONCEPT_CARD'
                                  ? '考点微卡'
                                  : rec.resource_type === 'EXAMPLE'
                                  ? '典型例题'
                                  : '学习材料'}
                              </span>
                              <span
                                data-testid="rec-source-badge"
                                className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${
                                  isMooc
                                    ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                    : 'bg-slate-100 text-slate-700'
                                }`}
                              >
                                {isMooc ? '中国大学 MOOC' : '学海智导'}
                              </span>
                            </div>
                            <h6 data-testid="rec-card-title" className="text-xs font-bold text-slate-900 line-clamp-1 leading-snug">
                              {rec.title}
                            </h6>
                            <div data-testid="rec-reason-box" className="p-2 rounded-lg bg-slate-50 border border-slate-100 text-left">
                              <div className="text-[10px] font-bold text-slate-600 mb-0.5 flex items-center gap-1">
                                <span>💡 为什么推荐</span>
                              </div>
                              <p data-testid="rec-reason-text" className="text-[11px] text-slate-700 leading-relaxed font-medium">
                                {rec.reason}
                              </p>
                            </div>
                          </div>

                          <button
                            type="button"
                            data-testid="rec-action-btn"
                            onClick={() => handleOpenRecommendedResource(rec)}
                            className={`w-full inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-bold text-white transition-all shadow-2xs cursor-pointer min-h-[44px] ${
                              isMooc
                                ? 'bg-rose-600 hover:bg-rose-700 active:scale-98'
                                : 'bg-indigo-600 hover:bg-indigo-700 active:scale-98'
                            }`}
                          >
                            <span>{isMooc ? '前往慕课学习' : '在平台学习'}</span>
                            {isMooc ? <ExternalLink className="w-3.5 h-3.5" /> : <ArrowRight className="w-3.5 h-3.5" />}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* B. 精选学习资源 (Deterministic Baseline 确定性兜底) */}
              <div className="space-y-2.5 pt-1">
                <div className="flex items-center justify-between">
                  <h5 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
                    <span>精选学习资源</span>
                  </h5>
                  <span className="text-[11px] text-slate-400">平台权威收录</span>
                </div>

                {isResourceLoading ? (
                  <div className="py-8 flex flex-col items-center justify-center text-center space-y-2">
                    <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
                    <p className="text-xs text-slate-500">正在加载精选资源...</p>
                  </div>
                ) : resourceError ? (
                  // 关键：Resource 500 异常降级，绝不阻断学习主链路
                  <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200 text-center space-y-2.5">
                    <div className="text-xs font-bold text-amber-900">暂时无法加载精选学习资源</div>
                    <p className="text-xs text-amber-700">
                      网络扩展资源加载异常，但这不会影响你的学习进度，你可以直接开始小测验。
                    </p>
                    <button
                      type="button"
                      data-testid="resource-fallback-start-quiz-btn"
                      onClick={handleStartQuizStep}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-xs cursor-pointer min-h-[44px]"
                    >
                      <span>直接开始小测验</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {baselineTopResources.map((res) => (
                      <div
                        key={res.resource_id}
                        className="p-3 rounded-xl border border-slate-200 bg-white hover:border-indigo-200 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-2.5"
                      >
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-1.5">
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                              {res.resource_type === 'VIDEO'
                                ? '导学视频'
                                : res.resource_type === 'DOCUMENT'
                                ? '精讲讲义'
                                : res.resource_type === 'EXAMPLE'
                                ? '典型例题'
                                : '学习材料'}
                            </span>
                            {res.is_external && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                中国大学 MOOC
                              </span>
                            )}
                          </div>
                          <h6 className="text-xs font-bold text-slate-800">{res.title}</h6>
                          <p className="text-[11px] text-slate-500 line-clamp-1">{res.description}</p>
                        </div>

                        {res.is_external ? (
                          <button
                            type="button"
                            data-testid={`mooc-external-btn-${res.resource_id}`}
                            onClick={() => setActiveMoocResource(res)}
                            className="shrink-0 inline-flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 transition-colors cursor-pointer min-h-[44px]"
                          >
                            <span>前往慕课学习</span>
                            <ExternalLink className="w-3.5 h-3.5" />
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => {
                              recordResourceEvent({
                                student_id: studentId,
                                resource_id: res.resource_id,
                                knowledge_id: activeKid,
                                event_type: 'RESOURCE_OPEN',
                              }).catch(() => {});
                            }}
                            className="shrink-0 inline-flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors cursor-pointer min-h-[44px]"
                          >
                            <span>在平台学习</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* C. 底部操作栏 (主链小测验永远畅通可用) */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setCurrentStep('CONCEPT')}
                  className="px-3 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 cursor-pointer min-h-[44px]"
                >
                  返回概念微卡
                </button>
                <button
                  type="button"
                  data-testid="resource-step-start-quiz-btn"
                  onClick={handleStartQuizStep}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-bold shadow-xs flex items-center gap-1.5 cursor-pointer min-h-[44px]"
                >
                  <span>开始小测验</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* --------------------------------------------------------------- */}
          {/* STEP 4: QUIZ 随堂小测步骤 */}
          {/* --------------------------------------------------------------- */}
          {currentStep === 'QUIZ' && (
            <div data-testid="session-step-quiz" className="space-y-4 animate-in fade-in duration-200">
              {isQuizLoading ? (
                <div className="py-12 flex flex-col items-center justify-center text-center space-y-2.5">
                  <Loader2 className="w-7 h-7 animate-spin text-indigo-600" />
                  <p className="text-xs font-semibold text-slate-500">正在获取随堂微测试题...</p>
                </div>
              ) : quizLoadError ? (
                <div className="py-8 px-4 flex flex-col items-center justify-center text-center space-y-3.5">
                  <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center">
                    <AlertCircle className="w-6 h-6" />
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-sm font-bold text-slate-900">小测验暂时无法加载</h4>
                    <p className="text-xs text-rose-600 leading-relaxed">{quizLoadError}</p>
                  </div>
                  <div className="flex gap-2.5">
                    <button
                      type="button"
                      data-testid="quiz-retry-btn"
                      onClick={() => loadQuiz(activeKid)}
                      className="py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-xs transition-colors cursor-pointer min-h-[44px]"
                    >
                      重新加载
                    </button>
                    <button
                      type="button"
                      onClick={() => setCurrentStep('CONCEPT')}
                      className="py-2.5 px-4 rounded-xl border border-slate-200 text-slate-700 font-semibold text-xs hover:bg-slate-50 transition-colors cursor-pointer min-h-[44px]"
                    >
                      返回概念微卡
                    </button>
                  </div>
                </div>
              ) : quizQuestions.length > 0 ? (
                (() => {
                  const q = quizQuestions[currentQuestionIndex];
                  if (!q) return null;
                  const isFeedback = !!currentFeedback;
                  const isLast = currentQuestionIndex === quizQuestions.length - 1;

                  return (
                    <div className="space-y-4">
                      {/* 题目进度与小标签 */}
                      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                        <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider">
                          小测验 · 第 {currentQuestionIndex + 1} 题 / {quizQuestions.length}
                        </span>
                        <span className="text-xs text-amber-500 font-mono">
                          {'★'.repeat(q.difficulty || 1)}
                        </span>
                      </div>

                      {/* 题干 */}
                      <div className="p-3.5 bg-slate-50/90 rounded-2xl border border-slate-200/80">
                        <p className="text-xs sm:text-sm font-semibold text-slate-900 leading-relaxed whitespace-pre-line">
                          {q.stem}
                        </p>
                      </div>

                      {/* 选项列表 (触控靶点高度 >= 48px) */}
                      <div className="space-y-2.5">
                        {q.options.map((opt) => {
                          const isSelected = selectedOption === opt.key;
                          let style =
                            'bg-white border-slate-200 text-slate-800 hover:border-indigo-300 hover:bg-slate-50/60';

                          if (isFeedback) {
                            if (currentFeedback.correct_option === opt.key) {
                              style =
                                'bg-emerald-50/90 border-emerald-500 text-emerald-950 font-bold ring-2 ring-emerald-200';
                            } else if (isSelected && !currentFeedback.is_correct) {
                              style = 'bg-rose-50/90 border-rose-500 text-rose-950 line-through opacity-80';
                            } else {
                              style = 'bg-white border-slate-200 text-slate-400 opacity-60';
                            }
                          } else if (isSelected) {
                            style =
                              'bg-indigo-50 border-indigo-600 text-indigo-950 font-bold ring-2 ring-indigo-200 shadow-xs';
                          }

                          return (
                            <button
                              key={opt.key}
                              type="button"
                              disabled={isFeedback || isSubmitting}
                              onClick={() => handleOptionSelect(opt.key)}
                              className={`w-full text-left p-3.5 rounded-xl border transition-all flex items-start gap-3 min-h-[48px] cursor-pointer disabled:cursor-default ${style}`}
                            >
                              <div
                                className={`w-6 h-6 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 transition-colors ${
                                  isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'
                                }`}
                              >
                                {opt.key}
                              </div>
                              <div className="text-xs sm:text-sm leading-relaxed flex-1 mt-0.5">
                                {opt.text}
                              </div>
                            </button>
                          );
                        })}
                      </div>

                      {/* 即时反馈区：人本正误与解析详解，绝对无技术黑话 */}
                      {isFeedback && currentFeedback && (
                        <div
                          aria-live="polite"
                          data-testid="quiz-feedback-box"
                          className={`p-4 rounded-2xl border space-y-2.5 animate-in fade-in duration-200 ${
                            currentFeedback.is_correct
                              ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
                              : 'bg-rose-50/70 border-rose-200 text-rose-950'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              {currentFeedback.is_correct ? (
                                <>
                                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                                  <span className="text-xs sm:text-sm font-black text-emerald-900">
                                    ✓ 回答正确
                                  </span>
                                </>
                              ) : (
                                <>
                                  <XCircle className="w-5 h-5 text-rose-600 shrink-0" />
                                  <span className="text-xs sm:text-sm font-black text-rose-900">
                                    这道题还需要再想一想
                                  </span>
                                </>
                              )}
                            </div>
                            <div className="text-xs font-bold text-slate-700">
                              正确答案：
                              <span className="text-emerald-700 font-black ml-1">
                                {currentFeedback.correct_option}
                              </span>
                            </div>
                          </div>

                          <div className="pt-2 border-t border-slate-200/50 text-xs text-slate-700 leading-relaxed">
                            <span className="font-bold text-slate-900">【解析详解】</span>
                            <p className="mt-1 whitespace-pre-line">{currentFeedback.explanation}</p>
                          </div>
                        </div>
                      )}

                      {/* 提交报错提示 */}
                      {submitError && (
                        <div
                          data-testid="quiz-submit-error-box"
                          className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2"
                        >
                          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                          <span>{submitError}</span>
                        </div>
                      )}

                      {/* 底部交互控制按钮 */}
                      <div className="pt-2">
                        {!isFeedback ? (
                          <button
                            type="button"
                            data-testid="quiz-submit-btn"
                            disabled={!selectedOption || isSubmitting}
                            onClick={handleSubmitAnswer}
                            className="w-full py-3.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed text-white font-bold text-xs sm:text-sm shadow-xs flex items-center justify-center gap-2 transition-all cursor-pointer min-h-[44px]"
                          >
                            {isSubmitting ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span>正在判题中...</span>
                              </>
                            ) : (
                              <span>提交答案</span>
                            )}
                          </button>
                        ) : (
                          <button
                            type="button"
                            data-testid="quiz-next-btn"
                            onClick={handleNextQuestion}
                            className="w-full py-3.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs sm:text-sm shadow-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer min-h-[44px]"
                          >
                            <span>{isLast ? '查看本次测验结果' : '下一题'}</span>
                            <ArrowRight className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })()
              ) : null}
            </div>
          )}

          {/* --------------------------------------------------------------- */}
          {/* STEP 5: RESULT 成果结算与下一步行动 */}
          {/* --------------------------------------------------------------- */}
          {currentStep === 'RESULT' && (
            <div data-testid="session-step-result" className="space-y-5 animate-in fade-in duration-200">
              {/* 顶部荣誉徽标与完成卡 */}
              <div
                className={`p-5 rounded-2xl border text-center space-y-2 ${
                  accuracyPercent >= 60
                    ? 'bg-emerald-50/80 border-emerald-200 text-emerald-950'
                    : 'bg-amber-50/80 border-amber-200 text-amber-950'
                }`}
              >
                <div
                  className={`w-12 h-12 mx-auto rounded-2xl flex items-center justify-center ${
                    accuracyPercent >= 60
                      ? 'bg-emerald-100 text-emerald-600'
                      : 'bg-amber-100 text-amber-600'
                  }`}
                >
                  <Award className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="text-lg font-black">本次练习完成</h4>
                  <p className="text-xs opacity-80 mt-0.5">
                    已顺利完成「{displayKpName}」随堂测验评估
                  </p>
                </div>
              </div>

              {/* 核心指标网格：权威正确率、题数、重新读取的权威掌握度 */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
                  <div className="text-xs text-slate-500 font-medium">答对题数</div>
                  <div
                    data-testid="result-correct-count"
                    className="text-xl font-black text-slate-900 mt-0.5"
                  >
                    {correctCount} / {totalQuestions} 正确
                  </div>
                </div>

                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-center">
                  <div className="text-xs text-slate-500 font-medium">本次正确率</div>
                  <div
                    data-testid="result-accuracy"
                    className={`text-xl font-black mt-0.5 ${
                      accuracyPercent >= 60 ? 'text-emerald-600' : 'text-rose-600'
                    }`}
                  >
                    {accuracyPercent}%
                  </div>
                </div>

                <div className="col-span-2 sm:col-span-1 p-3.5 bg-indigo-50/80 rounded-xl border border-indigo-200 text-center">
                  <div className="text-xs text-indigo-700 font-bold">当前掌握度</div>
                  <div
                    data-testid="result-mastery-display"
                    className="text-xl font-black text-indigo-700 mt-0.5"
                  >
                    {isMasteryReading ? (
                      <Loader2 className="w-5 h-5 animate-spin mx-auto text-indigo-600" />
                    ) : authoritativeMastery != null ? (
                      `当前掌握度 ${authoritativeMastery}%`
                    ) : (
                      '读取中...'
                    )}
                  </div>
                </div>
              </div>

              {/* 掌握度读取异常提示与重试 */}
              {masteryReadError && (
                <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 flex items-center justify-between gap-2">
                  <span>{masteryReadError}</span>
                  <button
                    type="button"
                    onClick={() => fetchAuthoritativeMastery(studentId, activeKid)}
                    className="shrink-0 px-2.5 py-1 rounded-lg bg-amber-200 text-amber-900 font-bold text-xs cursor-pointer"
                  >
                    重新查看
                  </button>
                </div>
              )}

              {/* 下一步行动人本建议 */}
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
                <div className="text-xs font-bold text-slate-800">接下来建议：</div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {accuracyPercent === 100
                    ? '全对通关！知识点掌握非常扎实，建议直接继续学习下一个进阶考点。'
                    : accuracyPercent >= 60
                    ? '练习达标！已建立良好认知，可以继续下一步，也可以回顾刚才的错题解析。'
                    : '本轮小测中部分核心机制存在薄弱点，建议重新巩固概念微卡或稍后再练一次。'}
                </p>
              </div>

              {/* 底部导航出口：绝无死胡同 */}
              <div className="pt-2 flex flex-col sm:flex-row items-center gap-2.5">
                <button
                  type="button"
                  data-testid="result-next-action-btn"
                  onClick={handleNextKnowledgeSession}
                  className="w-full sm:flex-1 py-3.5 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-bold text-xs sm:text-sm shadow-md flex items-center justify-center gap-1.5 cursor-pointer min-h-[44px]"
                >
                  <span>继续下一步</span>
                  <ArrowRight className="w-4 h-4" />
                </button>

                <button
                  type="button"
                  data-testid="result-retry-quiz-btn"
                  onClick={handleStartQuizStep}
                  className="w-full sm:w-auto py-3.5 px-4 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs sm:text-sm flex items-center justify-center gap-1.5 cursor-pointer min-h-[44px]"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>再练一次</span>
                </button>

                <button
                  type="button"
                  data-testid="result-back-home-btn"
                  onClick={handleBackHome}
                  className="w-full sm:w-auto py-3.5 px-4 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs sm:text-sm flex items-center justify-center gap-1.5 cursor-pointer min-h-[44px]"
                >
                  <span>返回今日任务</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 中国大学 MOOC 外部安全重定向模态框 (Sprint 10-A 规则) */}
      <ExternalRedirectModal
        resource={activeMoocResource}
        onClose={() => setActiveMoocResource(null)}
        onConfirm={(res) => {
          recordResourceEvent({
            student_id: studentId,
            resource_id: res.resource_id,
            knowledge_id: activeKid,
            event_type: 'RESOURCE_EXTERNAL_OPEN',
          }).catch(() => {});
          if (res.source_url) {
            openExternalMoocUrl(res.source_url);
          }
          setActiveMoocResource(null);
        }}
      />
    </div>
  );
};
