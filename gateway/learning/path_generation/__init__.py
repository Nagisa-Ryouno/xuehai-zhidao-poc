# -*- coding: utf-8 -*-
"""
gateway/learning/path_generation package
"""

from gateway.learning.path_generation.models import DynamicLearningRoute, RouteStep
from gateway.learning.path_generation.scoring import (
    WEIGHT_DIAGNOSTIC_PRIORITY,
    WEIGHT_PATH_AVAILABILITY,
    WEIGHT_PREREQUISITE_READINESS,
    WEIGHT_TARGET_RELEVANCE,
    WEIGHT_WEAKNESS,
    calculate_node_priority,
)
from gateway.learning.path_generation.generator import (
    DynamicPathGenerator,
    default_dynamic_path_generator,
    identify_target_knowledge_ids,
    get_target_ancestor_ids,
)

__all__ = [
    "RouteStep",
    "DynamicLearningRoute",
    "calculate_node_priority",
    "WEIGHT_WEAKNESS",
    "WEIGHT_TARGET_RELEVANCE",
    "WEIGHT_PREREQUISITE_READINESS",
    "WEIGHT_PATH_AVAILABILITY",
    "WEIGHT_DIAGNOSTIC_PRIORITY",
    "DynamicPathGenerator",
    "default_dynamic_path_generator",
    "identify_target_knowledge_ids",
    "get_target_ancestor_ids",
]
