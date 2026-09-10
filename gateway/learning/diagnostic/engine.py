# -*- coding: utf-8 -*-
"""
gateway/learning/diagnostic/engine.py
学海智导 (Xuehai Zhidao) - 极速前测与学情诊断执行引擎

职责：
1. 目标相关且跨前置拓扑的 3 题极速前测组卷
2. 绝对剔除正确答案与解析的公开题目输出
3. 客观评分与多维初步诊断报告生成
4. 纯只读评估：绝不污染正式 BKT 状态与正式事件仓储
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings
from app.services.knowledge_graph_service import knowledge_graph_service
from gateway.learning.diagnostic.models import (
    DiagnosticOption,
    DiagnosticQuestionPublic,
    DiagnosticResult,
    KnowledgeDiagnostic,
    PretestSession,
    PretestSubmitRequest,
)

# 内存会话与诊断结果缓存（支持单元测试与快速交互）
_sessions: Dict[str, PretestSession] = {}
_results_by_session: Dict[str, DiagnosticResult] = {}
_latest_result_by_student: Dict[str, DiagnosticResult] = {}


def _get_quiz_bank() -> Dict[str, dict]:
    """读取种子题库，建立 question_id 索引"""
    quiz_file = settings.QUIZ_BANK_FILE
    if not quiz_file.exists():
        # Fallback to local seeds
        quiz_file = settings.PROJECT_ROOT / "data" / "seeds" / "quiz_bank.json"
    with open(quiz_file, "r", encoding="utf-8") as f:
        items = json.load(f)
    return {item["question_id"]: item for item in items}


def select_diagnostic_question_ids(goal: str) -> List[str]:
    """
    根据学习目标确定性精选 3 道跨越前置链路的诊断题。
    
    规则：
    1. 相同目标输入必须产生 100% 确定且相同的题目序列；
    2. 严格覆盖 3 个不同的核心知识点；
    3. 题目按前置拓扑序（根前置 -> 中继 -> 进阶/核心）排列。
    """
    goal_lower = goal.lower()
    
    if any(kw in goal_lower for kw in ["弹性", "税收", "k08", "k09", "k11", "elasticity"]):
        # 弹性与税收目标：覆盖 机会成本(K02) -> 需求理论(K04) -> 需求价格弹性(K08)
        return ["Q-K02-01", "Q-K04-01", "Q-K08-01"]
    
    if any(kw in goal_lower for kw in ["供求", "均衡", "市场", "k06", "k07", "equilibrium"]):
        # 供求均衡目标：覆盖 稀缺性(K01) -> 需求理论(K04) -> 市场均衡(K06)
        return ["Q-K01-01", "Q-K04-01", "Q-K06-01"]
    
    # 默认微观经济学基础目标：覆盖 稀缺性(K01) -> 机会成本(K02) -> 需求定理(K04)
    return ["Q-K01-01", "Q-K02-01", "Q-K04-01"]


def create_pretest_session(student_id: str, goal: str) -> PretestSession:
    """
    创建 3 题极速前测会话。
    绝不向返回结果泄漏 answer 或 explanation。
    """
    bank = _get_quiz_bank()
    question_ids = select_diagnostic_question_ids(goal)
    
    questions_public: List[DiagnosticQuestionPublic] = []
    for qid in question_ids:
        raw = bank.get(qid)
        if not raw:
            continue
        kid = raw.get("knowledge_id", "")
        kp = knowledge_graph_service.get_knowledge_point(kid)
        kname = kp.get("knowledge_name", kid) if kp else kid
        
        options = [
            DiagnosticOption(key=opt["key"], text=opt["text"])
            for opt in raw.get("options", [])
        ]
        
        questions_public.append(
            DiagnosticQuestionPublic(
                question_id=qid,
                knowledge_id=kid,
                knowledge_name=kname,
                stem=raw.get("stem", ""),
                options=options,
                difficulty=raw.get("difficulty", 1),
            )
        )
    
    session_id = f"pretest-{student_id}-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    
    session = PretestSession(
        session_id=session_id,
        student_id=student_id,
        goal=goal,
        questions=questions_public,
        created_at=now_iso,
        completed=False,
    )
    
    _sessions[session_id] = session
    return session


def evaluate_pretest(session_id: str, answers: Dict[str, str]) -> DiagnosticResult:
    """
    评估前测作答，生成结构化学情诊断结果。
    
    严格红线：
    - 绝不向正式 EventRepository 写入 QUESTION_ATTEMPT 事件；
    - 绝不更新正式 BKT 状态或 PathState 仓储。
    """
    session = _sessions.get(session_id)
    if not session:
        raise ValueError(f"Pretest session '{session_id}' not found")
    
    bank = _get_quiz_bank()
    diagnostics: List[KnowledgeDiagnostic] = []
    weaknesses: List[str] = []
    strengths: List[str] = []
    
    for q in session.questions:
        qid = q.question_id
        kid = q.knowledge_id
        user_ans = answers.get(qid, "").strip().upper()
        raw = bank.get(qid, {})
        standard_ans = raw.get("answer", "").strip().upper()
        
        is_correct = bool(user_ans and user_ans == standard_ans)
        
        if is_correct:
            est_mastery = 0.75
            status = "DEVELOPING"
            feedback = "基础先修概念掌握准确，先修逻辑清晰。"
            strengths.append(kid)
        else:
            est_mastery = 0.25
            status = "WEAK"
            feedback = "该先修关键点存在认知盲区，建议列为优先攻坚节点。"
            weaknesses.append(kid)
            
        diagnostics.append(
            KnowledgeDiagnostic(
                knowledge_id=kid,
                knowledge_name=q.knowledge_name,
                question_id=qid,
                user_answer=user_ans,
                is_correct=is_correct,
                estimated_mastery=est_mastery,
                status=status,
                feedback=feedback,
            )
        )
    
    correct_count = sum(1 for d in diagnostics if d.is_correct)
    total_q = len(session.questions)
    accuracy = round(correct_count / total_q, 4) if total_q > 0 else 0.0
    
    if correct_count == 3:
        overall_level = "SOLID_FOUNDATION"
        overall_level_label = "稳固基础"
        summary_text = "前置基础知识扎实，已具备直接攻坚高阶核心机制的良好条件。"
    elif correct_count in (1, 2):
        overall_level = "PARTIAL_FOUNDATION"
        overall_level_label = "部分掌握"
        summary_text = "掌握部分前置核心概念，但在关键推导与底层机制上存在盲区，建议沿前置链路查漏补缺。"
    else:
        overall_level = "NEEDS_REMEDIAL"
        overall_level_label = "亟需巩固"
        summary_text = "前置先修概念较为薄弱，直接进入综合应用容易产生认知过载，系统已为你重组基础前置攻坚航线。"
        
    # 首选攻坚节点：优先选取拓扑序最靠前的薄弱考点
    recommended_focus_id = weaknesses[0] if weaknesses else (
        session.questions[-1].knowledge_id if session.questions else None
    )
    
    now_iso = datetime.now(timezone.utc).isoformat()
    result = DiagnosticResult(
        session_id=session_id,
        student_id=session.student_id,
        goal=session.goal,
        total_questions=total_q,
        correct_count=correct_count,
        accuracy=accuracy,
        overall_level=overall_level,
        overall_level_label=overall_level_label,
        knowledge_diagnostics=diagnostics,
        weaknesses=weaknesses,
        strengths=strengths,
        summary_text=summary_text,
        recommended_focus_id=recommended_focus_id,
        completed_at=now_iso,
    )
    
    session.completed = True
    _results_by_session[session_id] = result
    _latest_result_by_student[session.student_id] = result
    
    return result


def get_pretest_session(session_id: str) -> Optional[PretestSession]:
    """获取前测会话信息"""
    return _sessions.get(session_id)


def get_latest_diagnostic_result(student_id: str) -> Optional[DiagnosticResult]:
    """获取学生最新的前测诊断结果"""
    return _latest_result_by_student.get(student_id)


def clear_pretest_cache() -> None:
    """测试时清空缓存"""
    _sessions.clear()
    _results_by_session.clear()
    _latest_result_by_student.clear()
