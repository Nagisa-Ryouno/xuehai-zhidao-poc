# -*- coding: utf-8 -*-
"""
app.api.schemas
表现层统一 DTO 模型包 (Data Transfer Objects)
"""

from app.api.schemas.assistant import (
    AssistantChatResponse,
    AssistantGreetingResponse,
    AssistantMessageRequest,
    AssistantRelatedKnowledge,
)
from app.api.schemas.common import MessageResponse, StatusResponse
from app.api.schemas.event import (
    EventSubmissionResponse,
    LearningEventType,
    LearningEvent,
    LearningEventCreate,
    StoredEvent,
)
from app.api.schemas.knowledge_graph import (
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    KnowledgeGraphResponse,
)
from app.api.schemas.learning_state import (
    BKTStateResponse,
    LearningStateUpdateRequest,
    LearningStateUpdateResponse,
)
from app.api.schemas.path import (
    AllLearningPathsResponse,
    StudentPathStatesResponse,
)
from app.api.schemas.quiz import (
    LearningStateSnapshot,
    QuizKnowledgeListResponse,
    QuizOption,
    QuizQuestionInternal,
    QuizQuestionPublic,
    QuizSubmitRequest,
    QuizSubmitResponse,
    get_mastery_state,
)
from app.api.schemas.student import (
    AllReportsResponse,
    StudentDashboardResponse,
    StudentListItem,
    StudentListResponse,
)
from app.api.schemas.system import (
    OverviewStudentSummary,
    SystemHealthResponse,
    SystemOverviewResponse,
    SystemRootResponse,
)

__all__ = [
    "MessageResponse",
    "StatusResponse",
    "SystemRootResponse",
    "SystemHealthResponse",
    "OverviewStudentSummary",
    "SystemOverviewResponse",
    "StudentListItem",
    "StudentListResponse",
    "StudentDashboardResponse",
    "AllReportsResponse",
    "StudentPathStatesResponse",
    "AllLearningPathsResponse",
    "KnowledgeGraphNode",
    "KnowledgeGraphEdge",
    "KnowledgeGraphResponse",
    "AssistantMessageRequest",
    "AssistantRelatedKnowledge",
    "AssistantChatResponse",
    "AssistantGreetingResponse",
    "LearningEventType",
    "LearningEventCreate",
    "LearningEvent",
    "StoredEvent",
    "EventSubmissionResponse",
    "QuizOption",
    "QuizQuestionPublic",
    "QuizQuestionInternal",
    "QuizKnowledgeListResponse",
    "QuizSubmitRequest",
    "LearningStateSnapshot",
    "QuizSubmitResponse",
    "get_mastery_state",
    "BKTStateResponse",
    "LearningStateUpdateRequest",
    "LearningStateUpdateResponse",
]
