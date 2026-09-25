# -*- coding: utf-8 -*-
"""
gateway.adapter
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage E: Backend AI Provider Adapter 抽象层与 External LLM Readiness

设计原则：
1. 依赖倒置：网关上层依赖抽象 AIProviderAdapter，而非具体模型实现
2. 输入边界：Provider 只能接收 LearningPromptContext，严格只读，禁止修改
3. 输出边界：Provider 只能输出 StructuredAIResponse，绝对禁止任何学习决策控制字段
4. 超时与容灾：内置 5000ms 超时契约与异常隔离熔断
5. 密钥隔离：服务端专用，禁止透传或暴露 API 密钥
6. 离线隔离：ExternalLLMProvider 默认装配 DisabledNetworkTransport，严禁真实联网调用
"""

import asyncio
from abc import ABC, abstractmethod
import json
import logging
from typing import Literal, Optional, Set

from gateway.config import gateway_settings
from gateway.models import (
    LearningPromptContext,
    StructuredAIResponse,
)
from gateway.prompt import build_external_prompt
from gateway.transport import DisabledNetworkTransport, HttpLLMTransport, LLMTransport

logger = logging.getLogger("xuehai.gateway.adapter")

_USE_CONFIGURED_API_KEY = object()

FORBIDDEN_DECISION_FIELDS: Set[str] = {
    "decision",
    "unlock_nodes",
    "state_transition",
    "mutate_path",
    "modify_mastery",
    "set_mastery",
    "next_state",
    "learning_path_update",
    "next_action_command",
    "change_path",
    "path_mutation",
}


class ProviderException(Exception):
    """Provider 基础调用异常"""
    pass


class ProviderTimeoutError(ProviderException):
    """Provider 超时异常"""
    pass


class ProviderConfigurationError(ProviderException):
    """Provider 配置缺失或无效异常 (受控异常，不暴露密钥细节)"""
    pass


class AIProviderAdapter(ABC):
    """
    AI 服务商适配器抽象基类
    
    职责边界：
    - 纯文本组织、事实解释与辅导性说明
    - 严禁任何学习决策权 (BKT / PathState / Decision Core)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """获取当前提供商名称标识"""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt_context: LearningPromptContext,
    ) -> StructuredAIResponse:
        """
        根据只读白名单提示词上下文生成结构化响应
        
        @param prompt_context 只读的 LearningPromptContext
        @return StructuredAIResponse 结构化响应
        """
        pass


class MockGatewayProvider(AIProviderAdapter):
    """
    确定性 Mock AI 提供商实现
    
    特征：
    - 100% 确定性输出：相同输入产生相同输出
    - 零外部网络、零外部数据库、零 API Key 依赖
    - 零 Math.random()、零 Date.now()
    - 严禁修改传入的 prompt_context
    """

    def __init__(
        self,
        name: str = "mock-gateway-provider",
        mode: Literal["default", "error", "timeout"] = "default",
        delay_ms: int = 0,
        custom_response: Optional[StructuredAIResponse] = None,
    ):
        self._name = name
        self.mode = mode
        self.delay_ms = delay_ms
        self.custom_response = custom_response

    @property
    def provider_name(self) -> str:
        return self._name

    async def generate(
        self,
        prompt_context: LearningPromptContext,
    ) -> StructuredAIResponse:
        # 1. 模拟延迟或超时
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000.0)

        # 2. 模拟内部异常
        if self.mode == "error":
            raise ProviderException("Simulated upstream provider failure")

        # 3. 模拟长时间无响应超时
        if self.mode == "timeout":
            await asyncio.sleep(10.0)

        # 4. 自定义响应支持
        if self.custom_response:
            return self.custom_response

        # 5. 基于系统事实生成确定性结构化回答（严格解释事实，不修改系统状态）
        sf = prompt_context.system_facts
        question = prompt_context.user_question

        referenced_facts = [
            f"current_knowledge_point={sf.current_knowledge_id}:{sf.current_knowledge_name}",
            f"current_mastery_percent={sf.current_mastery_percent:.1f}%",
            f"mastery_target_percent={sf.mastery_target_percent:.1f}%",
            f"path_state={sf.current_path_state}",
            f"next_action={sf.next_action.label}",
        ]

        answer = (
            f"同学你好！你当前正在学习【{sf.current_chapter}】中的【{sf.current_knowledge_name}】"
            f"（编号 {sf.current_knowledge_id}）。当前掌握度为 {sf.current_mastery_percent:.1f}%，"
            f"距离达标目标 {sf.mastery_target_percent:.1f}% 还差 {sf.mastery_gap_percent:.1f}%。"
            f"当前路径状态为 {sf.current_path_state}。"
            f"针对你的提问「{question}」，根据系统诊断事实，建议你下一步：{sf.next_action.label}"
            f"（{sf.next_action.reason}）。继续加油！"
        )

        suggested_explanation = (
            f"知识点 {sf.current_knowledge_id} 当前路径状态为 {sf.current_path_state}，"
            f"建议行动为 {sf.next_action.label}。"
        )

        return StructuredAIResponse(
            answer=answer,
            referenced_facts=referenced_facts,
            suggested_explanation=suggested_explanation,
            grounding_status="grounded",
        )


class ExternalLLMProvider(AIProviderAdapter):
    """
    外部真实大模型服务商抽象适配器 (Stage E: Ready but Offline)
    
    架构红线与工作流：
    1. 严格检查 Provider 配置（未配置 API Key 时抛出受控 ProviderConfigurationError）
    2. 调用 build_external_prompt 组装纯净的提示词载荷
    3. 委托底层 transport.send_payload 发送（默认使用 DisabledNetworkTransport 杜绝外网请求）
    4. 严密执行越权学习决策字段扫描（FORBIDDEN_DECISION_FIELDS 命中立即阻断）
    5. 最终规范化校验为强类型 StructuredAIResponse
    """

    def __init__(
        self,
        name: str = "external-llm-provider",
        api_key: object = _USE_CONFIGURED_API_KEY,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        transport: Optional[LLMTransport] = None,
    ):
        self._name = name
        self.api_key = (
            gateway_settings.api_key
            if api_key is _USE_CONFIGURED_API_KEY
            else api_key
        )
        self.base_url = base_url or gateway_settings.base_url
        self.model = model or gateway_settings.model
        if transport is not None:
            self.transport = transport
        elif self.base_url and self.api_key:
            self.transport = HttpLLMTransport(
                base_url=self.base_url,
                api_key=self.api_key,
                model=self.model,
                timeout_ms=gateway_settings.timeout_ms,
            )
        else:
            self.transport = DisabledNetworkTransport()

    @property
    def provider_name(self) -> str:
        return self._name

    async def generate(
        self,
        prompt_context: LearningPromptContext,
    ) -> StructuredAIResponse:
        # 1. 严格配置校验 (Configuration Validation)
        # 缺少有效 API Key 时受控抛出配置异常，杜绝敏感词汇泄露
        if not self.api_key or not self.api_key.strip():
            raise ProviderConfigurationError(
                "External AI provider is not configured: missing API key"
            )

        # 2. 组装只读外部提示词载荷
        prompt_payload = build_external_prompt(
            prompt_context,
            model=self.model or gateway_settings.model,
        )

        request_dict = {
            "model": prompt_payload.model,
            "system_prompt": prompt_payload.system_prompt,
            "user_prompt": prompt_payload.user_prompt,
            "system_facts": prompt_context.system_facts.model_dump(),
            "response_format": prompt_payload.response_format,
            "temperature": prompt_payload.temperature,
        }

        # 3. 通过 Transport 抽象层发送（Stage E 默认 DisabledNetworkTransport，离线测试注入 FakeLLMTransport）
        raw_response = await self.transport.send_payload(
            request_dict,
            timeout_ms=gateway_settings.timeout_ms,
        )

        # 4. 原始响应类型与格式防御
        if not isinstance(raw_response, dict):
            raise ProviderException(
                "Invalid response from external LLM transport: expected JSON object"
            )

        # DeepSeek 等 OpenAI-compatible API 会把 JSON 文本包在
        # choices[0].message.content 中；测试传输则可直接返回内部对象。
        if "choices" in raw_response and "answer" not in raw_response:
            try:
                content = raw_response["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise TypeError("message content is not text")
                clean_content = content.strip()
                if clean_content.startswith("```"):
                    lines = clean_content.splitlines()
                    if lines and lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    clean_content = "\n".join(lines).strip()
                raw_response = json.loads(clean_content)
            except (KeyError, IndexError, TypeError, json.JSONDecodeError):
                raise ProviderException(
                    "Invalid structured content returned by external LLM"
                ) from None

        # 5. 越权学习决策字段防御扫描 (Forbidden Decision Field Detection)
        for forbidden_key in FORBIDDEN_DECISION_FIELDS:
            if forbidden_key in raw_response:
                raise ProviderException(
                    f"External LLM returned forbidden decision field: {forbidden_key}"
                )

        # 6. StructuredAIResponse 契约规范化与校验
        if "answer" not in raw_response or not isinstance(raw_response["answer"], str):
            raise ProviderException(
                "Invalid StructuredAIResponse from external LLM: missing required 'answer' string"
            )

        if "referenced_facts" not in raw_response or not isinstance(
            raw_response["referenced_facts"], list
        ):
            raise ProviderException(
                "Invalid StructuredAIResponse from external LLM: missing required 'referenced_facts' list"
            )

        grounding_status = raw_response.get("grounding_status", "grounded")
        if grounding_status not in ("grounded", "insufficient_context"):
            grounding_status = "grounded"

        suggested_explanation = raw_response.get("suggested_explanation")
        if suggested_explanation is not None and not isinstance(suggested_explanation, str):
            suggested_explanation = str(suggested_explanation)

        return StructuredAIResponse(
            answer=raw_response["answer"],
            referenced_facts=[str(f) for f in raw_response["referenced_facts"]],
            suggested_explanation=suggested_explanation,
            grounding_status=grounding_status,
        )


# 向后兼容别名，保障已有测试平稳运行
FutureExternalLLMProvider = ExternalLLMProvider


# ============================================================
# 超时执行保护与 Provider 注册工厂
# ============================================================

_active_provider: Optional[AIProviderAdapter] = None


def get_provider(provider_type: Optional[str] = None) -> AIProviderAdapter:
    """获取当前激活的 Provider 实例 (依赖注入工厂)"""
    global _active_provider
    if _active_provider is not None and provider_type is None:
        return _active_provider

    selected_type = (provider_type or gateway_settings.provider).strip().lower()

    if selected_type in ("mock", "default"):
        return MockGatewayProvider()
    elif selected_type in ("deepseek", "deepseek-flash", "deepseek-v4-pro"):
        from gateway.ai.deepseek import DeepSeekProvider
        return DeepSeekProvider(name="deepseek")
    elif selected_type in ("external", "openai"):
        return ExternalLLMProvider(name=selected_type)
    else:
        logger.warning(f"Unknown provider '{selected_type}', falling back to MockGatewayProvider")
        return MockGatewayProvider()


def set_provider(provider: Optional[AIProviderAdapter]) -> None:
    """设置或覆盖当前激活的 Provider 实例 (用于测试与依赖注入)"""
    global _active_provider
    _active_provider = provider


async def execute_provider_with_timeout(
    provider: AIProviderAdapter,
    prompt_context: LearningPromptContext,
    timeout_ms: Optional[int] = None,
) -> StructuredAIResponse:
    """
    在安全超时保护与异常捕获容器内执行 Provider.generate()
    """
    timeout_limit = (timeout_ms if timeout_ms is not None else gateway_settings.timeout_ms) / 1000.0

    try:
        return await asyncio.wait_for(
            provider.generate(prompt_context),
            timeout=timeout_limit,
        )
    except asyncio.TimeoutError:
        logger.error(f"Provider {provider.provider_name} timed out after {timeout_limit}s")
        raise ProviderTimeoutError(f"Provider timed out after {timeout_limit}s")
    except ProviderException:
        raise
    except Exception as e:
        logger.error(f"Provider {provider.provider_name} raised unexpected error: {type(e).__name__}")
        raise ProviderException(f"Provider error: {type(e).__name__}") from None
