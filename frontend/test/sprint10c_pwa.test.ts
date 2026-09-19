/**
 * sprint10c_pwa.test.ts
 * Sprint 10-C / Phase 1: Student PWA Productization 契约与规范测试
 *
 * 覆盖：
 * 1. Web App Manifest 格式、核心字段与图标完整性
 * 2. HTML 入口 PWA 元数据、viewport 与 theme-color 契约
 * 3. Service Worker 静态缓存策略与 /api/ 动态网络红线保护
 * 4. PWA 独立窗口 (Standalone) 与 Safe-Area 适配契约
 * 5. PWA Install Banner 规范与免打扰机制
 * 6. 无算法黑话与零伪造离线同步安全契约
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, '..');
const publicDir = path.resolve(frontendRoot, 'public');

describe('Sprint 10-C / Phase 1: Student PWA Productization 契约测试', () => {

  // =========================================================================
  // C1: Web App Manifest 结构与字段合规性
  // =========================================================================
  describe('C1: Web App Manifest 契约', () => {
    it('1. manifest.webmanifest 存在且为合法 JSON', () => {
      const manifestPath = path.join(publicDir, 'manifest.webmanifest');
      assert.ok(fs.existsSync(manifestPath), 'manifest.webmanifest 必须存在于 public 目录');

      const content = fs.readFileSync(manifestPath, 'utf-8');
      const manifest = JSON.parse(content);
      assert.ok(manifest, 'manifest 必须能解析为对象');
    });

    it('2. manifest 基础定位字段合法 (name, short_name, description)', () => {
      const manifestPath = path.join(publicDir, 'manifest.webmanifest');
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));

      assert.equal(manifest.name, '学海智导');
      assert.equal(manifest.short_name, '学海智导');
      assert.ok(manifest.description && manifest.description.length > 0);
    });

    it('3. start_url 与 scope 契约保证学生端直接入站', () => {
      const manifestPath = path.join(publicDir, 'manifest.webmanifest');
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));

      assert.equal(manifest.start_url, '/student', 'start_url 必须直接指向学生端入口');
      assert.equal(manifest.scope, '/', 'scope 必须覆盖应用根路径');
    });

    it('4. display 必须为 standalone 独立应用窗口', () => {
      const manifestPath = path.join(publicDir, 'manifest.webmanifest');
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));

      assert.equal(manifest.display, 'standalone', 'PWA 必须以独立应用窗口模式启动');
      assert.equal(manifest.theme_color, '#4f46e5', 'theme_color 应契合学海智导品牌蓝紫调');
      assert.equal(manifest.background_color, '#f8fafc', 'background_color 应为 slate-50');
    });

    it('5. 图标清单满足 192x192、512x512 及 maskable 标准要求', () => {
      const manifestPath = path.join(publicDir, 'manifest.webmanifest');
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));

      assert.ok(Array.isArray(manifest.icons), 'icons 必须是数组');

      const has192 = manifest.icons.some(
        (icon: any) => icon.sizes === '192x192' && icon.type === 'image/png'
      );
      const has512 = manifest.icons.some(
        (icon: any) => icon.sizes === '512x512' && icon.type === 'image/png'
      );
      const hasMaskable = manifest.icons.some(
        (icon: any) => icon.purpose && icon.purpose.includes('maskable')
      );

      assert.ok(has192, '必须包含 192x192 规格 PNG 图标');
      assert.ok(has512, '必须包含 512x512 规格 PNG 图标');
      assert.ok(hasMaskable, '必须包含 maskable 适配图标');
    });

    it('6. 声明的图标物理文件必须真实存在且字节数大于 0', () => {
      const manifestPath = path.join(publicDir, 'manifest.webmanifest');
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));

      for (const icon of manifest.icons) {
        const iconRelPath = icon.src.startsWith('/') ? icon.src.slice(1) : icon.src;
        const iconFullPath = path.join(publicDir, iconRelPath);
        assert.ok(
          fs.existsSync(iconFullPath),
          `manifest 中引用的图标文件 ${icon.src} 必须存在`
        );
        const stat = fs.statSync(iconFullPath);
        assert.ok(stat.size > 0, `图标文件 ${icon.src} 必须非空`);
      }
    });

    it('7. manifest.json 兼容别名与 webmanifest 保持一致', () => {
      const jsonPath = path.join(publicDir, 'manifest.json');
      assert.ok(fs.existsSync(jsonPath), 'manifest.json 别名文件必须存在');
      const manifest = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
      assert.equal(manifest.name, '学海智导');
      assert.equal(manifest.start_url, '/student');
    });
  });

  // =========================================================================
  // C2: index.html PWA 标签与移动端 Viewport 契约
  // =========================================================================
  describe('C2: index.html PWA 元数据契约', () => {
    it('8. index.html 正确链接 manifest 与 apple-touch-icon', () => {
      const htmlPath = path.join(frontendRoot, 'index.html');
      const html = fs.readFileSync(htmlPath, 'utf-8');

      assert.ok(
        html.includes('rel="manifest"') && html.includes('/manifest.webmanifest'),
        'index.html 必须包含 manifest 链接'
      );
      assert.ok(
        html.includes('rel="apple-touch-icon"'),
        'index.html 必须包含 apple-touch-icon 链接'
      );
    });

    it('9. index.html 包含 viewport-fit=cover 满足安全区计算', () => {
      const htmlPath = path.join(frontendRoot, 'index.html');
      const html = fs.readFileSync(htmlPath, 'utf-8');

      assert.ok(
        html.includes('viewport-fit=cover'),
        'viewport meta 标签必须包含 viewport-fit=cover 属性以支持 safe-area'
      );
    });

    it('10. index.html 包含 mobile-web-app-capable 与 theme-color', () => {
      const htmlPath = path.join(frontendRoot, 'index.html');
      const html = fs.readFileSync(htmlPath, 'utf-8');

      assert.ok(html.includes('name="theme-color"'), '必须声明 theme-color');
      assert.ok(
        html.includes('name="mobile-web-app-capable"') || html.includes('name="apple-mobile-web-app-capable"'),
        '必须声明 web-app-capable'
      );
    });
  });

  // =========================================================================
  // C3: Service Worker 缓存策略与安全红线
  // =========================================================================
  describe('C3: Service Worker 缓存策略与动态 API 隔离', () => {
    it('11. sw.js 文件存在于 public 根目录', () => {
      const swPath = path.join(publicDir, 'sw.js');
      assert.ok(fs.existsSync(swPath), 'sw.js 必须存在于 public 根目录');
    });

    it('12. sw.js 明确排除 /api/ 动态权威接口的持久缓存 (Network Only / No SW Cache)', () => {
      const swPath = path.join(publicDir, 'sw.js');
      const content = fs.readFileSync(swPath, 'utf-8');

      assert.ok(
        content.includes('/api/'),
        'sw.js 必须对 /api/ 路由具备专门的过滤拦截逻辑'
      );
      assert.ok(
        content.includes('fetch(request)') && (content.includes('503') || content.includes('NETWORK_UNAVAILABLE')),
        '对 API 请求失败时返回 503 明确告知网络不可用，绝不伪造陈旧状态'
      );
    });

    it('13. sw.js 实现了对导航请求 (mode === "navigate") 的 App Shell 回退', () => {
      const swPath = path.join(publicDir, 'sw.js');
      const content = fs.readFileSync(swPath, 'utf-8');

      assert.ok(
        content.includes("request.mode === 'navigate'"),
        'sw.js 必须捕获 navigate 请求并提供 App Shell 降级保障'
      );
      assert.ok(
        content.includes('/index.html') || content.includes("caches.match('/')"),
        '离线回退必须指向 SPA 基础骨架'
      );
    });

    it('14. sw.js 具备缓存版本管理与 activate 阶段旧缓存清理', () => {
      const swPath = path.join(publicDir, 'sw.js');
      const content = fs.readFileSync(swPath, 'utf-8');

      assert.ok(content.includes('CACHE_VERSION') || content.includes('STATIC_CACHE_NAME'), '必须包含缓存版本号定义');
      assert.ok(content.includes('addEventListener(\'activate\''), '必须监听 activate 生命周期');
      assert.ok(content.includes('caches.delete'), 'activate 阶段必须清理过期缓存，防止旧 JS 僵尸残留');
    });
  });

  // =========================================================================
  // C4: Safe Area 与移动优先排版契约
  // =========================================================================
  describe('C4: Safe Area 与移动排版契约', () => {
    it('15. Header 组件包含 pt-[env(safe-area-inset-top)]', () => {
      const headerPath = path.join(frontendRoot, 'src', 'components', 'Header.tsx');
      const content = fs.readFileSync(headerPath, 'utf-8');

      assert.ok(
        content.includes('safe-area-inset-top'),
        'Header 必须包含 safe-area-inset-top 顶部避让，防止刘海屏遮挡'
      );
    });

    it('16. BottomNav 包含 pb-[env(safe-area-inset-bottom)]', () => {
      const navConfigPath = path.join(frontendRoot, 'src', 'components', 'student', 'navConfig.ts');
      const content = fs.readFileSync(navConfigPath, 'utf-8');

      assert.ok(
        content.includes('safe-area-inset-bottom'),
        'BottomNav 必须包含 safe-area-inset-bottom 避让底部横条'
      );
    });

    it('17. StudentLayout 引入 PwaInstallBanner 与离线提示', () => {
      const layoutPath = path.join(frontendRoot, 'src', 'layouts', 'StudentLayout.tsx');
      const content = fs.readFileSync(layoutPath, 'utf-8');

      assert.ok(
        content.includes('PwaInstallBanner'),
        'StudentLayout 必须挂载 PwaInstallBanner 安装提示组件'
      );
      assert.ok(
        content.includes('pwa-offline-notice'),
        'StudentLayout 必须具备 data-testid="pwa-offline-notice" 离线状态提示'
      );
    });
  });

  // =========================================================================
  // C5: 用户叙事合规性与无算法黑话
  // =========================================================================
  describe('C5: 人本温度与无技术黑话契约', () => {
    it('18. PWA 横幅与离线文案绝不包含算法黑话', () => {
      const bannerPath = path.join(frontendRoot, 'src', 'components', 'student', 'PwaInstallBanner.tsx');
      const bannerContent = fs.readFileSync(bannerPath, 'utf-8');

      const forbiddenJargon = [
        'BKT',
        'DeepSeek',
        'PathState',
        'mastery_probability',
        '置信度',
        '决策',
        'Replanning',
      ];

      for (const jargon of forbiddenJargon) {
        assert.ok(
          !bannerContent.includes(jargon),
          `PwaInstallBanner 中禁止包含技术黑话 "${jargon}"`
        );
      }
    });

    it('19. 离线提示文案严格诚实，绝不伪造离线自动同步', () => {
      const layoutPath = path.join(frontendRoot, 'src', 'layouts', 'StudentLayout.tsx');
      const layoutContent = fs.readFileSync(layoutPath, 'utf-8');

      assert.ok(
        !layoutContent.includes('最新学习状态会自动同步'),
        '严禁向学生承诺系统会自动同步离线学习状态'
      );
      assert.ok(
        layoutContent.includes('需恢复网络后使用'),
        '离线提示文案必须如实说明需恢复网络后使用'
      );
    });
  });
});
