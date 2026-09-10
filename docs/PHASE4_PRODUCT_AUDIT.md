# 学海智导 (Xuehai Zhidao) — Phase 4 / Sprint 8 产品审计与体验架构白皮书
## PHASE4_PRODUCT_AUDIT: From AI Infrastructure to Usable Learning Experience

---

## 1. Executive Summary (执行摘要)

「学海智导」经过前期研发，已成功在底层构建了坚实可信的 AI 自适应学习与评测基础设施（Stage G1~G4 全部验收通过，238 项 Gateway 测试、172 项前端契约测试与 160 项后端架构及回归测试 100% PASS）。

然而，当前工程仍处于典型**“技术基础设施成熟，但产品体验割裂”**的临界状态：
1. **真实学生无入口**：系统写死了 5 名虚拟学生画像（S001~S005），没有注册登录，缺乏任何新用户 Onboarding 与学习目标输入端；
2. **学习闭环仅对 S001 单人成立**：30 个微观经济学考点中仅 8 个考点拥有微测验题目（共 13 题）。除 S001 外，其余 4 位预置学生（S002、S003、S004、S005）的学习路径在执行第 1 步或后续步骤时均会遭遇“暂无可用题目”中断，S004 甚至路径为空；
3. **“只测不学”的体验缺陷**：当前核心任务卡仅有“开始微测验”按钮，完全缺失概念解析、讲义、例题等轻量化学习承载；
4. **架构集成微断裂**：AI 伴学助手调用的 `/api/ai/companion` 接口实际定义在独立 Gateway 应用中，主 API 应用 (`app.main:app`) 未做路由挂载，导致前端在开发与标准生产环境下始终触发 404 并被动进入离线兜底；
5. **教师端为纯骨架占位**：教师决策驾驶舱三个模块全为 `P0-10~P0-12 预留` 的空白卡片。

本审计报告基于真实代码库，全面盘点现有技术资产，识别产品化断点，并提出以“10 分钟完成真实自适应学习闭环”为目标的 Phase 4 MVP 实施方案。

---

## 2. Current Product State (当前产品现状)

| 维度 | 现状评估 | 真实代码依据与描述 |
|---|---|---|
| **代码冻结区** | `app/`, `tests/`, `data/seeds/` 严格 0 diff | `git diff --stat -- app/ tests/ data/seeds/` 输出为空 |
| **测试门禁** | 100% 通过 | Gateway 238/238, Frontend 172/172, Backend 160/160, G1~G4 Gates 全部 PASS |
| **运行时数据** | 混合持久化 | 静态种子位于 `data/seeds/`，动态状态写入 `data/runtime/` (JSON / JSONL) |
| **前端架构** | React 19 + TypeScript + Tailwind CSS v4 + Vite + @xyflow/react | 纯前端状态机驱动，单页面应用，无第三方重型状态库 |
| **后端架构** | FastAPI 模块化单体 (`app/`) + 独立 Gateway 网关 (`gateway/`) | 清晰分层（Core, Domain, Services, Infrastructure, API） |
| **真实用户可用性** | **不可用于陌生真实学生** | 仅供展示演示（Demo Only），依赖硬编码 Persona |

---

## 3. Existing User Journey (现有用户路径实测追踪)

以一名全新访问系统的大学生视角，复盘当前完整交互轨迹：

```text
[打开浏览器访问 http://localhost:5173/]
                 │
                 ▼
     [重定向至 /student/tasks]
                 │
                 ▼
[Header 下拉框写死 S001~S005，自动绑定 S001 张伟]
   - 疑问：我是谁？为什么我是张伟？我的专业为什么是经济学？
                 │
                 ▼
[看到 HeroBanner: "个人学习目标: 掌握微观经济学基础并能够解决综合分析题..."]
   - 疑问：这不是我的目标，我无法修改它。
                 │
                 ▼
[今日核心重点任务卡: K08 需求价格弹性]
   - 提示：当前掌握度 42%，目标 80%
   - 点击“为什么先学这个考点？”：展开推荐理由与先修依赖（体验良好）
                 │
                 ▼
[点击“开始微测验”]
   - 弹出 BottomSheet 测验抽屉
   - 题库成功加载 2 道题目 (Q07, Q08)
   - 学生答题、查看单题解析与用时
                 │
                 ▼
[测验通关结算]
   - 掌握度跃迁：42.00% → 81.18% (+39.18%)
   - 阶段变化：薄弱 → 已掌握
   - 局部重规划：触发 UNLOCK_DOWNSTREAM，成功解锁 K09
   - 操作栏：高亮展示“继续学习下一个考点 K09”
                 │
                 ▼
[点击“继续学习下一个考点 K09”]
   - 弹窗刷新载入 K09 微测验
   - 答题通关，解锁 K11
                 │
                 ▼
[继续学习 K11]
   - 答题通关，解锁 K12
                 │
                 ▼
[点击“继续学习下一个考点 K12”]
   - ❌ 阻断故障：页面弹出红字“该知识点暂无可用微测验题目”
   - 学习闭环在此处彻底中断！
```

若用户在顶部将学生切换为 **S002** 或 **S005**：
- 第一步核心任务即为 **K14 (预算约束线)**；
- 点击“开始微测验”，立即提示 **“该知识点暂无可用微测验题目”**；
- 用户在第 1 分钟即被彻底卡死，无法体验任何自适应流转！

---

## 4. Current Page / Route Inventory (前端页面与路由清单)

| 页面 / 路由 | 对应组件 / 布局 | 主要功能 | 依赖 API | 完成度 | 存在的核心问题 |
|---|---|---|---|---|---|
| `/` 或空路径 | `router.ts` | 根路径重定向 | 无 | COMPLETE | 强制跳转 `/student/tasks` |
| `/student/tasks` | `StudentLayout` (subRoute='tasks') | 今日核心任务卡、学习路径时间轴、快捷导航 | `/api/students/{id}/dashboard`, `/api/students/{id}/path-states` | COMPLETE | 依赖静态路径；无概念学习；S004 呈现空白卡 |
| `/student/graph` | `StudentLayout` (subRoute='graph') | 30 考点拓扑网络、状态筛选、详情抽屉 | `/api/students/{id}/knowledge-graph` | COMPLETE | 22/30 考点抽屉点击“开始测验”会报空题库错误 |
| `/student/profile` | `StudentLayout` (subRoute='profile') | 学情档案、雷达图、薄弱知识点、AI诊断建议 | `/api/students/{id}/profile`, `/api/students/{id}/report` | COMPLETE | 数据来源于离线 Excel 静态切片，缺乏动态历史趋势 |
| `/student/assistant` | `StudentLayout` (subRoute='assistant') | AI 导师伴学答疑、快捷提问、相关考点卡 | `/api/students/{id}/assistant`, `/api/ai/companion` | PARTIAL | 网关路由未挂载，始终触发异常进入离线纯规则兜底 |
| `/teacher` | `TeacherLayout` | 教师学情监控驾驶舱 | `/api/students` | DEMO_ONLY | 3 个模块全部为占位卡片 (`P0-10~P0-12 预留`) |

---

## 5. Backend Capability Inventory (后端能力盘点)

| 后端模块 / 路由 | 端点 (Endpoint) | 数据源 / 机制 | 真实能力评价 | 状态 |
|---|---|---|---|---|
| **学生与全景看板** | `GET /api/students`<br>`GET /api/students/{id}/dashboard`<br>`GET /api/students/{id}/profile`<br>`GET /api/students/{id}/report` | `ProfileRepository` (读取 seeds/output JSON) | 稳定提供 5 位学生聚合学情 | COMPLETE |
| **推荐路径** | `GET /api/students/{id}/learning-path`<br>`GET /api/learning-paths` | `ProfileRepository` | 仅返回离线 JSON 中的静态切片，无实时路径生成算法 | PARTIAL |
| **动态路径状态** | `GET /api/students/{id}/path-states` | `path_state_service` (`learning_path_states.json`) | 纯状态持久化（LOCKED/AVAILABLE/IN_PROGRESS/COMPLETED） | COMPLETE |
| **微测验题库** | `GET /api/quiz/{knowledge_id}` | `quiz_service` (`quiz_bank.json`) | 服务端权威脱敏（不泄露答案），但**仅覆盖 8/30 考点** | PARTIAL |
| **测验提交与闭环** | `POST /api/quiz/submit` | 权威判题 → 记录事件 → 驱动 BKT → 触发路径重规划 | 极其完整且具备强一致性审计信封 | COMPLETE |
| **BKT 掌握度状态** | `GET /api/students/{id}/knowledge-state/{kid}`<br>`POST /api/learning-state/update` | `bkt_state_service` + `bkt_event_processor` | 纯数学模型，追踪 $P(L)$、作答数、连续正误 | COMPLETE (BACKEND_ONLY) |
| **知识图谱** | `GET /api/students/{id}/knowledge-graph` | `knowledge_graph_service` | 完整输出 30 个考点、42 条前置边、掌握状态及图谱洞察 | COMPLETE |
| **行为事件采集** | `POST /api/events` | `event_service` (`learning_events.jsonl`) | 支持任意学习事件追加日志 | COMPLETE |
| **系统概况** | `GET /api/overview` | `student_service` | 统计学生数、路径数、报告数 | COMPLETE (BACKEND_ONLY) |
| **AI Companion 网关** | `POST /api/ai/companion` | `gateway.api` (独立应用) | 具备 G1~G4 完整安全防御与审计 | PARTIAL_INTEGRATION |

---

## 6. Frontend Capability Inventory (前端能力盘点)

| 前端模块 / 模型 | 对应源码文件 | 职责与能力 | 交互成熟度 |
|---|---|---|---|
| **统一路由核心** | `router.ts` | 角色/Tab 解析、状态机迁移、保留学生上下文 | 极高 (纯 TypeScript，0 外部依赖) |
| **焦点仲裁引擎** | `taskFocusModel.ts` | 动态仲裁 `IN_PROGRESS` > `AVAILABLE`，计算跃迁指标与下一步行动 | 极高 (包含完整单元测试) |
| **自适应解释模型** | `adaptiveLearningModel.ts` | 将 BKT 浮点数与重规划枚举转化为四层教学法解释文本 | 极高 (无技术黑话，面向大学生) |
| **微测验状态机** | `quizModel.ts` | 答题耗时毫秒级打点、防重复提交、结算统计 | 极高 |
| **知识图谱可视化** | `KnowledgeGraph.tsx` | 基于 `@xyflow/react` 渲染拓扑，支持状态高亮、搜索过滤、右侧抽屉 | 极高 |
| **AI 伴学服务管道** | `aiCompanionService.ts` | 白名单投影 → 超时控制 → 事实硬校验 → 确定性降级 | 极高，但受限于后端端口未集成 |
| **用户身份与目标表单** | 无 | 无登录注册、无目标设定交互 | **MISSING** |
| **知识讲义 / 概念卡片** | 无 | 无学习材料载体 | **MISSING** |

---

## 7. Feature Inventory (产品功能矩阵全景表)

| Feature (功能项) | Backend | Frontend | User Accessible | Product Value | Status |
|---|---|---|---|---|---|
| **学生注册 / 登录体系** | ❌ (硬编码S001~S005) | ❌ (Header下拉框) | ❌ (无独立账户) | High | MISSING |
| **学习目标设定 / 调整** | ❌ (无修改API) | ❌ (只读文本展示) | ❌ (无法配置) | High | MISSING |
| **学情诊断 (前测摸底)** | ⚠️ (离线静态报告) | ⚠️ (Profile只读图表) | ⚠️ (仅看静态数据) | High | PARTIAL |
| **BKT 认知掌握度建模** | ✅ (Domain/BKT数学库) | ⚠️ (测验结算展示) | ⚠️ (无独立历史视图) | High | PARTIAL |
| **自适应学习路径规划** | ⚠️ (静态离线JSON) | ✅ (时序卡片/焦点卡) | ⚠️ (仅支持5个Persona) | Critical | PARTIAL |
| **学习资源 / 讲义推荐** | ❌ (无资源实体) | ❌ (无展示组件) | ❌ (直接做题) | Critical | MISSING |
| **推荐原因多维解释** | ✅ (规则与元数据) | ✅ (四层教学法抽屉) | ✅ (一键展开) | High | COMPLETE |
| **微测验练习突破** | ⚠️ (仅8/30考点有题) | ✅ (BottomSheet抽屉) | ⚠️ (仅S001能全通) | Critical | BROKEN |
| **学习结果与状态反馈** | ✅ (QuizSubmitResponse)| ✅ (正误/用时/阶段) | ✅ (即时结算) | Critical | COMPLETE |
| **掌握度跃迁与路径重规划**| ✅ (evaluate_and_replan)| ✅ (实时解锁与高亮) | ✅ (实时响应) | Critical | COMPLETE |
| **AI 伴学导师** | ✅ (Gateway/Assistant) | ✅ (AIAssistant对话) | ⚠️ (端口未接通走兜底) | Medium | PARTIAL_INTEGRATION |
| **教师学情决策驾驶舱** | ⚠️ (基础数据聚合) | ❌ (3张占位卡片) | ❌ (无实质功能) | Medium | DEMO_ONLY |
| **AI 评测基础设施 (G1~G4)**| ✅ (网关/守卫/漂移监控)| ❌ (运维级设施) | ❌ (后台保障) | Infrastructure | COMPLETE |

---

## 8. Productization Gap Matrix (产品化体验缺口矩阵)

### 🔴 P0 — 阻止用户完成核心学习闭环 (Showstoppers)
1. **P0-1: 缺少新用户初始化与学习目标设定**
   - 现状：首次进入直接成为“S001 张伟”，学生无法表达自己的年级、学科方向和目标（如“零基础入门”、“期末突击”、“考研刷题”）。
   - 影响：用户没有心理归属感，无法验证“为我量身定制”。
2. **P0-2: 题库覆盖率极度匮乏导致闭环中断**
   - 现状：30 个知识点仅 8 个有题目（共 13 题）。除 S001 外，其余 4 人路径第 1 步或后续节点即刻报红中断；S001 走完 K11 后解锁 K12 同样中断。
   - 影响：80% 的使用场景处于不可用崩溃状态。
3. **P0-3: “只测不学”违背认知规律**
   - 现状：核心任务卡唯一操作是“开始微测验”，完全没有考点定义、关键公式或典型例题的阅读载体。薄弱学生不会做只能乱蒙。
   - 影响：严重脱离真实学习场景，形成“测试逼退”体验。
4. **P0-4: 缺乏动态自适应路径生成器 (Dynamic Path Synthesizer)**
   - 现状：路径全靠离线写死的 `learning_paths.json`。新学生或已有学生达到不同目标时，系统无法从知识图谱拓扑动态生成新路径。
   - 影响：无法真正支撑个性化自适应学习。

### 🟡 P1 — 严重影响产品体验与可信度 (Friction & Quality)
1. **P1-1: AI 网关路由未挂载到主服务**
   - 现状：`gateway.api:app` 独立存在，未被 `app/main.py` 挂载，前端调用 `/api/ai/companion` 遭遇 404，永远只能返回本地硬编码兜底。
   - 影响：耗时研发的高性能 AI Gateway 和真实模型伴学能力在前端完全沉睡。
2. **P1-2: 知识图谱缺乏与学习路径的航线视觉高亮**
   - 现状：图谱是一个孤立的探索视图，未直观高亮“你当前处于哪一步”、“下一站去哪里”。
   - 影响：图谱与任务割裂，学生缺乏大局观认知。
3. **P1-3: 掌握度缺乏时间序列历史趋势展现**
   - 现状：BKT 状态只在做题后闪现一次对比，学情档案里只有静态雷达图，缺乏“近 7 天认知演进曲线”。
   - 影响：学生无法看到自己付出的努力所带来的累积成就感。
4. **P1-4: 教师驾驶舱处于纯虚构占位状态**
   - 现状：教师切换过去只有 3 个空白占位卡。
   - 影响：无法支撑国创汇报中关于“教学协同与闭环干预”的完整陈述。

### 🟢 P2 — 明显提升产品商业与使用价值 (Value Enhancers)
1. **P2-1: 错题本与弱点专项复习库**：自动沉淀 QUESTION_ATTEMPT 中的错误记录，一键再次巩固。
2. **P2-2: 知识点精要卡片 (Concept Micro-Card)**：1 分钟图文或思维导图速览。
3. **P2-3: 学习成效海报与学情总结卡片导出**：供学生保存分享或期末打印。

### ⚪ P3 — 后续演进增强 (Future Backlog)
1. **P3-1: 跨学科扩展支撑**：支持导入其他学科（如计算机网络、微积分）的知识图谱与题库。
2. **P3-2: 班级匿名分位数对比**：让学生了解自己在班级中的大概位置。

---

## 9. Current Learning Loop Analysis (现有闭环各环节判定)

```text
① 用户进入       [PARTIAL]  硬编码 Persona，无新用户入口
   ↓
② 学习目标       [MISSING]  静态文本展示，无输入与配置
   ↓
③ 学情诊断       [PARTIAL]  离线生成报告，无新用户前测
   ↓
④ 路径规划       [PARTIAL]  依赖静态 JSON 预置切片，非图谱动态合成
   ↓
⑤ 推荐解释       [COMPLETE] 四层教学法展开（Stage, Prereq, Goal, Pedagogy）
   ↓
⑥ 学习资源       [MISSING]  零讲义、零微课、零概念卡，直接跳过
   ↓
⑦ 测验练习       [BROKEN]   仅覆盖 8/30 考点，22 个考点报错中断
   ↓
⑧ 答题反馈       [COMPLETE] 服务端判题，回传正误与解析
   ↓
⑨ 状态更新       [COMPLETE] BKT 掌握度动态演进与百分比计算
   ↓
⑩ 路径重规划     [COMPLETE] 1-hop 局部动态拓扑计算与解锁审计
   ↓
⑪ 下一步流转     [PARTIAL]  下一考点若无题则立刻崩溃
```

---

## 10. Proposed MVP Learning Loop (提议第一版核心闭环)

专为**“完全陌生的大学生在 10 分钟内完成一次闭环”**量身定制的 7 步敏捷流转闭环：

```text
┌─────────────────────────────────────────────────────────────┐
│              學海智導 10 分鐘沉浸式 MVP 學習閉環             │
└─────────────────────────────────────────────────────────────┘

  ① [轻量目标确立] (30 秒)
     - 选择学科：“微观经济学”
     - 选择当前学习模式：【期末突击】/【基础补弱】/【查漏补缺】
     - 确立核心目标考点范围（如：导论、弹性理论、供求均衡）
             ↓
  ② [极速前测诊断] (2 分钟)
     - 系统自动从目标知识子图生成 3 道代表性诊断题
     - 答完即刻计算初始 BKT 掌握度与当前薄弱点
             ↓
  ③ [生成专属学习路径] (即时)
     - 基于拓扑依赖与弱点优先算法，动态生成 3 个按序排列的攻坚考点
     - 明确标识：第 1 考点 IN_PROGRESS，后继考点 LOCKED
             ↓
  ④ [今日焦点任务 + 1 分钟概念微卡] (1 分钟)
     - 聚焦第 1 个考点（如 K08 需求价格弹性）
     - 查看“为什么推荐这个考点”
     - 点击【知识精要】，用 1 分钟速览核心定义、计算公式与易错警示
             ↓
  ⑤ [靶向微测验突破] (3 分钟)
     - 完成 2 道精选微测验（如基础题 + 计算题）
     - 查看即时解析与耗时分析
             ↓
  ⑥ [掌握度跃迁与路径解锁] (30 秒)
     - 目睹掌握度从 40% 跨越至 82%（阶段变更为“已掌握”）
     - 路径重规划即刻生效：第 2 个后继考点（如 K09）动态解锁变亮
             ↓
  ⑦ [下一步行动或 AI 答疑] (2 分钟)
     - 选项 A：一键顺延进入刚解锁的考点 K09
     - 选项 B：向 AI 导师发问巩固疑问，获得经过 G1 校验的合规辅导
```

---

## 11. Proposed Information Architecture (提议产品信息架构)

```text
学海智导 (Xuehai Zhidao)
│
├── [公共体验层]
│   ├── 新用户极速 Onboarding 模态弹窗 (免注册体验模式 / 输入昵称)
│   ├── 3 题极速学情摸底前测
│   └── 学习模式与目标配置器
│
├── [学生工作台] (移动端优先 4-Tab)
│   │
│   ├── 1. 今日任务 (/student/tasks) —— 【核心行动中心】
│   │   ├── 学习目标与今日进度条
│   │   ├── 今日重点攻坚卡 (Current Focus)
│   │   │   ├── 为什么先学它（可折叠解释）
│   │   │   ├── 【知识速览】(Concept Micro-Card 弹窗)
│   │   │   └── 【开始微测验】(BottomSheet 测验流)
│   │   └── 自适应路径时序时间轴 (Learning Path Timeline)
│   │
│   ├── 2. 知识图谱 (/student/graph) —— 【宏观认知导航】
│   │   ├── 30 考点拓扑网络 (React Flow)
│   │   ├── 学习路径当前航线动态脉冲连线
│   │   ├── 状态筛选器 (全部 / 已掌握 / 学习中 / 已解锁 / 未解锁)
│   │   └── 考点详情抽屉 (支持查看先修依赖并直接启动测验)
│   │
│   ├── 3. 学情档案 (/student/profile) —— 【成长成效沉淀】
│   │   ├── 核心指标看板 (总掌握度、累计刷题、平均耗时)
│   │   ├── 认知能力多维雷达图
│   │   ├── BKT 掌握度演进历史折线图 (近 7 次/近 7 天趋势)
│   │   └── 薄弱知识点清单与先修穿透
│   │
│   └── 4. AI 伴学导师 (/student/assistant) —— 【智能答疑辅导】
│       ├── 苏格拉底式启发对话界面
│       ├── 学情强关联考点卡片
│       └── 基于真实 Gateway 运行时的合规无幻觉辅导
│
└── [教师驾驶舱] (/teacher) —— 【教学协同中枢】
    ├── 班级认知掌握度宏观分布看板
    ├── 典型共性卡点排行与高危预警名单
    └── 针对性干预方案一键推送
```

---

## 12. P0 / P1 / P2 / P3 Roadmap (分级实施演进路线)

```text
Phase 4 产品化里程碑
│
├── Sprint 8-A: 【闭环畅通 (P0)】
│   ├── 补齐全量 30 考点基础题库（每个考点至少 2 题，总数达到 60+ 题）
│   ├── 增加轻量化 Onboarding 与学习目标选择弹窗
│   ├── 为 30 考点增加 1 分钟“知识速览微卡”
│   └── 挂载 Gateway 路由至主服务，打通真实 AI 伴学链路
│
├── Sprint 8-B: 【体验跃升 (P1)】
│   ├── 动态路径生成器：根据选定目标从图谱实时拓扑剪枝生成 3~5 步路径
│   ├── 知识图谱与当前学习路径动态航线高亮联动
│   ├── 学情档案增加历史掌握度成长演进折线图
│   └── 实现教师驾驶舱基础班级聚合看板
│
├── Sprint 8-C: 【价值深化 (P2)】
│   ├── 错题本与薄弱考点二轮靶向强化
│   ├── 学习成就海报生成与导出
│   └── 移动端触控细节优化与全屏沉浸式测验
│
└── Sprint 8-D: 【长效扩展 (P3)】
    ├── 跨学科多图谱模板机制
    └── 班级匿名排位与学习周报
```

---

## 13. Web Productization Strategy (Web 产品化关键策略)

1. **“体验即合规”原则**：所有前端交互（包括快捷提示、AI 对话推荐、路径跳转）严格遵守 G1 策略门禁，不为了追求所谓的“AI 自由度”而允许越权或幻觉。
2. **轻量化原则 (Zero Heavy Framework)**：保持现有 Vite + React 19 + Tailwind 技术栈，不引入复杂的重型前端状态库或庞大 UI 套件。
3. **“先学后测”闭环设计**：每个考点在微测验前均提供 100~200 字的核心概念微卡，确保基础薄弱学生能够“看懂概念 → 做对题目 → 提升掌握度 → 体验成就感”。
4. **统一数据持久化策略**：前端所有更新继续通过后端规范 API 进行原子落地，杜绝纯前端 mock 假刷新。

---

## 14. Future Mobile Strategy (面向未来的移动端战略)

虽然本阶段明确**不开发 App、不引入 React Native**，但当前 Web 架构已具备极佳的原生移植性：
1. **视图与逻辑解耦**：前端核心模型（`taskFocusModel.ts`, `adaptiveLearningModel.ts`, `quizModel.ts`, `router.ts`）全为 100% 纯 TypeScript 编写，无任何 DOM、window 或 document 依赖。未来迁移至 React Native + Expo 时可直接 1:1 复用；
2. **纯 JSON API 交互契约**：所有后端接口均采用标准 HTTP/JSON 契约，移动端只需引入标准网络客户端即可直接调用；
3. **移动优先的 UI 布局规范**：现有 UI 已具备 `MobileContainer`、`BottomNav`、`BottomSheet`，桌面端与移动端在同一个代码库内以 Tailwind 断点优雅适配，未来向移动端原生视图迁移成本极低。

---

## 15. Architecture Boundary Recommendations (架构边界建议)

1. **主后端路由集成边界**：
   - 建议在 `app/main.py` 中以 `app.include_router(gateway.api.router, prefix="/api")` 或挂载子应用方式接入 AI 网关，使前端对 `/api/ai/companion` 的请求能够在单端口单服务下顺畅工作，消除割裂。
2. **业务核心冻结边界**：
   - `app/domain/bkt/` 数学公式不可篡改；
   - `app/domain/path_replanning/` 5 组合法决策矩阵与四位定点序列化不可篡改；
   - `gateway/evaluation/` G1 策略/事实门禁与 G4 守卫不可篡改。
3. **数据管理边界**：
   - 将现有只读题库从 13 题静态补全为 30 考点全覆盖的 60 题基线；
   - 保持只读种子与运行时动态隔离原则。

---

## 16. Risks (核心风险预警)

1. **题库断裂风险 (当前已爆发)**：若不在第一优先级补齐 30 考点基础题库，任何产品化工作都会因为 404/空数据而前功尽弃；
2. **静态假象风险**：如果继续依赖写死的 S001~S005 JSON，产品在答辩或用户体验时会被一眼识别为“预录 Demo”而非“真正系统”；
3. **越权决策风险**：在增加 AI 对话和推荐功能时，必须严格捍卫 `allow_production_decision = False`，绝不能让大模型直接修改 BKT 或路径状态。

---

## 17. What NOT to Build (绝对不做的不必要功能清单 - YAGNI)

在 Phase 4 期间，坚决抵制以下偏离核心学习闭环的功能：
- ❌ **复杂社交体系**：不建好友列表、不建私聊、不建班级群聊；
- ❌ **社区与论坛**：不建问答社区、不建讨论版块；
- ❌ **游戏化宠物与积分商城**：不搞签到送金币、不养虚拟宠物；
- ❌ **商业变现与复杂权限**：不搞 VIP 会员卡、不搞收费墙；
- ❌ **多 Agent 自由聊天群**：不引入无拘无束的闲聊大模型，坚守严肃的学情伴学边界；
- ❌ **重型本地 App 打包**：暂不启动 Expo / React Native 工程，集中火力打通 Web 闭环。

---

## 18. Recommended Phase 4 Sprint Breakdown (Phase 4 迭代规划拆解)

| Sprint | 核心目标 | 交付物 | 关键验收指标 |
|---|---|---|---|
| **Sprint 8-A**<br>(基础闭环救生) | 消除阻断缺口，确保任一考点均可学习与测试 | 1. 30 考点全覆盖题库 (每考点 $\ge 2$ 题)<br>2. 30 考点概念微卡<br>3. Gateway 路由挂载集成<br>4. 新用户初始目标选择模态窗 | 30 个考点全部可启动微测验，0 次空题库报错；AI 伴学真实响应 |
| **Sprint 8-B**<br>(动态路径与图谱) | 摆脱写死 Persona，实现真实自适应 | 1. 基于知识图谱的动态路径生成算法<br>2. 3 题极速前测摸底流程<br>3. 知识图谱航线高亮联动 | 任意新选择的目标均能动态生成有效路径；图谱直观反映航线 |
| **Sprint 8-C**<br>(成效沉淀与教师端) | 提升产品质感与教师闭环 | 1. 学情成长历史曲线图表<br>2. 错题重练模块<br>3. 教师驾驶舱宏观看板落地 | 学生可查阅连续 7 次掌握度轨迹；教师端展示真实班级聚合指标 |
| **Sprint 8-D**<br>(全真演练与验收) | 10 分钟陌生学生真实体验验收 | 1. 端到端自动化冒烟测试套件<br>2. 性能与移动端触控优化<br>3. 最终产品文档与使用手册 | 真实陌生人在 10 分钟内无障碍完成闭环，全系统质量门禁 100% PASS |

---

## 19. Acceptance Criteria (Phase 4 验收标准)

一个合格的 Phase 4 最终版本必须满足：
1. **零阻断测试**：在知识图谱或学习路径中随机点选任意知识点，启动微测验的成功率必须为 **100%**（绝无“暂无可用题目”弹窗）；
2. **10 分钟闭环成立**：以全新学生身份进入系统，从设定目标、前测、获得路径、看概念卡、测验突破到掌握度跃迁解锁，全程在 **10 分钟内流畅完成**；
3. **AI Gateway 真实生效**：AI 伴学助手返回经过 G1 校验的合规结构化解答，网络状态码为 200，绝不因 404 降级；
4. **核心安全红线坚挺**：`allow_production_decision = False` 维持不变，G1 Supremacy 绝对否决权维持不变，核心业务代码零篡改；
5. **质量门禁 100% PASS**：TypeScript 0 错误、前端测试全绿、后端架构与回归测试全绿、Quality Gate 5/5 全绿。

---

## 20. Files / Components Reviewed (审计覆盖源码清单)

### 前端组件与模型
- `frontend/src/router.ts`: 纯函数路由解析器与状态机
- `frontend/src/App.tsx`: 应用主控制器、异步竞态隔离与刷新管线
- `frontend/src/api.ts`: API 封装与网络拦截层
- `frontend/src/layouts/StudentLayout.tsx`: 学生端多 Tab 布局与测验抽屉提升
- `frontend/src/layouts/TeacherLayout.tsx`: 教师端驾驶舱骨架与占位模块
- `frontend/src/components/Header.tsx`: 顶部学生切换与服务状态指示器
- `frontend/src/components/HeroBanner.tsx`: 目标与策略问候展示
- `frontend/src/components/KnowledgeGraph.tsx`: React Flow 知识网络拓扑与抽屉联动
- `frontend/src/components/LearningPath.tsx`: 自适应时序时间轴卡片
- `frontend/src/components/AIAssistant.tsx`: AI 伴学对话窗口与考点推荐卡
- `frontend/src/components/student/CurrentFocusCard.tsx`: 今日焦点任务仲裁卡
- `frontend/src/components/student/KnowledgePointQuiz.tsx`: 交互式微测验核心控制器
- `frontend/src/components/student/taskFocusModel.ts`: 任务仲裁与跃迁计算纯模型
- `frontend/src/components/student/adaptiveLearningModel.ts`: 四层教学法解释模型
- `frontend/src/components/student/quizModel.ts`: 微测验状态机与指标测算
- `frontend/src/components/student/aiCompanionService.ts`: AI 伴学安全管道
- `frontend/src/components/student/aiGatewayProvider.ts`: AI 网关前端适配器

### 后端服务与路由
- `app/main.py`: FastAPI 应用入口与 8 大路由挂载
- `app/api/routers/students.py`: 学生画像与看板聚合路由
- `app/api/routers/path.py`: 学习路径与执行状态路由
- `app/api/routers/quiz.py`: 分知识点测验与判题提交路由
- `app/api/routers/learning_state.py`: BKT 掌握度认知状态路由
- `app/api/routers/assistant.py`: 学习助手问答与问候路由
- `app/api/routers/knowledge_graph.py`: 知识图谱拓扑路由
- `app/api/routers/events.py`: 学习行为事件采集路由
- `app/api/routers/system.py`: 健康检查与概况路由
- `app/services/quiz_service.py`: 测验与闭环重规划联动应用服务
- `app/services/path_service.py`: 路径查询应用服务
- `app/services/student_service.py`: 学生看板聚合应用服务
- `app/services/knowledge_graph_service.py`: 知识图谱应用服务
- `app/infrastructure/persistence/profile_repository.py`: 档案仓储与内存缓存
- `gateway/api.py`: 独立 AI Gateway 应用与故障分类器
- `gateway/adapter.py`: LLM 提供商适配层
- `gateway/evaluation/judge/runtime.py`: Judge 运行时策略

### 数据与种子文件
- `data/seeds/quiz_bank.json`: 13 题脱敏微测验题库 (仅覆盖 8 考点)
- `data/seeds/knowledge_graph.json`: 30 考点 / 42 依赖边标准知识图谱
- `data/seeds/learning_paths.json`: 5 名预置学生静态推荐路径
- `data/seeds/student_profiles.json`: 5 名学生基础画像
- `data/seeds/student_reports.json`: 5 名学生离线分析报告
- `data/runtime/learning_path_states.json`: 动态路径状态存储
- `data/runtime/bkt_states.json`: 动态 BKT 掌握度状态存储
- `data/runtime/learning_events.jsonl`: 学习行为事件日志
