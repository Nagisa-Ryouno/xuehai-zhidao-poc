# 学海智导 (Xuehai Zhidao) V2 产品演进路线图 (Product Roadmap)

> **版本**：Phase 6 Complete / Final Handoff Freeze Baseline
> **更新时间**：2026-09-26
> **当前基线**：`handoff-final-2026-09` (`99c68a2`)
> **产品状态**：**[ACCEPTED / FEATURE FROZEN] (已全部验收 / 功能彻底冻结 / 交付交接)**
> **核心导向**：以自适应学习真实闭环为基石，保持后端与算法稳定，支持团队高效交接与人工验收。

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
│ Phase 5 / Sprint 9-F: Retention Check & Spaced Review Lite   [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 5 / Sprint 9-G: Today Action & Next Step Orchestration [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 6 / Sprint 10-A: Curated MOOC & External Redirect      [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 6 / Sprint 10-B: AI Recommendation & DeepSeek Provider [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 6 / Sprint 10-C: Student PWA & Session Productization  [ACCEPTED]     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 6 / Sprint 10-D: Teacher Web 30-KP Loop & Freeze       [ACCEPTED]     │
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
  - 9/9 质量门禁全绿，6/6 真实 Chromium 浏览器端到端 UAT 全数通过。

### Phase 5 / Sprint 9-F & 9-G: Retention Check & Today Action Orchestration 【已验收 / ACCEPTED】
- **目标**：打通记忆留存间隔复习检查与学生端今日唯一最高优先级行动调度。
- **成果**：
  - 交付 `TodayActionResolver` 引擎，基于掌握度与遗忘曲线确定「攻克薄弱/间隔复习/靶向微练」；
  - 前端上线 `TodayActionCard`，作为学生端首页唯一主 Hero CTA。

---

## 四、Phase 6 核心里程碑：产品化闭环与最终交接封版 (Phase 6 Milestones)

> **当前阶段**：`[ACCEPTED / FEATURE FROZEN]` (功能彻底冻结，通过全量质量门禁与工程审计)

### Phase 6 / Sprint 10-A: 权威精选名校 MOOC 与安全跳转闭环 【已验收 / ACCEPTED】
- **成果**：
  - 引入北京大学与武汉大学 12 项真实微课条目，其余 18 项如实由平台原生资源覆盖，杜绝数据伪造；
  - 交付前端 `ExternalRedirectModal`，严格进行域名白名单、HTTPS 协议与跳转免责校验。

### Phase 6 / Sprint 10-B: AI 个性化推荐与 DeepSeek 官方大模型接入 【已验收 / ACCEPTED】
- **成果**：
  - 官方接入 DeepSeek 模型，实现离线启发式安全兜底；
  - 建立三层推荐校验器，严格保障推荐结果 100% 存在于统一目录，杜绝幻觉链接。

### Phase 6 / Sprint 10-C: 学生端 PWA 离线外壳与学习会话产品化 【已验收 / ACCEPTED】
- **成果**：
  - 交付 Web App Manifest 与 Service Worker，`/api/*` 强制 Network-Only 策略防止脏缓存；
  - 学习会话重塑为 5 步微时序看板（导引 ➔ 概念 ➔ 材料 ➔ 测验 ➔ 结算），提供极致人本体验。

### Phase 6 / Sprint 10-D: 教师端观察与干预中台闭环与封版 【已验收 / ACCEPTED】
- **成果**：
  - 交付 Overview / Knowledge / Students 3-Tab 架构，支持 30 考点全景分析与错因诊断抽屉；
  - 支持学生全维学情画像下钻与 3 类教学干预动作发起（REVIEW_CONCEPT / RETRY_PRACTICE / MARK_FOLLOWED）；
  - 执行工程质量加固，达成 749 项后端测试全绿、469 项前端测试全绿、25/25 最终门禁全通，完成交接封版。
