# -*- coding: utf-8 -*-
"""
gateway.learning.companion
==========================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-A & 9-B
AI 学习伙伴与智能引导闭环模块 (AI Learning Companion & Guided Learning)
"""

from gateway.learning.companion.models import (
    ActionType,
    CompanionChatMessage,
    CompanionContextMetadata,
    CompanionMode,
    CompanionSafetyMetadata,
    CompanionSession,
    CompanionStudyRequest,
    CompanionStudyResponse,
    CompanionSuggestedAction,
    LearningActionResultRequest,
    LearningActionResultResponse,
    QuickCheckOption,
    QuickCheckQuestion,
    QuickCheckSubmitRequest,
    QuickCheckResponse,
)
from gateway.learning.companion.context import (
    CompanionContextBuilder,
    default_companion_context_builder,
)
from gateway.learning.companion.guided_actions import (
    DeterministicActionBuilder,
    VALID_ACTION_TYPES,
)
from gateway.learning.companion.quick_check import (
    QuickCheckService,
    default_quick_check_service,
)
from gateway.learning.companion.reflection import (
    ActionReflectionService,
    default_action_reflection_service,
)
from gateway.learning.companion.events import (
    record_companion_event,
    get_all_student_companion_events,
)
from gateway.learning.companion.prompt import (
    build_system_prompt,
    is_potential_injection,
)
from gateway.learning.companion.service import (
    CompanionService,
    default_companion_service,
)

__all__ = [
    "ActionType",
    "CompanionMode",
    "CompanionSafetyMetadata",
    "CompanionContextMetadata",
    "CompanionStudyRequest",
    "CompanionStudyResponse",
    "CompanionSuggestedAction",
    "QuickCheckOption",
    "QuickCheckQuestion",
    "QuickCheckSubmitRequest",
    "QuickCheckResponse",
    "LearningActionResultRequest",
    "LearningActionResultResponse",
    "CompanionChatMessage",
    "CompanionSession",
    "CompanionContextBuilder",
    "default_companion_context_builder",
    "DeterministicActionBuilder",
    "QuickCheckService",
    "default_quick_check_service",
    "ActionReflectionService",
    "default_action_reflection_service",
    "record_companion_event",
    "get_all_student_companion_events",
    "CompanionService",
    "default_companion_service",
    "build_system_prompt",
    "is_potential_injection",
]
