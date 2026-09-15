import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  BookOpen,
  Sparkles,
  Search,
  ArrowRight,
  RefreshCw,
  Clock,
  PlayCircle,
  CheckCircle2,
  ArrowUpRight,
  Award,
  ChevronRight,
  Check,
  RotateCcw,
} from 'lucide-react';
import type {
  LearningResource,
  ResourceType,
  RecommendedResourcesResponse,
  LearningSession,
  KnowledgeEffectivenessResponse,
  SessionCompleteResponse,
} from '../../types';
import {
  getResourcesByKnowledge,
  getRecommendedResources,
  recordResourceEvent,
  createLearningSession,
  completeLearningSession,
  getKnowledgeEffectiveness,
} from '../../api';
import { ResourceCard } from './ResourceCard';
import { ExampleReaderModal } from './ExampleReaderModal';
import { ALL_CONCEPT_CARDS, type ConceptCardData } from './conceptCardData';

interface ResourceHubProps {
  studentId: string;
  initialKnowledgeId?: string;
  onOpenConceptCard: (knowledgeId: string, knowledgeName: string) => void;
  onStartQuiz: (knowledgeId: string, knowledgeName: string) => void;
  onAskAI: (
    knowledgeId: string,
    knowledgeName: string,
    prefillMessage?: string,
    resourceContext?: Record<string, any>
  ) => void;
}

const TYPE_FILTER_TABS: Array<{ id: string; label: string; type?: ResourceType }> = [
  { id: 'ALL', label: '全部材料' },
  { id: 'CONCEPT_CARD', label: '考点微卡', type: 'CONCEPT_CARD' },
  { id: 'EXAMPLE', label: '典型例题', type: 'EXAMPLE' },
  { id: 'PRACTICE', label: '靶向微练', type: 'PRACTICE' },
  { id: 'DOCUMENT', label: '精讲讲义', type: 'DOCUMENT' },
  { id: 'VIDEO', label: '导学视频', type: 'VIDEO' },
];

export const ResourceHub: React.FC<ResourceHubProps> = ({
  studentId,
  initialKnowledgeId = 'K01',
  onOpenConceptCard,
  onStartQuiz,
  onAskAI,
}) => {
  const [selectedKnowledgeId, setSelectedKnowledgeId] = useState<string>(initialKnowledgeId);
  const [activeTypeFilter, setActiveTypeFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // 资源列表状态
  const [resources, setResources] = useState<LearningResource[]>([]);
  const [isLoadingResources, setIsLoadingResources] = useState<boolean>(false);

  // 自适应推荐状态
  const [recommendedData, setRecommendedData] = useState<RecommendedResourcesResponse | null>(null);
  const [isLoadingRecs, setIsLoadingRecs] = useState<boolean>(false);

  // Sprint 9-D: 学习会话与效果反馈状态
  const [activeSession, setActiveSession] = useState<LearningSession | null>(null);
  const [isStartingSession, setIsStartingSession] = useState<boolean>(false);
  const [isCompletingSession, setIsCompletingSession] = useState<boolean>(false);
  const [completionResult, setCompletionResult] = useState<SessionCompleteResponse | null>(null);
  const [knowledgeEffectiveness, setKnowledgeEffectiveness] = useState<KnowledgeEffectivenessResponse | null>(null);

  // 例题阅读模态框状态
  const [activeReadingResource, setActiveReadingResource] = useState<LearningResource | null>(null);

  // 获取当前考点名称
  const currentKnowledgeName = useMemo(() => {
    const found = ALL_CONCEPT_CARDS.find((c: ConceptCardData) => c.knowledgeId === selectedKnowledgeId);
    return found ? found.knowledgeName : selectedKnowledgeId;
  }, [selectedKnowledgeId]);

  // 当 studentId 改变时，严格重置所有本地会话状态，保障多学生上下文隔离
  useEffect(() => {
    setActiveSession(null);
    setCompletionResult(null);
    setKnowledgeEffectiveness(null);
  }, [studentId]);

  // 加载当前考点学习效果与最新会话信息 (Sprint 9-D)
  const fetchEffectiveness = useCallback(async () => {
    try {
      const eff = await getKnowledgeEffectiveness(selectedKnowledgeId, studentId);
      setKnowledgeEffectiveness(eff);
      if (eff.latest_session && eff.latest_session.status === 'IN_PROGRESS') {
        setActiveSession(eff.latest_session);
      }
    } catch {
      setKnowledgeEffectiveness(null);
    }
  }, [selectedKnowledgeId, studentId]);

  // 加载自适应推荐资源
  const fetchRecommendations = useCallback(async () => {
    try {
      setIsLoadingRecs(true);
      const data = await getRecommendedResources(studentId, selectedKnowledgeId);
      setRecommendedData(data);
    } catch {
      setRecommendedData(null);
    } finally {
      setIsLoadingRecs(false);
    }
  }, [studentId, selectedKnowledgeId]);

  // 加载指定考点的所有资源
  const fetchResources = useCallback(async () => {
    try {
      setIsLoadingResources(true);
      const data = await getResourcesByKnowledge(selectedKnowledgeId);
      setResources(data.resources || []);
    } catch {
      setResources([]);
    } finally {
      setIsLoadingResources(false);
    }
  }, [selectedKnowledgeId]);

  useEffect(() => {
    fetchRecommendations();
    fetchResources();
    fetchEffectiveness();
  }, [fetchRecommendations, fetchResources, fetchEffectiveness]);

  // 记录卡片曝光事件 (RESOURCE_VIEW)
  useEffect(() => {
    if (resources.length > 0) {
      recordResourceEvent({
        student_id: studentId,
        resource_id: `res_${selectedKnowledgeId.toLowerCase()}_hub_view`,
        knowledge_id: selectedKnowledgeId,
        event_type: 'RESOURCE_VIEW',
        metadata: {
          total_count: resources.length,
        },
      }).catch(() => {});
    }
  }, [studentId, selectedKnowledgeId, resources.length]);

  // 启动学习会话 (Sprint 9-D)
  const handleStartSession = async () => {
    try {
      setIsStartingSession(true);
      const recIds = recommendedData?.recommendations.map((r) => r.resource.resource_id) || [];
      const session = await createLearningSession(studentId, selectedKnowledgeId, recIds);
      setActiveSession(session);
      setCompletionResult(null);
    } catch (err) {
      console.error('Failed to create learning session:', err);
    } finally {
      setIsStartingSession(false);
    }
  };

  // 完成学习会话并触发权威 BKT 效果校验 (Sprint 9-D)
  const handleCompleteSession = async () => {
    if (!activeSession) return;
    try {
      setIsCompletingSession(true);
      const res = await completeLearningSession(activeSession.session_id, {
        student_id: studentId,
        completed_resource_ids: activeSession.completed_resource_ids,
      });
      setCompletionResult(res);
      setActiveSession(res.session);
      fetchEffectiveness();
    } catch (err) {
      console.error('Failed to complete learning session:', err);
    } finally {
      setIsCompletingSession(false);
    }
  };

  // 过滤资源
  const filteredResources = useMemo(() => {
    return resources.filter((res) => {
      // 类型过滤
      if (activeTypeFilter !== 'ALL' && res.resource_type !== activeTypeFilter) {
        return false;
      }
      // 搜索词过滤
      if (searchQuery.trim()) {
        const query = searchQuery.trim().toLowerCase();
        const matchesTitle = res.title.toLowerCase().includes(query);
        const matchesDesc = res.description.toLowerCase().includes(query);
        const matchesSummary = (res.summary || '').toLowerCase().includes(query);
        if (!matchesTitle && !matchesDesc && !matchesSummary) {
          return false;
        }
      }
      return true;
    });
  }, [resources, activeTypeFilter, searchQuery]);

  // 打开具体资源
  const handleOpenResource = (res: LearningResource) => {
    // 上报打开事件
    recordResourceEvent({
      student_id: studentId,
      resource_id: res.resource_id,
      knowledge_id: res.knowledge_id,
      event_type: 'RESOURCE_OPEN',
      metadata: {
        resource_type: res.resource_type,
        title: res.title,
      },
    }).catch(() => {});

    // 若当前有活跃会话，动态标记该材料为已访问/完成
    if (activeSession && !activeSession.completed_resource_ids.includes(res.resource_id)) {
      setActiveSession((prev) =>
        prev
          ? {
              ...prev,
              completed_resource_ids: [...prev.completed_resource_ids, res.resource_id],
            }
          : null
      );
    }

    if (res.resource_type === 'CONCEPT_CARD') {
      onOpenConceptCard(res.knowledge_id, currentKnowledgeName);
    } else if (res.resource_type === 'PRACTICE') {
      onStartQuiz(res.knowledge_id, currentKnowledgeName);
    } else {
      setActiveReadingResource(res);
    }
  };

  // 标记完成材料
  const handleCompleteResource = (res: LearningResource) => {
    recordResourceEvent({
      student_id: studentId,
      resource_id: res.resource_id,
      knowledge_id: res.knowledge_id,
      event_type: 'RESOURCE_COMPLETE',
      duration_seconds: res.estimated_minutes * 60,
      metadata: {
        resource_type: res.resource_type,
        title: res.title,
      },
    }).catch(() => {});

    if (activeSession && !activeSession.completed_resource_ids.includes(res.resource_id)) {
      setActiveSession((prev) =>
        prev
          ? {
              ...prev,
              completed_resource_ids: [...prev.completed_resource_ids, res.resource_id],
            }
          : null
      );
    }
  };

  // 问问 AI 伴学 (携带真实材料上下文)
  const handleAskAI = (res: LearningResource) => {
    const prefill = `请帮我讲解关于【${res.title}】的核心思路与关键注意点：${res.description}`;
    onAskAI(res.knowledge_id, currentKnowledgeName, prefill, {
      resource_id: res.resource_id,
      resource_title: res.title,
      resource_type: res.resource_type,
    });
  };

  return (
    <div className="space-y-6 pb-12">
      {/* 顶部标题区 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-indigo-600 uppercase tracking-wider mb-1">
            <BookOpen className="w-4 h-4" />
            <span>自适应学习材料库</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            学习资源中心
          </h2>
          <p className="text-xs sm:text-sm text-slate-600 mt-1">
            提供覆盖 30 考点的精要微卡、生活与商业例题、靶向微练与精讲讲义，闭环验证学习效果。
          </p>
        </div>

        {/* 考点下拉选择器 */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-2 w-full sm:w-auto">
          <label htmlFor="knowledge-select" className="text-xs font-bold text-slate-600 whitespace-nowrap">
            当前考点：
          </label>
          <select
            id="knowledge-select"
            value={selectedKnowledgeId}
            onChange={(e) => {
              setSelectedKnowledgeId(e.target.value);
              setActiveSession(null);
              setCompletionResult(null);
            }}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs sm:text-sm font-semibold text-slate-800 shadow-xs focus:border-indigo-500 focus:outline-hidden cursor-pointer w-full sm:w-auto max-w-full truncate"
          >
            {ALL_CONCEPT_CARDS.map((card: ConceptCardData) => (
              <option key={card.knowledgeId} value={card.knowledgeId}>
                {card.knowledgeId} - {card.knowledgeName} ({card.chapter})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 1. 核心结果卡：本次学习完成与效果评估 (Sprint 9-D 闭环展示) */}
      {/* ========================================================================= */}
      {completionResult && (
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-emerald-50 via-white to-indigo-50 border-2 border-emerald-300 p-6 shadow-sm animate-in fade-in slide-in-from-top-4 duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-emerald-100">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-emerald-600 text-white shadow-xs">
                <Award className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
                    {completionResult.effectiveness.status_display}
                  </span>
                  <span className="text-xs text-slate-500">
                    考点：{selectedKnowledgeId} {currentKnowledgeName}
                  </span>
                </div>
                <h3 className="text-lg font-extrabold text-slate-900 mt-0.5">
                  本次学习完成！学习效果评估与反馈
                </h3>
              </div>
            </div>

            <button
              type="button"
              onClick={() => {
                setCompletionResult(null);
                setActiveSession(null);
              }}
              className="inline-flex items-center gap-1 text-xs font-bold text-slate-500 hover:text-slate-800 px-3 py-1.5 rounded-xl border border-slate-200 bg-white/80 cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>开启新一轮学习</span>
            </button>
          </div>

          {/* 掌握度对比与净变化展示 (Initial -> Final + Delta) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 my-5">
            <div className="bg-white rounded-2xl p-4 border border-emerald-100 shadow-2xs">
              <span className="text-xs font-medium text-slate-500">学习前掌握度</span>
              <div className="text-2xl font-black text-slate-700 mt-1">
                {(completionResult.effectiveness.initial_mastery * 100).toFixed(1)}%
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">学习会话开始时快照</div>
            </div>

            <div className="bg-white rounded-2xl p-4 border border-emerald-100 shadow-2xs">
              <span className="text-xs font-medium text-slate-500">学习后掌握度</span>
              <div className="text-2xl font-black text-slate-900 mt-1">
                {(completionResult.effectiveness.final_mastery * 100).toFixed(1)}%
              </div>
              <div className="text-[11px] text-emerald-600 font-semibold mt-0.5">
                权威掌握度实时更新
              </div>
            </div>

            <div className="bg-white rounded-2xl p-4 border border-emerald-100 shadow-2xs flex flex-col justify-between">
              <div>
                <span className="text-xs font-medium text-slate-500">掌握度净变化</span>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className={`text-2xl font-black ${
                      completionResult.effectiveness.mastery_delta > 0
                        ? 'text-emerald-600'
                        : completionResult.effectiveness.mastery_delta === 0
                        ? 'text-slate-600'
                        : 'text-rose-600'
                    }`}
                  >
                    {completionResult.effectiveness.mastery_delta > 0 ? '+' : ''}
                    {(completionResult.effectiveness.mastery_delta * 100).toFixed(1)}%
                  </span>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-bold ${
                      completionResult.effectiveness.mastery_delta > 0
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {completionResult.effectiveness.status_display}
                  </span>
                </div>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                完成材料研读与微测验效果验证
              </div>
            </div>
          </div>

          {/* 本次学习完成清单 */}
          <div className="bg-white/90 rounded-2xl p-4 border border-emerald-100 mb-4">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>已完成的学习步骤清单</span>
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 bg-emerald-50/70 px-3 py-2 rounded-xl">
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span>考点微卡精要研读</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 bg-emerald-50/70 px-3 py-2 rounded-xl">
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span>典型例题深度剖析</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 bg-emerald-50/70 px-3 py-2 rounded-xl">
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span>靶向微练 / 效果验证</span>
              </div>
            </div>
          </div>

          {/* 人本导师反馈语 (杜绝技术黑话，强调时间关联) */}
          <div className="bg-indigo-900/5 rounded-2xl p-4 border border-indigo-100 mb-5">
            <div className="flex items-center gap-2 text-xs font-bold text-indigo-700 mb-1">
              <Sparkles className="w-4 h-4" />
              <span>{completionResult.effectiveness.feedback_title}</span>
            </div>
            <p className="text-xs sm:text-sm text-slate-800 leading-relaxed font-medium">
              {completionResult.effectiveness.feedback_message}
            </p>
            <p className="text-[11px] text-slate-500 mt-2">
              完成本次学习后，掌握情况从{' '}
              <span className="font-bold text-slate-700">
                {(completionResult.effectiveness.initial_mastery * 100).toFixed(1)}%
              </span>{' '}
              变为{' '}
              <span className="font-bold text-emerald-700">
                {(completionResult.effectiveness.final_mastery * 100).toFixed(1)}%
              </span>
              。继续保持积极思考！
            </p>
          </div>

          {/* 下一步行动引导 */}
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => onStartQuiz(selectedKnowledgeId, currentKnowledgeName)}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-xs cursor-pointer"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>再练一道巩固</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setCompletionResult(null);
                setActiveSession(null);
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 transition-colors cursor-pointer"
            >
              <span>开启新一轮学习</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. 活跃学习会话进行中卡片 (Sprint 9-D 4步闭环流转) */}
      {/* ========================================================================= */}
      {activeSession && activeSession.status === 'IN_PROGRESS' && !completionResult && (
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 via-indigo-700 to-slate-900 text-white p-6 shadow-md">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-white/20 text-white backdrop-blur-xs">
                <PlayCircle className="w-6 h-6 animate-pulse text-amber-300" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-400 text-slate-900">
                    学习进行中
                  </span>
                  <span className="text-xs text-indigo-200">
                    初始掌握度快照：{(activeSession.initial_mastery * 100).toFixed(1)}%
                  </span>
                </div>
                <h3 className="text-base sm:text-lg font-bold text-white mt-0.5">
                  本次自适应学习会话（{selectedKnowledgeId} {currentKnowledgeName}）
                </h3>
              </div>
            </div>

            <button
              type="button"
              onClick={handleCompleteSession}
              disabled={isCompletingSession}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold text-indigo-900 bg-amber-400 hover:bg-amber-300 transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
            >
              <Award className="w-4 h-4" />
              <span>{isCompletingSession ? '正在评估中...' : '完成本次学习并检验掌握度'}</span>
            </button>
          </div>

          {/* 4 步流程微卡片 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div
              onClick={() => onOpenConceptCard(selectedKnowledgeId, currentKnowledgeName)}
              className="bg-white/10 hover:bg-white/15 backdrop-blur-xs p-3.5 rounded-2xl border border-white/15 cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-indigo-200 font-bold">步骤 1</span>
                {activeSession.completed_resource_ids.some((id) => id.includes('concept')) ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <span className="text-[10px] text-amber-300">建议先学</span>
                )}
              </div>
              <div className="text-xs font-bold text-white">考点微卡精要</div>
              <div className="text-[11px] text-indigo-200 mt-0.5">回顾核心直观与要点</div>
            </div>

            <div
              onClick={() => {
                const ex = resources.find((r) => r.resource_type === 'EXAMPLE');
                if (ex) handleOpenResource(ex);
              }}
              className="bg-white/10 hover:bg-white/15 backdrop-blur-xs p-3.5 rounded-2xl border border-white/15 cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-indigo-200 font-bold">步骤 2</span>
                {activeSession.completed_resource_ids.some((id) => id.includes('example')) ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <span className="text-[10px] text-amber-300">生活与商业案例</span>
                )}
              </div>
              <div className="text-xs font-bold text-white">典型例题深度剖析</div>
              <div className="text-[11px] text-indigo-200 mt-0.5">理解分析逻辑与误区</div>
            </div>

            <div
              onClick={() => onStartQuiz(selectedKnowledgeId, currentKnowledgeName)}
              className="bg-white/10 hover:bg-white/15 backdrop-blur-xs p-3.5 rounded-2xl border border-white/15 cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-indigo-200 font-bold">步骤 3</span>
                <ChevronRight className="w-3.5 h-3.5 text-indigo-300" />
              </div>
              <div className="text-xs font-bold text-white">靶向微练巩固</div>
              <div className="text-[11px] text-indigo-200 mt-0.5">前往微测验驱动掌握度提升</div>
            </div>

            <div
              onClick={handleCompleteSession}
              className="bg-white/10 hover:bg-white/15 backdrop-blur-xs p-3.5 rounded-2xl border border-white/15 cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="text-indigo-200 font-bold">步骤 4</span>
                <ArrowUpRight className="w-3.5 h-3.5 text-indigo-300" />
              </div>
              <div className="text-xs font-bold text-white">检验学习效果</div>
              <div className="text-[11px] text-indigo-200 mt-0.5">对比前后变化与导师评价</div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 3. 自适应推荐横幅 (当无活跃会话且未展示完成卡时呈现) */}
      {/* ========================================================================= */}
      {(!activeSession || activeSession.status !== 'IN_PROGRESS') && !completionResult && recommendedData && recommendedData.recommendations.length > 0 && (
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-500/10 via-white to-amber-500/10 border border-indigo-200/80 p-6 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-indigo-600 text-white shadow-xs">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-indigo-100 text-indigo-700">
                    智能自适应导引
                  </span>
                  <span className="text-xs font-semibold text-slate-600">
                    当前考点客观掌握度：{(recommendedData.mastery * 100).toFixed(1)}%
                  </span>
                  {knowledgeEffectiveness?.effectiveness && (
                    <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-emerald-100 text-emerald-800">
                      上次完成：{knowledgeEffectiveness.effectiveness.status_display}
                    </span>
                  )}
                </div>
                <h3 className="text-base sm:text-lg font-bold text-slate-900 mt-0.5">
                  为你量身定制的步骤建议
                </h3>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleStartSession}
                disabled={isStartingSession}
                className="inline-flex items-center justify-center gap-1.5 py-2 px-4 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
              >
                <PlayCircle className="w-4 h-4" />
                <span>{isStartingSession ? '正在开启...' : '开始本次学习'}</span>
              </button>

              <button
                type="button"
                onClick={fetchRecommendations}
                className="p-2 rounded-xl text-slate-600 hover:text-indigo-600 hover:bg-white/80 transition-colors cursor-pointer"
                title="刷新推荐"
              >
                <RefreshCw className={`w-4 h-4 ${isLoadingRecs ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          <p className="text-xs sm:text-sm text-slate-700 leading-relaxed mb-4 bg-white/70 p-3 rounded-2xl border border-indigo-100/60 font-medium">
            {recommendedData.reason_summary}
          </p>

          {/* 推荐时序卡片横向网格 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {recommendedData.recommendations.map((rec) => (
              <div
                key={rec.resource.resource_id}
                className="relative flex flex-col justify-between bg-white rounded-2xl border border-indigo-100/80 p-4 shadow-2xs hover:shadow-xs transition-shadow"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-indigo-100 text-indigo-700">
                      步骤 {rec.suggested_order}
                    </span>
                    <span className="text-[11px] text-slate-600 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {rec.resource.estimated_minutes} 分钟
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900 line-clamp-1 mb-1">
                    {rec.resource.title}
                  </h4>
                  <p className="text-xs text-amber-800 leading-snug line-clamp-2 bg-amber-50/80 p-2 rounded-xl border border-amber-100/80 mb-3">
                    {rec.recommended_reason}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => handleOpenResource(rec.resource)}
                  className="w-full inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-2xs cursor-pointer"
                >
                  <span>立即执行</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 搜索与分类过滤器 */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pt-2">
        {/* 类型标签过滤 */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none max-w-full">
          {TYPE_FILTER_TABS.map((tab) => {
            const isActive = activeTypeFilter === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTypeFilter(tab.id)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all cursor-pointer ${
                  isActive
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* 关键字搜索框 */}
        <div className="relative w-full md:w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
          <input
            type="text"
            placeholder="搜索材料名称或关键词..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 placeholder:text-slate-600 shadow-xs focus:border-indigo-500 focus:outline-hidden"
          />
        </div>
      </div>

      {/* 资源列表网格 */}
      {isLoadingResources ? (
        <div className="p-12 text-center text-xs text-slate-600">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-600" />
          <span>正在加载该考点的学习材料...</span>
        </div>
      ) : filteredResources.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-200 p-12 text-center">
          <BookOpen className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-sm font-bold text-slate-700">暂无匹配的学习材料</p>
          <p className="text-xs text-slate-600 mt-1">
            可尝试切换资源类型或清空搜索关键词。
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredResources.map((res) => (
            <ResourceCard
              key={res.resource_id}
              resource={res}
              onOpenResource={handleOpenResource}
              onAskAI={handleAskAI}
            />
          ))}
        </div>
      )}

      {/* 例题与讲义精读模态框 */}
      <ExampleReaderModal
        resource={activeReadingResource}
        onClose={() => setActiveReadingResource(null)}
        onComplete={handleCompleteResource}
        onAskAI={handleAskAI}
      />
    </div>
  );
};
