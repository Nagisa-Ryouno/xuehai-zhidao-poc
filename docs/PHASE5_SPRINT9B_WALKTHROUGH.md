# Phase 5 / Sprint 9-B 封版交付报告与演练指南 (Walkthrough)

**项目名称**：学海智导 (Xuehai Zhidao) — AI驱动的大学生个性化学习指导平台  
**当前阶段**：Phase 5 — AI Companion & Intelligent Study Assistance  
**Sprint 周期**：Sprint 9-B — AI 引导学习与学习结果反思闭环 (AI Guided Learning & Learning Reflection)  
**交付时间**：2026-09-12  
**基线提交**：`275e272` (Sprint 9-A 封版基线)  

---

## 一、Sprint 9-B 交付目标与双层闭环架构

Sprint 9-A 成功接入了具备概念精讲、错题剖析、阶段总结和自由探讨的 AI 学习伙伴。但彼时 AI 仍停留在“对话式孤岛”，学生与 AI 讨论后无法直接转化为确定性的学习行动，学习完成后的客观成果也无法被 AI 感知与反思。

**Sprint 9-B 的核心目标**：将 AI 伴学从孤立会话升级为完整的认知闭环：

$$\text{AI 引导辅导} \longrightarrow \text{确定性行动建议} \longrightarrow \text{真实学习与测验} \longrightarrow \text{BKT 权威更新} \longrightarrow \text{AI 读取最新事实} \longrightarrow \text{学习结果反思} \longrightarrow \text{下一步攻坚}$$

形成真正可重复、可验证、确定性主导的 **“理解 → 尝试 → 验证 → 反思 → 再学习”** 闭环。

---

### 1.1 双层架构与单向依赖流

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          学生端 (Student UI)                           │
│   今日任务 (Tasks) / 知识图谱 (Graph) / 学情档案 (Profile) / AI伴学     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
       ┌────────────────────────────┴────────────────────────────┐
       ▼                                                         ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│     底层确定性学习引擎 (权威真实源)      │ │        上层 AI 伴学与引导层 (只读)       │
├───────────────────────────────────────┤ ├───────────────────────────────────────┤
│ • 知识图谱 30 考点拓扑网络 (K01~K30)    │ │ • 4 种辅导模式 (精讲/错题/总结/探讨)   │
│ • BKT 贝叶斯知识追踪模型 (公式锁定)     │ │ • 考点微检验 (Quick Check 30 考点)    │
│ • 动态路径局部重规划引擎 (1-hop 域)     │ │ • 5 种确定性 Guided Actions (Case A~E) │
│ • Append-Only 正式事件 (learning_events)│ │ • 学习结果反思 (Action Reflection)     │
│ • 测验判题与答题落盘 (POST /quiz/submit) │ │ • 伴学辅助日志 (companion_events.jsonl)│
│ • 生产状态权威持久化 (bkt_states.json)  │ │ • allow_production_decision = false   │
└───────────────────────────────────────┘ └───────────────────────────────────────┘
                                ▲                          │
                                └─────── 只读查询事实 ──────┘
```

---

### 1.2 严格遵循的核心不变量与安全红线

1. **只读伴学与零生产状态突变 (Zero Mutation Invariant)**：
   - AI 伴学模块（包括 Quick Check、Guided Actions、Action Result Reflection）**绝对严禁直接修改 BKT 掌握度、路径状态或正式学习事件日志**。
   - 所有响应均硬编码携带 `allow_production_decision = False`。
   - 伴学辅助事件（如 `AI_ACTION_CLICK`、`AI_QUICK_CHECK`）独立持久化至 `data/companion_events.jsonl`，确保 `data/learning_events.jsonl` 严格仅由学生正式学习产生。
2. **冻结目录 0 差异 (Zero Diff)**：
   - 历史架构迁移与测试目录 `app/`、`tests/`、`data/seeds/` 严格保持 0 差异（`git diff --stat HEAD -- app/ tests/ data/seeds/` 严格为空）。
3. **单一事实源与真实掌握度读取 (Single Source of Truth)**：
   - 学习行动反思（Action Reflection）严禁信任前端传入的假造掌握度数值，必须调用系统权威 `AnalyticsService` 与 `BKT` 引擎读取真实计算后的 $P(L)$ 掌握度。
4. **杜绝底层工程技术黑话 (No Jargon)**：
   - 学生端界面与 AI 生成的所有建议、解析、反思文案中，绝对禁止出现任何内部底层术语（如 `BKT`、`Bayesian`、`PathState`、`DynamicPathGenerator`、`EventRepository`、`MutationDomain`、`mastery_probability`）。
5. **离线优先与透明度保障**：
   - 离线状态下透明展示 `离线确定性保障`，不依赖任何第三方网络外部 API。

---

## 二、Sprint 9-B 交付核心功能组件

### 2.1 确定性推荐行动引擎 (DeterministicActionBuilder)

基于学生的真实认知状态与图谱拓扑，覆盖 **Case A ~ Case E** 五大确定性状态映射：

| 场景分支 | 学生认知状态判定条件 | 核心推荐行动 (优先级 1) | 次级推荐行动 (优先级 2) |
| :--- | :--- | :--- | :--- |
| **Case A** | 掌握度薄弱 ($P(L) < 0.60$) | `📖 重新看概念` (`READ_CONCEPT`) | `✏️ 靶向再练一道` (`TARGETED_PRACTICE`) |
| **Case B** | 掌握度巩固中 ($0.60 \le P(L) < 0.80$) | `✏️ 靶向再练一道` (`TARGETED_PRACTICE`) | `📖 重新看概念` (`READ_CONCEPT`) |
| **Case C** | 考点已达标 ($P(L) \ge 0.80$) 且有未掌握后继 | `🚀 挑战下一考点` (`TARGETED_PRACTICE`) | `📊 查看学情进展` (`VIEW_PROGRESS`) |
| **Case D** | 考点已达标且为图谱终点 ($P(L) \ge 0.80$) | `📊 查看学情进展` (`VIEW_PROGRESS`) | `💬 与导师深度探讨` (`CONTINUE_DISCUSSION`) |
| **Case E** | 连续答错 $\ge 2$ 次 (认知受阻) | `📖 重温概念微卡` (`READ_CONCEPT`) | `🔍 错题归因复盘` (`REVIEW_WRONG_ANSWERS`) |

### 2.2 30 考点轻量微检验 (Quick Check)

- **覆盖完备**：覆盖宏微观经济学全图谱 30 个考点（`K01` ~ `K30`），每个考点内置 4 项标准化选项（A/B/C/D）。
- **零生产副作用**：纯启发式教学自测，不写入 BKT，不产生 `QUESTION_ATTEMPT` 事件。
- **即时反馈闭环**：作答后即时展开启发式解析与核心要点，并引导前往微测验进行正式评估。

### 2.3 学习行动成效反思 (Action Reflection)

- **真实增量捕获**：读取正式测验提交后的最新掌握度，计算掌握度增量 $\Delta P(L)$。
- **多阶正向评价**：针对突破 80% 达标标准、稳步巩固中、答错查漏补缺等情境，输出针对性、鼓舞性的专业导师评语。
- **指示器可视化**：展示「行动前掌握度 → 行动后掌握度」进度条与净变化指示器（如 `+18.3%`）。

---

## 三、全自动化测试与质量门禁证据

### 3.1 质量门禁全绿矩阵 (Quality Gates)

| 门禁脚本 | 检查项数 | 执行结果 | 核心断言 |
| :--- | :---: | :---: | :--- |
| `scripts/sprint9b_quality_gate.py` | 12 / 12 | **PASS** | Guided Actions契约、Case A~E矩阵全覆盖、404边界、Quick Check 30考点覆盖与零突变、掌握度真实读取与增量评价、防注入、无黑话、安全元数据硬冻结、伴学日志隔离 |
| `scripts/sprint9a_quality_gate.py` | 10 / 10 | **PASS** | 4大伴学模式、事实溯源、会话滑动窗口、防越狱、零突变快照、无黑话 |
| `scripts/sprint8d_quality_gate.py` | 10 / 10 | **PASS** | 统一真实源、API契约、Append-only日志、无伪造数据、冻结目录0 diff |
| `scripts/sprint8c_quality_gate.py` | 10 / 10 | **PASS** | 学情进展、错题复盘、教师分析、30考点守恒 |
| `scripts/sprint8b_dynamic_path_gate.py` | 12 / 12 | **PASS** | 3题前测、Top-3动态推荐航线、图谱高亮 |
| `scripts/quality_gate.py` | 5 / 5 | **PASS** | TypeScript 0错误、前端210全测通过、Vite生产打包成功、后端回归通过、冻结目录0 diff |

### 3.2 单元与集成测试结果

1. **后端 Sprint 9-B 专属测试 (`gateway/tests/test_sprint9b_guided_learning.py`)**：
   - 20 / 20 测试全部一次性通过（覆盖 Cases A~E、白名单校验、Quick Check 30 考点覆盖与作答、零突变、掌握度读取、多生隔离、伴学日志分离、防注入）。
2. **后端全量回归测试**：
   - `gateway/tests/`：342 个测试全部通过。
   - `tests/`：143 个核心业务与架构迁移测试全部通过。
3. **前端 Sprint 9-B 契约测试 (`frontend/test/sprint9b_guided_learning.test.ts`)**：
   - 11 / 11 测试全部通过（覆盖 5 种行动契约、Quick Check 模型、反思 Delta 计算、无黑话断言、闭环状态机流转）。
4. **前端全量回归与生产构建**：
   - `npm test --prefix frontend`：210 个测试全部通过（37 个测试套件，0 失败）。
   - `npm run typecheck --prefix frontend`：0 TypeScript 错误。
   - `npm run build --prefix frontend`：生产打包耗时 523ms 成功生成 `dist/`。

---

## 四、真实 Chromium 浏览器端到端 UAT 验收报告

- **自动化脚本**：`python scripts/uat_sprint9b_browser.py`
- **数据报告**：`artifacts/uat_results.json`
- **截图凭证**：`artifacts/uat_screenshots/sprint9b_01~12.png`

### 4.1 验收场景矩阵 (Scenarios A ~ L)

| 场景编号 | 场景名称 | 验收核心内容 | 截图凭证 | 验收结论 |
| :---: | :--- | :--- | :--- | :---: |
| **Scenario A** | AI 伴学界面与导师身份 | 访问 `/student/assistant`，验证导师头像、学生专属标识、安全状态与确定性引导行动 | `sprint9b_01_assistant_landing.png` | **PASS** |
| **Scenario B** | 概念精讲与 Guided Actions | 验证概念精讲模式下渲染 `📖 重新看概念` 与 `✏️ 靶向再练一道` 行动卡片 | `sprint9b_02_concept_explain_actions.png` | **PASS** |
| **Scenario C** | 考点微检验组件触发 | 点击顶部「考点微检验」快捷按钮，调出包含 4 项选项的微自测卡片 | `sprint9b_03_quick_check_rendered.png` | **PASS** |
| **Scenario D** | 微检验作答与解析反馈 | 点击 Quick Check 选项作答，即时展开启发式解析与核心要点抽屉 | `sprint9b_04_quick_check_feedback.png` | **PASS** |
| **Scenario E** | 引导行动调起微测验 | 点击 `✏️ 靶向再练一道` Guided Action，弹出底层微测验抽屉 | `sprint9b_05_targeted_practice_quiz_modal.png` | **PASS** |
| **Scenario F** | 测验作答与正式 BKT 更新 | 完成测验选择并提交答案，调用官方判题引擎并完成 BKT 掌握度演进 | `sprint9b_06_quiz_submitted_bkt_updated.png` | **PASS** |
| **Scenario G** | 学习结果反思 Banner | 关闭微测验返回伴学，AI 即时显示反思消息与掌握度 Delta 进度指示条 | `sprint9b_07_action_result_reflection_banner.png` | **PASS** |
| **Scenario H** | 引导行动调起概念微卡 | 点击 `📖 重新看概念` Guided Action，弹出权威概念微卡模态框 | `sprint9b_08_concept_card_modal.png` | **PASS** |
| **Scenario I** | 概念微卡阅读后反思 | 关闭概念微卡，导师记录学习轨迹并给出概念梳理与跟进练习指引 | `sprint9b_09_concept_reflection_feedback.png` | **PASS** |
| **Scenario J** | 错题复盘行动顺畅导航 | 错题剖析模式下点击 `🔍 错题归因复盘`，顺畅导航至学情档案错题标签 | `sprint9b_10_wrong_answers_navigation.png` | **PASS** |
| **Scenario K** | 学生切换物理隔离 | 切换至学生 S002，验证导师专属身份同步更新，会话与上下文完全隔离 | `sprint9b_11_student_switch_isolation.png` | **PASS** |
| **Scenario L** | 安全标签与纯净文案审计 | 审计界面“零生产副作用”标签，验证全局无任何工程底层技术黑话 | `sprint9b_12_safety_offline_invariants.png` | **PASS** |

### 4.2 控制台与页面健康指标

```json
{
  "total_console_errors": 0,
  "total_page_errors": 0,
  "total_failed_requests": 0,
  "security_invariants": {
    "allow_production_decision_is_false": true,
    "zero_console_errors": true,
    "zero_page_errors": true
  }
}
```

---

## 五、演练与验证操作指南 (How to Run)

### 1. 运行质量门禁矩阵
```bash
python scripts/sprint9b_quality_gate.py
python scripts/sprint9a_quality_gate.py
python scripts/sprint8d_quality_gate.py
python scripts/quality_gate.py
```

### 2. 运行自动化全真浏览器 UAT
```bash
python scripts/uat_sprint9b_browser.py
```

### 3. 运行全量单元与回归测试
```bash
# 后端专项与回归
pytest gateway/tests/test_sprint9b_guided_learning.py -v
pytest gateway/tests/ -q
pytest tests/ -q

# 前端契约与类型检查
npm test --prefix frontend
npm run typecheck --prefix frontend
npm run build --prefix frontend
```

### 4. 验证冻结目录守恒
```bash
git diff --stat HEAD -- app/ tests/ data/seeds/
# 严格输出为空 (0 diff)
```

---

## 六、封版交付结论

Phase 5 / Sprint 9-B（AI Guided Learning & Learning Reflection）现已**全量通过所有 12 项质量门禁与 12 个真实 Chromium 浏览器 UAT 验收场景**，所有测试 100% 通过，冻结目录 0 修改，正式达成封版交付标准！
