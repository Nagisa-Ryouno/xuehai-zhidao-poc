/**
 * sw.js - 学海智导 (Xuehai Zhidao) Student PWA Service Worker
 *
 * 职责与边界：
 * 1. App Shell 与静态前端资源缓存 (Cache First with Network Fallback)
 * 2. 导航请求离线回退至 App Shell (Navigation Fallback to /index.html)
 * 3. 动态权威 API 请求绝对不进入持久缓存 (Network-Only / No SW Cache for /api/*)
 * 4. 严禁在 SW 中实现 BKT、PathState、学习事件、AI 推荐或私有会话逻辑
 * 5. 安全版本生命周期管理与旧缓存清理 (skipWaiting & clients.claim)
 */

const CACHE_VERSION = 'xuehai-pwa-v1';
const STATIC_CACHE_NAME = `static-${CACHE_VERSION}`;
const SHELL_CACHE_NAME = `shell-${CACHE_VERSION}`;

// 预缓存的最小 App Shell 核心骨架与静态资产清单
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/student',
  '/student/tasks',
  '/manifest.webmanifest',
  '/favicon.svg',
  '/pwa-icon.svg',
  '/pwa-192x192.png',
  '/pwa-512x512.png',
  '/pwa-maskable-512x512.png',
];

// 安装阶段：预缓存 App Shell 基础静态资源
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => {
      // 立即接管，免去等待旧 SW 退出
      return self.skipWaiting();
    }).catch((err) => {
      console.warn('[PWA SW] Precache warning:', err);
    })
  );
});

// 激活阶段：清理旧版本缓存并声明控制权
self.addEventListener('activate', (event) => {
  const allowedCaches = [STATIC_CACHE_NAME, SHELL_CACHE_NAME];
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (!allowedCaches.includes(cacheName)) {
            console.log('[PWA SW] Deleting obsolete cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// 抓取策略仲裁
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 1. 绝对红线：动态 API 请求一律走网络直连，绝对禁止 SW 持久缓存
  // 保证 BKT、PathState、Learning Events、AI 推荐、TodayAction 权威状态不被陈旧数据污染
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(() => {
        // 网络不可用时返回标准 503 JSON，绝不伪造成功响应
        return new Response(
          JSON.stringify({
            error: 'NETWORK_UNAVAILABLE',
            message: '当前网络不可用，请检查网络连接后重试。',
            is_offline: true,
          }),
          {
            status: 503,
            headers: { 'Content-Type': 'application/json; charset=utf-8' },
          }
        );
      })
    );
    return;
  }

  // 2. 页面导航请求 (HTML Navigation)：Network First, Fallback to Cached App Shell
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          // 若网络响应正常，存入 Shell 缓存供离线使用
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(SHELL_CACHE_NAME).then((cache) => {
              cache.put(request, responseToCache);
            });
          }
          return networkResponse;
        })
        .catch(async () => {
          // 离线时安全回退至已缓存的导航页或 /index.html 骨架
          const cachedResponse = await caches.match(request);
          if (cachedResponse) return cachedResponse;

          const shellResponse = await caches.match('/index.html');
          if (shellResponse) return shellResponse;

          return caches.match('/');
        })
    );
    return;
  }

  // 3. 静态构建资源 (.js, .css, .woff2, .png, .svg 等)：Cache First with Network Fallback
  const isStaticAsset =
    url.pathname.startsWith('/assets/') ||
    url.pathname.endsWith('.js') ||
    url.pathname.endsWith('.css') ||
    url.pathname.endsWith('.svg') ||
    url.pathname.endsWith('.png') ||
    url.pathname.endsWith('.ico') ||
    url.pathname.endsWith('.woff2');

  if (isStaticAsset) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(STATIC_CACHE_NAME).then((cache) => {
              cache.put(request, responseToCache);
            });
          }
          return networkResponse;
        });
      })
    );
    return;
  }

  // 4. 其他常规请求：直接走网络
  event.respondWith(fetch(request));
});
