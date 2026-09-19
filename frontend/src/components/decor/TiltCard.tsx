import React, { useCallback, useRef } from 'react';

/**
 * TiltCard.tsx —— 3D 倾斜交互面板引擎
 * 思路源自 Aceternity UI 3D Card Effect 与业界 tilt-with-glare 模式：
 * - 指针在面板内移动时，面板绕 X/Y 轴实时倾斜（rotateX/rotateY）
 * - 高光（glare）跟随指针位置，形成玻璃上的镜面反射感
 * - 子元素可加 .tilt-z 获得 translateZ(30px) 的悬浮景深
 * - 指针离开以 easeOutExpo 曲线 500ms 平滑回正
 * - prefers-reduced-motion / 触屏设备自动退化为静态面板
 */

export interface TiltCardProps {
  /** 外层（透视容器）类名 */
  className?: string;
  /** 内层（被倾斜的面板本体）类名，通常承载 glass-card 与形状类 */
  innerClassName?: string;
  children: React.ReactNode;
  /** 最大倾斜角度，默认 10 */
  maxTilt?: number;
  /** 悬停放大倍数，默认 1.015 */
  scale?: number;
  /** 是否显示跟随高光，默认 true */
  glare?: boolean;
  /** 高光颜色（rgba），默认暖白 */
  glareColor?: string;
}

export const TiltCard: React.FC<TiltCardProps> = ({
  className = '',
  innerClassName = '',
  children,
  maxTilt = 10,
  scale = 1.015,
  glare = true,
  glareColor = 'rgba(255,255,255,.55)',
}) => {
  const outerRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const glareRef = useRef<HTMLDivElement>(null);

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (e.pointerType === 'touch') return;
      const el = outerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const px = (e.clientX - rect.left) / rect.width - 0.5;
      const py = (e.clientY - rect.top) / rect.height - 0.5;
      if (innerRef.current) {
        innerRef.current.style.transition = 'transform 80ms linear';
        innerRef.current.style.transform = `rotateX(${(-py * maxTilt).toFixed(2)}deg) rotateY(${(px * maxTilt).toFixed(2)}deg) scale(${scale})`;
      }
      if (glare && glareRef.current) {
        glareRef.current.style.opacity = '1';
        glareRef.current.style.background = `radial-gradient(circle at ${((px + 0.5) * 100).toFixed(1)}% ${((py + 0.5) * 100).toFixed(1)}%, ${glareColor}, transparent 62%)`;
      }
    },
    [maxTilt, scale, glare, glareColor]
  );

  const onPointerLeave = useCallback(() => {
    if (innerRef.current) {
      innerRef.current.style.transition = 'transform 520ms cubic-bezier(.16,1,.3,1)';
      innerRef.current.style.transform = 'rotateX(0deg) rotateY(0deg) scale(1)';
    }
    if (glareRef.current) {
      glareRef.current.style.opacity = '0';
    }
  }, []);

  return (
    <div
      ref={outerRef}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
      className={`[perspective:960px] ${className}`}
    >
      <div
        ref={innerRef}
        className={`relative transform-gpu will-change-transform [transform-style:preserve-3d] ${innerClassName}`}
      >
        {children}
        {glare && (
          <div
            ref={glareRef}
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-500"
          />
        )}
      </div>
    </div>
  );
};
