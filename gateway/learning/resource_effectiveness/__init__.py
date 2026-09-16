# -*- coding: utf-8 -*-
"""
gateway.learning.resource_effectiveness
=======================================
学海智导 (Xuehai Zhidao) — Phase 5 / Sprint 9-E
资源学习效果档案与自适应微调策略模块
"""

from gateway.learning.resource_effectiveness.models import (
    ADJUSTMENT_SCORES,
    EffectivenessProfileResponse,
    HistoricalEffectiveness,
    ResourceEffectivenessProfile,
    classify_effectiveness,
)
from gateway.learning.resource_effectiveness.aggregator import (
    ResourceEffectivenessAggregator,
    default_resource_effectiveness_aggregator,
)
from gateway.learning.resource_effectiveness.strategy import (
    DeterministicAdaptationStrategy,
    WHY_RECOMMENDED_TEMPLATES,
    default_adaptation_strategy,
)

__all__ = [
    "HistoricalEffectiveness",
    "ADJUSTMENT_SCORES",
    "ResourceEffectivenessProfile",
    "EffectivenessProfileResponse",
    "classify_effectiveness",
    "ResourceEffectivenessAggregator",
    "default_resource_effectiveness_aggregator",
    "DeterministicAdaptationStrategy",
    "WHY_RECOMMENDED_TEMPLATES",
    "default_adaptation_strategy",
]
