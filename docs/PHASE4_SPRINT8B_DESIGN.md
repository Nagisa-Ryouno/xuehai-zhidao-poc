# Phase 4 / Sprint 8-B 详细设计白皮书
## Dynamic Learning Path & Diagnostic Intelligence
### 动态学习路径规划、极速学情诊断与知识图谱自适应航线

**项目名称**：学海智导（Xuehai Zhidao）  
**阶段**：Phase 4 / Sprint 8-B  
**版本**：v1.0  
**状态**：已实现并通过 12/12 专项质量门禁  

---

## 1. 架构目标与背景

在 Sprint 8-A 中，学海智导成功打通了轻量级闭环救生体系（`新学生 -> 设定目标 -> 今日任务 -> 概念微卡 -> 微测验 -> BKT演进 -> 路径重规划 -> 下游解锁`）。然而，原系统中的候选路径主要依赖于静态离线预置的 `learning_paths.json` 切片，尚未形成基于知识图谱全貌与学情诊断的实时动态航线。

**Sprint 8-B 的核心使命**：
> 将学海智导从依赖静态路径切片，全面升级为**由知识图谱拓扑、学生当前 BKT 认知状态、前置依赖硬约束、学习目标以及 3 题极速前测共同驱动的确定性自适应学习航线系统**。

```text
                        ┌───────────────────────────────┐
                        │   学习目标设定 (Goal Setting)    │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │    3题极速前测 (Rapid Pre-test)│
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │   学情诊断评估 (Diagnostic)    │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │  确定性自适应动态路径生成器     │
                        │  (KG + BKT + Prereq + Goal)   │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │  知识图谱航线高亮与时序流动边  │
                        │   (CURRENT / NEXT / UPCOMING) │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │  锁定当前焦点任务 (Focus Card) │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │   概念微卡先学 -> 微测验练习  │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │  BKT 演进 -> 动态航线即时重算 │
                        └───────────────────────────────┘
```

---

## 2. 六大架构决议与红线落实

根据工程指令，本 Sprint 严格落实了 6 项修正与红线：

1. **复用统一 Mastery 判定语义，绝不制造第二套标准**：
   - 严格复用项目权威常量 `MASTERY_THRESHOLD_HIGH = 0.80` 与 `is_knowledge_mastered`。
   - 考点掌握度 $\ge 0.80$ 判定为已掌握，$< 0.80$ 判定为未掌握。
2. **Top-3 航线长度上限约束 ($0 \le route\_length \le 3$)**：
   - 拓扑硬约束优先于航线长度。
   - 绝不强塞未就绪的锁定节点来凑满 3 站。若学生全掌握，输出 $route\_length = 0$。
3. **前测诊断估计 $\ne$ 正式 BKT 认知状态**：
   - 3 题前测仅输出客观诊断报告 `DiagnosticResult` 与初始掌握度预估。
   - 绝不向正式 `EventRepository` 写入 `QUESTION_ATTEMPT` 事件，绝不直接篡改正式 BKT 仓储。
4. **决策确定性排除元数据时间戳**：
   - 评估幂等与确定性时，严格基于决策字段（`knowledge_id`, `rank`, `role`, `score`, `reason_codes`, `explanation`），排除 `generated_at`。
5. **安全降级防线 (Safe Fallback)**：
   - 遇到未预料数据异常时，安全回退至当前学生可达的 `PathState` 序列并标明 `is_fallback = True`，绝不抛出 500。
6. **核心目录绝对冻结不变**：
   - `app/`、`tests/`、`data/seeds/` 严格维持 0 diff。所有新能力均收敛于 `gateway/learning/`、`gateway/api.py` 与 `frontend/`。

---

## 3. 核心子系统实现细节

### 3.1 极速前测与学情诊断引擎 (`gateway/learning/diagnostic/`)

- **3 题跨拓扑确定性选题策略** (`select_diagnostic_question_ids`)：
  - 针对弹性与税收目标：精选 `Q-K02-01` (机会成本) $\to$ `Q-K04-01` (需求定理) $\to$ `Q-K08-01` (需求价格弹性)。
  - 针对市场供求目标：精选 `Q-K01-01` (稀缺性) $\to$ `Q-K04-01` (需求定理) $\to$ `Q-K06-01` (市场均衡)。
  - 默认微观经济学目标：精选 `Q-K01-01` $\to$ `Q-K02-01` $\to$ `Q-K04-01`。
  - 100% 确定性、覆盖 3 个独立节点、严格前置保序。
- **公开模型数据脱敏** (`DiagnosticQuestionPublic`)：
  - 公开端点绝不向前端泄漏 `answer` 或 `explanation`。
- **多维学情诊断** (`evaluate_pretest`)：
  - 综合评价等级划分：
    - 3 题全对：`SOLID_FOUNDATION`（稳固基础）
    - 对 1~2 题：`PARTIAL_FOUNDATION`（部分掌握）
    - 0 题全错：`NEEDS_REMEDIAL`（亟需巩固）
  - 单考点诊断详情：记录 `is_correct`, `estimated_mastery`, `weaknesses`, `strengths`, `feedback`。

### 3.2 动态自适应路径生成器 (`gateway/learning/path_generation/`)

- **多因子综合评分模型** (`calculate_node_priority`)：
  $$\text{PriorityScore} = 0.35 \times \text{WeaknessScore} + 0.25 \times \text{TargetRelevance} + 0.20 \times \text{PrerequisiteReadiness} + 0.10 \times \text{PathAvailability} + 0.10 \times \text{DiagnosticPriority}$$
  - **WeaknessScore** ($35\%$): $1.0 - \text{mastery}$，认知越薄弱攻坚权重越高；
  - **TargetRelevance** ($25\%$): 处于学习目标直接推导祖先链上为 $1.0$，同章节为 $0.5$，其余为 $0.1$；
  - **PrerequisiteReadiness** ($20\%$): 前置依赖全部掌握为 $1.0$，未掌握为 $0.0$；
  - **PathAvailability** ($10\%$): `IN_PROGRESS` 为 $1.0$，`AVAILABLE` 为 $0.8$，`LOCKED` 为 $0.0$；
  - **DiagnosticPriority** ($10\%$): 前测发现薄弱盲区为 $1.0$，中性为 $0.5$，已掌握为 $0.3$。
- **前置知识绝对霸权硬约束 (Prerequisite Supremacy)**：
  - 任何节点如果存在未掌握的前置依赖，**绝对禁止排在该前置节点之前**。
  - 第 1 站（CURRENT）的前置依赖必须全部已掌握或为空，保证学生立刻具备可学性。
- **确定性 Tie-Break 规则**：
  - 当得分完全相同时，按照 `(-score, chapter_index, difficulty, knowledge_id)` 排序，确保多次生成结果字节级一致。

### 3.3 知识图谱航线叠加与流动高亮 (`gateway/learning/graph/`)

- **航线角色徽章**：
  - `CURRENT`：第 1 站 · 当前焦点（翡翠绿光晕与呼吸动效）；
  - `NEXT`：第 2 站 · 紧接学习（琥珀金高亮）；
  - `UPCOMING`：第 3 站 · 进阶延伸（浅紫预备）。
- **时序流动高亮边 (`routeEdge`)**：
  - 连接第 1 站 $\to$ 第 2 站 $\to$ 第 3 站，具有 `animated: true`、带箭头的加粗虚线流动动画。
- **原有图谱完整性保护**：
  - 底层 30 节点与 42 条前置依赖边的原始拓扑属性完全保留，绝无破坏性变更。

---

## 4. API 端点列表

统一在 `gateway/api.py` 中挂载：

| HTTP 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| `POST` | `/api/diagnostic/pretest` | 创建 3 题极速前测会话（脱敏，剔除答案与解析） |
| `POST` | `/api/diagnostic/pretest/{session_id}/submit` | 提交前测作答，评估学情并即时生成首条自适应动态路线 |
| `GET` | `/api/path/dynamic/{student_id}` | 获取指定学生的 Top-3 动态自适应学习路线 |
| `GET` | `/api/path/dynamic/{student_id}/explanation` | 获取动态路线的结构化推荐理由与证据说明 |
| `GET` | `/api/students/{student_id}/knowledge-graph/dynamic` | 获取叠加了航线高亮与流动动画的知识图谱数据 |

---

## 5. 质量门禁与验证汇总

### 5.1 自动化测试覆盖

- **Sprint 8-B 专属测试套件**：
  - `test_sprint8b_diagnostic.py`: 7/7 PASS
  - `test_sprint8b_dynamic_path.py`: 12/12 PASS
  - `test_sprint8b_graph_route.py`: 5/5 PASS
  - `test_sprint8b_product_loop.py`: 1/1 PASS
  - **小计：25/25 PASS**
- **Frontend 验证**：
  - `npm run typecheck`: 0 errors
  - `npm test`: 172/172 PASS
  - `npm run build`: 生产打包成功
- **Sprint 8-B 专属 Quality Gate** (`scripts/sprint8b_dynamic_path_gate.py`)：
  - 12/12 项硬核检查全部通过。
- **目录冻结检查**：
  - `git diff --stat -- app/ tests/ data/seeds/`：严格 0 diff。
