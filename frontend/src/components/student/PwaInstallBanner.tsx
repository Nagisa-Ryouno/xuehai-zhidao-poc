import React, { useState, useEffect } from 'react';
import { Download } from 'lucide-react';
import { isStandaloneMode } from '../../pwa';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
}

export const PWA_DISMISSED_KEY = 'pwa_install_dismissed';

export const PwaInstallBanner: React.FC = () => {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isVisible, setIsVisible] = useState<boolean>(false);

  useEffect(() => {
    // 1. 若当前已经处于 Standalone 独立窗口，不展示安装引导
    if (isStandaloneMode()) {
      return;
    }

    // 2. 若用户之前已经选择过“稍后再说”，不再重复骚扰
    try {
      const dismissed = localStorage.getItem(PWA_DISMISSED_KEY);
      if (dismissed === 'true') {
        return;
      }
    } catch {
      // 容错处理
    }

    // 3. 监听浏览器原生 beforeinstallprompt 事件 (Chromium / Edge / Android)
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setIsVisible(true);
    };

    // 4. 监听应用安装完成事件
    const handleAppInstalled = () => {
      setIsVisible(false);
      setDeferredPrompt(null);
      try {
        localStorage.setItem(PWA_DISMISSED_KEY, 'true');
      } catch {
        // 容错
      }
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, []);

  // 点击安装触发浏览器安装确认面板
  const handleInstall = async () => {
    if (!deferredPrompt) return;

    try {
      await deferredPrompt.prompt();
      const choiceResult = await deferredPrompt.userChoice;
      if (choiceResult.outcome === 'accepted') {
        setIsVisible(false);
        setDeferredPrompt(null);
        try {
          localStorage.setItem(PWA_DISMISSED_KEY, 'true');
        } catch {
          // 容错
        }
      }
    } catch (err) {
      console.warn('[PWA] Error launching install prompt:', err);
    }
  };

  // 点击稍后再说隐藏提示并记录免打扰标记
  const handleDismiss = () => {
    setIsVisible(false);
    try {
      localStorage.setItem(PWA_DISMISSED_KEY, 'true');
    } catch {
      // 容错
    }
  };

  if (!isVisible || !deferredPrompt) {
    return null;
  }

  return (
    <div
      data-testid="pwa-install-banner"
      className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-50/90 via-white to-purple-50/50 border border-indigo-100/90 p-4 shadow-xs mb-4 transition-all"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start sm:items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-600 text-white shadow-2xs shrink-0 mt-0.5 sm:mt-0">
            <Download className="w-4 h-4" />
          </div>
          <div>
            <h4
              data-testid="pwa-banner-title"
              className="text-sm font-bold text-slate-900"
            >
              📱 安装学海智导
            </h4>
            <p
              data-testid="pwa-banner-desc"
              className="text-xs text-slate-600 mt-0.5"
            >
              把学习空间放到主屏幕，下次打开更方便。
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          <button
            type="button"
            data-testid="pwa-dismiss-btn"
            onClick={handleDismiss}
            className="px-3 py-1.5 rounded-xl text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            稍后再说
          </button>
          <button
            type="button"
            data-testid="pwa-install-btn"
            onClick={handleInstall}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 active:scale-98 transition-all shadow-2xs cursor-pointer"
          >
            <span>安装</span>
          </button>
        </div>
      </div>
    </div>
  );
};
