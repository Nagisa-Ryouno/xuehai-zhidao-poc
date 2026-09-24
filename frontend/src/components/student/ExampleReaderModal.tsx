import React, { useState } from 'react';
import {
  X,
  Lightbulb,
  FileText,
  Clock,
  Flame,
  Bot,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  RotateCcw,
  Target,
  BookOpen,
} from 'lucide-react';
import type { LearningResource } from '../../types';
import { getConceptCardById } from './conceptCardData';
import { useBodyScrollLock } from '../../utils/useBodyScrollLock';

interface ExampleReaderModalProps {
  resource: LearningResource | null;
  isCompleted?: boolean;
  onClose: () => void;
  onComplete?: (resource: LearningResource) => void;
  onToggleComplete?: (resource: LearningResource, newCompleted: boolean) => void;
  onAskAI?: (resource: LearningResource) => void;
}

export const ExampleReaderModal: React.FC<ExampleReaderModalProps> = ({
  resource,
  isCompleted: isCompletedProp,
  onClose,
  onComplete,
  onToggleComplete,
  onAskAI,
}) => {
  useBodyScrollLock(!!resource);

  const [internalCompleted, setInternalCompleted] = useState<boolean>(false);
  const isCompleted = isCompletedProp !== undefined ? isCompletedProp : internalCompleted;

  if (!resource) return null;

  const card = getConceptCardById(resource.knowledge_id);
  const metadata = resource.metadata || {};
  const chapter = card?.chapter || metadata.chapter || '微观经济学考点精要';
  const kname = card?.knowledgeName || resource.title;
  const kid = resource.knowledge_id;

  const handleToggleComplete = () => {
    const nextVal = !isCompleted;
    setInternalCompleted(nextVal);
    if (onToggleComplete) {
      onToggleComplete(resource, nextVal);
    } else if (nextVal && onComplete) {
      onComplete(resource);
    }
  };

  React.useEffect(() => {
    if (!resource) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [resource, onClose]);

  const isExample = resource.resource_type === 'EXAMPLE';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="reader-modal-title"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-2xl max-h-[90vh] flex flex-col bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100 bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-white shadow-xs border border-slate-200/60">
              {isExample ? (
                <Lightbulb className="w-5 h-5 text-amber-600" />
              ) : (
                <FileText className="w-5 h-5 text-blue-600" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`px-2 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider ${
                    isExample ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'
                  }`}
                >
                  {isExample ? '典型生活与商业实例精析' : '核心讲义与理论全解'}
                </span>
                <span className="text-xs text-slate-500 font-medium">
                  {kid} · {chapter}
                </span>
              </div>
              <h3
                id="reader-modal-title"
                className="text-lg font-bold text-slate-900 mt-0.5"
              >
                {resource.title}
              </h3>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-200/60 transition-colors cursor-pointer"
            aria-label="关闭模态框"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5 text-slate-700">
          {/* 学习指标与提示 */}
          <div className="flex flex-wrap items-center justify-between p-3 rounded-2xl bg-slate-50 border border-slate-100 text-xs text-slate-600 gap-2">
            <div className="flex items-center gap-4">
              <span className="inline-flex items-center gap-1.5 font-medium">
                <Clock className="w-4 h-4 text-slate-500" />
                建议精读：{resource.estimated_minutes} 分钟
              </span>
              <span className="inline-flex items-center gap-1.5 font-medium">
                <Flame className="w-4 h-4 text-amber-500" />
                难度系数：{resource.difficulty.toFixed(1)}
              </span>
            </div>
            <span className="text-emerald-700 font-semibold flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5" />
              内部权威考点精准绑定
            </span>
          </div>

          {/* 考点与学习目标 */}
          <div className="rounded-2xl bg-indigo-50/50 border border-indigo-100 p-4 space-y-1.5">
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-indigo-700" />
              <h4 className="text-xs font-bold text-indigo-950 uppercase tracking-wider">
                考点直观应用脉络
              </h4>
              <span className="text-xs font-mono font-bold text-indigo-600 bg-white px-1.5 py-0.5 rounded border border-indigo-200">
                {kid} {kname}
              </span>
            </div>
            <p className="text-sm text-indigo-900 leading-relaxed font-medium">
              “{card?.oneLineIntuition || resource.description}”
            </p>
            {card?.learningObjective && (
              <div className="pt-2 text-xs text-indigo-800/80 flex items-center gap-1 border-t border-indigo-100/60">
                <span className="font-bold">达成目标：</span>
                <span>{card.learningObjective}</span>
              </div>
            )}
          </div>

          {/* 案例精析 / 讲义正文 */}
          {isExample ? (
            <div className="space-y-4">
              {/* 真实情境与题干 */}
              <div className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-xs space-y-2">
                <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                  <span>生活与商业真实情境拆解</span>
                </h4>
                <div className="text-sm text-slate-800 leading-relaxed bg-amber-50/40 p-4 rounded-xl border border-amber-100/80 font-sans">
                  {card?.simpleExample || metadata.example_detail || resource.summary}
                </div>
              </div>

              {/* 核心问题与思考 */}
              <div className="rounded-2xl bg-slate-50 border border-slate-200/80 p-4 space-y-1.5">
                <h5 className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                  <BookOpen className="w-4 h-4 text-slate-600" />
                  <span>核心启发问题</span>
                </h5>
                <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                  结合【{kname}】的核心经济学机制，决策者应如何基于边际权衡做出最优选择？为什么不应被沉没成本或表面数量所误导？
                </p>
              </div>

              {/* 参考解析与理论推导 */}
              <div className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-xs space-y-2">
                <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  <span>解题思路与理论精析</span>
                </h4>
                <div className="text-xs sm:text-sm text-slate-800 leading-relaxed bg-emerald-50/30 p-4 rounded-xl border border-emerald-100/80 font-sans whitespace-pre-line">
                  {card?.coreConcept || resource.summary}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* 讲义理论核心 */}
              <div className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-xs space-y-2">
                <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                  <span>核心理论定义与内在机制</span>
                </h4>
                <div className="text-xs sm:text-sm text-slate-800 leading-relaxed bg-blue-50/30 p-4 rounded-xl border border-blue-100/80 font-sans whitespace-pre-line">
                  {card?.coreConcept || resource.summary}
                </div>
              </div>

              {/* 实例佐证 */}
              {card?.simpleExample && (
                <div className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-xs space-y-2">
                  <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                    <span>现实案例应用印证</span>
                  </h4>
                  <div className="text-xs sm:text-sm text-slate-700 leading-relaxed bg-amber-50/30 p-4 rounded-xl border border-amber-100 font-sans">
                    {card.simpleExample}
                  </div>
                </div>
              )}

              {/* 导师讲义小结 */}
              <div className="rounded-2xl bg-slate-50 border border-slate-200 p-4">
                <h5 className="text-xs font-bold text-slate-700 mb-1">导师讲义小结：</h5>
                <p className="text-xs text-slate-600 leading-relaxed">
                  本讲系统剖析了【{kname}】的关键概念与推导脉络。掌握该考点不仅有助于应对期末理论分析题，更是后续高阶考点的关键基石。研读完毕后可直接进入随堂练习巩固！
                </p>
              </div>
            </div>
          )}

          {/* 易错误区与避坑指南 (若存在) */}
          {(card?.commonMisconceptions || metadata.misconceptions) && (
            <div className="rounded-2xl bg-rose-50/60 border border-rose-200/80 p-5 space-y-2">
              <h4 className="text-sm font-bold text-rose-900 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-800" />
                <span>考试常见易错陷阱与思维防坑</span>
              </h4>
              <p className="text-xs text-rose-800 leading-relaxed font-medium">
                {card?.commonMisconceptions || metadata.misconceptions}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 bg-slate-50/70">
          <div>
            {onAskAI && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onAskAI(resource);
                }}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold text-xs transition-colors cursor-pointer"
              >
                <Bot className="w-4 h-4" />
                <span>向 AI 伴学提问此内容</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100 font-semibold text-xs transition-colors cursor-pointer"
            >
              关闭
            </button>

            <button
              type="button"
              onClick={handleToggleComplete}
              className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs shadow-xs transition-all cursor-pointer ${
                isCompleted
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-300 hover:bg-emerald-100'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white'
              }`}
            >
              {isCompleted ? <RotateCcw className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
              <span>{isCompleted ? '取消完成标记' : '研读完毕，标记完成'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
