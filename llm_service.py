# -*- coding: utf-8 -*-
"""
llm_service.py
学海智导 (Xuehai Zhidao) - LLM 统一服务商抽象与调用层 (Backward-compatible Facade)

向后兼容门面，内部委托给 app.infrastructure.external.llm_client。
"""

from app.infrastructure.external.llm_client import (
    LLMClient,
    LLMService,
    llm_client,
)

llm_service = llm_client

__all__ = [
    "LLMClient",
    "LLMService",
    "llm_service",
]
