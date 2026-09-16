# Phase 5 / Sprint 9-E 封版交付报告与演练指南 (Walkthrough)

**项目名称**：学海智导 (Xuehai Zhidao) — AI驱动的大学生个性化学习指导平台  
**当前阶段**：Phase 5 — AI Companion & Intelligent Study Assistance  
**Sprint 周期**：Sprint 9-E — 学习保持度验证与资源策略自适应 Lite (Learning Retention & Resource Strategy Adaptation Lite)  
**交付时间**：2026-09-16  
**基线提交**：`7008cee` (Sprint 9-D 封版基线 `feat(learning): add learning effectiveness feedback`)  

---

## 一、Sprint 9-E 交付目标与核心使命

在 Sprint 9-C 与 Sprint 9-D 中，系统建立了覆盖 30 个考点（130 项内部资源）的学习资源库、确定性推荐引擎，以及打通了“资源学习 ➔ 靶向微练 ➔ 权威掌握度变化 ➔ 4 档学习效果验证”的完整闭环。

然而，传统的静态规则推荐每次都千篇一律，不会根据学生历史上的真实表现进行自我进化。

Sprint 9-E 的目标是一个**小型增量式闭环升级**：
> **「根据学生过去使用不同资源后产生的真实学习效果，确定性地调整下一次资源推荐顺序，并以人本导师口吻向学生阐明推荐原因。」**

最终实现：
```text
当前学习状态 / 前置条件
        ↓
现有 ResourceResolver
        ↓
得到合法候选资源池
        ↓
读取真实历史资源效果 (data/resource_effectiveness_events.jsonl)
        ↓
确定性 +2/+1/0/-1 微调加权
        ↓
候选池内部重新稳定排序
        ↓
展示“为什么这样推荐”与温和尝试新策略建议
```

**本 Sprint 严格控制工程量，坚守以下边界：**
- ❌ 不做大型推荐系统，不引入协同过滤。
- ❌ 不引入任何机器学习 (ML) 与模型训练。
- ❌ 不引入向量数据库 (Vector DB)。
- ❌ 不新增任何数据库（MySQL/PostgreSQL 等）。
- ❌ 不让 LLM 决定推荐排序。
- ❌ 严禁出现任何技术黑话（如 BKT、P(L)、Vector、Score 等）。

---

## 二、双层架构与闭环流转

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   学生端 (Student UI)                                   │
│   今日任务 (Tasks) / 学习资源中心 (ResourceHub) / 知识图谱 (Graph) / 学情档案 (Profile)    │
└───────────────────────────┬────────────────────────────────────────────────────────────┘
                            │ (请求自适应资源推荐 GET /api/learning/resources/recommendations)
                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          网关与自适应资源服务 (Gateway Layer)                             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. ResourceResolver: 基于当前掌握度 & 前置条件解析合法候选资源池                          │
│ 2. ResourceEffectivenessAggregator: 只读解析 data/resource_effectiveness_events.jsonl  │
│    - 计算学生各资源类型的平均掌握度净增量 avg_delta 与使用频次 usage_count              │
│    - 确定性 5 档分级: VERY_EFFECTIVE / EFFECTIVE / NEUTRAL / INEFFECTIVE / INSUFFICIENT│
│ 3. DeterministicAdaptationStrategy: 确定性二次微调重排序                               │
│    - 基础分: base_score = 100.0 - (original_order - 1) * 5.0                           │
│    - 调整分: VERY_EFFECTIVE(+2), EFFECTIVE(+1), NEUTRAL(0), INEFFECTIVE(-1), 缺数(0)    │
│    - 最终分: final_score = base_score + score_adjustment * 10.0                       │
│    - 稳定排序: (-final_score, original_order)                                          │
│    - 生成人本推荐理由: 💡 为什么推荐？ / 🔄 这次换一种方式试试                          │
└───────────────────────────┬────────────────────────────────────────────────────────────┘
                            │ (只读读取 BKT 权威掌握度与历史事件)
                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        底层权威学习引擎与持久化 (Single Source of Truth)                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ • 生产决策唯一事实源: data/bkt_states.json (严禁修改，0 diff)                           │
│ • 正式学习事件日志: data/learning_events.jsonl (严禁写入，0 diff)                       │
│ • 知识图谱依赖 DAG: data/seeds/knowledge_graph.json (严格冻结，0 diff)                  │
│ • 资源效果遥测日志: data/resource_effectiveness_events.jsonl (只读聚合)                │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心设计原则与安全红线实施

1. **架构冻结目录绝对 0 差异 (Zero Diff)**：
   - 核心领域与迁移目录 `app/`、`tests/`、`data/seeds/` 严格保持 0 diff（`git diff --stat HEAD -- app/ tests/ data/seeds/` 输出严格为空）。
   - 严禁修改底层 BKT 模型 `bkt_service.py`、`path_state_service.py`、`dynamic_path_generator.py`。
2. **纯确定性与稳定排序**：
   - 相同历史输入下，排序结果与推荐理由字节级完全确定，排序使用 Python 稳定排序 `(-final_score, original_order)`，同分严格保持原始合法推荐顺序。
3. **数据不足优雅回退 (Insufficient Data Fallback)**：
   - 当历史使用记录不足 2 次时，判定为 `INSUFFICIENT_DATA`，`score_adjustment = 0`，保持原有排位，展示标准推荐理由，绝不捏造虚假成效。
4. **效果欠佳温和引导 (Try Alternative)**：
   - 当某类资源历史效果为 `INEFFECTIVE` 时，`score_adjustment = -1` 降序，并展示人本卡片「🔄 这次换一种方式试试」，鼓励学生尝试其他更适合的学习形式。
5. **人本导师叙事与零技术黑话 (No Jargon)**：
   - 界面上仅展示符合学生直觉的引导卡片与徽章：`💡 为什么推荐？`、`成效优选 (+2)`、`温和提升 (+1)`、`这次换一种方式试试`。
   - 杜绝任何工程黑话（如 BKT、P(L)、Vector、Score、Bayesian、Adjustment 等）。
6. **多学生画像物理隔离**：
   - S001（概念卡效果好）与 S002（例题效果好）在相同考点（如 K08）下获得完全不同的差异化排序与推荐理由，跨学生状态绝不串扰。
7. **移动端自适应与零横向滚动条**：
   - 完美适配 375px 窄视口，卡片徽章与文案自适应折行，无水平溢出滚动条。

---

## 四、确定性策略分级与微调加权矩阵

| 历史效果等级 | 触发条件 (usage_count >= 2) | 加分系数 | 界面标签 | 人本推荐理由 (why_recommended) |
| :--- | :--- | :--- | :--- | :--- |
| **VERY_EFFECTIVE** | $\text{avg\_delta} \ge +0.10$ | **+2** | 成效优选 (+2) | 你之前学习这类材料时理解提升最快，优先推荐继续使用。 |
| **EFFECTIVE** | $+0.02 \le \text{avg\_delta} < +0.10$ | **+1** | 温和提升 (+1) | 历史学习显示这种材料对你掌握该考点很有帮助。 |
| **NEUTRAL** | $-0.02 \le \text{avg\_delta} < +0.02$ | **0** | - | 围绕当前考点循序渐进，适合巩固基础。 |
| **INEFFECTIVE** | $\text{avg\_delta} < -0.02$ | **-1** | 这次换一种方式试试 | 你上次在类似材料中遇到过阻碍，建议换一种材料突破，也可以尝试概念卡。 |
| **INSUFFICIENT_DATA** | $\text{usage\_count} < 2$ | **0** | - | 根据当前掌握度为你推荐的核心学习材料。 |

---

## 五、前后端全栈交付资产清单

### 5.1 后端模块 (`gateway/learning/resource_effectiveness/`)
- `models.py`：定义 `HistoricalEffectiveness` 枚举（5 档）、`classify_effectiveness` 分类函数、`ResourceEffectivenessProfile`、`EffectivenessProfileResponse`。
- `aggregator.py`：`ResourceEffectivenessAggregator` 只读 JSONL 解析器，支持别名容错、非致命错误跳过与按学生分组统计。
- `strategy.py`：`DeterministicAdaptationStrategy` 确定性微调引擎，实现基础分、微调分计算与稳定排序及理由映射。
- `gateway/learning/resources/models.py`：`ResourceRecommendation` 扩展 `historical_effectiveness`、`why_recommended`、`score_adjustment` 字段。
- `gateway/learning/resources/resolver.py`：集成聚合器与策略引擎，无缝输出二次微调后的自适应资源列表。
- `gateway/api.py`：挂载新端点 `GET /api/learning/resources/effectiveness-profile/{student_id}`（放置在 `{knowledge_id}` 之前避免路由冲突）。

### 5.2 前端模块 (`frontend/src/`)
- `types.ts` & `api.ts`：增加 Sprint 9-E 类型与 `getResourceEffectivenessProfile` API 调用。
- `components/student/ResourceHub.tsx`：
  - 为推荐资源卡片添加 `data-testid="recommended-resource-card"`。
  - 渲染「💡 为什么推荐？」人本理由气泡。
  - 针对 `VERY_EFFECTIVE` / `EFFECTIVE` 渲染「成效优选」紫色高亮标签。
  - 针对 `INEFFECTIVE` 渲染「🔄 这次换一种方式试试」温和引导卡片。
  - 针对 `INSUFFICIENT_DATA` 保持自然兜底理由，不作夸大声明。

---

## 六、质量门禁与全量测试验证

### 6.1 全量自动化测试套件
1. **后端专用自适应策略测试**：
   - `pytest gateway/tests/test_sprint9e_resource_adaptation.py -v`：**17/17 PASSED**。
2. **后端全量回归测试**：
   - `pytest gateway/tests/ -v`：**415/415 PASSED**（Phase 2 ~ Sprint 9-E 所有网关测试）。
   - `pytest tests/ -q`：**143/143 PASSED**（根目录核心权威测试）。
   - **后端测试总计**：**558/558 PASSED (100%)**。
3. **前端专用契约测试**：
   - `frontend/test/sprint9e_resource_adaptation.test.ts`：**8/8 PASSED**。
4. **前端全量契约测试**：
   - `npm test --prefix frontend`：**242/242 PASSED**（54 suites，0 errors）。
5. **前端生产构建与类型检查**：
   - `npm run typecheck --prefix frontend`：**0 错误**。
   - `npm run build --prefix frontend`：**Vite 构建成功**。

### 6.2 质量门禁执行结果
- `python scripts/sprint9e_quality_gate.py`：**9/09 CHECKS GREEN (100%)**。
- `python scripts/sprint9d_quality_gate.py`：**12/12 CHECKS GREEN (100%)**。
- `python scripts/sprint9c_quality_gate.py`：**12/12 CHECKS GREEN (100%)**。
- `python scripts/quality_gate.py`：**5/5 GATES PASSED (100%)**。

### 6.3 Playwright 真实浏览器端到端 UAT 验证
脚本 `scripts/uat_sprint9e_browser.py` 自动化执行并通过全部 6 个用户真实旅程场景，0 控制台错误，0 失败请求：

| 场景编号 | 场景标题 | 验证要点 | 留存截图路径 |
| :--- | :--- | :--- | :--- |
| **A** | 自适应资源排序生效 | 验证高成效资源（CONCEPT_CARD）成功晋升至首位，卡片具有 `data-testid="recommended-resource-card"` | `artifacts/uat_screenshots/sprint9e_01_resource_hub_adaptive_ranking.png` |
| **B** | 展示「💡 为什么推荐？」与标签 | 验证首位卡片包含推荐理由气泡与「成效优选 (+2)」徽章，杜绝黑话 | `artifacts/uat_screenshots/sprint9e_02_why_recommended_badge_and_narrative.png` |
| **C** | 效果欠佳资源展示「这次换一种方式试试」 | 针对效果较差的习题材料降权并展示温和替代建议卡片 | `artifacts/uat_screenshots/sprint9e_03_ineffective_try_alternative_card.png` |
| **D** | 数据不足资源展示默认理由 | 对未学或使用不足 2 次考点展示标准推荐理由，不捏造数据 | `artifacts/uat_screenshots/sprint9e_04_insufficient_data_graceful_fallback.png` |
| **E** | 多学生自适应排序隔离 | 切换 S001 与 S002，在考点 K08 下验证推荐顺序与理由完全个性化且互不干扰 | `artifacts/uat_screenshots/sprint9e_05_multi_student_adaptation_isolation.png` |
| **F** | 移动端 375px 布局无溢出 | 验证 375x812 窄视口下推荐徽章与解释气泡正常折行，无横向滚动条 | `artifacts/uat_screenshots/sprint9e_06_mobile_375px_ergonomics_no_overflow.png` |

---

## 七、演练与验证操作指南

### 1. 启动服务
确保本地环境已安装依赖，分别在两个终端启动服务：
```bash
# 终端 1: 启动后端网关服务
python -m uvicorn gateway.api:app --host 127.0.0.1 --port 8011

# 终端 2: 启动前端开发服务器
npm run dev --prefix frontend
```

### 2. 体验自适应推荐与人本理由
1. 打开浏览器访问 `http://127.0.0.1:5173/student/resources`。
2. 顶部考点选择 **K08（需求价格弹性）**，当前学生为 **S001（林峰）**。
3. 观察「自适应推荐材料」卡片列表：
   - 首位卡片为「概念精要」，顶部带有紫色「成效优选 (+2)」徽章。
   - 卡片内嵌人本理由气泡：「💡 为什么推荐？你之前学习这类材料时理解提升最快，优先推荐继续使用。」
   - 往后翻看「靶向微练」卡片，带有温和提示：「🔄 这次换一种方式试试：你上次在类似材料中遇到过阻碍，建议换一种材料突破，也可以尝试概念卡。」
4. 切换考点至未学习过的 **K15**：
   - 观察卡片展示自然的标准理由：「💡 为什么推荐？根据当前掌握度为你推荐的核心学习材料。」无任何夸大虚构。
5. 切换学生至 **S002（苏瑾）**，再返回 **K08**：
   - 观察推荐卡片顺序与理由与 S001 截然不同，完全基于 S002 个体历史生成。
6. 调整浏览器窗口至 375px 宽度，验证页面舒适排版，无水平滚动条。

### 3. 一键运行全量质量门禁与端到端 UAT
```bash
# 运行 Sprint 9-E 端到端浏览器自动化 UAT
python scripts/uat_sprint9e_browser.py

# 运行 Sprint 9-E 专用质量门禁 (9 项自检)
python scripts/sprint9e_quality_gate.py

# 运行全局质量门禁 (5 大门禁)
python scripts/quality_gate.py
```
