# -*- coding: utf-8 -*-
"""
assistant_service.py
学海智导 (Xuehai Zhidao) - AI 学习助手核心服务模块 (Backward-compatible Facade)

向后兼容门面，内部委托给 app.services.assistant_service。
"""

from app.services.assistant_service import (
    AssistantService,
    assistant_service,
    build_student_context,
    build_system_prompt,
    detect_intent,
    find_mentioned_knowledge,
    generate_assistant_response,
    generate_rule_based_response,
    get_assistant_greeting,
    get_student_context,
    validate_and_sanitize_response,
)

__all__ = [
    "build_student_context",
    "get_student_context",
    "build_system_prompt",
    "validate_and_sanitize_response",
    "find_mentioned_knowledge",
    "detect_intent",
    "generate_rule_based_response",
    "generate_assistant_response",
    "get_assistant_greeting",
    "AssistantService",
    "assistant_service",
]
