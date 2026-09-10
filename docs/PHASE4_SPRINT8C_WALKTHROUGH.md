# 学海智导 (Xuehai Zhidao) — Phase 4 / Sprint 8-C 交付 Walkthrough
## Learning Outcome & Progress Intelligence: 掌握度历史 + 错题复盘 + 基础教师学习分析

**Sprint 版本**: Phase 4 / Sprint 8-C  
**基线 Commit**: `940cfb0` (Sprint 8-B)  
**验收状态**: **ALL 14 BROWSER UAT SCENARIOS PASS (100%), ALL GATES PASS**  
**红线约束**: `app/`, `tests/`, `data/seeds/` 严格 0-diff 冻结  

---

## 目录
1. [Sprint 8-C 目标与核心成果](#一sprint-8-c-目标与核心成果)
2. [三位一体系统架构与算法设计](#二三位一体系统架构与算法设计)
   - [2.1 C1: 学生全景掌握度与活动时间轴](#21-c1-学生全景掌握度与活动时间轴)
   - [2.2 C2: 错题复盘本与双向学习闭环](#22-c2-错题复盘本与双向学习闭环)
   - [2.3 C3: 教师学情分析驾驶舱与单生下钻](#23-c3-教师学情分析驾驶舱与单生下钻)
3. [核心红线与系统不变量审计](#三核心红线与系统不变量审计)
4. [两大闭环验证与运行实证](#四大闭环验证与运行实证)
   - [4.1 学生端闭环: 学习 → 测验 → BKT更新 → 历史沉淀 → 错题复盘 → 重新学习/练习](#41-学生端闭环)
   - [4.2 教师端闭环: 全班宏观 → 共性卡点 → 预警排查 → 单生深潜档案](#42-教师端闭环)
5. [Playwright Chromium 真实浏览器 UAT 结果与截图索引](#五playwright-chromium-真实浏览器-uat-结果与截图索引)
6. [质量门禁与自动化测试矩阵](#六质量门禁与自动化测试矩阵)
7. [变更文件清单与提交规范](#七变更文件清单与提交规范)
8. [后续演进建议 (Sprint 8-D / Phase 5)](#八后续演进建议-sprint-8-d--phase-5)

---

## 一、Sprint 8-C 目标与核心成果

Sprint 8-C 将 Sprint 8-A/8-B 已产生的底层学习行为事件（`CONCEPT_VIEW`、`QUESTION_ATTEMPT`）、BKT 学情状态、知识图谱及动态航线沉淀为直接面向学生与教师的高价值认知与分析系统：

1. **统一学习成效沉淀引擎 (Analytics Engine)**：在 `gateway/learning/analytics/` 实现了基于事件溯源与 BKT 状态投影的纯净分析计算服务，确保零 Mock 假数据。
2. **学生端全维成效看板 (Progress & Wrong Answers)**：
   - 全景 30 知识点掌握度矩阵（掌握 / 发展中 / 待巩固 / 未学习 四态分类）。
   - 掌握度演进历史趋势折线与不可篡改的事件时间轴。
   - 结构化错题复盘本，提供详细解析、错误归因，并直连“📖 重新学习微卡”与“✏️ 再次练习突破”。
3. **教师端宏观驾驶舱与单生下钻深潜 (Teacher Analytics Cockpit)**：
   - 4 项班级全貌核心 KPI（总学生数、活跃率、班级均分、预警生数）。
   - Top-5 班级共性薄弱卡点透视，提供精准的教研干预建议。
   - 全量学生学情花名册，支持风险等级筛选与单生“学情档案”弹窗深潜下钻。

---

## 二、三位一体系统架构与算法设计

### 2.1 C1: 学生全景掌握度与活动时间轴

- **服务模块**: `gateway/learning/analytics/service.py` (`get_student_progress`)
- **数据源**:
  - `bkt_state_service.get_all_student_states(student_id)` 获得学生实际 BKT 概率状态。
  - `knowledge_graph_service.get_all_knowledge_points()` 确保全谱 30 个知识点全覆盖投影。
  - `learning_events.jsonl` 获取真实追加事件，按时间倒序构建 `history_timeline`。
- **掌握度状态计算统一规范**:
  - $P(L) \ge 0.80$：`MASTERED`（已掌握，绿徽）
  - $0.60 \le P(L) < 0.80$：`DEVELOPING`（发展中，蓝徽）
  - $P(L) < 0.60$ 且已有练习尝试：`NEEDS_REINFORCEMENT`（待巩固/薄弱，黄/红徽）
  - 无尝试记录且 $P(L) = 0.20$（初始默认值）：`UNSTUDIED`（未学习，灰徽）
- **整体掌握度**: 30 个考点 $P(L)$ 的算术平均值 $\bar{P} = \frac{1}{30}\sum_{i=1}^{30} P(L_i)$，与教师端计算完全一致。

### 2.2 C2: 错题复盘本与双向学习闭环

- **服务模块**: `gateway/learning/analytics/service.py` (`get_student_wrong_answers`)
- **真实投影与去重**:
  - 扫描真实 `QUESTION_ATTEMPT` 事件且 `is_correct == False`。
  - 按题号归纳，保留该题最近一次错误作答、发生时间及累计错误次数。
  - 关联试题库题干、全量选项与详解，以及考点当前最新 BKT 掌握度与路径状态。
- **确定性复习优先级算法**:
  - 若考点掌握度 $< 0.60$ 且错次 $\ge 2$：`HIGH`（高优巩固）
  - 若考点掌握度 $< 0.80$：`MEDIUM`（中优跟进）
  - 其余：`LOW`（低优温习）
- **双向学习闭环**:
  - **闭环 A**: 点击“📖 重新学习微卡” → 触发 `CONCEPT_VIEW` 事件并呼出概念卡抽屉，加深理解。
  - **闭环 B**: 点击“✏️ 再次练习突破” → 唤起该知识点微测验抽屉，重答正确后驱动 BKT 更新并刷新错题本。

### 2.3 C3: 教师学情分析驾驶舱与单生下钻

- **服务模块**: `gateway/learning/analytics/service.py` (`get_teacher_overview`, `get_teacher_student_detail`)
- **前端组件**:
  - `frontend/src/layouts/TeacherLayout.tsx`（驾驶舱看板）
  - `frontend/src/components/teacher/TeacherStudentDetailModal.tsx`（单生深潜档案弹窗）
- **班级宏观 KPI**:
  - 班级总学生、活跃学生数、全班平均掌握度、预警学生数（掌握度 $< 0.60$ 或错题多）。
- **共性薄弱点算法 (Weak Knowledge Points)**:
  - 遍历 30 知识点在所有学生中的平均掌握度及错误总次数。
  - 按掌握度升序（最弱优先）、错次降序排列，截取 Top-5。
  - 输出针对性教学干预建议（如“建议课堂开展需求价格弹性微观测算案例精讲”）。
- **单生下钻深潜**:
  - 点击学生行右侧“学情档案”，无刷新打开深潜弹窗，展示该生 30 考点分布、动态航线焦点、错题详情及时间轴。

---

## 三、核心红线与系统不变量审计

| 序号 | 核心红线 / 系统不变量 | 审计结果 | 验证证据 |
|:---:|:---|:---:|:---|
| 1 | `app/`, `tests/`, `data/seeds/` 严格 0-diff | **严格遵守 (0 diff)** | `git diff --stat -- app/ tests/ data/seeds/` 为空 |
| 2 | 不产生第二套掌握度标准 | **严格遵守** | 复用 `MASTERY_THRESHOLD_HIGH = 0.80`, `LOW = 0.60`，公式及参数完全统一 |
| 3 | 不伪造空数据 / 无 Mock 假数据 | **严格遵守** | 新学生纯净空白；所有进展、错题、时间轴均源自真实追加事件 |
| 4 | 教师端绝对只读 | **严格遵守** | 教师端路由仅有只读 GET 接口，禁止产生任何 BKT 或路径状态变更 |
| 5 | AI Judge 生产隔离 | **严格遵守** | `allow_production_decision = False` 硬门禁保持，影子运行不影响核心决策 |
| 6 | 异常防御与数据隔离 | **严格遵守** | 不存在学生返回 404，不引发 500；跨生切换状态物理隔离 |

---

## 四、两大闭环验证与运行实证

### 4.1 学生端闭环

```text
[初始状态: 新学生纯白]
       ↓
[微测验作答正确: Q-K08-01 答对] → 写入 QUESTION_ATTEMPT (is_correct=True) → BKT 掌握度升至 0.4566
       ↓
[微测验故意答错: Q-K01-01 选错] → 写入 QUESTION_ATTEMPT (is_correct=False) → BKT 更新
       ↓
[成果沉淀: 成效页面] → 30 考点矩阵实时呈现 K08 发展中、K01 待巩固
       ↓
[错题复盘本归纳] → 实时出现 Q-K01-01 错题卡片，标定 HIGH 优先级，展示试题解析
       ↓
[闭环 A: 重新学习] → 点击“重新学习微卡”呼出概念卡抽屉，产生 CONCEPT_VIEW 事件
       ↓
[闭环 B: 再次练习] → 点击“再次练习突破”调起微测验抽屉，完成练习巩固
```

### 4.2 教师端闭环

```text
[教师进入宏观驾驶舱 /teacher]
       ↓
[班级 4 项 KPI 概览: 覆盖总学生数与平均掌握度]
       ↓
[班级共性薄弱卡点 Top-5 洞察] → 发现薄弱考点与成因
       ↓
[全班学生名单筛选] → 发现存在预警标签的学生
       ↓
[点击单生“学情档案”] → 呼出下钻深潜弹窗，精准查看该生 30 考点分布与历史时间轴
       ↓
[生成教学干预策略] → 形成针对性课后辅导
```

---

## 五、Playwright Chromium 真实浏览器 UAT 结果与截图索引

在 `scripts/uat_sprint8c_browser.py` 中，使用真实无头 Chromium 浏览器，对真实运行中的前端（Port 5173）与后端（Port 8000）执行了全流程 14 个测试场景，**14 个场景 100% 全部通过**：

| 编号 | UAT 测试场景描述 | 执行结果 | 对应截图凭证 |
|:---:|:---|:---:|:---|
| **A1** | 新学生学习进展空数据规范展示 | **PASS** | `artifacts/uat_screenshots/uat8c_01_empty_progress.png` |
| **A2** | 新学生错题本零错题纯净空状态 | **PASS** | `artifacts/uat_screenshots/uat8c_02_empty_wrong_answers.png` |
| **B** | 首次微测验提交答对并驱动 BKT 更新 | **PASS** | `artifacts/uat_screenshots/uat8c_03_first_quiz_correct.png` |
| **C** | 第二次微测验故意答错产生真实错题 | **PASS** | `artifacts/uat_screenshots/uat8c_04_second_quiz_wrong.png` |
| **D** | 错题复盘本智能归纳与详细解析展示 | **PASS** | `artifacts/uat_screenshots/uat8c_05_wrong_answer_review.png` |
| **E** | 错题闭环 A: 📖 重新学习微卡抽屉联动 | **PASS** | `artifacts/uat_screenshots/uat8c_06_concept_card_relearn.png` |
| **F** | 错题闭环 B: ✏️ 再次练习突破测验抽屉联动 | **PASS** | `artifacts/uat_screenshots/uat8c_07_quiz_remediation.png` |
| **G** | 掌握度演进历史趋势折线与真实事件时间轴 | **PASS** | `artifacts/uat_screenshots/uat8c_08_progress_timeline.png` |
| **H** | 页面硬刷新状态稳定性与持久化验证 | **PASS** | `artifacts/uat_screenshots/uat8c_09_reload_stability.png` |
| **I** | 学生切换与学情数据严格隔离 | **PASS** | `artifacts/uat_screenshots/uat8c_10_student_isolation.png` |
| **J** | 教师端宏观驾驶舱全景 KPI、薄弱点与花名册 | **PASS** | `artifacts/uat_screenshots/uat8c_11_teacher_dashboard.png` |
| **K** | 教师端单生下钻深潜档案弹窗联动与数据渲染 | **PASS** | `artifacts/uat_screenshots/uat8c_12_teacher_student_detail.png` |
| **L** | 学生端与教师端全局掌握度字节级一致性断言 | **PASS** | 断言 $\vert P_{stu} - P_{tch} \vert < 0.0001$ 成立 |
| **M** | 教师端下钻新初始化学生无假数据安全性 | **PASS** | 验证 0 次练习、0 条错题、0 条脏事件 |
| **N** | 异常学生 ID 请求鲁棒性断言 (404/422，绝不 500) | **PASS** | 验证未知学生请求均返回规范 404 |
| **SEC** | 敏感信息过滤与未作答试题脱敏安全审查 | **PASS** | 页面无 API Key 泄露，公开试题严禁携带答案及解析 |

---

## 六、质量门禁与自动化测试矩阵

### 6.1 后端单元与集成测试 (`pytest gateway/tests/`)
- `gateway/tests/test_sprint8c_analytics.py`: **22/22 passed**
- 全量 Gateway 测试套件: **295/295 passed in 3.80s**

### 6.2 前端类型与契约测试
- TypeScript 静态检查: `npm run typecheck` → **0 errors**
- 前端测试套件: `npm test` → **179/179 passed (20 suites)**
- 生产打包验证: `npm run build` → **Vite build succeeded**

### 6.3 质量门禁执行汇总
1. `scripts/sprint8c_quality_gate.py`: **10/10 PASS**
2. `scripts/sprint8b_dynamic_path_gate.py`: **12/12 PASS**
3. `scripts/ai_judge_shadow_gate.py`: **12/12 PASS**
4. `scripts/quality_gate.py`: **5/5 PASS**

---

## 七、变更文件清单与提交规范

### 新增文件
- `gateway/learning/analytics/__init__.py`: 分析模块导出定义
- `gateway/learning/analytics/models.py`: Pydantic 规范响应模型
- `gateway/learning/analytics/service.py`: 纯净成效沉淀服务计算层
- `gateway/tests/test_sprint8c_analytics.py`: 后端 22 项全维度回归测试集
- `frontend/src/components/student/ProgressOverview.tsx`: 掌握度概览与时间轴组件
- `frontend/src/components/student/WrongAnswerReview.tsx`: 错题复盘与闭环操作组件
- `frontend/src/components/teacher/TeacherStudentDetailModal.tsx`: 教师单生下钻深潜弹窗
- `frontend/test/sprint8c_outcome_contract.test.ts`: 前端契约与状态流转测试
- `scripts/sprint8c_quality_gate.py`: Sprint 8-C 10 项严苛质量门禁脚本
- `scripts/uat_sprint8c_browser.py`: 14 场景全自动化 Playwright UAT 脚本
- `artifacts/uat_results.json`: UAT 自动化执行报告
- `artifacts/uat_screenshots/uat8c_01~12.png`: 12 张真实浏览器运行截图

### 修改文件
- `gateway/api.py`: 挂载 5 个分析 API 端点并增强事件写入适配
- `frontend/src/types.ts`: 补全进展、错题与教师看板类型定义
- `frontend/src/api.ts`: 封装成效与教师 API 请求客户端
- `frontend/src/layouts/StudentLayout.tsx`: 挂接档案页三项子导航（进展、错题、雷达）
- `frontend/src/layouts/TeacherLayout.tsx`: 升级真实教师学情分析驾驶舱
- `frontend/src/components/student/TasksQuickNav.tsx`: 补全快捷导航与指标联动

---

## 八、后续演进建议 (Sprint 8-D / Phase 5)

1. **错题本多维筛选与导出**: 支持按章节（Chapter）、难度（Difficulty）筛选错题，并支持一键导出 PDF/Markdown 错题集。
2. **班级群体认知对比雷达图**: 在教师端引入全班掌握度中位数与离散度分析，帮助教师识别两极分化考点。
3. **自适应补偿题推送**: 当学生在微测验中同一知识点连续答错 2 次以上时，在错题复盘本中智能生成同构变形题推荐。
