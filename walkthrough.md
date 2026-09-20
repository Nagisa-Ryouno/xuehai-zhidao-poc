# Sprint 10-B Phase 3 — Real DeepSeek Controlled Live Smoke Test 验收报告

**阶段定位**: 真实 DeepSeek API 受控联调与端到端验证 Sprint  
**唯一目标**: 在不改变现有产品业务逻辑、不修改权威学习状态、不扩大 AI 权限边界的前提下，证明 Sprint 10-B Phase 1/2 建立的 `Provider → Candidate Generator → Deterministic Validator` 闭环可以安全承接一次真实 DeepSeek API 输出。  
**核心红线**: `allow_production_decision = False` 永久成立，AI 只能产出候选，确定性校验器拥有最终仲裁权。  

---

## 一、Phase 3 实际变更 (Files Changed)

- [`scripts/sprint10b_phase3_live_smoke.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/scripts/sprint10b_phase3_live_smoke.py): 新增受控真实 DeepSeek API 联调脚本（硬上限 $\le 3$ 次，脱敏审计日志存盘，零 API Key 泄露）；
- [`scripts/sprint10b_phase3_gate.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/scripts/sprint10b_phase3_gate.py): 新增 18 维严苛质量门禁脚本；
- [`artifacts/phase3_live_smoke_summary.json`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/artifacts/phase3_live_smoke_summary.json): 真实调用脱敏审计工件（无明文 Key，无敏感 Prompt）；
- [`gateway/tests/test_sprint10b_deepseek_provider.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/gateway/tests/test_sprint10b_deepseek_provider.py): 增强 `test_18` 断言兼容性，确保开发者本地配置 Key 时仍能平稳运行离线测试；
- [`implementation_plan.md`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/implementation_plan.md) / [`walkthrough.md`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/walkthrough.md): 交付文档。

---

## 二、调用链路 (Invocation Flow)

```
Authoritative Learning State (BKT, PathState, Concept Cards, Resource Catalog)
        ↓ (只读读取，零重新实现)
Recommendation Context (脱敏上下文快照，零 PII，伪匿名 student_s001)
        ↓
DeepSeekCandidateGenerator (显式 task="recommendation" 任务路由)
        ↓
AIProvider (DeepSeekProvider + HttpLLMTransport)
        ↓
Transport: https://api.deepseek.com/chat/completions (model="deepseek-flash", response_format={"type": "json_object"})
        ↓
AI Candidate (纯候选元数据，严格 extra="forbid"，仅限 knowledge_id, resource_id, reason)
        ↓
Deterministic Validator (确定性三层防御、结构化去重与排序仲裁)
        ↓
Validated Candidates + Rejected Candidates (自包含 code/reason) + Zero Mutation Invariant
```

---

## 三、Live API 执行状态

- **是否执行真实 API**: **YES**
- **执行原因**: 本地已配置有效 `DEEPSEEK_API_KEY`，且通过 `--live` 显式 opt-in 触发受控联调。

---

## 四、真实请求次数与结果 (Live Requests Execution)

单次联调执行严格受到硬上限限制（最多 3 次），实际执行 **3 次**：

### 1. Request #1 — Happy Path
- **模式**: 真实模型调用（`deepseek-flash`）
- **耗时**: 3615 ms
- **状态**: `SUCCESS`
- **模型候选结果**:
  - `Validated #1`: `(K03, res_k03_concept)` - 需求价格弹性 考点精要微卡
  - `Validated #2`: `(K03, res_k03_example)` - 需求价格弹性 典型例题精析
  - `Rejected`: 0 项
- **决策权**: `allow_production_decision = False`

### 2. Request #2 — Context Boundary
- **模式**: 真实模型调用（单资源受限 Context）
- **耗时**: 2851 ms
- **状态**: `SUCCESS`
- **边界校验结果**:
  - `Validated #1`: `(K03, res_k03_concept)` - 微卡
  - `Boundary respected`: **YES**（所有候选严格属于 Context 白名单候选池，绝无外溢）
  - `Rejected`: 0 项

### 3. Request #3 — Full E2E Mutation Safety
- **模式**: 完整 `RecommendationService.get_recommendations("S001")` 端到端调用
- **耗时**: 3226 ms
- **状态**: `SUCCESS`
- **零突变断言结果**:
  - `bkt_mutation`: 0
  - `path_mutation`: 0
  - `learning_event_mutation`: 0
  - `resource_event_mutation`: 0
  - `resource_eff_mutation`: 0
  - `total_mutations`: **0**

---

## 五、JSON Output 模式验证

真实 `deepseek-flash` 模型调用显式携带：
```json
{
  "type": "json_object"
}
```
且系统 Prompt 明确包含 JSON 指令。3 次真实请求均成功解析为合法 Python `dict`，零解析截断、零语法错误。

---

## 六、Context Boundary 验证

无论模型返回何种内容，只有包含在当前 Context 白名单中的 `(knowledge_id, resource_id)` 才能被 Validator 采纳。Request #2 明确证明了 Context 候选池白名单拦截机制在真实模型输出下依然生效。

---

## 七、业务状态零突变验证 (Zero Mutation Safety)

- **BKT 掌握度状态** (`data/bkt_states.json`): **0 mutation (unchanged)**
- **学习路径状态** (`data/learning_path_states.json`): **0 mutation (unchanged)**
- **正式学习事件** (`data/learning_events.jsonl`): **0 lines added (unchanged)**
- **资源消费事件** (`data/resource_events.jsonl`): **0 lines added (unchanged)**
- **今日行动推荐** (`TodayAction`): **0 mutation (unchanged)**

---

## 八、PII / API Key 安全防护

- **PII 检查**: `assert_no_pii()` 全流程扫描，仅包含伪匿名 `student_s001`；
- **API Key 隔离**:
  - 密钥存放在 `.env`（受 `.gitignore` 保护）；
  - `git grep` 严格断言源码中无实际 API Key；
  - `artifacts/` 存盘的审计文件严格进行敏感脱敏处理；
  - 交付报告与日志中绝对不泄露明文密钥。

---

## 九、Phase 3 专项质量门禁 (18/18 PASS)

门禁脚本：[`scripts/sprint10b_phase3_gate.py`](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/scripts/sprint10b_phase3_gate.py)

```
============================================================================
Sprint 10-B / Phase 3 — Real DeepSeek Live Smoke Quality Gate
============================================================================
[01/18] Phase 2 Baseline ........................................ PASS
[02/18] Live Mode Explicit Opt-In ............................... PASS
[03/18] API Key Not in Source ................................... PASS
[04/18] API Key Not in Logs/Artifacts ........................... PASS
[05/18] Provider Abstraction Reused ............................. PASS
[06/18] Response Format JSON Object ............................. PASS
[07/18] Prompt Contains JSON Instruction ........................ PASS
[08/18] Candidate Schema Unchanged .............................. PASS
[09/18] Validator Still Authoritative ........................... PASS
[10/18] allow_production_decision=False ......................... PASS
[11/18] No BKT Mutation (0 mutation) ............................ PASS
[12/18] No PathState Mutation (0 mutation) ...................... PASS
[13/18] No Learning Event Mutation (0 mutation) ................. PASS
[14/18] No Resource Event Mutation (0 mutation) ................. PASS
[15/18] No TodayAction Mutation (0 mutation) .................... PASS
[16/18] Maximum Live Request Count <= 3 ......................... PASS
[17/18] Live Failure Is Safe .................................... PASS
[18/18] Frozen Areas 0 Diff ..................................... PASS
============================================================================
Gate Summary: 18 PASSED, 0 UNDEFINED_BOUNDARY, 0 FAILED
============================================================================
RESULT: PASS (All invariants held with FAIL == 0)
```

---

## 十、全量回归测试汇总 (Full Regression Summary)

| 测试套件 | 测试命令 | 测试结果 | 状态 |
| :--- | :--- | :---: | :---: |
| **Phase 3 专项质量门禁** | `python scripts/sprint10b_phase3_gate.py` | **18 PASSED, 0 FAIL** | ✅ PASS |
| **Phase 3 受控联调** | `python scripts/sprint10b_phase3_live_smoke.py --live` | **3/3 SUCCESS, 0 Mutation** | ✅ PASS |
| **Phase 2 专项测试套件** | `pytest gateway/tests/test_sprint10b_phase2.py -v` | **15 passed** (100%) | ✅ PASS |
| **Gateway 整体回归** | `pytest gateway/tests/ -v` | **558 passed, 2 skipped** | ✅ PASS |
| **Core 根目录历史回归** | `pytest tests/ -v` | **143 passed** (100%) | ✅ PASS |
| **前端契约测试** | `npm test --prefix frontend` | **320 passed, 0 fail** (100%) | ✅ PASS |
| **前端类型检查** | `npm run typecheck --prefix frontend` | **0 errors (tsc -b)** | ✅ PASS |
| **前端生产构建** | `npm run build --prefix frontend` | **Built successfully** | ✅ PASS |

---

## 十一、冻结区域 0 Diff 验证 (Frozen Areas 0 Diff)

执行对比：
```bash
git diff -- app/ tests/ data/seeds/ gateway/learning/ gateway/ai/companion/ gateway/api.py gateway/adapter.py gateway/config.py frontend/src/ frontend/public/ frontend/index.html
```
**结果**: 0 行修改，100% 严格 0 diff。

---

## 十二、未解决问题与边界声明

- 无未定义边界（`UNDEFINED_BOUNDARY = 0`）；
- 无阻断性缺陷（`FAIL = 0`）。

---

## 十三、最终判定

🏆 **Sprint 10-B Phase 3 判定: PASS**  
Sprint 10-B 全阶段圆满封板，系统已准备好进入 **Sprint 10-C：学生端产品化 + PWA**。
