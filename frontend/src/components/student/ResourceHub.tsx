import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  BookOpen,
  Sparkles,
  Search,
  ArrowRight,
  RefreshCw,
  Clock,
} from 'lucide-react';
import type {
  LearningResource,
  ResourceType,
  RecommendedResourcesResponse,
} from '../../types';
import {
  getResourcesByKnowledge,
  getRecommendedResources,
  recordResourceEvent,
} from '../../api';
import { ResourceCard } from './ResourceCard';
import { ExampleReaderModal } from './ExampleReaderModal';
import { ALL_CONCEPT_CARDS, type ConceptCardData } from './conceptCardData';

interface ResourceHubProps {
  studentId: string;
  initialKnowledgeId?: string;
  onOpenConceptCard: (knowledgeId: string, knowledgeName: string) => void;
  onStartQuiz: (knowledgeId: string, knowledgeName: string) => void;
  onAskAI: (knowledgeId: string, knowledgeName: string, prefillMessage?: string) => void;
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

  // 例题阅读模态框状态
  const [activeReadingResource, setActiveReadingResource] = useState<LearningResource | null>(null);

  // 获取当前考点名称
  const currentKnowledgeName = useMemo(() => {
    const found = ALL_CONCEPT_CARDS.find((c: ConceptCardData) => c.knowledgeId === selectedKnowledgeId);
    return found ? found.knowledgeName : selectedKnowledgeId;
  }, [selectedKnowledgeId]);

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
  }, [fetchRecommendations, fetchResources]);

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

    if (res.resource_type === 'CONCEPT_CARD') {
      onOpenConceptCard(res.knowledge_id, currentKnowledgeName);
    } else if (res.resource_type === 'PRACTICE') {
      onStartQuiz(res.knowledge_id, currentKnowledgeName);
    } else {
      setActiveReadingResource(res);
    }
  };

  // 标记完成
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
  };

  // 问问 AI 伴学
  const handleAskAI = (res: LearningResource) => {
    const prefill = `请帮我讲解关于【${res.title}】的核心思路与关键注意点：${res.description}`;
    onAskAI(res.knowledge_id, currentKnowledgeName, prefill);
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
            提供覆盖 30 考点的精要微卡、生活与商业例题、靶向微练与精讲讲义，助力扎实通关。
          </p>
        </div>

        {/* 考点下拉选择器 */}
        <div className="flex items-center gap-2">
          <label htmlFor="knowledge-select" className="text-xs font-bold text-slate-600 whitespace-nowrap">
            当前考点：
          </label>
          <select
            id="knowledge-select"
            value={selectedKnowledgeId}
            onChange={(e) => setSelectedKnowledgeId(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs sm:text-sm font-semibold text-slate-800 shadow-xs focus:border-indigo-500 focus:outline-hidden cursor-pointer"
          >
            {ALL_CONCEPT_CARDS.map((card: ConceptCardData) => (
              <option key={card.knowledgeId} value={card.knowledgeId}>
                {card.knowledgeId} - {card.knowledgeName} ({card.chapter})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 🎯 自适应推荐横幅 (Resource Recommendations) */}
      {recommendedData && recommendedData.recommendations.length > 0 && (
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-500/10 via-white to-amber-500/10 border border-indigo-200/80 p-6 shadow-xs">
          <div className="flex items-start justify-between gap-4 mb-4">
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
                </div>
                <h3 className="text-base sm:text-lg font-bold text-slate-900 mt-0.5">
                  为你量身定制的步骤建议
                </h3>
              </div>
            </div>

            <button
              type="button"
              onClick={fetchRecommendations}
              className="p-2 rounded-xl text-slate-600 hover:text-indigo-600 hover:bg-white/80 transition-colors cursor-pointer"
              title="刷新推荐"
            >
              <RefreshCw className={`w-4 h-4 ${isLoadingRecs ? 'animate-spin' : ''}`} />
            </button>
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
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
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
