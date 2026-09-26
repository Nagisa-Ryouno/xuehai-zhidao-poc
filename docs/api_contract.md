# 学海智导（Xuehai Zhidao）V2 API 契约规范 (Single Source of Truth)

本文档定义学海智导 V2 系统前后端通信的全部数据契约与接口规范。

> [!NOTE] 架构层级与统一网关说明 (Architecture Scope)
> 本文档定义的是系统核心领域层基础契约（对应 `app/api` 模块）。
> 在当前生产部署与端到端运行中，系统采用 `gateway/api.py` 统一安全服务网关（端口 **8011**），为前端 Student PWA 与 Teacher Web 提供聚合路由（如 `/api/students/{id}/dashboard`、`/api/learning/today/{id}`、`/api/teacher/overview` 等）。
> 生产环境接口完整调用清单请以 `gateway/api.py` 及根目录 [HANDOFF.md](file:///c:/Users/XSL/Desktop/国创/xuehai-zhidao-poc/HANDOFF.md) 为准。

---

## 一、通用约定
- **Base URL**: `/api`
- **数据格式**: JSON (`Content-Type: application/json; charset=utf-8`)
- **时间格式**: ISO 8601 字符串 (如 `2026-09-05T19:30:00+08:00`)
- **错误响应统一结构**:
  ```json
  {
    "detail": "错误详细描述"
  }
  ```

---

## 二、指标定义与解耦契约
1. **empirical_accuracy (经验正确率)**:
   - 字段类型: `float` (0.0 ~ 100.0)
   - 释义: 历史做题统计量，即 $\frac{\text{正确作答数}}{\text{总作答数}} \times 100\%$。
   - 用途: 学生学情档案展示、历史答题报表、教师风险预警雷达观察指标。
2. **bkt_mastery (BKT 掌握度)**:
   - 字段类型: `float` (0.0 ~ 1.0)
   - 释义: 贝叶斯知识追踪模型推断的潜在掌握概率 $P(L)$。
   - 用途: 唯一决定三态知识状态 (`WEAK` / `DEVELOPING` / `MASTERED`)、驱动 DAG 依赖解锁和个性化学习路径动态重规划。

---

## 三、学习行为事件接口 (Learning Events)

### 1. 行为事件上报
- **URL**: `POST /api/events`
- **说明**: 记录答题、求助、概念查阅等学习行为事件，支持异步落盘追加至 `data/learning_events.jsonl`。
- **Request Body**:
  ```json
  {
    "event_id": "evt-20260905-001",
    "student_id": "S001",
    "knowledge_id": "K08",
    "event_type": "QUESTION_ATTEMPT",
    "payload": {
      "question_id": "Q-K08-01",
      "is_correct": true,
      "time_spent_ms": 4200,
      "selected_option": "A"
    },
    "client_timestamp": "2026-09-05T19:30:00+08:00"
  }
  ```
- **Response 200**:
  ```json
  {
    "status": "success",
    "event_id": "evt-20260905-001",
    "server_timestamp": "2026-09-05T19:30:00.123+08:00"
  }
  ```

---

## 四、微测验接口 (Knowledge Quiz)

### 1. 获取知识点测验题
- **URL**: `GET /api/quiz/{knowledge_id}`
- **说明**: 获取指定知识点的微测验题，不泄露正确答案字段。
- **Response 200**:
  ```json
  {
    "knowledge_id": "K08",
    "knowledge_name": "需求价格弹性",
    "questions": [
      {
        "question_id": "Q-K08-01",
        "stem": "当某商品的需求价格弹性绝对值大于1时，降价会导致总收益如何变化？",
        "options": [
          {"key": "A", "text": "总收益增加"},
          {"key": "B", "text": "总收益减少"},
          {"key": "C", "text": "总收益不变"},
          {"key": "D", "text": "无法确定"}
        ],
        "difficulty": 2
      }
    ]
  }
  ```

### 2. 提交测验并触发 BKT 联动更新
- **URL**: `POST /api/quiz/submit`
- **说明**: 提交答案，服务端判题，自动触发 Learning Event 记录与 BKT 计算，原子返回判题与最新掌握度状态。
- **Request Body**:
  ```json
  {
    "student_id": "S001",
    "knowledge_id": "K08",
    "question_id": "Q-K08-01",
    "selected_option": "A",
    "time_spent_ms": 4500
  }
  ```
- **Response 200**:
  ```json
  {
    "is_correct": true,
    "correct_option": "A",
    "explanation": "需求富有弹性时，价格下降引起的销量增加比例大于价格下降比例，因此总收益增加。",
    "bkt_update": {
      "previous_mastery": 0.42,
      "current_mastery": 0.7643,
      "previous_state": "WEAK",
      "current_state": "DEVELOPING",
      "is_state_changed": true
    },
    "path_replan_required": false
  }
  ```

---

## 五、BKT 与路径动态重规划接口

### 1. BKT 状态查询
- **URL**: `GET /api/bkt/state/{student_id}`
- **Response 200**:
  ```json
  {
    "student_id": "S001",
    "bkt_states": {
      "K08": {
        "mastery": 0.7643,
        "state": "DEVELOPING",
        "last_updated": "2026-09-05T19:30:00+08:00",
        "practice_count": 1
      }
    }
  }
  ```

### 2. 动态学习路径重规划
- **URL**: `GET /api/learning-path/replan/{student_id}`
- **说明**: 基于当前 BKT 潜变量与 DAG 前置依赖拓扑重新计算待学队列与解锁状态。
- **Response 200**:
  ```json
  {
    "student_id": "S001",
    "pending_nodes": [
      {
        "knowledge_id": "K08",
        "knowledge_name": "需求价格弹性",
        "bkt_mastery": 0.7643,
        "mastery_state": "DEVELOPING",
        "status": "IN_PROGRESS",
        "is_unlocked": true
      }
    ],
    "unlocked_next_nodes": [
      {
        "knowledge_id": "K09",
        "knowledge_name": "需求收入弹性与交叉弹性",
        "is_unlocked": false,
        "missing_prerequisites": ["K08"]
      }
    ]
  }
  ```

---

## 六、教师端决策看板接口 (Teacher Cockpit)

### 1. 班级全景学情概览
- **URL**: `GET /api/teacher/class-overview`
- **Response 200**:
  ```json
  {
    "total_students": 5,
    "class_average_mastery": 0.724,
    "top_weak_knowledge_points": [
      {
        "knowledge_id": "K08",
        "knowledge_name": "需求价格弹性",
        "fail_rate": 0.60,
        "affected_student_count": 3
      }
    ],
    "risk_summary": {
      "critical_count": 1,
      "warning_count": 2,
      "normal_count": 2
    }
  }
  ```

### 2. 学生多维风险预警雷达
- **URL**: `GET /api/teacher/student-risks`
- **Response 200**:
  ```json
  {
    "students": [
      {
        "student_id": "S003",
        "student_name": "王同学",
        "risk_level": "CRITICAL",
        "risk_factors": [
          "薄弱知识点超过 8 个 (当前 12 个)",
          "导论核心前置节点 K01 掌握度不足"
        ],
        "average_accuracy": 54.2,
        "bkt_average_mastery": 0.485,
        "weak_count": 12
      }
    ]
  }
  ```

### 3. 一键干预建议生成
- **URL**: `POST /api/teacher/intervene/suggest`
- **Request Body**:
  ```json
  {
    "student_id": "S003"
  }
  ```
- **Response 200**:
  ```json
  {
    "student_id": "S003",
    "diagnosis": "该生基础概念断层严重，K01（稀缺性）尚未达标直接阻滞后续微观全链条。",
    "suggested_actions": [
      "安排一对一面谈，梳理机会成本与生产可能性边界",
      "降维练习：推送导论第一章概念诊断测验"
    ],
    "ai_generated_brief": "王同学在微观经济学前置概念存在结构性阻滞..."
  }
  ```
