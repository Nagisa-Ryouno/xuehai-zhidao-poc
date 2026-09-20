# Sprint 10-B Phase 2 — DeepSeek Candidate Recommendation & Deterministic Validation 实施计划 (已修订)

## 一、阶段定位与架构闭环

本 Sprint 的唯一目标：
> **建立一个可以由 DeepSeek 生成“候选学习资源推荐”，再由系统确定性验证其合法性的后端闭环。**  
> **定位为：`AI Candidate Generation + Deterministic Validation`，绝非 AI 决策 Sprint。**

### 核心处理流水线
```
Authoritative Learning State (BKT, PathState, Catalog)
        ↓ (纯只读读取，零重新实现)
Recommendation Context (脱敏上下文快照，零 PII，伪匿名 student_id)
        ↓
DeepSeek Candidate Generator (通过 Sprint 10-B Phase 1 Provider 抽象)
        ↓
AI Candidate (纯候选元数据，禁止包含 rank/priority/decision/mutation)
        ↓
Deterministic Validator (确定性三层校验、结构化去重与候选排序仲裁)
        ↓
Validated Candidates + Rejected Candidates (自包含 code/reason) + Summary
```

---

## 二、架构红线与绝对冻结边界 (0 Diff Invariant)

### 1. 架构红线 (Hard Invariants)
- **`allow_production_decision = False` 必须永久成立**；
- AI 永远不是生产决策者，只能提出候选，绝不直接决定学生下一学习节点；
- AI 推荐代码绝对不得修改：
  - BKT 状态 (`bkt_states.json`)
  - PathState (`learning_path_states.json`)
  - TodayAction
  - LearningContext
  - Mastery
  - QUESTION_ATTEMPT 事件
  - 正式 learning events (`learning_events.jsonl`)
  - 正式 resource events (`resource_events.jsonl`, `resource_effectiveness_events.jsonl`)
  - 权威学习状态与生产决策流
- AI 候选必须经过 Deterministic Validator 仲裁，任何未在 Context 候选池中的 ID（即使存在于全局资源库）坚决 REJECT；
- AI 输出的任何 `rank`、`priority`、`score` 绝对不被系统采纳为权威优先级。

### 2. 绝对冻结区域（严格断言 0 Diff）
- `app/`（0 diff）
- `tests/`（0 diff）
- `data/seeds/`（0 diff）
- `gateway/learning/`（0 diff）
- `gateway/ai/companion/`（0 diff）
- `gateway/api.py`（**0 diff，复用既有 `/api/ai/recommendations/{student_id}` 路由，严禁使用 import side-effect 注入**）
- `gateway/adapter.py`（0 diff）
- `gateway/config.py`（0 diff）
- `frontend/src/`（0 diff，后端纯闭环验证，不改前端）
- `frontend/public/`（0 diff）
- `frontend/index.html`（0 diff）

### 3. 允许修改 / 新增范围
- `gateway/ai/recommendation/`（模型契约、候选生成器、校验器增强、服务编排）
- `gateway/tests/`（新增 Phase 2 测试用例套件 `test_sprint10b_phase2.py`）
- `scripts/`（新增 `scripts/sprint10b_phase2_gate.py` 质量门禁）
- `artifacts/`（门禁测试证据）
- `implementation_plan.md` / `walkthrough.md`

---

## 三、6 项核心设计修正与实现细节

### 1. Router 挂载与端点复用机制（严禁 Side-Effect 注入）
- **复用现有端点**: 经过深度检查，`gateway/api.py` 已经存在由 Sprint 10-B 建立的合法路由：
  `POST /api/ai/recommendations/{student_id}`
  该路由直接委托给 `default_recommendation_service.get_recommendations(student_id, req)`。
- **放弃隐式注入**: 不在 `gateway/ai/recommendation/__init__.py` 中采用任何 import side-effect 或 monkey-patch 方式动态挂载新路由，不引入全局注入机制，确保 **`gateway/api.py` 严格保持 0 diff**。
- **响应契约无缝增强**: `RecommendationResponse` 保持向后兼容的同时，平滑扩展结构化字段：`ai_candidates`, `validated_candidates`, `rejected_candidates`, `validation_reasons`, `allow_production_decision = False`。

### 2. Rejected Candidate 结构化自包含关联
- 拒绝候选不再与字符串原因数组按索引耦合，新增专属实体：
  ```python
  class RejectedCandidate(BaseModel):
      model_config = ConfigDict(extra="forbid")
      candidate: Dict[str, Any] = Field(..., description="未通过校验的原始候选载荷")
      code: str = Field(..., description="标准校验拒绝码，如 UNKNOWN_KNOWLEDGE_ID, DUPLICATE_CANDIDATE 等")
      reason: str = Field(..., description="详细拒绝原因说明")
  ```
- `CandidateValidationResult` 明确定义：
  - `validated_candidates: List[ValidatedRecommendation]`
  - `rejected_candidates: List[RejectedCandidate]`
  - `validation_reasons: List[str]`（作为派生汇总列表保留，便于日志与宏观监控）

### 3. Reason 安全边界合理化（坚决避免自然语言黑名单误杀）
- 保持边界防护：
  - 非空文本 (`reason.strip() != ""`)；
  - 长度限制 (`len(reason) <= 300`)；
  - 明确的结构化攻击防御（SQL 注入关键句式、`<script>` 标签、Python `os.system` 执行、`set_mastery` 等系统状态修改指令）。
- **坚决避免脆弱词汇误杀**：不写脆弱的自然语言 regex，不误杀包含 "update", "explain", "progress" 等正常教学解释词汇。
- **真正的安全防线**：坚决立足于严格 candidate schema、authoritative candidate pool 白名单比对、考点与资源拓扑关系的确定性校验。

### 4. 专项 Gate 与 Full Regression 清晰解耦
- **Phase 2 专项质量门禁 (`scripts/sprint10b_phase2_gate.py`)**: 聚焦于 Phase 2 自身核心 17 项不变量（Provider、Schema、Case A~H、去重、顺序确定性、PII、状态零变动、20x 重复性）。
- **Full Regression**: 作为独立命令与独立测试报告执行（`pytest gateway/tests/`, `pytest tests/`, `npm test` 等），不混淆专项门禁语义。

### 5. PII 边界与 `user_id` 确认
- 复用 Phase 1 已经建立的 `assert_no_pii` 防火墙；
- `user_id` 仅传递系统内部脱敏的伪匿名标识（例如 `"student_s001"`），绝不包含学生姓名、手机号、邮箱、身份证号；
- 严禁将任何 API Key 或鉴权凭证放入 prompt 或 context。

### 6. Candidate 排序确定性策略 (Order Determinism)
- 引入确定性仲裁排序规则：
  无论 AI 返回的顺序如何（例如 Run A 先返回 K03 再返回 K04，Run B 先返回 K04 再返回 K03），`RecommendationValidator` 均按照统一的确定性键值进行稳定排序：
  ```python
  validated_candidates.sort(key=lambda r: (r.knowledge_id, r.resource_id))
  ```
- **核心断言**:
  - AI 输出顺序不决定系统推荐顺序；
  - AI rank 绝对不参与权威排序；
  - AI priority 绝对不参与权威排序；
  - AI score 绝对不参与权威排序。

---

## 四、安全攻防测试用例规划 (Case A ~ H)

在 `gateway/tests/test_sprint10b_phase2.py` 中完整覆盖：
1. **Case A**: Context 包含 K03->R031，AI 返回 K03->R031 -> **ACCEPT**；
2. **Case B**: Context 包含 K03->R031，AI 返回 K03->R999（R999 即使存在于全局统一资源目录，但不属于本次 Context 候选池） -> **REJECT (`RESOURCE_NOT_IN_CONTEXT`)**；
3. **Case C**: AI 返回未知考点 K999->R031 -> **REJECT (`UNKNOWN_KNOWLEDGE_ID`)**；
4. **Case D**: AI 返回全库不存在资源 K03->R999 -> **REJECT (`UNKNOWN_RESOURCE_ID`)**；
5. **Case E**: AI 返回重复候选 K03->R031, K03->R031 -> **首项保留，第二项记录为 REJECT (`DUPLICATE_CANDIDATE`)**；
6. **Case F**: AI 返回空数组 -> **validated_candidates = []，不自动回退到 AI 决策**；
7. **Case G**: AI 返回格式错误的非 JSON 字符串 -> **REJECT (`INVALID_JSON_SYNTAX`)**，状态零污染；
8. **Case H**: AI 尝试返回 `{"rank": 1}` 或 `{"priority": "high"}` -> **REJECT (`FORBIDDEN_FIELD_ITEM`)**，禁止将 AI rank 提升为生产优先级；
9. **Order Determinism Case**: Run A (K03, K04) 与 Run B (K04, K03)，最终输出的 `validated_candidates` 顺序完全一致。

---

## 五、质量门禁与验证执行流程

1. 编写与完善 `gateway/ai/recommendation/` 模块；
2. 运行单元与集成测试 `pytest gateway/tests/test_sprint10b_phase2.py -v`；
3. 运行专项质量门禁 `python scripts/sprint10b_phase2_gate.py`；
4. 运行全量回归套件；
5. 验证冻结目录 0 diff；
6. 提交 commit: `feat(ai): add deterministic recommendation validation`；
7. 输出最终交付报告。
