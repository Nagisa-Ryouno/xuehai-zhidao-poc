# 学海智导 (Xuehai Zhidao) V2 功能基线盘点 (Feature Baseline)

> **版本**：Phase 2.2 Baseline  
> **更新时间**：2026-09-07  
> **审计基线 Commit**：`f0c0a0f chore(architecture): freeze phase 2.1 modular monolith baseline`  
> **状态标注原则**：严格区分 **Backend Capability**、**Frontend Experience** 与 **End-to-End Capability**，不因存在后台 service 即宣称功能完成。

---

## 一、核心功能矩阵 (Feature Matrix)

| 业务领域 | 核心功能 (Feature) | 后端状态 (Backend) | 前端状态 (Frontend) | 端到端闭环 (E2E) | 优先级 | 当前总体状态 (Status) | 现状说明与体验差距 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **学生学情** | **Student Profile (多维画像)** | 完整 (API + Repo) | 完整 (ProfileCard) | 完整联调 | P0 | **COMPLETE** | 支持 S001~S005 五名典型学生画像数据，雷达图、基础信息与多维评估展示完整。 |
| **学生学情** | **Dashboard (学情聚合)** | 完整 (聚合 Service) | 完整 (双端 Layout) | 完整联调 | P0 | **COMPLETE** | 学生端/教师端角色无缝切换，聚合卡片、薄弱点列表与最近任务一览完整。 |
| **学情诊断** | **Reports (综合学情报告)** | 完整 (5份只读报告) | 完整 (AIDiagnosis/Summary) | 完整联调 | P0 | **COMPLETE** | 维度拆解、成绩分布、优势与薄弱考点分析完整呈现。 |
| **拓扑导学** | **Knowledge Graph (知识图谱)** | 完整 (30节点/42边/纯JSON) | 完整 (React Flow 拓扑交互) | 完整联调 | P0 | **COMPLETE** | 节点依据 BKT 掌握度动态着色，点击节点弹出详情抽屉，前置/后继关系高亮。 |
| **路径推荐** | **Learning Path (静态基线路径)** | 完整 (拓扑排序规划) | 完整 (路径步进卡片) | 完整联调 | P0 | **COMPLETE** | 展示当前学生的推荐修读序列，按前置依赖与优先级编排。 |
| **自适应评测**| **Quiz (知识点微测验)** | 完整 (8考点/13题/权威判题) | 完整 (独立状态机组件) | 完整联调 | P0 | **COMPLETE** | 题库脱敏、选项判定、防重复提交、解析反馈与客户端计时（`time_spent_ms > 0`）完整。 |
| **行为追溯** | **Learning Event (行为事件日志)** | 完整 (JSONL 追加写/RLock/服务端时间戳) | 隐式集成 (通过测验提交) | 完整 (落盘可测) | P0 | **BACKEND READY** | 后端支持事件流追加与查询；前端在微测验提交时自动生成事件并落盘，暂无前端独立“事件流水可视化界面”。 |
| **认知追踪** | **BKT (贝叶斯掌握度演进)** | 完整 (4参数/幂等回放/状态更新) | 部分 (卡片与节点数值展示) | 闭环可测 | P0 | **FRONTEND PARTIAL** | 作答后后端状态已更新，图谱与仪表盘能显示最新概率；但前端缺少实时的“贝叶斯概率演化动态折线图”。 |
| **自适应重规划**| **Path Replanning (动态路径流转)** | 完整 (1-hop 决策核心/Canonical JSON/确定性测试) | 完整 (五层自适应进阶解释/防虚假解锁) | 完整闭环 | P0 | **COMPLETE** | 答题后经权威判题与局部重规划生成五层反馈，解锁后继并驱动任务中心即时流转。 |
| **状态持久化**| **Path State (路径状态机)** | 完整 (独立原子持久化/4态流转) | 完整 (统一四态表现/空间识别/无刷新更新) | 完整闭环 | P0 | **COMPLETE** | 四态落盘与 API 完备，前端实现双重指示、空间位置标识与并发刷新单调序号防护。 |
| **智能导学** | **AI Assistant (伴学副驾)** | 完整 (多维上下文装配+规则兜底) | 完整 (问答抽屉+快捷提示词+事实对齐) | 完整对齐 (Grounded) | P0 | **COMPLETE** | 支持学生专属问候语、快捷追问，且基于 `LearningContext` 深度对齐 17 项系统客观事实，提供确定性导学解释，杜绝 AI 伪造解锁或掌握事实。 |
| **历史复盘** | **Learning History (错题与历史)** | 基础数据已记录 | 待建设 | 待建设 | P1 | **PLANNED** | 行为事件与答题明细已落盘，待在 Phase 2.2 增强错题集回顾与历史趋势视图。 |
| **主动导学** | **Proactive AI Tips (主动关怀)** | 规则已定义 | 待建设 | 待建设 | P1 | **PLANNED** | 针对连续答错或停滞节点的自适应弹窗点拨提示，规划于 P1。 |
| **扩展服务** | **Payment / Social / Ranking** | 不支持 | 不支持 | 不支持 | P2 | **DEFERRED** | 支付、社交、排行榜、游戏化积分等非核心功能，明确列为暂缓范围。 |

---

## 二、能力层级对比总结 (Capability Level Summary)

### 1. 达到【端到端完整体验 (COMPLETE)】的能力：
- 学生画像查看与多学生切换 (`S001` ~ `S005`)
- 学情仪表盘数据看板与教师端双端隔离
- 综合学情诊断与雷达图评测报告
- 微观经济学 30 节点拓扑知识图谱浏览与节点详情探查
- 分知识点微测验交互（开题、作答、倒计时、判题、查看解析）
- **AI 伴学助手智能问答与事实对齐 (Grounded AI Companion)**：
  接入 `LearningContext` 统一上下文，针对推荐理由、掌握度差距、下一步行动提供基于系统事实的确定性导学回答。
- **自适应闭环学习与动态重规划 (Adaptive Closed-Loop)**：
  “推荐路径 $\to$ 今日核心焦点 $\to$ 微测验答题 $\to$ 服务端权威判题 $\to$ BKT 演进 $\to$ 1-hop 局部重规划 $\to$ 五层可解释反馈 $\to$ 无刷新刷新 $\to$ 下一步行动 $\to$ 焦点平滑流转”已全面闭合并通过全链路端到端验证。

### 2. 达到【后端就绪 / 前端待深化 (BACKEND READY / FRONTEND PARTIAL)】的能力：
- 学习行为事件底层流水追溯（后端已完备写入 `data/runtime/learning_events.jsonl`，前端作为后台底座运行）
- BKT 状态实时多题演进（后端完全自动化，前端需在后续完善视觉化认知曲线）
- 历史错题集回顾与时间轴演化视图（规划于后续阶段）

---

## 三、工程质量门禁与自动化测试基线 (Quality Gate Baseline)

项目已固化统一的五层全自动化质量门禁系统，可通过 `python scripts/quality_gate.py` 或前端目录 `npm run quality:gate` 单一命令一键触发：

| 门禁层级 (Gate) | 检验目标 | 校验命令 | 验证资产规模 | 判定标准 |
| :--- | :--- | :--- | :--- | :--- |
| **Gate 1: Frontend Type Safety** | 静态强类型安全性与导出契约 | `tsc -b` | 整个前端工程 | 0 TS errors |
| **Gate 2: Frontend Contract Tests** | 纯函数契约、UI 状态机、集成场景 | `node --experimental-strip-types --test test/*.test.ts` | 148 个测试 (14 大 Suite) | 100% PASS (<850ms) |
| **Gate 3: Frontend Production Build** | Vite 静态生产构建与资源打包 | `vite build` | 生产分发包 (`dist/`) | 构建成功无致命警告 |
| **Gate 4: Backend Regression Tests** | 领域架构适应度与后端全量业务回归 | `pytest tests/architecture/ -v` + `pytest tests/ -q` | 17 架构测试 + 143 业务测试 = 160 个测试 | 100% PASS |
| **Gate 5: Backend Freeze Invariant** | 后端领域模型、API 与数据库红线冻结 | `git diff -- app/ tests/ data/seeds/` | `app/`、`tests/`、`data/seeds/` 目录 | 严格 0 diff |

### 代码规范与工程卫生 (Engineering Hygiene)
- **React Rules of Hooks**：全量组件遵循 Hook 调用顶层规范，零条件调用违规；
- **Oxlint 静态检查**：`npm run lint` 保持 0 errors；
- **无重型测试依赖**：前端直接利用 Node 原生测试运行器 (`node:test` + `--experimental-strip-types`)，单次执行 <850ms，无需臃肿复杂的测试脚手架。

---

## 四、AI 学习伴学上下文边界与事实对齐基线 (Phase 3 / Sprint 7-A Baseline)

- **纯函数 Context 架构**：通过 `learningContextModel.ts` 将系统真实状态无副作用地投影为只读的 `LearningContext`，杜绝一切非纯函数调用（零随机数、零时间戳隐式生成）；
- **单向数据流与零决策权**：`Backend Facts → Frontend State → Deterministic Models → LearningContext → AI Companion`，严格禁止 AI 拥有学习决策权或反向篡改 BKT、PathState 与重规划结果；
- **16 项契约测试基线**：在 `learning_context_contract.test.ts` 中建立覆盖真实状态绑定、掌握度单一阈值（0.80/80%）、不可变性、无随机性、防事实伪造等 16 项测试；
- **真实模型接入声明**：当前阶段尚未接入真实外部大模型 API，尚未允许 AI 改变学习路径，采用前端确定性事实适配器保障 100% 事实一致性。

---

## 五、AI 输出侧事实校验管线与安全兜底基线 (Phase 3 / Sprint 7-B Baseline)

- **完整 Grounded 响应架构管线**：
  ```text
  Deterministic Adaptive Learning Engine
                  ↓
          LearningContext
                  ↓
          PromptContext
                  ↓
                LLM
                  ↓
        StructuredAIResponse
                  ↓
           FactValidator
                  ↓
        GroundedAnswer / SafeFallback
                  ↓
            AI Assistant
  ```
- **结构有效性 ≠ 事实有效性**：强类型 Schema 无法防御模型在合法字段内编造虚假掌握度或虚假解锁。FactValidator 是防御 AI 幻觉的第二道硬性安全屏障；
- **PromptContext 白名单投影与规则注入 (`learningPromptModel.ts`)**：
  - 严格剔除系统私有字段，仅投影学生身份、当前考点、统一掌握度（80%）、路径状态、前置与下一步行动；
  - 自动注入 10 大 Grounding Rules，约束 AI 行为边界。
- **StructuredAIResponse 零决策权限 (`aiResponseModel.ts`)**：
  - 响应契约严格仅包含 `answer`、`referenced_facts`、`suggested_explanation` 与 `grounding_status`；
  - 绝不暴露 `next_action`、`decision`、`unlock_nodes` 等决策字段。
- **FactValidator 事实校验引擎与确定性兜底 (`aiResponseValidator.ts`)**：
  - 覆盖 8 大类违规拦截：`MASTERY_HALLUCINATION`、`THRESHOLD_HALLUCINATION`、`FAKE_UNLOCK`、`RETAIN_CONTRADICTION`、`REGRESS_CONTRADICTION`、`LOCKED_CONTRADICTION`、`UNKNOWN_KNOWLEDGE_POINT`、`UNKNOWN_NUMERIC_FACT`；
  - 拦截后生成基于系统权威事实的 Safe Fallback，100% 确定性输出。
- **20 项 Sprint 7-B 契约测试基线**：
  - `learning_prompt_contract.test.ts`（10 项）+ `ai_response_validation.test.ts`（10 项）；
  - 全前端测试达 120/120 PASS（12 Suites）。

---

## 六、AI Provider 抽象、故障隔离与受控伴学基线 (Phase 3 / Sprint 7-C Baseline)

- **AI Provider 抽象契约 (`aiProvider.ts`)**：
  - 定义统一接口 `AIProvider.generate(promptContext: LearningPromptContext): Promise<StructuredAIResponse>`；
  - 强制执行白名单输入边界：Provider 只能消费 `LearningPromptContext`，严禁直接传入原始业务对象；只能输出 `StructuredAIResponse`，物理隔离一切决策字段。
- **确定性 Mock Provider (`mockAIProvider.ts`)**：
  - 本地纯内存运算，零外部网络依赖、零 `Math.random`、零 `Date.now`、零 `localStorage`；
  - 提供针对掌握度幻觉、虚假解锁、状态矛盾、超时和崩溃的受控仿真模式，支持在完全无 API Key 环境下进行闭环验证。
- **AI 伴学服务与全链路容灾 (`aiCompanionService.ts`)**：
  - 统一入口 `askLearningCompanion(context, question, provider)`；
  - **故障隔离机制 (Failure Isolation)**：对 Provider 运行实施超时时限保护（默认 5000ms），无论 Provider 发生超时、崩溃或畸形输出，均安全拦截并降级为 `createDeterministicFallback` 产出的 `GroundedAnswer`，绝不冒泡到 UI。
- **UI 与 AI 逻辑彻底解耦 (`AIAssistant.tsx`)**：
  - 交互组件只负责发起调用并渲染标准 `GroundedAnswer`，不直接包含 Prompt 构造或 Validator 规则。
- **零 Secret 暴露红线**：
  - 严禁在浏览器端客户端代码中硬编码或读取任何真实 API Key。
- **28 项 Sprint 7-C 契约测试基线**：
  - `ai_provider_contract.test.ts`（8 项）+ `ai_companion_pipeline.test.ts`（20 项）；
  - 全前端测试达 **148/148 PASS (14 Suites, ~800ms)**。
