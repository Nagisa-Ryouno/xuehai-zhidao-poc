# -*- coding: utf-8 -*-
"""
gateway.ai.models
=================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B
通用 AI Provider 请求、响应与故障分类契约模型
"""

from enum import Enum
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class ProviderErrorCategory(str, Enum):
    """Provider 统一故障分级分类（供网关遥测与容灾路由仲裁）"""
    PROVIDER_DISABLED = "PROVIDER_DISABLED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PROVIDER_INVALID_RESPONSE = "PROVIDER_INVALID_RESPONSE"
    PROVIDER_CONFIGURATION_ERROR = "PROVIDER_CONFIGURATION_ERROR"
    MOCK_RESPONSE = "MOCK_RESPONSE"


class AIProviderRequest(BaseModel):
    """
    通用统一 Provider 提示词请求载荷契约
    
    设计原则：
    1. 严格白名单：extra='forbid' 拦截非预期参数
    2. PII 保护：user_id 仅限伪匿名标识符 (如内部 student_id)，严禁明文隐私数据
    3. 提示词分界：明确分立 system_prompt 与 user_prompt，防御 Prompt Injection
    """
    model_config = ConfigDict(extra="forbid")

    system_prompt: str = Field(..., description="系统指令（定义角色与决策权边界）")
    user_prompt: str = Field(..., description="用户内容（不可信用户输入与上下文事实）")
    response_format: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None,
        description="输出格式规范 (如 'json_object' 或 {'type': 'json_object'})",
    )
    max_tokens: int = Field(default=2048, ge=1, le=8192, description="最大生成 token 预算")
    temperature: Optional[float] = Field(default=0.0, ge=0.0, le=2.0, description="采样温度")
    user_id: Optional[str] = Field(
        default=None,
        description="不可逆伪匿名学生标识符，严禁包含真实邮箱、手机号等 PII",
    )
    model: Optional[str] = Field(default=None, description="可选覆盖模型名称")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="只读元数据上下文")


class AIProviderResponse(BaseModel):
    """
    通用统一 Provider 模型响应模型
    """
    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., description="模型生成的文本或原始 JSON 字符串")
    model: str = Field(..., description="实际响应的模型名称")
    provider: str = Field(default="deepseek", description="模型提供商标识")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="Token 消耗统计元数据")
    finish_reason: Optional[str] = Field(default="stop", description="模型生成结束原因")
    parsed_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="结构化 JSON 输出解析结果（若为 json_object 模式）",
    )
