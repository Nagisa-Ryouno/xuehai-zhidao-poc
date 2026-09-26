# 学海智导 (Xuehai Zhidao) — 交接封版说明书 (HANDOFF.md)

> **本项目已进入【功能冻结 (Feature Freeze) + 交接封版 (Handoff Freeze)】状态。**  
> **严禁开发新功能、严禁扩大产品范围、严禁篡改底层学习算法与评估数据。**

---

## 1. 项目简介 (Project Overview)

**学海智导** 是一个面向大学生的 **AI-assisted adaptive learning platform（人工智能辅助个性化自适应学习平台）**。  
以高校经济学核心基础课《微观经济学》（30 个拓扑考点图谱、130 项内部原生权威学习材料、12 项名校精选 MOOC 拓展微课）为教学实验载体，解决传统教学中“前置断层未可知、千人一面、缺乏即时闭环反馈”等问题。

---

## 2. 当前状态与 Git 基线 (Current Status & Git Baseline)

### 2.1 产品生命周期状态
- **产品生命周期**：**Feature Frozen (功能彻底冻结)**
- **开发策略**：**No New Feature Development (禁止任何新功能开发)**
- **最新阶段**：Sprint 10-D (Teacher Action Loop & Product Hardening) 封版
- **主要工作模式**：QA Hardening、代码可靠性整理、人工验收验证、缺陷记录与修复。

### 2.2 Git 交付事实基线 (Git Delivery Baseline)
- **交付分支 (Branch)**：`master`（主要交付分支），`main`（完全镜像同步，两者 SHA 严格一致）
- **交付 Tag**：`handoff-final-2026-09`（指向当前封版 HEAD）
- **历史 Freeze Tag**：`handoff-freeze-2026-09-r1`, `handoff-freeze-2026-09`, `v0.6.0`
- **远程仓库 (Remote)**：`origin` -> `https://github.com/Nagisa-Ryouno/xuehai-zhidao-poc.git`
- **工作区状态**：Clean（0 未跟踪文件，0 未提交修改）
- **推荐接手拉取命令**：
  ```bash
  git clone https://github.com/Nagisa-Ryouno/xuehai-zhidao-poc.git
  cd xuehai-zhidao-poc
  git checkout master
  ```

### 2.3 功能状态与验证分类 (Status & Verification Categories)
- **已实现且已自动化验证 (Implemented & Automated Verified)**：
  - 核心领域层：BKT 数学公式、PathState 状态机、Decision Core 决策矩阵、1-hop 局部动态重规划（`tests/`: 143 passed）；
  - 服务网关层：DeepSeek 伴学、离线启发保底、评测隔离、MOOC 目录与 API、资源中心、成效评估、保持度建议、教师干预（`gateway/tests/`: 606 passed, 2 skipped）；
  - 前端工程：组件契约、模型转换、防穿透锁、学生端会话、教师端 3-Tab（`frontend test`: 469 passed / 104 suites）；
  - 质量门禁：`sprint10c_final_integration_gate.py`（25/25 checks PASS）、`quality_gate.py`（5/5 GATES PASSED）；
  - 静态检查与打包：`npm run typecheck`（0 errors）、`npm run build`（Vite 生产打包成功）。
- **已实现但待人工体验核验 (Implemented, Pending Manual QA)**：
  - 学生端 5 步微时序学习会话（真实浏览器点击流畅度、正误反馈人本口吻）；
  - 移动端 375px 窄视口下的触控靶点、排版折行与防横向溢出；
  - 模态框打开与关闭时的背景滚动锁体验；
  - 教师端 30 考点诊断抽屉展开与学生全维档案卡片交互；
  - 中国大学 MOOC 外部跳转免责弹窗的浏览器点击与标签页呼起。
- **未验证事项 (Not Verified)**：
  - 中国大学 MOOC 外部第三方网站的实时 HTTP 连通性（测试处于离线隔离沙箱，不发起对外部外网的真实网络请求）；
  - 百人以上并发高负载下的服务器承载表现（当前架构定位于单机务实单体原型 POC）。

---

## 3. 系统核心架构与数据流 (Architecture)

### 3.1 核心自适应学习闭环 (Student Learning Loop)
```
[ 学生端 PWA ]
      │
      ▼ (启动考点研读 / 靶向练习)
[ 4步学习会话 (Learning Session) ]
      │
      ▼ (提交正式微测验作答)
[ 权威判题与题库服务 (Quiz Judging Service) ]
      │
      ▼ (产生正式学习事件 QUESTION_ATTEMPT)
[ 确定性学习引擎 (Authoritative Learning Engine) ]
      │
      ├─► [ 贝叶斯知识追踪 (BKT State & P(L) 掌握度) ]
      │
      └─► [ 局部自适应重规划决策核心 (Path Replanning Decision Core) ]
            │
            ▼ (1-hop 节点解锁 / 后继推进)
      [ 路径状态更新 (PathState: AVAILABLE / IN_PROGRESS / COMPLETED) ]
            │
            ▼
      [ 今日学习行动聚合 (Today Action Engine) ]
```

### 3.2 AI 辅助与影子决策边界 (AI Architecture Boundary)
```
                     [ 学生或系统触发 AI 诉求 ]
                                 │
                                 ▼
                     [ 候选生成与辅助交互 ]
        (AI Companion 答疑 / Guided Action / Candidate Recommendation)
                                 │
                                 ▼
                ┌────────────────────────────────┐
                │   【红线】：AI 绝非生产决策者   │
                │   allow_production_decision =  │
                │             False              │
                └────────────────┬───────────────┘
                                 │
                                 ▼
                    [ G1 确定性安全验证门禁 ]
               (Deterministic Gate & PII Firewall)
                                 │
                                 ▼
                  [ 仅作为观察者 / 解释者 / 候选项 ]
    (严禁写入 BKT、PathState、Mastery、QUESTION_ATTEMPT、learning_events)
```

### 3.3 教师端观察与干预中台 (Teacher Web Loop)
```
[ 教师管理中台 (Teacher Web) ]
      │
      ├─► 1. Observe (宏观观察): 班级平均掌握度、薄弱考点分布 Top-5、学情分布
      │
      ├─► 2. Understand (深度理解): 30 考点全景下钻、易错题目辨析、错误分布
      │
      ├─► 3. Identify (个体识别): 学生花名册、S001~S005 个体学情全维画像
      │
      └─► 4. Act (教学干预): 发起 REVIEW_CONCEPT / RETRY_PRACTICE / MARK_FOLLOWED
                │
                ▼
          【只读与辅助原则】：教师干预属于人本指导记录，
          独立持久化至教师历史，严禁篡改底层 BKT 掌握度与生产学习事件。
```

---

## 4. 绝对不可逾越的架构红线 (Architectural Invariants)

1. **学习引擎确定性 (Deterministic Learning Engine)**：
   - BKT 数学计算（`app/domain/bkt/`）、PathState 状态机（`app/domain/path_replanning/`）、决策核心（Decision Core）必须严格保持纯内存确定性计算，严禁引入随机性或概率漂移。
   - `app/`、`tests/`、`data/seeds/` 处于严格冻结状态，`git diff -- app/ tests/ data/seeds/` 必须恒为 0。
2. **教学测验与正式评测边界 (Quick Check vs Official Quiz)**：
   - **Quick Check**：纯伴学/微卡自检，必须显式携带 `allow_production_decision = False`，绝对不得产生 `QUESTION_ATTEMPT` 事件，绝对不得更新 BKT 掌握度或解锁路径。
   - **Official Quiz**：来自题库标准题目，由学生在任务卡或微测模态框中提交，产生合法 `QUESTION_ATTEMPT` 事件并驱动 BKT 演进。
3. **AI 隔离与会话物理隔离**：
   - AI 对话历史按学生物理隔离（`xuehai_companion_sessions_${studentId}`），切换学生时即刻重置。
   - AI 伴学 Prompt 严格限制在微观经济学专业领域，严禁越界或泄露底层算法术语（BKT、PathState）。
4. **教师干预零生产副作用**：
   - 教师动作仅记录在辅导建议流中，不改变学生的掌握度数值或学习事件流水。
5. **资源真实性与零伪造**：
   - 内部原生资源保持 130 项（`RESOURCE_CATALOG`）。
   - 中国大学 MOOC 外部资源保持 12 项精选示范（`MOOC_RESOURCE_CATALOG`），严禁为凑齐 30 考点而编造虚假章节、虚构 URL 或编造 100% 覆盖。

---

## 5. 快速启动与运行指南 (How To Run)

### 5.1 环境要求
- **Python**: $\ge$ 3.10 (已在 Python 3.13 验证)
- **Node.js**: $\ge$ 18 (推荐 Node 20+)
- **OS**: Windows / macOS / Linux

### 5.2 依赖安装
```bash
# 1. 后端依赖
pip install -r requirements.txt
# 或直接通过 pyproject.toml 安装:
pip install -e ".[dev,pipeline]"

# 2. 前端依赖
npm --prefix frontend install
```

### 5.3 启动后端服务网关
后端网关监听端口为 **8011**：
```bash
# 方式 1：标准启动
python -m uvicorn gateway.api:app --host 127.0.0.1 --port 8011 --reload

# 方式 2：使用项目脚本 (Windows PowerShell)
python scripts/run_gateway.py
```
- 健康检查端点：`http://127.0.0.1:8011/health`
- API 文档 Swagger UI：`http://127.0.0.1:8011/docs`

### 5.4 启动前端应用
前端 Vite 开发服务器监听端口为 **5173**：
```bash
npm --prefix frontend run dev
```
- 学生端访问地址：`http://localhost:5173/student`
- 教师端访问地址：`http://localhost:5173/teacher`
- 根路径重定向：访问 `http://localhost:5173/` 自动引导至 `/student`

### 5.5 外部大模型 (DeepSeek) 配置（可选）
本系统设计为**“离线可用、优雅降级”**：
- **未配置 API Key 时**：系统自动启用内置启发式推荐与离线伴学兜底，所有核心学习闭环、微测验、BKT 掌握度推导、路径重规划 100% 正常运行，控制台仅提示使用模拟响应。
- **配置真实 DeepSeek**：
  在系统环境变量或项目根目录 `.env` 中设置：
  ```bash
  DEEPSEEK_API_KEY=sk-your-actual-api-key
  DEEPSEEK_MODEL=deepseek-flash
  ```

---

## 6. 验证与质量测试命令 (Verification Commands)

新接手同学请严格按以下顺序执行全面验证：

```bash
# 1. 运行核心架构与领域测试 (143 项全通)
pytest tests/ -q

# 2. 运行网关与集成测试套件 (606 passed, 2 skipped)
pytest gateway/tests/ -q

# 3. 运行端到端产品门禁 (25/25 checks PASS)
python scripts/sprint10c_final_integration_gate.py

# 4. 运行前端自动化测试 (469 项全通)
npm --prefix frontend test -- --run

# 5. 前端 TypeScript 类型检查 (0 errors)
npm --prefix frontend run typecheck

# 6. 前端生产打包构建 (PASS)
npm --prefix frontend run build

# 7. 检查工作区数据零污染（正常完成的 gateway pytest 会通过 session fixture 恢复指定运行态文件；测试完成后仍必须执行 git diff -- data/ 进行最终核验）
git diff -- data/
```

---

## 7. 目录资产与资源真实性清册

- **知识图谱 (Knowledge Graph)**：`data/seeds/knowledge_graph.json`，共 30 个考点（K01~K30）、42 条拓扑前置依赖边、S001~S005 五名学生共 60 条基准学习记录。
- **内部原生资源 (Internal Resources)**：`gateway/learning/resources/catalog.py`，共 130 项原生学习材料，覆盖全部 30 个考点。
- **中国大学 MOOC 外部资源 (MOOC Resources)**：`gateway/learning/resources/mooc_catalog.py`，精选 12 项优质名校微课（北京大学《微观经济学之供给与需求》PKU-1003090003 与武汉大学《微观经济学》whu-23003 官方十讲结构）。其余 18 个考点如实标记无外链 MOOC，由平台内部原生资源覆盖，绝不伪造。
- **题库资产 (Quiz Bank)**：`gateway/content/quiz_bank.py` 与 `frontend/src/components/student/quizBankData.ts`，共 35 道权威微测试题，覆盖全部 30 个考点。

---

## 8. 接手同学排查与调试索引 (Troubleshooting FAQ)

| 现象 | 排查定位 | 恢复措施 |
|:---|:---|:---|
| 运行 `pytest` 后 `git status` 提示 `data/` 文件有改动 | `gateway/tests/conftest.py` 自动备份还原机制未触发或被强制中断 | 执行 `git checkout -- data/` 恢复干净基线 |
| 前端提示跨域或 API 连接失败 | 检查后端网关是否在 8011 端口启动 | 确认 `uvicorn` 正在监听 `127.0.0.1:8011` |
| 模态框打开时背景滚动条消失导致抖动 | `frontend/src/utils/useBodyScrollLock.ts` 滚动条补偿逻辑 | 检查浏览器是否启用了浮动隐藏式滚动条 |
| AI 伴学返回超时或提示不可用 | 未配置 `DEEPSEEK_API_KEY` 或外部网络连接超时 | 属于设计内的离线安全回退，检查网络或补充 `.env` 配置 |

---

## 9. 当前已知问题与局限 (Known Issues & Limitations)

1. **外部 MOOC 资源连通性依赖第三方网络**：
   - 12 项精选 MOOC 微课严格指向中国大学 MOOC 官方真实公开课程（PKU-1003090003 与 whu-23003）。自动化测试在离线沙箱中验证了元数据、URL 协议与跳转逻辑，但无法保证第三方 MOOC 平台服务器的 7×24h 绝对实时可用性。若外部平台维护，前端将提示用户通过平台内部原生材料学习。
2. **轻量离线启发式伴学回答较为简短**：
   - 在未配置 `DEEPSEEK_API_KEY` 时，伴学系统自动回退至离线关键词与启发式模板引擎。此模式保障学习闭环绝对不阻断，但生成内容的丰富度逊于接入真实 LLM API。
3. **架构规模边界**：
   - 本系统为国家级大创项目教育科技原型（POC），底层采用轻量原子文件替换持久化（`data/*.json`, `data/*.jsonl`），适合单机/演示/教学试验场景，不适用于数千并发的高吞吐生产环境。

---

## 10. 接手同学第一步快速指引 (First Step for Next Engineer)

下一位同学接手仓库后的**唯一标准第一步**：

```bash
# 1. 验证工作区与分支
git status
git branch

# 2. 依次运行全量自动化门禁确认当前基线完全绿灯 (约 30 秒)
pytest tests/ -q && pytest gateway/tests/ -q && python scripts/sprint10c_final_integration_gate.py && npm --prefix frontend test -- --run && npm --prefix frontend run typecheck && npm --prefix frontend run build

# 3. 启动前后端服务并参照 TESTING.md 开始人工体验点测
# 终端 1 (后端网关):
python -m uvicorn gateway.api:app --host 127.0.0.1 --port 8011 --reload
# 终端 2 (前端界面):
npm --prefix frontend run dev
```
