# Sprint 10-C Phase 5 — Student UX/UI Usability Audit Report

**审计定位**: 学海智导 (Xuehai Zhidao) 学生端可用性全面审计 (Real Student User Usability Audit)  
**审计视角**: 第一次使用产品的普通大学生（无产品培训、无源码背景、任务导向）  
**审计视口**: 375×812 (iPhone SE/Mini), 390×844 (iPhone 12/13/14), 1440×900 (Desktop)  
**审计任务**: Task A (首屏与任务识别) / Task B (完整学习会话) / Task C (AI推荐与资源) / Task D (测验体验) / Task E (导航与返回) / Task F (离线与异常)

---

## 一、审计概述 (Audit Summary)

本次审计通过真实 Chromium 浏览器自动化遍历，结合人工专业走查，全面覆盖学生端 15 个主要交互界面与状态组件。

| 严重等级 | 定义 | 发现问题数 | 状态 |
| :--- | :--- | :---: | :--- |
| **P0** | 用户无法完成核心学习任务（阻塞性） | **0** | 已清零（Phase 2-4 已保证主链路连通） |
| **P1** | 严重阻碍认知 / 明显困惑 / CTA 视觉冲突竞争 | **4** | 待本阶段优先修复 |
| **P2** | 明显可用性缺陷 / 触控靶点不足 / 反馈遮挡 / 黑话残留 | **5** | 待本阶段优先修复 |
| **P3** | 视觉层级微调 / 间距一致性 / 辅助文案打磨 | **3** | 伴随优化 |
| **合计** | - | **12** | - |

---

## 二、Top 10 UX Problems (重点可用性问题总览)

| 序号 | 问题 ID | 严重级别 | 页面/组件 | 问题核心现象 | 用户影响 |
| :---: | :--- | :---: | :--- | :--- | :--- |
| 1 | **UX-ISSUE-01** | **P1** | `StudentHome` / `TodayActionCard` & `CurrentFocusCard` | 首屏存在 5 个主要行动按钮同时抢占视线，今日行动与规划焦点考点不一致时无主次区分 | 刚进来的学生不知道今天到底该学哪一个、该点哪个按钮，认知负荷过大 |
| 2 | **UX-ISSUE-02** | **P1** | `LearningSessionModal` (RESULT Step) | 测验未达标 (<60%) 时，主 CTA 仍为绿色的“继续下一步”，与上方的“建议巩固”文案直接矛盾 | 引导学生盲目跳过薄弱考点，造成挫败感和知识断层 |
| 3 | **UX-ISSUE-03** | **P1** | `LearningSessionModal` (Header / 全局) | 学习会话缺少当前阶段步骤进度与预期耗时引导，学生进入后不知道有几步、要多久 | 学生产生“这个窗口到底什么时候能学完”的不可预期感 |
| 4 | **UX-ISSUE-04** | **P1** | `BottomNav` / `StudentLayout` | 移动端底部导航仅 4 项缺“学习资源”，学生进入资源页后底栏无任何高亮，无法辨别位置 | 移动端路径感知割裂，学生在资源中心无法通过底栏返回或识别当前 Tab |
| 5 | **UX-ISSUE-05** | **P2** | `LearningSessionModal` (QUIZ Step) | 移动端 (375x812) 答题提交后，解析框内容过长将“下一题”按钮挤出首屏且无自动滚动 | 学生以为页面卡住或提交无响应，不知道需要向下滑动寻找按钮 |
| 6 | **UX-ISSUE-06** | **P2** | `LearningSessionModal` (RESOURCE Step) | AI 推荐理由中偶现底层技术编码 (如 “建议优先攻克考点 K02”) | 学生不理解 “K02” 是什么，产生技术黑话疏离感 |
| 7 | **UX-ISSUE-07** | **P2** | `LearningSessionModal` (Header) | 关闭按钮 (`aria-label='关闭学习会话'`) 触控盒仅 36x36px，移动端手指极易点空 | 学生想退出或暂停学习时反复点不中 X，产生误触困扰 |
| 8 | **UX-ISSUE-08** | **P2** | `LearningSessionModal` (RESOURCE Step) | “返回概念微卡” 按钮高度仅 32px，低于移动端 44px 人机工效基准 | 移动端单手操作不易触达与点击 |
| 9 | **UX-ISSUE-09** | **P2** | `Header` (Mobile / Desktop) | 顶部角色切换按钮 (34x26px) 与学生切换下拉框垂直触控区域偏小 | 在小屏手机上容易误触或点到边缘无效 |
| 10 | **UX-ISSUE-10** | **P3** | `RecentProgressCard` | “查看完整学情档案”纯文字链接高度仅 16px，无明显点击反馈区域 | 触控不明确，学生不易发现和点按 |

---

## 三、UX Issue Inventory 详细审计清单

### 1. UX-ISSUE-01: 首屏双卡片 CTA 恶性竞争与主次层级模糊
- **ID**: `UX-ISSUE-01`
- **Severity**: **P1**
- **Page**: `StudentHome.tsx` / `TodayActionCard.tsx` / `CurrentFocusCard.tsx`
- **User scenario**: 新用户或每天首次打开学海智导的学生，进入首页准备开始学习。
- **Observed problem**:
  - `TodayActionCard` 呈现蓝色主按钮（如“重新学习”/“开始学习”），针对考点 A（例如机会成本）。
  - 下方的 `CurrentFocusCard` 同样拥有高饱和度靛蓝色背景、大尺寸进度条，以及底部的 4 个彩色按钮：`📖 考点精要速览`、`📚 推荐学习材料`、`🤖 问问 AI`、`继续挑战微测验`（针对考点 B，如需求价格弹性）。
  - 全屏视野内同时呈现 5 个各不相同的可操作按钮。
- **Why it is a problem**: 违背“Primary / Secondary / Supporting”层级原则。两个卡片都在召唤用户“快来测验/快来学”，且考点还不同。用户第一眼产生严重犹豫：“我到底该学哪个？是今天推荐的，还是当前焦点的？”
- **User impact**: 用户决策阻滞，初次体验产生困惑，无法在 30 秒内明确单一行动目标。
- **Evidence**: `audit_task_a_home_375x812.png`, `audit_task_a_home_390x844.png`, `hierarchy_observations` 记录 5 个同时可见的主行动。
- **Recommended solution**:
  1. `TodayActionCard` 确立为全页唯一的 **PRIMARY HERO** 行为中心，视觉权重最高。
  2. `CurrentFocusCard` 调整为 **ROADMAP CONTEXT（学习航线与整体全景）**，强化其“你在课程总图中的位置”语义；将其底部的 `继续挑战微测验` 改为次级边框按钮（Secondary Button），其他辅助操作（速览、材料、问AI）做成轻量胶囊/工具条，绝不与今日主任务 CTA 竞争注意力。
  3. 当 TodayAction 与 CurrentFocus 考点不同时，在 TodayAction 上标明“今日优先任务”，在 CurrentFocus 上标明“航线主线（巩固后继续）”，逻辑完全自洽。
- **Implementation cost**: Low (调整卡片按钮层级与标签辅助语).

---

### 2. UX-ISSUE-02: 测验未达标 (<60%) 成果页主 CTA 导向倒错
- **ID**: `UX-ISSUE-02`
- **Severity**: **P1**
- **Page**: `LearningSessionModal.tsx` (RESULT Step)
- **User scenario**: 学生在随堂小测中仅答对 0 题或 1 题（正确率 <60%），进入结算成果页。
- **Observed problem**:
  - 提示文案写着：“本轮小测中部分核心机制存在薄弱点，建议重新巩固概念微卡或稍后再练一次。”
  - 但页面最醒目、最突出的大绿色渐变主按钮却是：`继续下一步` (`result-next-action-btn`)，而 `再练一次` 是弱化的白底灰色细边框按钮。
- **Why it is a problem**: 视觉引导与教学建议产生直接背离。学生心理本能会去点那个最显眼的大按钮（“继续下一步”），导致薄弱考点未经消化就被直接跳过，破坏自适应学习闭环。
- **User impact**: 盲目跳关导致后续进阶知识更加学不懂，降低系统学习效果与信任度。
- **Evidence**: `audit_task_b_07_session_result.png`, 代码第 1248-1262 行。
- **Recommended solution**:
  - 当正确率 `>= 60%` 时：保持 `继续下一步` 为 Primary 主按钮，`再练一次` 为 Secondary。
  - 当正确率 `< 60%` 时：动态将 `巩固重测 / 再练一次` 提升为 Primary 主按钮（例如 Indigo 亮色大按钮），将 `继续下一步` 降为 Secondary 次级按钮，形成言行一致的正向教学引导。
- **Implementation cost**: Very Low.

---

### 3. UX-ISSUE-03: 学习会话缺乏明确的线性步骤与耗时预期感知
- **ID**: `UX-ISSUE-03`
- **Severity**: **P1**
- **Page**: `LearningSessionModal.tsx` (Header 及整体体验)
- **User scenario**: 学生点击“开始学习”唤起全屏模态框，准备进入沉浸式会话。
- **Observed problem**:
  - 模态框 Header 只有一个孤立的小胶囊标签（如“考点导引”或“概念精读”），缺乏清晰的步骤链展示（例如 `导引 ➔ 精读 ➔ (选学) ➔ 微测 ➔ 结算`）。
  - 学生不知道这次会话一共有几步、当前在第几步、测验有几道题、预计需要 5 分钟还是 30 分钟。
- **Why it is a problem**: 缺乏预期的黑盒流程会引发学生的使用焦虑，容易中途直接叉掉退出。
- **User impact**: 中途弃学率上升，不知道几分钟能学完。
- **Evidence**: `audit_task_b_01_session_entry.png`, `audit_task_b_02_session_concept.png`.
- **Recommended solution**:
  - 在模态框 Header 增加轻量级极简步骤进度条（如 3 节点微型进度或 `第 1 步 / 共 3 步 · 预计 5 分钟`），让学生对学习节奏一目了然。
- **Implementation cost**: Low.

---

### 4. UX-ISSUE-04: 移动端底部导航缺失“学习资源”，导航位置感断裂
- **ID**: `UX-ISSUE-04`
- **Severity**: **P1**
- **Page**: `BottomNav.tsx` / `navConfig.ts` / `StudentLayout.tsx`
- **User scenario**: 学生在手机端通过主页卡片点击“推荐学习材料”进入 `/student/resources`。
- **Observed problem**:
  - 桌面端导航有 5 项（今日任务、学习资源、知识图谱、学情档案、AI伴学）。
  - 移动端 `BottomNav` 仅写死了 4 项（今日任务、知识图谱、学情档案、AI伴学），未收纳“学习资源”。
  - 当学生身处 `/student/resources` 时，底部没有任何一个 Tab 处于激活状态，底栏成了“哑巴”。
- **Why it is a problem**: 移动端用户迷路，不知道自己在哪个主功能区，无法一键切换回任务或图谱。
- **User impact**: 导航状态脱节，影响移动端整体可用性。
- **Evidence**: `audit_task_e_01_nav_tasks.png` ~ `audit_task_e_04_nav_assistant.png`, `navConfig.ts` 源码。
- **Recommended solution**:
  - 统一为标准 5-Tab 移动底栏（今日任务、资源中心、知识图谱、学情档案、AI伴学）。375px 下每个 Tab 占 75px，完全符合苹果与谷歌标准的 48px 触控要求与主流 App 惯例。
- **Implementation cost**: Low.

---

### 5. UX-ISSUE-05: 测验提交后解析过长遮挡“下一题”CTA，移动端无平滑视口引导
- **ID**: `UX-ISSUE-05`
- **Severity**: **P2**
- **Page**: `LearningSessionModal.tsx` (QUIZ Step)
- **User scenario**: 移动端学生在做题界面选中选项，点击“提交答案”。
- **Observed problem**:
  - 提交后立刻展开【即时反馈区】与【详细解析】。在 375×812 视口下，详细解析展开后直接把“下一题 / 查看本次测验结果”按钮推到了屏幕视口以下。
  - 页面没有自动滚动到底部，学生停留在选项和解析顶部，看不到“下一题”按钮。
- **Why it is a problem**: 学生不知道下一步该点哪里，部分学生会以为系统死锁或无法继续。
- **User impact**: 答题节奏被打断，产生误触或焦虑。
- **Evidence**: `audit_task_b_06_quiz_feedback.png`, 视口高度测算。
- **Recommended solution**:
  - 在提交答案并获得反馈后，执行一次平滑微滚 `scrollIntoView({ behavior: 'smooth' })` 将底部“下一题”按钮呈现于视口内；同时确保反馈卡片排版适度精简，不出现无意义大空白。
- **Implementation cost**: Low.

---

### 6. UX-ISSUE-06: 资源推荐理由中偶现底层技术代号 (如 K02)
- **ID**: `UX-ISSUE-06`
- **Severity**: **P2**
- **Page**: `LearningSessionModal.tsx` (RESOURCE Step)
- **User scenario**: 学生在资源推荐卡片中查看“💡 为什么推荐”。
- **Observed problem**:
  - 部分推荐理由文本包含：“建议优先攻克考点 K02 并学习对应辅导资源。”
- **Why it is a problem**: “K02” 是知识库底层内部主键代号，普通大学生不知道 K02 对应什么，显得冰冷且不专业。
- **User impact**: 破坏人本温度，产生技术疏离感。
- **Evidence**: `audit_data['tasks']['task_c_ai_reasons']` 实测抓取到包含 "K02"。
- **Recommended solution**:
  - 在前端渲染理由前，增加人本名称替换或正则脱敏机制：将 `K\d+` 动态置换为当前考点人本名（例如“机会成本与生产可能性边界”或“当前考点”），确保用户可见文本 100% 自然。
- **Implementation cost**: Very Low.

---

### 7. UX-ISSUE-07: 学习会话弹窗关闭按钮 (X) 触控盒仅 36x36px
- **ID**: `UX-ISSUE-07`
- **Severity**: **P2**
- **Page**: `LearningSessionModal.tsx` (Header)
- **User scenario**: 手机单手操作时，学生想关闭弹窗返回首页。
- **Observed problem**:
  - `<button aria-label="关闭学习会话" className="p-2 ...">` 尺寸实测仅 36×36px，右上角内边距紧凑。
- **Why it is a problem**: 触控靶点低于 44×44px 行业人体工效学标准。大拇指按压时极易点空。
- **User impact**: 关闭失败，需要连续多次点击。
- **Evidence**: `audit_data['touch_target_issues']` 记录 `关闭学习会话 width: 36, height: 36`。
- **Recommended solution**:
  - 增加 `min-w-[44px] min-h-[44px] flex items-center justify-center`。
- **Implementation cost**: Very Low.

---

### 8. UX-ISSUE-08: 资源步骤“返回概念微卡”按钮高度仅 32px
- **ID**: `UX-ISSUE-08`
- **Severity**: **P2**
- **Page**: `LearningSessionModal.tsx` (RESOURCE Step)
- **User scenario**: 学生在资源列表页想返回概念卡再温习一下。
- **Observed problem**:
  - 顶部返回按钮高度仅 32px，内边距过窄。
- **Why it is a problem**: 触控目标小，容易点不准。
- **User impact**: 移动端返回操作不灵敏。
- **Evidence**: `audit_data['touch_target_issues']` 记录 `返回概念微卡 width: 63.1, height: 32`。
- **Recommended solution**:
  - 增加 `min-h-[44px] inline-flex items-center` 与适度 padding。
- **Implementation cost**: Very Low.

---

### 9. UX-ISSUE-09: 顶部栏角色与学生切换控件垂直高度偏小
- **ID**: `UX-ISSUE-09`
- **Severity**: **P2**
- **Page**: `Header.tsx`
- **User scenario**: 在移动端顶部切换演示学生或查看身份。
- **Observed problem**:
  - 角色切换按钮仅 34×26px，学生下拉框高度约 30px。
- **Why it is a problem**: 移动端 Header 空间有限，但过小的按钮容易误触。
- **User impact**: 误切换或无法一次性点中下拉菜单。
- **Evidence**: `audit_data['touch_target_issues']` 记录高度 26~28px。
- **Recommended solution**:
  - 增加容器最小触控高度 `min-h-[40px]`，优化移动端间距。
- **Implementation cost**: Low.

---

### 10. UX-ISSUE-10: 最近进展“查看完整学情档案”链接触控区域过小
- **ID**: `UX-ISSUE-10`
- **Severity**: **P3**
- **Page**: `RecentProgressCard.tsx`
- **User scenario**: 学生在首页看最近进展，想点击进入学情档案页。
- **Observed problem**:
  - 纯文字按钮无垂直内边距，触控高度仅 16px。
- **Why it is a problem**: 易误触为滚动，点击不易生效。
- **User impact**: 入口不易用。
- **Evidence**: `audit_data['touch_target_issues']` 记录高度 16px。
- **Recommended solution**:
  - 添加 `min-h-[44px] inline-flex items-center px-2 -mx-2` 扩大有效可点区域。
- **Implementation cost**: Very Low.

---

## 四、实施整改路线图 (Prioritized Action Plan)

按照真实用户影响度优先排序：
1. **Batch 1 (P1 认知与决策阻碍解决)**:
   - 修复 `StudentHome` 双卡片 CTA 恶性竞争，强化 `TodayActionCard` 的 Primary Hero 定位，将 `CurrentFocusCard` 调整为支持性规划全景（Secondary Outline）。
   - 修复 `LearningSessionModal` 结算成果页，当测验 `<60%` 时动态提升“再练一次”为主操作，纠正教学导向。
   - 在 `LearningSessionModal` Header 增加“轻量步骤指示器”（极简 3 节点感知），消除无预期黑盒感。
   - 在 `BottomNav` 补充“学习资源”Tab，实现 5-Tab 统一定位。
2. **Batch 2 (P2 移动端可用性与细节修复)**:
   - QUIZ 提交答案后平滑微滚至“下一题”CTA，防移动端遮挡。
   - 脱敏 AI 推荐理由中的 `K\d+` 技术代号，转为自然考点名。
   - 修复 `LearningSessionModal` 关闭按钮、返回按钮及 Header 控件的 44px 触控靶点尺寸。
3. **Batch 3 (P3 视觉与微观打磨)**:
   - 扩大 `RecentProgressCard` 档案跳转链接的触控区域。
