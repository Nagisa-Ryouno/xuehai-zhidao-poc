import React, { useState, useEffect, useRef } from 'react';
import {
  Bot,
  Sparkles,
  Send,
  User,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  BookOpen,
  RotateCcw,
} from 'lucide-react';
import { askAssistant, getAssistantGreeting } from '../api';
import type {
  ChatMessage,
  AssistantRelatedKnowledgePoint,
  LearningContext,
} from '../types';
import { askLearningCompanion } from './student/aiCompanionService';

interface AIAssistantProps {
  currentStudentId: string;
  studentName: string;
  isOnline: boolean;
  learningContext?: LearningContext;
}

export const AIAssistant: React.FC<AIAssistantProps> = ({
  currentStudentId,
  studentName,
  isOnline,
  learningContext,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState<string>('');
  const [quickPrompts, setQuickPrompts] = useState<string[]>([
    '我目前的学习情况怎么样？',
    '我接下来应该学什么？',
    '帮我安排今天的学习任务',
  ]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Load greeting and reset chat when student changes
  useEffect(() => {
    let isSubscribed = true;

    async function loadGreeting() {
      setIsLoading(true);
      setErrorMsg(null);
      try {
        const greetingData = await getAssistantGreeting(currentStudentId);
        if (isSubscribed) {
          setQuickPrompts(greetingData.quick_prompts);
          const initialMessage: ChatMessage = {
            id: `greeting-${Date.now()}`,
            sender: 'assistant',
            content: greetingData.greeting,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            suggested_actions: [
              '点击下方快捷问题快速发问',
              '输入具体知识点名称查询掌握详情',
              '询问今日专属任务与做题时限',
            ],
          };
          setMessages([initialMessage]);
        }
      } catch {
        if (isSubscribed) {
          // Fallback greeting if network offline
          const fallbackGreeting: ChatMessage = {
            id: `greeting-${Date.now()}`,
            sender: 'assistant',
            content: `你好，${studentName}！我是学海智导 AI 学习助手。你可以向我询问你的学习现状、推荐学习路径以及今日学习任务安排。`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
          setMessages([fallbackGreeting]);
        }
      } finally {
        if (isSubscribed) {
          setIsLoading(false);
        }
      }
    }

    loadGreeting();

    return () => {
      isSubscribed = false;
    };
  }, [currentStudentId, studentName]);

  // Send message to AI assistant
  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend !== undefined ? textToSend : inputMessage).trim();
    if (!text || isLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setErrorMsg(null);
    setIsLoading(true);

    try {
      // 若存在 learningContext，由伴学管线服务输出经过事实校验与安全兜底的回答
      if (learningContext) {
        const sf = learningContext.system_facts;
        const de = learningContext.derived_explanations;
        const companionAnswer = await askLearningCompanion(learningContext, text);

        const assistantMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          sender: 'assistant',
          content: companionAnswer.answer,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          related_knowledge_points: [
            {
              knowledge_id: sf.current_knowledge_id,
              knowledge_name: sf.current_knowledge_name,
              accuracy: sf.current_mastery_percent,
              priority: sf.path_priority,
              reason: de.recommendation_reason,
              chapter: sf.current_chapter,
            },
          ],
          suggested_actions: [sf.next_action.label, '查看知识图谱全景', '返回今日任务'],
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setIsLoading(false);
        return;
      }

      const response = await askAssistant(currentStudentId, text);
      const assistantMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: 'assistant',
        content: response.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        related_knowledge_points: response.related_knowledge_points,
        suggested_actions: response.suggested_actions,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg('助手暂时无法回应，请稍后重试。');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Handle keyboard submit
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Helper for knowledge point accuracy badge color
  const getAccuracyBadge = (accuracy: number | null) => {
    if (accuracy === null) {
      return {
        text: '尚无记录',
        className: 'bg-slate-100 text-slate-600 border-slate-200',
      };
    }
    if (accuracy < 60) {
      return {
        text: `${accuracy.toFixed(1)}% (高风险)`,
        className: 'bg-rose-50 text-rose-700 border-rose-200',
      };
    }
    if (accuracy <= 70) {
      return {
        text: `${accuracy.toFixed(1)}% (需加强)`,
        className: 'bg-amber-50 text-amber-700 border-amber-200',
      };
    }
    return {
      text: `${accuracy.toFixed(1)}% (良好)`,
      className: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    };
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden flex flex-col">
      {/* 1. Header */}
      <div className="p-5 sm:p-6 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 flex items-center justify-center shadow-md shadow-indigo-500/30 text-white">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold tracking-tight">AI 学习助手</h2>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">
                <Sparkles className="w-3 h-3 text-indigo-400" />
                智能学伴
              </span>
            </div>
            <p className="text-xs text-slate-300">
              基于你的真实学情画像与知识图谱，动态解答疑问与制定攻关路线
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-white/10 text-slate-200 border border-white/15">
            当前指导：{studentName}
          </span>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>{isOnline ? 'AI服务在线' : '离线模式'}</span>
          </div>
        </div>
      </div>

      {/* 1.5 Context Grounding Fact Bar */}
      {learningContext && (
        <div className="px-5 py-2.5 bg-indigo-50/80 border-b border-indigo-100 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 text-slate-700 font-medium">
            <span className="px-2 py-0.5 rounded bg-indigo-100 text-indigo-700 font-bold text-[11px]">
              事实对齐
            </span>
            <span>
              焦点：<strong>{learningContext.system_facts.current_knowledge_id} · {learningContext.system_facts.current_knowledge_name}</strong>
            </span>
            <span className="text-slate-300">|</span>
            <span>
              掌握度：<strong>{learningContext.system_facts.current_mastery_percent}%</strong>（目标 {learningContext.system_facts.mastery_target_percent}%）
            </span>
          </div>
          <div className="text-indigo-600 text-[11px] font-semibold">
            状态：{learningContext.system_facts.current_path_state}
          </div>
        </div>
      )}

      {/* 2. Quick Prompts Bar */}
      <div className="px-5 py-3 bg-slate-50 border-b border-slate-200/80 flex items-center gap-2 overflow-x-auto no-scrollbar">
        <span className="text-[11px] font-bold text-slate-400 shrink-0 flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-indigo-500" />
          快捷发问：
        </span>
        <div className="flex items-center gap-2">
          {(learningContext
            ? [
                `为什么推荐我学 ${learningContext.system_facts.current_knowledge_name}？`,
                '我现在掌握度距离目标还差多少？',
                '我下一步应该做什么？',
                ...quickPrompts.filter((p) => !p.includes('接下来应该学什么')),
              ]
            : quickPrompts
          ).map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(prompt)}
              disabled={isLoading}
              className="text-xs font-medium px-3 py-1.5 rounded-full bg-white hover:bg-indigo-50 text-slate-700 hover:text-indigo-700 border border-slate-200 hover:border-indigo-200 transition-all shrink-0 cursor-pointer shadow-2xs hover:shadow-xs disabled:opacity-50"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* 3. Message List Container */}
      <div className="p-5 sm:p-6 space-y-5 min-h-[360px] max-h-[520px] overflow-y-auto bg-slate-50/50">
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          return (
            <div
              key={msg.id}
              className={`flex items-start gap-3 ${
                isUser ? 'flex-row-reverse' : 'flex-row'
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 shadow-2xs ${
                  isUser
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white text-indigo-600 border border-slate-200'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Bubble Content */}
              <div
                className={`max-w-2xl rounded-2xl p-4 text-xs sm:text-sm leading-relaxed ${
                  isUser
                    ? 'bg-indigo-600 text-white rounded-tr-xs shadow-xs'
                    : 'bg-white text-slate-800 border border-slate-200/90 rounded-tl-xs shadow-xs space-y-3'
                }`}
              >
                {/* Main Text Content */}
                <div className="whitespace-pre-wrap leading-relaxed font-normal">
                  {msg.content}
                </div>

                {/* Structured: Related Knowledge Points */}
                {!isUser && msg.related_knowledge_points && msg.related_knowledge_points.length > 0 && (
                  <div className="pt-3 border-t border-slate-100 space-y-2">
                    <div className="flex items-center gap-1.5 text-[11px] font-bold text-indigo-700">
                      <BookOpen className="w-3.5 h-3.5" />
                      <span>关联知识点透视</span>
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {msg.related_knowledge_points.map((kp: AssistantRelatedKnowledgePoint) => {
                        const accBadge = getAccuracyBadge(kp.accuracy);
                        return (
                          <div
                            key={kp.knowledge_id}
                            className="bg-slate-50/80 rounded-xl p-3 border border-slate-200/80 space-y-1.5"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-1.5">
                                <span className="font-mono text-[10px] font-bold bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-600">
                                  {kp.knowledge_id}
                                </span>
                                <span className="font-bold text-slate-900 text-xs">
                                  {kp.knowledge_name}
                                </span>
                              </div>
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${accBadge.className}`}
                              >
                                {accBadge.text}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-600 leading-snug">
                              {kp.reason}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Structured: Suggested Actions Checklist */}
                {!isUser && msg.suggested_actions && msg.suggested_actions.length > 0 && (
                  <div className="pt-2 border-t border-slate-100 space-y-1.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-bold text-emerald-700">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>推荐下一步行动指南</span>
                    </div>
                    <div className="space-y-1 bg-emerald-50/40 rounded-xl p-2.5 border border-emerald-100">
                      {msg.suggested_actions.map((act, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-1.5 text-[11px] text-slate-700 leading-snug"
                        >
                          <ArrowRight className="w-3 h-3 text-emerald-600 shrink-0 mt-0.5" />
                          <span>{act}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Timestamp */}
                <div
                  className={`text-[10px] mt-1 text-right ${
                    isUser ? 'text-indigo-200' : 'text-slate-400'
                  }`}
                >
                  {msg.timestamp}
                </div>
              </div>
            </div>
          );
        })}

        {/* Loading Typing Indicator */}
        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-xl bg-white text-indigo-600 border border-slate-200 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-white rounded-2xl rounded-tl-xs p-4 border border-slate-200 text-xs text-slate-500 shadow-xs flex items-center gap-2">
              <span className="flex gap-1 items-center">
                <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce"></span>
                <span
                  className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce"
                  style={{ animationDelay: '0.2s' }}
                ></span>
                <span
                  className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce"
                  style={{ animationDelay: '0.4s' }}
                ></span>
              </span>
              <span>AI 正在结合你的学情画像与图谱关系进行分析...</span>
            </div>
          </div>
        )}

        {/* Error Alert */}
        {errorMsg && (
          <div className="flex items-center justify-between p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button
              onClick={() => handleSendMessage()}
              className="font-bold flex items-center gap-1 hover:underline cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" /> 重试
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 4. Bottom Input Form */}
      <div className="p-4 bg-white border-t border-slate-200/80">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex flex-col gap-2"
        >
          <div className="relative flex items-center">
            <textarea
              ref={inputRef}
              rows={2}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="向 AI 提问：例如“我为什么要先学习稀缺性？”或“我今天应该学什么？”"
              disabled={isLoading}
              className="w-full text-xs sm:text-sm bg-slate-50 hover:bg-white focus:bg-white rounded-xl p-3 pr-12 border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 focus:outline-none resize-none transition-all"
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || isLoading}
              className="absolute right-2.5 bottom-2.5 p-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white disabled:opacity-30 disabled:pointer-events-none transition-all shadow-xs cursor-pointer"
              title="发送消息 (Enter)"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" /> 按 Enter 发送，Shift + Enter 换行
            </span>
            <span>结合 S001~S005 真实学情画像回答</span>
          </div>
        </form>
      </div>
    </div>
  );
};
