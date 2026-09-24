import React from 'react';
import {
  X,
  BookOpen,
  Sparkles,
  Lightbulb,
  AlertTriangle,
  Target,
  ArrowRight,
  Clock,
} from 'lucide-react';
import type { ConceptCardData } from './conceptCardData';
import { useBodyScrollLock } from '../../utils/useBodyScrollLock';

interface ConceptCardModalProps {
  isOpen: boolean;
  card: ConceptCardData | null;
  onClose: () => void;
  onStartQuiz: (knowledgeId: string, knowledgeName: string) => void;
}

export const ConceptCardModal: React.FC<ConceptCardModalProps> = ({
  isOpen,
  card,
  onClose,
  onStartQuiz,
}) => {
  useBodyScrollLock(isOpen && !!card);

  React.useEffect(() => {
    if (!isOpen || !card) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, card, onClose]);

  if (!isOpen || !card) return null;

  const handleStartQuiz = () => {
    onClose();
    onStartQuiz(card.knowledgeId, card.knowledgeName);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="concept-card-title"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl max-w-xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-200/90 overflow-hidden animate-in zoom-in-95 duration-200"
      >
        {/* Modal Header */}
        <div className="px-5 sm:px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-indigo-50/70 via-white to-violet-50/70">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold font-mono">
                {card.knowledgeId}
              </span>
              <span className="text-xs font-semibold text-slate-500">
                {card.chapter}
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md font-medium border border-indigo-200/50">
                <Clock className="w-3 h-3" />
                约 {card.readingTimeSeconds} 秒速览
              </span>
            </div>
            <h2
              id="concept-card-title"
              className="text-lg sm:text-xl font-black text-slate-900 tracking-tight"
            >
              {card.knowledgeName}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭速览卡片"
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-4 text-slate-700 text-sm">
          {/* 1. 一句话直觉导引 */}
          <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50/90 to-violet-50/90 border border-indigo-100/90 text-indigo-950 shadow-2xs">
            <div className="flex items-center gap-1.5 text-xs font-black uppercase tracking-wider text-indigo-700 mb-1">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              <span>直觉导引 · 一句话顿悟</span>
            </div>
            <p className="text-sm font-semibold leading-relaxed text-indigo-900">
              “{card.oneLineIntuition}”
            </p>
          </div>

          {/* 2. 核心概念与关键结论 */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700 uppercase tracking-wider">
              <BookOpen className="w-4 h-4 text-slate-600" />
              <span>核心理论与关键机制</span>
            </div>
            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed whitespace-pre-line font-normal">
              {card.coreConcept}
            </p>
          </div>

          {/* 3. 生活/商业实例 */}
          <div className="p-4 rounded-xl bg-amber-50/60 border border-amber-200/70 space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-amber-800 uppercase tracking-wider">
              <Lightbulb className="w-4 h-4 text-amber-600" />
              <span>鲜活现实案例</span>
            </div>
            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed font-normal">
              {card.simpleExample}
            </p>
          </div>

          {/* 4. 常见认知易错陷阱 */}
          <div className="p-4 rounded-xl bg-rose-50/60 border border-rose-200/70 space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-rose-700 uppercase tracking-wider">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <span>考试易错陷阱避坑</span>
            </div>
            <p className="text-xs sm:text-sm text-rose-900 leading-relaxed font-normal">
              {card.commonMisconceptions}
            </p>
          </div>

          {/* 5. 达标学习目标 */}
          <div className="p-3.5 rounded-xl bg-emerald-50/60 border border-emerald-200/70 flex items-start gap-2 text-xs text-emerald-900">
            <Target className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
            <div>
              <span className="font-bold">掌握度达成标准：</span>
              <span>{card.learningObjective}</span>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-5 sm:px-6 py-3.5 border-t border-slate-100 bg-slate-50/80 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="text-xs text-slate-500 text-center sm:text-left">
            已阅读卡片精要？立即测验即可实时检验掌握度
          </span>
          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100 text-xs sm:text-sm font-semibold transition-all cursor-pointer min-h-[44px]"
            >
              稍后温习
            </button>
            <button
              type="button"
              onClick={handleStartQuiz}
              className="flex-1 sm:flex-none px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white text-xs sm:text-sm font-bold shadow-md shadow-indigo-500/20 flex items-center justify-center gap-2 transition-all cursor-pointer min-h-[44px]"
            >
              <span>我已读懂，开始微测验</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
