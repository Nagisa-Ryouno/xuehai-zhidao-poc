# -*- coding: utf-8 -*-
"""
gateway.evaluation.judge.config
学海智导 (Xuehai Zhidao) V2 - Phase 3 / Sprint 7-D
Stage G3 / Checkpoint 1: LLM Judge 安全配置与传输构建契约

核心原则：
1. 默认安全关闭：默认 AI_JUDGE_ENABLED=False，未经显式配置绝对禁止开启外部网络与真实模型
2. 零密钥泄露：__repr__ 与日志输出中严禁出现原始 API Key，提供严格脱敏函数
3. 强类型与合法性校验：对超时、重试、温度、熔断阈值及 Base URL 进行严格边界防御
4. 安全传输工厂：build_judge_transport 在 enabled=False 时返回 DisabledNetworkTransport
"""

from dataclasses import dataclass, field
import os
import re
from typing import Optional
from urllib.parse import urlparse

from gateway.transport import (
    DisabledNetworkTransport,
    HttpLLMTransport,
    LLMTransport,
)


_TRUTHY_VALUES = {"true", "1", "yes", "t", "y"}


@dataclass
class JudgeSettings:
    """
    LLM Judge 独立安全配置对象
    """
    enabled: bool = False
    provider: str = "fake"
    model: str = "deepseek-chat"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    timeout_ms: int = 5000
    max_retries: int = 2
    temperature: float = 0.0
    circuit_fail_threshold: int = 3

    def __post_init__(self):
        # 1. 运行参数边界校验
        if self.timeout_ms <= 0:
            raise ValueError(f"timeout_ms must be positive (> 0), got: {self.timeout_ms}")

        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative (>= 0), got: {self.max_retries}")

        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError(f"temperature must be between 0.0 and 2.0, got: {self.temperature}")

        if self.circuit_fail_threshold <= 0:
            raise ValueError(
                f"circuit_fail_threshold must be positive (> 0), got: {self.circuit_fail_threshold}"
            )

        # 2. Base URL 合法性校验
        if self.base_url is not None:
            url_str = self.base_url.strip()
            parsed = urlparse(url_str)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValueError(
                    f"Invalid base_url: '{self.base_url}'. Must be a valid http/https URL."
                )

    def get_masked_api_key(self) -> str:
        """
        安全脱敏获取 API Key 用于日志与审计，绝不暴露完整密钥
        """
        if not self.api_key or not self.api_key.strip():
            return "<UNSET>"
        clean = self.api_key.strip()
        if len(clean) <= 8:
            return "***"
        return f"{clean[:3]}...{clean[-4:]}"

    def __repr__(self) -> str:
        return (
            f"JudgeSettings(enabled={self.enabled}, provider='{self.provider}', "
            f"model='{self.model}', base_url={repr(self.base_url)}, "
            f"api_key='{self.get_masked_api_key()}', timeout_ms={self.timeout_ms}, "
            f"max_retries={self.max_retries}, temperature={self.temperature}, "
            f"circuit_fail_threshold={self.circuit_fail_threshold})"
        )

    @classmethod
    def from_env(cls) -> "JudgeSettings":
        """
        从受控环境变量读取生成强类型 JudgeSettings
        优先级：显式环境变量 > 默认安全值
        """
        enabled_raw = os.getenv("AI_JUDGE_ENABLED", "false").strip().lower()
        enabled = enabled_raw in _TRUTHY_VALUES

        provider = os.getenv("AI_JUDGE_PROVIDER", "fake").strip()
        model = os.getenv("AI_JUDGE_MODEL", "deepseek-chat").strip()
        base_url = os.getenv("AI_JUDGE_BASE_URL", None)
        if base_url:
            base_url = base_url.strip() or None

        api_key = os.getenv("AI_JUDGE_API_KEY", None)
        if api_key:
            api_key = api_key.strip() or None

        timeout_ms_raw = os.getenv("AI_JUDGE_TIMEOUT_MS", "5000").strip()
        try:
            timeout_ms = int(timeout_ms_raw)
        except ValueError:
            timeout_ms = 5000

        max_retries_raw = os.getenv("AI_JUDGE_MAX_RETRIES", "2").strip()
        try:
            max_retries = int(max_retries_raw)
        except ValueError:
            max_retries = 2

        temperature_raw = os.getenv("AI_JUDGE_TEMPERATURE", "0.0").strip()
        try:
            temperature = float(temperature_raw)
        except ValueError:
            temperature = 0.0

        circuit_fail_raw = os.getenv("AI_JUDGE_CIRCUIT_FAIL_THRESHOLD", "3").strip()
        try:
            circuit_fail_threshold = int(circuit_fail_raw)
        except ValueError:
            circuit_fail_threshold = 3

        return cls(
            enabled=enabled,
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            timeout_ms=timeout_ms,
            max_retries=max_retries,
            temperature=temperature,
            circuit_fail_threshold=circuit_fail_threshold,
        )


_cached_settings: Optional[JudgeSettings] = None


def get_judge_settings(reload: bool = False) -> JudgeSettings:
    """获取 JudgeSettings 单例配置"""
    global _cached_settings
    if _cached_settings is None or reload:
        _cached_settings = JudgeSettings.from_env()
    return _cached_settings


def build_judge_transport(settings: Optional[JudgeSettings] = None) -> LLMTransport:
    """
    根据配置构建安全的 Judge 传输层实例

    安全红线：
    当 enabled=False 时，必须返回 DisabledNetworkTransport，严禁初始化任何真实 HTTP Transport！
    """
    cfg = settings or get_judge_settings()

    if not cfg.enabled:
        return DisabledNetworkTransport()

    # 仅在明确启用时构建 HttpLLMTransport
    return HttpLLMTransport(
        base_url=cfg.base_url or "https://api.deepseek.com/v1",
        api_key=cfg.api_key,
        model=cfg.model,
        timeout_ms=cfg.timeout_ms,
    )
