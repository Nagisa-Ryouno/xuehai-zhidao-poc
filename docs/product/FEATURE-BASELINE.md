# 学海智导 (Xuehai Zhidao) V2 功能基线盘点 (Feature Baseline)

> **版本**：Phase 5 / Sprint 9-E Baseline  
> **更新时间**：2026-09-16  
> **审计基线 Commit**：`2a3ece6 feat(learning): add resource strategy adaptation`  
> **状态标注原则**：严格区分 **Backend Capability**、**Frontend Experience** 与 **End-to-End Capability**，不因存在后台 service 即宣称功能完成。

---

## 一、核心功能矩阵 (Feature Matrix)

| 业务领域 | 核心功能 (Feature) | 后端状态 (Backend) | 前端状态 (Frontend) | 端到端闭环 (E2E) | 优先级 | 当前总体状态 (Status) | 现状说明与体验边界 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **学生学情** | **Student Profile (多维画像)** | 完整 (API + Repo) | 完整 (ProfileCard) | 完整联调 | P0 | **COMPLETE** | 支持 S001~S005 五名典型学生画像数据，雷达图、基础信息与多维评估展示完整。 |
| **学生学情** | **Dashboard (学情聚合)** | 完整 (聚合 Service) | 完整 (双端 Layout) | 完整联调 | P0 | **COMPLETE** | 学生端/教师端角色无缝切换，聚合卡片、薄弱点列表与最近任务一览完整。 |
| **学情诊断** | **Reports (综合学情报告)** | 完整 (5份只读报告) | 完整 (AIDiagnosis/Summary) | 完整联调 | P0 | **COMPLETE** | 维度拆解、成绩分布、优势与薄弱考点分析完整呈现。 |
| **拓扑导学** | **Knowledge Graph (知识图谱)** | 完整 (30节点/42边/纯JSON) | 完整 (React Flow 拓扑交互) | 完整联调 | P0 | **COMPLETE** | 节点依据 BKT 掌握度动态着色，点击节点弹出详情抽屉，前置/后继关系高亮。 |
| **动态路径** | **Dynamic Path (动态路径排期)** | 完整 (DynamicPathGenerator) | 完整 (FocusCard/PathStep) | 完整联调 | P0 | **COMPLETE** | 基于 DAG 拓扑、前置约束与当前掌握度动态计算焦点节点与推荐队列。 |
| **自适应评测**| **Quiz (知识点微测验)** | 完整 (题库脱敏/权威判题) | 完整 (独立状态机组件) | 完整联调 | P0 | **COMPLETE** | 题库脱敏、选项判定、防重复提交、解析反馈与客户端计时（`time_spent_ms > 0`）完整。 |
| **行为追溯** | **Learning Event (行为事件日志)** | 完整 (JSONL 追加写/RLock) | 完整 (伴随作答自动沉淀) | 完整 (落盘可测) | P0 | **COMPLETE** | 答题与行为事件自动沉淀至 `data/learning_events.jsonl`，作为生产事实源。 |
| **认知追踪** | **BKT (贝叶斯掌握度追踪)** | 完整 (4参数/幂等回放/状态更新) | 完整 (数值与等级动态联动) | 完整闭环 | P0 | **COMPLETE** | 四参数闭式方程计算，单调落盘事实，提供唯一客观掌握概率 $P(L)$。 |
| **自适应重规划**| **Path Replanning (动态路径流转)** | 完整 (1-hop 决策核心/Canonical) | 完整 (五层自适应反馈/即时解锁) | 完整闭环 | P0 | **COMPLETE** | 答题达标后由 1-hop 决策引擎触发下游解锁，驱动焦点任务即时平滑流转。 |
| **学习资源** | **Resource Hub (资源中心)** | 完整 (130项原生学习材料) | 完整 (分类筛选/自适应推荐) | 完整联调 | P0 | **COMPLETE** | 覆盖 30 考点共 130 项内部资源（概念微卡、典型例题深度剖析、靶向微练）。 |
| **学习闭环** | **Learning Session (4步会话)** | 完整 (SessionService/状态机) | 完整 (4步微时序进度看板) | 完整闭环 | P0 | **COMPLETE** | 考点精要 ➔ 典型例题 ➔ 靶向微练 ➔ 检验掌握度，服务端原子快照隔离。 |
| **效果验证** | **Effectiveness Feedback (成效反馈)** | 完整 (重读BKT计算ΔP(L)) | 完整 (核心完成卡片/时间叙事) | 完整闭环 | P0 | **COMPLETE** | 4 档确定性效果映射，人本时间关联反馈，引导再练一道或新一轮学习。 |
| **推荐自适应**| **Resource Strategy Adaptation** | 完整 (DeterministicStrategy) | 完整 (为什么推荐/成效优选徽章) | 完整闭环 | P0 | **COMPLETE** | 基于历史成效确定性 +2/+1/0/-1 微调排序，展示人本推荐理由与温和换方式建议。 |
| **智能导学** | **AI Assistant (伴学副驾)** | 完整 (白名单上下文/规则兜底) | 完整 (问答抽屉/引导动作/自测) | 完整对齐 | P0 | **COMPLETE** | 支持学生专属问候语、材料上下文提问、快捷追问 (Guided Actions) 与快速自测 (Quick Check)。 |
| **教师决策** | **Teacher Cockpit (教师决策看板)** | 完整 (只读聚合服务) | 完整 (班级概览/风险雷达) | 完整联调 | P0 | **COMPLETE** | 班级宏观平均掌握度、高危薄弱考点预警、学生个体多维风险雷达与一键干预建议。 |
| **历史复盘** | **Wrong Answers Book (错题复盘)** | 完整 (错题索引与详情) | 完整 (错题列表/靶向练习) | 完整联调 | P0 | **COMPLETE** | 学生端独立错题本，支持根据错题直接唤起对应考点的靶向练习。 |

---

## 二、能力层级对比总结 (Capability Level Summary)

### 达到【端到端完整体验 (COMPLETE)】的核心能力：
1. **多维学生画像与学情看板**：支持 S001~S005 五名学生完整画像切换与雷达图评测；学生端/教师端角色双端隔离。
2. **微观经济学 30 考点拓扑图谱**：30 个微观经济学考点、42 条依赖边，React Flow 拓扑交互与掌握度动态着色。
3. **分考点微测验交互**：开题、作答、计时、权威判题、防重复提交互斥锁与解析反馈。
4. **自适应学习资源中心 (Resource Hub)**：130 项内部原生材料（概念微卡、典型例题剖析、靶向微练），支持按类型与考点自适应推荐与检索。
5. **4 步学习会话看板 (Learning Session)**：考点微卡 ➔ 例题剖析 ➔ 靶向微练 ➔ 检验掌握度，服务端记录初始快照。
6. **学习效果验证闭环 ($\Delta P(L)$)**：服务端权威重读 BKT 状态计算掌握度净增量，4 档分级，人本导师时间关联叙事反馈。
7. **资源策略二次微调 (Deterministic Strategy Adaptation)**：根据学生过去使用材料的真实效果，确定性 +2/+1/0/-1 微调排位，展示「💡 为什么推荐？」与「🔄 这次换一种方式试试」。
8. **AI 伴学副驾与事实对齐 (Grounded AI Companion)**：接入 `LearningContext` 统一上下文，支持材料上下文感知提问、快捷追问与即时微测自测，杜绝一切伪造解锁。
9. **教师决策分析中心 (Teacher Cockpit)**：班级宏观分析、高危考点统计、学生风险雷达与一键干预建议。

---

## 三、工程质量门禁与自动化测试基线 (Quality Gate Baseline)

系统建立全方位的全自动自动化测试与多层质量门禁体系：

| 门禁层级 (Gate) | 检验目标 | 校验命令 | 验证资产规模 | 判定标准 |
| :--- | :--- | :--- | :--- | :--- |
| **Sprint 9-E Quality Gate** | 资源自适应排序与 5 档微调策略门禁 | `python scripts/sprint9e_quality_gate.py` | 9 大专项核验点 | **9/09 CHECKS GREEN (100%)** |
| **Sprint 9-D Quality Gate** | 学习效果验证与会话闭环门禁 | `python scripts/sprint9d_quality_gate.py` | 12 大专项核验点 | **12/12 CHECKS GREEN (100%)** |
| **Sprint 9-C Quality Gate** | 30 考点 130 项资源库与推荐门禁 | `python scripts/sprint9c_quality_gate.py` | 12 大专项核验点 | **12/12 CHECKS GREEN (100%)** |
| **Root Quality Gate** | 五大核心架构与冻结守护门禁 | `python scripts/quality_gate.py` | 5 大核心门禁 | **5/5 GATES PASSED (100%)** |
| **Backend Gateway Tests** | 网关 API、伴学、会话、资源与策略测试 | `pytest gateway/tests/ -v` | 415 个自动化测试 | **415/415 PASSED (100%)** |
| **Backend Root Tests** | 核心领域 BKT、DAG 与 Golden E2E 测试 | `pytest tests/ -q` | 143 个核心测试 | **143/143 PASSED (100%)** |
| **Frontend Contract Tests** | 前端组件契约、模型与自适应集成测试 | `npm test --prefix frontend` | 242 个契约测试 (54 Suites) | **242/242 PASSED (100%)** |
| **Frontend Type Safety** | 静态强类型安全性 | `npm run typecheck --prefix frontend` | 整个前端工程 | **0 TS errors** |
| **Frontend Production Build** | Vite 静态打包编译 | `npm run build --prefix frontend` | 生产分发包 (`dist/`) | **构建成功无错误** |
| **Browser End-to-End UAT** | Chromium 真实浏览器端到端旅程 | `python scripts/uat_sprint9e_browser.py` | 6 大场景自动化脚本 | **6/6 PASSED (100%)** |
