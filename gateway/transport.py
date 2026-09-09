# -*- coding: utf-8 -*-
"""
gateway.transport
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage E: External LLM Transport 抽象与离线隔离防线

设计目标：
1. 网络传输抽象：将底层 HTTP/API 网络调用与 Provider 业务逻辑完全解耦
2. 零网络保证 (Zero Network Guarantee)：默认装配 DisabledNetworkTransport，严禁真实外网请求
3. 离线测试支持：提供 FakeLLMTransport，支持在 100% 离线环境下测试成功、超时、4xx、5xx 与越权场景
4. 密钥与异常隔离：底层网络异常或错误信息严禁包含真实 API Key 或敏感凭证
"""

import asyncio
from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Literal, Optional

from gateway.models import StructuredAIResponse

logger = logging.getLogger("xuehai.gateway.transport")


class LLMTransport(ABC):
    """外部大模型网络传输层抽象基类"""

    @abstractmethod
    async def send_payload(
        self,
        request_payload: Dict[str, Any],
        timeout_ms: int,
    ) -> Dict[str, Any]:
        """
        向大模型服务端点发送结构化提示词载荷
        
        @param request_payload 组装好的提示词与参数载荷字典
        @param timeout_ms 超时毫秒限制
        @return 解析后的原始模型响应字典
        """
        pass


class DisabledNetworkTransport(LLMTransport):
    """
    Stage E 默认网络传输实现 (强制禁用真实网络)
    
    红线保证：
    任何意外尝试访问外部互联网的行为都会被直接阻断，抛出受控的 ProviderException。
    """

    async def send_payload(
        self,
        request_payload: Dict[str, Any],
        timeout_ms: int,
    ) -> Dict[str, Any]:
        logger.warning(
            "Attempted external network call while DisabledNetworkTransport is active in Stage E"
        )
        from gateway.adapter import ProviderException

        raise ProviderException(
            "Real network calls are disabled in Stage E: External LLM transport is ready but offline."
        )


class FakeLLMTransport(LLMTransport):
    """
    用于 Stage E 自动化契约测试的 Fake 传输层实现
    
    100% 运行于离线内存环境，支持精确模拟各种网络与模型输出场景。
    """

    def __init__(
        self,
        mode: Literal[
            "success",
            "timeout",
            "http_4xx",
            "http_5xx",
            "malformed",
            "forbidden_decision",
        ] = "success",
        custom_response_payload: Optional[Dict[str, Any]] = None,
        status_code: int = 200,
        delay_ms: int = 0,
    ):
        self.mode = mode
        self.custom_response_payload = custom_response_payload
        self.status_code = status_code
        self.delay_ms = delay_ms
        self.last_request_payload: Optional[Dict[str, Any]] = None

    async def send_payload(
        self,
        request_payload: Dict[str, Any],
        timeout_ms: int,
    ) -> Dict[str, Any]:
        self.last_request_payload = request_payload

        # 1. 模拟网络延迟
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000.0)

        # 2. 模拟超时异常
        if self.mode == "timeout":
            from gateway.adapter import ProviderTimeoutError

            raise ProviderTimeoutError(
                f"Fake transport simulated timeout after {timeout_ms}ms"
            )

        # 3. 模拟 HTTP 4xx 客户端异常 (如 401 Unauthorized / 429 RateLimit)
        if self.mode == "http_4xx":
            from gateway.adapter import ProviderException

            code = self.status_code if 400 <= self.status_code < 500 else 401
            raise ProviderException(
                f"Upstream external LLM provider returned client error (HTTP {code})"
            )

        # 4. 模拟 HTTP 5xx 服务端异常 (如 502 Bad Gateway / 500 Internal Error)
        if self.mode == "http_5xx":
            from gateway.adapter import ProviderException

            code = self.status_code if 500 <= self.status_code < 600 else 502
            raise ProviderException(
                f"Upstream external LLM provider returned server error (HTTP {code})"
            )

        # 5. 模拟返回畸形输出 (缺少必须字段或非期望结构)
        if self.mode == "malformed":
            if self.custom_response_payload is not None:
                return self.custom_response_payload
            return {"malformed_output": "missing_required_answer_and_facts"}

        # 6. 模拟模型输出尝试包含学习决策控制字段 (越权测试)
        if self.mode == "forbidden_decision":
            if self.custom_response_payload is not None:
                return self.custom_response_payload
            return {
                "answer": "我建议为你解锁下一个知识点。",
                "referenced_facts": ["current_knowledge_point=K08"],
                "decision": "FORCE_UNLOCK",
                "grounding_status": "grounded",
            }

        # 7. 正常成功输出 (Success)
        if self.custom_response_payload is not None:
            return self.custom_response_payload

        kid = request_payload.get("system_facts", {}).get("current_knowledge_id", "K08")
        return {
            "answer": "这是由外部模型抽象层在离线测试中生成的合规测试回答。",
            "referenced_facts": [f"current_knowledge_point={kid}"],
            "suggested_explanation": "根据当前客观学情继续巩固基础练习。",
            "grounding_status": "grounded",
        }
