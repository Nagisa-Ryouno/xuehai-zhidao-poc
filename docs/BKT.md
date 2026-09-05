# 学海智导 (Xuehai Zhidao) V2 · 经典贝叶斯知识追踪 (BKT) 引擎设计契约

---

## 1. 为什么需要 BKT (Background & Motivation)

在传统的在线题库或教育管理系统中，通常直接采用“做题正确率（Correct Rate = 答对数 / 总题数）”来衡量学生的知识掌握情况。然而，在真实学习场景中：
1. **学生具备认知发展性**：初学者连续答错两道题后通过学习理解了概念，后续连续做对三道题，此时表面正确率只有 60%，但实际掌握程度已大幅提升。
2. **答题存在偶发扰动**：
   - **猜测（Guess）**：学生未真正掌握考点，但通过四选一猜对了选项。
   - **失误（Slip）**：学生已深刻理解该知识点，但在计算或审题时出现疏忽。

单纯使用静态正确率不仅无法捕捉学生的动态认知演进，还会对智能决策（如薄弱点识别、学习路径动态分支切换）产生严重误导。因此，学海智导引入了教育数据挖掘与智能辅导系统（ITS）领域的经典模型 —— **贝叶斯知识追踪（Bayesian Knowledge Tracing, BKT）**。

---

## 2. BKT 解决什么问题 (Problem Statement)

BKT 将学生的认知状态建模为一个两状态的隐马尔可夫模型（Hidden Markov Model, HMM）：
- **隐藏状态（Latent State）**：学生在当前考点上究竟处于“未掌握（Unlearned / $L_0$）”还是“已掌握（Learned / $L_1$）”。
- **观测序列（Observed Sequence）**：学生在上报的一系列作答行为中表现为“答对（Correct）”或“答错（Incorrect）”。

BKT 解决的核心问题：
> **“根据学生在某一知识点上的历史连续作答表现，计算学生当前确实已经掌握该知识点的后验概率 $P(L_t) \in [0, 1]$。”**

---

## 3. BKT 四大核心参数 (Core Parameters)

每一个 `(student_id, knowledge_id)` 认知节点均由标准 BKT 四参数刻画：

| 参数符号 | 代码字段 | 中文含义 | 取值范围 | POC 默认值 | 作用与解释 |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **$P(L_0)$** | `p_l0` | 初始掌握先验概率 | $(0, 1)$ | `0.20` | 学生未进行任何作答时，默认已掌握该知识点的先验概率 |
| **$P(T)$** | `p_t` | 学习转移概率 | $(0, 1)$ | `0.10` | 发生一次答题或学习活动后，知识状态由“未掌握”跃迁至“已掌握”的概率 |
| **$P(G)$** | `p_g` | 猜测概率 (Guess) | $(0, 1)$ | `0.20` | 在“未掌握”真实状态下，学生碰巧答对题目的概率 |
| **$P(S)$** | `p_s` | 失误概率 (Slip) | $(0, 1)$ | `0.10` | 在“已掌握”真实状态下，学生偶然失误做错题目的概率 |

> [!NOTE]
> **可识别性约束（Identifiability Condition）**：模型必须满足 $P(G) + P(S) < 1.0$。若两概率之和大于或等于 1.0，意味着猜测和失误的噪音超过了有效信息信号，将导致模型无法从答题中提取有效学习证据。

---

## 4. 概率更新数学公式 (Mathematical Formulation)

设第 $t$ 次作答前掌握概率为 $P(L)$：

### 4.1 当学生答对 ($is\_correct = True$)
第一步：利用贝叶斯法则计算观测后验概率：
$$P(L \mid \text{correct}) = \frac{P(L) \cdot (1 - P(S))}{P(L) \cdot (1 - P(S)) + (1 - P(L)) \cdot P(G)}$$

第二步：加入学习跃迁（即使此前未掌握，经过本次做题也有 $P(T)$ 的概率完成学习）：
$$P(L_{\text{new}}) = P(L \mid \text{correct}) + (1 - P(L \mid \text{correct})) \cdot P(T)$$

### 4.2 当学生答错 ($is\_correct = False$)
第一步：利用贝叶斯法则计算观测后验概率：
$$P(L \mid \text{incorrect}) = \frac{P(L) \cdot P(S)}{P(L) \cdot P(S) + (1 - P(L)) \cdot (1 - P(G))}$$

第二步：加入学习跃迁保底：
$$P(L_{\text{new}}) = P(L \mid \text{incorrect}) + (1 - P(L \mid \text{incorrect})) \cdot P(T)$$

---

## 5. Event → BKT 状态演进完整流程

```
[前端/移动端测验]
       ↓ (POST /api/quiz/submit)
[服务端权威判题]
       ↓
[P0-3 学习事件记录器] (event_service.record_event)
       ↓ 追加至 data/learning_events.jsonl
LearningEvent {
  event_id: "evt-quiz-xxx",
  student_id: "S001",
  knowledge_id: "K08",
  event_type: "QUESTION_ATTEMPT",
  payload: { is_correct: true, ... },
  server_timestamp: "2026-09-05T20:30:00+08:00"
}
       ↓
[BKT Event Processor] (bkt_event_processor.process_event)
       ├─ 幂等检查 (is_event_processed)
       ├─ 事件类型过滤 (仅 QUESTION_ATTEMPT 推进，其余忽略)
       ├─ 加载当前状态 (bkt_state_service.get_state)
       ├─ 调用纯数学引擎 (bkt_service.apply_attempt)
       └─ 原子持久化至 data/bkt_states.json 并记录已消费索引
       ↓
[BKT 知识认知状态]
BKTState {
  student_id: "S001",
  knowledge_id: "K08",
  mastery_probability: 0.576471,
  attempts: 1,
  correct_attempts: 1,
  ...
}
```

---

## 6. 正确率 vs 掌握度深度剖析

| 比较维度 | 传统正确率 (Accuracy) | BKT 掌握概率 (Mastery Probability) |
| :--- | :--- | :--- |
| **计算方式** | 累计对题 / 累计总题数（无时序加权） | 基于隐马尔可夫模型的递归贝叶斯后验估计 |
| **对时序的敏感度** | **无敏感度**（先对后错 vs 先错后对结果相同） | **强敏感**（先错后对反映认知突破，先对后错反映认知滑坡） |
| **对噪音的鲁棒性** | 弱（单次失误直接拉低指标） | 强（失误率 $P(S)$ 与猜测率 $P(G)$ 提供概率缓冲） |
| **业务决策价值** | 仅适合作为粗粒度历史统计 | 直接作为后续自适应学习路径动态重规划（P0-8）的触发信号 |

---

## 7. 当前默认参数及其性质 (Default Parameters)

> [!WARNING]
> **重要声明**：
> 当前 BKT 参数（$P(L_0)=0.20, P(T)=0.10, P(G)=0.20, P(S)=0.10$）为 **POC 原型系统默认参数**，尚未经过大规模真实学生历史作答数据的最大似然估计（EM/Expectation-Maximization）校准。参数目前作为确定性基准运行。

### 性质自验证算例（以 S001 练习 K08 为例）：
1. 初始状态：$P(L) = 0.2000$
2. 第 1 题答错：$P(L) \to \frac{4.2}{33} \approx 0.1273$（掌握度下降）
3. 第 2 题答对：$P(L) \to \approx 0.4566$（克服困难后显著回升）
4. 第 3 题答对：$P(L) \to \approx 0.8118$（连续做对巩固信心，跃迁至掌握区间）

---

## 8. 幂等消费设计 (Idempotency Design)

由于网络重试、客户端离线同步或重放，同一 `event_id` 可能被多次递交至状态更新接口。
- **全局索引存储**：在 `data/bkt_processed_events.json` 中记录已消费的 `event_id` 字典与处理元数据。
- **状态写前拦截**：
  ```python
  if bkt_state_service.is_event_processed(event_id):
      return BKTProcessResult(status="already_processed", changed=False)
  ```
- **测试证明**：同一事件无论调用多少次，BKT `mastery_probability` 严格保持首次计算值，`attempts` 计数器绝不自增。

---

## 9. 历史事件重建机制 (Historical Replay & Rebuild)

为了保障数据一致性、可审计性与故障自愈，系统提供了全量状态确定性重建接口：
`rebuild_student_knowledge_state(student_id, knowledge_id, events)`

1. **事件过滤**：抽取特定学生与考点的 `QUESTION_ATTEMPT` 事件。
2. **事件去重**：自动剔除历史日志中的重复 `event_id`。
3. **权威时间排序**：严格按 `server_timestamp`（时间相同时按 `event_id` 字典序）排序，杜绝客户端伪造时间戳产生的回放乱序。
4. **顺序重放**：从 $P(L_0)$ 初始状态开始逐一演算，输出与实时流式计算 100% 吻合的确定性认知状态。

---

## 10. 当前限制与未来演进 (Current Limitations & Future Work)

1. **单题多技能关联暂未支持**：当前模型假设 1 道题目严格绑定 1 个主要考点（Single-Skill BKT）。
2. **答题耗时（time_spent_ms）未深度加权**：目前题目作答耗时已完整落盘，但尚未直接介入 BKT 公式（未来可将过长或过短耗时转化为失误或猜测的概率权重）。
3. **提示（HINT）未折减掌握度**：目前 `HINT_REQUEST` 仅作为行为日志记录并返回 `ignored`，未折减掌握概率，后续将在 P0-7 中建立多模态学习证据融合。
