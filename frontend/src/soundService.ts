/**
 * soundService.ts
 * 界面音效服务（v2 · 清透柔和合成音效）
 *
 * 全部音效用 Web Audio API 实时合成，参考 UI 音效设计原则：
 * - 仅使用正弦波/三角波（无方波/锯齿波的刺耳谐波）
 * - 柔和起音包络（4–18ms attack）+ 指数衰减
 * - 主输出经 2400Hz 低通滤波，整体清透不刺耳
 * - 短时长（70–600ms）、低音量、语义化命名
 *
 * 静音状态持久化 localStorage，可订阅；播放失败静默降级，绝不阻断交互。
 */

export type SoundName =
  | 'select'
  | 'press'
  | 'success'
  | 'error'
  | 'notification'
  | 'open'
  | 'close'
  | 'toggle'
  | 'levelup'
  | 'swipe'
  | 'send';

const MUTE_KEY = 'xuehai-sound-muted';
const muteListeners = new Set<(muted: boolean) => void>();

let muted = false;
try {
  muted = localStorage.getItem(MUTE_KEY) === '1';
} catch {
  muted = false;
}

let ctx: AudioContext | null = null;
let masterFilter: BiquadFilterNode | null = null;
let masterGain: GainNode | null = null;

function getContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  const AC =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AC) return null;
  if (!ctx) {
    ctx = new AC();
    masterFilter = ctx.createBiquadFilter();
    masterFilter.type = 'lowpass';
    masterFilter.frequency.value = 2400;
    masterGain = ctx.createGain();
    masterGain.gain.value = 0.9;
    masterFilter.connect(masterGain);
    masterGain.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') {
    void ctx.resume().catch(() => {});
  }
  return ctx;
}

interface ToneOpts {
  freq: number;
  freqEnd?: number;
  type?: OscillatorType;
  delay?: number;
  attack?: number;
  decay: number;
  peak: number;
}

/** 播放一个柔和音符：柔和起音 + 指数衰减，可带上行/下行滑音 */
function tone(c: AudioContext, opts: ToneOpts): void {
  const { freq, freqEnd, type = 'sine', delay = 0, attack = 0.008, decay, peak } = opts;
  const t0 = c.currentTime + delay;
  const osc = c.createOscillator();
  const gain = c.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, t0);
  if (freqEnd) {
    osc.frequency.exponentialRampToValueAtTime(freqEnd, t0 + decay);
  }
  gain.gain.setValueAtTime(0.0001, t0);
  gain.gain.linearRampToValueAtTime(peak, t0 + attack);
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + decay);
  osc.connect(gain);
  gain.connect(masterFilter!);
  osc.start(t0);
  osc.stop(t0 + decay + 0.05);
}

/** 各语义音效的柔和音色设计（频率 Hz / 时长 s / 峰值音量） */
const SCORE: Record<SoundName, (c: AudioContext) => void> = {
  // 选项选中：660Hz 极轻短tick
  select: (c) => tone(c, { freq: 660, decay: 0.09, peak: 0.14 }),
  // 主按钮按压：520→460Hz 柔和落音
  press: (c) => tone(c, { freq: 520, freqEnd: 460, decay: 0.13, peak: 0.18 }),
  // 答对/完成：E5→A5 双音上行，清透小钟
  success: (c) => {
    tone(c, { freq: 659.25, decay: 0.32, peak: 0.18, attack: 0.012 });
    tone(c, { freq: 880, decay: 0.42, peak: 0.16, attack: 0.012, delay: 0.09 });
    tone(c, { freq: 1320, type: 'triangle', decay: 0.2, peak: 0.03, delay: 0.09 });
  },
  // 答错/失败：220→180Hz 低音轻顿（不警告、不刺耳）
  error: (c) => tone(c, { freq: 220, freqEnd: 180, decay: 0.2, peak: 0.15, attack: 0.01 }),
  // AI 回复到达：880Hz 柔铃 + 轻泛音
  notification: (c) => {
    tone(c, { freq: 880, type: 'triangle', decay: 0.42, peak: 0.12, attack: 0.015 });
    tone(c, { freq: 1318.5, decay: 0.3, peak: 0.04, attack: 0.015, delay: 0.03 });
  },
  // 弹层打开：440→660Hz 上滑
  open: (c) => tone(c, { freq: 440, freqEnd: 660, decay: 0.14, peak: 0.1 }),
  // 弹层关闭：660→440Hz 下滑
  close: (c) => tone(c, { freq: 660, freqEnd: 440, decay: 0.13, peak: 0.09 }),
  // 开关/切换：740Hz 短珠音
  toggle: (c) => tone(c, { freq: 740, decay: 0.07, peak: 0.13 }),
  // 完成荣誉：C5-E5-G5-C6 琶音
  levelup: (c) => {
    const notes = [523.25, 659.25, 783.99, 1046.5];
    notes.forEach((f, i) => tone(c, { freq: f, decay: 0.36, peak: 0.16, attack: 0.012, delay: i * 0.09 }));
  },
  // 页面切换：500→700Hz 极轻上拂
  swipe: (c) => tone(c, { freq: 500, freqEnd: 700, decay: 0.1, peak: 0.08 }),
  // 发送消息：700→900Hz 轻送
  send: (c) => tone(c, { freq: 700, freqEnd: 900, decay: 0.11, peak: 0.11 }),
};

/** 播放指定语义音效；静音或环境不支持时静默跳过 */
export function playSound(name: SoundName): void {
  if (muted) return;
  try {
    const c = getContext();
    if (!c) return;
    SCORE[name](c);
  } catch {
    /* 忽略播放异常，绝不阻断交互 */
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
