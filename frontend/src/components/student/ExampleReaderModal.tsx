import React, { useState } from 'react';
import {
  X,
  Lightbulb,
  FileText,
  Video,
  Clock,
  Flame,
  Bot,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
} from 'lucide-react';
import type { LearningResource } from '../../types';

interface ExampleReaderModalProps {
  resource: LearningResource | null;
  onClose: () => void;
  onComplete?: (resource: LearningResource) => void;
  onAskAI?: (resource: LearningResource) => void;
}

export const ExampleReaderModal: React.FC<ExampleReaderModalProps> = ({
  resource,
  onClose,
  onComplete,
  onAskAI,
}) => {
  const [isCompleted, setIsCompleted] = useState<boolean>(false);

  if (!resource) return null;

  const metadata = resource.metadata || {};
  const chapter = metadata.chapter || '微观经济学考点精要';
  const exampleDetail = metadata.example_detail || resource.summary || resource.description;
  const misconceptions = metadata.misconceptions;
  const learningObjective = metadata.learning_objective;

  const handleMarkComplete = () => {
    setIsCompleted(true);
    if (onComplete) {
      onComplete(resource);
    }
  };

  const getHeaderIcon = () => {
    if (resource.resource_type === 'EXAMPLE') {
      return <Lightbulb className="w-5 h-5 text-amber-600" />;
    }
    if (resource.resource_type === 'VIDEO') {
      return <Video className="w-5 h-5 text-purple-600" />;
    }
    return <FileText className="w-5 h-5 text-blue-600" />;
  };

  const getBadgeStyle = () => {
    if (resource.resource_type === 'EXAMPLE') {
      return 'bg-amber-100 text-amber-800';
    }
    if (resource.resource_type === 'VIDEO') {
      return 'bg-purple-100 text-purple-800';
    }
    return 'bg-blue-100 text-blue-800';
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="reader-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-2xl max-h-[90vh] flex flex-col bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100 bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-white shadow-xs border border-slate-200/60">
              {getHeaderIcon()}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`px-2 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider ${getBadgeStyle()}`}
                >
                  {resource.resource_type === 'EXAMPLE'
                    ? '典型例题精析'
                    : resource.resource_type === 'VIDEO'
                    ? '导学微课'
                    : '考点讲义'}
                </span>
                <span className="text-xs text-slate-600 font-medium">{chapter}</span>
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
            className="p-2 text-slate-600 hover:text-slate-600 rounded-full hover:bg-slate-200/60 transition-colors cursor-pointer"
            aria-label="关闭模态框"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* 学习指标与提示 */}
          <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-50 border border-slate-100 text-xs text-slate-600">
            <div className="flex items-center gap-4">
              <span className="inline-flex items-center gap-1.5 font-medium">
                <Clock className="w-4 h-4 text-slate-600" />
                建议精读：{resource.estimated_minutes} 分钟
              </span>
              <span className="inline-flex items-center gap-1.5 font-medium">
                <Flame className="w-4 h-4 text-amber-500" />
                难度系数：{resource.difficulty.toFixed(1)}
              </span>
            </div>
            <span className="text-emerald-700 font-semibold flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5" />
              内部官方题库精选
            </span>
          </div>

          {/* 核心描述 */}
          <div className="rounded-2xl bg-indigo-50/50 border border-indigo-100 p-4">
            <h4 className="text-xs font-bold text-indigo-950 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <Lightbulb className="w-4 h-4 text-indigo-800" />
              <span>考点直观应用脉络</span>
            </h4>
            <p className="text-sm text-slate-700 leading-relaxed font-normal">
              {resource.description}
            </p>
          </div>

          {/* 案例精析 / 讲义正文 */}
          <div className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-xs space-y-3">
            <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span>
                {resource.resource_type === 'EXAMPLE'
                  ? '生活与商业真实情境拆解'
                  : '讲义重点与理论核心'}
              </span>
            </h4>
            <div className="text-sm text-slate-800 leading-relaxed whitespace-pre-line bg-slate-50/60 p-4 rounded-xl border border-slate-100 font-sans">
              {exampleDetail}
            </div>
          </div>

          {/* 易错误区与避坑指南 (若存在) */}
          {misconceptions && (
            <div className="rounded-2xl bg-rose-50/60 border border-rose-200/80 p-5 space-y-2">
              <h4 className="text-sm font-bold text-rose-900 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-800" />
                <span>考试常见易错陷阱与思维防坑</span>
              </h4>
              <p className="text-xs text-rose-800 leading-relaxed font-medium">
                {misconceptions}
              </p>
            </div>
          )}

          {/* 学习目标 (若存在) */}
          {learningObjective && (
            <div className="text-xs text-slate-600 flex items-center gap-2 px-1">
              <span className="font-semibold text-slate-600">达成目标：</span>
              <span>{learningObjective}</span>
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
                <span>向 AI 伴学提问此例题</span>
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
              onClick={handleMarkComplete}
              disabled={isCompleted}
              className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs text-white shadow-xs transition-all cursor-pointer ${
                isCompleted
                  ? 'bg-emerald-600 cursor-default'
                  : 'bg-indigo-600 hover:bg-indigo-700'
              }`}
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{isCompleted ? '已标记完成' : '研读完毕，标记完成'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
