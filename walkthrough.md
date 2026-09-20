# Sprint 10-B Phase 2 — DeepSeek Candidate Recommendation & Deterministic Validation 验收报告

**阶段定位**: `AI Candidate Generation + Deterministic Validation`（后端自闭环验证，绝非 AI 决策 Sprint）  
**核心原则**: AI 只能提出候选推荐，系统通过三层确定性校验器进行仲裁；AI 永远不是生产决策者 (`allow_production_decision = False`)  
**冻结保障**: 绝对冻结区域 100% 0 diff（`app/`, `tests/`, `data/seeds/`, `gateway/learning/`, `gateway/ai/companion/`, `gateway/api.py`, `gateway/adapter.py`, `gateway/config.py`, `frontend/src/`, `frontend/public/`, `frontend/index.html`）  

---

## 一、核心架构闭环 (Architecture)

```
Authoritative Learning State (BKT, PathState, Concept Cards, Resource Catalog)
        ↓ (纯只读读取，零重新实现)
Recommendation Context (脱敏上下文快照，零 PII，伪匿名 student_id)
        ↓
DeepSeek Candidate Generator (显式 task="recommendation" 契约路由)
        ↓
AI Candidate (纯候选元数据，严格 extra="forbid"，仅限 knowledge_id, resource_id, reason)
        ↓
Deterministic Validator (确定性三层防御、结构化去重与排序仲裁)
        ├── Layer 1: JSON 语法与容器合法性 (截断反引号、0<=长度<=3、空列表安全)
        ├── Layer 2: 结构安全性 (FORBIDDEN_FIELD_ROOT, FORBIDDEN_FIELD_ITEM, 命令/代码注入拦截)
        └── Layer 3: 上下文事实锚定 (Context Grounding、候选池物理隔离、去重 DUPLICATE_CANDIDATE)
        ↓
Deterministic Order Arbiter (按照 (knowledge_id, resource_id) 升序稳定排列，AI rank/priority/score 零参与)
        ↓
Validated Candidates + Rejected Candidates (自包含 code/reason) + Validation Reasons Summary
```

---

## 二、测试与质量门禁验证结果 (Verification Results)

### 1. Phase 2 核心质量门禁 (17/17 PASS)

门禁脚本：[`scripts/sprint10b_phase2_gate.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/scripts/sprint10b_phase2_gate.py)

```
============================================================================
Sprint 10-B / Phase 2 — DeepSeek Recommendation & Validation Quality Gate
============================================================================
[01/17] Provider Contract ....................................... PASS
[02/17] Candidate Schema ........................................ PASS
[03/17] Valid Candidate [Case A] ................................ PASS
[04/17] Invalid Knowledge [Case C] .............................. PASS
[05/17] Invalid Resource [Case D] ............................... PASS
[06/17] Invalid Relation ........................................ PASS
[07/17] Duplicate Candidate [Case E] ............................ PASS
[08/17] Empty Response [Case F] ................................. PASS
[09/17] Malformed Response [Case G] ............................. PASS
[10/17] PII Firewall ............................................ PASS
[11/17] allow_production_decision=False ......................... PASS
[12/17] BKT Unchanged (0 mutation) .............................. PASS
[13/17] PathState Unchanged (0 mutation) ........................ PASS
[14/17] Learning Events Unchanged (0 mutation) .................. PASS
[15/17] Resource Events Unchanged (0 mutation) .................. PASS
[16/17] Deterministic 20x Repeated Runs ......................... PASS
[17/17] Mock Offline Guarantee .................................. PASS
============================================================================
Gate Summary: 17 PASSED, 0 UNDEFINED_BOUNDARY, 0 FAILED
============================================================================
RESULT: PASS (All invariants held with FAIL == 0)
```

### 2. 全量回归与测试套件汇总 (Full Regression Summary)

| 测试套件 | 测试范围 | 统计结果 | 状态 |
| :--- | :--- | :---: | :---: |
| **Phase 2 专项测试套件** | [`gateway/tests/test_sprint10b_phase2.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/gateway/tests/test_sprint10b_phase2.py) | **15 passed** (100%) | ✅ PASS |
| **既有推荐测试套件** | [`gateway/tests/test_sprint10b_recommendation.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/gateway/tests/test_sprint10b_recommendation.py) | **31 passed, 1 skipped** (100%) | ✅ PASS |
| **Gateway 整体回归** | `pytest gateway/tests/` | **558 passed, 2 skipped** (100%) | ✅ PASS |
| **Core 根目录回归** | `pytest tests/` | **143 passed** (100%) | ✅ PASS |
| **前端契约测试** | `npm test --prefix frontend` | **320 passed, 0 fail** (100%) | ✅ PASS |
| **前端类型检查** | `npm run typecheck --prefix frontend` | **0 errors (tsc -b)** | ✅ PASS |
| **前端生产构建** | `npm run build --prefix frontend` | **Built successfully (dist/)** | ✅ PASS |

---

## 三、安全攻防与边界测试覆盖 (Cases A ~ H)

1. **Case A (Valid Candidate)**: Context 包含 `K03->res_k03_concept`，AI 输出该对 -> `ACCEPT` 并自动注入权威系统元数据（标题、资源类型、来源渠道）。
2. **Case B (Candidate Pool Isolation)**: 【Service/集成层测试】即使全局资源库存在资源 `res_k01_concept`，但本次推荐 Context 仅提供 K03 候选池，AI 试图跨考点或跨候选池推荐时，在 Service 编排层坚决拦截并记录 `RESOURCE_NOT_IN_CONTEXT`，确立“**Global Catalog 存在 ≠ 当前 Context 合法**”。
3. **Case C (Unknown Knowledge ID)**: AI 输出不存在于图谱的考点 `K999` -> 拦截并标记 `UNKNOWN_KNOWLEDGE_ID`。
4. **Case D (Unknown Resource ID)**: AI 输出全库不存在的虚构资源 `res_not_exist_99` -> 拦截并标记 `UNKNOWN_RESOURCE_ID`。
5. **Case E (Duplicate Candidate)**: AI 输出两个相同的推荐对 `(K03, res_k03_concept)` -> 第一项保留，第二项记录为 `DUPLICATE_CANDIDATE` 结构化拒绝项。
6. **Case F (Empty Recommendations)**: AI 返回空列表 `{"recommendations": []}` -> 安全通过，返回 `validated_candidates = []`，绝不触发生产决策回退或虚假候选伪造。
7. **Case G (Malformed Non-JSON & E2E Zero Mutation)**: 完整验证链路 `Mock Provider -> Generator -> JSON parse failure -> RejectedCandidate(INVALID_JSON_SYNTAX) -> Service Response`，并断言调用前后 BKT、PathState、Learning Events、Resource Events 绝对 0 增量、0 变动。
8. **Case H (Forbidden Decision Fields & Rank/Priority/Score)**: AI 试图输出 `rank`, `priority`, `score`, `set_mastery`, `mutation` 等字段时，通过 `extra="forbid"` 与字段扫描统一映射为稳定业务错误码 `FORBIDDEN_FIELD_ITEM`，彻底阻断 AI rank 转化为生产优先级。
9. **Order Determinism (排序确定性)**: Run A 输出 `[K03, K04]`，Run B 输出 `[K04, K03]`；两者经校验器排序仲裁后，最终输出的 `validated_candidates` 顺序 100% 保持为 `[("K03", "res_k03_concept"), ("K04", "res_k04_practice")]`。AI 输出顺序与打分永远不参与系统排序。

---

## 四、生产状态零修改保证 (Mutation Safety Invariant)

在执行推荐请求与异常测试全流程中，系统严格只读：
- **BKT 掌握度状态** (`data/bkt_states.json`): **0 mutation (unchanged)**
- **学习路径状态** (`data/learning_path_states.json`): **0 mutation (unchanged)**
- **正式学习事件** (`data/learning_events.jsonl`): **0 lines added (unchanged)**
- **资源消费与效果事件** (`data/resource_events.jsonl`, `data/resource_effectiveness_events.jsonl`): **0 lines added (unchanged)**
- **今日行动裁决** (`TodayAction`): **0 mutation (unchanged)**
- **生产决策权限** (`allow_production_decision = False`): **永久保持**

---

## 五、冻结路径 0 Diff 证据 (Frozen Areas 0 Diff Verification)

执行 `git diff -- app/ tests/ data/seeds/ gateway/learning/ gateway/ai/companion/ gateway/api.py gateway/adapter.py gateway/config.py frontend/src/ frontend/public/ frontend/index.html`：
**输出为空，100% 0 diff 严格成立**。

### 本 Sprint 代码变更清单 (Files Changed)

- [`gateway/ai/recommendation/models.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/gateway/ai/recommendation/models.py): 新增 `RejectedCandidate`、`CandidateValidationResult` 实体；为 `RecommendationResponse` 增量扩展 `ai_candidates`, `validated_candidates`, `rejected_candidates`, `validation_reasons` 字段；
- [`gateway/ai/recommendation/generator.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/gateway/ai/recommendation/generator.py): 新增 `DeepSeekCandidateGenerator` 候选生成器，绑定显式 `task="recommendation"` 任务契约；
- [`gateway/ai/recommendation/validator.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/gateway/ai/recommendation/validator.py): 增强确定性三层校验器 `validate_candidates_detailed`，实现自包含结构化拒绝与确定性排序仲裁；
- [`gateway/ai/recommendation/service.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/gateway/ai/recommendation/service.py): 编排 Generator 与详细校验器，支持网关阻断模式与结构化响应模式并存；
- [`gateway/ai/recommendation/__init__.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/gateway/ai/recommendation/__init__.py): 导出新增模型与生成器类；
- [`gateway/tests/test_sprint10b_phase2.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/gateway/tests/test_sprint10b_phase2.py): 新增 15 项全面测试用例套件；
- [`scripts/sprint10b_phase2_gate.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/scripts/sprint10b_phase2_gate.py): 新增 17 项核心质量门禁；
- `implementation_plan.md` / `walkthrough.md`: 实施计划与验收报告。

---

## 六、离线保障说明 (Offline Guarantee)

- 默认配置 `DEEPSEEK_ENABLED=false`；
- 所有单元测试、专项测试、质量门禁均在完全离线状态下运行（使用 `MockDeepSeekProvider`）；
- 未产生任何真实外部 DeepSeek API 网络调用。
