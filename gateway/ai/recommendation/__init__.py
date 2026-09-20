# -*- coding: utf-8 -*-
"""
gateway.ai.recommendation
=========================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B / Phase 2
AI 个性化推荐引擎领域模块包
"""

from gateway.ai.recommendation.models import (
    RECOMMENDATION_FORBIDDEN_FIELDS,
    CandidateValidationResult,
    KnowledgeStateSnapshot,
    RecommendationCandidate,
    RecommendationContext,
    RecommendationRequest,
    RecommendationResponse,
    RejectedCandidate,
    ResourceCandidateSnapshot,
    ValidatedRecommendation,
)
from gateway.ai.recommendation.context import (
    RecommendationContextBuilder,
    resolve_authoritative_focus_knowledge,
)
from gateway.ai.recommendation.prompt import (
    RECOMMENDATION_SYSTEM_PROMPT,
    build_recommendation_prompt,
)
from gateway.ai.recommendation.generator import DeepSeekCandidateGenerator
from gateway.ai.recommendation.validator import (
    RecommendationValidator,
    ValidationRejectedError,
)
from gateway.ai.recommendation.service import (
    RecommendationService,
    default_recommendation_service,
)

__all__ = [
    "RECOMMENDATION_FORBIDDEN_FIELDS",
    "CandidateValidationResult",
    "KnowledgeStateSnapshot",
    "RecommendationCandidate",
    "RecommendationContext",
    "RecommendationRequest",
    "RecommendationResponse",
    "RejectedCandidate",
    "ResourceCandidateSnapshot",
    "ValidatedRecommendation",
    "RecommendationContextBuilder",
    "resolve_authoritative_focus_knowledge",
    "RECOMMENDATION_SYSTEM_PROMPT",
    "build_recommendation_prompt",
    "DeepSeekCandidateGenerator",
    "RecommendationValidator",
    "ValidationRejectedError",
    "RecommendationService",
    "default_recommendation_service",
]
