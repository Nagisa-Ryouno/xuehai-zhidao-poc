import React, { useEffect, useCallback } from 'react';
import { X } from 'lucide-react';
import { BOTTOM_SHEET_STYLE_CLASSES } from './bottomSheetModel';
import { useBodyScrollLock } from '../../utils/useBodyScrollLock';

export interface BottomSheetProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
}

export const BottomSheet: React.FC<BottomSheetProps> = ({
  open,
  onClose,
  title,
  description,
  children,
}) => {
  useBodyScrollLock(open);

  // 监听 ESC 键关闭
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title || '详情抽屉'}
      className="fixed inset-0 z-50 overflow-hidden flex flex-col justify-end"
    >
      {/* 背景遮罩 (Backdrop) */}
      <div
        className={BOTTOM_SHEET_STYLE_CLASSES.backdrop}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* 底部滑出面板 (Sheet Container) */}
      <div className={BOTTOM_SHEET_STYLE_CLASSES.sheet}>
        {/* 顶部手势指示条 */}
        <div className={BOTTOM_SHEET_STYLE_CLASSES.handleBar} />

        {/* 弹窗顶栏 */}
        <div className={BOTTOM_SHEET_STYLE_CLASSES.header}>
          <div>
            {title && (
              <h3 className="text-base font-bold text-slate-900 leading-tight">
                {title}
              </h3>
            )}
            {description && (
              <p className="text-xs text-slate-500 mt-0.5">{description}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-11 h-11 flex items-center justify-center rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label="关闭面板"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 可滚动正文区域 */}
        <div className={BOTTOM_SHEET_STYLE_CLASSES.body}>{children}</div>
      </div>
    </div>
  );
};
