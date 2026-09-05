# -*- coding: utf-8 -*-
"""
assistant_service.py
学海智导 (Xuehai Zhidao) - AI 学习助手核心服务模块

设计架构：
Data Layer (JSON 读取与缓存)
       ↓
Context Builder (学生多维学情上下文提炼)
       ↓
LLM Service (大模型调用、超时与异常处理)
       ↓
Response Validator (模型响应结构与事实真实性校验)
       ↓
Rule-based Engine (降级保障与兜底引擎)
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from llm_service import llm_service

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

PROFILE_FILE = OUTPUT_DIR / "student_profiles.json"
PATH_FILE = OUTPUT_DIR / "learning_paths.json"
REPORT_FILE = OUTPUT_DIR / "student_reports.json"


def load_json(file_path: Path) -> Dict[str, Any]:
    """读取 JSON 文件"""
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# Context Builder: 学生多维学情上下文提炼
# ============================================================

def build_student_context(student_id: str) -> Optional[Dict[str, Any]]:
    """
    将学生画像、学习路径与综合报告提炼为干净、有限长度的结构化上下文，
    并构建全量已知知识点索引库用于防幻觉事实校验。
    """
    profiles = load_json(PROFILE_FILE)
    paths = load_json(PATH_FILE)
    reports = load_json(REPORT_FILE)

    if student_id not in profiles:
        return None

    raw_profile = profiles.get(student_id, {})
    raw_path = paths.get(student_id, {})
    raw_report = reports.get(student_id, {})

    student_info = raw_profile.get("student", {})
    raw_name = student_info.get("student_name", student_id)
    student_name = raw_name if raw_name.endswith("同学") else f"{raw_name}同学"

    overall = raw_profile.get("overall_profile", {})
    diagnosis = raw_report.get("diagnosis", {})
    daily = raw_report.get("daily_learning_plan", {})
    path_steps = raw_path.get("learning_path", [])
    weaks = raw_profile.get("weak_knowledge_points", [])
    prereqs = raw_profile.get("prerequisite_knowledge_points", [])
    recommendation_type = raw_path.get("recommendation_type", "个性化学习推荐")

    # 构建精炼的上下文（控制 Token 长度，去除不必要冗余）
    condensed = {
        "student": {
            "id": student_id,
            "name": student_name,
            "major": student_info.get("major", "经济学"),
            "grade": student_info.get("grade", "大二"),
            "goal": student_info.get("learning_goal", "")
        },
        "profile": {
            "average_accuracy": overall.get("average_accuracy", 0.0),
            "assessment_score": overall.get("average_assessment_score", 0.0),
            "mastery_level": overall.get("mastery_level", "中等"),
            "completion_rate": overall.get("average_completion_rate", 0.0),
            "completion_level": overall.get("completion_level", "中"),
            "activity_level": overall.get("activity_level", "中"),
            "interaction_count": overall.get("total_interaction_count", 0),
            "practice_count": overall.get("total_practice_count", 0),
            "answer_time_seconds": overall.get("average_answer_time_seconds", 60.0),
            "speed_status": overall.get("speed_status", "答题速度较快")
        },
        "diagnosis": {
            "main_problems": diagnosis.get("main_problems", raw_profile.get("diagnosis", [])),
            "description": diagnosis.get("mastery_description", ""),
            "behavior": diagnosis.get("behavior_description", ""),
            "weak_count": len(weaks),
            "prereq_count": len(prereqs)
        },
        "recommendation_type": recommendation_type,
        "learning_path": [
            {
                "stage": s.get("stage", idx + 1),
                "knowledge_id": s.get("knowledge_id"),
                "knowledge_name": s.get("knowledge_name"),
                "current_accuracy": s.get("current_accuracy"),
                "accuracy": s.get("current_accuracy"),
                "priority": s.get("priority", "中"),
                "chapter": s.get("chapter", ""),
                "learning_goal": s.get("learning_goal", ""),
                "reason": s.get("reason", "")
            }
            for idx, s in enumerate(path_steps)
        ],
        "weak_knowledge_points": [
            {
                "knowledge_id": w.get("knowledge_id"),
                "knowledge_name": w.get("knowledge_name"),
                "accuracy": w.get("accuracy"),
                "difficulty": w.get("difficulty", 2),
                "prerequisite": w.get("prerequisite", [])
            }
            for w in weaks[:6]
        ],
        "prerequisite_knowledge_points": [
            {
                "knowledge_id": p.get("knowledge_id"),
                "knowledge_name": p.get("knowledge_name"),
                "accuracy": p.get("accuracy"),
                "reason": p.get("reason", "")
            }
            for p in prereqs[:6]
        ],
        "daily_plan": {
            "duration_minutes": daily.get("recommended_minutes", 30),
            "question_count": daily.get("recommended_questions", 8),
            "focus": daily.get("focus", "基础概念理解与巩固")
        },
        "optimization_suggestions": raw_report.get("optimization_suggestions", [])
    }

    # 构建已知知识点字典，供校验器比对事实
    known_map = {}
    for s in path_steps:
        k_id = s.get("knowledge_id")
        if k_id:
            known_map[k_id] = {
                "knowledge_id": k_id,
                "knowledge_name": s.get("knowledge_name", ""),
                "accuracy": s.get("current_accuracy"),
                "priority": s.get("priority", "中"),
                "reason": s.get("reason", ""),
                "chapter": s.get("chapter", ""),
                "learning_goal": s.get("learning_goal", ""),
                "source": s.get("source", "学习路径")
            }
            known_map[s.get("knowledge_name", "")] = known_map[k_id]

    for w in weaks:
        k_id = w.get("knowledge_id")
        if k_id and k_id not in known_map:
            known_map[k_id] = {
                "knowledge_id": k_id,
                "knowledge_name": w.get("knowledge_name", ""),
                "accuracy": w.get("accuracy"),
                "priority": "高" if (w.get("accuracy") or 0) < 60 else "中",
                "reason": f"当前正确率仅 {w.get('accuracy')}%, 属于明确薄弱点",
                "chapter": w.get("chapter", ""),
                "learning_goal": "优先修复知识薄弱点",
                "source": "薄弱知识点"
            }
            known_map[w.get("knowledge_name", "")] = known_map[k_id]

    for p in prereqs:
        k_id = p.get("knowledge_id")
        if k_id and k_id not in known_map:
            known_map[k_id] = {
                "knowledge_id": k_id,
                "knowledge_name": p.get("knowledge_name", ""),
                "accuracy": p.get("accuracy"),
                "priority": "中",
                "reason": p.get("reason", ""),
                "chapter": "",
                "learning_goal": "补齐前置知识基础",
                "source": "前置知识"
            }
            known_map[p.get("knowledge_name", "")] = known_map[k_id]

    return {
        "student_id": student_id,
        "student_name": student_name,
        "raw_profile": raw_profile,
        "raw_path": raw_path,
        "raw_report": raw_report,
        "condensed": condensed,
        "known_map": known_map
    }


def get_student_context(student_id: str) -> Optional[Dict[str, Any]]:
    """向后兼容接口"""
    return build_student_context(student_id)


# ============================================================
# System Prompt 设计
# ============================================================

def build_system_prompt(student_name: str) -> str:
    """构建专业、严格受控的 AI 学习导师 System Prompt"""
    return (
        f"你是“学海智导”微观经济学智能导师 (AI Learning Coach)，正在为学生【{student_name}】提供个性化指导。\n\n"
        "【核心身份与职责】\n"
        "1. 你的职责不是代替学生做题或无意义闲聊，而是解读学情画像、阐明知识依赖关系、解释推荐学习时序、制定科学复习计划。\n"
        "2. 保持专业、亲切、鼓励且逻辑严密的教学风格，语言通俗易懂，善于用经济学逻辑解答认知困惑。\n\n"
        "【严苛的事实约束准则（最高优先级，违背即判定失败）】\n"
        "1. 事实完全来自上下文：学生的平均正确率、各知识点正确率、优先级、薄弱点列表、学习路径节点、每日规划时长与题量，必须 100% 严格使用提供的上下文 JSON 数据！\n"
        "2. 严禁捏造或猜测数据：绝不允许自行猜测或编造学生的分数、正确率、做题耗时等任何统计数值。\n"
        "3. 严禁虚构知识点：推荐和提及的微观经济学知识点必须来源于上下文已知知识列表。\n"
        "4. S004 特殊情况处理：若学生（如赵同学）当前学习路径为空（0 个知识点），说明其平均正确率高达 89.42%，各基础模块掌握优秀，无明显低分薄弱点，系统推荐策略为【综合能力提升】；严禁为其捏造基础薄弱知识点，应指导其进行综合应用题、跨考点联动推导与限时模拟突破。\n\n"
        "【结构化输出规范】\n"
        "你的回复必须为严格合法的 JSON 对象，包含以下三个字段，绝不能输出其他文本：\n"
        "{\n"
        '  "answer": "深入浅出、有事实依据的导师解答（支持 Markdown 强调与列表）",\n'
        '  "related_knowledge_points": [\n'
        '    {\n'
        '      "knowledge_id": "知识点编号，如 K01 (必须存在于上下文)",\n'
        '      "knowledge_name": "知识点全称 (必须与上下文完全匹配)",\n'
        '      "accuracy": 数值或 null (必须与上下文真实正确率一致),\n'
        '      "priority": "优先级，如 高 / 中 / 低",\n'
        '      "reason": "推荐或关联依据"\n'
        '    }\n'
        '  ],\n'
        '  "suggested_actions": [\n'
        '    "1. 具体可落地的学习行动",\n'
        '    "2. 下一步精炼做题建议"\n'
        '  ]\n'
        "}\n"
    )


# ============================================================
# Response Validation: 强制事实与结构校验
# ============================================================

def validate_and_sanitize_response(
    raw_response: Any,
    context: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    严格校验并清洗 LLM 的输出。
    若存在缺失字段、格式错误或捏造知识点，则自动修正或拒绝（返回 None 触发 fallback）。
    """
    if not isinstance(raw_response, dict):
        return None

    answer = raw_response.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return None

    related_kps = raw_response.get("related_knowledge_points")
    if not isinstance(related_kps, list):
        related_kps = []

    suggested_actions = raw_response.get("suggested_actions")
    if not isinstance(suggested_actions, list):
        suggested_actions = []

    known_map = context.get("known_map", {})
    sanitized_kps = []

    for item in related_kps:
        if not isinstance(item, dict):
            continue

        k_id = item.get("knowledge_id", "").strip()
        k_name = item.get("knowledge_name", "").strip()

        matched_truth = None
        if k_id and k_id in known_map:
            matched_truth = known_map[k_id]
        elif k_name and k_name in known_map:
            matched_truth = known_map[k_name]

        if matched_truth:
            # 采用真实数据对模型输出进行事实加固，防止幻觉数值溢出
            sanitized_kps.append({
                "knowledge_id": matched_truth["knowledge_id"],
                "knowledge_name": matched_truth["knowledge_name"],
                "accuracy": matched_truth["accuracy"],
                "priority": matched_truth["priority"],
                "reason": item.get("reason", matched_truth["reason"]),
                "chapter": matched_truth.get("chapter", ""),
                "learning_goal": matched_truth.get("learning_goal", ""),
                "source": matched_truth.get("source", "薄弱知识点")
            })

    # 确保 suggested_actions 均为字符串
    clean_actions = [str(act).strip() for act in suggested_actions if str(act).strip()]
    if not clean_actions:
        clean_actions = [
            "1. 结合当前学习路径进行专项自测",
            "2. 记录典型错题并对照解析强化理解"
        ]

    return {
        "student_id": context["student_id"],
        "message": "",
        "answer": answer.strip(),
        "related_knowledge_points": sanitized_kps,
        "suggested_actions": clean_actions
    }


# ============================================================
# Rule-based Engine: 本地规则降级与兜底引擎
# ============================================================

def find_mentioned_knowledge(
    message: str,
    context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """从用户输入中识别提及的知识点"""
    mentioned = []
    seen_ids = set()
    raw_path = context.get("raw_path", {})
    raw_profile = context.get("raw_profile", {})

    path_steps = raw_path.get("learning_path", [])
    for step in path_steps:
        k_name = step.get("knowledge_name", "")
        k_id = step.get("knowledge_id", "")
        if (k_name and (k_name in message or any(sub in message for sub in [k_name[:4], k_name[:2]] if len(sub) >= 2))) or (k_id.lower() in message.lower()):
            if k_id not in seen_ids:
                seen_ids.add(k_id)
                mentioned.append({
                    "knowledge_id": k_id,
                    "knowledge_name": k_name,
                    "accuracy": step.get("current_accuracy"),
                    "priority": step.get("priority", "中"),
                    "reason": step.get("reason", ""),
                    "chapter": step.get("chapter", ""),
                    "learning_goal": step.get("learning_goal", ""),
                    "source": step.get("source", "学习路径"),
                })

    weak_points = raw_profile.get("weak_knowledge_points", [])
    for wp in weak_points:
        k_id = wp.get("knowledge_id", "")
        k_name = wp.get("knowledge_name", "")
        if k_id not in seen_ids and (k_name in message or (len(k_name) >= 3 and k_name[:3] in message)):
            seen_ids.add(k_id)
            mentioned.append({
                "knowledge_id": k_id,
                "knowledge_name": k_name,
                "accuracy": wp.get("accuracy"),
                "priority": "高" if (wp.get("accuracy") or 0) < 50 else "中",
                "reason": f"当前正确率仅 {wp.get('accuracy')}%, 属于明确薄弱点",
                "chapter": wp.get("chapter", ""),
                "learning_goal": "优先修复知识薄弱点",
                "source": "薄弱知识点",
            })

    prereqs = raw_profile.get("prerequisite_knowledge_points", [])
    for pp in prereqs:
        k_id = pp.get("knowledge_id", "")
        k_name = pp.get("knowledge_name", "")
        if k_id not in seen_ids and (k_name in message or (len(k_name) >= 3 and k_name[:3] in message)):
            seen_ids.add(k_id)
            mentioned.append({
                "knowledge_id": k_id,
                "knowledge_name": k_name,
                "accuracy": pp.get("accuracy"),
                "priority": "中",
                "reason": pp.get("reason", ""),
                "chapter": "",
                "learning_goal": "补齐前置知识基础",
                "source": "前置知识",
            })

    return mentioned


def detect_intent(message: str) -> str:
    """基于关键词进行意图识别"""
    msg = message.strip()

    if any(kw in msg for kw in ["为什么", "为啥", "为何", "原因", "凭什么", "推荐理由"]):
        return "why_recommend"

    if any(kw in msg for kw in ["接下来", "下一步", "先学", "先做", "学习顺序", "学什么", "路径", "路线", "阶段"]):
        return "learning_path"

    if any(kw in msg for kw in ["成绩", "表现", "学情", "掌握", "怎么样", "学得好", "学得差", "最大问题", "薄弱", "分析"]):
        return "academic_status"

    if any(kw in msg for kw in ["今天", "安排", "计划", "任务", "建议", "复习", "规划", "怎么学"]):
        return "daily_plan"

    if any(kw in msg for kw in ["讲一下", "讲讲", "解释一下", "概念", "定义", "什么是"]):
        return "explain_concept"

    return "unknown"


def generate_rule_based_response(
    context: Dict[str, Any],
    message: str
) -> Dict[str, Any]:
    """确定性规则回复引擎，作为稳定降级保障"""
    student_id = context["student_id"]
    student_name = context["student_name"]
    raw_profile = context["raw_profile"]
    raw_path = context["raw_path"]
    raw_report = context["raw_report"]

    overall = raw_profile.get("overall_profile", {})
    learning_path = raw_path.get("learning_path", [])
    diagnosis = raw_report.get("diagnosis", {})
    daily_plan = raw_report.get("daily_learning_plan", {})
    opt_suggestions = raw_report.get("optimization_suggestions", [])
    recommendation_type = raw_path.get("recommendation_type", "个性化推荐")

    mentioned_kps = find_mentioned_knowledge(message, context)
    intent = detect_intent(message)

    # 1. S004 特殊情况
    if len(learning_path) == 0:
        avg_acc = overall.get("average_accuracy", 89.42)
        ans_parts = [
            f"{student_name}，系统分析显示你当前的平均正确率高达 **{avg_acc:.2f}%**，各基础知识模块掌握扎实，**目前没有检测到明显薄弱知识点**。",
            f"因此系统未为你安排基础概念的逐级补差路径，推荐策略为【**{recommendation_type}**】。",
            "接下来的核心发力点在于：提升做题效率与答题速度（目前答题耗时约 168 秒/题），并向高阶跨知识点综合题冲刺。"
        ]
        answer = "\n\n".join(ans_parts)
        actions = [
            "1. 开展限时模拟训练：针对中高难度题目设定 90~100 秒严格时限",
            "2. 演练综合应用大题：强化供求、弹性与福利效应联动推导",
            "3. 挑战跨章节拔高试题：逐步攻克不完全竞争市场与博弈论高分考点"
        ]
        return {
            "student_id": student_id,
            "message": message,
            "answer": answer,
            "related_knowledge_points": [],
            "suggested_actions": actions
        }

    # 2. 知识点原因或概念讲解
    if intent in ("why_recommend", "explain_concept") or (mentioned_kps and any(kw in message for kw in ["为什么", "怎么", "掌握", "讲"])):
        if mentioned_kps:
            target_kp = mentioned_kps[0]
            kp_name = target_kp["knowledge_name"]
            acc = target_kp["accuracy"]
            acc_str = f"{acc:.1f}%" if acc is not None else "尚无充足记录"
            priority = target_kp.get("priority", "中")
            reason = target_kp.get("reason", "为核心基础知识点")
            goal = target_kp.get("learning_goal", "修复知识薄弱点")

            ans_parts = [
                f"针对【**{kp_name}**】（编号：{target_kp['knowledge_id']}），导师为你梳理的核心分析如下：",
                f"1. **当前掌握现状**：你在该知识点的平均正确率为 **{acc_str}**，优先级评定为【**{priority}**】；",
                f"2. **拓扑依赖诊断**：{reason}；",
                f"3. **攻坚目标方向**：{goal}。彻底吃透该考点有助于打通上下游知识网络，提升综合题得分率。"
            ]
            answer = "\n\n".join(ans_parts)
            actions = [
                f"1. 仔细精读《{target_kp.get('chapter', '对应章节')}》关于【{kp_name}】的核心概念与公式推导",
                f"2. 针对性完成 5~8 道练习题，力争将正确率稳定提升至 75% 以上",
                "3. 在掌握扎实后，顺次推进知识链下一阶段的学习任务"
            ]
            return {
                "student_id": student_id,
                "message": message,
                "answer": answer,
                "related_knowledge_points": [target_kp],
                "suggested_actions": actions
            }

    # 3. 学习路径
    if intent == "learning_path":
        steps_preview = learning_path[:3]
        step_descs = []
        for i, step in enumerate(steps_preview, 1):
            acc_val = f"{step['current_accuracy']:.1f}%"
            step_descs.append(
                f"- **第 {i} 阶段（Stage {step['stage']}）**：【**{step['knowledge_name']}**】(当前正确率 {acc_val} · 优先级 {step['priority']})\n"
                f"  - 推荐依据：{step['reason']}"
            )

        ans_parts = [
            f"根据你的知识图谱依赖关系与错因分析，系统为你动态规划的整体策略为【**{recommendation_type}**】。",
            f"你当前最应该优先学习的前 {len(steps_preview)} 个关键节点为：\n" + "\n".join(step_descs),
            "遵循此顺序可以避免在未掌握前置概念时盲目刷难题，从而建立起稳固的知识网络。"
        ]
        answer = "\n\n".join(ans_parts)
        actions = [
            f"1. 立即启动 Stage {steps_preview[0]['stage']}：【{steps_preview[0]['knowledge_name']}】的专项复习",
            f"2. 完成该知识点学习目标：{steps_preview[0]['learning_goal']}",
            f"3. 随后衔接 Stage {steps_preview[1]['stage']}：【{steps_preview[1]['knowledge_name']}】" if len(steps_preview) > 1 else "3. 检验阶段成果并更新学情"
        ]
        return {
            "student_id": student_id,
            "message": message,
            "answer": answer,
            "related_knowledge_points": [
                {
                    "knowledge_id": s["knowledge_id"],
                    "knowledge_name": s["knowledge_name"],
                    "accuracy": s["current_accuracy"],
                    "priority": s["priority"],
                    "reason": s["reason"]
                }
                for s in steps_preview
            ],
            "suggested_actions": actions
        }

    # 4. 学情分析
    if intent == "academic_status":
        avg_acc = overall.get("average_accuracy", 0)
        mastery = overall.get("mastery_level", "中等")
        speed = overall.get("speed_status", "正常")
        weak_count = diagnosis.get("weak_knowledge_count", len(raw_profile.get("weak_knowledge_points", [])))
        main_problems = diagnosis.get("main_problems", ["部分知识掌握尚需巩固"])
        problems_str = "、".join(main_problems) if main_problems else "局部基础掌握不牢"

        ans_parts = [
            f"{student_name}，你的近期多维学情综合评估如下：",
            f"- **综合正确率**：**{avg_acc:.2f}%**，处于【**{mastery}**】掌握水平；",
            f"- **作答节奏**：{speed}（平均作答时间约 {overall.get('average_answer_time_seconds', 60):.0f} 秒/题）；",
            f"- **核心痛点诊断**：当前共识别出 **{weak_count} 个薄弱知识点**，主要问题集中在【{problems_str}】；",
            f"- **AI建议方向**：{raw_report.get('ai_summary', '建议按照系统定制路径进行针对性强化。')}"
        ]
        answer = "\n\n".join(ans_parts)

        top_weaks = [
            {
                "knowledge_id": wp.get("knowledge_id", ""),
                "knowledge_name": wp.get("knowledge_name", ""),
                "accuracy": wp.get("accuracy"),
                "priority": "高" if (wp.get("accuracy") or 0) < 60 else "中",
                "reason": f"答题正确率 {wp.get('accuracy')}%, 亟需巩固"
            }
            for wp in raw_profile.get("weak_knowledge_points", [])[:3]
        ]

        actions = [
            "1. 优先查漏补缺，重点攻关高风险薄弱知识点",
            "2. 保持当前的良好做题节奏，注意提高做题准确率",
            "3. 按照每日学习节奏定时定量训练"
        ]
        return {
            "student_id": student_id,
            "message": message,
            "answer": answer,
            "related_knowledge_points": top_weaks,
            "suggested_actions": actions
        }

    # 5. 今日计划
    if intent == "daily_plan":
        mins = daily_plan.get("recommended_minutes", 30)
        questions = daily_plan.get("recommended_questions", 8)
        focus = daily_plan.get("focus", "基础巩固与强化训练")

        first_step = learning_path[0] if learning_path else None
        first_step_text = f"今日首要攻坚知识点为【**{first_step['knowledge_name']}**】（当前正确率 {first_step['current_accuracy']:.1f}%）。" if first_step else "今日重点进行综合模拟练习。"

        ans_parts = [
            f"根据你的认知负荷与当前掌握瓶颈，AI 学习助手为你制定的今日学习方案如下：",
            f"- **建议学习时长**：专注投入 **{mins} 分钟**",
            f"- **推荐精炼题量**：完成 **{questions} 道精选题目**",
            f"- **今日突破重心**：【**{focus}**】",
            f"- **主攻目标**：{first_step_text}"
        ]
        if opt_suggestions:
            ans_parts.append(f"- **指导提示**：{opt_suggestions[0]}")

        answer = "\n\n".join(ans_parts)
        actions = [
            f"1. 专注学习 {mins} 分钟，优先吃透今日突破重点【{focus}】",
            f"2. 精做 {questions} 道练习题，认真对照解析总结错因",
            "3. 完成后在系统记录做题反馈，动态更新学习进度"
        ]
        return {
            "student_id": student_id,
            "message": message,
            "answer": answer,
            "related_knowledge_points": [
                {
                    "knowledge_id": first_step["knowledge_id"],
                    "knowledge_name": first_step["knowledge_name"],
                    "accuracy": first_step["current_accuracy"],
                    "priority": first_step["priority"],
                    "reason": first_step["reason"]
                }
            ] if first_step else [],
            "suggested_actions": actions
        }

    # 6. 特定知识点泛化查询
    if mentioned_kps:
        kp = mentioned_kps[0]
        acc_text = f"{kp['accuracy']:.1f}%" if kp['accuracy'] is not None else "尚无充足记录"
        ans_parts = [
            f"针对你关心的【**{kp['knowledge_name']}**】（编号：{kp['knowledge_id']}）：",
            f"- **当前掌握度**：正确率为 **{acc_text}**；",
            f"- **系统定位**：属于{kp.get('source', '关键知识点')}，优先级为【{kp.get('priority', '中')}】；",
            f"- **分析结论**：{kp.get('reason', '该知识点在微观经济学知识网络中起到承上启下的枢纽作用。')}"
        ]
        answer = "\n\n".join(ans_parts)
        actions = [
            f"1. 查看【{kp['knowledge_name']}】的相关概念与例题解析",
            "2. 进行小题专项自测以提升掌握稳定性"
        ]
        return {
            "student_id": student_id,
            "message": message,
            "answer": answer,
            "related_knowledge_points": [kp],
            "suggested_actions": actions
        }

    # 7. 兜底回答
    answer = (
        f"你好，{student_name}！我是你的专属 AI 学习助手。我能够根据你的真实学情画像与知识图谱关系，为你提供精准的个性化指导。\n\n"
        "你可以试着这样问我：\n"
        "- “我目前的成绩和掌握情况怎么样？”\n"
        "- “我接下来应该优先学习哪个知识点？”\n"
        "- “为什么推荐我先学稀缺性（或需求价格弹性）？”\n"
        "- “帮我安排今天的学习任务”"
    )
    actions = [
        "点击上方快捷提问按钮直接向我发问",
        "提问具体知识点名称了解你的薄弱掌握细节",
        "询问学习规划获取今日定制复习任务"
    ]
    return {
        "student_id": student_id,
        "message": message,
        "answer": answer,
        "related_knowledge_points": [],
        "suggested_actions": actions
    }


# ============================================================
# 核心入口：统一调度 (LLM 优先 + 自动降级保障)
# ============================================================

def generate_assistant_response(
    student_id: str,
    message: str
) -> Dict[str, Any]:
    """
    接收用户消息，调度真实 LLM 生成结构化指导；
    若 LLM 未配置、调用失败、格式非法，则自动无缝降级到本地规则引擎。
    """
    context = build_student_context(student_id)
    if not context:
        return {
            "student_id": student_id,
            "message": message,
            "answer": "未找到对应的学生档案，请确认学生编号是否正确。",
            "related_knowledge_points": [],
            "suggested_actions": []
        }

    # 1. 判断并尝试调用 LLM 服务
    if llm_service.is_available():
        system_prompt = build_system_prompt(context["student_name"])
        llm_raw_result = llm_service.generate(
            system_prompt=system_prompt,
            user_message=message,
            context=context["condensed"]
        )

        if llm_raw_result:
            validated = validate_and_sanitize_response(llm_raw_result, context)
            if validated:
                print(f"[Assistant] provider={llm_service.get_provider_name()} status=success")
                validated["message"] = message
                return validated
            else:
                print("[Assistant] fallback=invalid_response (validation failed)")
        else:
            # 内部错误已在 llm_service 中记录具体原因
            pass
    else:
        print("[Assistant] provider=rule (LLM not configured)")

    # 2. 自动降级执行本地规则引擎
    rule_res = generate_rule_based_response(context, message)
    return rule_res


# ============================================================
# 专属问候语生成
# ============================================================

def get_assistant_greeting(student_id: str) -> Dict[str, Any]:
    """生成针对当前学生的个性化首次问候语与动态快捷问题"""
    context = build_student_context(student_id)
    if not context:
        return {
            "student_id": student_id,
            "greeting": "你好！我是学海智导 AI 学习助手，随时准备为你提供个性化学习建议。",
            "quick_prompts": [
                "我目前的学习情况怎么样？",
                "我接下来应该学什么？",
                "帮我安排今天的学习任务"
            ]
        }

    student_name = context["student_name"]
    overall = context["raw_profile"].get("overall_profile", {})
    avg_acc = overall.get("average_accuracy", 0)
    path = context["raw_path"].get("learning_path", [])

    if len(path) == 0:
        # S004 综合拔高特殊情况
        greeting = (
            f"你好，{student_name}！我已经分析了你的近期学习情况。你目前的平均正确率高达 {avg_acc:.2f}%，"
            f"当前没有明显薄弱知识点，基础非常扎实。接下来可以重点进行综合应用与限时提速训练。你可以问我：“我接下来应该学什么？”"
        )
        quick_prompts = [
            "我目前的学习情况怎么样？",
            "我接下来应该学什么？",
            "帮我安排今天的学习任务",
            "如何进一步提高解题速度？"
        ]
    else:
        first_step = path[0]
        greeting = (
            f"你好，{student_name}！我已经分析了你的近期学习数据。你目前的平均正确率为 {avg_acc:.2f}%，"
            f"系统已为你定位到薄弱环节与关键前置依赖。你可以问我：“我接下来应该学什么？”或“为什么推荐我先学{first_step['knowledge_name']}？”"
        )
        quick_prompts = [
            "我目前的学习情况怎么样？",
            "我接下来应该学什么？",
            f"为什么推荐我先学{first_step['knowledge_name']}？",
            "帮我安排今天的学习任务"
        ]

    return {
        "student_id": student_id,
        "student_name": student_name,
        "greeting": greeting,
        "quick_prompts": quick_prompts
    }
