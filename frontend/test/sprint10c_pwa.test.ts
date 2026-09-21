import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');
const PUBLIC_DIR = path.resolve(PROJECT_ROOT, 'public');
const SRC_DIR = path.resolve(PROJECT_ROOT, 'src');

describe('Sprint 10-C Phase 4: 学生端 PWA 与移动端体验加固测试套件', () => {

  // ===========================================================================
  // Group 1: PWA Web App Manifest 契约测试
  // ===========================================================================
  describe('C1: PWA Web App Manifest 契约与安装性标准', () => {
    test('1. manifest.webmanifest 与 manifest.json 文件存在且为合法 JSON', () => {
      const manifestPath = path.join(PUBLIC_DIR, 'manifest.webmanifest');
      const manifestJsonPath = path.join(PUBLIC_DIR, 'manifest.json');
      assert.ok(fs.existsSync(manifestPath), 'manifest.webmanifest 必须存在于 public 目录');
      assert.ok(fs.existsSync(manifestJsonPath), 'manifest.json 必须存在于 public 目录');

      const content = fs.readFileSync(manifestPath, 'utf-8');
      const data = JSON.parse(content);
      assert.equal(typeof data, 'object');
      assert.ok(data !== null);
    });

    test('2. Manifest 核心应用名称与标识符符合规范', () => {
      const manifestPath = path.join(PUBLIC_DIR, 'manifest.webmanifest');
      const data = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
      assert.equal(data.name, '学海智导');
      assert.equal(data.short_name, '学海智导');
      assert.ok(data.description && data.description.length > 0);
    });

    test('3. start_url 与 scope 严格限定于学生端合理入口，绝不指向受保护私有端点', () => {
      const manifestPath = path.join(PUBLIC_DIR, 'manifest.webmanifest');
      const data = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
      assert.ok(
        data.start_url === '/student' || data.start_url === '/student/tasks',
        `start_url 必须指向学生端入口，实际为: ${data.start_url}`
      );
      assert.equal(data.scope, '/');
    });

    test('4. display 模式设为 standalone，严禁使用侵入式 fullscreen', () => {
      const manifestPath = path.join(PUBLIC_DIR, 'manifest.webmanifest');
      const data = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
      assert.equal(data.display, 'standalone');
      assert.notEqual(data.display, 'fullscreen');
    });

    test('5. PWA 图标阵列完整覆盖 192x192、512x512 以及 maskable 规格', () => {
      const manifestPath = path.join(PUBLIC_DIR, 'manifest.webmanifest');
      const data = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
      assert.ok(Array.isArray(data.icons));
      assert.ok(data.icons.length >= 3);

      const has192 = data.icons.some((i: any) => i.sizes === '192x192' && i.type === 'image/png');
      const has512 = data.icons.some((i: any) => i.sizes === '512x512' && i.type === 'image/png');
      const hasMaskable = data.icons.some((i: any) => i.purpose === 'maskable');

      assert.ok(has192, '必须提供 192x192 PNG 图标');
      assert.ok(has512, '必须提供 512x512 PNG 图标');
      assert.ok(hasMaskable, '必须提供 maskable 自适应图标');

      // 验证真实图标文件均存在于 public/
      assert.ok(fs.existsSync(path.join(PUBLIC_DIR, 'pwa-192x192.png')));
      assert.ok(fs.existsSync(path.join(PUBLIC_DIR, 'pwa-512x512.png')));
      assert.ok(fs.existsSync(path.join(PUBLIC_DIR, 'pwa-maskable-512x512.png')));
    });

    test('6. index.html 完整链接 manifest 与 PWA 元数据标签', () => {
      const indexPath = path.join(PROJECT_ROOT, 'index.html');
      const html = fs.readFileSync(indexPath, 'utf-8');
      assert.ok(html.includes('rel="manifest"'), 'index.html 必须包含 rel="manifest"');
      assert.ok(html.includes('viewport-fit=cover'), 'index.html viewport 必须包含 viewport-fit=cover');
      assert.ok(html.includes('name="theme-color"'), 'index.html 必须声明 theme-color');
      assert.ok(html.includes('name="mobile-web-app-capable"'), 'index.html 必须声明 mobile-web-app-capable');
    });
  });

  // ===========================================================================
  // Group 2: Service Worker 缓存策略与动态 API 隔离测试
  // ===========================================================================
  describe('C2: Service Worker 离线降级与权威 API 隔离策略', () => {
    test('7. sw.js 文件存在并声明 App Shell 核心预缓存资源', () => {
      const swPath = path.join(PUBLIC_DIR, 'sw.js');
      assert.ok(fs.existsSync(swPath));
      const code = fs.readFileSync(swPath, 'utf-8');
      assert.ok(code.includes('PRECACHE_ASSETS'));
      assert.ok(code.includes('/index.html'));
      assert.ok(code.includes('/manifest.webmanifest'));
    });

    test('8. 权威动态 API (/api/*) 绝对禁止持久缓存，保障真实学习状态零污染', () => {
      const swPath = path.join(PUBLIC_DIR, 'sw.js');
      const code = fs.readFileSync(swPath, 'utf-8');
      assert.ok(code.includes("url.pathname.startsWith('/api/')"));
      // 离线时返回 503 NETWORK_UNAVAILABLE，严禁伪造成功
      assert.ok(code.includes('NETWORK_UNAVAILABLE'));
      assert.ok(!code.includes("cache.put(request, ...api)"));
    });

    test('9. sw.js 中绝对禁止包含任何 BKT、PathState、QUESTION_ATTEMPT、LearningEvent 本地计算与伪造', () => {
      const swPath = path.join(PUBLIC_DIR, 'sw.js');
      const code = fs.readFileSync(swPath, 'utf-8');
      const forbiddenFunctionalPatterns = [
        'indexedDB',
        'openDatabase',
        'localStorage',
        'sessionStorage',
        'update_bkt',
        'updateBkt',
        'calculateBkt',
        'offline_queue',
        'sync_queue',
        'replay_events',
      ];
      for (const term of forbiddenFunctionalPatterns) {
        assert.ok(
          !code.includes(term),
          `sw.js 严禁包含离线状态存储或队列计算代码: ${term}`
        );
      }
    });

    test('10. pwa.ts Service Worker 注册逻辑具备空值保护，异常被安全捕获', () => {
      const pwaPath = path.join(SRC_DIR, 'pwa.ts');
      const code = fs.readFileSync(pwaPath, 'utf-8');
      assert.ok(code.includes("if (!registration) return;"));
      assert.ok(code.includes(".catch("));
    });
  });

  // ===========================================================================
  // Group 3: 离线人本提示与网络恢复契约 (Zero Mutation Invariant)
  // ===========================================================================
  describe('C3: 离线温和降级与网络恢复零写操作不变性', () => {
    test('11. StudentLayout 离线通知包含人本化说明与重试按钮', () => {
      const layoutPath = path.join(SRC_DIR, 'layouts', 'StudentLayout.tsx');
      const code = fs.readFileSync(layoutPath, 'utf-8');
      assert.ok(code.includes('data-testid="pwa-offline-notice"'));
      assert.ok(code.includes('当前处于离线模式'));
      assert.ok(code.includes('需恢复网络后使用'));
    });

    test('12. api.ts 对离线与 503 异常提供人本化温和错误，且绝不许诺虚假自动同步', () => {
      const apiPath = path.join(SRC_DIR, 'api.ts');
      const code = fs.readFileSync(apiPath, 'utf-8');
      assert.ok(code.includes('NETWORK_UNAVAILABLE'));
      assert.ok(code.includes('当前网络不可用，已加载的内容仍然可以查看'));
      assert.ok(code.includes('学习进度、测验结果等需要联网后才能同步'));
      // 严禁承诺“系统稍后会自动同步”等不切实际的暗示
      assert.ok(!code.includes('稍后自动同步'));
      assert.ok(!code.includes('将在后台自动上传'));
    });

    test('13. App.tsx 监听 window online / offline 事件，且 online 恢复时仅触发只读刷新', () => {
      const appPath = path.join(SRC_DIR, 'App.tsx');
      const code = fs.readFileSync(appPath, 'utf-8');
      assert.ok(code.includes("window.addEventListener('online'"));
      assert.ok(code.includes("window.addEventListener('offline'"));
      assert.ok(code.includes('handleRefreshData()'));
      // 断言 online 事件绝不调用写入类接口 (submitQuizAnswer, postLearningActionResult, recordResourceEvent)
      const onlineHandlerSnippet = code.slice(
        code.indexOf("const handleOnline ="),
        code.indexOf("const handleOffline =")
      );
      assert.ok(!onlineHandlerSnippet.includes('submitQuizAnswer'));
      assert.ok(!onlineHandlerSnippet.includes('postLearningActionResult'));
      assert.ok(!onlineHandlerSnippet.includes('recordResourceEvent'));
      assert.ok(!onlineHandlerSnippet.includes('initStudent'));
    });
  });

  // ===========================================================================
  // Group 4: 移动端视口、安全区与触控目标加固测试
  // ===========================================================================
  describe('C4: 移动优先安全区与触控目标合规性', () => {
    test('14. 全局 index.css 声明横向防溢出规范 (overflow-x: hidden)', () => {
      const cssPath = path.join(SRC_DIR, 'index.css');
      const css = fs.readFileSync(cssPath, 'utf-8');
      assert.ok(css.includes('overflow-x: hidden'));
      assert.ok(css.includes('max-width: 100vw'));
    });

    test('15. Header 与 BottomNav 适配 safe-area-inset 顶底防遮挡', () => {
      const headerPath = path.join(SRC_DIR, 'components', 'Header.tsx');
      const navPath = path.join(SRC_DIR, 'components', 'student', 'navConfig.ts');
      const hCode = fs.readFileSync(headerPath, 'utf-8');
      const nCode = fs.readFileSync(navPath, 'utf-8');
      assert.ok(hCode.includes('safe-area-inset-top'), 'Header 必须适配 safe-area-inset-top');
      assert.ok(nCode.includes('safe-area-inset-bottom'), 'BottomNav 必须适配 safe-area-inset-bottom');
    });

    test('16. LearningSessionModal 滚动容器与底部操作区适配 safe-area-inset-bottom', () => {
      const modalPath = path.join(SRC_DIR, 'components', 'student', 'LearningSessionModal.tsx');
      const code = fs.readFileSync(modalPath, 'utf-8');
      assert.ok(
        code.includes('env(safe-area-inset-bottom)'),
        'LearningSessionModal 必须适配 env(safe-area-inset-bottom) 防 Home Bar 遮挡'
      );
    });

    test('17. ExternalRedirectModal 底部适配安全边距并声明取消按钮 test ID', () => {
      const redirectPath = path.join(SRC_DIR, 'components', 'student', 'ExternalRedirectModal.tsx');
      const code = fs.readFileSync(redirectPath, 'utf-8');
      assert.ok(code.includes('data-testid="cancel-redirect-btn"'));
      assert.ok(code.includes('env(safe-area-inset-bottom)'));
    });

    test('18. 核心移动触控按钮严格满足 min-h-[44px] 或 min-h-[48px] 指引', () => {
      const todayCardPath = path.join(SRC_DIR, 'components', 'student', 'TodayActionCard.tsx');
      const redirectPath = path.join(SRC_DIR, 'components', 'student', 'ExternalRedirectModal.tsx');
      const bottomNavPath = path.join(SRC_DIR, 'components', 'student', 'BottomNav.tsx');

      const todayCode = fs.readFileSync(todayCardPath, 'utf-8');
      const redirectCode = fs.readFileSync(redirectPath, 'utf-8');
      const navCode = fs.readFileSync(bottomNavPath, 'utf-8');

      assert.ok(todayCode.includes('min-h-[48px]'), 'TodayActionCard 主 CTA 触控高度必须 >= 44px');
      assert.ok(redirectCode.includes('min-h-[44px]'), 'ExternalRedirectModal 按钮触控高度必须 >= 44px');
      assert.ok(navCode.includes('min-h-[48px]'), 'BottomNav 底部导航触控高度必须 >= 44px');
    });
  });
});
