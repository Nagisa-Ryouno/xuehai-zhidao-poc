# -*- coding: utf-8 -*-
"""
gateway.ai.deepseek
===================
学海智导 (Xuehai Zhidao) — Phase 6 / Sprint 10-B
DeepSeek 官方 OpenAI-compatible 大模型 Provider 实现与安全防护层

核心原则：
1. 权限边界隔离：AI 永远是教学与分析辅助者，绝对零学习决策权 (allow_production_decision=False)
2. 离线默认安全：DEEPSEEK_ENABLED=false 时杜绝任何外网 HTTP 连接
3. 凭证脱敏绝密：全生命周期不记录明文 API Key，日志与异常信息严格过滤
4. 故障分级分类：精确映射 401(AUTHENTICATION_ERROR)、429(RATE_LIMITED)、5xx(PROVIDER_UNAVAILABLE)、超时(PROVIDER_TIMEOUT)、格式错误(PROVIDER_INVALID_RESPONSE)
5. 绝无虚假伪造：DeepSeek 失败时绝不自动降级成伪造的假成功数据
6. 隐私最小化：严禁在向外部大模型发起的请求中包含真实姓名、手机号、身份证或邮箱
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

from gateway.adapter import (
    AIProviderAdapter,
    FORBIDDEN_DECISION_FIELDS,
    ProviderConfigurationError,
    ProviderException,
    ProviderTimeoutError,
)
from gateway.ai.models import (
    AIProviderRequest,
    AIProviderResponse,
    ProviderErrorCategory,
)
from gateway.config import gateway_settings
from gateway.models import LearningPromptContext, StructuredAIResponse
from gateway.prompt import build_external_prompt
from gateway.redaction import redact_sensitive_string
from gateway.transport import (
    DisabledNetworkTransport,
    HttpLLMTransport,
    LLMTransport,
)

logger = logging.getLogger("xuehai.ai.deepseek")

# PII 敏感信息正则表达式
_PHONE_PATTERN = re.compile(r"(?:\+?86)?1[3-9]\d{9}")
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_ID_CARD_PATTERN = re.compile(r"\b\d{17}[\dXx]\b")


# ==============================================================================
# 异常类型继承树 (继承自已有 ProviderException 确保向后完全兼容)
# ==============================================================================

class AIProviderError(ProviderException):
    """DeepSeek Provider 基础异常类，携带标准化故障分类"""

    def __init__(
        self,
        message: str,
        category: ProviderErrorCategory,
        status_code: Optional[int] = None,
        raw_error: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.status_code = status_code
        self.raw_error = raw_error

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(category={self.category.value}, status_code={self.status_code}, message={self.message})"


class AuthenticationError(AIProviderError):
    """HTTP 401/403 鉴权失败异常"""

    def __init__(
        self,
        message: str = "DeepSeek API authentication failed: invalid or expired API key",
        status_code: int = 401,
    ):
        super().__init__(message, ProviderErrorCategory.AUTHENTICATION_ERROR, status_code=status_code)


class RateLimitError(AIProviderError):
    """HTTP 429 频控限制异常"""

    def __init__(
        self,
        message: str = "DeepSeek API rate limit reached: too many requests (HTTP 429)",
        status_code: int = 429,
    ):
        super().__init__(message, ProviderErrorCategory.RATE_LIMITED, status_code=status_code)


class ProviderUnavailableError(AIProviderError):
    """HTTP 5xx 或网络阻断服务端不可用异常"""

    def __init__(
        self,
        message: str = "DeepSeek API upstream service unavailable (HTTP 5xx)",
        status_code: int = 502,
    ):
        super().__init__(message, ProviderErrorCategory.PROVIDER_UNAVAILABLE, status_code=status_code)


class ProviderTimeout(AIProviderError, ProviderTimeoutError):
    """调用超时异常（多重继承，完全兼容已有 except ProviderTimeoutError）"""

    def __init__(
        self,
        message: str = "DeepSeek API request timed out",
        timeout_seconds: float = 20.0,
    ):
        super().__init__(message, ProviderErrorCategory.PROVIDER_TIMEOUT, status_code=408)
        self.timeout_seconds = timeout_seconds


class ProviderInvalidResponseError(AIProviderError):
    """上游返回畸形、空内容或非合法 JSON 异常"""

    def __init__(
        self,
        message: str = "DeepSeek API returned invalid or malformed response",
    ):
        super().__init__(message, ProviderErrorCategory.PROVIDER_INVALID_RESPONSE, status_code=502)


class ProviderDisabledError(AIProviderError, ProviderConfigurationError):
    """服务商未开启受控异常（多重继承，完全兼容已有 except ProviderConfigurationError）"""

    def __init__(
        self,
        message: str = "DeepSeek provider is disabled in configuration (DEEPSEEK_ENABLED=false)",
    ):
        super().__init__(message, ProviderErrorCategory.PROVIDER_DISABLED, status_code=503)


class PIIViolationError(AIProviderError):
    """检测到学生个人敏感隐私数据越界异常"""

    def __init__(
        self,
        message: str = "PII detected in request payload: sending sensitive user data to external LLM is forbidden",
    ):
        super().__init__(message, ProviderErrorCategory.PROVIDER_INVALID_RESPONSE, status_code=400)


# ==============================================================================
# PII 检测防护纯函数
# ==============================================================================

def assert_no_pii(text: Optional[str], context_name: str = "prompt") -> None:
    """
    深度扫描文本中是否包含个人隐私敏感信息 (手机号、邮箱、身份证)
    一旦命中直接抛出受控 PIIViolationError，阻断外泄风险
    """
    if not text or not isinstance(text, str):
        return

    if _PHONE_PATTERN.search(text):
        logger.warning(f"PII detection triggered in {context_name}: phone number matched")
        raise PIIViolationError(f"PII detected in {context_name}: mobile phone numbers are strictly forbidden")

    if _EMAIL_PATTERN.search(text):
        logger.warning(f"PII detection triggered in {context_name}: email address matched")
        raise PIIViolationError(f"PII detected in {context_name}: email addresses are strictly forbidden")

    if _ID_CARD_PATTERN.search(text):
        logger.warning(f"PII detection triggered in {context_name}: national ID matched")
        raise PIIViolationError(f"PII detected in {context_name}: national ID numbers are strictly forbidden")


# ==============================================================================
# DeepSeek 官方 Provider 实现
# ==============================================================================

class DeepSeekProvider(AIProviderAdapter):
    """
    DeepSeek 官方 OpenAI-compatible 大模型服务商实现
    
    接入规范：
    - base_url 默认 https://api.deepseek.com
    - 默认模型 deepseek-flash（支持 deepseek-v4-pro 等替换配置）
    - 默认离线关闭 (DEEPSEEK_ENABLED=false)
    - 严格只读辅助定位，绝对零学习决策权 (allow_production_decision = False)
    """

    def __init__(
        self,
        name: str = "deepseek",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        enabled: Optional[bool] = None,
        transport: Optional[LLMTransport] = None,
    ):
        self._name = name
        self.api_key = api_key if api_key is not None else gateway_settings.deepseek_api_key
        self.base_url = (
            base_url.rstrip("/") if base_url is not None else gateway_settings.deepseek_base_url.rstrip("/")
        )
        self.model = model if model is not None else gateway_settings.deepseek_model
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else gateway_settings.deepseek_timeout_seconds
        )
        self.enabled = enabled if enabled is not None else gateway_settings.deepseek_enabled

        # Transport 抽象装配：
        # 若未开启外部模型，强制使用 DisabledNetworkTransport 杜绝意外外部联网
        if transport is not None:
            self.transport: LLMTransport = transport
        elif not self.enabled:
            self.transport = DisabledNetworkTransport()
        else:
            self.transport = HttpLLMTransport(
                base_url=self.base_url,
                api_key=self.api_key,
                model=self.model,
                timeout_ms=self.timeout_seconds * 1000,
            )

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def is_configured(self) -> bool:
        """检查 API Key 是否已有效配置"""
        return bool(self.api_key and self.api_key.strip())

    def health_status(self) -> Dict[str, Any]:
        """返回当前 Provider 的静态健康与就绪元数据，绝不主动发网探活产生费用"""
        return {
            "provider": self.provider_name,
            "enabled": self.enabled,
            "configured": self.is_configured,
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "reachable": "unknown",  # 静态就绪声明，不主动网络探测
        }

    async def complete(self, request: AIProviderRequest) -> AIProviderResponse:
        """
        发送通用 AI 请求至 DeepSeek 官方兼容接口并解析返回结果
        """
        # 1. 离线开关防御
        if not self.enabled:
            raise ProviderDisabledError(
                "DeepSeek provider is disabled in configuration (DEEPSEEK_ENABLED=false)"
            )

        # 2. 密钥配置校验
        if not self.is_configured:
            raise AIProviderError(
                "DeepSeek API key is not configured (missing DEEPSEEK_API_KEY)",
                category=ProviderErrorCategory.PROVIDER_CONFIGURATION_ERROR,
            )

        # 3. PII 隐私越界检测
        assert_no_pii(request.system_prompt, context_name="system_prompt")
        assert_no_pii(request.user_prompt, context_name="user_prompt")
        assert_no_pii(request.user_id, context_name="user_id")

        # 4. 组装 DeepSeek OpenAI-compatible Payload
        system_content = request.system_prompt
        user_content = request.user_prompt

        # DeepSeek 官方要求：开启 JSON Mode 时 prompt 必须显式要求 JSON
        response_format_dict: Optional[Dict[str, Any]] = None
        if request.response_format:
            if isinstance(request.response_format, str) and request.response_format == "json_object":
                response_format_dict = {"type": "json_object"}
            elif isinstance(request.response_format, dict):
                response_format_dict = request.response_format

        if response_format_dict and response_format_dict.get("type") == "json_object":
            if "json" not in system_content.lower() and "json" not in user_content.lower():
                system_content = f"{system_content}\n\nIMPORTANT: You must respond in valid JSON format."

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        target_model = request.model or self.model
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": request.temperature if request.temperature is not None else 0.0,
            "max_tokens": request.max_tokens,
        }

        if response_format_dict:
            payload["response_format"] = response_format_dict

        if request.user_id:
            payload["user"] = request.user_id

        # 5. 通过 Transport 发送并捕获底层网络异常分类转换
        try:
            raw_response = await self.transport.send_payload(
                payload,
                timeout_ms=self.timeout_seconds * 1000,
            )
        except ProviderTimeoutError:
            raise ProviderTimeout(
                f"DeepSeek API request timed out after {self.timeout_seconds}s",
                timeout_seconds=self.timeout_seconds,
            )
        except ProviderException as pe:
            msg = str(pe)
            if "401" in msg or "authentication failed" in msg.lower():
                raise AuthenticationError(
                    "DeepSeek API authentication failed (HTTP 401)",
                    status_code=401,
                ) from None
            elif "429" in msg or "rate limit" in msg.lower():
                raise RateLimitError(
                    "DeepSeek API rate limit reached (HTTP 429)",
                    status_code=429,
                ) from None
            elif any(c in msg for c in ("500", "502", "503", "504", "server error")):
                raise ProviderUnavailableError(
                    f"DeepSeek API upstream service error: {redact_sensitive_string(msg)}",
                    status_code=502,
                ) from None
            elif "disabled in stage e" in msg.lower() or "real network calls are disabled" in msg.lower():
                raise ProviderDisabledError(
                    "DeepSeek network transport is offline/disabled"
                ) from None
            else:
                raise AIProviderError(
                    f"DeepSeek upstream transport error: {redact_sensitive_string(msg)}",
                    category=ProviderErrorCategory.PROVIDER_UNAVAILABLE,
                ) from None

        # 6. 校验原始响应结构
        if not isinstance(raw_response, dict):
            raise ProviderInvalidResponseError("Invalid response from DeepSeek: expected JSON object")

        # 兼容两种返回：OpenAI 标准 choices 结构 或 简化结构 (适配内部测试 FakeTransport)
        content: str = ""
        finish_reason: Optional[str] = "stop"
        usage: Optional[Dict[str, Any]] = raw_response.get("usage")

        if "choices" in raw_response and isinstance(raw_response["choices"], list) and len(raw_response["choices"]) > 0:
            choice = raw_response["choices"][0]
            finish_reason = choice.get("finish_reason", "stop")
            message_obj = choice.get("message", {})
            content = message_obj.get("content", "") or ""
        elif "answer" in raw_response:
            # 兼容网关已有的直接 dict 模拟格式
            content = json.dumps(raw_response, ensure_ascii=False) if response_format_dict else str(raw_response["answer"])
        else:
            raise ProviderInvalidResponseError("Missing 'choices' or content in DeepSeek response payload")

        # 7. 空响应拦截
        if not content or not content.strip():
            raise ProviderInvalidResponseError("DeepSeek API returned empty response content")

        # 8. 结构化 JSON 校验
        parsed_json: Optional[Dict[str, Any]] = None
        if response_format_dict and response_format_dict.get("type") == "json_object":
            try:
                parsed_json = json.loads(content)
                if not isinstance(parsed_json, dict):
                    raise ProviderInvalidResponseError("DeepSeek JSON output must be a valid JSON dictionary")
            except json.JSONDecodeError as je:
                raise ProviderInvalidResponseError(f"DeepSeek response content is not valid JSON: {str(je)}")

        return AIProviderResponse(
            content=content,
            model=raw_response.get("model", target_model),
            provider=self.provider_name,
            usage=usage,
            finish_reason=finish_reason,
            parsed_json=parsed_json,
        )

    async def generate(
        self,
        prompt_context: LearningPromptContext,
    ) -> StructuredAIResponse:
        """
        实现 AIProviderAdapter 接口，满足网关 AI 伴学主干调用契约
        """
        # 1. 组装只读提示词载荷
        prompt_payload = build_external_prompt(
            prompt_context,
            model=self.model,
        )

        ai_req = AIProviderRequest(
            system_prompt=prompt_payload.system_prompt,
            user_prompt=prompt_payload.user_prompt,
            response_format="json_object",
            temperature=prompt_payload.temperature,
            user_id=prompt_context.system_facts.student_id,
            model=self.model,
        )

        # 2. 执行模型调用
        ai_resp = await self.complete(ai_req)

        # 3. 越权决策拦截防御扫描
        parsed = ai_resp.parsed_json or {}
        for forbidden_key in FORBIDDEN_DECISION_FIELDS:
            if forbidden_key in parsed:
                raise ProviderException(
                    f"External DeepSeek LLM returned forbidden decision field: {forbidden_key}"
                )

        # 4. 构造标准规范化契约 StructuredAIResponse
        if "answer" not in parsed or not isinstance(parsed["answer"], str):
            raise ProviderException(
                "Invalid StructuredAIResponse from DeepSeek: missing required 'answer' string"
            )

        referenced_facts = parsed.get("referenced_facts", [])
        if not isinstance(referenced_facts, list):
            referenced_facts = [str(referenced_facts)]

        grounding_status = parsed.get("grounding_status", "grounded")
        if grounding_status not in ("grounded", "insufficient_context"):
            grounding_status = "grounded"

        suggested_explanation = parsed.get("suggested_explanation")
        if suggested_explanation is not None and not isinstance(suggested_explanation, str):
            suggested_explanation = str(suggested_explanation)

        return StructuredAIResponse(
            answer=parsed["answer"],
            referenced_facts=[str(f) for f in referenced_facts],
            suggested_explanation=suggested_explanation,
            grounding_status=grounding_status,
        )


# ==============================================================================
# 确定性 Mock DeepSeek Provider (测试与离线环境专用)
# ==============================================================================

class MockDeepSeekProvider(AIProviderAdapter):
    """
    100% 确定性 Mock DeepSeek 服务商实现
    
    特征：
    - 绝不调用任何外部网络与外部 API
    - 相同输入（20 次连续调用）严格产生完全一致的输出
    - 零 math.random()、零 time()、零 uuid()
    - 声明 MOCK_RESPONSE 状态，不伪造为真实在线 DeepSeek
    """

    def __init__(
        self,
        name: str = "mock-deepseek",
        model: str = "deepseek-flash",
    ):
        self._name = name
        self.model = model

    @property
    def provider_name(self) -> str:
        return self._name

    async def complete(self, request: AIProviderRequest) -> AIProviderResponse:
        """根据请求确定性返回结构化 Mock 响应"""
        # 即使是 Mock 也必须验证无 PII 泄露
        assert_no_pii(request.system_prompt, context_name="system_prompt")
        assert_no_pii(request.user_prompt, context_name="user_prompt")
        assert_no_pii(request.user_id, context_name="user_id")

        is_json = False
        if request.response_format:
            if isinstance(request.response_format, str) and request.response_format == "json_object":
                is_json = True
            elif isinstance(request.response_format, dict) and request.response_format.get("type") == "json_object":
                is_json = True

        if is_json:
            parsed = {
                "answer": f"这是由 MockDeepSeekProvider 为「{request.user_prompt[:20]}」生成的确定性回答。",
                "referenced_facts": ["fact_mock_verified=true"],
                "suggested_explanation": "当前为离线确定性测试模拟响应。",
                "grounding_status": "grounded",
                "mock_marker": ProviderErrorCategory.MOCK_RESPONSE.value,
            }
            content = json.dumps(parsed, ensure_ascii=False)
        else:
            parsed = None
            content = f"Mock DeepSeek 纯文本输出：{request.user_prompt[:30]}"

        return AIProviderResponse(
            content=content,
            model=self.model,
            provider=self.provider_name,
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            finish_reason="stop",
            parsed_json=parsed,
        )

    async def generate(
        self,
        prompt_context: LearningPromptContext,
    ) -> StructuredAIResponse:
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
            f"（编号 {sf.current_knowledge_id}）。当前掌握度为 {sf.current_mastery_percent:.1f}%。"
            f"针对提问「{question}」，建议下一步：{sf.next_action.label}。"
        )

        return StructuredAIResponse(
            answer=answer,
            referenced_facts=referenced_facts,
            suggested_explanation=f"考点 {sf.current_knowledge_id} 建议行动为 {sf.next_action.label}。",
            grounding_status="grounded",
        )


# 向后兼容与规范别名
MockAIProvider = MockDeepSeekProvider
