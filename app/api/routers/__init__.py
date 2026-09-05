# -*- coding: utf-8 -*-
"""
app.api.routers
API 表现层领域路由包
"""

from app.api.routers import (
    assistant,
    events,
    knowledge_graph,
    learning_state,
    path,
    quiz,
    students,
    system,
)

__all__ = [
    "system",
    "students",
    "path",
    "knowledge_graph",
    "assistant",
    "events",
    "quiz",
    "learning_state",
]
