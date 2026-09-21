import React, { useEffect } from 'react';
import { ExternalLink, X, GraduationCap, ShieldCheck } from 'lucide-react';
import type { LearningResource } from '../../types';

interface ExternalRedirectModalProps {
  resource: LearningResource | null;
  onClose: () => void;
  onConfirm: (resource: LearningResource) => void;
}

export const ExternalRedirectModal: React.FC<ExternalRedirectModalProps> = ({
  resource,
  onClose,
  onConfirm,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!resource) return null;

  const metadata = resource.metadata || {};
  const university = metadata.university;
  const instructor = metadata.instructor;
  const course = metadata.course || resource.title;
  const provider = metadata.provider || '中国大学MOOC';

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid="external-redirect-modal"
      aria-labelledby="external-redirect-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 animate-in fade-in duration-150"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-200 p-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] overflow-hidden">
        {/* 关闭按钮 */}
        <button
          type="button"
          onClick={onClose}
          aria-label="关闭提示"
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* 顶部图标与标题 */}
        <div className="flex items-start gap-3.5 mb-4">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-xl shrink-0">
            <ExternalLink className="w-6 h-6" />
          </div>
          <div>
            <h3
              id="external-redirect-title"
              className="text-lg font-bold text-slate-900 leading-snug"
            >
              即将离开学海智导
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              你将前往中国大学MOOC官方页面继续学习。
            </p>
          </div>
        </div>

        {/* 课程详情信息卡 */}
        <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-4 mb-4 text-left space-y-2.5">
          <div className="flex items-start justify-between gap-2">
            <h4 className="text-sm font-bold text-slate-800 line-clamp-2">
              {course}
            </h4>
            <span className="shrink-0 inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-100 text-blue-700">
              {provider}
            </span>
          </div>

          {(university || instructor) && (
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
              {university && (
                <span className="inline-flex items-center gap-1 font-medium text-slate-700">
                  <GraduationCap className="w-3.5 h-3.5 text-slate-400" />
                  <span>{university}</span>
                </span>
              )}
              {instructor && (
                <span className="text-slate-500">
                  主讲：{instructor}
                </span>
              )}
            </div>
          )}

          <div className="pt-2 border-t border-slate-200/60 flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
            <span>官方权威认证链接 (icourse163.org)</span>
          </div>
        </div>

        <p className="text-xs text-slate-500 leading-relaxed mb-6">
          在外部平台完成课程学习后，可随时返回学海智导，在任务中心完成微测验以检验学习成效。
        </p>

        {/* 操作按钮组 */}
        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            data-testid="cancel-redirect-btn"
            onClick={onClose}
            className="px-4 py-2 min-h-[44px] inline-flex items-center justify-center text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
          >
            取消
          </button>
          <button
            type="button"
            data-testid="external-redirect-confirm-btn"
            onClick={() => onConfirm(resource)}
            className="inline-flex items-center justify-center gap-1.5 px-5 py-2 min-h-[44px] text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-all shadow-xs cursor-pointer"
          >
            <span>前往学习</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
