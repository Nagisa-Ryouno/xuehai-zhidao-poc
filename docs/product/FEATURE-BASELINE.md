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
| **自适应重规划**| **Path Replanning (动态路径流转)** | 完整 (1-hop 决策核心/Canonical JSON/确定性测试) | 部分 (API 待直连响应展示) | 部分闭环 | P0 | **E2E PARTIAL** | 后端在答题成功后已通过 `QuizSubmitResponse.replanning` 返回完整信封且持久化状态；前端需在 Phase 2.2-C 强化动态更新提示与动效反馈。 |
| **状态持久化**| **Path State (路径状态机)** | 完整 (独立原子持久化/4态流转) | 部分 (样式准备完毕) | 部分闭环 | P0 | **BACKEND READY** | `LOCKED/AVAILABLE/IN_PROGRESS/COMPLETED` 四态落盘与 API 完备；前端需在 Phase 2.2-B/C 完整连通节点状态解锁动效。 |
| **智能导学** | **AI Assistant (伴学副驾)** | 完整 (多维上下文装配+规则兜底) | 完整 (问答抽屉+快捷提示词) | 完整联调 | P0 | **COMPLETE** | 支持学生专属学情问候语、快捷追问、结构化回答生成与流式打字模拟。 |
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
- AI 伴学助手智能问答与专属问候

### 2. 达到【后端就绪 / 前端待深化 (BACKEND READY / FRONTEND PARTIAL)】的能力：
- 学习行为事件底层流水追溯（后端已完备写入 `data/runtime/learning_events.jsonl`，前端作为后台底座运行）
- BKT 状态实时多题演进（后端完全自动化，前端需在后续完善视觉化认知曲线）
- 路径状态独立持久化（后端已独立落盘至 `data/runtime/learning_path_states.json`，前端节点解锁链路需在 Phase 2.2-B/C 全面闭环）

### 3. 【端到端部分闭环 (E2E PARTIAL)】的核心突破点：
- **作答 $\to$ BKT 演进 $\to$ 局部重规划**：
  后端 Golden E2E 3步时序已取得字节级确定性通过（`test_path_replanning_golden_e2e.py`）。
  前端当前已能接收响应中的 `replanning` 字段，Phase 2.2 的重点是使前端感知并动态重绘解锁节点（如从 LOCKED 变为 AVAILABLE），向学生讲明“恭喜达标！已为你解锁后继知识点”。
