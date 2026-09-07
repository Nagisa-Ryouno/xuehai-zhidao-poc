# 学海智导 (Xuehai Zhidao) V2 架构宪章 (Architecture Constitution)

> **版本**：Phase 2.1 Baseline Frozen  
> **生效时间**：2026-09-07  
> **效力等级**：最高架构约束（任何业务开发、功能迭代或 Agent 操作均不得违反）

---

## 一、架构风格与核心原则 (Architectural Style & Principles)

1. **务实分层模块化单体 (Pragmatic Layered Modular Monolith)**
   - 学海智导 V2 是且永远是一个清晰、模块化、单仓部署的模块化单体。
   - 严禁引入微服务、RPC、分布式事务、消息队列（Kafka/RabbitMQ/Celery）、集中式缓存（Redis/Memcached）或容器编排（K8s/Docker）。
   - 保证单机本地开发与运行环境轻量、确定、可重复运行。

2. **单向分层依赖原则 (Strict Unidirectional Dependency Rule)**
   - 系统依赖方向严格遵循：`Presentation (API) -> Application (Services) -> Domain -> Core`，以及 `Infrastructure -> Domain -> Core`。
   - **绝对禁止反向依赖**（如 Service 依赖 API、Domain 依赖 Service/Infrastructure）。
   - **绝对禁止跨层越权**（如 API Router 直接绕过 Service 访问 Infrastructure/Repository）。

3. **证据先行原则 (Evidence Before Claims)**
   - 任何架构或业务完整性断言必须附带真实可复现的命令行输出与测试证据，严禁仅凭上一阶段报告或臆断下结论。

---

## 二、分层职责与边界约束 (Layer Responsibilities & Boundaries)

### 1. 表现层 `app/api/`
- **职责**：HTTP 协议适配、路由分发、请求数据校验（Pydantic Schemas）、HTTP 状态码映射。
- **边界红线**：
  - 纯协议网关，严禁包含任何直接数据持久化、磁盘文件读写（`open()`、`read_text()`、`json.load()`）或复杂领域裁决。
  - 必须且只能调用 `app/services/` 应用服务层，严禁直接依赖 `app/infrastructure/` 仓储。
  - 捕获领域与应用层抛出的纯 Python 异常并映射为规范 HTTP 状态码（如 `EntityNotFoundError` $\to$ 404，`InvalidOptionError` $\to$ 422）。

### 2. 应用服务层 `app/services/`
- **职责**：用例编排（Use Case Orchestration）、事务与业务流程调度（如：判题 $\to$ 记录事件 $\to$ 触发 BKT 演进 $\to$ 触发路径局部重规划）。
- **边界红线**：
  - **绝不依赖 Web 框架**：严禁 `import fastapi`，严禁抛出 `HTTPException`。
  - 不做纯数学或纯算法的硬编码计算，纯领域计算委托给 `app/domain/`。
  - 通过 `app/infrastructure/` 执行持久化，并在测试时支持文件路径的显式依赖注入。

### 3. 领域核心层 `app/domain/`
- **职责**：核心认知追踪模型（BKT 数学计算）、自适应路径重规划决策引擎（Path Replanning Core）、知识拓扑与事件领域实体。
- **边界红线**：
  - **纯内存计算 (100% In-Memory Pure Compute)**：绝不执行任何磁盘文件读写（禁止 `open()`, `json.load()`）或网络 I/O。
  - 绝不依赖任何外部框架或外层模块（零 `fastapi`, 零 `requests`, 零 `app.infrastructure`, 零 `app.services`）。
  - 函数必须具备确定性与可幂等性，给定相同输入必须产出字节级一致的输出。

### 4. 基础设施层 `app/infrastructure/`
- **职责**：本地持久化（JSON/JSONL 读写、线程安全锁 RLock、文件原子替换 `os.replace`）、外部第三方模型适配（LLM Client）。
- **边界红线**：
  - 仓储层只做数据存取与安全持久化，严禁嵌入任何 BKT 数学公式或重规划规则裁决。
  - 严禁依赖应用服务层或表现层（零 `app.services`, 零 `app.api`）。

### 5. 核心基础层 `app/core/`
- **职责**：系统级全局配置（`config.py`）、系统级常量与业务枚举（`constants.py`）、纯 Python 通用异常体系（`exceptions.py`）。
- **边界红线**：
  - 位于依赖图最底层，严禁依赖系统内任何其他层。

---

## 三、数据生命周期三层物理隔离 (Data Lifecycle Rules)

数据目录划分为三层独立区域，其生命周期与 Git 策略严格隔离：

| 数据分层 | 物理路径 | 存储属性 | Git 策略 | 典型文件 |
| :--- | :--- | :--- | :--- | :--- |
| **原始层 (Raw)** | `data/raw/` | 离线、只读原始参考源 | Git 跟踪 | `economics_learning_demo.xlsx` |
| **种子层 (Seeds)** | `data/seeds/` | 冷启动只读基准数据 | Git 跟踪 | `quiz_bank.json`, `knowledge_graph.json`, `student_profiles.json`, `learning_paths.json`, `student_reports.json` |
| **运行层 (Runtime)** | `data/runtime/` | 在线动态持久化产物 | **.gitignore 排除 (0 文件跟踪)** | `learning_events.jsonl`, `bkt_states.json`, `bkt_processed_events.json`, `learning_path_states.json` |

- **红线**：运行时在线业务绝对禁止直接读取 `data/raw/economics_learning_demo.xlsx`，必须 100% 读取 `data/seeds/` 或 `data/runtime/` 下的 JSON/JSONL 文件。
- **红线**：`data/runtime/` 严禁出现任何 Git 跟踪文件。

---

## 四、API 契约与前端绑定规则 (API Contract & Frontend Rules)

1. **REST API 契约绝对冻结**
   - 全部 18 个 `/api/*` 端点与 1 个根端点 `/` 的 HTTP Method、URL 路由、请求载荷及响应模型完全冻结。
   - 严禁擅自修改字段名称、嵌套结构或返回类型。

2. **前端 API 客户端契约冻结**
   - `frontend/src/api.ts` 作为前端网络传输门面，自 Phase 2.1 起与起点保持严格 0 diff。
   - 严禁为前端开发私有特殊接口或绕过统一接口。

---

## 五、核心领域数学模型与算法规则 (Mathematical & Algorithmic Invariants)

1. **BKT 动力学方程与超参数物理冻结**
   - 初始先验概率：$P(L_0) = 0.20$
   - 知识转移概率：$P(T) = 0.10$
   - 猜对概率：$P(G) = 0.20$
   - 失误概率：$P(S) = 0.10$
   - 可识别性检验：$P(G) + P(S) = 0.30 < 1.0$
   - 黄金作答序列 (Wrong $\to$ Correct $\to$ Correct) 掌握度数学轨迹必须精确无偏：$0.2000 \to 0.1273 \to 0.4566 \to 0.8118$。

2. **自适应路径重规划决策核心 (Decision Core)**
   - 掌握度阈值：达标门槛 0.80（MASTERED），薄弱门槛 0.60（WEAK），回退门槛 0.70（DEMOTION）。
   - 严格且仅有 5 组法定合法配对（Legal Decision Pairs），非法配对一律抛出 `ValueError`。
   - 变动边界：严格 1-hop 局部隔离（MutationDomain 仅限当前节点及其直接后继）。
   - 序列化确定性：使用 Decimal 四舍五入保留 4 位定点小数，`CanonicalBusinessPayload` 生成规范紧凑无空格 JSON，SHA-256 跨运行稳定一致。

---

## 六、违宪后果与自检标准 (Constitutional Violations & Enforcement)

凡违反上述宪章规则的代码：
1. `tests/architecture/` 架构适应度测试将立即挂起并判定为 RED。
2. 任何引入 Web 依赖至 Service、引入 I/O 至 Domain、引入 `openpyxl` 至 `app/`、或破坏分层单向性的 Pull Request / Commit 均被判定为架构严重缺陷，拒绝合并。
