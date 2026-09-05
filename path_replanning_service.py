# -*- coding: utf-8 -*-
"""
path_replanning_service.py
学海智导 V2 - Path Replanning Decision Core (Backward-compatible Facade)

向后兼容门面，内部委托给 app.services.path_replanning_service。
"""

from app.services.path_replanning_service import (
    AuditMetadata,
    CanonicalBusinessPayload,
    DecisionAuditEnvelope,
    LEGAL_DECISION_PAIRS,
    PathAction,
    PathState,
    ReplanningReasonCode,
    can_unlock_successor,
    evaluate_and_replan,
    evaluate_decision_core,
    format_canonical_mastery,
    get_prerequisites,
    get_successors,
    is_knowledge_mastered,
    validate_decision_pair,
)

__all__ = [
    "PathAction",
    "ReplanningReasonCode",
    "LEGAL_DECISION_PAIRS",
    "validate_decision_pair",
    "format_canonical_mastery",
    "CanonicalBusinessPayload",
    "AuditMetadata",
    "DecisionAuditEnvelope",
    "PathState",
    "evaluate_decision_core",
    "evaluate_and_replan",
    "get_prerequisites",
    "get_successors",
    "is_knowledge_mastered",
    "can_unlock_successor",
]
