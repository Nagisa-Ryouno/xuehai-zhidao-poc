# -*- coding: utf-8 -*-
"""
app.api.schemas.knowledge_graph
知识图谱拓扑与学情联动响应 DTO 模型
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class KnowledgeGraphNode(BaseModel):
    """知识图谱节点模型"""
    id: str
    name: str
    chapter: str
    description: str
    difficulty: float
    accuracy: Optional[float] = None
    mastery_status: str
    is_weak: bool
    is_prerequisite: bool
    is_recommended: bool


class KnowledgeGraphEdge(BaseModel):
    """知识图谱依赖边模型"""
    id: str
    source: str
    target: str
    type: str = "prerequisite"


class KnowledgeGraphResponse(BaseModel):
    """知识图谱综合响应"""
    student_id: str
    student_name: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    stats: Dict[str, Any]
    ai_insight: Dict[str, Any]
