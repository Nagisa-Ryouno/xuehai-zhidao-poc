# Phase 5 / Sprint 9-D 封版交付报告与演练指南 (Walkthrough)

**项目名称**：学海智导 (Xuehai Zhidao) — AI驱动的大学生个性化学习指导平台  
**当前阶段**：Phase 5 — AI Companion & Intelligent Study Assistance  
**Sprint 周期**：Sprint 9-D — 学习效果验证与资源自适应反馈 (Learning Effectiveness & Adaptive Resource Feedback)  
**交付时间**：2026-09-15  
**基线提交**：`3039fd3` (Sprint 9-C 封版基线 `feat(learning): add resource-aware adaptive learning`)  

---

## 一、Sprint 9-D 交付目标与核心使命

在 Sprint 9-C 中，系统构建了覆盖全图谱 30 考点（130 项原生资源）的「学习资源中心」与确定性推荐引擎。然而，系统过去无法回答一个至关重要的教育学问题：

> **「学生使用一个学习资源之后，到底学会了没有？掌握度是否真的发生了变化？」**

Sprint 9-D 的目标不是单纯继续增加资源数量，而是**打通从“资源使用”到“学习成效验证”的闭环反馈系统**：

```text
推荐学习资源
     ↓
启动学习会话 (LearningSession, 服务端记录 initial_mastery 快照)
     ↓
研读材料 / 概念微卡 / 例题精析
     ↓
完成靶向微练 / 考点微测验 (真实作答驱动权威 BKT 状态跃迁)
     ↓
点击完成本次学习并检验掌握度
     ↓
服务端权威重新读取 BKT 掌握度，计算掌握度净变化 ΔP(L)
     ↓
生成 4 档效果判定信号与人本导师反馈语 (时间关联叙事，零黑话)
     ↓
呈现核心完成卡片，引导下一步行动 (再练一道巩固 / 开启新一轮学习)
```

---

## 二、双层架构与闭环流转

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   学生端 (Student UI)                                   │
│   今日任务 (Tasks) / 学习资源 (Resources) / 知识图谱 (Graph) / 学情档案 (Profile) / AI伴学     │
└───────────────────────────┬────────────────────────────────────────────┬───────────────┘
                            │ (启动会话 / 提交完成 / 查询效果)               │ (材料上下文提问)
                            ▼                                            ▼
┌───────────────────────────────────────────────────────┐ ┌─────────────────────────────┐
│       学习效果与会话服务 (Effectiveness & Sessions)      │ │   AI伴学层 (Companion)     │
├───────────────────────────────────────────────────────┤ ├─────────────────────────────┤
│ • 学习会话管理 (LearningSessionService, atomic I/O)    │ │ • Grounded with real        │
│ • 初始掌握度服务端权威快照 (禁止前端篡改)                  │ │   resource_context          │
│ • 掌握度净变化计算 ΔP(L) = final - initial            │ │ • allow_production_decision │
│ • 4 档确定性效果判定 (FeedbackService)                 │ │   = False (只读伴学)        │
│ • 人本导师时间关联叙事反馈 (零工程技术黑话)                │ └──────────────┬──────────────┘
│ • 独立遥测日志 (data/resource_effectiveness_events)   │                │
└───────────────────────────┬───────────────────────────┘                │
                            │ (只读读取掌握度快照)                         │ (只读读取掌握度)
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
2. **权威 BKT 单一事实源与禁止伪造掌握度**：
   - 初始掌握度 `initial_mastery` 必须由服务端根据当前学生在底层 `bkt_states.json` 的权威状态生成快照，禁止信任前端传入的值。
   - 学习结束时的 `final_mastery` 同样由服务端重新读取 BKT 状态，计算真实的掌握度净变化 $\Delta P(L)$。
3. **遥测日志物理隔离 (Telemetry Isolation)**：
   - 学习会话的启动与效果验证事件严格追加落盘至 `data/resource_effectiveness_events.jsonl`，严禁写入 `data/learning_events.jsonl`，严禁直接修改 `data/bkt_states.json`。
4. **人本导师叙事与零技术黑话 (No Jargon)**：
   - 评语严格采用**时间关联**叙事（“完成本次学习后，掌握情况从 A% 变为 B%”），严禁建立虚假因果承诺。
   - 界面与反馈中杜绝出现 `BKT`、`Bayesian`、`mastery_probability`、`PathState` 等底层工程黑话。
5. **多学生上下文严格隔离**：
   - 会话操作必须校验学生身份，跨学生访问或完成他人会话严格抛出 HTTP 403 Forbidden。
   - 前端切换学生时，立即重置活跃会话与完成卡片，杜绝上下文残留污染。
6. **移动端自适应与零横向滚动条**：
   - 完美适配 375px 窄视口，导航栏与下拉选择器响应式收缩，无水平溢出滚动条。

---

## 四、4 档学习效果分级判定矩阵

| 效果分级 | 判定条件 | 界面标签 | 人本导师反馈主旨 (No Jargon) |
| :--- | :--- | :--- | :--- |
| **STRONG_PROGRESS** | $\Delta P(L) \ge +0.10$ | 显著提升 | 本次学习收效显著！对该考点核心规律的理解明显加深，答题准确度与思路清晰度显著提升。 |
| **MEANINGFUL_PROGRESS** | $+0.02 \le \Delta P(L) < +0.10$ | 稳步提升 | 本次学习稳扎稳打！关键概念与解题要点得到有效巩固，掌握情况在持续向好发展。 |
| **STABLE** | $-0.02 \le \Delta P(L) < +0.02$ | 保持稳定 | 当前掌握情况保持平稳。对于概念内涵已具备清晰认知，可结合更深入的生活例题加深体悟。 |
| **NEEDS_MORE_SUPPORT** | $\Delta P(L) < -0.02$ | 遇到阻碍 | 本次学习中似乎遇到了一些困惑或易错陷阱。别灰心，建议放慢节奏，先回顾基础概念卡片。 |

---

## 五、前后端全栈交付资产清单

### 5.1 后端服务模块 (`gateway/learning/effectiveness/`)
- `models.py`：定义 `SessionStatus`、`EffectivenessStatus` 枚举、`LearningSession` 实体、`LearningEffectiveness`、`ResourceEffectivenessSignal`、`KnowledgeEffectivenessResponse`、`SessionCompleteResponse`。
- `events.py`：线程安全的追加写学习效果遥测日志层（`data/resource_effectiveness_events.jsonl`）。
- `feedback.py`：`ResourceFeedbackService` 4 档确定性效果映射引擎，纯时间关联叙事，杜绝技术黑话。
- `sessions.py`：`LearningSessionService` 会话持久化与状态机流转管理，服务端原子落盘与快照校验。
- `analyzer.py`：`ResourceEffectivenessAnalyzer` 只读效果分析器。
- `gateway/api.py`：挂载 4 个核心 API 端点：
  - `POST /api/learning/sessions`（创建学习会话并快照初始掌握度）
  - `GET /api/learning/sessions/{session_id}`（获取学习会话详情）
  - `POST /api/learning/sessions/{session_id}/complete`（完成会话并生成效果评估）
  - `GET /api/learning/resources/{knowledge_id}/effectiveness`（查询考点学习效果与历史表现）
- `gateway/learning/companion/models.py` & `service.py`：支持携带真实 `resource_id` 与 `resource_context` 进行定向提问。

### 5.2 前端组件与交互升级 (`frontend/src/`)
- `types.ts` & `api.ts`：导出完整的 Sprint 9-D 数据契约与 API 调用函数。
- `components/student/ResourceHub.tsx`：
  - 自适应推荐横幅：新增「开始本次学习」核心行动入口。
  - 4 步闭环时序看板：考点精要 ➔ 典型例题 ➔ 靶向微练 ➔ 效果检查。
  - 核心完成结果卡：学习前掌握度 ➔ 学习后掌握度、净变化 delta 徽章、已完成步骤清单、人本导师反馈语、下一步行动按钮。
  - 多学生上下文隔离：学生或考点切换时自动清理状态。
- `components/AIAssistant.tsx` & `layouts/StudentLayout.tsx`：材料精读直通 AI 伴学，并在输入框显式提示当前材料上下文。
- `components/Header.tsx` & `components/RoleSwitcher.tsx` & `index.css`：移动端（375px）完美响应式排版，彻底消除横向溢出滚动条。

---

## 六、质量门禁与全量测试验证

### 6.1 全量自动化测试套件
1. **后端专用单元与集成测试**：
   - `pytest gateway/tests/test_sprint9d_learning_effectiveness.py`：**28/28 PASSED**。
2. **后端全量回归测试**：
   - `pytest gateway/tests/ -q`：**398/398 PASSED**（覆盖从 Phase 2 到 Sprint 9-D 所有功能）。
3. **前端专用契约测试**：
   - `frontend/test/sprint9d_learning_effectiveness.test.ts`：**12/12 PASSED**。
4. **前端全量契约测试**：
   - `npm test --prefix frontend`：**234/234 PASSED**（50 suites，0 errors）。
5. **前端生产构建检验**：
   - `npm run build --prefix frontend`：TypeScript 类型检查 0 错误，Vite 构建成功。

### 6.2 质量门禁执行结果
- `python scripts/sprint9d_quality_gate.py`：**12/12 CHECKS GREEN**。
- `python scripts/sprint9c_quality_gate.py`：**12/12 CHECKS GREEN**。
- `python scripts/sprint9b_quality_gate.py`：**12/12 CHECKS GREEN**。
- `python scripts/sprint9a_quality_gate.py`：**10/10 CHECKS GREEN**。
- `python scripts/sprint8d_quality_gate.py`：**10/10 CHECKS GREEN**。
- `python scripts/sprint8c_quality_gate.py`：**10/10 CHECKS GREEN**。
- `python scripts/quality_gate.py`：**5/5 GATES GREEN**。

### 6.3 Playwright 真实浏览器端到端 UAT 验证
脚本 `scripts/uat_sprint9d_browser.py` 自动化执行并通过全部 12 个用户真实旅程场景：

| 编号 | 场景标题 | 验证要点 | 截图留存 |
| :--- | :--- | :--- | :--- |
| **A** | 访问学习资源中心 | 「开始本次学习」核心行动入口与推荐步骤 | `artifacts/uat_screenshots/sprint9d_01_resource_hub_start_session_button.png` |
| **B** | 点击「开始本次学习」 | 学习会话激活与 4 步时序微进度看板 | `artifacts/uat_screenshots/sprint9d_02_active_session_stepper.png` |
| **C** | 执行步骤 1「考点微卡精要」 | 速览微卡调起与核心直观呈现 | `artifacts/uat_screenshots/sprint9d_03_session_step1_concept_card.png` |
| **D** | 执行步骤 2「典型例题深度剖析」| 真实生活与商业情境案例精读 | `artifacts/uat_screenshots/sprint9d_04_session_step2_example_reader.png` |
| **E** | 在例题中「向 AI 伴学提问」 | 携带真实材料上下文直通 AI 辅导 | `artifacts/uat_screenshots/sprint9d_05_companion_with_resource_context.png` |
| **F** | 点击「完成本次学习并检验掌握度」| 触发服务端权威重读与核心结果卡呈现 | `artifacts/uat_screenshots/sprint9d_06_core_completion_card_effectiveness.png` |
| **G** | 检查已完成步骤清单 | 概念卡片、典型例题、微测验验证清晰展示 | `artifacts/uat_screenshots/sprint9d_07_completed_checklist.png` |
| **H** | 检查人本导师评语 | 严格时间关联叙事，零底层技术黑话 | `artifacts/uat_screenshots/sprint9d_08_tutor_feedback_narrative.png` |
| **I** | 点击「再练一道巩固」 | 顺畅调起考点靶向微练 | `artifacts/uat_screenshots/sprint9d_09_next_action_quiz_start.png` |
| **J** | 切换考点 (K01 ➔ K07) | 会话重置与自适应推荐更新 | `artifacts/uat_screenshots/sprint9d_10_knowledge_switch_reset.png` |
| **K** | 切换学生 (S001 ➔ S002) | 学习会话与效果反馈多学生上下文严格隔离 | `artifacts/uat_screenshots/sprint9d_11_student_isolation_switch.png` |
| **L** | 移动端视口 (375x812) 人体工学 | 自适应布局、时序微看板与零横向滚动条 | `artifacts/uat_screenshots/sprint9d_12_mobile_effectiveness_card.png` |

---

## 七、演练与验证操作指南

### 1. 启动服务
确保已安装环境依赖，分别启动后端与前端服务：
```bash
# 终端 1: 启动后端网关服务
python -m uvicorn gateway.api:app --host 127.0.0.1 --port 8011

# 终端 2: 启动前端开发服务器
npm run dev --prefix frontend
```

### 2. 体验学习闭环
1. 打开浏览器访问 `http://127.0.0.1:5173/student/resources`。
2. 在「自适应学习材料库」顶部点击「开始本次学习」。
3. 观察出现的紫色进行中看板，初始掌握度快照清晰呈现。
4. 依次点击「步骤 1 考点微卡精要」与「步骤 2 典型例题深度剖析」，在例题模态框中点击「向 AI 伴学提问」，体验材料上下文联动。
5. 点击「完成本次学习并检验掌握度」，查看呈现的绿色「核心结果卡」：
   - 学习前掌握度 vs 学习后掌握度对比。
   - 掌握度净变化 delta 徽章。
   - 人本导师评语（时间关联叙事）。
   - 下一步行动引导按钮。
6. 调整浏览器窗口至移动端（375px），验证整体页面无水平滚动条，布局规整舒适。

### 3. 一键运行自动化门禁
```bash
# 运行 Sprint 9-D 专用端到端浏览器 UAT
python scripts/uat_sprint9d_browser.py

# 运行 Sprint 9-D 质量门禁 (12 项严格自检)
python scripts/sprint9d_quality_gate.py
```
