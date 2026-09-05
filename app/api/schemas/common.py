# -*- coding: utf-8 -*-
"""
app.api.schemas.common
通用基础响应与错误模式定义
"""

from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str = Field(..., description="响应提示信息")


class StatusResponse(BaseModel):
    """通用状态响应"""
    status: str = Field(..., description="执行状态 (ok / success / error)")
    message: Optional[str] = Field(default=None, description="详细说明")
