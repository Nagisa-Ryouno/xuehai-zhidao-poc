/**
 * bottomSheetModel.ts
 * 移动端 Bottom Sheet 状态机与样式规范契约
 */

export type BottomSheetDismissReason = 'backdrop_click' | 'close_button' | 'escape_key';

export interface BottomSheetState<T = unknown> {
  isOpen: boolean;
  activePayload: T | null;
  lastDismissReason?: BottomSheetDismissReason;
}

export function createBottomSheetState<T = unknown>(): BottomSheetState<T> {
  return {
    isOpen: false,
    activePayload: null,
  };
}

export function openBottomSheet<T = unknown>(
  state: BottomSheetState<T>,
  payload: T
): BottomSheetState<T> {
  return {
    ...state,
    isOpen: true,
    activePayload: payload,
  };
}

export function closeBottomSheet<T = unknown>(
  state: BottomSheetState<T>,
  reason: BottomSheetDismissReason = 'close_button'
): BottomSheetState<T> {
  return {
    ...state,
    isOpen: false,
    lastDismissReason: reason,
  };
}

export const BOTTOM_SHEET_STYLE_CLASSES = {
  backdrop:
    'fixed inset-0 bg-slate-950/50 backdrop-blur-xs z-50 transition-opacity duration-200',
  sheet:
    'fixed inset-x-0 bottom-0 z-50 bg-[rgba(253,246,238,.94)] backdrop-blur-2xl rounded-t-3xl shadow-2xl border-t border-white/80 max-h-[85vh] flex flex-col pb-[env(safe-area-inset-bottom)] animate-sheet-up',
  handleBar: 'w-12 h-1.5 bg-slate-300 rounded-full mx-auto my-2.5 shrink-0',
  header: 'px-6 py-3.5 border-b border-slate-100 flex items-center justify-between shrink-0',
  body: 'overflow-y-auto overscroll-contain flex-1 px-6 py-4',
} as const;
