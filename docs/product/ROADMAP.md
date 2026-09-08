# 学海智导 (Xuehai Zhidao) V2 产品演进路线图 (Phase 2.2 Roadmap)

> **版本**：Phase 2.2 Product Roadmap  
> **基线状态**：Phase 2.1 Architecture FROZEN  
> **核心导向**：以核心自适应学习闭环为唯一驱动，拒绝过度设计与架构反复，专注于产品体验与业务流转。

---

## 一、路线图全景概览 (Roadmap Overview)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 2.2-A: Product Baseline & Repository Governance        [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2.2-B: Core Student Experience Consolidation           [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2.2-C: Closed-Loop Adaptive Learning & Path Replanning [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2.2-D: Adaptive Learning Integration & Validation      [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2.2-E / Sprint 6: Release Hardening & Quality Gate     [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 3 / Sprint 7-A: AI Learning Companion Context Boundary [ACCEPTED]     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、阶段详细规划 (Detailed Phase Breakdown)

### Phase 2.2-A: Product Baseline & Repository Governance 【当前阶段】
- **目标 (Goal)**：建立清晰的产品定位基线、功能盘点与演进路线图，规范根目录工程文档。
- **用户价值 (User Value)**：让项目参与者与评审人员在 3~5 分钟内准确理解项目核心价值、真实能力现状及边界，消除信息不对称。
- **交付物 (Deliverables)**：
  - 根目录标准 `README.md`
  - `docs/product/PRODUCT-VISION.md`
  - `docs/product/FEATURE-BASELINE.md`
  - `docs/product/ROADMAP.md`
- **验收标准 (Acceptance Criteria)**：
  - 架构冻结不变，测试（143 后端 / 37 前端 / 17 架构适应度）100% 通过；
  - 真实反映技术栈（React 19 + TypeScript + Vite + Tailwind CSS v4 / FastAPI）；
  - 明确标注各项功能在后端、前端及端到端层面的成熟度。

---

### Phase 2.2-B: Core Student Experience Consolidation 【下一阶段】
- **目标 (Goal)**：巩固学生端移动端优先 (Mobile-First) 核心体验，打通任务流、图谱与学情卡片的数据一致性。
- **用户价值 (User Value)**：学生进入平台后拥有清晰明了的“今日任务”、“图谱探查”与“学情看板”，交互流畅无阻断。
- **交付物 (Deliverables)**：
  - 学生端 4-Tab（今日任务、知识图谱、学情档案、AI伴学）体验打磨；
  - 路径节点状态（LOCKED, AVAILABLE, IN_PROGRESS, COMPLETED）在任务列表中的直观视觉表达；
  - 弱网与异常场景下的友好错误反馈与重试交互。
- **验收标准 (Acceptance Criteria)**：
  - 学生端在桌面端与移动端触控场景（>=44px 靶点）适配良好；
  - 切换学生（S001~S005）时图谱节点状态与推荐路径 100% 保持同步响应。

---

### Phase 2.2-C: Closed-Loop Adaptive Learning & Path Replanning (Sprint 4)
- **状态 (Status)**：`ACCEPTED` (已全面验收归档)
- **目标 (Goal)**：全面闭合“测验作答 → BKT 演进 → 1-hop 局部动态重规划 → 前端节点即时解锁”端到端链路，建立可解释推荐与五层微测验反馈。
- **核心成果 (Achievements)**：
  - 交付 `adaptiveLearningModel.ts` 纯函数解释模型与全站统一 0.80/80% 掌握度目标；
  - `CurrentFocusCard` 接入“AI推荐依据”四要素手风琴面板；
  - `KnowledgePointQuiz` 建立五层结构化自适应进阶反馈，杜绝虚假解锁；
  - `LearningPath` 建立空间位置标识与空值/未命中安全收敛；
  - 前端 75 项契约测试全部通过，后端 17 架构 + 143 全量测试 100% 通过，`app/` 0 修改。

---

### Phase 2.2-D / Sprint 5: Adaptive Learning Integration & Real-World Validation
- **状态 (Status)**：`ACCEPTED` (全链路真实运行闭环全面验收归档)
- **目标 (Goal)**：
  证明 Sprint 4 建立的自适应学习闭环能够在真实运行环境中端到端成立，验证“推荐路径 → Focus Task → Quiz 作答 → 权威判题 → BKT 更新 → 局部重规划 → 五层反馈 → 刷新状态 → 焦点移转”的全链路真实闭环。
- **核心成果 (Achievements)**：
  - 交付 `frontend/test/adaptive_learning_integration_contract.test.ts`，矩阵化覆盖 Scenario A ~ F 六大核心业务场景；
  - 引入单调递增 `requestIdRef`，实现跨学生与同学生并发刷新的全链路乱序拦截；
  - 引入 `isSubmittingRef` 同步提交互斥锁，彻底杜绝移动端高频双击引发的二次作答提交；
  - 前端 84 项测试全部通过，后端 17 架构 + 143 全量测试 100% 通过，`app/` 0 修改。

---

### Phase 2.2-E / Sprint 6: Release Hardening & Quality Gate 【当前完成 / ACCEPTED】
- **状态 (Status)**：`ACCEPTED` (全工程质量门禁固化与发布加固)
- **目标 (Goal)**：
  将 Phase 2.2-B ~ 2.2-D 建立的自适应学习闭环与工程资产固化为不可绕过、全自动化、可审计的统一质量门禁系统（Quality Gate），确保后续任何迭代无法静默破坏闭环与边界。
- **范围与边界红线 (Scope & Red Lines)**：
  - **后端绝对冻结 (Freeze Invariant)**：`app/` 0 修改，`tests/` 0 修改，BKT 数学公式及参数 0 修改，Decision Core 决策矩阵 0 修改，API 契约与数据库 Schema 0 修改。
  - **代码与测试双向守护**：前端生产构建无报错，TypeScript 严格类型检查无错误，React Rules of Hooks 零违反。
- **五层统一质量门禁架构 (Unified 5-Gate Architecture)**：
  - **Gate 1 — Frontend Type Safety**：`tsc -b` 严格编译检查，0 错误；
  - **Gate 2 — Frontend Contract & Integration Tests**：`node --experimental-strip-types --test test/*.test.ts` 原生极速测试，84 项全通（9 个 Suite，~500ms）；
  - **Gate 3 — Frontend Production Build**：`vite build` 生产打包编译，生成干净静态 bundle，0 警告；
  - **Gate 4 — Backend Regression Tests**：`pytest tests/architecture/ -v` (17 tests) + `pytest tests/ -q` (143 tests)，共 160 个后端测试 100% PASS；
  - **Gate 5 — Backend Freeze Invariant**：`git diff -- app/ tests/` 自动化比对，严格断言 0 diff。
- **关键修复与成果 (Key Deliverables & Hardening)**：
  - 交付统一门禁脚本 `scripts/quality_gate.py`，支持动态解析测试计数与清晰的失败诊断指引；
  - 在 `frontend/package.json` 挂载 `"test"`, `"typecheck"`, `"quality:gate"` 原生指令；
  - 彻底修复 `CurrentFocusCard.tsx` 中条件调用 `useState` 导致的 React Rules of Hooks 违规；
  - 清理 `adaptive_learning_contract.test.ts` 中无用的未引用类型导入，`oxlint` 0 报错；
  - 建立 10 大核心自适应能力与测试资产审计矩阵，实现从领域模型到端到端构建的全面可追溯性。
- **验收结果 (Acceptance Evidence)**：
  - `npm run quality:gate`：5/5 Gates Passed (100%)；
  - 总体系统质量达到高可用发布就绪基线（READY FOR RELEASE）。

---

### Phase 3 / Sprint 7-A: AI Learning Companion Context Boundary Recon & Contract Foundation 【已验收 / ACCEPTED】
- **状态 (Status)**：`ACCEPTED` (AI 学习伴学上下文边界基石固化)
- **目标 (Goal)**：
  建立「Deterministic Adaptive Learning Engine → Learning Context → AI Companion」之间的严格单向事实数据流与防篡改边界，禁止 AI 拥有任何学习决策权或反向篡改客观事实的能力。
- **核心成果与交付物 (Key Deliverables)**：
  - **纯函数上下文模型**：`frontend/src/components/student/learningContextModel.ts`，100% 纯函数、无副作用、无 DOM、无 IO、零随机性，通过 `deepFreeze` 输出完全只读的 `LearningContext`；
  - **契约测试基准套件**：`frontend/test/learning_context_contract.test.ts`，16 项严格契约测试（Test 1~16）全部通过；
  - **全量测试绿色突破**：前端测试总数从 84 项提升至 100 项（10 个 Suite），执行耗时 ~620ms，100% PASS；
  - **质量门禁持续守护**：`npm run quality:gate` 5/5 门禁全数通过。

---

### Phase 3 / Sprint 7-B: Grounded AI Response Pipeline 【已验收 / ACCEPTED】
- **状态 (Status)**：`ACCEPTED` (AI 输出侧事实校验与安全兜底双重边界建立)
- **目标 (Goal)**：
  建立输出侧第二道确定性安全边界，完成 `LearningContext → PromptContext → LLM → StructuredAIResponse → FactValidator → GroundedAnswer / SafeFallback` 的完整响应管线。
- **架构核心理念 (Core Principles)**：
  - **结构有效性 ≠ 事实有效性**：结构化输出 Schema 仅保障响应符合 JSON/TypeScript 字段定义，无法保证其内容符合客观事实；
  - **FactValidator 事实校验强边界**：对大模型输出进行多维硬性一致性校验（掌握度幻觉、达标线伪造、虚假解锁、状态矛盾、认知回退矛盾、未知考点与编造的统计事实），杜绝一切伪造；
  - **确定性安全兜底 (Deterministic Safe Fallback)**：当 AI 回答被 Validator 阻断时，系统绝不抛出异常，而是基于 `LearningContext` 权威状态生成结构完备的确定性兜底回答。
- **核心成果与交付物 (Key Deliverables)**：
  - **Prompt 上下文格式化模型**：`frontend/src/components/student/learningPromptModel.ts`，实现 `buildLearningPromptContext` 纯函数白名单投影与 10 大 `GROUNDING_RULES` 注入；
  - **结构化响应契约模型**：`frontend/src/components/student/aiResponseModel.ts`，定义 `StructuredAIResponse`，物理隔离一切决策权限字段；
  - **事实校验与兜底引擎**：`frontend/src/components/student/aiResponseValidator.ts`，实现 `validateAIResponse` 8 大类违规检测与 `createDeterministicFallback`；
  - **组件端安全接入**：`frontend/src/components/AIAssistant.tsx` 全面接入 `validateAIResponse`，实现输出前事实拦截；
  - **契约测试突破**：新增 `learning_prompt_contract.test.ts`（10 项）与 `ai_response_validation.test.ts`（10 项），全量前端测试达到 **120/120 PASS (12 Suites)**；
  - **五大质量门禁 100% PASS**：通过统一 `npm run quality:gate`，保持 `app/`、`tests/`、`data/seeds/` 严格 0 变更。

---

### Phase 3 / Sprint 7-C: Controlled LLM Integration & Grounded Companion 【当前完成 / ACCEPTED】
- **状态 (Status)**：`ACCEPTED` (受控 AI Provider 抽象层、故障隔离与伴学全管线打通)
- **目标 (Goal)**：
  建立可替换、可测试、可失败、可回退、不可越权的 AI Provider 抽象层与完整的 Grounded AI Companion 管线，实现模型故障与幻觉时的系统级高可用容灾。
- **核心架构理念与安全边界 (Core Architecture & Boundary Principles)**：
  1. **AI Provider 抽象与隔离 (`AIProvider`)**：Provider 只能接收白名单 `LearningPromptContext`，严禁直接接收学生对象、学习路径、PathState 或 Decision Core，只能返回 `StructuredAIResponse`；
  2. **确定性 Mock Provider (`MockAIProvider`)**：纯本地无网络、无 `Math.random`、无 `Date.now`，相同输入 100% 幂等，支持模拟超时、崩溃、掌握度/解锁幻觉与畸形结构；
  3. **伴学管线服务与故障隔离 (`aiCompanionService`)**：`askLearningCompanion` 统一封装 Prompt 构建、Provider 超时拦截、FactValidator 校验与兜底降级。无论模型超时、抛错或返回非合法结构，均安全降级为基于真实学情的 `GroundedAnswer`，绝不冒泡至 UI；
  4. **AI 零学习决策权 (Zero Decision Authority)**：模型仅作为解释者、答疑者与导师，绝对无权修改掌握度、路径状态、前置依赖、重规划动作与下一步任务；
  5. **UI 与 AI 逻辑彻底解耦 (`AIAssistant.tsx`)**：组件只负责用户交互与渲染 `GroundedAnswer`，不直接包含 Prompt 拼装、Validator 规则或 Provider 选择；
  6. **零 Secret 暴露红线**：当前阶段使用本地 `MockAIProvider`，严禁在浏览器端客户端代码中硬编码或暴露任何真实 API Key；
  7. **后端红线绝对冻结**：`app/`、`tests/`、`data/seeds/` 保持严格 0 diff。
- **核心成果与交付物 (Key Deliverables)**：
  - **AI Provider 接口**：`frontend/src/components/student/aiProvider.ts`
  - **确定性 Mock 实现**：`frontend/src/components/student/mockAIProvider.ts`
  - **伴学统一服务**：`frontend/src/components/student/aiCompanionService.ts`
  - **伴学组件接入**：`frontend/src/components/AIAssistant.tsx` 重构接入 `askLearningCompanion`
  - **契约测试集 (新增 28 项)**：
    - `frontend/test/ai_provider_contract.test.ts` (8 项 Provider 契约测试)
    - `frontend/test/ai_companion_pipeline.test.ts` (20 项 Pipeline 集成、故障隔离与容灾契约测试)
  - **测试基线新突破**：前端测试总数从 120 项跃升至 **148/148 PASS (14 Suites, ~800ms)**；
  - **质量门禁持续 100% PASS**：统一 `npm run quality:gate` 五大门禁全部通过。
