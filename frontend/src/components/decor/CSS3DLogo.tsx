import React, { useEffect, useRef } from 'react';

/**
 * CSS3DLogo.tsx
 * 纯 CSS 3D 品牌立方体（零依赖的"动人" 3D 交互）
 * - transform-style: preserve-3d 六面立方体，缓慢自转 + 上下浮动
 * - 指针移动产生视差跟随（rotateX/rotateY 按指针位置平滑插值）
 * - 环绕轨道星 + 同步呼吸软阴影
 * - prefers-reduced-motion 下自动静止（全局降级规则生效）
 * 说明：WebGL 方案（react-three-fiber）因当前网络无法下载大体积依赖而改用
 * 纯 CSS 3D 实现，交互观感一致且零加载成本。
 */

const FACE = 112; // 立方体边长 px

const faceBase: React.CSSProperties = {
  position: 'absolute',
  width: FACE,
  height: FACE,
  borderRadius: 26,
  backfaceVisibility: 'hidden',
  display: 'grid',
  placeItems: 'center',
};

const LogoMark: React.FC<{ size?: number }> = ({ size = 58 }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true">
    <path
      d="M32 13.5 42.5 34h-6.6l1.2 4.6h-10.2l1.2-4.6h-6.6Z"
      fill="#22304A"
    />
    <path
      d="M12 41.5c6.7-3.3 13.3-3.3 20 0 6.7-3.3 13.3-3.3 20 0v8c-6.7-3.3-13.3-3.3-20 0-6.7-3.3-13.3-3.3-20 0Z"
      fill="#FFF6EC"
    />
    <path
      d="M47 9.5l1.9 4.5 4.5 1.9-4.5 1.9-1.9 4.5-1.9-4.5-4.5-1.9 4.5-1.9Z"
      fill="#FFF3E2"
    />
  </svg>
);

export const CSS3DLogo: React.FC<{ className?: string }> = ({ className = '' }) => {
  const parallaxRef = useRef<HTMLDivElement>(null);
  const target = useRef({ x: 0, y: 0 });
  const current = useRef({ x: 0, y: 0 });
  const rafId = useRef<number>(0);

  // 指针视差：监听指针位置，插值平滑跟随
  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) return;

    const onMove = (e: PointerEvent) => {
      const nx = e.clientX / window.innerWidth - 0.5;
      const ny = e.clientY / window.innerHeight - 0.5;
      target.current = { x: ny * -18, y: nx * 26 };
    };
    const tick = () => {
      current.current.x += (target.current.x - current.current.x) * 0.06;
      current.current.y += (target.current.y - current.current.y) * 0.06;
      if (parallaxRef.current) {
        parallaxRef.current.style.transform = `rotateX(${current.current.x.toFixed(2)}deg) rotateY(${current.current.y.toFixed(2)}deg)`;
      }
      rafId.current = requestAnimationFrame(tick);
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    rafId.current = requestAnimationFrame(tick);
    return () => {
      window.removeEventListener('pointermove', onMove);
      cancelAnimationFrame(rafId.current);
    };
  }, []);

  const half = FACE / 2;

  return (
    <div className={className} role="img" aria-label="学海智导品牌 3D 立方体标识">
      <style>{`
        .c3d-stage{perspective:980px;perspective-origin:50% 42%}
        .c3d-parallax{transform-style:preserve-3d;will-change:transform}
        .c3d-spin{transform-style:preserve-3d;animation:c3d-spin 15s linear infinite,c3d-float 5.2s ease-in-out infinite}
        @keyframes c3d-spin{from{transform:rotateY(-26deg)}to{transform:rotateY(334deg)}}
        @keyframes c3d-float{0%,100%{translate:0 0}50%{translate:0 -12px}}
        .c3d-orbit{transform-style:preserve-3d;animation:c3d-orbit 7s linear infinite}
        @keyframes c3d-orbit{from{transform:rotateX(72deg) rotateZ(0deg)}to{transform:rotateX(72deg) rotateZ(360deg)}}
        .c3d-shadow{animation:c3d-shadow 5.2s ease-in-out infinite}
        @keyframes c3d-shadow{0%,100%{transform:scale(1);opacity:.2}50%{transform:scale(.82);opacity:.12}}
      `}</style>

      <div className="c3d-stage relative mx-auto" style={{ width: 190, height: 200 }}>
        {/* 指针视差层 */}
        <div ref={parallaxRef} className="c3d-parallax absolute inset-0 grid place-items-center">
          {/* 自转 + 浮动层 */}
          <div className="c3d-spin relative" style={{ width: FACE, height: FACE }}>
            {/* 前面（带品牌图形） */}
            <div
              style={{
                ...faceBase,
                transform: `translateZ(${half}px)`,
                background: 'linear-gradient(145deg,#F2764A,#E2573F)',
                boxShadow: 'inset 0 2px 0 rgba(255,255,255,.35), inset 0 -6px 14px rgba(150,40,15,.35)',
              }}
            >
              <LogoMark />
            </div>
            {/* 后面 */}
            <div
              style={{
                ...faceBase,
                transform: `rotateY(180deg) translateZ(${half}px)`,
                background: 'linear-gradient(145deg,#D44B31,#B4552F)',
              }}
            />
            {/* 右面 */}
            <div
              style={{
                ...faceBase,
                transform: `rotateY(90deg) translateZ(${half}px)`,
                background: 'linear-gradient(145deg,#EA5A3C,#D44B31)',
              }}
            />
            {/* 左面 */}
            <div
              style={{
                ...faceBase,
                transform: `rotateY(-90deg) translateZ(${half}px)`,
                background: 'linear-gradient(145deg,#F28A5C,#E8593C)',
              }}
            />
            {/* 顶面 */}
            <div
              style={{
                ...faceBase,
                transform: `rotateX(90deg) translateZ(${half}px)`,
                background: 'linear-gradient(145deg,#F9A176,#F2764A)',
              }}
            />
            {/* 底面 */}
            <div
              style={{
                ...faceBase,
                transform: `rotateX(-90deg) translateZ(${half}px)`,
                background: '#A83A24',
              }}
            />
            {/* 环绕轨道与智导星 */}
            <div
              className="c3d-orbit absolute"
              style={{ inset: -34, pointerEvents: 'none' }}
            >
              <span
                className="absolute left-1/2 top-1/2 block"
                style={{
                  width: 16,
                  height: 16,
                  margin: -8,
                  background: '#FFF3E2',
                  clipPath: 'polygon(50% 0,63% 37%,100% 50%,63% 63%,50% 100%,37% 63%,0 50%,37% 37%)',
                  filter: 'drop-shadow(0 2px 6px rgba(226,87,63,.5))',
                }}
              />
            </div>
          </div>
        </div>

        {/* 呼吸软阴影 */}
        <div
          className="c3d-shadow absolute left-1/2 bottom-1 -translate-x-1/2 rounded-full"
          style={{ width: 110, height: 20, background: 'radial-gradient(closest-side, rgba(120,60,30,.4), transparent)' }}
        />
      </div>
    </div>
  );
};
