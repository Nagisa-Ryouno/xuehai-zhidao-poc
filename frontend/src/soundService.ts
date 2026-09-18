/**
 * soundService.ts
 * 界面音效服务：语义化音效播放、音量与静音管理
 *
 * 音效素材：UI SFX (https://github.com/romainsimon/uisfx)，CC0 授权，见 public/sounds/NOTICE.md
 * 设计要点：
 * - 懒加载 + 元素池：首次播放时创建 Audio 元素，避免自动播放限制（播放均由用户交互触发）
 * - 静音状态持久化 localStorage，可订阅（供 Header 开关按钮同步）
 * - 播放失败静默降级，绝不阻断交互
 */

const SOUND_FILES = {
  select: '/sounds/select.mp3',
  press: '/sounds/press.mp3',
  success: '/sounds/success.mp3',
  error: '/sounds/error.mp3',
  notification: '/sounds/notification.mp3',
  open: '/sounds/open.mp3',
  close: '/sounds/close.mp3',
  toggle: '/sounds/toggle-on.mp3',
  levelup: '/sounds/level-up.mp3',
  swipe: '/sounds/swipe.mp3',
  send: '/sounds/send.mp3',
} as const;

export type SoundName = keyof typeof SOUND_FILES;

const MUTE_KEY = 'xuehai-sound-muted';
const DEFAULT_VOLUME = 0.35;

const audioPool = new Map<SoundName, HTMLAudioElement>();
const muteListeners = new Set<(muted: boolean) => void>();

let muted = false;
try {
  muted = localStorage.getItem(MUTE_KEY) === '1';
} catch {
  muted = false;
}

function getAudio(name: SoundName): HTMLAudioElement | null {
  if (typeof Audio === 'undefined') return null;
  let el = audioPool.get(name);
  if (!el) {
    el = new Audio(SOUND_FILES[name]);
    el.preload = 'auto';
    el.volume = DEFAULT_VOLUME;
    audioPool.set(name, el);
  }
  return el;
}

/** 播放指定语义音效；静音或环境不支持时静默跳过 */
export function playSound(name: SoundName): void {
  if (muted) return;
  const el = getAudio(name);
  if (!el) return;
  try {
    el.currentTime = 0;
    void el.play().catch(() => {
      /* 浏览器自动播放策略拦截时忽略，不影响交互 */
    });
  } catch {
    /* 忽略播放异常 */
  }
}

export function isSoundMuted(): boolean {
  return muted;
}

export function setSoundMuted(next: boolean): void {
  muted = next;
  try {
    localStorage.setItem(MUTE_KEY, next ? '1' : '0');
  } catch {
    /* 存储不可用时仅保留内存态 */
  }
  muteListeners.forEach((fn) => fn(muted));
}

export function subscribeSoundMuted(fn: (muted: boolean) => void): () => void {
  muteListeners.add(fn);
  return () => {
    muteListeners.delete(fn);
  };
}
