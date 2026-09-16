# 学海智导 (Xuehai Zhidao) - 前端工程与 UI 优化开发指南

> 本指南专为负责**界面 UI 视觉与交互体验优化**的小组成员编写。  
> 请在开始调整样式前花 3 分钟阅读本文档，助你高效开发且不破坏现有业务测试。

---

## 1. 技术栈概览 (Tech Stack)

- **核心框架**：React 19 (`^19.2.8`)
- **开发语言**：TypeScript 5.x (严格类型检查 `strict: true`)
- **构建工具**：Vite 8 (`^8.2.2`)
- **样式方案**：Tailwind CSS v4 (`^4.3.3`)
- **图标库**：Lucide React (`^1.41.0`)
- **图表与图谱**：
  - `@xyflow/react` (`^12.11.6`, React Flow 30考点拓扑网络画布)
  - `recharts` (`^3.10.1`, 多维学情能力雷达图)
- **自动化测试**：Vitest 3.x (`npm test`, 54 Suites / 242 Tests, 执行时间 <1.5s)
- **静态代码检查**：Oxlint

---

## 2. 本地快速启动 (Quick Start)

### 步骤 1：安装依赖
确保本地环境已安装 **Node.js 18+**：
```bash
cd frontend
npm install
```

### 步骤 2：启动前端开发服务器
```bash
npm run dev
```
启动后访问控制台输出的本地端口（通常为 `http://127.0.0.1:5173`）。

> **💡 后端通信说明**：  
> 前端 `vite.config.ts` 已默认配置反向代理：所有向 `/api/*` 发起的请求均会自动转发至本地后端服务 `http://127.0.0.1:8011`。  
> 请确保在另一个终端启动了后端网关：`python -m uvicorn gateway.api:app --host 127.0.0.1 --port 8011`。

---

## 3. 核心视图组件目录导引 (Component Inventory)

源码主要位于 `src/` 目录下，以下是重点关注的 UI 组件：

```text
src/
├── components/
│   ├── student/
│   │   ├── ResourceHub.tsx           # ⭐ 自适应学习材料中心 (包含自适应推荐材料、4步学习会话看板、成效反馈卡片、为什么推荐气泡)
│   │   ├── CurrentFocusCard.tsx      # ⭐ 今日任务核心聚焦卡片 (当前焦点知识点、推进按钮、推荐依据面板)
│   │   ├── ExampleReaderModal.tsx    # ⭐ 典型例题精读弹窗 (包含生活商业真实情境剖析、向AI提问快捷入口)
│   │   ├── ResourceCard.tsx          # 学习资源卡片组件 (概念微卡、典型例题、靶向微练)
│   │   ├── KnowledgeGraphView.tsx    # 知识图谱 Tab 主视图
│   │   ├── GraphCanvas.tsx           # React Flow 拓扑图谱渲染核心 (支持缩放、连线高亮、掌握度颜色)
│   │   ├── KnowledgePointQuiz.tsx    # 考点微测验交互组件与防连击状态机
│   │   ├── WrongAnswersView.tsx      # 错题集与靶向巩固练习视图
│   │   ├── StudentDashboard.tsx      # 学生端学情主看板
│   │   ├── ProfileView.tsx           # 学情档案与能力雷达图
│   │   └── BottomNav.tsx             # 移动端触控底部导航栏
│   ├── teacher/
│   │   └── TeacherDashboard.tsx      # 教师端班级宏观分析、薄弱考点预警与干预建议
│   ├── AIAssistant.tsx               # ⭐ AI 伴学对话抽屉、引导式操作 (Guided Actions) 与快速自测 (Quick Check)
│   ├── Header.tsx                    # 顶部导航栏 (包含学生切换、当前考点快速下拉选择)
│   └── RoleSwitcher.tsx              # 右下角学生端 / 教师端身份切换浮动胶囊
├── layouts/
│   ├── StudentLayout.tsx             # 学生端整体页面骨架布局
│   └── TeacherLayout.tsx             # 教师端整体页面骨架布局
├── api.ts                            # 前端向后端网关发起的所有 fetch 请求封装
└── types.ts                          # 前后端数据契约的 TypeScript 类型定义
```

---

## 4. UI/UX 优化核心原则与守则 (Crucial Guidelines)

### ⚠️ 守则 1：绝对保留所有 `data-testid` 属性
本项目拥有全自动化的端到端浏览器测试（Playwright UAT）与契约测试，测试脚本通过 `data-testid` 定位核心卡片与按钮。  
例如：
- `data-testid="recommended-resource-card"`
- `data-testid="start-session-btn"`
- `data-testid="complete-session-btn"`
- `data-testid="quiz-submit-btn"`
- `data-testid="ai-assistant-toggle"`

> **规则**：你可以自由调整元素的样式（`className`）、内边距、字体、阴影、外层布局或动画，**但请务必原样保留 JSX 中的 `data-testid="..."` 属性**，不要改名或删除。

### ⚠️ 守则 2：移动端 375px 窄视口严禁横向溢出
平台设计理念为**移动优先 (Mobile-First)**，在 iPhone SE / 常见小屏手机（宽度 **375px**）下必须具备优秀的排版体验：
- 页面必须保持 `overflow-x: hidden` 或自适应折行，**绝对不能出现横向滚动条**；
- 顶部导航栏、卡片内部徽章、按钮文字在 375px 下应平滑折行或缩短间距；
- 点击靶点（按钮、图标、选择器）触控区域建议维持 $\ge 44 \times 44\text{ px}$。

### ⚠️ 守则 3：严禁在学生界面展示技术底层黑话 (No Jargon)
面向大学生的用户界面必须呈现**温暖、鼓励、清晰的人本导学口吻**：
- ❌ 严禁出现：`BKT`、`Bayesian`、`mastery_probability`、`PathState`、`Decision Core`、`MutationDomain`、`Vector`、`Score` 等工程术语；
- ✅ 正确表达：`掌握度`（百分比，如 80%）、`薄弱` / `发展中` / `已掌握`、`💡 为什么推荐？`、`成效优选 (+2)`、`🔄 这次换一种方式试试`。

### ⚠️ 守则 4：保持 API 契约与类型稳定
- 尽量不要修改 `src/api.ts` 与 `src/types.ts` 中已有字段与方法签名；
- 若需要扩展前端专用的状态或视觉配置，可在对应组件内部自行声明局部 `interface`。

---

## 5. 本地自检三步法 (Pre-commit Verification)

每次优化完样式或组件结构后，在 `frontend` 目录执行以下三条命令进行自检：

```bash
# 1. 静态类型检查 (确认无类型语法报错)
npm run typecheck

# 2. 运行全量契约测试 (242 项测试必须全部通过)
npm test

# 3. 生产打包验证 (确认 Vite 编译打包零错误)
npm run build
```

如果三项全部绿灯，即可放心将你的 UI 成果提交并推送到 GitHub！
