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
let previousPosition = '';
let previousTop = '';
let previousWidth = '';
let isListenerAttached = false;

export function getActiveLockCount(): number {
  return activeLockCount;
}

export function getSavedScrollY(): number {
  return savedScrollY;
}

function handlePreventScrollOutside(e: TouchEvent | WheelEvent) {
  const target = e.target as HTMLElement | null;
  if (!target) return;

  // 检查当前事件触发源是否位于允许滚动的子容器内部
  let curr: HTMLElement | null = target;
  let insideScrollable = false;

  while (curr && curr !== document.body && curr !== document.documentElement) {
    if (typeof window !== 'undefined' && window.getComputedStyle) {
      try {
        const style = window.getComputedStyle(curr);
        const overflowY = style ? style.overflowY : '';
        if ((overflowY === 'auto' || overflowY === 'scroll') && curr.scrollHeight > curr.clientHeight) {
          insideScrollable = true;
          break;
        }
      } catch {
        // Safe fallback in test environments
      }
    }
    // 遇到弹窗遮罩根节点停止向上追溯
    if (curr.getAttribute && (curr.getAttribute('role') === 'dialog' || (curr.classList && curr.classList.contains('fixed')))) {
      break;
    }
    curr = curr.parentElement;
  }

  // 若处于遮罩背景、弹窗空白处或不可滚动区域，彻底阻断事件向下穿透
  if (!insideScrollable) {
    if (e.cancelable) {
      e.preventDefault();
    }
  }
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

    if ('position' in document.body.style) {
      previousPosition = document.body.style.position;
      previousTop = document.body.style.top;
      previousWidth = document.body.style.width;
    }

    // 计算当前浏览器原生滚动条宽度并补偿 paddingRight，消除横向跳动
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    if (scrollbarWidth > 0) {
      document.body.style.paddingRight = `${scrollbarWidth}px`;
    }

    document.body.style.overflow = 'hidden';
    document.body.style.touchAction = 'none';

    // 移动端与桌面端双重物理锁死：防止背景页面产生任何位移
    if ('position' in document.body.style) {
      document.body.style.position = 'fixed';
      document.body.style.top = `-${savedScrollY}px`;
      document.body.style.width = '100%';
    }

    if (document.documentElement && document.documentElement.style && 'overscrollBehavior' in document.documentElement.style) {
      document.documentElement.style.overscrollBehavior = 'none';
    }

    // 事件层非 passive 阻断：杜绝移动端 touchmove 与桌面 wheel 击穿遮罩
    if (!isListenerAttached && typeof window.addEventListener === 'function') {
      window.addEventListener('touchmove', handlePreventScrollOutside, { passive: false });
      window.addEventListener('wheel', handlePreventScrollOutside, { passive: false });
      isListenerAttached = true;
    }
  }
  activeLockCount++;
}

export function unlockBodyScroll() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;

  activeLockCount = Math.max(0, activeLockCount - 1);
  if (activeLockCount === 0) {
    if (isListenerAttached && typeof window.removeEventListener === 'function') {
      window.removeEventListener('touchmove', handlePreventScrollOutside);
      window.removeEventListener('wheel', handlePreventScrollOutside);
      isListenerAttached = false;
    }

    const targetScrollY = savedScrollY;

    document.body.style.overflow = previousOverflow;
    document.body.style.touchAction = previousTouchAction;
    document.body.style.paddingRight = previousPaddingRight;

    if ('position' in document.body.style) {
      document.body.style.position = previousPosition;
      document.body.style.top = previousTop;
      document.body.style.width = previousWidth;
    }

    if (document.documentElement && document.documentElement.style && 'overscrollBehavior' in document.documentElement.style) {
      document.documentElement.style.overscrollBehavior = '';
    }

    // 精准恢复到打开弹窗前的坐标，并在连续帧中确认恢复，避免异步渲染或布局重排导致跳顶
    window.scrollTo({
      top: targetScrollY,
      behavior: 'instant' as ScrollBehavior,
    });

    if (typeof window.requestAnimationFrame === 'function') {
      window.requestAnimationFrame(() => {
        window.scrollTo({
          top: targetScrollY,
          behavior: 'instant' as ScrollBehavior,
        });
        window.requestAnimationFrame(() => {
          window.scrollTo({
            top: targetScrollY,
            behavior: 'instant' as ScrollBehavior,
          });
        });
      });
    }
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
