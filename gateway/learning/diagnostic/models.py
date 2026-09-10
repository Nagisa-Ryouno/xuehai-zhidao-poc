# -*- coding: utf-8 -*-
"""
gateway/learning/diagnostic/models.py
学海智导 (Xuehai Zhidao) - 极速前测与学情诊断数据模型
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DiagnosticOption(BaseModel):
    """前测题目选项（脱敏）"""
    key: str = Field(..., description="选项标识，如 A, B, C, D")
    text: str = Field(..., description="选项文本描述")


class DiagnosticQuestionPublic(BaseModel):
    """前测题目对外公开模型（绝不包含正确答案与解析）"""
    question_id: str = Field(..., description="题目唯一标识")
    knowledge_id: str = Field(..., description="关联知识点 ID")
    knowledge_name: str = Field(..., description="关联知识点名称")
    stem: str = Field(..., description="题干")
    options: List[DiagnosticOption] = Field(..., description="选项列表")
    difficulty: int = Field(default=1, description="难度等级 1~3")


class PretestSession(BaseModel):
    """前测会话模型"""
    session_id: str = Field(..., description="会话唯一 ID")
    student_id: str = Field(..., description="学生 ID")
    goal: str = Field(..., description="学习目标")
    questions: List[DiagnosticQuestionPublic] = Field(..., description="精选 3 道诊断题")
    created_at: str = Field(..., description="创建时间 ISO 格式")
    completed: bool = Field(default=False, description="是否已完成提交")


class PretestSubmitRequest(BaseModel):
    """提交前测作答请求"""
    answers: Dict[str, str] = Field(
        ..., description="作答字典，key 为 question_id，value 为选中的选项 key (如 'A')"
    )


class KnowledgeDiagnostic(BaseModel):
    """单知识点学情诊断细节"""
    knowledge_id: str = Field(..., description="考点 ID")
    knowledge_name: str = Field(..., description="考点名称")
    question_id: str = Field(..., description="题目 ID")
    user_answer: str = Field(..., description="用户作答")
    is_correct: bool = Field(..., description="是否正确")
    estimated_mastery: float = Field(..., description="初步诊断掌握度预估 (0.00 ~ 1.00)")
    status: str = Field(..., description="掌握标签: WEAK / DEVELOPING / PROFICIENT")
    feedback: str = Field(..., description="诊断反馈说明")


class DiagnosticResult(BaseModel):
    """综合学情诊断报告"""
    session_id: str = Field(..., description="关联会话 ID")
    student_id: str = Field(..., description="学生 ID")
    goal: str = Field(..., description="学习目标")
    total_questions: int = Field(default=3, description="前测总题数")
    correct_count: int = Field(..., description="正确题数")
    accuracy: float = Field(..., description="前测正确率 (0.00 ~ 1.00)")
    overall_level: str = Field(
        ..., description="综合基础评价: SOLID_FOUNDATION / PARTIAL_FOUNDATION / NEEDS_REMEDIAL"
    )
    overall_level_label: str = Field(
        ..., description="综合评价中文标签: 稳固基础 / 部分掌握 / 亟需巩固"
    )
    knowledge_diagnostics: List[KnowledgeDiagnostic] = Field(
        default_factory=list, description="各考点诊断明细"
    )
    weaknesses: List[str] = Field(
        default_factory=list, description="薄弱考点 ID 列表"
    )
    strengths: List[str] = Field(
        default_factory=list, description="优势考点 ID 列表"
    )
    summary_text: str = Field(..., description="针对性诊断结论与学习建议")
    recommended_focus_id: Optional[str] = Field(
        default=None, description="建议第一优先攻坚的知识点 ID"
    )
    completed_at: str = Field(..., description="完成时间戳")
