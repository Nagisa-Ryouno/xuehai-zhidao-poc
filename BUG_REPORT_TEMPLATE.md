# 学海智导 (Xuehai Zhidao) — 缺陷工单模板 (BUG_REPORT_TEMPLATE.md)

> 接手同学在人工测试或回归验证中发现任何异常时，请按本标准模板提交 Issue / Bug 记录。

---

## 缺陷严重度分级标准 (Severity Definition)

- **P0（阻断 / 核心数据损坏）**：
  - 系统无法启动或白屏崩溃。
  - 学习核心闭环断裂（如判题卡死、BKT 无法更新、路径无法解锁）。
  - 数据文件损坏或不可逆的数据污染（如伪造 BKT 状态、篡改生产事件）。
- **P1（重要功能异常）**：
  - 核心功能逻辑错误（如答错题却判定掌握、后继错误解锁）。
  - AI 伴学并发请求锁失效、多学生会话串台。
  - 教师端关键下钻或干预动作提交失败。
- **P2（常规交互 / 视觉适配问题）**：
  - 模态框滚动穿透、背景跳动、Esc 快捷键失效。
  - 移动端小屏断点下的排版折行或样式轻度遮挡。
  - 非核心按钮点击反馈延迟或缺少 Loading 态。
- **P3（微小优化 / 文案用词）**：
  - 提示词出现轻微口语化或底层技术用语遗留。
  - 颜色明度对比度轻微偏差、间距不均匀。

---

## 缺陷记录模板 (Bug Template)

```markdown
### 基本信息
- **Bug ID**: BUG-202609-XXXX
- **Severity**: P0 / P1 / P2 / P3
- **Status**: NEW / CONFIRMED / IN_PROGRESS / FIXED / VERIFIED / CLOSED
- **Page / Route**: /student | /teacher | /student/resources | ...
- **Environment**: 
  - OS: Windows 11 / macOS Sequoia / Linux
  - Browser: Chrome 128 / Safari 18 / Edge 128
  - Viewport: Mobile (390x844) / Desktop (1440x900)
  - Backend Version: Commit Hash (e.g., cfc3d6e)
  - Node / Python: Node 20.x, Python 3.13.x

---

### 复现步骤 (Steps to Reproduce)
1. 访问页面 `http://localhost:5173/...`
2. 点击按钮 `[...]`
3. 执行操作 `[...]`
4. 观察页面表现

---

### 现象对比 (Expected vs Actual)
- **Expected（期望行为）**: 
  [清晰描述符合业务规范的预期结果]
- **Actual（实际行为）**: 
  [清晰描述当前观察到的错误表现]

---

### 诊断日志与现场 (Diagnostics & Evidence)
- **Console Error（浏览器控制台报错）**:
  ```text
  [若有报错信息，完整粘贴此处；若无写 None]
  ```
- **Network Error（网络请求状态码及 Response Payload）**:
  - Request URL: POST /api/...
  - Status Code: 500 / 422 / 400
  - Response Body:
  ```json
  [粘贴响应体 JSON]
  ```
- **Screenshot / Screen Recording（截图或录屏路径）**:
  - `docs/bug_evidence/BUG-XXXX-screenshot.png`

---

### 代码与回归分析 (Code Analysis)
- **Related API**: `gateway/api.py` -> `endpoint_name`
- **Related Component**: `frontend/src/components/.../ComponentName.tsx`
- **Regression Risk（回归风险评估）**:
  [修改此缺陷是否会影响 BKT 算法、PathState 状态机、学习会话等核心链路？]

---

### 修复与验证方案 (Fix & Verification)
- **Root Cause（根本原因）**:
  [分析导致该缺陷的代码或逻辑漏洞]
- **Proposed Fix（修复方案）**:
  [简要描述拟修改的文件与核心改动]
- **Retest Result（回归复测结果）**:
  - Automated Tests: pytest / npm test 结果
  - Manual Verification: 人工确认现象消除
- **Fixed In Commit**: [Commit Hash]
```
