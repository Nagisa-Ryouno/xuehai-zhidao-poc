/**
 * pwa.ts
 * 学海智导 (Xuehai Zhidao) Student PWA 工具层
 *
 * 职责：
 * 1. 安全注册 Service Worker
 * 2. 检测应用是否运行于独立窗口 (Standalone / PWA Display Mode)
 * 3. 辅助判断移动优先环境与安装就绪状态
 */

/**
 * 判断当前是否处于 PWA 独立应用窗口 (display-mode: standalone)
 */
export function isStandaloneMode(): boolean {
  if (typeof window === 'undefined') return false;

  const isStandaloneMedia = window.matchMedia('(display-mode: standalone)').matches;
  const isIosStandalone = (window.navigator as unknown as { standalone?: boolean }).standalone === true;

  return isStandaloneMedia || isIosStandalone;
}

/**
 * 注册 PWA Service Worker
 */
export function registerServiceWorker(): void {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return;
  }

  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        if (!registration) return;
        console.log('[PWA] Service Worker registered with scope:', registration.scope);

        // 监听 SW 更新
        registration.onupdatefound = () => {
          const installingWorker = registration.installing;
          if (!installingWorker) return;

          installingWorker.onstatechange = () => {
            if (installingWorker.state === 'installed') {
              if (navigator.serviceWorker.controller) {
                console.log('[PWA] New content is available; please refresh.');
              } else {
                console.log('[PWA] Content is cached for offline use.');
              }
            }
          };
        };
      })
      .catch((error) => {
        // 在开发环境或不支持的环境下静默捕获，绝不影响应用渲染
        console.warn('[PWA] Service Worker registration failed:', error);
      });
  });
}
