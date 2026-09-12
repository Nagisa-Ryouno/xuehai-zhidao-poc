# Phase 5 / Sprint 9-A 封版交付报告与演练指南 (Walkthrough)

**项目名称**：学海智导 (Xuehai Zhidao) — AI驱动的大学生个性化学习指导平台  
**当前阶段**：Phase 5 — AI Companion & Intelligent Study Assistance  
**Sprint 周期**：Sprint 9-A — AI 学习伙伴与智能辅学体验  
**交付时间**：2026-09-12  
**基线提交**：`c6d891f` (Phase 4 封版基线)  

---

## 一、Sprint 9-A 交付目标与核心架构

在 Phase 4 已通过全真浏览器 UAT 封版的「确定性自适应学习闭环」基础之上，Sprint 9-A 成功接入了产品级 **AI 学习伙伴 (AI Learning Companion)**，建立了**“底层确定性认知计算引擎 + 上层智能启发式辅学导师”**的双层架构。

### 1.1 双层架构职责划分与硬隔离屏障

```
┌────────────────────────────────────────────────────────┐
│                   学生端 (Student UI)                  │
│   今日任务 (Tasks) / 知识图谱 (Graph) / 学情档案 (Profile)  │
└───────────────────────┬────────────────────────────────┘
                        │
       ┌────────────────┴────────────────┐
       ▼                                 ▼
┌─────────────────────────────┐   ┌───────────────────────────────────┐
│   底层确定性自适应学习闭环     │   │      上层 AI 学习伙伴 (Sprint 9-A)    │
│  (Phase 4 封版 - 冻结保护)    │   │         (只读智能导师层)          │
├─────────────────────────────┤   ├───────────────────────────────────┤
│ • BKT 贝叶斯知识追踪模型    │   │ • 4 种启发式辅导模式               │
│ • 局部动态路径重规划引擎    │   │ • 考点权威微卡事实溯源             │
│ • 知识图谱 30 考点拓扑网络  │   │ • 题库精准错题盲区剖析             │
│ • Append-Only 学习事件日志  │   │ • 阶段学情全景全息分析             │
│ • 生产状态读写与持久化      │   │ • 多轮苏格拉底式启发对话           │
│                             │   │ • 5 轮滑动记忆窗口                │
│                             │   │ • allow_production_decision=false │
│                             │   │ • 零生产状态副作用 (Zero Mutation) │
└─────────────────────────────┘   └───────────────────────────────────┘
```

### 1.2 严格遵循的不变量与安全红线

1. **零生产状态修改 (Zero State Mutation)**：伴学助手的所有交互行为（提问、探讨、总结、切换模式）**绝不修改**学生的 BKT 掌握度、路径状态、学习事件日志或学生档案。`allow_production_decision = false` 作为最高硬约束。
2. **冻结目录 0 差异 (Zero Diff)**：`app/`、`tests/`、`data/seeds/` 严格保持 0 修改（`git diff --stat HEAD -- app/ tests/ data/seeds/` 严格为空）。
3. **事实依据溯源 (Fact Traceability)**：AI 生成的所有教学解答均基于经过白名单校验的权威系统事实（30 个考点微卡、题库标准试题与解析、学生真实掌握度分布），杜绝幻觉。前端消息体提供可展开的「引用事实依据」透明抽屉。
4. **杜绝技术黑话 (Zero Jargon)**：面向学生的界面与回答中绝对严禁出现任何内部底层实现词汇（如 `BKT`、`PathState`、`DynamicPathGenerator`、`EventRepository`、`MutationDomain`、`mastery_probability`）。
5. **多层安全防线**：
   - 输入长度拦截：单次输入严格限制 2000 字符，超长在前端（计数指示器与禁用按钮）及后端（422 SCHEMA_VALIDATION_FAILED）双重拦截。
   - 越狱与提示注入防御：内置 Prompt Injection 检测防护盾牌，拒绝越权指令。
   - 离线透明度保障：明确标识离线确定性保障状态，绝不伪造在线大模型。

---

## 二、4 种核心辅导模式与全流程贯通

| 模式标识 | 模式名称 | 核心功能与呈现特点 | 入口来源与打通路径 |
| :--- | :--- | :--- | :--- |
| `concept_explain` | **概念精讲** | 结构化输出「一句话直观理解」、「核心考点精要」、「生活与商业实例」、「考试常见陷阱与误区」、「导师复习指引」 | 1. AI 伴学主页模式切换<br>2. 今日任务中心 `CurrentFocusCard` 点击 `🤖 问问 AI` |
| `wrong_answer_review` | **错题剖析** | 依据试题题干、标准答案、学生错误选择及权威解析，启发式剖析错误思维根源并给出提分避坑建议 | 1. AI 伴学主页模式切换<br>2. 学情档案 `错题复盘本` 卡片点击 `🤖 AI 帮我分析` |
| `learning_summary` | **阶段总结** | 全景概括 30 考点掌握分布（已达标/发展中/薄弱待强化）、错题总数统计、并自适应指出下一阶段学习主攻方向 | 1. AI 伴学主页模式切换<br>2. 学情档案 `30考点掌握度全览` 点击 `🤖 总结我的学习情况` |
| `conversation` | **自由探讨** | 支持针对微观经济学概念、公式推导、现实案例的启发式连续对话，保持 5 轮学生专属滑动记忆窗口 | 1. AI 伴学主页模式切换<br>2. 消息流底部快捷「建议行动」标签一键触发追问 |

---

## 三、全自动化测试与质量门禁证据

### 3.1 质量门禁全绿矩阵 (Quality Gates)

| 门禁脚本 | 检查项数 | 执行结果 | 核心断言 |
| :--- | :---: | :---: | :--- |
| `scripts/sprint9a_quality_gate.py` | 10 / 10 | **PASS** | 4大模式完整性、404边界、注入拦截、2000字截断、零突变快照、零黑话 |
| `scripts/sprint8d_quality_gate.py` | 10 / 10 | **PASS** | 统一真实源、API契约、Append-only日志、无伪造数据、冻结目录0 diff |
| `scripts/sprint8c_quality_gate.py` | 10 / 10 | **PASS** | 学情进展、错题复盘、教师分析、30考点守恒 |
| `scripts/sprint8b_dynamic_path_gate.py` | 12 / 12 | **PASS** | 3题前测、Top-3动态推荐航线、图谱高亮 |
| `scripts/ai_judge_shadow_gate.py` | 12 / 12 | **PASS** | AI 影子判题审计合规 |

### 3.2 单元与集成测试结果

1. **后端单元测试 (`gateway/tests/test_sprint9a_companion.py`)**：
   - 12 / 12 测试全部通过（覆盖模式输出、404 边界、多轮对话、5 轮滑动窗口、注入防御、长度限制、多生隔离与会话重置、无黑话、零副作用）。
   - 全量回归测试：`gateway/tests/` 322 个测试全部通过；`tests/` 143 个测试全部通过。
2. **前端单元与契约测试 (`frontend/test/sprint9a_companion.test.ts`)**：
   - 10 / 10 测试全部通过（覆盖模式载荷、2000 字拦截、零黑话断言、安全元数据、学生切换状态清理）。
   - 全量回归测试：`frontend` 199 个测试（31 个测试套件）100% 通过。
3. **前端编译与类型检查**：
   - `npm run typecheck --prefix frontend`：0 错误。
   - `npm run build --prefix frontend`：生产打包通过（`dist/` 生成成功）。

---

## 四、真实 Chromium 浏览器端到端 UAT 验收报告

运行自动化验收脚本：`python scripts/uat_sprint9a_browser.py`  
测试数据报告路径：`artifacts/uat_results.json`  
测试截图存储路径：`artifacts/uat_screenshots/sprint9a_01~12.png`  

### 4.1 验收场景矩阵 (Scenarios A ~ L)

| 场景编号 | 场景名称 | 验收内容 | 截图凭据 | 验收结论 |
| :---: | :--- | :--- | :--- | :---: |
| **Scenario A** | AI 伴学页面直达与导师身份 | 访问 `/student/assistant`，验证导师头像、学生专属标识、安全状态与零黑话呈现 | `sprint9a_01_assistant_landing.png` | **PASS** |
| **Scenario B** | 概念精讲启发辅导 | 验证首发概念精讲结构（直观理解、要义、实例、陷阱、指引） | `sprint9a_02_concept_explain.png` | **PASS** |
| **Scenario C** | 引用事实依据透明展开 | 点击展开折叠抽屉，验证引用的 6 项权威卡片事实（章节、掌握度、难度等） | `sprint9a_03_referenced_facts_expanded.png` | **PASS** |
| **Scenario D** | 今日任务焦点直通 AI | 从 `/student/tasks` 的 `CurrentFocusCard` 点击 `🤖 问问 AI` 直达伴学界面 | `sprint9a_04_ask_ai_from_focus_card.png` | **PASS** |
| **Scenario E** | 错题剖析模式切换 | 切换至 `错题剖析` 模式，验证题目分析、选项剖析与避坑指引 | `sprint9a_05_wrong_answer_review.png` | **PASS** |
| **Scenario F** | 错题本直通 AI 分析 | 从 `/student/profile` 错题卡片点击 `🤖 AI 帮我分析` 唤起精准辅导 | `sprint9a_06_ask_ai_from_wrong_answers.png` | **PASS** |
| **Scenario G** | 阶段学情全景总结 | 切换至 `阶段总结` 模式，全景呈现 30 考点分布与下阶段自适应建议 | `sprint9a_07_learning_summary.png` | **PASS** |
| **Scenario H** | 档案总览直通 AI 总结 | 从 `/student/profile` 掌握度全览点击 `🤖 总结我的学习情况` 直达 | `sprint9a_08_ask_ai_summary_button.png` | **PASS** |
| **Scenario I** | 自由探讨启发式多轮互动 | 输入提问“需求价格弹性大于1降价是否增加总收益”，获得苏格拉底式启发解答 | `sprint9a_09_conversation_multiturn.png` | **PASS** |
| **Scenario J** | 建议行动标签触发追问 | 点击伴学消息底部的建议行动 Chip，自动发起深入追问与解答 | `sprint9a_10_action_chip_triggered.png` | **PASS** |
| **Scenario K** | 字符长度防线硬校验 | 输入 2000+ 超长字符，触发前端实时红色告警与发送按钮安全禁用 | `sprint9a_11_character_limit_defense.png` | **PASS** |
| **Scenario L** | 学生切换隔离与新话题重置 | 点击“新话题”重置会话，切换学生至 S002 验证独立身份与数据隔离 | `sprint9a_12_student_switch_isolation.png` | **PASS** |

### 4.2 运行时可靠性统计

- **Console Errors**：**0**
- **Page Exceptions**：**0**
- **Failed HTTP Requests**：**0**

---

## 五、交付文件清单

```text
gateway/
├── learning/companion/
│   ├── __init__.py           # 模块导出定义
│   ├── models.py             # 伴学模式、请求响应、安全元数据与会话模型
│   ├── context.py            # 事实依据提取器、上下文脱敏与白名单过滤器
│   ├── prompt.py             # 启发式导师系统提示词、防注入护盾与防黑话模板
│   └── service.py            # 伴学核心服务、5轮滑动记忆窗口、零突变单例
├── api.py                    # 伴学端点暴露 (POST /api/ai/companion, POST /reset, GET /sessions)
└── tests/
    └── test_sprint9a_companion.py  # 12项完整后端验收测试

frontend/
├── src/
│   ├── types.ts              # 伴学模式与数据类型契约
│   ├── api.ts                # 伴学 API 客户端函数
│   ├── components/
│   │   ├── AIAssistant.tsx   # 伴学专属导师产品级组件
│   │   └── student/
│   │       ├── CurrentFocusCard.tsx  # 接入 "🤖 问问 AI"
│   │       ├── ProgressOverview.tsx  # 接入 "🤖 总结我的学习情况"
│   │       └── WrongAnswerReview.tsx # 接入 "🤖 AI 帮我分析"
│   └── layouts/
│       └── StudentLayout.tsx         # 上下文直通路由、学生切换状态清理
└── test/
    └── sprint9a_companion.test.ts    # 10项前端契约自动化测试

scripts/
├── sprint9a_quality_gate.py  # Sprint 9-A 10项严格质量门禁
└── uat_sprint9a_browser.py   # 12场景全自动化 Playwright Chromium UAT 脚本

artifacts/
├── uat_results.json          # UAT 运行完整日志与结果记录
└── uat_screenshots/          # 12 张高清验收截图
    ├── sprint9a_01_assistant_landing.png
    ├── sprint9a_02_concept_explain.png
    ├── sprint9a_03_referenced_facts_expanded.png
    ├── sprint9a_04_ask_ai_from_focus_card.png
    ├── sprint9a_05_wrong_answer_review.png
    ├── sprint9a_06_ask_ai_from_wrong_answers.png
    ├── sprint9a_07_learning_summary.png
    ├── sprint9a_08_ask_ai_summary_button.png
    ├── sprint9a_09_conversation_multiturn.png
    ├── sprint9a_10_action_chip_triggered.png
    ├── sprint9a_11_character_limit_defense.png
    └── sprint9a_12_student_switch_isolation.png
```

---

## 六、交付结论

Phase 5 / Sprint 9-A — AI Learning Companion & Intelligent Study Assistance 各项功能需求、架构契约、安全隔离屏障、自动化测试套件与浏览器端到端验收**全部 100% 达成**，正式封版交付。
