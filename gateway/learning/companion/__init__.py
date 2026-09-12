# -*- coding: utf-8 -*-
"""
gateway.learning.companion
==========================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-A
AI 学习伙伴与智能辅学体验模块 (AI Learning Companion)
"""

from gateway.learning.companion.models import (
    CompanionChatMessage,
    CompanionContextMetadata,
    CompanionMode,
    CompanionSafetyMetadata,
    CompanionSession,
    CompanionStudyRequest,
    CompanionStudyResponse,
)
from gateway.learning.companion.context import (
    CompanionContextBuilder,
    default_companion_context_builder,
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
    "CompanionMode",
    "CompanionSafetyMetadata",
    "CompanionContextMetadata",
    "CompanionStudyRequest",
    "CompanionStudyResponse",
    "CompanionChatMessage",
    "CompanionSession",
    "CompanionContextBuilder",
    "default_companion_context_builder",
    "CompanionService",
    "default_companion_service",
    "build_system_prompt",
    "is_potential_injection",
]
