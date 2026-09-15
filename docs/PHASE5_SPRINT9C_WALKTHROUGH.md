# Phase 5 / Sprint 9-C 封版交付报告与演练指南 (Walkthrough)

**项目名称**：学海智导 (Xuehai Zhidao) — AI驱动的大学生个性化学习指导平台  
**当前阶段**：Phase 5 — AI Companion & Intelligent Study Assistance  
**Sprint 周期**：Sprint 9-C — 学习资源中心与资源感知自适应学习 (Learning Resource Hub & Resource-aware Adaptive Learning)  
**交付时间**：2026-09-15  
**基线提交**：`79b8d15` (Sprint 9-B 封版基线 `feat(ai): add guided learning actions and reflection loop`)  

---

## 一、Sprint 9-C 交付目标与系统演进

在经过 Phase 4（30考点图谱、BKT掌握度追踪、动态路径、学情档案）与 Phase 5 前期（Sprint 9-A 伴学对话、Sprint 9-B 确定性引导行动与闭环反思）之后，系统已具备“精准获知学生弱点、推荐下一步学习动作”的能力。

然而，过去的动作建议主要停留在“看概念卡片”或“做微测验”，缺乏**真正可执行、多层次、系统化的全套学习材料**。

**Sprint 9-C 的核心使命**：
> **让系统从“知道学生下一步应该学什么”，升级为“能够为学生提供真正可执行、高质量、自适应匹配认知状态的全套学习材料”。**

构建全图谱 30 考点（K01~K30）完备覆盖的**学习资源中心 (Learning Resource Hub)** 与**资源感知自适应推荐引擎 (Resource-aware Adaptive Recommendation)**。

---

## 二、双层架构与单向依赖流

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   学生端 (Student UI)                                   │
│   今日任务 (Tasks) / 学习资源 (Resources) / 知识图谱 (Graph) / 学情档案 (Profile) / AI伴学     │
└───────────────────────────┬────────────────────────────────────────────┬───────────────┘
                            │                                            │
                            ▼                                            ▼
┌───────────────────────────────────────────────────────┐ ┌─────────────────────────────┐
│             学习资源中心 (Learning Resource Hub)        │ │   AI伴学层 (Companion)     │
├───────────────────────────────────────────────────────┤ ├─────────────────────────────┤
│ • 30 考点 130 项内部官方学习材料静态库 (Catalog)         │ │ • 4 种辅导模式              │
│ • 5 种资源类型：微卡 / 例题精析 / 靶向微练 / 讲义 / 视频  │ │ • Guided Actions 引导       │
│ • 步骤化自适应导引：步骤 1 ➔ 步骤 2 ➔ 步骤 3           │ │ • Quick Check 30 考点       │
│ • 确定性推荐规则引擎 (Cases A ~ E，零黑话，零随机)     │ │ • 学习成果反思 (Reflection)  │
│ • 材料研读模态框 (生活商业案例拆解 + 防坑指南)          │ └──────────────┬──────────────┘
│ • 辅助交互遥测日志 (data/resource_events.jsonl)        │                │
└───────────────────────────┬───────────────────────────┘                │
                            │ (只读读取掌握度)                            │ (只读读取掌握度)
                            ▼                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        底层权威学习引擎与持久化 (Single Source of Truth)                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ • BKT 贝叶斯知识追踪状态 (data/bkt_states.json) — 生产决策唯一权威事实源                  │
│ • 知识图谱 30 考点依赖 DAG 拓扑 (data/seeds/knowledge_graph.json)                       │
│ • 正式学习事件日志 (data/learning_events.jsonl) — 仅由官方测验提交追加落盘                │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心设计原则与安全红线实施

1. **架构冻结目录绝对 0 差异 (Zero Diff)**：
   - 核心领域与迁移目录 `app/`、`tests/`、`data/seeds/` 严格保持 0 diff（`git diff --stat HEAD -- app/ tests/ data/seeds/` 输出严格为空）。
2. **零伪造外部链接 (Zero Synthetic External Links)**：
   - 所有 130 项学习资源均为系统原生高质量材料（`is_external=False`，`source="xuehai_internal"`），禁止生成任何不可访问或失效的第三方假外链。
3. **权威 BKT 单一事实源与零生产突变 (Zero Mutation Invariant)**：
   - 学习资源模块完全基于底层权威 BKT 计算结果进行自适应推导，资源本身**绝对不拥有修改掌握度、路径状态或改写 BKT 状态文件的权限**。
4. **遥测事件物理隔离 (Telemetry Event Isolation)**：
   - 学生在资源中心的浏览、开启、阅读完成等辅助交互事件严格追加落盘至 `data/resource_events.jsonl`，与正式作答事件 `data/learning_events.jsonl` 物理隔离，保持正式学情数据的高度纯洁。
5. **杜绝底层工程技术黑话 (No Jargon)**：
   - 界面推荐文案、自适应理由与导向说明中，绝对杜绝出现 `BKT`、`Bayesian`、`mastery_probability`、`PathState` 等内部工程术语，全量采用学生友好的人本导向表达。

---

## 四、自适应推荐决策引擎 (Cases A ~ E)

根据学生在目标考点的客观掌握度 $P(L)$ 以及历史连续作答受阻次数，推荐引擎严格输出步骤化材料序列（步骤 1 ➔ 步骤 2 ➔ 步骤 3）：

| 场景分支 | 触发条件 | 推荐材料位次与步骤序列 | 人本化推荐原因说明 (No Jargon) |
| :--- | :--- | :--- | :--- |
| **Case A** | 考点基础薄弱<br>($P(L) < 0.60$) | **步骤 1**：考点精要微卡 (CONCEPT_CARD)<br>**步骤 2**：典型生活例题 (EXAMPLE)<br>**步骤 3**：靶向通关微练 (PRACTICE) | 考点当前处于基础起步阶段，建议先通读概念卡片，再结合生活实例加深理解，最后进行靶向自测巩固。 |
| **Case B** | 考点发展进阶中<br>($0.60 \le P(L) < 0.80$) | **步骤 1**：典型生活例题 (EXAMPLE)<br>**步骤 2**：靶向通关微练 (PRACTICE)<br>**步骤 3**：核心精讲讲义 (DOCUMENT) | 考点已具备一定基础，建议重点剖析典型商业实例与避坑要点，并完成靶向测验冲击熟练掌握。 |
| **Case C** | 考点已熟练达标且有未掌握后继<br>($P(L) \ge 0.80$) | **步骤 1**：靶向通关微练 (PRACTICE)<br>**步骤 2**：核心精讲讲义 (DOCUMENT)<br>**步骤 3**：考点精要微卡 (CONCEPT_CARD) | 该考点已达标掌握，可通过简短测验温故知新，或深入阅读讲义扩展知识面，准备迎接后续新考点。 |
| **Case D** | 考点已达标且为图谱终点考点<br>($P(L) \ge 0.80$) | **步骤 1**：核心精讲讲义 (DOCUMENT)<br>**步骤 2**：典型生活例题 (EXAMPLE)<br>**步骤 3**：考点精要微卡 (CONCEPT_CARD) | 该考点已达成最终熟练状态，推荐阅读综合讲义梳理学科知识体系，融会贯通章节综合应用。 |
| **Case E** | 连续作答受阻<br>($\text{consecutive\_incorrect} \ge 2$) | **步骤 1**：考点精要微卡 (CONCEPT_CARD)<br>**步骤 2**：典型生活例题 (EXAMPLE)<br>**步骤 3**：靶向通关微练 (PRACTICE) | 近期该考点连续作答受阻（≥2次），建议暂缓直接刷题，先回归概念卡片梳理核心要点与生活例题，排查思维误区。 |

---

## 五、前后端全栈交付资产清单

### 5.1 后端服务 (`gateway/learning/resources/`)
- `models.py`：定义资源类型枚举、学习资源实体模型、推荐序列模型、事件载荷模型。
- `catalog.py`：构建 130 个全覆盖静态学习材料目录，涵盖 30 个宏微观经济学考点。
- `events.py`：线程安全的追加写资源日志持久化层（`data/resource_events.jsonl`）。
- `resolver.py`：零黑话、确定性自适应材料推荐裁决引擎。
- `api.py`：挂载 `/api/learning/resources/...` 资源接口路由与辅助事件分流。

### 5.2 前端视图组件 (`frontend/src/`)
- `components/student/ResourceHub.tsx`：学习资源中心主视图（自适应推荐横幅、考点选择器、类型过滤筛选器、关键词动态搜索）。
- `components/student/ResourceCard.tsx`：标准化资源卡片（类型标识、预估耗时、难度系数、行动 CTA 按钮、AI 伴学提问快捷入口）。
- `components/student/ExampleReaderModal.tsx`：沉浸式例题与讲义精读模态框（真实商业情境拆解、易错陷阱避坑指南、标记研读完成）。
- `components/student/CurrentFocusCard.tsx`：今日任务焦点卡新增「📚 推荐学习材料」快捷直达按钮。
- `layouts/StudentLayout.tsx`：集成桌面端顶部主导航 `学习资源` Tab、移动端微调及跨模态弹窗调度。

---

## 六、全量测试验证与质量门禁执行证据

### 6.1 历史与当前质量门禁 100% 通过 (Quality Gates Matrix)

| 门禁流水线脚本 | 检查项 | 验证结果 | 重点验证内容 |
| :--- | :---: | :---: | :--- |
| `scripts/sprint9c_quality_gate.py` | 12 / 12 | **PASS (GREEN)** | 冻结目录0 diff、30考点100%覆盖、130项官方资源完备性、无假外链、Case A~E推荐准则、确定性一致断言、遥测事件物理隔离、零BKT突变、无黑话合规、后前端全量测试通过 |
| `scripts/sprint9b_quality_gate.py` | 12 / 12 | **PASS** | Guided Actions契约、Quick Check 30考点覆盖与零突变、学习反思增量捕获、无黑话、伴学事件隔离 |
| `scripts/sprint9a_quality_gate.py` | 10 / 10 | **PASS** | 伴学4模式完备性、防注入拦截、零突变快照不变量、只读元数据硬编码 |
| `scripts/sprint8d_quality_gate.py` | 10 / 10 | **PASS** | 单一事实源、学生数据隔离、教师端只读完整性、生产环境前端构建通过 |
| `scripts/sprint8c_quality_gate.py` | 10 / 10 | **PASS** | 30考点学情汇总、错题归因分析、教师看板无副作用 |
| `scripts/sprint8b_dynamic_path_gate.py` | 12 / 12 | **PASS** | 前测摸底脱敏、动态路径推荐、前置图谱拓扑硬约束 |

### 6.2 自动化测试套件执行证据
- **后端测试 (`pytest gateway/tests/`)**：
  - `gateway/tests/test_sprint9c_learning_resources.py`：**28 / 28 PASSED**
  - Gateway 全量回归：**370 / 370 PASSED** (耗时 8.00s，0 失败)
- **前端测试 (`npm test --prefix frontend`)**：
  - `frontend/test/sprint9c_learning_resources.test.ts`：**12 / 12 PASSED**
  - 前端全量回归：**222 / 222 PASSED** (耗时 1.06s，0 失败)
- **生产构建 (`npm run build --prefix frontend`)**：
  - TypeScript 类型检查：0 错误
  - Vite 生产打包：成功输出 `dist/`，gzip 优化完毕

---

## 七、12 场景端到端浏览器 UAT 验收与截图矩阵

执行 `python scripts/uat_sprint9c_browser.py`，12 项端到端业务旅程全量通过，控制台 0 报错、网络请求 100% 成功，截图均持久化保存至 `artifacts/uat_screenshots/`：

| 编号 | 验收场景 (Scenario) | 验证重点与断言 | 产出截图文件 |
| :---: | :--- | :--- | :--- |
| **A** | 访问「今日任务」视图 | 验证桌面 5-Tab 主导航呈现「学习资源」Tab；焦点卡展示「📚 推荐学习材料」快捷按钮 | `sprint9c_01_tasks_page_recommended_resources.png` |
| **B** | 进入学习资源中心 | 点击 Tab 直达 `/student/resources`，主界面渲染标题、副标题与自适应材料库骨架 | `sprint9c_02_resource_hub_view.png` |
| **C** | 验证自适应导引横幅 | 呈现当前考点客观掌握度、步骤 1、步骤 2、步骤 3 步骤化建议与人本化导引文案 | `sprint9c_03_adaptive_recommendation_banner.png` |
| **D** | 考点微卡分类过滤 | 点击「考点微卡」分类标签，材料列表即时精准过滤为 CONCEPT_CARD | `sprint9c_04_resource_type_filter_concept.png` |
| **E** | 典型例题分类过滤 | 点击「典型例题」分类标签，材料列表呈现 EXAMPLE 题目并展示「研读例题」按钮 | `sprint9c_05_resource_type_filter_example.png` |
| **F** | 打开例题研读模态框 | 点击「研读例题」，弹出沉浸式研读弹窗，完整展示生活商业实例拆解与建议耗时 | `sprint9c_06_open_example_reader_modal.png` |
| **G** | 标记研读完成与上报 | 点击「研读完毕，标记完成」，状态流转为已完成，辅助事件成功追加写入日志 | `sprint9c_07_example_modal_complete_action.png` |
| **H** | 从资源中心查看微卡 | 点击「查看微卡」，顺利调起系统官方考点精要速览微卡，直觉导引与关键机制呈现完整 | `sprint9c_08_open_concept_card_from_hub.png` |
| **I** | 关键词检索动态筛选 | 在搜索框输入「稀缺性」，材料列表即时响应联动，仅展示相关考点匹配材料 | `sprint9c_09_search_keyword_filter.png` |
| **J** | 调起官方通关微测验 | 在靶向微练卡片点击「开始微练」，调起官方通关微测验底部抽屉，实现无缝练测闭环 | `sprint9c_10_launch_quiz_from_practice_card.png` |
| **K** | 多生上下文隔离验证 | 切换学生上下文 (S001 -> S002)，资源中心自适应推荐依据新学生状态精准更新 | `sprint9c_11_student_context_isolation.png` |
| **L** | 移动端自适应与人体工学 | 调整视口至 375x812 移动端规格，底部主导航保持 4-Tab 人体工学，布局自适应响应良好 | `sprint9c_12_mobile_bottom_nav_ergonomics.png` |

---

## 八、验收结论

**Sprint 9-C — 学习资源中心与资源感知自适应学习** 已经全面达成设计标准：
1. 建立健全 30 考点覆盖的 130 项内部高质量自营学习材料库；
2. 达成确定性自适应材料推荐模型（Cases A ~ E）；
3. 实现材料浏览、精读研读、标记完成、微卡查看与微测验调起的全流程交互闭环；
4. 恪守架构边界（app/ tests/ seeds/ 零修改、BKT 掌握度零突变、遥测日志严格物理隔离）；
5. 通过所有历史和当前自动化门禁，完成 Playwright 真实浏览器端到端全绿验收。

**Sprint 9-C 具备正式封版与 Git 提交条件。**
