import React, { useState, useEffect, useRef, useCallback } from 'react';
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
} from 'lucide-react';
import {
  postCompanionStudy,
  resetCompanionSession,
} from '../api';
import type {
  CompanionMode,
  CompanionStudyRequest,
  CompanionStudyResponse,
  CompanionContextMetadata,
  LearningContext,
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
  } | null;
  onNavigateToKnowledge?: (knowledgeId: string) => void;
  onNavigateToQuiz?: (knowledgeId: string) => void;
}

interface DisplayMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  mode?: CompanionMode;
  context?: CompanionContextMetadata;
  suggested_actions?: string[];
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
  onNavigateToQuiz,
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

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

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

      try {
        const req: CompanionStudyRequest = {
          student_id: currentStudentId,
          mode,
          knowledge_id: kid,
          question_id: mode === 'wrong_answer_review' ? qid : undefined,
          message: userText || undefined,
          session_id: sessionId || undefined,
        };

        const res: CompanionStudyResponse = await postCompanionStudy(req);

        setSessionId(res.session_id);
        setActiveContextMeta(res.context);
        if (res.context.knowledge_id) {
          setActiveKnowledgeId(res.context.knowledge_id);
        }

        const assistantDisplayMsg: DisplayMessage = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: res.answer,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          mode: res.mode,
          context: res.context,
          suggested_actions: res.suggested_actions,
          referenced_facts: res.referenced_facts,
        };

        setMessages((prev) => [...prev, assistantDisplayMsg]);
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
    // 取消可能正在进行的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    setMessages([]);
    setSessionId(null);
    setErrorMsg(null);
    setActiveContextMeta(null);

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
  }, [currentStudentId]); // 仅当学生切换时触发完整重置

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

  // 点击建议行动
  const handleActionClick = (actionText: string) => {
    if (actionText.includes('微测验') && onNavigateToQuiz && activeKnowledgeId) {
      onNavigateToQuiz(activeKnowledgeId);
      return;
    }
    executeCompanionRequest('conversation', `请导师深入指导：${actionText}`);
  };

  // 重置当前会话
  const handleResetSession = async () => {
    if (isLoading) return;
    try {
      await resetCompanionSession(currentStudentId);
      setMessages([]);
      setSessionId(null);
      setErrorMsg(null);
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
    <div className="flex flex-col h-[750px] bg-slate-50 border border-slate-200 rounded-3xl overflow-hidden shadow-sm" data-testid="ai-companion-assistant">
      {/* 顶部状态与安全隔离声明栏 */}
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white flex items-center justify-center shadow-md shadow-indigo-200">
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

        {/* 安全边界标签与重置按钮 */}
        <div className="flex items-center gap-2.5">
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
                    : 'bg-gradient-to-tr from-indigo-600 to-purple-600 text-white'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* 消息体 */}
              <div className={`max-w-[85%] space-y-2.5 ${isUser ? 'items-end' : 'items-start'}`}>
                <div
                  className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                    isUser
                      ? 'bg-slate-900 text-white rounded-tr-none'
                      : 'bg-white text-slate-800 border border-slate-200/90 shadow-xs rounded-tl-none space-y-3'
                  }`}
                >
                  {/* 消息正文 */}
                  <div className="whitespace-pre-wrap font-sans">
                    {msg.content}
                  </div>

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

                {/* 导师建议的下一步动作标签 */}
                {!isUser && msg.suggested_actions && msg.suggested_actions.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <span className="text-[11px] text-slate-400 font-medium">建议行动：</span>
                    {msg.suggested_actions.map((action, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleActionClick(action)}
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
      <div className="p-4 bg-white border-t border-slate-200">
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
                : 'border-slate-200 focus:ring-indigo-500 focus:border-transparent bg-slate-50/50'
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
