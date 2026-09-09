# -*- coding: utf-8 -*-
"""
gateway.evaluation.calibration.bias
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 Checkpoint 3: Bias Audit Infrastructure
"""

import math
from typing import Any, Dict, List, Optional

from gateway.evaluation.judge.adapter import JudgeAdapter
from gateway.models import (
    LearningPromptContext,
    LearningPromptSystemFacts,
    PromptNextAction,
    StructuredAIResponse,
)


def _make_standard_audit_context() -> LearningPromptContext:
    return LearningPromptContext(
        user_question="老师，为什么奢侈品的需求价格弹性通常比较大，而必需品比较小？",
        system_facts=LearningPromptSystemFacts(
            student_id="S001",
            student_name="测试学生",
            major="经济学",
            grade="大一",
            learning_goal="微观经济学基础巩固",
            current_knowledge_id="K08",
            current_knowledge_name="需求价格弹性",
            current_chapter="第二章 需求与供给",
            current_path_state="IN_PROGRESS",
            current_mastery_percent=70.0,
            mastery_target_percent=80.0,
            mastery_gap_percent=10.0,
            is_mastered=False,
            prerequisites_met=True,
            path_priority="NORMAL",
            is_path_completed=False,
            recent_quiz=None,
            next_action=PromptNextAction(
                type="PRACTICE",
                label="巩固微测验",
                target_knowledge_id="K08",
                reason="强化弹性决定因素理解",
            ),
        ),
        grounding_rules=["必须基于客观事实回答"],
    )


def audit_verbosity_bias(
    judge_adapter: JudgeAdapter,
    delta_threshold: float = 0.15,
) -> Dict[str, Any]:
    """
    Bias 1: 长度偏好审计 (Verbosity Bias)
    构造语义等价的简明版与详尽版回答，检测 Judge 是否单纯因字数长度而产生系统性评分偏差。
    """
    context = _make_standard_audit_context()

    # 简明版回答 (核心逻辑完整无误)
    resp_short = StructuredAIResponse(
        answer="必需品缺乏替代品且为生活刚需，价格上涨也必须购买，因而弹性较小；奢侈品替代性强、非生活必需，价格上涨消费者可迅速放弃购买，因而弹性较大。你目前掌握度为70%，建议完成微测验加深理解！",
        referenced_facts=["current_knowledge_id=K08", "mastery=70.0%"],
        suggested_explanation="提炼必需品与奢侈品替代性差异对弹性的决定作用。",
        grounding_status="grounded",
    )

    # 详尽版回答 (相同核心逻辑，增加背景铺垫和修饰，但无额外新知识点)
    resp_long = StructuredAIResponse(
        answer=(
            "你好！这是一个非常经典的微观经济学问题。首先，根据经济学原理，物品的可替代性以及在生活中的必需程度是决定需求价格弹性的核心因素。"
            "对于大米、食用盐等生活必需品而言，一方面消费者日常维生不可或缺，另一方面市场上几乎不存在完全等价的低成本替代选择，"
            "因此即便价格发生较为显著的上涨，绝大多数消费者也只能被迫接受原价购买，需求量变动极其有限，呈现出显著的缺乏弹性特征。"
            "相反，对于高档珠宝、豪华跑车等奢侈品而言，它们并非生活的基本需求，且消费者往往具有极高选择自由度，一旦价格轻微上调，"
            "大家便会选择推迟消费或寻找其他娱乐方式替代，需求量因此发生剧烈下滑，呈现出富有弹性的特征。"
            "系统学情显示你当前在该考点的掌握度为 70.0%，距离 80.0% 仅一步之遥，完成配套练习即可巩固！"
        ),
        referenced_facts=["current_knowledge_id=K08", "mastery=70.0%"],
        suggested_explanation="详细对比必需品与奢侈品在替代性与需求弹性上的差异机理。",
        grounding_status="grounded",
    )

    res_short, _ = judge_adapter.evaluate_safe(context, resp_short)
    res_long, _ = judge_adapter.evaluate_safe(context, resp_long)

    score_short = res_short.overall_score if res_short else 0.5
    score_long = res_long.overall_score if res_long else 0.5

    delta = round(abs(score_long - score_short), 4)
    bias_detected = delta > delta_threshold

    return {
        "status": "PASS" if not bias_detected else "BIAS_DETECTED",
        "short_length": len(resp_short.answer),
        "long_length": len(resp_long.answer),
        "short_score": round(score_short, 4),
        "long_score": round(score_long, 4),
        "delta": delta,
        "delta_threshold": delta_threshold,
        "bias_detected": bias_detected,
        "note": "Heuristic audit assuming semantic equivalence across brevity levels",
    }


def audit_position_bias() -> Dict[str, Any]:
    """
    Bias 2: 位置偏好审计 (Position Bias)
    当前 Judge 契约为 Pointwise 单样本质量裁决，不存在 Pairwise 比较中 A/B 顺序导致的位置偏差。
    明确返回 NOT_APPLICABLE，严禁伪造数字。
    """
    return {
        "status": "NOT_APPLICABLE",
        "reason": "Current Judge contract is pointwise evaluation; position/ordering bias is not applicable",
        "bias_detected": False,
    }


def audit_style_bias(
    judge_adapter: JudgeAdapter,
    max_delta_threshold: float = 0.15,
) -> Dict[str, Any]:
    """
    Bias 3: 表达风格偏好审计 (Style Bias)
    构造语义等价的 4 种不同语言风格（学术严谨、通俗口语、干练极简、循序引导），检验 Judge 对文风差异的鲁棒性。
    """
    context = _make_standard_audit_context()

    styles: Dict[str, StructuredAIResponse] = {
        "formal": StructuredAIResponse(
            answer="从微观规制机理考察：生活必需品受制于刚性消费约束与替代品匮乏，需求价格弹性系数较低；高档奢侈品因边际效用替代空间广阔，弹性系数较高。当前学生掌握度为70.0%，建议实施强化训练。",
            referenced_facts=["K08", "70.0%"],
            suggested_explanation="学术规范化表达",
            grounding_status="grounded",
        ),
        "casual": StructuredAIResponse(
            answer="嗨！其实道理特别直观：油盐酱醋再贵你也得天天吃，没得选，所以价格怎么涨大家需求也差不多，弹性就小；名牌包包涨价了你可以立马不买，替代品又多，所以弹性就大。你现在学了70%啦，加油再刷套微测验！",
            referenced_facts=["K08", "70.0%"],
            suggested_explanation="通俗日常化表达",
            grounding_status="grounded",
        ),
        "concise": StructuredAIResponse(
            answer="必需品：无替代品、刚需，弹性小。奢侈品：替代品多、非刚需，弹性大。当前掌握度70%，建议练习。",
            referenced_facts=["K08", "70.0%"],
            suggested_explanation="极简提炼表达",
            grounding_status="grounded",
        ),
        "verbose": StructuredAIResponse(
            answer="让我们一步步来分析：首先看必需品，人们生活中无论如何不能缺少它们，因此在价格上涨时不会轻易压缩消费，表现为缺乏弹性；再看奢侈品，作为可选消费品，价格变动极易促使消费者转向其他商品，表现为富有弹性。当前掌握度70%，建议完成推荐测试！",
            referenced_facts=["K08", "70.0%"],
            suggested_explanation="步骤循序式表达",
            grounding_status="grounded",
        ),
    }

    style_scores: Dict[str, float] = {}
    for style_name, resp in styles.items():
        res, _ = judge_adapter.evaluate_safe(context, resp)
        score = res.overall_score if res else 0.5
        style_scores[style_name] = round(score, 4)

    scores_list = list(style_scores.values())
    max_delta = round(max(scores_list) - min(scores_list), 4)

    # 计算标准差
    mean_score = sum(scores_list) / len(scores_list)
    variance = sum((s - mean_score) ** 2 for s in scores_list) / len(scores_list)
    std_dev = round(math.sqrt(variance), 4)

    bias_detected = max_delta > max_delta_threshold

    return {
        "status": "PASS" if not bias_detected else "BIAS_DETECTED",
        "style_scores": style_scores,
        "max_delta": max_delta,
        "max_delta_threshold": max_delta_threshold,
        "std_dev": std_dev,
        "bias_detected": bias_detected,
    }


def audit_self_preference() -> Dict[str, Any]:
    """
    Bias 4: 自偏好审计 (Self-Preference Bias)
    当前离线环境与单向上下文投影中，待评测 Candidate 来源模型签名与 Judge 模型元数据解耦，无法获取生成者身份。
    明确返回 NOT_AVAILABLE，严禁伪造。
    """
    return {
        "status": "NOT_AVAILABLE",
        "reason": "Generator model identity is not tracked in current evaluation context projection; cannot measure self-preference bias",
        "bias_detected": None,
    }


def run_full_bias_audit(judge_adapter: JudgeAdapter) -> Dict[str, Any]:
    """
    运行全量偏见审计套件
    """
    return {
        "verbosity_bias": audit_verbosity_bias(judge_adapter),
        "position_bias": audit_position_bias(),
        "style_bias": audit_style_bias(judge_adapter),
        "self_preference": audit_self_preference(),
    }
