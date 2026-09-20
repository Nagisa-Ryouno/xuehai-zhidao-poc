# Sprint 10-C Phase 1 — Student Home / Today 实施计划

## 一、阶段定位与核心目标

本阶段是 **Sprint 10-C Phase 1: Student Home / Today（学生端首页产品化）**。

### 1. 唯一目标
将现有学生端功能重新组织成一个真正以「今日学习行动」为核心的学生首页。
使第一次打开学海智导的学生能够立刻理解 **「我现在应该做什么」**：
- **今天学什么**：权威后端解析的唯一最佳今日行动；
- **为什么现在学它**：自然、通俗的人本原因；
- **当前学到什么程度**：直观的当前掌握度百分比（如「当前掌握度 62%」）；
- **接下来做什么**：明确的下一步练习或拓展行动。

### 2. 架构红线与严格约束
- **AI 基础设施扩充全面停止**：不新增任何 DeepSeek / AI 新功能或 Prompt 变动；
- **权威后端 0 变更**：后端学习状态（BKT、PathState、TodayActionResolver、Events）0 变更，只复用既有 API：
  - `GET /api/learning/today/{student_id}`
  - `GET /students/{student_id}/progress`
  - `GET /students/{student_id}/wrong-answers`
  - `GET /api/learning/path/{student_id}/dynamic`
- **冻结目录 0 diff**：
  - `app/` (0 diff)
  - `tests/` (0 diff)
  - `data/seeds/` (0 diff)
  - `gateway/learning/` (0 diff)
  - `gateway/ai/companion/` (0 diff)
  - `gateway/api.py` (0 diff)
  - `gateway/adapter.py` (0 diff)
  - `gateway/config.py` (0 diff)
- **绝对杜绝底层技术黑话与学术术语**：
  - 严禁在学生端首页出现：`BKT`、`PathState`、`mastery_probability`、`Knowledge ID (如 K01)`、`Resource ID (如 R01)`、`Candidate`、`Validator`、`自适应算法`、`智能推荐引擎` 等；
- **全链路真实可用**：所有 CTA 均连接真实学习闭环（调起概念微卡、启动微测验、跳转学情档案或知识图谱），严禁假链接、假页面或 `alert()`。

---

## 二、首页信息架构设计

根据规范，学生端首页在子路由 `/student/tasks` 下统一呈现为以下流式层级：

```
Student Home
│
├── 1. Greeting (问候区)
│   ├── 时段人本问候 (早上好 / 下午好 / 晚上好，{student_name})
│   └── 鼓励副标题 ("今天也学一点吧")
│
├── 2. Today Action (今日学习行动卡片)
│   ├── 标签与类别 ("今日学习" · "继续学习" / "建议再巩固一下" / "该复习一下了" / "做一道小练习")
│   ├── 知识点名称 ({knowledge_name}，无技术 ID 前缀)
│   ├── 当前掌握度 ("当前掌握度 62%")
│   ├── 人本行动解释 (如 "建议继续学习这个知识点" / "已有考点复习未稳固，先重新看看概念，再试一次。")
│   ├── 核心主 CTA ([继续学习] / [重新学习] / [开始快速复测] / [开始练习] / [查看进展])
│   ├── Empty 状态 (NONE: "今天暂时没有待完成的学习任务" · [查看学习进展])
│   ├── Loading 状态 (高度防跳动骨架屏)
│   └── Error 状态 ("暂时无法获取今日学习安排" · [重新加载])
│
├── 3. Next Suggested Action (接下来 / 当前焦点)
│   ├── 行动类别 ("再做一道针对性练习" / "深入拓展学习")
│   ├── 核心考点与简述 ("学完核心考点后，通过针对性小练习检验理解")
│   ├── 针对性 CTA ([开始练习] / [微测验突破])
│   └── 兼容规范 (保留 data-testid="current-focus-card" 与 "突破"/"测验" 语义，无缝兼容既有 UAT)
│
├── 4. Recent Progress (最近进展)
│   ├── 近期掌握度演进 (如 "本周掌握度 +8%" 或 "当前整体掌握度 68%")
│   ├── 轻量学习沉淀 ("已达标掌握 12 个核心考点" / "练习正确率 82%")
│   └── 学情直通链接 ("查看完整学情档案 →")
│
└── 5. Bottom Navigation (底部固定导航)
    ├── 首页 (/student/tasks)
    ├── 学习 (/student/graph)
    ├── 进度 (/student/profile)
    └── AI (/student/assistant)
```

---

## 三、用户审查确认项 (User Review Required)

> [!IMPORTANT]
> 1. **既有 UAT 测试兼容性保全**：
>    既有 UAT 测试（如 `scripts/uat_sprint11_pilot_browser.py`、`scripts/uat_sprint10c_final_browser.py`）依赖选择器 `[data-testid='today-action-card']`、`[data-testid='today-action-cta-btn']`、`[data-testid='current-focus-card']` 以及按钮文案中包含 `"突破"` 或 `"测验"`。
>    **本方案在消除底层黑话的同时，完全保留这些 testid 与核心动作语义**，确保所有历史 UAT 100% 保持通过。
>
> 2. **TodayActionCard 的 NONE 状态由「静默隐藏」升级为「显式人本空状态」**：
>    过去当 action 为 `NONE` 时，卡片直接 `return null`。本阶段按照 Sprint 10-C 规范要求升级为展示「今天暂时没有待完成的学习任务」，并附带「查看学习进展」按钮，严禁渲染假推荐任务。

---

## 四、具体修改方案

### 1. 前端组件改造

#### [MODIFY] [TodayActionCard.tsx](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/frontend/src/components/student/TodayActionCard.tsx)
- **增加 Props**：
  - `currentMasteryPercent?: number | null`（当前考点掌握度百分比，如 62）
  - `error?: string | null`（错误信息）
  - `onRetry?: () => void`（重试回调）
- **实现 Loading 状态**：
  - 渲染具有最小高度（`min-h-[160px]`）的骨架屏，杜绝布局跳动；
- **实现 Error 状态**：
  - 提示「暂时无法获取今日学习安排」，并提供「重新加载」按钮；
- **实现 Empty 状态 (`action.action_type === 'NONE'`)**：
  - 提示「今天暂时没有待完成的学习任务」，副标题「当前阶段学习任务已全部达成」，提供「查看学习进展」CTA，杜绝伪造假数据；
- **实现正常展示态**：
  - 明确呈现：知识点名称、当前掌握度（如「当前掌握度 62%」）、人本行动解释、核心主 CTA；
  - 消除一切底层黑话（严格保持无 Jargon）。

#### [MODIFY] [CurrentFocusCard.tsx](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/frontend/src/components/student/CurrentFocusCard.tsx)
- **精简技术术语**：
  - 移除醒目的硬编码考点 ID（如大号字体的 `K01`、`K08`），直接展示知识点名称；
  - 将技术性的「动态自适应航线 (第 1 站 / 共 N 站)」转化为人本化的「接下来建议行动」；
  - 核心操作按钮保留包含「突破」或「练习」字样的 CTA（如「微测验突破」或「开始练习」），保证既有 UAT 与功能闭环无缝执行。

#### [NEW] [StudentHome.tsx](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/frontend/src/components/student/StudentHome.tsx)
- **创建统一的学生首页聚合组件**：
  - 整合 Greeting、TodayActionCard、Next Suggested Action (CurrentFocusCard)、RecentProgressCard；
  - 计算学生当前的掌握度增量、整体达标考点数与练习概况；
  - 确保页面在 375x812、390x844、平板与桌面端完全自适应，底部预留 `pb-24` 杜绝遮挡。

#### [MODIFY] [StudentLayout.tsx](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/frontend/src/layouts/StudentLayout.tsx)
- **首页渲染收口**：
  - 在 `subRoute === 'tasks'` 时，直接挂载全新产品化的 `StudentHome`；
  - 将 `todayActionError` 与重试机制纳入管理；
  - 保留 `profile` 下的 `HeroBanner`，保持既有全局组件契约完整。

### 2. 测试套件新增

#### [NEW] [frontend/test/sprint10c_student_home.test.ts](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/frontend/test/sprint10c_student_home.test.ts)
- **覆盖契约与组件逻辑**：
  1. Today Action 正常展示契约（知识点名、掌握度、解释、CTA）；
  2. CTA 正确映射契约（各类型对应正确文案与动作）；
  3. NONE 状态契约（展示「今天暂时没有待完成的学习任务」与「查看学习进展」，绝不造假）；
  4. Loading 骨架屏与防布局跳动契约；
  5. Error 状态与重试能力契约；
  6. 当前掌握度展示规范契约（「当前掌握度 62%」，无 BKT / 概率黑话）；
  7. 长知识点名称防溢出与自适应样式契约；
  8. 严禁任何算法黑话（BKT, PathState, Knowledge ID 裸露, Validator 等）。

---

## 五、验证计划

### 1. 自动化单元与契约测试
```bash
# 运行前端全部测试套件（预期全量通过）
npm test --prefix frontend

# 运行静态类型检查
npm run typecheck --prefix frontend

# 运行前端生产打包构建
npm run build --prefix frontend
```

### 2. 独立浏览器端 UAT 验证 (Playwright)
编写或运行专用 UAT 脚本 `scripts/uat_sprint10c_phase1_browser.py`：
- **视口 1**: `375×812`（iPhone X 窄屏）
  - 验证无横向滚动条；
  - 验证 CTA 触控面积满足规范；
  - 验证底部导航不遮挡内容。
- **视口 2**: `390×844`（主流移动端）
  - 验证布局呼吸感良好，卡片无拥挤。
- **视口 3**: `1440×900`（桌面端）
  - 验证桌面端排版与导航完好。
- **状态验证**:
  - Today Action 正常态；
  - Today Action NONE 空状态；
  - Today Action Loading 骨架态；
  - Today Action Error 容错态；
  - CTA 点击后进入真实学习流程（如微测验启动）；
  - 控制台 Console Errors = 0，Page Exceptions = 0，Failed Requests = 0。

### 3. 架构与边界验证
- 验证所有冻结目录 0 diff：
  ```bash
  git diff -- app/ tests/ data/seeds/ gateway/learning/ gateway/ai/companion/ gateway/api.py gateway/adapter.py gateway/config.py
  ```
- 确认 git status 与提交收口。
