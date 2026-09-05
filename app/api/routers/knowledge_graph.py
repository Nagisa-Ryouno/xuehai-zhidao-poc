# -*- coding: utf-8 -*-
"""
app.api.routers.knowledge_graph
微观经济学知识图谱拓扑与学情联动路由
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from app.services.knowledge_graph_service import knowledge_graph_service
from app.services.student_service import student_service

router = APIRouter(tags=["KnowledgeGraph"])


@router.get("/api/students/{student_id}/knowledge-graph")
def get_student_knowledge_graph(student_id: str) -> Dict[str, Any]:
    """
    获取指定学生的微观经济学知识图谱拓扑与学情联动数据
    包含全部 30 个知识点、前置依赖边、各知识点掌握状态与 AI 图谱洞察
    """
    profile = student_service.get_student_profile(student_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"找不到学生：{student_id}",
        )
    return knowledge_graph_service.get_student_knowledge_graph(student_id)
