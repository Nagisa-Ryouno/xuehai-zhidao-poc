import React, { useState } from 'react';
import {
  X,
  Sparkles,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Star,
  Layers,
  ArrowRight,
  Bot,
  Send,
  Loader2,
  Target,
  Lock,
  PlayCircle,
  RotateCcw,
} from 'lucide-react';
import type { KnowledgeGraphNodeData, AssistantResponse, PathState } from '../types';
import { askAssistant } from '../api';

interface KnowledgeGraphDetailDrawerProps {
  nodeData: KnowledgeGraphNodeData | null;
  studentId: string;
  studentName: string;
  allNodesMap: Record<string, KnowledgeGraphNodeData>;
  pathState?: PathState;
  onClose: () => void;
  onSelectNode: (nodeId: string) => void;
  onStartQuiz?: (knowledgeId: string, knowledgeName: string) => void;
  onJumpToAssistant?: () => void;
}

export const KnowledgeGraphDetailDrawer: React.FC<KnowledgeGraphDetailDrawerProps> = ({
  nodeData,
  studentId,
  studentName,
  allNodesMap,
  pathState,
  onClose,
  onSelectNode,
  onStartQuiz,
  onJumpToAssistant,
}) => {
  const [aiLoading, setAiLoading] = useState<boolean>(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiResponse, setAiResponse] = useState<AssistantResponse | null>(null);
  const [activeQuestion, setActiveQuestion] = useState<string>('');

  if (!nodeData) return null;

  const {
    knowledge_id,
    knowledge_name,
    chapter,
    description,
    difficulty,
    accuracy,
    assessment_score,
    practice_count,
    average_time_seconds,
    is_weak,
    prerequisite_reason,
    is_recommended,
    path_stage,
    priority,
    learning_goal,
    recommend_reason,
    upstream_prerequisites,
    downstream_knowledge,
  } = nodeData;

  // 调用 AI 学习助手问答
  const handleAskAI = async (query: string) => {
    setActiveQuestion(query);
    setAiLoading(true);
    setAiError(null);
    setAiResponse(null);

    try {
      const res = await askAssistant(studentId, query);
      setAiResponse(res);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setAiError(err.message);
      } else {
        setAiError('AI 导师连接异常，请重试。');
      }
    } finally {
      setAiLoading(false);
    }
  };

  // 推导考点当前 PathState (优先读取传入状态，保底依据掌握度和推荐标记)
  const resolvedPathState: PathState =
    pathState ||
    (accuracy !== null && accuracy >= 80
      ? 'COMPLETED'
      : is_recommended
      ? 'IN_PROGRESS'
      : 'AVAILABLE');

  const currentPathStateConfig = (() => {
    switch (resolvedPathState) {
      case 'LOCKED':
        return {
          badgeText: '🔒 需先掌握前置',
          badgeClass: 'bg-slate-100 text-slate-600 border-slate-300',
          buttonText: '需先掌握前置考点',
          buttonClass: 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed opacity-70',
          disabled: true,
          ariaLabel: '前置考点未满足，暂不可开始微测验',
        };
      case 'AVAILABLE':
        return {
          badgeText: '🔓 已满足学习条件',
          badgeClass: 'bg-sky-50 text-sky-700 border-sky-200',
          buttonText: '开始微测验',
          buttonClass: 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs cursor-pointer',
          disabled: false,
          ariaLabel: '已满足前置条件，点击开始微测验',
        };
      case 'IN_PROGRESS':
        return {
          badgeText: '🎯 正在进行',
          badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200 ring-2 ring-indigo-400/30',
          buttonText: '继续攻坚微测验',
          buttonClass: 'bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white shadow-sm cursor-pointer ring-2 ring-indigo-400/40',
          disabled: false,
          ariaLabel: '当前攻坚任务，点击进入微测验',
        };
      case 'COMPLETED':
        return {
          badgeText: '✓ 已掌握',
          badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          buttonText: '复习微测验',
          buttonClass: 'bg-white hover:bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-2xs cursor-pointer',
          disabled: false,
          ariaLabel: '已掌握考点，点击进行复习微测验',
        };
    }
  })();

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-white shadow-2xl z-50 flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-300">
      {/* 抽屉顶栏 */}
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/80">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-bold px-2.5 py-1 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
            {knowledge_id}
          </span>
          <span className="text-xs font-medium text-slate-500 px-2 py-0.5 rounded-full bg-slate-200/60">
            {chapter}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
          title="关闭详情面板"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* 抽屉可滚动正文 */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* 知识点标题与简介 */}
        <div>
          <h3 className="text-lg font-bold text-slate-900 leading-snug">
            {knowledge_name}
          </h3>
          <p className="mt-2 text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
            {description || '研究微观经济运行的核心概念与规律，构建严密的经济推导逻辑。'}
          </p>

          <div className="mt-3 flex items-center gap-4 text-xs text-slate-500">
            <div className="flex items-center gap-1">
              <span>难度：</span>
              <div className="flex items-center">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Star
                    key={i}
                    className={`w-3.5 h-3.5 ${
                      i < difficulty ? 'text-amber-400 fill-amber-400' : 'text-slate-200 fill-slate-200'
                    }`}
                  />
                ))}
              </div>
            </div>
            <span>·</span>
            <div>
              <span>辐射后续：</span>
              <span className="font-semibold text-slate-700">{downstream_knowledge.length} 个考点</span>
            </div>
          </div>
        </div>

        {/* 学生个人作答学情卡片 */}
        <div className="rounded-xl p-4 border border-slate-200 bg-slate-50/50 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
              <Target className="w-4 h-4 text-indigo-600" />
              {studentName} 的掌握现状
            </span>

            {/* 正确率徽章 */}
            {accuracy === null ? (
              <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-slate-200 text-slate-600 font-medium">
                <HelpCircle className="w-3.5 h-3.5" />
                尚无学习记录
              </span>
            ) : is_weak ? (
              <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-rose-100 text-rose-700 font-semibold border border-rose-200">
                <AlertTriangle className="w-3.5 h-3.5" />
                正确率 {accuracy.toFixed(1)}% (薄弱)
              </span>
            ) : accuracy < 70 ? (
              <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-amber-100 text-amber-700 font-semibold border border-amber-200">
                <AlertTriangle className="w-3.5 h-3.5" />
                正确率 {accuracy.toFixed(1)}% (待巩固)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-700 font-semibold border border-emerald-200">
                <CheckCircle className="w-3.5 h-3.5" />
                正确率 {accuracy.toFixed(1)}% (良好)
              </span>
            )}
          </div>

          {accuracy !== null ? (
            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200/60 text-center">
              <div className="bg-white p-2 rounded-lg border border-slate-100">
                <div className="text-[11px] text-slate-400">综合得分</div>
                <div className="text-sm font-bold text-slate-800">
                  {assessment_score !== null ? assessment_score.toFixed(0) : '--'}
                </div>
              </div>
              <div className="bg-white p-2 rounded-lg border border-slate-100">
                <div className="text-[11px] text-slate-400">练习题量</div>
                <div className="text-sm font-bold text-slate-800">
                  {practice_count !== null ? `${practice_count} 题` : '--'}
                </div>
              </div>
              <div className="bg-white p-2 rounded-lg border border-slate-100">
                <div className="text-[11px] text-slate-400">平均耗时</div>
                <div className="text-sm font-bold text-slate-800">
                  {average_time_seconds !== null ? `${average_time_seconds.toFixed(0)}s` : '--'}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500 bg-white p-2.5 rounded-lg border border-slate-100">
              该考点暂无作答测评历史。建议完成当前前置阶段任务后，再解锁此章节练习。
            </p>
          )}
        </div>

        {/* 学习路径联动卡片 (若在推荐路径中) */}
        {is_recommended && (
          <div className="rounded-xl p-4 border-2 border-indigo-200 bg-indigo-50/40 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-indigo-900 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-indigo-600" />
                AI 个性化学习路径
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-600 text-white shadow-xs">
                Stage {path_stage} · 优先级 {priority || '高'}
              </span>
            </div>

            {learning_goal && (
              <div className="text-xs text-indigo-950">
                <span className="font-semibold text-indigo-800">阶段目标：</span>
                {learning_goal}
              </div>
            )}

            {recommend_reason && (
              <div className="text-xs text-slate-600 bg-white/80 p-2.5 rounded-lg border border-indigo-100">
                <span className="font-semibold text-indigo-900">推荐依据：</span>
                {recommend_reason}
              </div>
            )}
          </div>
        )}

        {/* 前置知识与下游影响拓扑 */}
        <div className="space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5" />
            图谱拓扑依赖关系
          </h4>

          {/* 为什么需要学它 / 前置原因 */}
          {prerequisite_reason && (
            <div className="p-3 bg-amber-50/60 rounded-xl border border-amber-200 text-xs text-amber-900 leading-relaxed">
              <span className="font-bold">为什么优先推荐学习？</span>
              <p className="mt-1">{prerequisite_reason}</p>
            </div>
          )}

          {/* 前置依赖节点 */}
          <div>
            <div className="text-xs font-semibold text-slate-700 mb-1.5 flex items-center justify-between">
              <span>必须掌握的前置基础 ({upstream_prerequisites.length})：</span>
            </div>
            {upstream_prerequisites.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {upstream_prerequisites.map((pid) => {
                  const target = allNodesMap[pid];
                  return (
                    <button
                      key={pid}
                      onClick={() => onSelectNode(pid)}
                      className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-200 border border-slate-200 transition-colors"
                      title="点击在图谱中聚焦该节点"
                    >
                      <span className="font-mono font-bold text-[11px] text-slate-500">{pid}</span>
                      <span>{target ? target.knowledge_name : pid}</span>
                    </button>
                  );
                })}
              </div>
            ) : (
              <span className="text-xs text-slate-400 italic">属于学科源头基石，无前置依赖</span>
            )}
          </div>

          {/* 下游辐射影响节点 */}
          <div>
            <div className="text-xs font-semibold text-slate-700 mb-1.5 flex items-center justify-between">
              <span>掌握后可赋能的后续考点 ({downstream_knowledge.length})：</span>
            </div>
            {downstream_knowledge.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {downstream_knowledge.map((nid) => {
                  const target = allNodesMap[nid];
                  return (
                    <button
                      key={nid}
                      onClick={() => onSelectNode(nid)}
                      className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-200 border border-slate-200 transition-colors"
                      title="点击在图谱中聚焦该节点"
                    >
                      <span className="font-mono font-bold text-[11px] text-slate-500">{nid}</span>
                      <span>{target ? target.knowledge_name : nid}</span>
                      <ArrowRight className="w-3 h-3 text-slate-400" />
                    </button>
                  );
                })}
              </div>
            ) : (
              <span className="text-xs text-slate-400 italic">属于终端综合考点</span>
            )}
          </div>
        </div>

        {/* 问问 AI 联动区 */}
        <div className="pt-4 border-t border-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
              <Bot className="w-4 h-4 text-indigo-600" />
              问问 AI 学习导师
            </h4>
            <span className="text-[10px] text-slate-400">基于真实学情与拓扑</span>
          </div>

          {/* 快捷提问按钮 */}
          <div className="space-y-1.5">
            <button
              onClick={() =>
                handleAskAI(`为什么推荐我先学习【${knowledge_name}】？`)
              }
              disabled={aiLoading}
              className="w-full text-left text-xs px-3 py-2 rounded-lg bg-indigo-50/70 hover:bg-indigo-100 text-indigo-900 border border-indigo-200/80 transition-colors flex items-center justify-between group"
            >
              <span>为什么推荐我先学习【{knowledge_name}】？</span>
              <Send className="w-3.5 h-3.5 text-indigo-400 group-hover:text-indigo-600 transition-colors" />
            </button>

            <button
              onClick={() =>
                handleAskAI(`请深度诊断我对【${knowledge_name}】的掌握情况并给出攻克方案`)
              }
              disabled={aiLoading}
              className="w-full text-left text-xs px-3 py-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 transition-colors flex items-center justify-between group"
            >
              <span>诊断我的【{knowledge_name}】并给出攻坚方案</span>
              <Send className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-600 transition-colors" />
            </button>
          </div>

          {/* AI 交互回答展示区 */}
          {aiLoading && (
            <div className="p-4 rounded-xl bg-indigo-50/50 border border-indigo-100 flex items-center justify-center gap-2 text-xs text-indigo-700">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>AI 导师正在深入剖析你的拓扑网络与学情画像...</span>
            </div>
          )}

          {aiError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
              {aiError}
            </div>
          )}

          {aiResponse && (
            <div className="p-4 rounded-xl bg-white border border-indigo-200 shadow-sm space-y-3 animate-in fade-in-50 duration-200">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <span className="text-xs font-bold text-indigo-700 flex items-center gap-1.5">
                  <Bot className="w-3.5 h-3.5" />
                  AI 导师深度分析
                </span>
                <span className="text-[10px] text-slate-400">{activeQuestion.slice(0, 16)}...</span>
              </div>

              {/* 回答正文 */}
              <div className="text-xs text-slate-700 leading-relaxed whitespace-pre-line">
                {aiResponse.answer}
              </div>

              {/* 关联知识点卡片 */}
              {aiResponse.related_knowledge_points && aiResponse.related_knowledge_points.length > 0 && (
                <div className="pt-2 border-t border-slate-100 space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500">拓扑关联考点：</span>
                  <div className="space-y-1">
                    {aiResponse.related_knowledge_points.map((kp) => (
                      <div
                        key={kp.knowledge_id}
                        className="text-[11px] p-2 rounded bg-slate-50 border border-slate-100 flex items-center justify-between"
                      >
                        <span className="font-semibold text-slate-800">
                          {kp.knowledge_id} · {kp.knowledge_name}
                        </span>
                        <span className="text-slate-500">
                          {kp.accuracy !== null ? `${kp.accuracy.toFixed(0)}% 正确率` : '尚无记录'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 导师建议行动 */}
              {aiResponse.suggested_actions && aiResponse.suggested_actions.length > 0 && (
                <div className="pt-2 border-t border-slate-100 space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500">建议行动：</span>
                  <ul className="text-[11px] text-slate-600 space-y-1">
                    {aiResponse.suggested_actions.map((act, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0 mt-0.5" />
                        <span>{act}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 底部跳转链接 */}
              {onJumpToAssistant && (
                <button
                  onClick={onJumpToAssistant}
                  className="w-full text-center text-xs text-indigo-600 hover:text-indigo-800 hover:underline pt-2 font-medium"
                >
                  在页面底部“AI 学习助手”中继续多轮对话 →
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 抽屉底部固定行动区域 (P0-2: 打通图谱查看至微测验闭环) */}
      <div className="p-4 border-t border-slate-200 bg-slate-50/95 backdrop-blur-xs flex flex-col sm:flex-row items-center gap-2.5 shrink-0 shadow-xs">
        <div className="w-full sm:w-auto flex-1 flex items-center justify-between sm:justify-start gap-2">
          <span className="text-[11px] text-slate-500 font-medium">路径状态：</span>
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${currentPathStateConfig.badgeClass}`}>
            {currentPathStateConfig.badgeText}
          </span>
        </div>
        <button
          type="button"
          disabled={currentPathStateConfig.disabled}
          aria-label={currentPathStateConfig.ariaLabel}
          onClick={() => {
            if (!currentPathStateConfig.disabled && onStartQuiz) {
              onStartQuiz(knowledge_id, knowledge_name);
            }
          }}
          className={`w-full sm:w-auto px-5 py-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 transition-all min-h-[44px] ${currentPathStateConfig.buttonClass}`}
        >
          {resolvedPathState === 'LOCKED' && <Lock className="w-3.5 h-3.5" />}
          {resolvedPathState === 'AVAILABLE' && <PlayCircle className="w-3.5 h-3.5" />}
          {resolvedPathState === 'IN_PROGRESS' && <Target className="w-3.5 h-3.5" />}
          {resolvedPathState === 'COMPLETED' && <RotateCcw className="w-3.5 h-3.5" />}
          <span>{currentPathStateConfig.buttonText}</span>
        </button>
      </div>
    </div>
  );
};
