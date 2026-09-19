import React, { useEffect, useRef } from 'react';

/**
 * CSS3DLogo.tsx
 * 纯 CSS 3D 品牌立方体（v2 · 真实立体质感）
 * 针对"纸片拼合感"的三处重做：
 * 1. 锐角立方体 + 每面定向光照渐变（顶亮侧中底暗）+ 棱角描边，杜绝圆角露缝
 * 2. 往复摇摆替代全周旋转：始终展示品牌面，不再出现空白背面
 * 3. 标志多层 translateZ 堆叠挤出（深色底层 → 奶油表层），形成浮雕厚度
 * 指针移动产生视差跟随；环绕轨道星与呼吸软阴影保留；reduced-motion 自动静止
 */

const FACE = 116; // 立方体边长 px
const HALF = FACE / 2;

const faceBase: React.CSSProperties = {
  position: 'absolute',
  width: FACE,
  height: FACE,
  backfaceVisibility: 'hidden',
  display: 'grid',
  placeItems: 'center',
  boxShadow: 'inset 0 0 0 1px rgba(255,255,255,.14)',
};

const LogoMark: React.FC<{ size?: number }> = ({ size = 62 }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true">
    <path d="M32 13.5 42.5 34h-6.6l1.2 4.6h-10.2l1.2-4.6h-6.6Z" fill="#22304A" />
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

/** 挤出浮雕标志：8 层堆叠，后层加深形成厚度 */
const ExtrudedMark: React.FC = () => (
  <div style={{ position: 'relative', transformStyle: 'preserve-3d' }}>
    {Array.from({ length: 7 }).map((_, i) => (
      <div
        key={i}
        style={{
          position: 'absolute',
          inset: 0,
          transform: `translateZ(${-(i + 1) * 1.6}px)`,
          filter: 'brightness(.62) saturate(1.1)',
          opacity: 1 - i * 0.06,
        }}
      >
        <LogoMark />
      </div>
    ))}
    <div style={{ position: 'relative', transform: 'translateZ(0.5px)' }}>
      <LogoMark />
    </div>
  </div>
);

export const CSS3DLogo: React.FC<{ className?: string }> = ({ className = '' }) => {
  const parallaxRef = useRef<HTMLDivElement>(null);
  const target = useRef({ x: 0, y: 0 });
  const current = useRef({ x: 0, y: 0 });
  const rafId = useRef<number>(0);

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) return;

    const onMove = (e: PointerEvent) => {
      const nx = e.clientX / window.innerWidth - 0.5;
      const ny = e.clientY / window.innerHeight - 0.5;
      target.current = { x: ny * -16, y: nx * 24 };
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

  return (
    <div className={className} role="img" aria-label="学海智导品牌 3D 立方体标识">
      <style>{`
        .c3d-stage{perspective:1120px;perspective-origin:50% 40%}
        .c3d-parallax{transform-style:preserve-3d;will-change:transform}
        .c3d-sway{transform-style:preserve-3d;animation:c3d-sway 9s cubic-bezier(.45,0,.55,1) infinite,c3d-float 5.2s ease-in-out infinite}
        @keyframes c3d-sway{0%,100%{transform:rotateY(-30deg) rotateX(6deg)}50%{transform:rotateY(26deg) rotateX(6deg)}}
        @keyframes c3d-float{0%,100%{translate:0 0}50%{translate:0 -12px}}
        .c3d-orbit{transform-style:preserve-3d;animation:c3d-orbit 7s linear infinite}
        @keyframes c3d-orbit{from{transform:rotateX(72deg) rotateZ(0deg)}to{transform:rotateX(72deg) rotateZ(360deg)}}
        .c3d-shadow{animation:c3d-shadow 5.2s ease-in-out infinite}
        @keyframes c3d-shadow{0%,100%{transform:scale(1);opacity:.22}50%{transform:scale(.8);opacity:.12}}
      `}</style>

      <div className="c3d-stage relative mx-auto" style={{ width: 190, height: 200 }}>
        <div ref={parallaxRef} className="c3d-parallax absolute inset-0 grid place-items-center">
          <div className="c3d-sway relative" style={{ width: FACE, height: FACE }}>
            {/* 前面：品牌面（定向光照 + 顶部高光荣 + 挤出浮雕标志） */}
            <div
              style={{
                ...faceBase,
                transform: `translateZ(${HALF}px)`,
                background:
                  'linear-gradient(180deg, rgba(255,255,255,.26) 0%, rgba(255,255,255,0) 26%), linear-gradient(160deg,#F27A4E 0%,#E8593C 55%,#D64A2E 100%)',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: '8%',
                  right: '8%',
                  height: '38%',
                  borderRadius: '0 0 50% 50%',
                  background: 'linear-gradient(180deg, rgba(255,255,255,.34), rgba(255,255,255,0))',
                  pointerEvents: 'none',
                }}
              />
              <ExtrudedMark />
            </div>
            {/* 右面（受光侧） */}
            <div
              style={{
                ...faceBase,
                transform: `rotateY(90deg) translateZ(${HALF}px)`,
                background:
                  'linear-gradient(180deg, rgba(255,255,255,.14) 0%, rgba(255,255,255,0) 30%), linear-gradient(160deg,#E8593C,#D64A2E 80%)',
              }}
            />
            {/* 左面（背光侧，更深） */}
            <div
              style={{
                ...faceBase,
                transform: `rotateY(-90deg) translateZ(${HALF}px)`,
                background: 'linear-gradient(160deg,#C8452A,#A83A24 85%)',
              }}
            />
            {/* 后面（仅在最大摆角时隐约可见，深色收边） */}
            <div
              style={{
                ...faceBase,
                transform: `rotateY(180deg) translateZ(${HALF}px)`,
                background: 'linear-gradient(160deg,#B23E24,#8F2F1B)',
              }}
            />
            {/* 顶面（最亮受光面） */}
            <div
              style={{
                ...faceBase,
                transform: `rotateX(90deg) translateZ(${HALF}px)`,
                background: 'linear-gradient(160deg,#F9A176,#F2764A 80%)',
              }}
            />
            {/* 底面（最暗） */}
            <div
              style={{
                ...faceBase,
                transform: `rotateX(-90deg) translateZ(${HALF}px)`,
                background: '#8F2F1B',
              }}
            />
            {/* 环绕轨道与智导星 */}
            <div className="c3d-orbit absolute" style={{ inset: -36, pointerEvents: 'none' }}>
              <span
                className="absolute left-1/2 top-1/2 block"
                style={{
                  width: 16,
                  height: 16,
                  margin: -8,
                  background: '#FFF3E2',
                  clipPath: 'polygon(50% 0,63% 37%,100% 50%,63% 63%,50% 100%,37% 63%,0 50%,37% 37%)',
                  filter: 'drop-shadow(0 2px 6px rgba(226,87,63,.55))',
                }}
              />
            </div>
          </div>
        </div>

        {/* 呼吸软阴影 */}
        <div
          className="c3d-shadow absolute left-1/2 bottom-1 -translate-x-1/2 rounded-full"
          style={{ width: 112, height: 20, background: 'radial-gradient(closest-side, rgba(120,60,30,.42), transparent)' }}
        />
      </div>
    </div>
  );
};
