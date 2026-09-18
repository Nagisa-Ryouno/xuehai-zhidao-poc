import React, { useState, useEffect, useRef, useCallback } from 'react';
import { playSound } from '../soundService';
import {
  Bot,
  Sparkles,
  Send,
  User,
  AlertCircle,
  RotateCcw,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Compass,
  ArrowRight,
  BookOpen,
  Target,
  TrendingUp,
  RotateCw,
  Lightbulb,
} from 'lucide-react';
import {
  postCompanionStudy,
  resetCompanionSession,
  getQuickCheck,
  submitQuickCheck,
  recordLearningEvent,
} from '../api';
import type {
  CompanionMode,
  CompanionStudyRequest,
  CompanionStudyResponse,
  CompanionContextMetadata,
  LearningContext,
  CompanionSuggestedAction,
  QuickCheckQuestion,
  QuickCheckResponse,
  LearningActionResultResponse,
} from '../types';

interface AIAssistantProps {
  currentStudentId: string;
  studentName: string;
  isOnline: boolean;
  learningContext?: LearningContext;
  initialContext?: {
    mode?: CompanionMode;
    knowledgeId?: string;
    questionId?: string;
    message?: string;
    resourceContext?: Record<string, any>;
  } | null;
  latestActionResult?: LearningActionResultResponse | null;
  onNavigateToKnowledge?: (knowledgeId: string) => void;
  onNavigateToQuiz?: (knowledgeId: string) => void;
  onNavigateToConcept?: (knowledgeId: string) => void;
  onNavigateToProgress?: () => void;
  onNavigateToWrongAnswers?: () => void;
}

interface DisplayMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  mode?: CompanionMode;
  context?: CompanionContextMetadata;
  suggested_actions?: string[];
  guided_actions?: CompanionSuggestedAction[];
  quick_check?: QuickCheckQuestion;
  action_result?: LearningActionResultResponse;
  referenced_facts?: string[];
}

const MODE_CONFIGS: Record<
  CompanionMode,
  { label: string; icon: string; description: string; defaultMsg: string }
> = {
  concept_explain: {
    label: '概念精讲',
    icon: '📖',
    description: '深入剖析核心考点直观理解、现实案例与考试易错陷阱',
    defaultMsg: '请老师为我精讲当前核心考点',
  },
  wrong_answer_review: {
    label: '错题剖析',
    icon: '🔍',
    description: '依据题库权威解析，定位认知盲区并启发式复盘',
    defaultMsg: '请老师帮我分析这道错题的思维误区',
  },
  learning_summary: {
    label: '阶段总结',
    icon: '📊',
    description: '全景评估 30 考点掌握分布与下阶段自适应攻坚方向',
    defaultMsg: '请老师为我生成当前的阶段学情全景导师分析',
  },
  conversation: {
    label: '自由探讨',
    icon: '💬',
    description: '针对微观经济学疑难问题进行启发式多轮互动交流',
    defaultMsg: '',
  },
};

export const AIAssistant: React.FC<AIAssistantProps> = ({
  currentStudentId,
  studentName,
  isOnline,
  initialContext,
  latestActionResult,
  onNavigateToKnowledge,
  onNavigateToQuiz,
  onNavigateToConcept,
  onNavigateToProgress,
  onNavigateToWrongAnswers,
}) => {
  const [activeMode, setActiveMode] = useState<CompanionMode>(
    initialContext?.mode || 'concept_explain'
  );
  const [activeKnowledgeId, setActiveKnowledgeId] = useState<string>(
    initialContext?.knowledgeId || 'K01'
  );
  const [activeQuestionId, setActiveQuestionId] = useState<string>(
    initialContext?.questionId || 'Q-K01-01'
  );

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [inputMessage, setInputMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeContextMeta, setActiveContextMeta] = useState<CompanionContextMetadata | null>(null);
  const [showFactsMap, setShowFactsMap] = useState<Record<string, boolean>>({});

  // Quick Check 交互状态
  const [quickCheckAnswers, setQuickCheckAnswers] = useState<Record<string, QuickCheckResponse>>({});
  const [submittingQcId, setSubmittingQcId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // 监听外部学习行动完成 (如 Quiz 完成、微卡完成)
  useEffect(() => {
    if (latestActionResult) {
      const reflectionMsg: DisplayMessage = {
        id: `reflection-${Date.now()}`,
        role: 'assistant',
        content: latestActionResult.reflection_text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        action_result: latestActionResult,
        guided_actions: latestActionResult.next_actions,
      };
      setMessages((prev) => [...prev, reflectionMsg]);
    }
  }, [latestActionResult]);

  // 发起伴学请求核心流程
  const executeCompanionRequest = useCallback(
    async (
      mode: CompanionMode,
      userText?: string,
      targetKid?: string,
      targetQid?: string
    ) => {
      if (isLoading) return;

      const kid = targetKid || activeKnowledgeId || 'K01';
      const qid = targetQid || activeQuestionId || 'Q-K01-01';

      // 文本长度防线 (2000 字符硬约束)
      if (userText && userText.length > 2000) {
        setErrorMsg('提问内容超过最大允许限制 (2000 字符)，请精简后重试。');
        return;
      }

      setErrorMsg(null);
      setIsLoading(true);

      const userDisplayMsg: DisplayMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: userText || MODE_CONFIGS[mode].defaultMsg,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        mode,
      };
      setMessages((prev) => [...prev, userDisplayMsg]);
      playSound('send');

      try {
        const req: CompanionStudyRequest = {
          student_id: currentStudentId,
          mode,
          knowledge_id: kid,
          question_id: mode === 'wrong_answer_review' ? qid : undefined,
          message: userText || undefined,
          session_id: sessionId || undefined,
          resource_context: initialContext?.resourceContext || undefined,
        };

        const res: CompanionStudyResponse = await postCompanionStudy(req);

        setSessionId(res.session_id);
        setActiveContextMeta(res.context);
        if (res.context.knowledge_id) {
          setActiveKnowledgeId(res.context.knowledge_id);
        }

        const assistantDisplayMsg: DisplayMessage = {
          id: `ai-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
          role: 'assistant',
          content: res.answer,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          mode: res.mode,
          context: res.context,
          suggested_actions: res.suggested_actions,
          guided_actions: res.guided_actions,
          quick_check: res.quick_check,
          referenced_facts: res.referenced_facts,
        };

        setMessages((prev) => [...prev, assistantDisplayMsg]);
        playSound('notification');
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : '伴学服务暂时无响应，请重试';
        setErrorMsg(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [currentStudentId, activeKnowledgeId, activeQuestionId, sessionId, isLoading]
  );

  // 初始化或切换学生时：彻底隔离状态，清空历史，并加载首发精讲
  useEffect(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    setMessages([]);
    setSessionId(null);
    setErrorMsg(null);
    setActiveContextMeta(null);
    setQuickCheckAnswers({});

    const initialMode = initialContext?.mode || 'concept_explain';
    const initialKid = initialContext?.knowledgeId || 'K01';
    const initialQid = initialContext?.questionId || 'Q-K01-01';

    setActiveMode(initialMode);
    setActiveKnowledgeId(initialKid);
    setActiveQuestionId(initialQid);

    // 自动发起初始教学
    executeCompanionRequest(
      initialMode,
      initialContext?.message,
      initialKid,
      initialQid
    );

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [currentStudentId]);

  // 监听外部学习行动结果（微测验提交/概念微卡学习），即时生成导师反思与闭环反馈
  useEffect(() => {
    if (!latestActionResult) return;
    const reflText = latestActionResult.reflection_text || latestActionResult.reflection || '';
    const newMsg: DisplayMessage = {
      id: `act-res-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      role: 'assistant',
      content: reflText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      mode: activeMode,
      action_result: latestActionResult,
      guided_actions: latestActionResult.next_actions || latestActionResult.guided_actions,
    };
    setMessages((prev) => [...prev, newMsg]);
    setTimeout(scrollToBottom, 100);
  }, [latestActionResult]);

  // 模式切换
  const handleModeChange = (newMode: CompanionMode) => {
    if (newMode === activeMode || isLoading) return;
    setActiveMode(newMode);
    executeCompanionRequest(newMode);
  };

  // 手工发送消息
  const handleSendMessage = () => {
    const text = inputMessage.trim();
    if (!text || isLoading || text.length > 2000) return;
    setInputMessage('');
    executeCompanionRequest(activeMode, text);
  };

  // 点击确定性引导行动 (Sprint 9-B 核心闭环)
  const handleGuidedActionClick = (action: CompanionSuggestedAction) => {
    // 异步记录引导行动点击辅助事件 (零生产副作用)
    recordLearningEvent({
      student_id: currentStudentId,
      event_type: 'AI_ACTION_CLICK',
      knowledge_id: action.target_knowledge_id || activeKnowledgeId,
      payload: {
        action_id: action.action_id,
        action_type: action.action_type,
        route_destination: action.route_destination,
      },
    }).catch(() => {});

    switch (action.action_type) {
      case 'READ_CONCEPT':
        if (onNavigateToConcept) {
          onNavigateToConcept(action.target_knowledge_id || activeKnowledgeId);
        } else if (onNavigateToKnowledge) {
          onNavigateToKnowledge(action.target_knowledge_id || activeKnowledgeId);
        }
        break;
      case 'TARGETED_PRACTICE':
        if (onNavigateToQuiz) {
          onNavigateToQuiz(action.target_knowledge_id || activeKnowledgeId);
        }
        break;
      case 'VIEW_PROGRESS':
        if (onNavigateToProgress) {
          onNavigateToProgress();
        }
        break;
      case 'REVIEW_WRONG_ANSWERS':
        if (onNavigateToWrongAnswers) {
          onNavigateToWrongAnswers();
        }
        break;
      case 'CONTINUE_DISCUSSION':
      default:
        executeCompanionRequest('conversation', action.description || action.title);
        break;
    }
  };

  // 兼容老版本的简单行动点击
  const handleLegacyActionClick = (actionText: string) => {
    if (actionText.includes('微测验') && onNavigateToQuiz && activeKnowledgeId) {
      onNavigateToQuiz(activeKnowledgeId);
      return;
    }
    if (actionText.includes('微卡') && onNavigateToConcept && activeKnowledgeId) {
      onNavigateToConcept(activeKnowledgeId);
      return;
    }
    executeCompanionRequest('conversation', `请导师深入指导：${actionText}`);
  };

  // 提交微理解测验 (Quick Check)
  const handleSelectQuickCheckOption = async (
    question: QuickCheckQuestion,
    selectedOptionId: string
  ) => {
    if (submittingQcId || quickCheckAnswers[question.question_id]) return;
    setSubmittingQcId(question.question_id);
    try {
      const res = await submitQuickCheck({
        student_id: currentStudentId,
        knowledge_id: question.knowledge_id,
        question_id: question.question_id,
        selected_option: selectedOptionId,
      });
      setQuickCheckAnswers((prev) => ({
        ...prev,
        [question.question_id]: res,
      }));
    } catch (err) {
      console.error('Quick check submit failed:', err);
    } finally {
      setSubmittingQcId(null);
    }
  };

  // 手工调出微理解自测题
  const handleTriggerQuickCheck = async () => {
    if (isLoading) return;
    setIsLoading(true);
    try {
      const qc = await getQuickCheck(activeKnowledgeId);
      const qcMsg: DisplayMessage = {
        id: `qc-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        role: 'assistant',
        content: `针对「${activeContextMeta?.knowledge_name || activeKnowledgeId}」，导师为你准备了一道微理解自测题（本测验为纯理解自测，零生产副作用，不写入正式档案与成绩）：`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        mode: 'concept_explain',
        quick_check: qc,
      };
      setMessages((prev) => [...prev, qcMsg]);
    } catch {
      setErrorMsg('获取微理解检测题失败，请检查网络后重试');
    } finally {
      setIsLoading(false);
    }
  };

  // 重置当前会话
  const handleResetSession = async () => {
    if (isLoading) return;
    try {
      await resetCompanionSession(currentStudentId);
      setMessages([]);
      setSessionId(null);
      setErrorMsg(null);
      setQuickCheckAnswers({});
      executeCompanionRequest(activeMode, '老师好，我们重新开始讨论。');
    } catch {
      setMessages([]);
    }
  };

  // 切换事实展开收起
  const toggleFact = (msgId: string) => {
    setShowFactsMap((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const isOverLimit = inputMessage.length > 2000;

  return (
    <div className="flex flex-col h-[780px] glass-card rounded-3xl overflow-hidden" data-testid="ai-companion-assistant">
      {/* 顶部状态与安全隔离声明栏 */}
      <div className="bg-[rgba(255,252,248,.6)] backdrop-blur-xl border-b border-white/75 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-[#F2764A] to-[#E2573F] text-white flex items-center justify-center shadow-md shadow-orange-300/40 orb-ring animate-float">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-900 text-base">AI 伴学专属导师</h3>
              <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/60">
                <Sparkles className="w-3 h-3" />
                {studentName} 同学专属
              </span>
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-slate-500">
                当前考点：
                <strong className="text-slate-800 ml-1">
                  {activeContextMeta?.knowledge_id || activeKnowledgeId} {activeContextMeta?.knowledge_name || ''}
                </strong>
              </span>
              {activeContextMeta?.mastery_status && (
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-amber-50 text-amber-800 border border-amber-200">
                  {activeContextMeta.mastery_status}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* 顶部快捷操作与状态标签 */}
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={handleTriggerQuickCheck}
            disabled={isLoading}
            className="hidden sm:flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors cursor-pointer disabled:opacity-50"
            title="调出当前知识点的即时微理解自测题"
            data-testid="trigger-quick-check-btn"
          >
            <Lightbulb className="w-3.5 h-3.5 text-indigo-600" />
            <span>考点微检验</span>
          </button>

          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
            <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>{isOnline ? '伴学导师在线' : '离线确定性保障'} · 零生产副作用</span>
          </div>

          <button
            type="button"
            onClick={handleResetSession}
            disabled={isLoading}
            className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 transition-colors cursor-pointer disabled:opacity-50"
            title="清空当前对话历史"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>新话题</span>
          </button>
        </div>
      </div>

      {/* 4 种辅导模式切换药丸栏 */}
      <div className="bg-slate-100/90 border-b border-slate-200 px-6 py-2.5 flex items-center gap-2 overflow-x-auto no-scrollbar">
        {(Object.keys(MODE_CONFIGS) as CompanionMode[]).map((mode) => {
          const cfg = MODE_CONFIGS[mode];
          const isActive = activeMode === mode;
          return (
            <button
              key={mode}
              type="button"
              onClick={() => handleModeChange(mode)}
              disabled={isLoading}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap shrink-0 ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-50 border border-slate-200/80'
              }`}
            >
              <span>{cfg.icon}</span>
              <span>{cfg.label}</span>
            </button>
          );
        })}
        <div className="ml-auto text-[11px] text-slate-400 hidden md:block">
          {MODE_CONFIGS[activeMode].description}
        </div>
      </div>

      {/* 聊天会话消息流 */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          const isFactsOpen = showFactsMap[msg.id];
          const qc = msg.quick_check;
          const qcResult = qc ? quickCheckAnswers[qc.question_id] : undefined;
          const actResult = msg.action_result;

          return (
            <div
              key={msg.id}
              className={`flex gap-3.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
            >
              {/* 头像 */}
              <div
                className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 text-sm font-bold shadow-xs ${
                  isUser
                    ? 'bg-slate-900 text-white'
                    : 'bg-gradient-to-tr from-[#F2764A] to-[#E2573F] text-white'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* 消息体 */}
              <div className={`max-w-[88%] space-y-3 ${isUser ? 'items-end' : 'items-start'}`}>
                {/* 主气泡 */}
                <div
                  className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                    isUser
                      ? 'bg-slate-900 text-white rounded-tr-none'
                      : 'glass-card text-slate-800 rounded-tl-none space-y-3'
                  }`}
                >
                  {/* 消息正文 */}
                  <div className="whitespace-pre-wrap font-sans">
                    {msg.content}
                  </div>

                  {/* 学习行动反思卡片 (Sprint 9-B 闭环结果) */}
                  {actResult && (
                    <div className="p-4 rounded-2xl glass-card space-y-3 mt-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Target className="w-4 h-4 text-indigo-600" />
                          <span className="font-bold text-slate-800 text-xs">
                            学情状态：{actResult.knowledge_name} ({actResult.knowledge_id})
                          </span>
                        </div>
                        <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800">
                          {actResult.mastery_state_text}
                        </span>
                      </div>

                      {/* 掌握度变化指示条 */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs text-slate-600">
                          <span>行动前掌握度：{(actResult.before_mastery * 100).toFixed(1)}%</span>
                          <span>行动后掌握度：<strong className="text-indigo-700">{(actResult.after_mastery * 100).toFixed(1)}%</strong></span>
                        </div>
                        <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${Math.min(100, Math.max(0, actResult.after_mastery * 100))}%` }}
                          />
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-400">
                          <span>
                            净变化：
                            <span className={actResult.mastery_delta >= 0 ? 'text-emerald-600 font-bold' : 'text-rose-600 font-bold'}>
                              {actResult.mastery_delta >= 0 ? `+${(actResult.mastery_delta * 100).toFixed(1)}%` : `${(actResult.mastery_delta * 100).toFixed(1)}%`}
                            </span>
                          </span>
                          {actResult.consecutive_incorrect > 0 && (
                            <span className="text-amber-600">连续未达标: {actResult.consecutive_incorrect} 次</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 导师引用的权威事实依据折叠抽屉 */}
                  {!isUser && msg.referenced_facts && msg.referenced_facts.length > 0 && (
                    <div className="pt-2 border-t border-slate-100">
                      <button
                        type="button"
                        onClick={() => toggleFact(msg.id)}
                        className="inline-flex items-center gap-1.5 text-[11px] font-bold text-indigo-700 hover:text-indigo-900 transition-colors cursor-pointer"
                      >
                        <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
                        <span>引用事实依据 ({msg.referenced_facts.length})</span>
                        {isFactsOpen ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {isFactsOpen && (
                        <div className="mt-2 p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1 text-[11px] text-slate-600">
                          {msg.referenced_facts.map((fact, idx) => (
                            <div key={idx} className="flex items-start gap-1.5">
                              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                              <span>{fact}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* 交互式微理解测验小部件 (Sprint 9-B Quick Check) */}
                {qc && (
                  <div className="p-4 rounded-2xl glass-card space-y-3" data-testid="quick-check-widget">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-purple-900">
                        <Lightbulb className="w-4 h-4 text-purple-600" />
                        <span>考点微理解快速自测</span>
                      </div>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200/60">
                        零生产副作用 · 纯理解自检
                      </span>
                    </div>

                    <p className="text-xs sm:text-sm font-medium text-slate-800 leading-relaxed">
                      {qc.stem}
                    </p>

                    {/* 选项组 */}
                    <div className="space-y-2">
                      {qc.options.map((opt) => {
                        const isAnswered = !!qcResult;
                        const isCorrectOpt = qcResult && opt.id === qcResult.correct_option;

                        let optBtnStyle = 'bg-slate-50 hover:bg-purple-50/50 border-slate-200 text-slate-700';
                        if (isAnswered) {
                          if (isCorrectOpt) {
                            optBtnStyle = 'bg-emerald-50 border-emerald-300 text-emerald-900 font-semibold';
                          } else {
                            optBtnStyle = 'bg-slate-50 border-slate-200 text-slate-400 opacity-80';
                          }
                        }

                        return (
                          <button
                            key={opt.id}
                            type="button"
                            disabled={isAnswered || submittingQcId === qc.question_id}
                            onClick={() => handleSelectQuickCheckOption(qc, opt.id)}
                            className={`w-full text-left p-3 rounded-xl border text-xs sm:text-sm flex items-start gap-2.5 transition-all cursor-pointer disabled:cursor-default ${optBtnStyle}`}
                          >
                            <span className="w-5 h-5 rounded-lg bg-white border border-slate-200 flex items-center justify-center font-bold text-xs shrink-0 shadow-2xs">
                              {opt.id}
                            </span>
                            <span className="flex-1">{opt.text}</span>
                            {isAnswered && isCorrectOpt && (
                              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                            )}
                          </button>
                        );
                      })}
                    </div>

                    {/* 作答反馈结果抽屉 */}
                    {qcResult && (
                      <div className={`p-3.5 rounded-xl border space-y-2 text-xs leading-relaxed ${
                        qcResult.is_correct
                          ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
                          : 'bg-amber-50/80 border-amber-200 text-amber-900'
                      }`}>
                        <div className="flex items-center gap-1.5 font-bold">
                          {qcResult.is_correct ? (
                            <>
                              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                              <span>回答正确！直观理解非常扎实。</span>
                            </>
                          ) : (
                            <>
                              <AlertCircle className="w-4 h-4 text-amber-600" />
                              <span>回答有误，正确答案是 {qcResult.correct_option}。</span>
                            </>
                          )}
                        </div>
                        <p className="text-slate-700">{qcResult.explanation}</p>
                        <div className="pt-1 border-t border-slate-200/50 flex items-center gap-1.5 text-indigo-900 font-medium">
                          <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                          <span>核心要点：{qcResult.key_takeaway}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 导师建议行动组 (Sprint 9-B 结构化引导动作) */}
                {!isUser && msg.guided_actions && msg.guided_actions.length > 0 && (
                  <div className="space-y-1.5 pt-1" data-testid="companion-guided-actions">
                    <div className="text-[11px] text-slate-500 font-semibold flex items-center gap-1">
                      <Compass className="w-3.5 h-3.5 text-indigo-600" />
                      <span>导师建议的下一步确定性行动：</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {msg.guided_actions.map((act) => {
                        let IconComponent = Target;
                        if (act.action_type === 'READ_CONCEPT') IconComponent = BookOpen;
                        if (act.action_type === 'TARGETED_PRACTICE') IconComponent = Target;
                        if (act.action_type === 'VIEW_PROGRESS') IconComponent = TrendingUp;
                        if (act.action_type === 'REVIEW_WRONG_ANSWERS') IconComponent = RotateCw;

                        return (
                          <button
                            key={act.action_id}
                            type="button"
                            onClick={() => handleGuidedActionClick(act)}
                            className="p-3 rounded-2xl glass-card hover:bg-white/70 text-left transition-all duration-300 cursor-pointer group flex flex-col justify-between"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex items-center gap-1.5 font-bold text-xs text-slate-800 group-hover:text-indigo-700">
                                <IconComponent className="w-4 h-4 text-indigo-600 shrink-0" />
                                <span>{act.title}</span>
                              </div>
                              {act.badge && (
                                <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-indigo-50 text-indigo-700 border border-indigo-200 shrink-0">
                                  {act.badge}
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                              {act.description}
                            </p>
                            <div className="mt-2 text-[10px] font-bold text-indigo-600 flex items-center gap-1">
                              <span>立即前往</span>
                              <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 兼容旧版简单建议行动 */}
                {!isUser && (!msg.guided_actions || msg.guided_actions.length === 0) && msg.suggested_actions && msg.suggested_actions.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <span className="text-[11px] text-slate-400 font-medium">建议行动：</span>
                    {msg.suggested_actions.map((action, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleLegacyActionClick(action)}
                        className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 transition-colors cursor-pointer"
                      >
                        {action}
                      </button>
                    ))}
                  </div>
                )}

                <div className={`text-[10px] text-slate-400 px-1 ${isUser ? 'text-right' : 'text-left'}`}>
                  {msg.timestamp}
                </div>
              </div>
            </div>
          );
        })}

        {/* 加载动画 */}
        {isLoading && (
          <div className="flex gap-3.5 items-center text-slate-400 text-xs pl-1">
            <div className="w-8 h-8 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center animate-spin">
              <Sparkles className="w-4 h-4" />
            </div>
            <span>导师正在梳理考点逻辑与事实依据...</span>
          </div>
        )}

        {/* 错误提示卡片 */}
        {errorMsg && (
          <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button
              type="button"
              onClick={() => executeCompanionRequest(activeMode)}
              className="px-3 py-1 bg-rose-600 text-white rounded-lg font-bold hover:bg-rose-700 transition-colors cursor-pointer shrink-0"
            >
              重试
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 底部输入框与字数指示 */}
      <div className="p-4 bg-[rgba(255,252,248,.6)] backdrop-blur-xl border-t border-white/75">
        <div className="relative">
          <textarea
            rows={2}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            placeholder={
              activeMode === 'conversation'
                ? '向导师追问微观经济学逻辑、定理推导或学习困惑...'
                : '输入进一步追问，或直接回车与导师交流...'
            }
            className={`w-full p-3 pr-24 rounded-2xl border text-xs sm:text-sm focus:outline-none focus:ring-2 resize-none transition-all ${
              isOverLimit
                ? 'border-rose-400 focus:ring-rose-400 bg-rose-50/30'
                : 'border-white/80 focus:ring-indigo-500 focus:border-transparent bg-white/60'
            }`}
          />

          {/* 字符计数与发送按钮 */}
          <div className="absolute right-2.5 bottom-3 flex items-center gap-2">
            <span
              className={`text-[11px] font-mono ${
                isOverLimit ? 'text-rose-600 font-bold' : 'text-slate-400'
              }`}
            >
              {inputMessage.length}/2000
            </span>
            <button
              type="button"
              disabled={isLoading || !inputMessage.trim() || isOverLimit}
              onClick={handleSendMessage}
              className="p-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white shadow-xs transition-all cursor-pointer"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>

        {isOverLimit && (
          <p className="text-[11px] text-rose-600 mt-1 pl-1 font-medium">
            提问内容已超过 2000 字符限制，请精简提问后发送。
          </p>
        )}
      </div>
    </div>
  );
};
