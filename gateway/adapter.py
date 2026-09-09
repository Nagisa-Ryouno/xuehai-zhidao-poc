# -*- coding: utf-8 -*-
"""
gateway.adapter
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage B: Backend AI Provider Adapter 抽象层与密钥隔离边界

设计原则：
1. 依赖倒置：网关上层依赖抽象 AIProviderAdapter，而非具体模型实现
2. 输入边界：Provider 只能接收 LearningPromptContext，严格只读，禁止修改
3. 输出边界：Provider 只能输出 StructuredAIResponse，绝对禁止任何学习决策控制字段
4. 超时与容灾：内置 5000ms 超时契约与异常隔离熔断
5. 密钥隔离：服务端专用，禁止透传或暴露 API 密钥
"""

import asyncio
from abc import ABC, abstractmethod
import logging
from typing import Literal, Optional

from gateway.config import gateway_settings
from gateway.models import (
    LearningPromptContext,
    StructuredAIResponse,
)

logger = logging.getLogger("xuehai.gateway.adapter")


class ProviderException(Exception):
    """Provider 基础调用异常"""
    pass


class ProviderTimeoutError(ProviderException):
    """Provider 超时异常"""
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


class FutureExternalLLMProvider(AIProviderAdapter):
    """
    未来外部真实大模型服务商骨架 (OpenAI / DeepSeek / 通义千问等)
    
    架构红线：
    - 密钥仅从服务端读取 (gateway_settings.api_key)
    - 绝不向客户端暴露真实连接细节与密钥
    - Stage B 暂不发起真实网络请求，保持接口隔离
    """

    def __init__(
        self,
        name: str = "external-llm-provider",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._name = name
        self.api_key = api_key or gateway_settings.api_key
        self.model = model or gateway_settings.model

    @property
    def provider_name(self) -> str:
        return self._name

    async def generate(
        self,
        prompt_context: LearningPromptContext,
    ) -> StructuredAIResponse:
        # 未接入外部真实网络时安全降级，防止任何意外真实网络调用
        raise NotImplementedError(
            f"External provider '{self._name}' skeleton interface. "
            "Real network calls are disabled in Stage B."
        )


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
    elif selected_type in ("external", "openai", "deepseek"):
        return FutureExternalLLMProvider(name=selected_type)
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
