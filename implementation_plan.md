# Sprint 10-C Phase 2 — 学习会话产品化 (Learning Session Productization) 实施方案

> **阶段定位**: 学生端产品化核心推进阶段 (Student Productization)  
> **核心使命**: 解决学生「我点下去以后，能不能顺畅地完成一次真正的学习？」的核心体验问题，将现有分散的概念微卡、学习资源、微测验、即时判题与学情进展串联为连续、直觉、人本闭环的 5-10 分钟学习会话（Learning Session）。  
> **硬性红线**: 
> 1. `allow_production_decision = False` 永久成立，零新增 AI 决策与提示词；
> 2. 后端学习引擎与既有核心接口严格冻结，目录 `app/`, `tests/`, `data/seeds/`, `gateway/learning/`, `gateway/ai/companion/`, `gateway/api.py`, `gateway/adapter.py`, `gateway/config.py` **严格 0 diff**；
> 3. 绝对禁止在学生可见界面呈现任何底层算法与学术技术黑话（No Jargon: 严禁出现 `BKT`, `PathState`, `mastery_probability`, `DynamicPathGenerator`, `QUESTION_ATTEMPT`, 裸露 `K02` 等）；
> 4. 严禁前端推算或伪造掌握度（`oldMastery + 0.08` 绝不容许），掌握度必须来自判题与提交后的服务端权威重新读取；
> 5. 外部资源（MOOC）必须严格经过已实现的 `ExternalRedirectModal`（域名白名单 + HTTPS 校验 + 安全跳转）。

---

## 一、现有能力 → Session Step 映射审计

系统现有底层学习服务与组件已高度完备，本阶段核心原则是：**能复用就绝不重写**，重点在于轻量编排与连续体验收敛。

| Session Step | 目标与交互定义 | 当前系统既有实现 | 使用的 API / Component | 是否需要新增代码 |
| :--- | :--- | :--- | :--- | :--- |
| **1. Entry (导引)** | 告知学生当前正在学什么（人本考点名）、为什么现在学（人本理由）、初始掌握度起点，提供清晰的「开始学习」引导 | `TodayActionCard.tsx`, `CurrentFocusCard.tsx` | `getTodayLearningAction`, `TodayActionCardProps` | **轻量新增 UI 编排**：在 `LearningSessionModal` 中提供人本 Entry 导引视图，杜绝技术代号 |
| **2. Concept (概念)** | 5 大要素卡片（一句话直觉、核心理论、鲜活案例、避坑指南、达成标准），下一步 CTA 明确为「开始小测验」 | `ConceptCardModal.tsx`, `conceptCardData.ts` | `getConceptCard(kid)`, `ConceptCardData` | **复用既有卡片结构**：将内容嵌入连续 Session 容器，去除生硬技术 ID，CTA 固定为「开始小测验」 |
| **3. Resource (资源)** | 展示当前考点 2-3 个精选资源，支持平台内部材料直接阅读，中国大学 MOOC 资源严格经 `ExternalRedirectModal` 打开 | `ResourceHub.tsx`, `ResourceCard.tsx`, `ExternalRedirectModal.tsx` | `getResourcesByKnowledge(kid)`, `ExternalRedirectModal`, `recordResourceEvent` | **复用既有资源层与安全跳转**：嵌入轻量资源列表；实现 500 容错降级，资源失败绝不阻断测验 |
| **4. Quiz (测验)** | 3 题微测验，单题单选作答，未选禁用提交，提交防双击重复，权威判题后即时反馈正误与解析 | `KnowledgePointQuiz.tsx`, `quizModel.ts`, `quizBankData.ts` | `getQuizQuestions(kid)`, `submitQuizAnswer(payload)` | **复用既有测验模型与 API**：严格防重复提交（disabled + 状态锁），剥离技术黑话 |
| **5. Result (结算)** | 测验通关结果，展示「本次练习完成」、正确题数（如 `3 / 3 正确`）、正确率百分比 | `KnowledgePointQuiz.tsx` summary 计算 | `calculateQuizSummary(records)` | **复用与重塑结果呈现**：清晰呈现答题统计，杜绝死胡同 |
| **6. Mastery (掌握度)** | 展示最新认知掌握度（如「当前掌握度 72%」），绝不前端推算，严格来自提交后服务端重新读取 | `submitQuizAnswer` 返回的 `learning_state` | `QuizSubmitResponse.learning_state`, `getTodayLearningAction` | **强化权威状态回读**：若状态加载失败展示友好降级，提供「重新查看」按钮 |
| **7. Next Action (下一步)** | 根据服务端权威重规划推荐，提供「继续下一步」与「返回今日任务」两大出口，顺畅推进 | `getLearningProgressionExplanation`, `TodayActionResolver` | `nextAction`, `onFinish`, `onNextKnowledgePoint` | **打通连续导航**：支持直接衔接下一考点 Session 或优雅回退到 `/student/tasks` |

---

## 二、架构设计与核心组件规划

```
StudentHome (TodayActionCard / CurrentFocusCard)
        │
        ▼ (点击主 CTA: 开始学习 / 继续学习 / 开始复测)
LearningSessionModal (统一全屏/半屏自适应学习会话容器)
        │
        ├── UI Step: ENTRY    ──► 告知学什么 (考点全名) + 为什么学 (人本理由) + 当前掌握度
        │        │
        │        ▼ (点击「开始概念学习」或自动推进)
        ├── UI Step: CONCEPT  ──► 概念微卡 (直觉导引/核心机制/实例/避坑) ──► CTA: [开始小测验]
        │        │ (可选查看资源)
        │        ▼
        ├── UI Step: RESOURCE ──► 精选资源列表 (内部学习 / MOOC 外部经 ExternalRedirectModal 跳转)
        │        │                 (API 500 容错降级，不阻断测验)
        │        ▼ (点击「开始小测验」)
        ├── UI Step: QUIZ     ──► 逐题作答 (未选禁用提交、防双击、即时正误与详解、零黑话)
        │        │
        │        ▼ (最后一题作答完毕)
        └── UI Step: RESULT   ──► 练习完成结算 + 权威掌握度重新读取 + [继续下一步] / [回到今日任务]
```

### 1. 轻量 UI 状态机规范
严格遵从第十四条规范：前端**仅维护 UI 视图步骤**，绝不建立任何业务学习状态机：
```typescript
export type SessionStep = 'ENTRY' | 'CONCEPT' | 'RESOURCE' | 'QUIZ' | 'RESULT';
```
所有学习状态（掌握度、考点推荐、重规划）严格依赖后端返回。

### 2. 异常处理与容错矩阵
1. **Concept 加载失败**: 呈现友好提示「暂时无法加载学习内容」，提供「重新加载」与「直接开始小测验」按钮；
2. **Resource API 失败 (500)**: 绝不阻断学习主链路，呈现「暂时无法加载学习资源」，提供醒目的「直接开始小测验」主按钮；
3. **Quiz 题目加载失败**: 呈现「小测验暂时无法加载」，提供「重新加载」按钮；
4. **Quiz 提交异常**: 按钮立即恢复可点击状态，提示友好错误，允许学生再次点击提交，防重提交锁保持健全；
5. **Result 掌握度读取失败**: 严禁前端推算 `oldMastery + 0.08`，呈现「本次练习已经完成，但暂时无法获取最新学习进展」，并提供「重新查看」重试按钮。

### 3. 防重复提交与幂等设计
- 提交按钮在 `isSubmitting === true` 或 `!selectedOption` 时置为 `disabled`；
- 使用 React `useRef<boolean>(false)` 作为同步信号量锁，浏览器快速连击（Double Click / Triple Click）在 JS 事件循环首个同步 tick 即被拦截，保证只向 `/api/quiz/submit` 发送单次 HTTP 请求。

### 4. 移动端体验规范
- 视口适配：针对 iPhone X (375x812) 与 iPhone 12/13/14 (390x844) 进行样式优化；
- 零横向溢出：`document.documentElement.scrollWidth === clientWidth`；
- 触控友好：所有可点击选项与主 CTA 高度 $\ge 44\text{px}$；
- 浮层防遮挡：弹窗自适应视口高度（`max-h-[90vh]` 或 `min-h-screen`），长考点名称弹性折行。

---

## 三、拟实施文件清单与改动点

### [NEW] `frontend/src/components/student/LearningSessionModal.tsx`
- 职责：承载连续学习会话的统一容器组件；
- 支持 `ENTRY` -> `CONCEPT` -> `RESOURCE` -> `QUIZ` -> `RESULT` 5 大轻量 UI 步骤；
- 嵌入 `ExternalRedirectModal` 保证 MOOC 外链安全；
- 实现统一顶栏步骤条、无技术黑话排版与移动端触控适配。

### [MODIFY] `frontend/src/layouts/StudentLayout.tsx`
- 挂载 `LearningSessionModal`；
- 将 `handleTodayActionCTA`、`handleStartQuiz` 与 `handleViewConceptCard` 统合至 Learning Session 流程；
- 保持向后兼容：现有 `activeQuiz` / `activeConceptCard` 调用平滑桥接到 Session 对应步骤。

### [NEW] `frontend/test/sprint10c_learning_session.test.ts`
- 编写覆盖全部 28 项核心契约的 Vitest 单元与组件测试：
  - Item 1~3: Session Entry (进入、考点名展示、无黑话)
  - Item 4~7: Concept (加载、骨架屏、异常处理、CTA 明确为「开始小测验」)
  - Item 8~10: Resource (内部资源、MOOC 外部弹窗、API 失败不阻断 Quiz)
  - Item 11~16: Quiz (加载、未选禁用、防双击、正确反馈、错误反馈、提交异常恢复)
  - Item 17~21: Result (真实题数正确率、掌握度权威读取、严禁前端推算、异常降级、下一步建议)
  - Item 22~24: Navigation (继续下一步、回到首页、无死路)
  - Item 25~28: Mobile (375x812 布局、390x844 布局、触控靶点 $\ge 44\text{px}$、Modal 防溢出)

### [NEW] `scripts/uat_sprint10c_phase2_learning_session.py`
- 编写 8 大端到端真实 Chromium 验收场景：
  - **Scenario 1**: Today Action -> Session Entry (无黑话、正确考点全称)
  - **Scenario 2**: Concept -> Quiz (页面连续、CTA 有效、无白屏)
  - **Scenario 3**: Quiz Complete (答题、提交、权威掌握度回读、零伪造)
  - **Scenario 4**: Wrong Answer (制造错误答案、友好正误提示、解析、无死路)
  - **Scenario 5**: Resource & MOOC (内部资源阅读，MOOC 外部严格经 ExternalRedirectModal)
  - **Scenario 6**: Partial Failure (Resource API 500 时 Concept/Quiz 仍可畅通完成)
  - **Scenario 7**: Submit Double Click (快速连击提交按钮，严格仅产生 1 次有效作答请求)
  - **Scenario 8**: Mobile Full Session (375x812 完整走通 5 步循环，0 溢出，0 控制台错误，0 失败请求)

---

## 四、验证与回归计划

1. **前端契约与单元测试**:
   - `npm test --prefix frontend` (既有 330 项 + 新增 28+ 项全部 PASS)
2. **前端类型与打包构建**:
   - `npm run typecheck --prefix frontend` (0 错误)
   - `npm run build --prefix frontend` (生产构建成功)
3. **后端只读冻结核验**:
   - `pytest tests/ -q` (143 passed)
   - `pytest gateway/tests/ -q` (558 passed, 2 skipped)
   - `python scripts/sprint10c_pwa_gate.py` (20/20 PASS)
   - `python scripts/sprint10c_final_integration_gate.py` (25/25 PASS)
4. **真实浏览器自动化 UAT**:
   - `python scripts/uat_sprint10c_phase2_learning_session.py` (8/8 场景 PASS，Console 0 错误，Failed Requests 0)
5. **Git 差异与冻结路径校验**:
   - `git diff -- app/ tests/ data/seeds/ gateway/learning/ gateway/ai/companion/ gateway/api.py gateway/adapter.py gateway/config.py` (必须严格 **0 diff**)
   - `git status --short` (提交后保持 clean)

---

## 五、待确认事项 (User Review Required)

- **Entry 步骤引导体验**: 从 Today Action 点击后，建议默认先展示 Entry 概览卡（清晰呈现「为什么学」和当前掌握度起点），并提供「进入概念学习」主按钮；对于复测提醒（`DUE_FOR_REVIEW`）或练习巩固（`PRACTICE`），允许学生直接点击「直接进入小测验」。
- 确认此方案无异议后即可开始实施。
