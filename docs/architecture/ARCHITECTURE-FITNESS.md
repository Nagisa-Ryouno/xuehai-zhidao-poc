# 学海智导 (Xuehai Zhidao) V2 架构适应度函数规范 (Architecture Fitness Functions)

> **版本**：Phase 2.1 Baseline Frozen  
> **更新时间**：2026-09-07  
> **执行命令**：`pytest tests/architecture/ -v`

---

## 一、架构适应度函数矩阵 (Architecture Invariants Matrix)

| 编号 | 不变量名称 (Architecture Invariant) | 约束目标与红线 | 自动化执行测试文件 | 判定机制 | 破坏后果与风险 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **INV-01** | **Domain 纯内存零 I/O** | `app/domain/` 绝不依赖任何 Web 框架、外层模块、非标 I/O 库，严禁直接调用 `open`、`read_text`、`json.load` 等磁盘与网络 I/O | `tests/architecture/test_domain_purity.py` | Python AST 静态语法树遍历所有 AST Node | 领域模型耦合 I/O，无法脱机轻量测试，出现难以调试的状态副作用 |
| **INV-02** | **Router 纯协议适配网关** | `app/api/routers/` 绝不直接依赖 `app.infrastructure` 仓储，绝不包含直接磁盘文件读写，业务完全委托 Service | `tests/architecture/test_router_boundaries.py` | Python AST 检查禁止引入仓储层与文件 I/O 函数 | Router 退化为小型 God Controller，API 层与存储细节强耦合 |
| **INV-03** | **Service 不依赖 Web 框架** | `app/services/` 绝不依赖 `fastapi` 及其子模块，绝不抛出 `HTTPException`，业务异常统一使用纯 Python 异常 | `tests/architecture/test_service_boundaries.py` | Python AST 检查禁止 `import fastapi` 及子模块 | Service 无法在 CLI/离线脚本/其他传输协议中复用，侵入性框架绑定 |
| **INV-04** | **运行时零 openpyxl 依赖** | `app/` 整个代码树严禁依赖 `openpyxl`，Excel 解析严格局限在离线管线 `scripts/data_pipeline/` | `tests/architecture/test_runtime_dependencies.py` | AST 遍历扫描 `app/` 目录下所有 import | 严重拖慢运行时启动速度与内存占用，引入不稳定的二进制重依赖 |
| **INV-05** | **知识图谱私有字典封装** | `_raw_knowledge_points` 底层属性仅限 `knowledge_graph_service.py` 及其仓储访问，外部模块一律禁止私自侵入 | `tests/architecture/test_runtime_dependencies.py` | 源码文本扫描与符号引用白名单校验 | 破坏图谱公开服务契约，绕过学情融合与安全脱敏机制 |
| **INV-06** | **数据生命周期三层隔离** | `data/raw/` 包含 Excel 原始源；`data/seeds/` 包含 5 份核心 JSON；`data/runtime/` Git 跟踪文件数严格为 0 | `tests/architecture/test_data_lifecycle.py` | 文件系统断言 + `git ls-files data/runtime` 命令调用 | 动态脏数据污染 Git 仓库历史，冷启动依赖丢失，数据冲突风险 |
| **INV-07** | **API 公开契约 100% 冻结** | 18 个 `/api/*` 业务端点 + 1 个 `/` 根端点，HTTP Method、Path、请求/响应模型严格匹配 | `tests/architecture/test_api_contract.py` | 动态反射 `app.main.app.routes` 提取全部 APIRoute 进行集合比对 | 前后端联调破坏，客户端功能大面积白屏或网络 404/422 报错 |
| **INV-08** | **前端 API 契约冻结** | `frontend/src/api.ts` 自 Phase 2.1 起与起点保持零破坏，前端调用端点全覆盖 | `tests/architecture/test_api_contract.py` | 前端源码 Token 比对与断言 | 破坏前端客户端网络契约，产生兼容性断层 |
| **INV-09** | **核心数学模型与决策契约不可篡改** | BKT 参数严格 `0.20/0.10/0.20/0.10`；作答轨迹精确 `0.2000->0.1273->0.4566->0.8118`；决策矩阵严格 5 组合法配对 | `tests/architecture/test_domain_contracts.py` | 单元数学断言 + 3 步作答序列模拟 + Canonical JSON 字节 SHA-256 哈希 | 认知追踪算法失真，学生掌握度评判失准，路径推荐决策紊乱 |
| **INV-10** | **测试边界绝对隔离** | `pytest --collect-only -q` 必须严格只收集当前项目测试，彻底隔离外部参考项目测试套件 | `pyproject.toml` 配置与 Bare Pytest Collection 断言 | `testpaths = ["tests"]` 约束与收集数量校验 | 外部参考项目代码侵入测试，测试结果不可信且执行极度缓慢 |
| **INV-11** | **单向分层依赖适应度函数** | 全系统严格遵循 `Core <- Domain <- Infrastructure / Services <- API` 单向流动，杜绝跨层与反向依赖 | `tests/architecture/test_dependencies.py` | AST 依赖拓扑图遍历与分层白名单检查 | 产生循环依赖、架构腐化，单体模块解耦彻底失败 |
| **INV-12** | **零外部重型组件入侵** | 全系统禁止引入 Redis, Celery, RabbitMQ, Kafka, Docker 等过度设计基础设施 | `pyproject.toml` 依赖项审查与架构静态断言 | AST / 配置扫描 | 本地无法轻量化运行与测试，运维复杂度指数级上升 |

---

## 二、本地与 CI 自动化执行指南

### 1. 单独运行架构适应度测试套件
```powershell
pytest tests/architecture/ -v
```
**期望结果**：17 passed in < 1.5s。

### 2. 运行全系统测试套件（含架构、单元、组件、集成测试）
```powershell
pytest -q
```
**期望结果**：143 passed in < 5s。

### 3. 运行前端完整性测试与生产构建
```powershell
node --experimental-strip-types --test frontend/test/*.test.ts
cd frontend && npm run build
```
**期望结果**：37 passed in < 300ms，构建输出 0 错误。
