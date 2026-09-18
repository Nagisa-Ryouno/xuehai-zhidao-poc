import React from 'react';

/**
 * Illustration.tsx
 * 学海智导装饰插画集（纯 SVG 手绘，零依赖、零版权风险、任意缩放）
 * - StudyScene：等距 2.5D 学习桌面（书堆/台灯/咖啡/星光）
 * - RocketScene：书海起航（与品牌 Logo 同源的箭头+旗帜+浪线）
 * - AuroraWaves：极光分层波浪（区块间的呼吸感装饰）
 */

interface SceneProps {
  className?: string;
  /** 是否播放轻微浮动动画，默认开启；reduced-motion 下自动静止 */
  animated?: boolean;
}

export const StudyScene: React.FC<SceneProps> = ({ className = '', animated = true }) => (
  <svg
    viewBox="0 0 240 180"
    className={`${animated ? 'animate-float' : ''} ${className}`}
    role="img"
    aria-label="学习桌面插画"
  >
    <defs>
      <linearGradient id="ss-sky" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#FADCC8" />
        <stop offset="1" stopColor="#F3C3AB" />
      </linearGradient>
      <linearGradient id="ss-book1" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#F2764A" />
        <stop offset="1" stopColor="#E2573F" />
      </linearGradient>
      <linearGradient id="ss-book2" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#3A4763" />
        <stop offset="1" stopColor="#22304A" />
      </linearGradient>
      <linearGradient id="ss-book3" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#FFF3E2" />
        <stop offset="1" stopColor="#F9D9C9" />
      </linearGradient>
    </defs>

    {/* 背景光斑 */}
    <ellipse cx="122" cy="86" rx="98" ry="72" fill="url(#ss-sky)" opacity=".55" />
    <ellipse cx="122" cy="152" rx="86" ry="14" fill="#E9C4A8" opacity=".4" />

    {/* 书堆（等距三层） */}
    <g>
      <path d="M60 132 122 168 184 132 122 96Z" fill="url(#ss-book2)" />
      <path d="M60 132v10l62 36 62-36v-10l-62 36Z" fill="#16213A" opacity=".28" />
      <path d="M72 118 122 146 172 118 122 90Z" fill="url(#ss-book3)" />
      <path d="M72 118v9l50 28 50-28v-9l-50 28Z" fill="#E4B48F" opacity=".35" />
      <path d="M84 104 122 124 160 104 122 84Z" fill="url(#ss-book1)" />
      <path d="M84 104v8l38 20 38-20v-8l-38 20Z" fill="#C8452A" opacity=".5" />
    </g>

    {/* 翻开的书（顶层） */}
    <g>
      <path d="M98 78c8-5 16-5 24 0 8-5 16-5 24 0v18c-8-5-16-5-24 0-8-5-16-5-24 0Z" fill="#FFF6EC" stroke="#E5CDB8" strokeWidth="1.5" />
      <path d="M122 78v18" stroke="#E5CDB8" strokeWidth="1.5" />
    </g>

    {/* 台灯 */}
    <g>
      <path d="M178 118v-34" stroke="#22304A" strokeWidth="4" strokeLinecap="round" />
      <path d="M178 84c0-8 10-12 16-7l-4 12Z" fill="#22304A" />
      <circle cx="190" cy="86" r="5" fill="#FFD98A" />
      <path d="M186 82c3 6 6 9 2 14" stroke="#FFD98A" strokeWidth="2" strokeLinecap="round" opacity=".8" />
      <path d="M168 122h20l-3-6h-14Z" fill="#22304A" />
    </g>

    {/* 咖啡杯 */}
    <g>
      <path d="M52 122h18v10c0 6-4 10-9 10s-9-4-9-10Z" fill="#FFF6EC" stroke="#E5CDB8" strokeWidth="1.5" />
      <path d="M70 124h5a4 4 0 0 1 0 8h-5" fill="none" stroke="#E5CDB8" strokeWidth="1.5" />
      <path d="M57 116c2-4 6-4 8 0" stroke="#C9A891" strokeWidth="1.6" fill="none" strokeLinecap="round" />
    </g>

    {/* 星星（闪烁动画） */}
    <g fill="#E8593C">
      <path className="animate-twinkle" d="M52 42l2.2 5.4 5.4 2.2-5.4 2.2-2.2 5.4-2.2-5.4-5.4-2.2 5.4-2.2Z" />
      <path className="animate-twinkle" style={{ animationDelay: '.7s' }} d="M196 34l1.8 4.4 4.4 1.8-4.4 1.8-1.8 4.4-1.8-4.4-4.4-1.8 4.4-1.8Z" />
      <path className="animate-twinkle" style={{ animationDelay: '1.3s' }} d="M210 118l1.5 3.6 3.6 1.5-3.6 1.5-1.5 3.6-1.5-3.6-3.6-1.5 3.6-1.5Z" />
    </g>
    <circle className="animate-twinkle" style={{ animationDelay: '.4s' }} cx="40" cy="88" r="3" fill="#F0A37E" />
  </svg>
);

export const RocketScene: React.FC<SceneProps> = ({ className = '', animated = true }) => (
  <svg
    viewBox="0 0 200 170"
    className={`${animated ? 'animate-float' : ''} ${className}`}
    role="img"
    aria-label="书海起航插画"
  >
    <defs>
      <linearGradient id="rs-hill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#FADCC8" />
        <stop offset="1" stopColor="#F3C3AB" />
      </linearGradient>
    </defs>
    <ellipse cx="100" cy="80" rx="88" ry="62" fill="#FBE7D9" opacity=".8" />
    {/* 浪线（书海） */}
    <path d="M16 128c14-10 28-10 42 0s28 10 42 0 28-10 42 0 28 10 42 0" stroke="url(#rs-hill)" strokeWidth="6" fill="none" strokeLinecap="round" />
    <path d="M34 146c12-7 24-7 36 0s24 7 36 0 24-7 36 0" stroke="#F9D9C9" strokeWidth="5" fill="none" strokeLinecap="round" />
    {/* 虚线航迹 */}
    <path d="M48 122C60 84 96 72 128 44" stroke="#E8593C" strokeWidth="3" strokeDasharray="2 8" fill="none" strokeLinecap="round" opacity=".75" />
    {/* 深藏青向上箭头 */}
    <path d="M128 20 148 62h-12l3 10h-22l3-10h-12Z" fill="#22304A" />
    {/* 旗帜 */}
    <path d="M58 52v34" stroke="#22304A" strokeWidth="3" strokeLinecap="round" />
    <path d="M58 52h24l-7 8 7 8H58Z" fill="#E8593C" />
    <circle cx="58" cy="86" r="3.5" fill="#22304A" />
    {/* 云 */}
    <g fill="#FFF6EC">
      <ellipse cx="46" cy="40" rx="14" ry="8" />
      <ellipse cx="60" cy="36" rx="10" ry="6" />
      <ellipse cx="160" cy="104" rx="13" ry="7" />
    </g>
    {/* 星 */}
    <path className="animate-twinkle" d="M168 26l1.8 4.4 4.4 1.8-4.4 1.8-1.8 4.4-1.8-4.4-4.4-1.8 4.4-1.8Z" fill="#E8593C" />
    <circle className="animate-twinkle" style={{ animationDelay: '.9s' }} cx="30" cy="70" r="3" fill="#F0A37E" />
  </svg>
);

export const AuroraWaves: React.FC<{ className?: string }> = ({ className = '' }) => (
  <svg viewBox="0 0 400 60" className={className} role="img" aria-label="极光波浪装饰" preserveAspectRatio="none">
    <path d="M0 40C60 18 120 52 200 36s140-24 200-6v30H0Z" fill="#FADCC8" opacity=".55" />
    <path d="M0 48C70 30 130 58 210 44s130-18 190-4v20H0Z" fill="#F3C3AB" opacity=".4" />
  </svg>
);
