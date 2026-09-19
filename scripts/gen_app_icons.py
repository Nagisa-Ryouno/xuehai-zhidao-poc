"""按 logo-coral.svg 绘制 PNG 应用图标（PWA/桌面/苹果触控图标）"""
from PIL import Image, ImageDraw

S = 1024  # 超采样绘制，再缩小

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

CORAL_TOP = (242, 118, 74)    # F2764A
CORAL_BOT = (226, 87, 63)     # E2573F
CREAM = (255, 246, 236)       # FFF6EC
STAR = (255, 243, 226)        # FFF3E2
NAVY = (34, 48, 74)           # 22304A

def render(size):
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 圆角方块（rx=16/64）
    r = S * 16 / 64
    for y in range(S):
        d.line([(0, y), (S, y)], fill=lerp(CORAL_TOP, CORAL_BOT, y / S) + (255,))
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S, S], radius=r, fill=255)
    img.putalpha(mask)
    d = ImageDraw.Draw(img)

    def sc(v):
        return v / 64 * S

    # 智导星（四角星，右上）
    cx, cy, r1, r2 = sc(47), sc(15.9), sc(7.6), sc(2.1)
    pts = []
    import math
    for i in range(8):
        ang = -math.pi / 2 + i * math.pi / 4
        rr = r1 if i % 2 == 0 else r2
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=STAR + (255,))

    # 深藏青向上箭头（书本上方）
    d.polygon([
        (sc(32), sc(13.5)), (sc(42.5), sc(34)), (sc(35.9), sc(34)),
        (sc(37.1), sc(38.6)), (sc(26.9), sc(38.6)), (sc(28.1), sc(34)),
        (sc(21.5), sc(34)),
    ], fill=NAVY + (255,))

    # 书海（翻开的书，双色页）
    def book(x0, y0, x1, y1, c1, c2):
        # 简化书形：底部 V 形页
        d.polygon([
            (sc(x0), sc(y0)), (sc(32), sc(y0 + 3.3)), (sc(32), sc(y1)),
            (sc(x0), sc(y1 - 3.3)),
        ], fill=c1 + (255,))
        d.polygon([
            (sc(x1), sc(y0)), (sc(32), sc(y0 + 3.3)), (sc(32), sc(y1)),
            (sc(x1), sc(y1 - 3.3)),
        ], fill=c2 + (255,))
    book(12, 41.5, 52, 49.5, CREAM, (249, 220, 200))

    # 浪线
    d.arc([sc(10), sc(51.5), sc(25), sc(58)], 20, 160, fill=CREAM + (255,), width=int(sc(2.6)))
    d.arc([sc(25), sc(51.5), sc(41), sc(58)], 20, 160, fill=CREAM + (255,), width=int(sc(2.6)))
    d.arc([sc(41), sc(51.5), sc(54), sc(58)], 20, 160, fill=CREAM + (255,), width=int(sc(2.6)))

    return img.resize((size, size), Image.LANCZOS)

import os
out = 'frontend/public'
for size, name in [(512, 'icon-512.png'), (192, 'icon-192.png'), (180, 'apple-touch-icon.png')]:
    render(size).save(os.path.join(out, name))
    print('written', name, size)
# maskable（安全区内缩 12%）
img = Image.new('RGBA', (512, 512), lerp(CORAL_TOP, CORAL_BOT, 0.5) + (255,))
icon = render(512).resize((410, 410), Image.LANCZOS)
img.paste(icon, (51, 51), icon)
img.save(os.path.join(out, 'icon-maskable-512.png'))
print('written icon-maskable-512.png')
