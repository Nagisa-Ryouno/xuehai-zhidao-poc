# 学海智导 (Xuehai Zhidao) V2 产品演进路线图 (Phase 2.2 Roadmap)

> **版本**：Phase 2.2 Product Roadmap  
> **基线状态**：Phase 2.1 Architecture FROZEN  
> **核心导向**：以核心自适应学习闭环为唯一驱动，拒绝过度设计与架构反复，专注于产品体验与业务流转。

---

## 一、路线图全景概览 (Roadmap Overview)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 2.2-A: Product Baseline & Repository Governance        [CURRENT / 完成]│
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2.2-B: Core Student Experience Consolidation           [NEXT / 待启动] │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2.2-C: Closed-Loop Adaptive Learning & Path Replanning [PLANNED]      │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2.2-D: AI Learning Copilot & Explainable Tutoring       [PLANNED]      │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2.2-E: End-to-End Golden Journey & Product Acceptance  [MILESTONE]    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、阶段详细规划 (Detailed Phase Breakdown)

### Phase 2.2-A: Product Baseline & Repository Governance 【当前阶段】
- **目标 (Goal)**：建立清晰的产品定位基线、功能盘点与演进路线图，规范根目录工程文档。
- **用户价值 (User Value)**：让项目参与者与评审人员在 3~5 分钟内准确理解项目核心价值、真实能力现状及边界，消除信息不对称。
- **交付物 (Deliverables)**：
  - 根目录标准 `README.md`
  - `docs/product/PRODUCT-VISION.md`
  - `docs/product/FEATURE-BASELINE.md`
  - `docs/product/ROADMAP.md`
- **验收标准 (Acceptance Criteria)**：
  - 架构冻结不变，测试（143 后端 / 37 前端 / 17 架构适应度）100% 通过；
  - 真实反映技术栈（React 19 + TypeScript + Vite + Tailwind CSS v4 / FastAPI）；
  - 明确标注各项功能在后端、前端及端到端层面的成熟度。

---

### Phase 2.2-B: Core Student Experience Consolidation 【下一阶段】
- **目标 (Goal)**：巩固学生端移动端优先 (Mobile-First) 核心体验，打通任务流、图谱与学情卡片的数据一致性。
- **用户价值 (User Value)**：学生进入平台后拥有清晰明了的“今日任务”、“图谱探查”与“学情看板”，交互流畅无阻断。
- **交付物 (Deliverables)**：
  - 学生端 4-Tab（今日任务、知识图谱、学情档案、AI伴学）体验打磨；
  - 路径节点状态（LOCKED, AVAILABLE, IN_PROGRESS, COMPLETED）在任务列表中的直观视觉表达；
  - 弱网与异常场景下的友好错误反馈与重试交互。
- **验收标准 (Acceptance Criteria)**：
  - 学生端在桌面端与移动端触控场景（>=44px 靶点）适配良好；
  - 切换学生（S001~S005）时图谱节点状态与推荐路径 100% 保持同步响应。

---

### Phase 2.2-C: Closed-Loop Adaptive Learning & Path Replanning
- **目标 (Goal)**：全面闭合“测验作答 $\to$ BKT 演进 $\to$ 1-hop 局部动态重规划 $\to$ 前端节点即时解锁”端到端链路。
- **用户价值 (User Value)**：学生真实感受到“我的努力有即时回报”——达标后前置通过，下游后继由灰暗锁定变为彩色可学，形成强烈自驱反馈。
- **交付物 (Deliverables)**：
  - 前端测验提交后对 `QuizSubmitResponse.replanning` 载荷的响应式消费与动效展示；
  - 节点解锁庆祝提示（如：“恭喜掌握 K08！已为您解锁后继知识点 K09”）；
  - 前端与 `GET /api/students/{id}/path-states` 实时同步机制。
- **验收标准 (Acceptance Criteria)**：
  - Golden 3 步序列（错 $\to$ 对 $\to$ 对）在浏览器界面上能肉眼可见地完成从薄弱保持到跨越达标，再到下游节点状态从 LOCKED 变为 AVAILABLE 的完整流转。

---

### Phase 2.2-D: AI Learning Copilot & Explainable Tutoring
- **目标 (Goal)**：基于冻结的确定性重规划信封，发挥 AI 伴学副驾的“可解释性教学说理”能力。
- **用户价值 (User Value)**：解答学生“为什么系统推荐我学这个”、“我刚才错在哪里”的核心疑惑，提供启发式引导。
- **交付物 (Deliverables)**：
  - AI 导学副驾针对局部重规划结果的结构化解读模块；
  - 基于前置考点依赖的错题启发提示（Socratic Hints）；
  - 多模型调用失败时的稳健纯本地规则化兜底解释。
- **验收标准 (Acceptance Criteria)**：
  - AI 生成的内容严格围绕微观经济学考点拓扑展开，严禁胡编乱造越权规则；
  - 在无外网 API Key 时，本地规则模板兜底率 100%，无白屏异常。

---

### Phase 2.2-E: End-to-End Golden Journey & Product Acceptance
- **目标 (Goal)**：全链路 Golden User Journey 演练、多场景自动化端到端测试与最终产品化验收交付。
- **用户价值 (User Value)**：交付一套稳定可靠、逻辑严密、教学闭环完整、具备高展示度的高校教学自适应示范系统。
- **交付物 (Deliverables)**：
  - 完整的黄金用户旅程演示脚本与操作手册；
  - 自动化端到端集成验证报告；
  - Phase 2.2 最终产品验收交付报告。
- **验收标准 (Acceptance Criteria)**：
  - 真实演示环境 0 崩溃、0 报错；
  - 143+ 后端与 37+ 前端全套测试保持绿色；
  - 达到可面向高校师生公开展示并开展教学试验的基线质量。
