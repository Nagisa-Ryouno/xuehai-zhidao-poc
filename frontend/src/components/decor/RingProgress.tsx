import React, { useEffect, useState } from 'react';

/**
 * RingProgress.tsx —— 环形掌握度指示器（打破"条形面板"的圆形元素）
 * 珊瑚渐变描边 + easeOutExpo 入场充能动画 + 中心大数字
 */

interface RingProgressProps {
  /** 0-100 */
  percent: number;
  size?: number;
  stroke?: number;
  className?: string;
  /** 中心是否显示百分比数字，默认 true */
  showValue?: boolean;
  /** 轨道色，默认暖白 */
  trackColor?: string;
}

export const RingProgress: React.FC<RingProgressProps> = ({
  percent,
  size = 84,
  stroke = 8,
  className = '',
  showValue = true,
  trackColor = '#F1E6D9',
}) => {
  const clamped = Math.max(0, Math.min(100, percent));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const [offset, setOffset] = useState(circumference);

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      setOffset(circumference * (1 - clamped / 100));
    });
    return () => cancelAnimationFrame(id);
  }, [clamped, circumference]);

  const gradientId = `ring-g-${size}-${stroke}`;

  return (
    <div className={`relative inline-grid place-items-center ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#F2764A" />
            <stop offset="1" stopColor="#E2573F" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={trackColor} strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1200ms cubic-bezier(.16,1,.3,1)' }}
        />
      </svg>
      {showValue && (
        <div className="absolute inset-0 grid place-items-center">
          <span className="font-mono font-black text-slate-900" style={{ fontSize: size * 0.24 }}>
            {Math.round(clamped)}
            <span className="font-semibold text-slate-500" style={{ fontSize: size * 0.13 }}>%</span>
          </span>
        </div>
      )}
    </div>
  );
};
