# -*- coding: utf-8 -*-
"""
gateway.ai
==========
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B
AI Gateway 外部 Provider 基础设施与 DeepSeek 接入层
"""

from gateway.ai.models import (
    AIProviderRequest,
    AIProviderResponse,
    ProviderErrorCategory,
)
from gateway.ai.deepseek import (
    AIProviderError,
    AuthenticationError,
    DeepSeekProvider,
    MockAIProvider,
    MockDeepSeekProvider,
    PIIViolationError,
    ProviderDisabledError,
    ProviderInvalidResponseError,
    ProviderTimeout,
    ProviderUnavailableError,
    RateLimitError,
    assert_no_pii,
)

__all__ = [
    "AIProviderRequest",
    "AIProviderResponse",
    "ProviderErrorCategory",
    "AIProviderError",
    "AuthenticationError",
    "RateLimitError",
    "ProviderUnavailableError",
    "ProviderTimeout",
    "ProviderInvalidResponseError",
    "ProviderDisabledError",
    "PIIViolationError",
    "DeepSeekProvider",
    "MockDeepSeekProvider",
    "MockAIProvider",
    "assert_no_pii",
]
