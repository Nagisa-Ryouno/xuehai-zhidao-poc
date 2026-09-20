# Sprint 11 / Phase 1 — Real User Pilot & State Reliability Hardening 实施计划 (最终收口版)

## 1. 实际允许修改的文件清单

本阶段定位为 **Hardening & Pilot Validation**，绝非 Feature Development。
本次实施**仅允许新增以下测试与验证套件文件**：

- **`scripts/sprint11_pilot_hardening.py`** [NEW]：Pilot 场景编排驱动、基线快照与恢复、受控时钟调度与证据链收集；
- **`gateway/tests/test_sprint11_pilot_hardening.py`** [NEW]：纳入标准自动化测试体系的测试用例（**明确声明为：测试代码新增例外 Test Code Addition Exception**）；
- **`scripts/sprint11_pilot_hardening_gate.py`** [NEW]：28 项质量门禁执行脚本与结构化证据输出；
- **`scripts/uat_sprint11_pilot_browser.py`** [NEW]：Playwright 浏览器端到端全场景验收脚本（Scenarios A ~ P）；
- **`artifacts/` 及相关测试报告/截屏**：自动化生成的测试证据与图片；
- **`implementation_plan.md` / `walkthrough.md`**：规划与交付报告。

---

## 2. 明确绝对冻结的文件与目录（0 Diff Invariant）

以下所有目录与文件**严禁任何修改**，最终提交前必须执行 `git diff` 严格断言 0 diff：
- `app/`（核心应用服务与领域模型，0 diff）
- `tests/`（根目录历史测试套件，0 diff）
- `data/seeds/`（种子数据目录，包含 `student_profiles.json`、`knowledge_graph.json` 等，0 diff）
- `gateway/learning/`（自适应学习引擎、BKT、PathState、TodayAction、Retention，0 diff）
- `gateway/ai/recommendation/`（AI 推荐服务、验证器、上下文构建器，0 diff）
- `gateway/ai/companion/`（AI 伴学服务、提示词、会话模型，0 diff）
- `gateway/api.py`, `gateway/adapter.py`, `gateway/config.py`（网关层生产逻辑与路由定义，0 diff）
- `gateway/tests/` 中除新增的 `test_sprint11_pilot_hardening.py` 外的所有既有测试文件（0 diff）
- `frontend/src/`（前端全部业务组件、页面、路由与 API 客户端，0 diff）
- `frontend/public/`, `frontend/index.html`（0 diff）

> [!CAUTION]
> **绝对禁止“为了让测试通过而修改业务逻辑”**。
> 若测试中发现现有系统缺少某项能力、UI 缺少某个按钮或交互不符，严禁向生产代码增加测试专用分支、fallback 或修改状态机，必须一律记录为 `Observed Gap / Undefined Boundary`。

---

## 3. Pilot 数据创建机制与正式演示数据隔离

### 3.1 真实契约深度核查结论
经对 `gateway/api.py`、`gateway/learning/today/resolver.py` 及 `app/services/student_service.py` 的源码与运行时联合核查：
1. `/api/students/init` 接口允许传入任意自定义 `student_id`，并将档案写入内存字典 `DEMO_STUDENTS`，同时在 `data/runtime/learning_path_states.json` 中初始化 30 个考点；
2. **关键下限制约**：下游核心依赖 `TodayActionResolver._validate_student(student_id)` 会调用 `student_service.get_student_profile(student_id)`，而该服务仅从种子文件 `data/seeds/student_profiles.json`（仅包含 `S001`~`S005`）中查找学生；
3. 若传入未在种子文件中登记的任意 ID（如 `PILOT_001`），`/api/learning/today/PILOT_001` 将抛出 `KeyError` 并返回 `404 找不到学生档案`；
4. 鉴于生产代码（`gateway/learning/today/resolver.py` 及 `data/seeds/`）处于**绝对冻结范围（0 diff）**，系统当前合法契约仅对种子库中存在的合法学生 ID 生效。

### 3.2 Pilot 专属测试学生方案
为确保既不侵入生产代码，又绝对不污染 `S001`、`S002`、`S003` 的正式演示基线：
- **选用 `S004` 作为主力 Pilot 测试学生**：
  - `S004`（赵同学）已存在于 `data/seeds/student_profiles.json` 中，符合下游全部鉴权与档案解析契约；
  - 经运行时检查，`data/runtime/bkt_states.json` 和 `data/runtime/learning_path_states.json` 中当前**完全不存在 `S004` 的任何运行时状态**（处于绝对初始状态）；
- **初始化调用**：
  通过调用标准 API `/api/students/init` 初始化 `S004`：
  ```json
  {
    "student_id": "S004",
    "student_name": "赵同学",
    "major": "经济学",
    "grade": "大二",
    "learning_goal": "在保持高正确率的同时压缩答题时间，适应限时考试",
    "start_knowledge_id": "K01"
  }
  ```
- **正式基线保护**：
  `S001`、`S002`、`S003` 的基线数据全程保持只读用于多学生隔离与教师端同源比对，绝不作为 Pilot 攻坚作答的主体。

---

## 4. Pilot 数据 Teardown 与基线还原机制 (P0 Gate)

在测试开始前捕获权威持久化数据基线，并在测试结束（无论成功或异常）后无条件执行原子级 Teardown：

### 4.1 快照范围
覆盖所有可能被写入的持久化文件：
- `data/runtime/bkt_states.json`
- `data/runtime/learning_path_states.json`
- `data/runtime/learning_events.jsonl`
- `data/runtime/bkt_processed_events.json`
- `data/companion_events.jsonl`
- `data/resource_events.jsonl`
- `data/resource_effectiveness_events.jsonl`
- `data/learning_sessions.json`

### 4.2 Teardown 还原验收断言
- 备份目录独立存储于临时安全路径；
- Teardown 时将备份文件无损拷贝回原路径，并清理 Pilot 期间产生的所有多余临时文件与内存中的 Demo 档案引用；
- 设立硬性门禁检查：
  $$\text{POST\_RESTORE\_STATE} == \text{PRE\_PILOT\_BASELINE}$$
  断言还原后的各持久化文件哈希与字段内容与测试前 100% 绝对一致，正式演示数据 `S001`~`S003` 零污染。

---

## 5. Controlled Test Clock 与 Simulated Day 实现机制

严禁真实等待 3～7 天（严禁 `sleep(86400)`），严禁修改操作系统时间，严禁对生产环境 `datetime` 进行全局 monkey-patch。

### 5.1 逻辑时间定义
在测试 Harness 与报告中统一定义并明确标注为**测试时间语义（Simulated Day）**：
- `Simulated Day 0`：基线时间 $T_0$（新学生注册冷启动与只读诊断）；
- `Simulated Day 1`：$T_0 + 1\text{d}$（首日微测验突破与权威写闭环）；
- `Simulated Day 2`：$T_0 + 2\text{d}$（重启恢复、艾宾浩斯记忆衰减评估与保持度复习）；
- `Simulated Day 3`：$T_0 + 3\text{d}$（持续演进、多学生隔离切换与教师端同源比对）。

### 5.2 注入方式与未定义边界处理
1. **已支持 `now` 参数的模块**：
   - `TodayActionResolver.resolve(student_id, now=...)`
   - `RetentionAnalyzer.analyze(student_id, knowledge_id, now=...)`
   直接传入对应的受控测试时间对象；
2. **未提供时间注入参数的生产接口**：
   - 严禁修改生产业务层添加测试参数；
   - 在测试 Harness 层构造具有相应逻辑时间戳的测试事件与测试上下文；
   - 若某些场景无法通过现有契约真实验证时间演变，必须在报告中明确标注为 `Undefined Boundary / Not Fully Verifiable`。

---

## 6. Level 1 验证范围 (Deterministic API & State Pilot)

**Level 1 是本 Sprint 的主门禁**。所有关于系统自适应闭环、状态持久化、重启恢复、多学生隔离与只读边界的核心架构结论必须由 Level 1 提供第一手权威证据：

1. **冷启动与只读诊断**：
   - `/api/students/init` 初始化 `S004`，验证 30 考点默认锁状态；
   - `/api/diagnostic/pretest` 获取与提交作答，断言诊断完全只读（$\Delta BKT = 0, \Delta PathState = 0, \Delta QUESTION\_ATTEMPT = 0$）；
2. **权威学习突变与精确前后快照比对**：
   - 微测验提交（`/api/quiz/submit`），记录并比对 4 组快照：
     - `before_bkt` vs `after_bkt`
     - `before_path` vs `after_path`
     - `before_events` vs `after_events`
     - `before_today_action` vs `after_today_action`
   - 断言写操作与事件产生严格 1:1 对应，只读操作产生 0 个事件；
3. **服务端权威持久化与状态恢复**：
   - 模拟客户端销毁与内存清空，验证直接从服务端持久化 JSON 文件重新反序列化学情数据；
4. **多学生状态快照级强隔离**：
   - 对 `S001`、`S002`、`S003`、`S004` 分别采集 6 维快照，执行轮换切换比对，验证各自的 BKT、路径状态、事件流、今日行动、推荐上下文与伴学上下文绝不交叉渗透；
5. **AI 只读直接权威不变量**：
   - 连续调用 AI 推荐 5 次与 AI 伴学 5 次，严格断言直接权威不变量：
     $$\Delta BKT = 0, \quad \Delta PathState = 0, \quad \Delta QUESTION\_ATTEMPT = 0, \quad \Delta LearningEvents = 0$$
   - 在固定权威状态与固定逻辑时钟下重新解析 Today Action，断言确定性输出一致；
6. **教师/学生同源核验（Canonical Projection）**：
   - 建立只存在于测试层中的 `CanonicalStudentLearningProjection` 规范投影模型，提取两端 7 大业务事实字段比对，不要求 API 原始 JSON 契约相同；
7. **Baseline Snapshot & Restore**：
   - 严格断言测试后状态完全复原，正式基线 0 污染。

---

## 7. Level 2 验证范围 (Browser UAT)

**Level 2 只验证端到端呈现链路**：`UI` $\rightarrow$ `API` $\rightarrow$ `Authoritative State` $\rightarrow$ `UI`。
Playwright 浏览器测试绝不作为判断后端权威状态是否正确的唯一证据。若因浏览器视口、网络加载或环境时序导致 Level 2 异常，应独立报告，不得抹杀 Level 1 的权威状态验证结论。

涵盖 Scenarios A ~ P 共 16 个高价值场景：
- **Scenario A: New Student Cold Start**：学生看板初始化渲染与考点呈现；
- **Scenario B: Diagnostic**：诊断前测交互与初始路线生成；
- **Scenario C: First Learning Action**：今日行动卡引导至资源中心；
- **Scenario D: Quiz $\rightarrow$ BKT $\rightarrow$ Replanning**：微测验答题提交与界面状态变迁；
- **Scenario E: Hard Refresh Recovery**：浏览器强制刷新，验证直接从服务端重载学情；
- **Scenario F: Simulated Next-Day Recovery**：跨天登录与学情看板同步；
- **Scenario G: Retention / Review**：保持度评估与复习入口呈现；
- **Scenario H: AI Recommendation Read-only**：资源中心推荐卡片浏览；
- **Scenario I: AI Companion Read-only**：智能伴学窗口互动；
- **Scenario J: Student Switching / Isolation**：多学生身份切换与看板隔离；
- **Scenario K: Teacher $\rightarrow$ Student Cross-view**：教师端学生详情画像下钻；
- **Scenario L: Student $\rightarrow$ Teacher Cross-view**：双端穿梭交互；
- **Scenario M: Mobile Recovery**：375×812 移动端视口浏览与无横向溢出断言；
- **Scenario N: Offline / API Failure Graceful Degradation**：接口异常时的友好提示；
- **Scenario O: Final Cross-day consistency**：多日演进后最终状态一致性核验；
- **Scenario P: Unexpected Console / Page / Request Error = 0**：统计 0 未捕获 page error、0 页面崩溃、0 非预期 request failure（Scenario N 中主动注入的预期故障不计入，但验证故障恢复后无残留异常）。

> [!NOTE]
> 若 UAT 执行中发现前端页面缺少某项预期按钮或交互路径与计划不同，必须忠实记录为 `Observed Gap / Undefined Boundary`，**严禁修改 `frontend/src/` 增补组件以迎合测试**。

---

## 8. 必须报告为 Undefined Boundary 的情况规范

当遇到以下未明确定义的系统行为时，严禁通过修改代码或伪造断言使其看起来“完美”，必须如实报告为 `Observed Gap / Undefined Boundary`：

1. **微测验提交的请求级幂等性（Request-Level Idempotency）**：
   - 现有 `/api/quiz/submit` 接收 `QuizSubmitRequest(student_id, question_id, chosen_option)`，未定义客户端生成的 `idempotency_key` 或 `request_id`；
   - 同一作答若发生网络重试，服务端当前会视为新的答题行为；
   - **报告策略**：将其定义为“现有重复提交行为核验”，如实记录系统行为，明确标注为 `Undefined Boundary: No client request-level idempotency contract`，严禁在业务层私自添加幂等处理。
2. **后端进程重启测试（Check 12）**：
   - 严格区分“真实 OS 进程重启”与“对象重建/内存重载”；
   - 若在测试运行环境中因端口占用或权限受限无法安全拉起并重启子进程，必须将进程级重启项如实标注为 `Not Fully Verifiable (Environment Constrained)`，而不得将模块 reload 冒充为进程重启。
3. **前端交互缺失**：
   - 若某些业务状态在前端页面尚未设计可视化入口（例如手动触发前测重新诊断），如实记录 `Observed Gap`，严禁修改前端组件代码。

---

## 9. 质量门禁 28 项检查与依赖证据链映射 (`sprint11_pilot_hardening_gate.py`)

门禁核心检查项必须构建完整的**证据链（Evidence Chain）**：
$$\text{Initial State} \longrightarrow \text{Operation} \longrightarrow \text{Response} \longrightarrow \text{Authoritative State} \longrightarrow \text{Side Effect} \longrightarrow \text{Recovery} \longrightarrow \text{Final Assertion}$$

| 检查项编号 | 检查项名称 | 依赖的核心证据 | 判定标准 |
|:---|:---|:---|:---|
| **Check 01** | 新学生注册初始化 | POST `/api/students/init` 返回 `StudentInitResponse` | 200 OK，包含 30 考点状态字典与初始聚焦考点 |
| **Check 02** | 30 个考点默认初始状态合法 | 读取 `data/runtime/learning_path_states.json` | 首考点 K01 为 `in_progress`，其余 29 考点均为 `locked` |
| **Check 03** | 诊断前测完全只读 | 前测提交前后比对 BKT、路径状态与事件文件 | $\Delta BKT = 0, \Delta PathState = 0, \Delta Events = 0$ |
| **Check 04** | 前测后动态生成有效航线与今日行动 | 调用 `/api/students/{id}/dashboard` 与 `/api/learning/today/{id}` | 生成包含目标考点的有效拓扑航线与首日行动卡 |
| **Check 05** | Day 1 试题获取脱敏断言 | GET `/api/quiz/K01` 响应体检视 | 试题内容包含 stem/options，绝不透传 `correct_option` 与题解解析 |
| **Check 06** | Day 1 测验驱动 BKT 掌握度更新 | 记录 `before_bkt` 与 `after_bkt` | 目标考点掌握度按照现有 BKT 参数及实际答题结果发生合法、可解释的更新并持久化到文件，不预设单调上升 |
| **Check 07** | Day 1 测验驱动 PathState 规则校验 | 记录 `before_path` 与 `after_path` | 节点状态转移符合现有 PathState / Dynamic Path 规则（允许因答题不足而保持不变，与 BKT 及前置关系一致） |
| **Check 08** | Day 1 测验驱动动态重规划一致性 | 检视作答响应中的 `replanning` 结构 | 前置合法、DAG 合法、信号合法、确定性输出，与当前 Dynamic Path Planner 生产契约严格一致 |
| **Check 09** | 作答后今日行动即时刷新 | 记录 `before_today_action` 与 `after_today_action` | 今日行动根据最新学情重新计算，不再停留在上一动作 |
| **Check 10** | 写操作与事件严格 1:1 对应 | 统计 `data/runtime/learning_events.jsonl` 新增记录 | 精确新增 1 条 `QUESTION_ATTEMPT` 事件，无额外事件注入 |
| **Check 11** | 客户端状态清空与服务端权威恢复 | 清空内存字典/客户端缓存后调用 API | 重新读取的数据与服务端持久化文件 100% 字段一致 |
| **Check 12** | 权威状态持久化文件反序列化保真度 | 重新建立服务实例读取持久化文件（区分进程重启与对象重建） | 持久化状态无损恢复，若执行真实进程重启则附带进程 PID 证据；若受限标注 ENVIRONMENT_CONSTRAINED |
| **Check 13** | 跨天状态留存与保持度计算契约 | 注入受控逻辑时间 $T_0 + 2\text{d}$ 调用现有 retention API | 输出符合现有代码定义的 retention interval / due 判定规则，不要求未实现的外部记忆模型 |
| **Check 14** | 条件保持度复习判定 | 根据 retention 契约判定今日行动 | 若满足到期复习条件则输出 REVIEW_RETENTION，未满足则如实反映实际状态 |
| **Check 15** | 现有微测验重复提交语义核验 | 连续发送相同作答 payload 并观察响应与事件写入 | 如实验证现有重复提交行为，若缺乏幂等键则记录 UNDEFINED_BOUNDARY |
| **Check 16** | S001 与 S002 6 维快照强隔离 | 提取 BKT、路径、事件、今日行动、推荐上下文、伴学上下文 | 两者核心数据无任何交集与串扰 |
| **Check 17** | S002 与 S003 6 维快照强隔离 | 提取两生 6 维状态快照比对 | 两者核心数据完全独立 |
| **Check 18** | 轮换切换身份无残留 | 执行 S001 $\rightarrow$ S002 $\rightarrow$ S003 $\rightarrow$ S001 循环 | 重新获取 S001 时，其状态与切换前 100% 一致 |
| **Check 19** | 教师端与学生端 7 维同源核验 | 基于 `CanonicalStudentLearningProjection` 提取两端数据比对 | 身份、目标、总正确率、分考点掌握度/分类、最近尝试、历史 100% 同源 |
| **Check 20** | AI 推荐连续 5 次调用只读边界 | 5 次调用前后比对持久化状态 | $\Delta BKT = 0, \Delta PathState = 0, \Delta QUESTION\_ATTEMPT = 0, \Delta LearningEvents = 0$ |
| **Check 21** | AI 伴学连续 5 次调用只读边界 | 5 次调用前后比对持久化状态 | $\Delta BKT = 0, \Delta PathState = 0, \Delta QUESTION\_ATTEMPT = 0, \Delta LearningEvents = 0$ |
| **Check 22** | 只读接口零事件写入 | 频繁请求今日行动、资源中心、教师中台前后比对事件数 | 事件总增量严格为 0 |
| **Check 23** | 依赖异常/超时优雅降级 | 模拟外部依赖不可用并调用服务 | 服务优雅返回降级/空结果，绝不产生半完成脏写 |
| **Check 24** | 异常入参输入防护 | 发送损坏 payload 或非法考点 ID | 接口返回标准 4xx/422，权威持久化文件零损坏 |
| **Check 25** | 全站用户可见文案合规 | 检视 API 返回文案与引导词 | 零技术黑话、零焦虑排名歧视，语言温和鼓励 |
| **Check 26** | **Pilot 数据隔离与正式基线保护** | 检视正式学生 S001~S003 在 Pilot 期间的状态 | S001~S003 持久化数据在 Pilot 期间零篡改、零写入 |
| **Check 27** | **跨天权威恢复纯净性** | 模拟跨天后直接由服务端文件重新恢复学情 | 数据 100% 来自服务端文件，不包含任何外部未持久化脏数据 |
| **Check 28** | **关键状态变迁完整证据链** | 检视核心检查项是否包含完整的 before $\rightarrow$ op $\rightarrow$ after 链条 | 核心写操作均具备完整的初始状态、操作响应、副作用断言记录 |

> [!IMPORTANT]
> **28 项门禁的五态判定原则**：
> 门禁允许以下五种状态：`PASS`、`OBSERVED_GAP`、`UNDEFINED_BOUNDARY`、`ENVIRONMENT_CONSTRAINED`、`FAIL`。
> 硬性规则：28 项必须全部执行完毕；任何明确既有契约被违反的项目不得存在 FAIL（FAIL = 明确既有契约被违反）。最终报告必须分别统计 PASS, OBSERVED_GAP, UNDEFINED_BOUNDARY, ENVIRONMENT_CONSTRAINED, FAIL 并给出每一项对应的直接证据。


---

## 10. 最终 Git Commit 前必须满足的全部先决条件

在执行任何 Git 提交前，必须依次完整执行以下检查，缺一不可：

1. **执行核心 Pilot 驱动脚本**：
   ```bash
   python scripts/sprint11_pilot_hardening.py
   ```
   输出完整的 Simulated Day 0 ~ Day 3 演化日志与状态快照；
2. **执行自动化回归测试**：
   ```bash
   pytest gateway/tests/test_sprint11_pilot_hardening.py -v
   ```
   所有用例必须 100% PASS；
3. **执行全量 28 项质量门禁**：
   ```bash
   python scripts/sprint11_pilot_hardening_gate.py
   ```
   必须输出 **28 / 28 PASS**（或经声明的已知未定义边界说明）；
4. **执行浏览器全场景 UAT**：
   ```bash
   python scripts/uat_sprint11_pilot_browser.py
   ```
   Scenarios A ~ P 全部执行完毕且控制台零报错；
5. **执行全系统全量回归套件**：
   ```bash
   pytest gateway/tests/
   pytest tests/
   npm test --prefix frontend
   npm run typecheck --prefix frontend
   npm run build --prefix frontend
   ```
   历史全部测试套件 100% 通过，前端类型检查与构建 0 错误；
6. **执行 Git 冻结检查（绝对 0 Diff 断言）**：
   ```bash
   git status --short
   git diff -- app/
   git diff -- tests/
   git diff -- data/seeds/
   git diff -- gateway/learning/
   git diff -- gateway/ai/recommendation/
   git diff -- gateway/ai/companion/
   git diff -- gateway/api.py
   git diff -- frontend/src/
   ```
   上述冻结目录与文件必须完全 **0 diff**；
7. **执行 Teardown 恢复校验**：
   确认 `POST_RESTORE_STATE == PRE_PILOT_BASELINE`，正式数据完全干净；
8. **原子提交**：
   仅在以上条件全部满足后，才执行单一原子提交：
   ```bash
   git commit -m "test(product): harden real user pilot flow"
   ```

---

## 11. 最终交付报告必须正面回答的 6 个核心架构问题

最终交付报告（`walkthrough.md`）将逐一正面回答以下 6 个核心架构问题并附带自动化证据：
1. **一个新学生能否从冷启动稳定进入学习闭环？**
2. **学生关闭页面、刷新、重新进入后，是否仍能恢复正确权威状态？**
3. **连续数日学习后，BKT、PathState、Today Action、Retention 是否始终保持一致？**
4. **多学生轮换时是否存在任何状态串扰？**
5. **AI Recommendation / Companion / Teacher 是否始终保持只读边界？**
6. **这次 Pilot 是否发现了任何此前 Sprint 10-C 未暴露的新问题？**
   （若发现问题，严格按 `Issue`, `Severity`, `Reproduction`, `Observed behavior`, `Expected behavior`, `Root cause`, `Whether core architecture must change` 结构化报告）。
