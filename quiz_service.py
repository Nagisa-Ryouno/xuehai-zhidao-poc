# -*- coding: utf-8 -*-
"""
quiz_service.py
学海智导 (Xuehai Zhidao) V2 分知识点微测验服务层

职责：
1. 加载并维护微观经济学分知识点微测验题库 (data/quiz_bank.json)
2. 提供脱敏的公共题目查询接口（严格禁止向学生暴露正确答案与解析）
3. 执行服务端安全判题，确保选项合法与题目真实性
4. 联动 P0-3 学习事件记录器 (event_service.record_event) 自动记录 QUESTION_ATTEMPT 事件
5. 联动 P0-6 BKT 事件处理器 (bkt_event_processor.process_event) 实现测验作答 -> 事件落盘 -> 认知状态演进的原子流式闭环
6. 坚守确定性代码边界：绝对不调用 DAG 路径重规划或 LLM
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from pydantic import BaseModel, Field

import bkt_event_processor
import event_service
from knowledge_graph_service import knowledge_graph_service
import path_replanning_service
from path_replanning_service import DecisionAuditEnvelope

# ============================================================
# 文件路径配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_QUIZ_FILE = BASE_DIR / "data" / "quiz_bank.json"

# ============================================================
# 数据模型契约
# ============================================================

class QuizOption(BaseModel):
    key: str = Field(..., description="选项标号，如 A, B, C, D")
    text: str = Field(..., description="选项文本")


class QuizQuestionPublic(BaseModel):
    """向学生端公开的题目数据模型（绝不暴露答案与解析）"""
    question_id: str
    knowledge_id: str
    stem: str
    options: List[QuizOption]
    difficulty: int


class QuizQuestionInternal(QuizQuestionPublic):
    """服务端内部使用的完整题目模型（含正确答案与详解）"""
    answer: str
    explanation: str


class QuizKnowledgeListResponse(BaseModel):
    knowledge_id: str
    knowledge_name: str
    questions: List[QuizQuestionPublic]


class QuizSubmitRequest(BaseModel):
    student_id: str = Field(..., min_length=1, description="学生ID")
    question_id: str = Field(..., min_length=1, description="题目ID")
    selected_option: str = Field(..., min_length=1, description="学生提交的选项Key")
    time_spent_ms: Optional[int] = Field(default=None, description="答题耗时(毫秒)")


def get_mastery_state(mastery: float) -> str:
    """
    根据 BKT 掌握概率推导三态认知等级：
    P(L) >= 0.80: MASTERED (达标掌握)
    0.60 <= P(L) < 0.80: DEVELOPING (巩固提升中)
    P(L) < 0.60: WEAK (薄弱/危险)
    """
    if mastery >= 0.80:
        return "MASTERED"
    elif mastery >= 0.60:
        return "DEVELOPING"
    else:
        return "WEAK"


class LearningStateSnapshot(BaseModel):
    """
    流式闭环自动更新返回的 BKT 学情状态快照
    """
    updated: bool = Field(..., description="BKT 状态是否已成功演进")
    mastery_probability: Optional[float] = Field(default=None, description="更新后的掌握概率 P(L)")
    mastery_percent: Optional[float] = Field(default=None, description="掌握度百分比 (0~100)")
    state: Optional[str] = Field(default=None, description="掌握度等级 (WEAK / DEVELOPING / MASTERED)")
    attempts: Optional[int] = Field(default=None, description="累计作答次数")
    consecutive_correct: Optional[int] = Field(default=None, description="连续答对次数")
    reason: Optional[str] = Field(default=None, description="状态附加说明或未更新原因")


class QuizSubmitResponse(BaseModel):
    is_correct: bool
    correct_option: str
    explanation: str
    knowledge_id: str
    question_id: str
    event_id: str
    learning_state: Optional[LearningStateSnapshot] = Field(
        default=None, description="流式闭环自动更新的 BKT 学情状态快照"
    )
    replanning: Optional[path_replanning_service.DecisionAuditEnvelope] = Field(
        default=None, description="局部动态路径重规划审计信封"
    )


# ============================================================
# 题库缓存与读取
# ============================================================

_cached_quiz_bank: Optional[List[QuizQuestionInternal]] = None


def load_quiz_bank(file_path: Optional[Path] = None) -> List[QuizQuestionInternal]:
    """加载题库 JSON 文件并解析为内部模型"""
    global _cached_quiz_bank
    target_file = file_path or DEFAULT_QUIZ_FILE

    if not target_file.exists():
        return []

    with open(target_file, "r", encoding="utf-8") as f:
        raw_list = json.load(f)

    questions = [QuizQuestionInternal(**item) for item in raw_list]
    if file_path is None:
        _cached_quiz_bank = questions
    return questions


def get_all_questions(bank_file: Optional[Path] = None) -> List[QuizQuestionInternal]:
    """获取所有题目内部模型列表"""
    if bank_file is not None:
        return load_quiz_bank(bank_file)
    global _cached_quiz_bank
    if _cached_quiz_bank is None:
        return load_quiz_bank()
    return _cached_quiz_bank


def is_valid_knowledge_id(knowledge_id: str) -> bool:
    """校验 knowledge_id 是否存在于真实知识图谱 30 个考点中"""
    return knowledge_graph_service.is_valid_knowledge_id(knowledge_id)


def get_question_by_id(
    question_id: str,
    bank_file: Optional[Path] = None,
) -> Optional[QuizQuestionInternal]:
    """通过 question_id 检索单道题目详情"""
    questions = get_all_questions(bank_file)
    for q in questions:
        if q.question_id == question_id:
            return q
    return None


# ============================================================
# 核心业务服务接口
# ============================================================

def get_questions_by_knowledge_id(
    knowledge_id: str,
    bank_file: Optional[Path] = None,
) -> QuizKnowledgeListResponse:
    """
    按知识点查询测验题目（返回脱敏公开模型）
    若知识点不存在，抛出 404
    """
    if not is_valid_knowledge_id(knowledge_id):
        raise HTTPException(status_code=404, detail=f"未找到对应知识点：{knowledge_id}")

    raw_kp = knowledge_graph_service.get_knowledge_point(knowledge_id) or {}
    knowledge_name = raw_kp.get("knowledge_name", knowledge_id)

    all_q = get_all_questions(bank_file)
    matched: List[QuizQuestionPublic] = []

    for q in all_q:
        if q.knowledge_id == knowledge_id:
            # 转换为公共模型，安全剔除 answer 与 explanation
            matched.append(
                QuizQuestionPublic(
                    question_id=q.question_id,
                    knowledge_id=q.knowledge_id,
                    stem=q.stem,
                    options=q.options,
                    difficulty=q.difficulty,
                )
            )

    return QuizKnowledgeListResponse(
        knowledge_id=knowledge_id,
        knowledge_name=knowledge_name,
        questions=matched,
    )


def submit_quiz_answer(
    req: QuizSubmitRequest,
    bank_file: Optional[Path] = None,
    events_file: Optional[Path] = None,
    states_file: Optional[Path] = None,
    processed_file: Optional[Path] = None,
    path_states_file: Optional[Path] = None,
) -> QuizSubmitResponse:
    """
    提交测验答案：
    1. 校验 question_id 是否存在 (404)
    2. 校验 selected_option 是否在题目合法选项中 (422)
    3. 服务端权威判定 is_correct
    4. 权威生成 LearningEvent (QUESTION_ATTEMPT) 并写入日志
    5. 联动 BKT 事件处理器流式演进学生认知状态，保证严格幂等与事实来源不丢失
    6. 联动局部动态路径重规划服务 (evaluate_and_replan) 触发路径执行状态演进与审计信封生成
    7. 返回判题响应、最新学情状态快照与重规划审计信封
    """
    question = get_question_by_id(req.question_id, bank_file)
    if not question:
        raise HTTPException(status_code=404, detail=f"题目不存在：{req.question_id}")

    # 校验选项是否合法
    valid_option_keys = [opt.key for opt in question.options]
    if req.selected_option not in valid_option_keys:
        raise HTTPException(
            status_code=422,
            detail=f"非法选项：{req.selected_option}，可选选项为：{valid_option_keys}",
        )

    is_correct = (req.selected_option == question.answer)

    # 组装 LearningEvent 有效载荷 (Payload)
    event_payload: Dict[str, Any] = {
        "question_id": question.question_id,
        "is_correct": is_correct,
        "selected_option": req.selected_option,
    }
    if req.time_spent_ms is not None:
        event_payload["time_spent_ms"] = req.time_spent_ms

    client_ts = datetime.now(timezone.utc).astimezone().isoformat()
    event_id = f"evt-quiz-{uuid.uuid4().hex[:12]}"

    # 服务端权威确定 knowledge_id（防客户端篡改）
    event_in = event_service.LearningEventCreate(
        event_id=event_id,
        student_id=req.student_id,
        knowledge_id=question.knowledge_id,
        event_type="QUESTION_ATTEMPT",
        payload=event_payload,
        client_timestamp=client_ts,
    )

    stored_event = event_service.record_event(event_in, target_file=events_file)

    # ============================================================
    # P0-7 闭环：由落盘的 QUESTION_ATTEMPT 事件驱动 BKT 状态自动演进
    # 保持 Event 为权威事实来源，容错降级，不因 BKT 异常丢弃 Event
    # ============================================================
    learning_state: Optional[LearningStateSnapshot] = None
    replanning_envelope: Optional[path_replanning_service.DecisionAuditEnvelope] = None
    try:
        bkt_res = bkt_event_processor.process_event(
            stored_event,
            states_file=states_file,
            processed_file=processed_file,
        )
        if bkt_res.status == "updated" and bkt_res.state is not None:
            prob = bkt_res.state.mastery_probability
            learning_state = LearningStateSnapshot(
                updated=True,
                mastery_probability=prob,
                mastery_percent=round(prob * 100.0, 2),
                state=get_mastery_state(prob),
                attempts=bkt_res.state.attempts,
                consecutive_correct=bkt_res.state.consecutive_correct,
            )
            # ============================================================
            # P0-8 闭环：BKT 更新成功驱动局部动态路径重规划
            # ============================================================
            try:
                prev_mastered = (bkt_res.before_mastery is not None and bkt_res.before_mastery >= 0.80)
                replanning_envelope = path_replanning_service.evaluate_and_replan(
                    student_id=req.student_id,
                    knowledge_id=question.knowledge_id,
                    before_mastery=bkt_res.before_mastery or 0.20,
                    after_mastery=bkt_res.after_mastery or bkt_res.state.mastery_probability,
                    consecutive_incorrect=bkt_res.state.consecutive_incorrect,
                    previously_mastered=prev_mastered,
                    is_task_context=True,
                    trace_id=stored_event.event_id,
                    states_file=path_states_file,
                    bkt_states_file=states_file,
                )
            except Exception:
                replanning_envelope = None
        elif bkt_res.status == "already_processed" and bkt_res.state is not None:
            prob = bkt_res.state.mastery_probability
            learning_state = LearningStateSnapshot(
                updated=False,
                mastery_probability=prob,
                mastery_percent=round(prob * 100.0, 2),
                state=get_mastery_state(prob),
                attempts=bkt_res.state.attempts,
                consecutive_correct=bkt_res.state.consecutive_correct,
                reason=bkt_res.reason or "事件之前已完成处理",
            )
        else:
            learning_state = LearningStateSnapshot(
                updated=False,
                mastery_probability=None,
                reason=bkt_res.reason or f"BKT消费状态: {bkt_res.status}",
            )
    except Exception as e:
        # 事实来源保证：即使 BKT 发生严重异常，Event 已确凿落盘，绝不伪装更新成功
        learning_state = LearningStateSnapshot(
            updated=False,
            mastery_probability=None,
            reason=f"BKT自动流式演进异常: {str(e)}",
        )

    return QuizSubmitResponse(
        is_correct=is_correct,
        correct_option=question.answer,
        explanation=question.explanation,
        knowledge_id=question.knowledge_id,
        question_id=question.question_id,
        event_id=stored_event.event_id,
        learning_state=learning_state,
        replanning=replanning_envelope,
    )
