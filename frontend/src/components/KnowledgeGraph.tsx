import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  MarkerType,
  type Node,
  type Edge,
  type NodeTypes,
  type ReactFlowInstance,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  Network,
  Sparkles,
  Search,
  X,
  RotateCcw,
  AlertTriangle,
} from 'lucide-react';

import { KnowledgeGraphNode } from './KnowledgeGraphNode';
import { KnowledgeGraphDetailDrawer } from './KnowledgeGraphDetailDrawer';
import { getStudentKnowledgeGraph } from '../api';
import type {
  KnowledgeGraphResponse,
  KnowledgeGraphNodeData,
  GraphFilterType,
  PathState,
} from '../types';

const nodeTypes: NodeTypes = {
  knowledgeNode: KnowledgeGraphNode,
};

interface KnowledgeGraphProps {
  currentStudentId: string;
  studentName: string;
  pathStates?: Record<string, PathState>;
  onStartQuiz?: (knowledgeId: string, knowledgeName: string) => void;
  onJumpToAssistant?: () => void;
}

export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  currentStudentId,
  studentName,
  pathStates,
  onStartQuiz,
  onJumpToAssistant,
}) => {
  const [graphData, setGraphData] = useState<KnowledgeGraphResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // 状态筛选与关键词搜索
  const [activeFilter, setActiveFilter] = useState<GraphFilterType>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // 选中节点
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);

  // 加载当前学生知识图谱数据
  const loadGraph = useCallback(async (sid: string) => {
    setLoading(true);
    setError(null);
    setSelectedNodeId(null);
    setSearchQuery('');
    setActiveFilter('all');

    try {
      const data = await getStudentKnowledgeGraph(sid);
      setGraphData(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('无法加载知识图谱拓扑数据，请确认后端 API 是否正常');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGraph(currentStudentId);
  }, [currentStudentId, loadGraph]);

  // 所有节点 Map 索引（方便快速获取上/下游节点信息）
  const allNodesMap = useMemo<Record<string, KnowledgeGraphNodeData>>(() => {
    if (!graphData) return {};
    const map: Record<string, KnowledgeGraphNodeData> = {};
    for (const n of graphData.nodes) {
      map[n.id] = n.data;
    }
    return map;
  }, [graphData]);

  // 根据当前筛选与搜索条件计算节点显示状态
  useEffect(() => {
    if (!graphData) return;

    const query = searchQuery.trim().toLowerCase();

    const formattedNodes: Node[] = graphData.nodes.map((n) => {
      const d = n.data;
      let matchesFilter = true;

      if (activeFilter === 'weak') {
        matchesFilter = d.is_weak;
      } else if (activeFilter === 'recommended') {
        matchesFilter = d.is_recommended;
      } else if (activeFilter === 'prerequisite') {
        matchesFilter = d.is_prerequisite;
      }

      const matchesSearch =
        !query ||
        d.knowledge_id.toLowerCase().includes(query) ||
        d.knowledge_name.toLowerCase().includes(query) ||
        d.chapter.toLowerCase().includes(query);

      const isFilteredOut = !matchesFilter || (!matchesSearch && query.length > 0);
      const isSearched = query.length > 0 && matchesSearch;

      return {
        id: n.id,
        type: 'knowledgeNode',
        position: n.position,
        selected: n.id === selectedNodeId,
        data: {
          ...d,
          isFilteredOut,
          isSearched,
        },
      };
    });

    // 格式化 Edges，区分前置依赖边与 AI 推荐流光边
    const formattedEdges: Edge[] = graphData.edges.map((e) => {
      const isPath = e.type === 'pathEdge' || (e.data && e.data.is_active_path);
      const isSpecialPath = e.type === 'pathEdge';

      return {
        id: e.id,
        source: e.source,
        target: e.target,
        type: 'smoothstep',
        animated: isPath,
        style: isSpecialPath
          ? {
              stroke: '#8b5cf6',
              strokeWidth: 2.5,
              strokeDasharray: '6,4',
            }
          : isPath
          ? {
              stroke: '#6366f1',
              strokeWidth: 2.5,
            }
          : {
              stroke: '#94a3b8',
              strokeWidth: 1.5,
            },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isSpecialPath ? '#8b5cf6' : isPath ? '#6366f1' : '#94a3b8',
          width: 14,
          height: 14,
        },
        data: e.data,
      };
    });

    setNodes(formattedNodes);
    setEdges(formattedEdges);
  }, [graphData, activeFilter, searchQuery, selectedNodeId, setNodes, setEdges]);

  // 点击节点事件
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNodeId(node.id);
    },
    []
  );

  // 点击画布空白区域取消选中
  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  // 在抽屉中点击前置/后续节点，平滑聚焦
  const handleSelectNodeFromDrawer = useCallback(
    (nodeId: string) => {
      setSelectedNodeId(nodeId);
      const targetNode = nodes.find((n) => n.id === nodeId);
      if (targetNode && reactFlowInstance.current) {
        reactFlowInstance.current.setCenter(
          targetNode.position.x + 120,
          targetNode.position.y + 60,
          { zoom: 1.1, duration: 600 }
        );
      }
    },
    [nodes]
  );

  // 选中的节点数据
  const selectedNodeData = useMemo(() => {
    if (!selectedNodeId) return null;
    return allNodesMap[selectedNodeId] || null;
  }, [selectedNodeId, allNodesMap]);

  return (
    <section className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden flex flex-col relative">
      {/* 顶部标题栏与学生学情统计 */}
      <div className="p-6 pb-4 border-b border-slate-100 bg-gradient-to-r from-slate-50/90 via-indigo-50/20 to-white flex flex-col gap-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-md shadow-indigo-100">
                <Network className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                    AI 知识图谱可视化工作台
                  </h2>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
                    {studentName} · 专属知识网络
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  基于微观经济学 30 个核心考点与真实前置拓扑网络，动态结合个人作答学情精准透视
                </p>
              </div>
            </div>
          </div>

          {/* 学情统计指标胶囊 */}
          {graphData && (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <div className="px-3 py-1.5 rounded-xl bg-white border border-slate-200 shadow-2xs flex items-center gap-1.5">
                <span className="text-slate-400">总体掌握</span>
                <span className="font-bold text-slate-800">
                  {graphData.stats.average_accuracy.toFixed(1)}%
                </span>
              </div>
              <div className="px-3 py-1.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                <span>薄弱考点</span>
                <span className="font-bold">{graphData.stats.weak_count}</span>
              </div>
              <div className="px-3 py-1.5 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-800 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                <span>AI推荐路径</span>
                <span className="font-bold">{graphData.stats.recommended_count} 阶段</span>
              </div>
              <div className="px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-slate-600 flex items-center gap-1.5">
                <span>知识全集</span>
                <span className="font-semibold">
                  已学 {graphData.stats.studied_count} / 未学 {graphData.stats.unstudied_count}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* AI 图谱洞察卡片 (AI Insight) */}
        {graphData?.ai_insight && (
          <div className="p-3.5 rounded-xl bg-gradient-to-r from-indigo-50/70 via-indigo-50/40 to-blue-50/40 border border-indigo-100 flex items-start gap-3">
            <div className="p-1 rounded-lg bg-indigo-600 text-white shrink-0 mt-0.5 shadow-xs">
              <Sparkles className="w-3.5 h-3.5" />
            </div>
            <div className="flex-1 text-xs text-slate-700 leading-relaxed">
              <span className="font-bold text-indigo-900 mr-1.5">AI 图谱导师洞察：</span>
              <span>{graphData.ai_insight}</span>
            </div>
          </div>
        )}

        {/* 筛选与搜索工具条 */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
          {/* 分类筛选 Tabs */}
          <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl border border-slate-200/80 text-xs">
            <button
              onClick={() => setActiveFilter('all')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                activeFilter === 'all'
                  ? 'bg-white text-indigo-700 shadow-2xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              全部考点 (30)
            </button>
            <button
              onClick={() => setActiveFilter('weak')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                activeFilter === 'weak'
                  ? 'bg-white text-rose-700 shadow-2xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              薄弱考点 ({graphData?.stats.weak_count ?? 0})
            </button>
            <button
              onClick={() => setActiveFilter('recommended')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                activeFilter === 'recommended'
                  ? 'bg-white text-indigo-700 shadow-2xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              学习路径 ({graphData?.stats.recommended_count ?? 0})
            </button>
            <button
              onClick={() => setActiveFilter('prerequisite')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                activeFilter === 'prerequisite'
                  ? 'bg-white text-amber-700 shadow-2xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              前置基石
            </button>
          </div>

          {/* 实时搜索框 */}
          <div className="relative flex-1 sm:max-w-xs">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索知识点名称或编号 (如: 弹性 / K01)..."
              className="w-full pl-9 pr-8 py-1.5 text-xs bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 text-slate-800 placeholder-slate-400 transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 图例说明栏 */}
      <div className="px-6 py-2 bg-slate-50/60 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-500">
        <div className="flex flex-wrap items-center gap-4">
          <span className="font-semibold text-slate-700">图谱图例：</span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
            <span>薄弱考点 (&lt;60%)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
            <span>待巩固 (60~70%)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
            <span>掌握良好 (≥70%)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-300 inline-block" />
            <span>尚无学习记录 (null)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-indigo-600 text-white flex items-center justify-center text-[8px] font-bold">
              ★
            </span>
            <span>AI推荐路径 Stage</span>
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="w-4 h-0.5 bg-slate-400 inline-block" />
            <span>前置依赖连线</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-4 h-0.5 border-t-2 border-indigo-500 border-dashed inline-block" />
            <span className="text-indigo-600 font-medium">AI 推荐时序流光</span>
          </span>
        </div>
      </div>

      {/* React Flow 画布主体 */}
      <div className="w-full h-[660px] bg-slate-50/40 relative">
        {loading ? (
          <div className="w-full h-full flex flex-col items-center justify-center gap-3 text-slate-500">
            <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs">正在渲染 {studentName} 的个性化知识网络拓扑...</span>
          </div>
        ) : error ? (
          <div className="w-full h-full flex flex-col items-center justify-center gap-3 text-rose-600 p-6 text-center">
            <AlertTriangle className="w-8 h-8" />
            <p className="text-sm font-semibold">{error}</p>
            <button
              onClick={() => loadGraph(currentStudentId)}
              className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 transition-colors flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              重新加载知识图谱
            </button>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            onInit={(instance) => {
              reactFlowInstance.current = instance;
              instance.fitView({ padding: 0.15, duration: 600 });
            }}
            fitView
            minZoom={0.2}
            maxZoom={1.6}
            defaultViewport={{ x: 0, y: 0, zoom: 0.75 }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={20}
              size={1}
              color="#cbd5e1"
            />
            <Controls
              className="!bg-white !border !border-slate-200 !rounded-xl !shadow-md !overflow-hidden"
              showInteractive={false}
            />
            <MiniMap
              className="!bg-white/90 !border !border-slate-200 !rounded-xl !shadow-md"
              zoomable
              pannable
              nodeColor={(n) => {
                const d = n.data as unknown as KnowledgeGraphNodeData;
                if (d.status === 'WEAK') return '#f43f5e';
                if (d.status === 'NEED_REVIEW') return '#f59e0b';
                if (d.status === 'MASTERED') return '#10b981';
                return '#cbd5e1';
              }}
            />
          </ReactFlow>
        )}
      </div>

      {/* 侧边节点详情与问问 AI 抽屉 */}
      <KnowledgeGraphDetailDrawer
        nodeData={selectedNodeData}
        studentId={currentStudentId}
        studentName={studentName}
        allNodesMap={allNodesMap}
        pathState={selectedNodeData ? pathStates?.[selectedNodeData.knowledge_id] : undefined}
        onClose={() => setSelectedNodeId(null)}
        onSelectNode={handleSelectNodeFromDrawer}
        onStartQuiz={onStartQuiz}
        onJumpToAssistant={onJumpToAssistant}
      />
    </section>
  );
};
