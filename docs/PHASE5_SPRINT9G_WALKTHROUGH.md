# Phase 5 / Sprint 9-G — 今日学习行动聚合 Lite 交付总览

> **国家级大学生创新创业训练计划项目 · 学海智导 (Xuehai Zhidao)**  
> **阶段**：Phase 5 — Today's Learning Action Aggregation Lite (今日学习行动聚合 Lite)  
> **封版日期**：2026-09-19  
> **Git 推荐提交信息**：`feat(learning): add today's learning action`

---

## 一、Sprint 9-G 核心目标与范围控制

### 1. 核心目标
在 Sprint 9-A 到 9-F 已经沉淀的多维能力（AI伴学、学后反思、资源中心、成效反馈、策略自适应、保持度复测）之上，通过一个非常薄的聚合层，在学生进入 `/student/tasks`（今日任务中心）时提供唯一的**「今日学习」行动卡片**，精准回答学生：
> **“我现在最适合做什么？”**

### 2. 严格安全红线与架构不变性 (Invariants)
- **绝对只读与零遥测负担**：不新增 `TODAY_ACTION_VIEW` 或其他 JSONL 日志，只读聚合现有数据源；
- **底层数据文件零污染**：严禁修改 `data/bkt_states.json` 与 `data/learning_events.jsonl`；
- **冻结目录零改动**：`app/`、`tests/`、`data/seeds/` 目录严格保持 0 diff；
- **纯确定性与时间无关幂等**：相同数据快照与时间基准下重复调用 50 次，输出严格一致；
- **人本温度与无黑话**：UI 提示严禁出现 BKT、P(L)、贝叶斯、算法分值与学术黑话。

---

## 二、确定性优先级仲裁阶梯 (`TodayActionResolver`)

```text
1. NEEDS_REINFORCEMENT (优先级 1)
   action_type = REVIEW_RETENTION
   title = 建议再巩固一下
   cta_label = 重新学习 (调起概念速览微卡)
   priority_reason = 已有考点复习未稳固，需针对性巩固

2. DUE_FOR_REVIEW (优先级 2)
   action_type = REVIEW_RETENTION
   title = 该复习一下了
   cta_label = 开始快速复测 (调起微测验突破抽屉)
   priority_reason = 已有考点达到复习间隔时间

3. IN_PROGRESS / AVAILABLE (优先级 3)
   action_type = CONTINUE_LEARNING
   title = 继续学习：{knowledge_name}
   cta_label = 开始学习 (调起概念学习或微测)
   priority_reason = 当前学习路径中的首要未完成任务

4. PRACTICE (优先级 4)
   action_type = PRACTICE
   title = 做一道小练习
   cta_label = 开始练习 (调起微测验)
   priority_reason = 推荐靶向微练保持学习节奏

5. VIEW_PROGRESS (优先级 5)
   action_type = VIEW_PROGRESS
   title = 看看最近的学习进展
   cta_label = 查看学情 (跳转 /student/profile)
   priority_reason = 当前所有阶段任务已全部达标

6. NONE (优先级 6)
   action_type = NONE
   title = ""
   卡片遵循静默原则，完全不渲染 (null)
```

**平局仲裁规则**：当多个考点处于相同保持度状态时，严格按 `knowledge_id` 字典序升序选择首个。

---

## 三、代码实现清单与目录结构

```text
gateway/learning/today/
├── __init__.py           # 导出 TodayActionResolver, default_today_action_resolver, 模型
├── models.py             # 定义 TodayActionType, TodayLearningAction, TodayActionResponse
└── resolver.py           # 核心 6 级确定性优先级仲裁解析器

gateway/api.py            # 挂载只读端点 GET /api/learning/today/{student_id}

frontend/src/
├── types.ts              # 导出 TodayActionType, TodayLearningAction, TodayActionResponse
├── api.ts                # 封装 getTodayLearningAction(studentId)
├── components/student/
│   └── TodayActionCard.tsx # 「今日学习」人本行动卡组件 (data-testid, 375px 无横向滚动)
└── layouts/
    └── StudentLayout.tsx # 在 /student/tasks 顶部挂载，处理 CTA 闭环与学生切换隔离
```

---

## 四、验证证据总览

### 1. 后端单元与集成测试 (`gateway/tests/test_sprint9g_today_action.py`)
- **12/12 Tests Passed (100%)**
  - 覆盖 6 级优先级、平局升序仲裁、多学生隔离、404 隔离、50 次时间幂等性、只读零污染。

### 2. 前端契约测试 (`frontend/test/sprint9g_today_action.test.ts`)
- **8/8 Tests Passed (100%)**
  - 覆盖类型枚举、实体结构、文案合规、无技术黑话、多学生切换、NONE 静默契约。

### 3. 全套回归套件
- **后端回归**：`pytest gateway/tests/` (441 passed) + `pytest tests/` (143 passed) = **584 passed (100%)**
- **前端回归**：`npm test --prefix frontend` = **260 passed (100%)**
- **前端类型**：`npm run typecheck` = **0 errors**
- **生产构建**：`npm run build` = **PASS (dist 生成成功)**

### 4. 质量门禁链
- `python scripts/sprint9g_quality_gate.py`: **8/8 Passed (100%)**
- `python scripts/sprint9f_quality_gate.py`: **8/8 Passed (100%)**
- `python scripts/sprint9e_quality_gate.py`: **9/9 Passed (100%)**

### 5. 端到端浏览器 UAT (`scripts/uat_sprint9g_browser.py`)
- **4/4 Scenarios Passed (100%)**
  - Scenario A: NEEDS_REINFORCEMENT $\to$ 重新学习 $\to$ 概念微卡
  - Scenario B: DUE_FOR_REVIEW $\to$ 开始快速复测 $\to$ 微测验
  - Scenario C: IN_PROGRESS / PRACTICE $\to$ 推荐练习 / 继续学习
  - Scenario D: 学生切换上下文隔离与 375x812 移动端排版无横向溢出
- **Console Errors**: 0
- **Failed Requests**: 0
- **截图归档**：`artifacts/uat_screenshots/sprint9g_01~04.png`
