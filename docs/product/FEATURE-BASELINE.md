# 学海智导 (Xuehai Zhidao) V2 功能基线盘点 (Feature Baseline)

> **版本**：Phase 6 / Final Handoff Freeze Baseline
> **更新时间**：2026-09-26
> **审计基线 Tag / Commit**：`handoff-final-2026-09` (`99c68a2`)
> **状态标注原则**：严格区分 **Backend Capability**、**Frontend Experience** 与 **End-to-End Capability**，区分 **Automated Verified** 与 **Manual QA Pending**，不夸大产品成熟度。

---

## 一、核心功能矩阵 (Feature Matrix)

| 业务领域 | 核心功能 (Feature) | 后端状态 (Backend) | 前端状态 (Frontend) | 端到端闭环 (E2E) | 优先级 | 当前总体状态 (Status) | 现状说明与体验边界 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **学生学情** | **Student Profile (多维画像)** | 完整 (API + Repo) | 完整 (ProfileCard) | 完整联调 | P0 | **COMPLETE** | 支持 S001~S005 五名典型学生画像数据，雷达图、基础信息与多维评估展示完整。 |
| **学生学情** | **Dashboard (学情聚合)** | 完整 (聚合 Service) | 完整 (双端 Layout) | 完整联调 | P0 | **COMPLETE** | 学生端/教师端角色无缝切换，聚合卡片、薄弱点列表与最近任务一览完整。 |
| **学情诊断** | **Reports (综合学情报告)** | 完整 (5份只读报告) | 完整 (AIDiagnosis/Summary) | 完整联调 | P0 | **COMPLETE** | 维度拆解、成绩分布、优势与薄弱考点分析完整呈现。 |
| **拓扑导学** | **Knowledge Graph (知识图谱)** | 完整 (30节点/42边/纯JSON) | 完整 (React Flow 拓扑交互) | 完整联调 | P0 | **COMPLETE** | 节点依据 BKT 掌握度动态着色，点击节点弹出详情抽屉，前置/后继关系高亮。 |
| **动态路径** | **Dynamic Path (动态路径排期)** | 完整 (DynamicPathGenerator) | 完整 (FocusCard/PathStep) | 完整联调 | P0 | **COMPLETE** | 基于 DAG 拓扑、前置约束与当前掌握度动态计算焦点节点与推荐队列。 |
| **今日行动** | **Today Action (今日学习行动)** | 完整 (TodayActionResolver) | 完整 (TodayActionCard) | 完整闭环 | P0 | **COMPLETE** | 基于掌握度与留存状态确定唯一最高优先级行动（攻克薄弱/间隔复习/靶向微练）。 |
| **自适应评测**| **Quiz (知识点微测验)** | 完整 (题库脱敏/权威判题) | 完整 (独立状态机组件) | 完整联调 | P0 | **COMPLETE** | 题库脱敏、选项判定、防重复提交、解析反馈与客户端计时（`time_spent_ms > 0`）完整。 |
| **行为追溯** | **Learning Event (行为事件日志)** | 完整 (JSONL 追加写/RLock) | 完整 (伴随作答自动沉淀) | 完整 (落盘可测) | P0 | **COMPLETE** | 答题与行为事件自动沉淀至 `data/learning_events.jsonl`，作为生产事实源。 |
| **认知追踪** | **BKT (贝叶斯掌握度追踪)** | 完整 (4参数/幂等回放/状态更新) | 完整 (数值与等级动态联动) | 完整闭环 | P0 | **COMPLETE** | 四参数闭式方程计算，单调落盘事实，提供唯一客观掌握概率 $P(L)$。 |
| **自适应重规划**| **Path Replanning (动态路径流转)** | 完整 (1-hop 决策核心/Canonical) | 完整 (五层自适应反馈/即时解锁) | 完整闭环 | P0 | **COMPLETE** | 答题达标后由 1-hop 决策引擎触发下游解锁，驱动焦点任务即时平滑流转。 |
| **原生资源** | **Resource Hub (原生资源中心)** | 完整 (130项原生学习材料) | 完整 (分类筛选/自适应推荐) | 完整联调 | P0 | **COMPLETE** | 覆盖 30 考点共 130 项内部原生资源（概念微卡、典型例题深度剖析、靶向微练）。 |
| **名校MOOC** | **MOOC Catalog (精选名校微课)** | 完整 (12项权威微课/白名单) | 完整 (安全跳转免责弹窗) | 完整联调 | P0 | **COMPLETE** | 北大/武大 12 项真实微课；其余 18 考点如实标记无外链由原生资源覆盖；零虚构。 |
| **学习闭环** | **Learning Session (会话产品化)** | 完整 (SessionService/状态机) | 完整 (5步微时序会话看板) | 完整闭环 | P0 | **COMPLETE** | 导引 ➔ 概念微卡 ➔ 精选材料 ➔ 随堂微测 ➔ 成果结算，服务端原子快照隔离。 |
| **效果验证** | **Effectiveness Feedback (成效反馈)** | 完整 (重读BKT计算ΔP(L)) | 完整 (核心完成卡片/时间叙事) | 完整闭环 | P0 | **COMPLETE** | 4 档确定性效果映射，人本时间关联反馈，引导再练一道或新一轮学习。 |
| **推荐自适应**| **Resource Strategy Adaptation** | 完整 (DeterministicStrategy) | 完整 (为什么推荐/成效优选徽章) | 完整闭环 | P0 | **COMPLETE** | 基于历史成效确定性 +2/+1/0/-1 微调排序，展示人本推荐理由与温和换方式建议。 |
| **智能伴学** | **AI Companion (伴学副驾)** | 完整 (DeepSeek/离线启发双模) | 完整 (问答抽屉/引导动作/自测) | 完整对齐 | P0 | **COMPLETE** | 白名单投影上下文、零生产决策权、快捷追问 (Guided Actions) 与快速自测 (Quick Check)。 |
| **教师中台** | **Teacher Web (教师教学中台)** | 完整 (Overview/Knowledge/Students) | 完整 (3-Tab架构/诊断抽屉/干预) | 完整闭环 | P0 | **COMPLETE** | 班级宏观分析、30考点全景分析与错因诊断抽屉、学生全维档案下钻、3类教学干预。 |
| **离线应用** | **PWA Shell (渐进式 Web 应用)** | 完整 (Manifest/Service Worker) | 完整 (安装引导条/移动容器) | 完整联调 | P1 | **COMPLETE** | 符合 PWA 安装标准，独立应用窗口模式，`/api/*` 强制 Network-Only 策略防脏读。 |
| **历史复盘** | **Wrong Answers Book (错题复盘)** | 完整 (错题索引与详情) | 完整 (错题列表/靶向练习) | 完整联调 | P0 | **COMPLETE** | 学生端独立错题本，支持根据错题直接唤起对应考点的靶向练习。 |

---

## 二、能力层级对比总结 (Capability Level Summary)

### 达到【端到端完整体验 (COMPLETE)】的核心能力：
1. **多维学生画像与学情看板**：支持 S001~S005 五名学生完整画像切换与雷达图评测；学生端/教师端角色双端隔离。
2. **微观经济学 30 考点拓扑图谱**：30 个微观经济学考点、42 条依赖边，React Flow 拓扑交互与掌握度动态着色。
3. **分考点微测验交互**：开题、作答、计时、权威判题、防重复提交互斥锁与解析反馈。
4. **今日学习行动调度 (Today Action)**：结合考点拓扑与留存记忆曲线，动态计算学生今日首要行动任务。
5. **双源学习资源中心 (Resource Hub)**：130 项内部原生材料 + 12 项精选名校 MOOC 微课（带安全跳转免责弹窗）。
6. **5 步学习会话看板 (Learning Session)**：导引 ➔ 概念微卡 ➔ 精选材料 ➔ 随堂微测 ➔ 成果结算，连续闭环推进。
7. **学习效果验证闭环 ($\Delta P(L)$)**：服务端权威重读 BKT 状态计算掌握度净增量，4 档分级，人本导师时间关联叙事反馈。
8. **资源策略二次微调 (Deterministic Strategy Adaptation)**：根据学生过去使用材料的真实效果，确定性 +2/+1/0/-1 微调排位，展示「💡 为什么推荐？」与「🔄 这次换一种方式试试」。
9. **AI 伴学副驾与事实对齐 (Grounded AI Companion)**：接入 DeepSeek 官方大模型（具备离线启发式安全兜底），支持材料上下文感知提问、快捷追问与即时自测，杜绝生产决策越权。
10. **教师端观察与干预中台 (Teacher Web)**：班级宏观分析、30 考点全景分析与错因诊断抽屉、学生全维档案下钻、3 类干预动作发起与记录。
11. **PWA 离线外壳**：Web App Manifest 与 Service Worker 完备，支持桌面与手机端独立安装。

---

## 三、工程质量门禁与自动化测试基线 (Quality Gate Baseline)

系统建立全方位的全自动自动化测试与多层质量门禁体系：

| 门禁层级 (Gate) | 检验目标 | 校验命令 | 验证资产规模 | 判定标准 |
| :--- | :--- | :--- | :--- | :--- |
| **Final Integration Gate** | 端到端产品整合与全功能链路门禁 | `python scripts/sprint10c_final_integration_gate.py` | 25 项全链路核验点 | **25/25 CHECKS GREEN (100%)** |
| **Root Quality Gate** | 五大核心架构与冻结守护门禁 | `python scripts/quality_gate.py` | 5 大核心门禁 | **5/5 GATES PASSED (100%)** |
| **Backend Gateway Tests** | 网关 API、伴学、会话、资源、MOOC与教师中台 | `pytest gateway/tests/ -q` | 608 项用例 (606 运行, 2 跳过) | **606/606 PASSED (100%)** |
| **Backend Root Tests** | 核心领域 BKT、DAG 与 Golden E2E 测试 | `pytest tests/ -q` | 143 个核心测试 | **143/143 PASSED (100%)** |
| **Backend Total Tests** | 后端全量测试组合基线 | `pytest tests/ -q && pytest gateway/tests/ -q` | 749 个通过测试 (2 skipped) | **749/749 PASSED (100%)** |
| **Frontend Contract Tests** | 前端组件契约、模型与自适应集成测试 | `npm test --prefix frontend` | 469 个契约测试 (104 Suites) | **469/469 PASSED (100%)** |
| **Frontend Type Safety** | 静态强类型安全性 | `npm run typecheck --prefix frontend` | 整个前端工程 (`tsc -b`) | **0 TS errors** |
| **Frontend Production Build** | Vite 静态打包编译 | `npm run build --prefix frontend` | 生产分发包 (`dist/`) | **构建成功无错误** |
