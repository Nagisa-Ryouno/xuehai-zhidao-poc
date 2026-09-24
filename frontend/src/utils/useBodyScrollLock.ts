import { useEffect, useRef } from 'react';

/**
 * useBodyScrollLock
 * =================
 * 学海智导 (Xuehai Zhidao) — 模态框与抽屉背景滚动锁定与位置还原 Hook
 * 
 * 核心保障：
 * 1. 弹窗打开时背景页面不可通过鼠标滚轮、触控板、中键或触控手势滚动；
 * 2. 严防页面回到顶部（Issue 12）：弹窗关闭后精确平稳恢复至打开前的 scrollY 位置；
 * 3. 引用计数机制：完美支持多层嵌套弹窗（如 LearningSessionModal 中嵌套 ExternalRedirectModal / ExampleReaderModal），
 *    仅在最外层弹窗完全关闭后才解锁背景；
 * 4. 滚动条宽度补偿：锁定背景时自动为 body 增加 paddingRight，彻底消除滚动条消失导致的页面横向跳动 (Layout Shift)。
 */

let activeLockCount = 0;
let savedScrollY = 0;
let previousOverflow = '';
let previousTouchAction = '';
let previousPaddingRight = '';

export function getActiveLockCount(): number {
  return activeLockCount;
}

export function getSavedScrollY(): number {
  return savedScrollY;
}

export function lockBodyScroll() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;

  if (activeLockCount === 0) {
    savedScrollY =
      window.scrollY ||
      window.pageYOffset ||
      document.documentElement.scrollTop ||
      document.body.scrollTop ||
      0;
    previousOverflow = document.body.style.overflow;
    previousTouchAction = document.body.style.touchAction;
    previousPaddingRight = document.body.style.paddingRight;

    // 计算当前浏览器原生滚动条宽度并补偿 paddingRight，消除横向跳动
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    if (scrollbarWidth > 0) {
      document.body.style.paddingRight = `${scrollbarWidth}px`;
    }

    document.body.style.overflow = 'hidden';
    document.body.style.touchAction = 'none';
  }
  activeLockCount++;
}

export function unlockBodyScroll() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;

  activeLockCount = Math.max(0, activeLockCount - 1);
  if (activeLockCount === 0) {
    document.body.style.overflow = previousOverflow;
    document.body.style.touchAction = previousTouchAction;
    document.body.style.paddingRight = previousPaddingRight;

    // 精准恢复到打开弹窗前的坐标，避免跳回顶部
    window.scrollTo({
      top: savedScrollY,
      behavior: 'instant' as ScrollBehavior,
    });
  }
}

export function useBodyScrollLock(isOpen: boolean) {
  const isLockedRef = useRef(false);

  useEffect(() => {
    if (isOpen && !isLockedRef.current) {
      lockBodyScroll();
      isLockedRef.current = true;
    } else if (!isOpen && isLockedRef.current) {
      unlockBodyScroll();
      isLockedRef.current = false;
    }

    return () => {
      if (isLockedRef.current) {
        unlockBodyScroll();
        isLockedRef.current = false;
      }
    };
  }, [isOpen]);
}
