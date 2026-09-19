# Phase 5 / Sprint 9-F — 学习保持度验证与间隔复习建议 Lite 交付总览

> **国家级大学生创新创业训练计划项目 · 学海智导 (Xuehai Zhidao)**  
> **阶段**：Phase 5 — Learning Retention & Spaced Review Lite (学习保持度验证与间隔复习建议 Lite)  
> **封版日期**：2026-09-19  
> **Git 提交信息**：`feat(learning): add retention check lite`

---

## 一、Sprint 9-F 核心目标与范围控制

### 1. 核心目标
在 Sprint 9-D（学习效果验证）和 Sprint 9-E（资源推荐策略自适应）已沉淀真实学习记录的基础之上，增加轻量、纯确定性的**学习保持度验证与间隔复习建议**能力：
- 基于学生在某考点的上一次正式学习时间（`latest_learning_at`），结合固定时间间隔规则（`REVIEW_AFTER_DAYS = 3`）；
- 结合当前服务端权威 BKT 掌握度与后续复测表现，确定性评估保持度状态（`RetentionStatus`）；
- 在学习资源中心（ResourceHub）顶部温和呈现「🔄 该复习一下了」或「📘 建议再巩固一下」卡片，并一键联动快速微测，闭环复测并驱动权威 BKT 更新。

### 2. 严格安全红线与架构不变性
- **严格零污染与只读分析**：保持度分析器（`RetentionAnalyzer`）与查询接口绝对只读，绝不修改 `data/bkt_states.json` 与 `data/learning_events.jsonl`；
- **服务端绝对权威**：天数计算、上次学习时间与状态判定 100% 由服务端权威计算，完全忽略前端篡改参数；
- **纯确定性与时间注入**：支持注入固定基准时间（`now`），确保测试 100% 幂等可重复；
- **零新组件引入**：无 Celery/Cron 等后台轮询任务，无 Redis/向量库，无艾宾浩斯等复杂黑盒拟合，无 LLM 决策介入；
- **冻结目录零改动**：`app/`、`tests/`、`data/seeds/` 目录严格保持 0 diff；
- **人本温度与无黑话**：UI 提示严禁出现 BKT、贝叶斯、艾宾浩斯、遗忘曲线、半衰期等底层术语。

---

## 二、状态机与核心业务规则

### 1. 四档确定性状态机 (`RetentionStatus`)

| 状态枚举 | 触发条件 | 建议行动 (`suggested_action`) | UI 表现 |
| :--- | :--- | :--- | :--- |
| **`INSUFFICIENT_DATA`** | 该学生从未完成过该考点的正式学习会话 | `None` | 静默不展示任何提示卡片，保持界面纯净 |
| **`NOT_DUE`** | 距上次学习时间 $< 3$ 天，或复测答对且掌握度已稳固（$< 3$ 天内） | `None` | 静默不展示任何提示卡片，零视觉干扰 |
| **`DUE_FOR_REVIEW`** | 距上次学习时间 $\ge 3$ 天且未在近期完成复测 | 若掌握度 $\ge 0.60$：`RETAKE_QUIZ`<br/>若掌握度 $< 0.60$：`REVIEW_CONCEPT` | 呈现琥珀色温和提醒卡片「🔄 该复习一下了」，引导 1~2 分钟微测 |
| **`NEEDS_REINFORCEMENT`** | 在复习测验中答错（`is_correct == False`）或当前掌握度 $< 0.60$ | `REVIEW_CONCEPT` | 呈现靛蓝色温和巩固卡片「📘 建议再巩固一下」，引导重读概念微卡 |

### 2. 契约模型与数据结构

```python
class RetentionStatus(str, Enum):
    NOT_DUE = "NOT_DUE"
    DUE_FOR_REVIEW = "DUE_FOR_REVIEW"
    NEEDS_REINFORCEMENT = "NEEDS_REINFORCEMENT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class RetentionProfile(BaseModel):
    student_id: str
    knowledge_id: str
    last_learning_at: Optional[datetime]
    days_since_learning: Optional[int]
    current_mastery: Optional[float]
    retention_status: RetentionStatus
    should_review: bool
    suggested_action: Optional[str]  # 严格受 ALLOWED_RETENTION_ACTIONS 白名单约束
```

---

## 三、系统架构与模块实现

```text
       [ 学生访问 /student/resources ]
                     │
                     ▼
          GET /api/learning/retention/{student_id}/{knowledge_id}
                     │
                     ▼
             RetentionAnalyzer (只读)
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
data/resource_effectiveness_events.jsonl   BKTStateRepository (权威只读)
          │                     │
          └──────────┬──────────┘
                     ▼
          计算 days_since_learning (自然日天数差)
          与 QUESTION_ATTEMPT 复测记录
                     │
                     ▼
          判定 RetentionProfile
          (DUE_FOR_REVIEW / NEEDS_REINFORCEMENT / NOT_DUE / INSUFFICIENT_DATA)
                     │
                     ▼
      [ 前端 ResourceHub.tsx 条件渲染提示卡 ]
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
「🔄 该复习一下了」卡片     「📘 建议再巩固一下」卡片
   点击「开始快速复测」       点击「重新学习」
         │                       │
         ▼                       ▼
调起现有 KnowledgePointQuiz  调起 ConceptCardModal
(POST /api/quiz/submit)
         │
         ▼
  权威 BKT 自动更新
```

---

## 四、验证证据与测试套件

### 1. 质量门禁校验 (8/8 严苛检查通过)
运行 `python scripts/sprint9f_quality_gate.py`：
```text
================================================================================
Sprint 9-F: Learning Retention Check Lite Quality Gate
================================================================================
[01/08] Git Baseline & Frozen Dirs 0 Diff Invariant ... PASS
[02/08] Retention Models & 4-Tier Status Enums ... PASS
[03/08] Time Thresholds & Day Boundary Contracts ... PASS
[04/08] Zero Mutation Invariant & 50x Idempotency ... PASS
[05/08] Multi-Student & Knowledge Context Isolation ... PASS
[06/08] Human-Centric Warmth & No Jargon Compliance ... PASS
[07/08] API Contract & 404 Error Isolation ... PASS
[08/08] Full Backend & Frontend Test Suite Execution ... PASS
================================================================================
ALL 8 QUALITY GATE CHECKS PASSED PERFECTLY! [READY FOR UAT]
```

### 2. 后端单元与集成测试 (14/14 通过)
运行 `pytest gateway/tests/test_sprint9f_retention_check.py -v`：
- `test_01_no_learning_history_insufficient_data`: PASSED
- `test_02_learning_two_days_ago_not_due`: PASSED
- `test_03_learning_exactly_three_days_due_for_review`: PASSED
- `test_04_four_days_high_mastery_retake_quiz`: PASSED
- `test_05_four_days_low_mastery_review_concept`: PASSED
- `test_06_student_context_isolation`: PASSED
- `test_07_knowledge_point_isolation`: PASSED
- `test_08_deterministic_idempotency`: PASSED
- `test_08b_retention_retest_failed_needs_reinforcement`: PASSED
- `test_08c_retention_retest_passed_not_due`: PASSED
- `test_09_server_authoritative_ignores_client_tampering`: PASSED
- `test_10_analyzer_zero_mutation_invariant`: PASSED
- `test_11_micro_quiz_submission_updates_bkt_normally`: PASSED
- `test_12_api_contract_and_404_handling`: PASSED

### 3. 全局回归测试
- `pytest gateway/tests/ -q`: **429 passed** in 9.36s
- `pytest tests/ -q`: **143 passed** in 3.98s
- **后端总测试量**：572 项自动化测试 100% 通过，零回归！

### 4. 前端契约测试与类型检查
- `npm run typecheck`: **0 errors**
- `npm test`: **252 passed**, 61 suites, 0 failed

### 5. Playwright 端到端浏览器验收 (5/5 通过)
运行 `python scripts/uat_sprint9f_browser.py`：
- **Scenario A**: 访问学习资源中心，达到复习间隔展示「🔄 该复习一下了」卡片与微测入口 (`sprint9f_01_retention_prompt_card.png`) -> PASS
- **Scenario B**: 点击「开始快速复测」联动调起现有微测验抽屉 (`sprint9f_02_retention_quiz_launch.png`) -> PASS
- **Scenario C**: 复测未稳固展示「📘 建议再巩固一下」卡片与概念回顾入口 (`sprint9f_03_retention_reinforcement_card.png`) -> PASS
- **Scenario D**: 切换学生或未学考点，验证优雅静默（`INSUFFICIENT_DATA` 零干扰）(`sprint9f_04_insufficient_data_clean_state.png`) -> PASS
- **Scenario E**: 移动端 375x812 视口下卡片响应式折行、无横向滚动条溢出 (`sprint9f_05_mobile_375px_ergonomics.png`) -> PASS

---

## 五、变更文件清单

| 文件路径 | 变更类型 | 说明 |
| :--- | :--- | :--- |
| `gateway/learning/retention/__init__.py` | **NEW** | 导出 `RetentionStatus`, `RetentionProfile`, `RetentionAnalyzer`, `REVIEW_AFTER_DAYS` 等 |
| `gateway/learning/retention/models.py` | **NEW** | 4 档状态机与白名单模型定义 |
| `gateway/learning/retention/analyzer.py` | **NEW** | 只读分析器核心实现（支持基准时间注入与多数据源依赖注入） |
| `gateway/api.py` | **MODIFY** | 挂载 `GET /api/learning/retention/{student_id}/{knowledge_id}` 端点 |
| `gateway/tests/test_sprint9f_retention_check.py` | **NEW** | 14 项后端严苛自动化测试 |
| `frontend/src/types.ts` | **MODIFY** | 增加 `RetentionStatus`, `RetentionProfile` 类型定义 |
| `frontend/src/api.ts` | **MODIFY** | 增加 `getRetentionProfile` API 调用方法 |
| `frontend/src/components/student/ResourceHub.tsx` | **MODIFY** | 挂载保持度提醒卡片、巩固卡片与联动微测逻辑 |
| `frontend/test/sprint9f_retention_check.test.ts` | **NEW** | 10 项前端契约测试 |
| `scripts/sprint9f_quality_gate.py` | **NEW** | 8 项全链路严格质量门禁 |
| `scripts/uat_sprint9f_browser.py` | **NEW** | 5 项 Playwright Chromium 端到端浏览器验收脚本 |
| `docs/PHASE5_SPRINT9F_WALKTHROUGH.md` | **NEW** | 交付技术文档与验收报告 |
