# -*- coding: utf-8 -*-
"""
gateway.prompt
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage E: External LLM 提示词工程与输入白名单构建器

设计原则：
1. 纯函数与确定性 (Pure Function & Determinism)：无 random、无 datetime.now()、无 uuid
2. 输入白名单边界：严格只接受 LearningPromptContext，杜绝原始领域实体穿透
3. 权限隔离硬约束：System Prompt 严格声明 AI 零学习决策权，禁止篡改状态与掌握度
4. 明确结构化输出约束：指定 JSON 格式输出，与 StructuredAIResponse 契约完全对齐
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from gateway.models import LearningPromptContext


class ExternalPromptPayload(BaseModel):
    """构建好的外部大模型提示词完整载荷"""
    model_config = ConfigDict(extra="forbid")

    system_prompt: str
    user_prompt: str
    model: str
    response_format: str = "json_object"
    temperature: float = 0.0


SYSTEM_INSTRUCTION = """\
You are the Xuehai Zhidao (学海智导) AI Learning Companion.
Your role is strictly limited to explaining learning facts and providing pedagogical coaching in Chinese.

ABSOLUTE SAFETY & AUTHORITY BOUNDARIES:
1. AI is an explanatory assistant only. You have ZERO learning decision authority.
2. AI must NOT:
   - Modify, recalculate, or assign mastery levels (BKT mastery is strictly owned by the deterministic engine).
   - Unlock, lock, or transition knowledge graph nodes.
   - Mutate, reorder, or alter the learning path.
   - Modify PathState or Decision Core states.
   - Issue state transition or action commands (e.g. FORCE_UNLOCK, MUTATE_PATH).
   - Invent or extrapolate facts not present in the provided system context.
3. The 'next_action' in the context is a READ-ONLY system fact already determined by the learning engine. You must explain it to the student, but you cannot change it.
4. Output MUST be strictly valid JSON matching the StructuredAIResponse schema with fields:
   - "answer": string, your direct coaching explanation.
   - "referenced_facts": list of strings citing the provided system facts used.
   - "suggested_explanation": optional string, supplementary explanation.
   - "grounding_status": "grounded" or "insufficient_context".
"""


def build_external_prompt(
    context: LearningPromptContext,
    model: str = "mock-companion-v1",
) -> ExternalPromptPayload:
    """
    基于只读白名单上下文构建外部大模型提示词
    
    @param context 权威只读学习提示词上下文
    @param model 模型标识符
    @return ExternalPromptPayload 结构化提示词载荷
    """
    sf = context.system_facts

    # 1. 组装学生信息块
    student_section = (
        f"[STUDENT CONTEXT]\n"
        f"- ID: {sf.student_id}\n"
        f"- Name: {sf.student_name}\n"
        f"- Major: {sf.major}\n"
        f"- Grade: {sf.grade}\n"
        f"- Goal: {sf.learning_goal}"
    )

    # 2. 组装当前知识点事实块
    kp_section = (
        f"[CURRENT KNOWLEDGE POINT]\n"
        f"- Knowledge ID: {sf.current_knowledge_id}\n"
        f"- Knowledge Name: {sf.current_knowledge_name}\n"
        f"- Chapter: {sf.current_chapter}\n"
        f"- Path State: {sf.current_path_state}\n"
        f"- Current Mastery: {sf.current_mastery_percent:.1f}%\n"
        f"- Mastery Target: {sf.mastery_target_percent:.1f}%\n"
        f"- Mastery Gap: {sf.mastery_gap_percent:.1f}%\n"
        f"- Is Mastered: {sf.is_mastered}\n"
        f"- Prerequisites Met: {sf.prerequisites_met}\n"
        f"- Priority: {sf.path_priority}\n"
        f"- Path Completed: {sf.is_path_completed}"
    )

    # 3. 组装近次微测验客观事实 (若存在)
    quiz_section = ""
    if sf.recent_quiz:
        rq = sf.recent_quiz
        unlocked_str = ", ".join(rq.unlocked_nodes) if rq.unlocked_nodes else "None"
        quiz_section = (
            f"\n\n[RECENT ASSESSMENT FACT]\n"
            f"- Question ID: {rq.question_id}\n"
            f"- Correct: {rq.is_correct}\n"
            f"- Before Mastery: {rq.before_mastery_percent:.1f}%\n"
            f"- After Mastery: {rq.after_mastery_percent:.1f}%\n"
            f"- Delta: {rq.delta_percent:+.1f}%\n"
            f"- Engine Action: {rq.action}\n"
            f"- Reason Code: {rq.reason_code}\n"
            f"- Unlocked Nodes: {unlocked_str}"
        )

    # 4. 组装确定性下一步行动事实 (只读)
    na = sf.next_action
    action_section = (
        f"\n\n[DETERMINISTIC NEXT ACTION (READ-ONLY)]\n"
        f"- Action Type: {na.type}\n"
        f"- Action Label: {na.label}\n"
        f"- Target Knowledge ID: {na.target_knowledge_id}\n"
        f"- Action Rationale: {na.reason}"
    )

    # 5. 组装事实约束规则
    rules_text = (
        "\n".join(f"- {rule}" for rule in context.grounding_rules)
        if context.grounding_rules
        else "- 仅依据客观事实回答，严禁编造任何掌握度数值或考点。"
    )
    rules_section = f"\n\n[FACT GROUNDING RULES]\n{rules_text}"

    # 6. 组装学生问题
    question_section = f"\n\n[STUDENT QUESTION]\n{context.user_question}"

    user_prompt = f"{student_section}\n\n{kp_section}{quiz_section}{action_section}{rules_section}{question_section}"

    return ExternalPromptPayload(
        system_prompt=SYSTEM_INSTRUCTION.strip(),
        user_prompt=user_prompt.strip(),
        model=model.strip(),
        response_format="json_object",
        temperature=0.0,
    )
