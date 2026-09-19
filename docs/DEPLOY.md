# 学海智导 · 云端部署指南（路径 A：手机/评委独立访问）

> 目标：把后端 + 前端 PWA 部署到 24h 在线的云服务，之后**任何手机**打开网址即可"添加到主屏幕"成为独立 App，与你的电脑无关。

## 方案一：Render 一键蓝图（推荐，约 8 分钟）

### 步骤

1. 打开 https://render.com ，用邮箱或 GitHub 账号免费注册登录
2. 首页点 **New → Blueprint Instance**
3. 连接你的 GitHub 账号，选择仓库（二选一）：
   - **guoda-design/xuehai-zhidao-poc**（郭达的完整副本，含全部分支与最新代码，推荐）
   - 或原仓库 `Nagisa-Ryouno/xuehai-zhidao-poc`（需要仓库所有者授权 Render 访问）
   分支选 `feat/ui-enhancement`（或等 PR 合并后选 `main`）

   > 若列表里看不到仓库：点页面右侧 GitHub 账号旁的 **Configure account**，
   在 Render GitHub App 的 Repository access 中勾选该仓库（或选 All repositories），保存后刷新页面。
4. Render 会自动检测到仓库根目录的 `render.yaml`，展示将创建的两个服务：
   - `xuehai-api`（后端 API，Free 计划）
   - `xuehai-app`（前端静态站，免费）
5. 点 **Apply**，等待构建完成（首次约 3–6 分钟）
6. 部署完成后访问前端地址：`https://xuehai-app.onrender.com`
   - 手机浏览器打开该地址 → "添加到主屏幕" → 完成独立安装

### 一个可能的 30 秒手动修正

蓝图里 `/api` 转发目标写为 `https://xuehai-api.onrender.com`。如果 Render 给你的后端分配了带随机后缀的域名（如 `xuehai-api-xxxx.onrender.com`）：

1. 在 Render Dashboard 打开 `xuehai-api` 服务，复制它的真实 URL
2. 打开 `xuehai-app` 静态站 → **Redirects/Rewrites**，把 `/api/*` 的 destination 改成真实 URL
3. 保存即可，无需重新部署

### 验证部署成功

- 后端：`https://<后端域名>/api/health` 返回 `{"status":"ok"}`
- 前端：`https://<前端域名>/` 出现玻璃拟态首页，数据正常加载

### 免费计划的已知特性（如实告知）

- **休眠**：15 分钟无请求后服务休眠，下一次打开需 30–60 秒冷启动（评审前提前 1 分钟访问一次唤醒即可）
- **数据易失**：学生答题产生的学情数据写在临时文件系统，服务重启/重新部署后回到初始演示数据（种子数据随仓库自带，界面永远可用）；如需持久化，可在 Render 给 `xuehai-api` 挂一块 Disk（付费）并配置数据目录环境变量

## 方案二：Railway（备选）

1. https://railway.com 注册 → **New Project → Deploy from GitHub repo**
2. 选择本仓库，Railway 自动用根目录 `Dockerfile` 构建后端
3. 为后端服务生成域名（Settings → Generate Domain）
4. 前端按"静态站"新建服务：`cd frontend && npm install && npm run build`，发布目录 `frontend/dist`，并在 `frontend` 层加一个把 `/api` 代理到后端域名的规则（或直接用 `python scripts/serve_dist.py` 思路的静态+代理服务）

## 方案三：自有服务器（阿里云/腾讯云等）

```bash
git clone https://github.com/Nagisa-Ryouno/xuehai-zhidao-poc.git
cd xuehai-zhidao-poc
docker build -t xuehai-api .
docker run -d --restart=always -p 8011:8011 xuehai-api
cd frontend && npm install && npm run build
# 用 Nginx 托管 frontend/dist，并把 /api 代理到 127.0.0.1:8011
```

Nginx 关键配置：

```nginx
location /api/ { proxy_pass http://127.0.0.1:8011; }
location / { root /var/www/xuehai/dist; try_files $uri /index.html; }
```

## 部署后

- 手机（安卓 Chrome / iPhone Safari）打开前端域名 → 添加到主屏幕 → 独立 App
- 评委无需接触你的电脑，任何网络下均可体验
