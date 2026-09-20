# Sprint 10-B Phase 3 — Real DeepSeek Controlled Live Smoke Test 实施计划

## 一、阶段定位与目标

本阶段是 **真实 DeepSeek API 受控联调与端到端验证 Sprint**。

### 唯一目标
> 在不改变现有产品业务逻辑、不修改权威学习状态、不扩大 AI 权限边界的前提下，证明 Sprint 10-B Phase 1/2 建立的 `Provider → Candidate Generator → Deterministic Validator` 闭环可以安全承接一次真实 DeepSeek API 输出。

### 本阶段明确非目标
- 不是 AI 推荐质量优化 Sprint；
- 不是新的推荐算法 Sprint；
- 不是前端/UI Sprint（后端自闭环验证，0 前端代码修改）；
- 不是 BKT / PathState 优化 Sprint；
- 不是 AI Judge Sprint；
- 不是让 AI 参与生产决策的 Sprint。

---

## 二、绝对架构红线与冻结区域 (0 Diff Invariant)

### 1. 核心架构红线 (Hard Redlines)
1. **`allow_production_decision = False` 永久成立**；
2. DeepSeek 只能产生候选 Candidate，绝无生产决策权；
3. DeepSeek 不能直接决定：下一学习节点、BKT、PathState、TodayAction、Mastery、学习路径、正式学习事件；
4. 所有真实 AI Candidate 必须经过现有 Deterministic Validator 仲裁；
5. Validator 对 AI 输出拥有最终仲裁权；
6. AI 输出的 `rank`, `priority`, `score` 绝不能参与权威排序或生产决策；
7. 真实 API 调用失败、超时、空内容、非法 JSON、非法 Candidate 等情况均必须安全失败，不能产生生产学习状态变更；
8. 不得为了适配真实 DeepSeek 而修改既有业务逻辑。

### 2. 绝对冻结路径 (100% 0 Diff)
- `app/`
- `tests/`
- `data/seeds/`
- `gateway/learning/`
- `gateway/ai/companion/`
- `gateway/api.py`
- `gateway/adapter.py`
- `gateway/config.py`
- `frontend/src/`
- `frontend/public/`
- `frontend/index.html`

### 3. 允许修改/新增范围
- `gateway/ai/recommendation/`（候选生成器模型解析优化，保持只读）
- `gateway/tests/`（测试用例）
- `scripts/`（`scripts/sprint10b_phase3_live_smoke.py`, `scripts/sprint10b_phase3_gate.py`）
- `artifacts/`（脱敏后的受控联调审计报告）
- `implementation_plan.md` / `walkthrough.md`

---

## 三、真实 API Key 安全防护规则

1. **零密钥泄漏防线**:
   - 绝不要求用户把 API Key 粘贴到代码或对话中；
   - 绝不将 API Key 写入源码、测试 fixture、prompt、日志、artifacts、walkthrough、Git 或交付报告；
   - 本地密钥存储在已处于 `.gitignore` 的 `.env` 文件中，并通过 `dotenv.load_dotenv()` 安全载入环境；
2. **环境未就绪降级机制**:
   - 若本地未检测到有效 Key，安全停止真实调用，报告 `LIVE_API_KEY_NOT_CONFIGURED`（定义为受控的 `UNDEFINED_BOUNDARY`），绝不伪造虚假通过；
   - 离线回归测试不受影响。

---

## 四、受控真实 API 请求设计 (最多 3 次硬上限)

### Request #1 — Happy Path
- **输入**: 准备最小、脱敏的标准 Recommendation Context（使用内部伪匿名 `student_id = student_s001`，包含 `K03` 权威考点与候选资源 `res_k03_concept`, `res_k03_example`）；
- **执行**: `Recommendation Context → DeepSeekCandidateGenerator → HttpLLMTransport → api.deepseek.com → Deterministic Validator`；
- **验证**:
  - 请求成功响应 (HTTP 200)；
  - 成功解析为合法 JSON 字典；
  - 候选进入 Candidate Validator，通过校验并注入权威元数据；
  - 验证 `allow_production_decision = False`；
  - 确认底层状态 0 mutation。

### Request #2 — Context Boundary
- **输入**: 严格限定 Context 仅包含 `K03 -> res_k03_concept` 和 `K04 -> res_k04_practice`；
- **验证**:
  - 观察真实模型输出候选；
  - 无论 AI 输出什么候选，凡是不在当前 Context 候选池内的资源（即使存在于全局资源库），均被 Validator 确定性拦截（`RESOURCE_NOT_IN_CONTEXT`）；
  - 若模型输出完全合规，验证均属于 Context 候选池；
  - 核心证明：“**无论 AI 返回什么，最终结果绝不能突破 Context 白名单**”。

### Request #3 — Full E2E Mutation Safety
- **前置**: 记录完整的权威持久化状态快照（`bkt_states.json`, `learning_path_states.json`, `learning_events.jsonl`, `resource_events.jsonl`, `resource_effectiveness_events.jsonl`, `TodayAction`）；
- **执行**: 调用完整 `RecommendationService.get_recommendations(student_id="S001")`；
- **后置对比**: 逐项验证所有状态文件与今日行动 100% 字节一致、0 增量、0 变动；
- **证明**: 推荐服务架构本身具有严格的**纯只读**特性。

---

## 五、交付物与实现步骤

### 1. 候选生成器模型解析适配 (`gateway/ai/recommendation/generator.py`)
- 保持向后兼容：离线时默认路由至 `MockDeepSeekProvider(model=gateway_settings.deepseek_model)`；
- 真实调用时，解析 `DEEPSEEK_MODEL`，当连接官方 `https://api.deepseek.com` 且配置为 `deepseek-flash` 时，自动映射为官方支持的 `deepseek-chat`，防止模型名不匹配导致 400；
- 复用 Sprint 10-B Phase 1 的 `DeepSeekProvider` 与 `HttpLLMTransport` 抽象，严禁在业务层直接调用 `requests.post` 或 `httpx.post`。

### 2. 受控 Live Smoke 验证脚本 (`scripts/sprint10b_phase3_live_smoke.py`)
- 必须显式检测 `DEEPSEEK_ENABLED=true` 与 `DEEPSEEK_API_KEY`；
- 明确输出模式与执行环境状态；
- 硬编码计数器：单次执行真实请求次数严格 $\le 3$；
- 格式化脱敏输出，审计证据存盘至 `artifacts/phase3_live_smoke_summary.json`；
- 不向终端输出完整原始响应或任何敏感 Token/Key。

### 3. Phase 3 专项质量门禁 (`scripts/sprint10b_phase3_gate.py`)
覆盖 18 项专项检查：
1. Phase 2 离线基线全部 PASS；
2. Live 模式显式 Opt-in 判定（未启用时不发真实外网请求）；
3. API Key 源码零泄露检查（搜索 git 跟踪文件）；
4. API Key 日志/工件零泄露检查；
5. 复用既有 Provider 抽象（`DeepSeekProvider`, `HttpLLMTransport`）；
6. `response_format={"type": "json_object"}` 契约保证；
7. Prompt 必须包含 JSON 输出显式指令；
8. Candidate Schema 严格保持 `extra="forbid"` 与字段白名单；
9. Validator 对真实模型输出继续保持绝对权威仲裁；
10. `allow_production_decision = False` 永久成立；
11. BKT 状态文件零变动；
12. 学习路径状态文件零变动；
13. 正式学习事件文件零新增；
14. 资源事件文件零新增；
15. 今日行动状态零突变；
16. 真实请求次数上限严格 $\le 3$；
17. 异常情况下安全失败（零脏写、受控异常映射）；
18. 冻结区域 100% 0 diff。

### 4. 全量回归与冻结目录检查
- `pytest gateway/tests/ -v`
- `pytest tests/ -v`
- `npm test --prefix frontend`
- `npm run typecheck --prefix frontend`
- `npm run build --prefix frontend`
- `git diff -- app/ tests/ ...` 严格 0 diff。

### 5. Git 提交与收口
- 提交 message: `feat(ai): validate real deepseek recommendation flow`；
- 确保 working tree clean。
