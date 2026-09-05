# -*- coding: utf-8 -*-
"""
knowledge_graph_service.py
学海智导 · AI 知识图谱服务层 (Backward-compatible Facade)

向后兼容门面，内部委托给 app.services.knowledge_graph_service。
"""

from app.services.knowledge_graph_service import (
    CHAPTER_COLUMN_MAP,
    COLUMN_X_BASE,
    COLUMN_X_GAP,
    NODE_POSITION_PRESETS,
    KnowledgeGraphService,
    knowledge_graph_service,
)

__all__ = [
    "CHAPTER_COLUMN_MAP",
    "COLUMN_X_BASE",
    "COLUMN_X_GAP",
    "NODE_POSITION_PRESETS",
    "KnowledgeGraphService",
    "knowledge_graph_service",
]
