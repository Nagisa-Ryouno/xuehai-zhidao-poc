# 学海智导 (Xuehai Zhidao) V2 产品演进路线图 (Product Roadmap)

> **版本**：Phase 5 / Sprint 9-E Complete & Phase 6 Initiation  
> **更新时间**：2026-09-16  
> **当前基线**：`2a3ece6 feat(learning): add resource strategy adaptation`  
> **核心导向**：以自适应学习真实闭环为基石，保持后端与算法稳定，支持团队高效协同推进界面 UI/UX 优化。

---

## 一、路线图全景概览 (Roadmap Overview)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 2.1: Pragmatic Layered Modular Monolith Architecture   [FROZEN]       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2.2: Productization & Baseline Governance              [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 3: Grounded AI Companion & Context Boundary            [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 4 / Sprint 8-B: Local Dynamic Replanning & Focus Task  [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 4 / Sprint 8-C: Multi-Student Dynamic Path Isolation   [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 4 / Sprint 8-D: AI Evaluation Gateway & Shadow Judge   [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 5 / Sprint 9-A: AI Companion Foundation & Alignment    [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 5 / Sprint 9-B: Guided Actions & Quick Check           [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 5 / Sprint 9-C: 30 KPs 130 Resources & Resource Hub    [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 5 / Sprint 9-D: Learning Effectiveness Verification    [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 5 / Sprint 9-E: Resource Strategy Adaptation Lite      [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 6: UI/UX Design Polish & Experience Enhancement        [IN PROGRESS]  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、Phase 4 核心里程碑 (Phase 4 Milestones)

### Phase 4 / Sprint 8-B: Local Dynamic Replanning & Focus Task Scheduling 【已验收 / ACCEPTED】
- **目标**：实现 DAG 拓扑约束下的局部动态路径重规划与今日核心任务调度。
- **成果**：
  - 交付 `DynamicPathGenerator` 服务，计算基于当前掌握度的优先修读序列与焦点考点；
  - 建立 1-hop 局部变更隔离，前置只读，后继单步激活为 `AVAILABLE`；
  - 前端渲染今日任务聚焦卡片与推荐依据面板。

### Phase 4 / Sprint 8-C: Multi-Student Dynamic Path Isolation & BKT Calibration 【已验收 / ACCEPTED】
- **目标**：实现多学生独立学情隔离与真实学习数据回放校准。
- **成果**：
  - 支持 S001~S005 五名学生动态路径与掌握度完全物理隔离；
  - 增加教师端决策看板接口（班级宏观分析、薄弱点统计、学生个体风险雷达）；
  - 交付校准门禁脚本 `scripts/ai_judge_calibration_gate.py`。

### Phase 4 / Sprint 8-D: AI Evaluation Gateway & Shadow Judge 【已验收 / ACCEPTED】
- **目标**：建立安全网关与 AI 影子评判层。
- **成果**：
  - 交付 `gateway/api.py` 生产级安全网关（8011 端口，请求关联、脱敏隔离、审计指标）；
  - 建立 AI Judge 影子比对引擎与判定质量门禁。

---

## 三、Phase 5 核心里程碑 (Phase 5 Milestones)

### Phase 5 / Sprint 9-A: AI Companion Foundation & Grounded Learning Dialog 【已验收 / ACCEPTED】
- **目标**：建立学生专属 AI 伴学对话体系与事实单向绑定。
- **成果**：
  - 问答抽屉结合当前考点与学生学情，生成专属问候语与启发式追问；
  - 严格保持 AI 零学习决策权，杜绝虚假掌握与伪造解锁。

### Phase 5 / Sprint 9-B: Guided Actions & Quick Check 【已验收 / ACCEPTED】
- **目标**：建立双向互动伴学动作与即时微测自测。
- **成果**：
  - 伴学组件提供「核心概念解读」、「易错陷阱剖析」等引导式动作 (Guided Actions)；
  - 内置即时快速自测 (Quick Check)，答题后提供启发式反馈与行动复盘横幅。

### Phase 5 / Sprint 9-C: 30 Knowledge Points, 130 Native Learning Resources & Resource Hub 【已验收 / ACCEPTED】
- **目标**：全量上线 30 考点内部原生材料库与自适应推荐中心。
- **成果**：
  - 原生支持 130 项内部资源（概念微卡、典型例题深度剖析、靶向微练）；
  - 上线「学习资源中心」(Resource Hub)，提供基于当前考点与掌握度的自适应推荐。

### Phase 5 / Sprint 9-D: Learning Effectiveness Verification & Session Closed Loop 【已验收 / ACCEPTED】
- **目标**：打通“资源学习 ➔ 靶向微练 ➔ 权威掌握度变化 ➔ 4 档学习效果验证”的完整闭环。
- **成果**：
  - 4 步会话看板（考点微卡 ➔ 典型例题 ➔ 靶向练习 ➔ 检验掌握度）；
  - 服务端记录初始快照并在完成时重读 BKT 计算 $\Delta P(L)$；
  - 交付人本时间关联导师叙事反馈，杜绝技术黑话。

### Phase 5 / Sprint 9-E: Learning Retention & Resource Strategy Adaptation Lite 【已封版 / ACCEPTED】
- **目标**：基于学生过去使用材料的真实效果，确定性微调下一次资源推荐排位并给出人本推荐理由。
- **成果**：
  - 纯确定性 +2/+1/0/-1 分级微调算法，稳定保序排序；
  - 展示「💡 为什么推荐？」理由气泡、紫色「成效优选 (+2)」徽章与「🔄 这次换一种方式试试」卡片；
  - 数据不足时优雅自然保序兜底，杜绝数据伪造；
  - 9/9 质量门禁全绿，6/6 真实 Chromium 浏览器端到端 UAT 全数通过。

---

## 四、Phase 6 演进目标：UI/UX 视觉与交互体验打磨 (Phase 6 Roadmap)

> **当前阶段**：`IN PROGRESS` (协作开展界面 UI 视觉优化)

- **核心目标**：
  在保持现有后端业务逻辑、API 契约与质量门禁 100% 绿灯的前提下，全面升级学生端与教师端的视觉美感、信息层级与操作流畅度。
- **重点优化模块**：
  1. **Resource Hub 视觉升级**：重构学习材料卡片层次，提升「💡 为什么推荐？」气泡与徽章的质感，优化 4 步学习看板进度条动效。
  2. **AI 伴学对话体验优化**：优化抽屉动画、气泡交互，提升 Guided Actions 按钮的触控反馈与微测验选项卡片视觉。
  3. **今日任务与聚焦卡片 (CurrentFocusCard)**：优化焦点知识点视觉比重与推进动效，提升推荐依据手风琴面板的美观度。
  4. **知识图谱 (Knowledge Graph)**：优化 React Flow 节点的排版、高亮光效与抽屉弹窗的移动端体验。
  5. **移动端 375px 窄视口精致适配**：在紧凑视口下打磨字体字阶、行高、边距与触控靶点（$\ge 44\text{px}$）。
- **质量验收标准**：
  - `npm run typecheck` 保持 0 错误；
  - `npm test --prefix frontend` 242 项契约测试 100% PASS；
  - `npm run build --prefix frontend` 生产构建成功；
  - 所有现有 `data-testid` 属性完整保留。
